from __future__ import annotations

import re

from app.clinical_rules import (
    detect_symptoms,
)
from app.i18n import normalize_language, t
from app.llm import LocalLLM
from app.pain_scale import (
    functional_anchor_prompt,
    pain_severity,
)
from app.report import generate_report
from app.schemas import ConversationState
from app.validators import (
    ValidationAction,
    validate_comparison_answer,
    validate_functional_impact_answer,
    validate_pain_location_answer,
    validate_pain_score_answer,
    validate_red_flags_answer,
    validate_side_effect_answer,
    validate_treatment_answer,
    classify_emergency_visit,
    classify_medication_changed,
    classify_respondent_source,
    classify_symptom_severity,
    classify_symptom_status,
    classify_yes_no_unsure,
)


class ConversationEngine:
    def __init__(self, llm: LocalLLM | None = None) -> None:
        self.llm = llm or LocalLLM()

    def start(self, language: str = "en") -> ConversationState:
        state = ConversationState(step="readiness_hearing", language=normalize_language(language))
        self._assistant(state, t(state.language, "intro"))
        self._assistant(state, t(state.language, "hearing_check"))
        return state

    def handle_user_message(self, state: ConversationState, text: str) -> ConversationState:
        user_text = text.strip()
        if not user_text:
            self._assistant(state, t(state.language, "not_caught"))
            return state

        state.user(user_text)

        if state.complete:
            self._assistant(
                state,
                t(state.language, "already_complete"),
            )
            return state

        detected = detect_symptoms(user_text)
        self._merge_safety_detection(state, user_text, detected)
        if state.safety.red_flag_present and not state.escalation_message_spoken:
            state.safety.action_advised = t(state.language, "urgent_action")
            state.escalation_message_spoken = True
            self._assistant(state, t(state.language, "escalation"))
            return state

        if state.pending_clarification:
            if self._handle_pending_clarification(state, user_text):
                return state

        if state.step == "readiness_hearing":
            self._handle_readiness_hearing(state, user_text)
        elif state.step == "readiness_time":
            self._handle_readiness_time(state, user_text)
        elif state.step == "permission":
            self._handle_permission(state, user_text)
        elif state.step == "identity":
            self._handle_identity(state, user_text)
        elif state.step == "respondent_source":
            self._handle_respondent_source(state, user_text)
        elif state.step == "average_pain_score":
            self._handle_average_pain_score(state, user_text)
        elif state.step == "current_pain_score":
            self._handle_current_pain_score(state, user_text)
        elif state.step == "pain_location":
            self._handle_pain_location(state, user_text)
        elif state.step == "functional_impact":
            self._handle_functional_impact(state, user_text)
        elif state.step == "usual_comparison":
            self._handle_usual_comparison(state, user_text)
        elif state.step == "treatment_context":
            self._handle_treatment_context(state, user_text)
        elif state.step == "side_effects":
            self._handle_side_effects(state, user_text)
        elif state.step == "side_effect_description":
            self._handle_side_effect_description(state, user_text)
        elif state.step == "side_effect_start":
            self._handle_side_effect_start(state, user_text)
        elif state.step == "side_effect_status":
            self._handle_side_effect_status(state, user_text)
        elif state.step == "side_effect_severity":
            self._handle_side_effect_severity(state, user_text)
        elif state.step == "medication_changed":
            self._handle_medication_changed(state, user_text)
        elif state.step == "doctor_contacted":
            self._handle_doctor_contacted(state, user_text)
        elif state.step == "emergency_visit":
            self._handle_emergency_visit(state, user_text)
        elif state.step == "red_flags":
            self._handle_red_flags(state, user_text)
        elif state.step == "closing":
            self._complete(state)
        else:
            self._assistant(state, t(state.language, "continue"))

        return state

    def _handle_readiness_hearing(self, state: ConversationState, text: str) -> None:
        answer = classify_yes_no_unsure(text)
        if answer == "unknown":
            self._assistant(state, t(state.language, "hearing_check"))
            return
        state.readiness["hearing_clear"] = answer
        state.step = "readiness_time"
        self._assistant(state, t(state.language, "time_check"))

    def _handle_readiness_time(self, state: ConversationState, text: str) -> None:
        answer = classify_yes_no_unsure(text)
        if answer == "unknown":
            self._assistant(state, t(state.language, "time_check"))
            return
        state.readiness["suitable_time"] = answer
        if answer == "no":
            state.step = "complete"
            state.complete = True
            state.report = generate_report(state)
            self._assistant(state, t(state.language, "not_suitable_time"))
            return
        state.step = "permission"
        self._assistant(state, t(state.language, "permission_check"))

    def _handle_permission(self, state: ConversationState, text: str) -> None:
        answer = classify_yes_no_unsure(text)
        if answer == "unknown":
            self._assistant(state, t(state.language, "permission_check"))
            return
        state.readiness["permission_to_continue"] = answer
        if answer == "no":
            state.step = "complete"
            state.complete = True
            state.report = generate_report(state)
            self._assistant(state, t(state.language, "permission_declined"))
            return
        state.step = "identity"
        self._assistant(state, t(state.language, "identity_prompt"))

    def _handle_identity(self, state: ConversationState, text: str) -> None:
        self._extract_identity(state, text)

        missing = []
        if not state.identity.name:
            missing.append(t(state.language, "identity_name"))
        if not state.identity.mobile_number:
            missing.append(t(state.language, "identity_mobile"))
        if state.identity.age is None:
            missing.append(t(state.language, "identity_age"))

        if missing:
            self._assistant(state, t(state.language, "missing_identity", missing=_join_missing(missing, state.language)))
            return

        state.step = "respondent_source"
        self._assistant(state, t(state.language, "respondent_source"))

    def _handle_respondent_source(self, state: ConversationState, text: str) -> None:
        state.respondent_source = classify_respondent_source(text)
        state.step = "average_pain_score"
        self._assistant(state, t(state.language, "average_pain_prompt"))

    def _handle_average_pain_score(self, state: ConversationState, text: str) -> None:
        validation = validate_pain_score_answer(text)
        if not validation.accepted:
            self._assistant(state, validation.prompt(state.language) or t(state.language, "invalid_pain_score"))
            return

        score = int(validation.value)
        state.pain.average_24h_score = score
        state.pain.average_24h_severity = pain_severity(score)
        state.pain.average_24h_score_confirmed = True
        state.pain.patient_words.append(f"24h average pain: {text}")
        state.step = "current_pain_score"
        self._assistant(
            state,
            t(state.language, "current_pain_prompt"),
        )

    def _handle_current_pain_score(self, state: ConversationState, text: str) -> None:
        validation = validate_pain_score_answer(text)
        if not validation.accepted:
            self._assistant(state, validation.prompt(state.language) or t(state.language, "invalid_pain_score"))
            return

        score = int(validation.value)
        state.pain.score = score
        state.pain.severity = pain_severity(score)
        state.pain.current_score_confirmed = True
        state.pain.patient_words.append(f"current pain: {text}")
        state.step = "pain_location"
        self._assistant(state, t(state.language, "pain_location"))

    def _handle_pain_location(self, state: ConversationState, text: str) -> None:
        validation = validate_pain_location_answer(text)
        if not validation.accepted:
            self._assistant(state, validation.prompt(state.language) or t(state.language, "pain_location"))
            return

        state.pain.location = _clean_short_answer(text)
        state.pain.patient_words.append(text)
        state.step = "functional_impact"
        self._assistant(state, functional_anchor_prompt(state.pain.score, state.language))

    def _handle_functional_impact(self, state: ConversationState, text: str) -> None:
        validation = validate_functional_impact_answer(state, text)
        if not validation.accepted:
            if validation.reason == "pain_zero_conflicts_with_functional_impact":
                state.pending_clarification = "pain_zero_after_function"
            elif validation.reason == "severe_score_conflicts_with_no_impact":
                state.pending_clarification = "severe_score_no_impact"
            self._assistant(state, validation.prompt(state.language) or t(state.language, "functional_impact"))
            return

        state.pain.functional_impact = _clean_short_answer(text, max_len=400)
        state.pain.patient_words.append(text)
        state.step = "usual_comparison"
        self._assistant(
            state,
            t(state.language, "comparison"),
        )

    def _handle_usual_comparison(self, state: ConversationState, text: str) -> None:
        validation = validate_comparison_answer(state, text)
        if not validation.accepted:
            if validation.reason == "pain_zero_conflicts_with_worse_comparison":
                state.pending_clarification = "pain_zero_after_worse"
            self._assistant(state, validation.prompt(state.language) or t(state.language, "comparison"))
            return

        state.pain.usual_comparison = str(validation.value)
        state.pain.patient_words.append(text)
        state.step = "treatment_context"
        self._assistant(
            state,
            t(state.language, "treatment"),
        )

    def _handle_treatment_context(self, state: ConversationState, text: str) -> None:
        validation = validate_treatment_answer(text)
        if not validation.accepted:
            self._assistant(state, validation.prompt(state.language) or t(state.language, "treatment"))
            return

        if not _is_negative(text):
            state.safety.medication_context = _clean_short_answer(text, max_len=400)
        else:
            state.safety.medication_context = t(state.language, "none_reported")
        state.step = "side_effects"
        self._assistant(state, t(state.language, "side_effects"))

    def _handle_side_effects(self, state: ConversationState, text: str) -> None:
        validation = validate_side_effect_answer(text)
        if validation.action == ValidationAction.ESCALATE:
            state.safety.action_advised = t(state.language, "urgent_action")
            state.escalation_message_spoken = True
            self._assistant(state, t(state.language, "escalation"))
            return
        if not validation.accepted:
            self._assistant(state, validation.prompt(state.language) or t(state.language, "side_effects"))
            return

        result = classify_yes_no_unsure(text)
        state.safety.side_effect_screening_result = result
        if result in {"yes", "uncertain"}:
            state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))
        elif result != "no" and not _is_negative(text):
            state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))

        if state.safety.red_flag_present and not state.escalation_message_spoken:
            state.safety.action_advised = t(state.language, "urgent_action")
            state.escalation_message_spoken = True
            self._assistant(state, t(state.language, "escalation"))
            return

        if result in {"yes", "uncertain"} or (result == "unknown" and not _is_negative(text) and text.strip()):
            state.step = "side_effect_description"
            self._assistant(state, t(state.language, "side_effect_description"))
            return

        state.step = "red_flags"
        self._assistant(state, t(state.language, "red_flags"))

    def _handle_side_effect_description(self, state: ConversationState, text: str) -> None:
        if not _is_negative(text):
            state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))
        state.step = "side_effect_start"
        self._assistant(state, t(state.language, "side_effect_start"))

    def _handle_side_effect_start(self, state: ConversationState, text: str) -> None:
        state.safety.symptom_start_time = _clean_short_answer(text, max_len=160)
        state.step = "side_effect_status"
        self._assistant(state, t(state.language, "side_effect_status"))

    def _handle_side_effect_status(self, state: ConversationState, text: str) -> None:
        state.safety.symptom_status = classify_symptom_status(text)
        state.step = "side_effect_severity"
        self._assistant(state, t(state.language, "side_effect_severity"))

    def _handle_side_effect_severity(self, state: ConversationState, text: str) -> None:
        state.safety.symptom_severity = classify_symptom_severity(text)
        if state.safety.symptom_severity == "severe":
            state.safety.researcher_alert_required = True
        state.step = "medication_changed"
        self._assistant(state, t(state.language, "medication_changed"))

    def _handle_medication_changed(self, state: ConversationState, text: str) -> None:
        state.safety.medication_changed = classify_medication_changed(text)
        if state.safety.medication_changed == "yes":
            state.safety.researcher_alert_required = True
        state.step = "doctor_contacted"
        self._assistant(state, t(state.language, "doctor_contacted"))

    def _handle_doctor_contacted(self, state: ConversationState, text: str) -> None:
        state.safety.doctor_contacted = classify_yes_no_unsure(text)
        state.step = "emergency_visit"
        self._assistant(state, t(state.language, "emergency_visit"))

    def _handle_emergency_visit(self, state: ConversationState, text: str) -> None:
        state.safety.emergency_visit_or_hospitalization = classify_emergency_visit(text)
        if state.safety.emergency_visit_or_hospitalization == "yes":
            state.safety.researcher_alert_required = True
        state.step = "red_flags"
        self._assistant(state, t(state.language, "red_flags"))

    def _handle_red_flags(self, state: ConversationState, text: str) -> None:
        validation = validate_red_flags_answer(text)
        if validation.action == ValidationAction.ESCALATE:
            state.safety.action_advised = t(state.language, "urgent_action")
            state.escalation_message_spoken = True
            self._assistant(state, t(state.language, "escalation"))
            return
        if not validation.accepted:
            self._assistant(state, validation.prompt(state.language) or t(state.language, "red_flags"))
            return

        if not _is_negative(text):
            state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))

        if state.safety.red_flag_present:
            state.safety.action_advised = t(state.language, "urgent_action")
            if not state.escalation_message_spoken:
                state.escalation_message_spoken = True
                self._assistant(state, t(state.language, "escalation"))
                return

        self._complete(state)

    def _complete(self, state: ConversationState) -> None:
        state.step = "complete"
        state.complete = True
        if not state.safety.red_flag_present:
            state.safety.action_advised = t(state.language, "no_urgent_escalation")
        state.report = generate_report(state)
        self._assistant(
            state,
            t(state.language, "complete"),
        )

    def _merge_safety_detection(self, state: ConversationState, text: str, detected: dict[str, object]) -> None:
        red_flags = detected.get("red_flags", [])
        non_urgent = detected.get("non_urgent", [])
        uncertain = bool(detected.get("uncertain", False))

        if isinstance(red_flags, list) and red_flags:
            state.safety.red_flag_present = True
            for item in red_flags:
                if item not in state.safety.red_flag_symptoms:
                    state.safety.red_flag_symptoms.append(item)
            if text not in state.safety.reported_symptoms:
                state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))

        if isinstance(non_urgent, list):
            for item in non_urgent:
                if item not in state.safety.non_urgent_concerns:
                    state.safety.non_urgent_concerns.append(item)

        if uncertain:
            state.safety.red_flag_uncertain = True

    def _extract_identity(self, state: ConversationState, text: str) -> None:
        cleaned = text.strip()

        age_match = re.search(
            r"\b(?:age(?:d)?|i am|i'm|im)?\s*(\d{1,3})\s*(?:years old|year old|yo|y/o)?\b|(\d{1,3})\s*岁",
            cleaned.lower(),
        )
        if age_match:
            age = int(age_match.group(1) or age_match.group(2))
            if 1 <= age <= 120:
                state.identity.age = age

        phone_match = re.search(r"(?:\+?\d[\d\s().-]{6,}\d)", cleaned)
        if phone_match:
            digits = re.sub(r"\D", "", phone_match.group(0))
            if 7 <= len(digits) <= 15:
                state.identity.mobile_number = phone_match.group(0).strip()

        name = self._extract_name(cleaned)
        if name:
            state.identity.name = name

    def _extract_name(self, text: str) -> str | None:
        zh_patterns = (
            r"(?:我叫|我的名字是|姓名是|名字是)\s*([\u4e00-\u9fff]{2,8})",
            r"(?:我是)\s*([\u4e00-\u9fff]{2,8})",
        )
        for pattern in zh_patterns:
            match = re.search(pattern, text)
            if match:
                candidate = re.split(r"(?:手机|手机号|电话|号码|年龄|岁)", match.group(1))[0]
                if candidate:
                    return candidate

        patterns = (
            r"\bmy name is\s+([a-zA-Z][a-zA-Z ,.'-]{1,60})",
            r"\bi am\s+([a-zA-Z][a-zA-Z ,.'-]{1,60})",
            r"\bi'm\s+([a-zA-Z][a-zA-Z ,.'-]{1,60})",
            r"\bname\s+is\s+([a-zA-Z][a-zA-Z ,.'-]{1,60})",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                candidate = re.split(
                    r"[,;]|\b(?:and|age|phone|mobile|number|handphone|hp|my mobile|my phone)\b",
                    candidate,
                    flags=re.I,
                )[0]
                return _title_name(candidate)

        without_phone = re.sub(r"(?:\+?\d[\d\s().-]{6,}\d)", " ", text)
        without_age = re.sub(r"\b\d{1,3}\b", " ", without_phone)
        words = re.findall(r"[A-Za-z][A-Za-z.'-]*", without_age)
        blocked = {
            "my",
            "name",
            "is",
            "and",
            "phone",
            "mobile",
            "number",
            "handphone",
            "hp",
            "age",
            "years",
            "old",
            "i",
            "am",
            "im",
        }
        name_words = [word for word in words if word.lower() not in blocked]
        if 1 <= len(name_words) <= 4:
            return _title_name(" ".join(name_words))
        return None

    def _assistant(self, state: ConversationState, message: str) -> None:
        state.assistant(self.llm.polish_assistant_reply(message))

    def _handle_pending_clarification(self, state: ConversationState, text: str) -> bool:
        pending = state.pending_clarification
        state.pending_clarification = None

        if pending in {"pain_zero_after_function", "pain_zero_after_worse", "severe_score_no_impact"}:
            score_validation = validate_pain_score_answer(text)
            if score_validation.accepted:
                score = int(score_validation.value)
                state.pain.score = score
                state.pain.severity = pain_severity(score)
                state.pain.patient_words.append(f"clarified pain score: {text}")
                if pending == "pain_zero_after_worse" and score > 0:
                    state.pain.usual_comparison = "worse"
                    state.step = "treatment_context"
                    self._assistant(
                        state,
                        t(state.language, "got_it_treatment"),
                    )
                    return True
                if pending in {"pain_zero_after_function", "severe_score_no_impact"}:
                    state.step = "functional_impact"
                    self._assistant(state, functional_anchor_prompt(score, state.language))
                    return True

            if _is_affirmative(text):
                if pending == "pain_zero_after_worse":
                    state.pain.usual_comparison = "worse"
                    state.step = "treatment_context"
                    self._assistant(state, t(state.language, "got_it_treatment"))
                    return True
                state.step = "functional_impact"
                self._assistant(state, t(state.language, "thanks_function"))
                return True

            if _is_negative(text):
                if pending == "pain_zero_after_worse":
                    state.pain.usual_comparison = "same"
                    state.step = "treatment_context"
                    self._assistant(state, t(state.language, "ok_treatment"))
                    return True
                state.pain.score = 0 if pending == "pain_zero_after_function" else state.pain.score
                state.pain.severity = pain_severity(state.pain.score)
                state.step = "functional_impact"
                self._assistant(state, t(state.language, "ok_function"))
                return True

            state.pending_clarification = pending
            self._assistant(state, t(state.language, "clarify_score"))
            return True

        return False


def _clean_short_answer(text: str, max_len: int = 240) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def _is_negative(text: str) -> bool:
    cleaned = text.lower().strip()
    compact = re.sub(r"\s+", "", cleaned)
    if compact in {"没有", "没", "无", "没有不舒服", "没有症状", "没事", "没有这些", "不"}:
        return True
    return bool(re.fullmatch(r"(no|none|nothing|nope|not sure no|no symptoms|nothing concerning)[.! ]*", cleaned))


def _is_affirmative(text: str) -> bool:
    cleaned = text.lower().strip()
    compact = re.sub(r"\s+", "", cleaned)
    if compact in {"有", "是", "对", "对的", "是的", "没错"}:
        return True
    return bool(re.fullmatch(r"(yes|yeah|yep|correct|that's right|that is right|right)[.! ]*", cleaned))


def _title_name(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip(" ,.'-"))
    if not cleaned:
        return ""
    if any("\u4e00" <= char <= "\u9fff" for char in cleaned):
        return cleaned
    return " ".join(part.capitalize() for part in cleaned.split())


def _join_missing(items: list[str], language: str) -> str:
    if language == "zh-CN":
        return "、".join(items)
    return " and ".join(items)
