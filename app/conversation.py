from __future__ import annotations

import re

from app.clinical_rules import (
    detect_symptoms,
    escalation_message,
    red_flags_prompt,
    side_effects_prompt,
)
from app.llm import LocalLLM
from app.pain_scale import (
    functional_anchor_prompt,
    pain_prompt,
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
)


INTRO_MESSAGE = (
    "Hello, I'm a researcher from Peking University Medical Hospital. "
    "I'm calling for a short joint pain check-in. "
    "May I confirm your name, mobile number, and age?"
)


class ConversationEngine:
    def __init__(self, llm: LocalLLM | None = None) -> None:
        self.llm = llm or LocalLLM()

    def start(self) -> ConversationState:
        state = ConversationState(step="identity")
        self._assistant(state, INTRO_MESSAGE)
        return state

    def handle_user_message(self, state: ConversationState, text: str) -> ConversationState:
        user_text = text.strip()
        if not user_text:
            self._assistant(state, "I didn't catch that. Could you please say that again?")
            return state

        state.user(user_text)

        if state.complete:
            self._assistant(
                state,
                "This check-in is complete. You can start a new one if needed.",
            )
            return state

        detected = detect_symptoms(user_text)
        self._merge_safety_detection(state, user_text, detected)
        if state.safety.red_flag_present and not state.escalation_message_spoken:
            state.safety.action_advised = "urgent medical care / emergency services / contact caregiver"
            state.escalation_message_spoken = True
            self._assistant(state, escalation_message())
            return state

        if state.pending_clarification:
            if self._handle_pending_clarification(state, user_text):
                return state

        if state.step == "identity":
            self._handle_identity(state, user_text)
        elif state.step == "pain_score":
            self._handle_pain_score(state, user_text)
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
        elif state.step == "red_flags":
            self._handle_red_flags(state, user_text)
        elif state.step == "closing":
            self._complete(state)
        else:
            self._assistant(state, "Let's continue with your pain check-in.")

        return state

    def _handle_identity(self, state: ConversationState, text: str) -> None:
        self._extract_identity(state, text)

        missing = []
        if not state.identity.name:
            missing.append("name")
        if not state.identity.mobile_number:
            missing.append("mobile number")
        if state.identity.age is None:
            missing.append("age")

        if missing:
            self._assistant(state, f"Thank you. Could I also have your {' and '.join(missing)}?")
            return

        state.step = "pain_score"
        self._assistant(
            state,
            f"Thank you, {state.identity.name}. {pain_prompt()}",
        )

    def _handle_pain_score(self, state: ConversationState, text: str) -> None:
        validation = validate_pain_score_answer(text)
        if not validation.accepted:
            self._assistant(state, validation.clarification_prompt or "I need a number from 0 to 10.")
            return

        score = int(validation.value)
        state.pain.score = score
        state.pain.severity = pain_severity(score)
        state.pain.patient_words.append(text)
        state.step = "pain_location"
        self._assistant(state, "Where is the pain today?")

    def _handle_pain_location(self, state: ConversationState, text: str) -> None:
        validation = validate_pain_location_answer(text)
        if not validation.accepted:
            self._assistant(state, validation.clarification_prompt or "Where is the pain today?")
            return

        state.pain.location = _clean_short_answer(text)
        state.pain.patient_words.append(text)
        state.step = "functional_impact"
        self._assistant(state, functional_anchor_prompt(state.pain.score))

    def _handle_functional_impact(self, state: ConversationState, text: str) -> None:
        validation = validate_functional_impact_answer(state, text)
        if not validation.accepted:
            if validation.reason == "pain_zero_conflicts_with_functional_impact":
                state.pending_clarification = "pain_zero_after_function"
            elif validation.reason == "severe_score_conflicts_with_no_impact":
                state.pending_clarification = "severe_score_no_impact"
            self._assistant(state, validation.clarification_prompt or "How is the pain affecting you today?")
            return

        state.pain.functional_impact = _clean_short_answer(text, max_len=400)
        state.pain.patient_words.append(text)
        state.step = "usual_comparison"
        self._assistant(
            state,
            "Is that better, worse, or about the same as usual?",
        )

    def _handle_usual_comparison(self, state: ConversationState, text: str) -> None:
        validation = validate_comparison_answer(state, text)
        if not validation.accepted:
            if validation.reason == "pain_zero_conflicts_with_worse_comparison":
                state.pending_clarification = "pain_zero_after_worse"
            self._assistant(state, validation.clarification_prompt or "Is it better, worse, or about the same?")
            return

        state.pain.usual_comparison = str(validation.value)
        state.pain.patient_words.append(text)
        state.step = "treatment_context"
        self._assistant(
            state,
            "Are you using anything for the pain now? Tablets, cream, injections, or therapy?",
        )

    def _handle_treatment_context(self, state: ConversationState, text: str) -> None:
        validation = validate_treatment_answer(text)
        if not validation.accepted:
            self._assistant(state, validation.clarification_prompt or "Are you using anything for the pain now?")
            return

        if not _is_negative(text):
            state.safety.medication_context = _clean_short_answer(text, max_len=400)
        else:
            state.safety.medication_context = "none reported"
        state.step = "side_effects"
        self._assistant(state, side_effects_prompt())

    def _handle_side_effects(self, state: ConversationState, text: str) -> None:
        validation = validate_side_effect_answer(text)
        if validation.action == ValidationAction.ESCALATE:
            state.safety.action_advised = "urgent medical care / emergency services / contact caregiver"
            state.escalation_message_spoken = True
            self._assistant(state, escalation_message())
            return
        if not validation.accepted:
            self._assistant(state, validation.clarification_prompt or "Any side effects or new symptoms?")
            return

        if not _is_negative(text):
            state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))

        if state.safety.red_flag_present and not state.escalation_message_spoken:
            state.safety.action_advised = "urgent medical care / emergency services / contact caregiver"
            state.escalation_message_spoken = True
            self._assistant(state, escalation_message())
            return

        state.step = "red_flags"
        self._assistant(state, red_flags_prompt())

    def _handle_red_flags(self, state: ConversationState, text: str) -> None:
        validation = validate_red_flags_answer(text)
        if validation.action == ValidationAction.ESCALATE:
            state.safety.action_advised = "urgent medical care / emergency services / contact caregiver"
            state.escalation_message_spoken = True
            self._assistant(state, escalation_message())
            return
        if not validation.accepted:
            self._assistant(state, validation.clarification_prompt or "Please answer yes or no.")
            return

        if not _is_negative(text):
            state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))

        if state.safety.red_flag_present:
            state.safety.action_advised = "urgent medical care / emergency services / contact caregiver"
            if not state.escalation_message_spoken:
                state.escalation_message_spoken = True
                self._assistant(state, escalation_message())
                return

        self._complete(state)

    def _complete(self, state: ConversationState) -> None:
        state.step = "complete"
        state.complete = True
        if not state.safety.red_flag_present:
            state.safety.action_advised = "no urgent escalation"
        report = generate_report(state)
        state.report = self.llm.summarize_report(report)
        self._assistant(
            state,
            "Thank you. That's all for now. I'll prepare the doctor report.",
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

        age_match = re.search(r"\b(?:age(?:d)?|i am|i'm|im)?\s*(\d{1,3})\s*(?:years old|year old|yo|y/o)?\b", cleaned.lower())
        if age_match:
            age = int(age_match.group(1))
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
                        "Got it. Are you using anything for the pain now?",
                    )
                    return True
                if pending in {"pain_zero_after_function", "severe_score_no_impact"}:
                    state.step = "functional_impact"
                    self._assistant(state, functional_anchor_prompt(score))
                    return True

            if _is_affirmative(text):
                if pending == "pain_zero_after_worse":
                    state.pain.usual_comparison = "worse"
                    state.step = "treatment_context"
                    self._assistant(state, "Got it. Are you using anything for the pain now?")
                    return True
                state.step = "functional_impact"
                self._assistant(state, "Thanks. How is it affecting you today?")
                return True

            if _is_negative(text):
                if pending == "pain_zero_after_worse":
                    state.pain.usual_comparison = "same"
                    state.step = "treatment_context"
                    self._assistant(state, "Okay. Are you using anything for the pain now?")
                    return True
                state.pain.score = 0 if pending == "pain_zero_after_function" else state.pain.score
                state.pain.severity = pain_severity(state.pain.score)
                state.step = "functional_impact"
                self._assistant(state, "Okay. How is it affecting you today?")
                return True

            state.pending_clarification = pending
            self._assistant(state, "Sorry, please give a pain number from 0 to 10.")
            return True

        return False


def _clean_short_answer(text: str, max_len: int = 240) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def _is_negative(text: str) -> bool:
    cleaned = text.lower().strip()
    return bool(re.fullmatch(r"(no|none|nothing|nope|not sure no|no symptoms|nothing concerning)[.! ]*", cleaned))


def _is_affirmative(text: str) -> bool:
    cleaned = text.lower().strip()
    return bool(re.fullmatch(r"(yes|yeah|yep|correct|that's right|that is right|right)[.! ]*", cleaned))


def _title_name(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip(" ,.'-"))
    if not cleaned:
        return ""
    return " ".join(part.capitalize() for part in cleaned.split())
