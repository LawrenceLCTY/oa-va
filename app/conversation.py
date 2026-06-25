from __future__ import annotations

import os
import re
from app.clinical_rules import (
    detect_symptoms,
)
from app.i18n import normalize_language, t
from app.llm import LocalLLM
from app.openai_client import OpenAIClient, UnderstandingResult
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
    def __init__(self, llm: LocalLLM | None = None, ai: OpenAIClient | None = None) -> None:
        self.llm = llm or LocalLLM()
        self.ai = ai or OpenAIClient()

    def start(self, language: str = "en") -> ConversationState:
        state = ConversationState(language=normalize_language(language))
        if _strict_readiness_enabled():
            state.step = "readiness_hearing"
            self._assistant(state, t(state.language, "intro"))
            self._assistant(state, t(state.language, "hearing_check"))
            return state

        state.step = "identity"
        state.readiness["hearing_clear"] = "assumed"
        state.readiness["suitable_time"] = "assumed"
        state.readiness["permission_to_continue"] = "assumed"
        self._assistant(state, t(state.language, "natural_intro"))
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

        understood = self.ai.understand(state.step, state.language, user_text)
        if understood:
            self._merge_understanding_safety(state, user_text, understood)
            self._apply_understood_slots(state, understood, user_text)
            if state.safety.red_flag_present and not state.escalation_message_spoken:
                state.safety.action_advised = t(state.language, "urgent_action")
                state.escalation_message_spoken = True
                self._assistant(state, t(state.language, "escalation"))
                return state

        if state.pending_clarification:
            if self._handle_pending_clarification(state, user_text, understood):
                return state

        if state.step == "readiness_hearing":
            self._handle_readiness_hearing(state, user_text, understood)
        elif state.step == "readiness_time":
            self._handle_readiness_time(state, user_text, understood)
        elif state.step == "permission":
            self._handle_permission(state, user_text, understood)
        elif state.step == "identity":
            self._handle_identity(state, user_text, understood)
        elif state.step == "respondent_source":
            self._handle_respondent_source(state, user_text, understood)
        elif state.step == "average_pain_score":
            self._handle_average_pain_score(state, user_text, understood)
        elif state.step == "current_pain_score":
            self._handle_current_pain_score(state, user_text, understood)
        elif state.step == "pain_location":
            self._handle_pain_location(state, user_text, understood)
        elif state.step == "functional_impact":
            self._handle_functional_impact(state, user_text, understood)
        elif state.step == "usual_comparison":
            self._handle_usual_comparison(state, user_text, understood)
        elif state.step == "treatment_context":
            self._handle_treatment_context(state, user_text, understood)
        elif state.step == "side_effects":
            self._handle_side_effects(state, user_text, understood)
        elif state.step == "side_effect_description":
            self._handle_side_effect_description(state, user_text, understood)
        elif state.step == "side_effect_start":
            self._handle_side_effect_start(state, user_text, understood)
        elif state.step == "side_effect_status":
            self._handle_side_effect_status(state, user_text, understood)
        elif state.step == "side_effect_severity":
            self._handle_side_effect_severity(state, user_text, understood)
        elif state.step == "medication_changed":
            self._handle_medication_changed(state, user_text, understood)
        elif state.step == "doctor_contacted":
            self._handle_doctor_contacted(state, user_text, understood)
        elif state.step == "emergency_visit":
            self._handle_emergency_visit(state, user_text, understood)
        elif state.step == "red_flags":
            self._handle_red_flags(state, user_text, understood)
        elif state.step == "closing":
            self._complete(state)
        else:
            self._assistant(state, t(state.language, "continue"))

        return state

    def _handle_readiness_hearing(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        answer = _understood_yes_no(understood) or classify_yes_no_unsure(text)
        if answer == "unknown":
            self._clarify(state, text, t(state.language, "hearing_check"), "unclear_yes_no")
            return
        state.readiness["hearing_clear"] = answer
        state.step = "readiness_time"
        self._assistant(state, t(state.language, "time_check"))

    def _handle_readiness_time(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        answer = _understood_yes_no(understood) or classify_yes_no_unsure(text)
        if answer == "unknown":
            self._clarify(state, text, t(state.language, "time_check"), "unclear_yes_no")
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

    def _handle_permission(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        answer = _understood_yes_no(understood) or classify_yes_no_unsure(text)
        if answer == "unknown":
            self._clarify(state, text, t(state.language, "permission_check"), "unclear_yes_no")
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

    def _handle_identity(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        self._apply_understood_identity(state, understood)
        self._extract_identity(state, text)

        missing = []
        if not state.identity.name:
            missing.append(t(state.language, "identity_name"))
        if not state.identity.mobile_number:
            missing.append(t(state.language, "identity_mobile"))
        if state.identity.age is None:
            missing.append(t(state.language, "identity_age"))

        if missing:
            prompt = t(state.language, "missing_identity", missing=_join_missing(missing, state.language))
            self._clarify(state, text, prompt, "missing_identity")
            return

        state.step = "respondent_source"
        self._advance_to_next_missing(state, after="identity")

    def _handle_respondent_source(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        state.respondent_source = _understood_choice(
            understood,
            {"participant_independently", "participant_with_caregiver_assistance", "caregiver_proxy", "unknown"},
        ) or classify_respondent_source(text)
        state.step = "average_pain_score"
        self._advance_to_next_missing(state, after="respondent_source")

    def _handle_average_pain_score(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        score = _understood_pain_score(understood)
        validation = validate_pain_score_answer(text)
        if score is None and not validation.accepted:
            prompt = validation.prompt(state.language) or t(state.language, "invalid_pain_score")
            self._clarify(state, text, prompt, validation.reason)
            return

        score = int(score if score is not None else validation.value)
        state.pain.average_24h_score = score
        state.pain.average_24h_severity = pain_severity(score)
        state.pain.average_24h_score_confirmed = True
        state.pain.patient_words.append(f"24h average pain: {text}")
        state.step = "current_pain_score"
        self._advance_to_next_missing(state, after="average_pain_score")

    def _handle_current_pain_score(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        score = _understood_pain_score(understood)
        validation = validate_pain_score_answer(text)
        if score is None and not validation.accepted:
            prompt = validation.prompt(state.language) or t(state.language, "invalid_pain_score")
            self._clarify(state, text, prompt, validation.reason)
            return

        score = int(score if score is not None else validation.value)
        state.pain.score = score
        state.pain.severity = pain_severity(score)
        state.pain.current_score_confirmed = True
        state.pain.patient_words.append(f"current pain: {text}")
        state.step = "pain_location"
        self._advance_to_next_missing(state, after="current_pain_score")

    def _handle_pain_location(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        validation = validate_pain_location_answer(text)
        value = _understood_text(understood)
        if value is None and not validation.accepted:
            prompt = validation.prompt(state.language) or t(state.language, "pain_location")
            self._clarify(state, text, prompt, validation.reason)
            return

        state.pain.location = _clean_short_answer(value or text)
        state.pain.patient_words.append(text)
        state.step = "functional_impact"
        self._advance_to_next_missing(state, after="pain_location")

    def _handle_functional_impact(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        validation = validate_functional_impact_answer(state, text)
        value = _understood_text(understood)
        if value is None and not validation.accepted:
            if validation.reason == "pain_zero_conflicts_with_functional_impact":
                state.pending_clarification = "pain_zero_after_function"
            elif validation.reason == "severe_score_conflicts_with_no_impact":
                state.pending_clarification = "severe_score_no_impact"
            prompt = validation.prompt(state.language) or t(state.language, "functional_impact")
            self._clarify(state, text, prompt, validation.reason)
            return

        state.pain.functional_impact = _clean_short_answer(value or text, max_len=400)
        state.pain.patient_words.append(text)
        state.step = "usual_comparison"
        self._advance_to_next_missing(state, after="functional_impact")

    def _handle_usual_comparison(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        validation = validate_comparison_answer(state, text)
        comparison = _understood_choice(understood, {"better", "worse", "same", "unknown"})
        if comparison is None and not validation.accepted:
            if validation.reason == "pain_zero_conflicts_with_worse_comparison":
                state.pending_clarification = "pain_zero_after_worse"
            prompt = validation.prompt(state.language) or t(state.language, "comparison")
            self._clarify(state, text, prompt, validation.reason)
            return

        state.pain.usual_comparison = str(comparison or validation.value)
        state.pain.patient_words.append(text)
        state.step = "treatment_context"
        self._advance_to_next_missing(state, after="usual_comparison")

    def _handle_treatment_context(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        validation = validate_treatment_answer(text)
        answer = _understood_yes_no(understood)
        value = _understood_text(understood)
        if answer is None and value is None and not validation.accepted:
            prompt = validation.prompt(state.language) or t(state.language, "treatment")
            self._clarify(state, text, prompt, validation.reason)
            return

        if answer == "no" or _is_negative(text):
            state.safety.medication_context = t(state.language, "none_reported")
        else:
            state.safety.medication_context = _clean_short_answer(value or text, max_len=400)
        state.step = "side_effects"
        self._advance_to_next_missing(state, after="treatment_context")

    def _handle_side_effects(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        validation = validate_side_effect_answer(text)
        if validation.action == ValidationAction.ESCALATE:
            state.safety.action_advised = t(state.language, "urgent_action")
            state.escalation_message_spoken = True
            self._assistant(state, t(state.language, "escalation"))
            return
        result = (
            _slot_choice(understood, "side_effect_screening_result", {"yes", "no", "uncertain"})
            or _understood_yes_no(understood)
            or classify_yes_no_unsure(text)
        )
        if result == "unknown" and not validation.accepted:
            prompt = validation.prompt(state.language) or t(state.language, "side_effects")
            self._clarify(state, text, prompt, validation.reason)
            return

        state.safety.side_effect_screening_result = result
        if result == "unknown" and validation.accepted:
            state.safety.side_effect_screening_result = "yes"
            result = "yes"
        description = _slot_text((understood.slots or {}).get("side_effect_description")) if understood else None
        if description and description not in state.safety.reported_symptoms:
            state.safety.reported_symptoms.append(_clean_short_answer(description, max_len=400))
        elif result in {"yes", "uncertain"} and not _is_short_confirmation(text):
            state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))
        elif result != "no" and not _is_negative(text) and not _is_short_confirmation(text):
            state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))

        if state.safety.red_flag_present and not state.escalation_message_spoken:
            state.safety.action_advised = t(state.language, "urgent_action")
            state.escalation_message_spoken = True
            self._assistant(state, t(state.language, "escalation"))
            return

        state.step = "red_flags"
        self._advance_to_next_missing(state, after="side_effects")

    def _handle_side_effect_description(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        description = _slot_text((understood.slots or {}).get("side_effect_description")) if understood else None
        if description:
            state.safety.reported_symptoms.append(_clean_short_answer(description, max_len=400))
        elif not _is_negative(text):
            state.safety.reported_symptoms.append(_clean_short_answer(text, max_len=400))
        state.step = "side_effect_start"
        self._advance_to_next_missing(state, after="side_effect_description")

    def _handle_side_effect_start(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        start_time = _slot_text((understood.slots or {}).get("symptom_start_time")) if understood else None
        state.safety.symptom_start_time = _clean_short_answer(start_time or text, max_len=160)
        state.step = "side_effect_status"
        self._advance_to_next_missing(state, after="side_effect_start")

    def _handle_side_effect_status(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        state.safety.symptom_status = (
            _slot_choice(understood, "symptom_status", {"ongoing", "resolved", "unknown"})
            or _understood_choice(understood, {"ongoing", "resolved", "unknown"})
            or classify_symptom_status(text)
        )
        state.step = "side_effect_severity"
        self._advance_to_next_missing(state, after="side_effect_status")

    def _handle_side_effect_severity(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        state.safety.symptom_severity = (
            _slot_choice(understood, "symptom_severity", {"mild", "moderate", "severe", "unknown"})
            or _understood_choice(understood, {"mild", "moderate", "severe", "unknown"})
            or classify_symptom_severity(text)
        )
        if state.safety.symptom_severity == "severe":
            state.safety.researcher_alert_required = True
        state.step = "medication_changed"
        self._advance_to_next_missing(state, after="side_effect_severity")

    def _handle_medication_changed(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        state.safety.medication_changed = (
            _slot_choice(understood, "medication_changed", {"yes", "no", "uncertain"})
            or _understood_yes_no(understood)
            or classify_medication_changed(text)
        )
        if state.safety.medication_changed == "yes":
            state.safety.researcher_alert_required = True
        state.step = "doctor_contacted"
        self._advance_to_next_missing(state, after="medication_changed")

    def _handle_doctor_contacted(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        state.safety.doctor_contacted = (
            _slot_choice(understood, "doctor_contacted", {"yes", "no", "uncertain"})
            or _understood_yes_no(understood)
            or classify_yes_no_unsure(text)
        )
        state.step = "emergency_visit"
        self._advance_to_next_missing(state, after="doctor_contacted")

    def _handle_emergency_visit(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        state.safety.emergency_visit_or_hospitalization = (
            _slot_choice(understood, "emergency_visit_or_hospitalization", {"yes", "no", "uncertain"})
            or _understood_yes_no(understood)
            or classify_emergency_visit(text)
        )
        if state.safety.emergency_visit_or_hospitalization == "yes":
            state.safety.researcher_alert_required = True
        state.step = "red_flags"
        self._advance_to_next_missing(state, after="emergency_visit")

    def _handle_red_flags(self, state: ConversationState, text: str, understood: UnderstandingResult | None) -> None:
        validation = validate_red_flags_answer(text)
        if validation.action == ValidationAction.ESCALATE:
            state.safety.action_advised = t(state.language, "urgent_action")
            state.escalation_message_spoken = True
            self._assistant(state, t(state.language, "escalation"))
            return
        answer = _understood_yes_no(understood)
        if answer is None and not validation.accepted:
            prompt = validation.prompt(state.language) or t(state.language, "red_flags")
            self._clarify(state, text, prompt, validation.reason)
            return

        if answer != "no" and not _is_negative(text):
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

    def _merge_understanding_safety(self, state: ConversationState, text: str, understood: UnderstandingResult) -> None:
        if understood.red_flags:
            self._merge_safety_detection(
                state,
                text,
                {
                    "red_flags": understood.red_flags,
                    "non_urgent": understood.non_urgent_concerns or [],
                    "uncertain": False,
                },
            )
        elif understood.non_urgent_concerns:
            self._merge_safety_detection(
                state,
                text,
                {
                    "red_flags": [],
                    "non_urgent": understood.non_urgent_concerns,
                    "uncertain": False,
                },
            )

    def _apply_understood_slots(self, state: ConversationState, understood: UnderstandingResult, text: str) -> None:
        if understood.confidence < 0.55:
            return
        self._apply_understood_identity(state, understood)
        slots = understood.slots or {}
        respondent_source = slots.get("respondent_source")
        if isinstance(respondent_source, str) and respondent_source in {
            "participant_independently",
            "participant_with_caregiver_assistance",
            "caregiver_proxy",
        }:
            state.respondent_source = respondent_source

        average_score = slots.get("average_24h_score")
        if isinstance(average_score, int) and 0 <= average_score <= 10 and state.pain.average_24h_score is None:
            state.pain.average_24h_score = average_score
            state.pain.average_24h_severity = pain_severity(average_score)
            state.pain.average_24h_score_confirmed = True
            state.pain.patient_words.append(f"24h average pain: {text}")

        current_score = slots.get("current_pain_score")
        if isinstance(current_score, int) and 0 <= current_score <= 10 and state.pain.score is None:
            state.pain.score = current_score
            state.pain.severity = pain_severity(current_score)
            state.pain.current_score_confirmed = True
            state.pain.patient_words.append(f"current pain: {text}")

        location = _slot_text(slots.get("pain_location"))
        if location and not state.pain.location:
            state.pain.location = _clean_short_answer(location)
            state.pain.patient_words.append(text)

        impact = _slot_text(slots.get("functional_impact"))
        if impact and not state.pain.functional_impact:
            state.pain.functional_impact = _clean_short_answer(impact, max_len=400)
            state.pain.patient_words.append(text)

        comparison = slots.get("usual_comparison")
        if isinstance(comparison, str) and comparison in {"better", "worse", "same"}:
            state.pain.usual_comparison = comparison

        treatment = _slot_text(slots.get("treatment_context"))
        if treatment and not state.safety.medication_context:
            state.safety.medication_context = _clean_short_answer(treatment, max_len=400)

        side_effects = slots.get("side_effect_screening_result")
        if isinstance(side_effects, str) and side_effects in {"yes", "no", "uncertain"}:
            state.safety.side_effect_screening_result = side_effects

        side_effect_description = _slot_text(slots.get("side_effect_description"))
        if side_effect_description and side_effect_description not in state.safety.reported_symptoms:
            state.safety.reported_symptoms.append(_clean_short_answer(side_effect_description, max_len=400))

        symptom_start = _slot_text(slots.get("symptom_start_time"))
        if symptom_start and not state.safety.symptom_start_time:
            state.safety.symptom_start_time = _clean_short_answer(symptom_start, max_len=160)

        symptom_status = slots.get("symptom_status")
        if isinstance(symptom_status, str) and symptom_status in {"ongoing", "resolved"}:
            state.safety.symptom_status = symptom_status

        symptom_severity = slots.get("symptom_severity")
        if isinstance(symptom_severity, str) and symptom_severity in {"mild", "moderate", "severe"}:
            state.safety.symptom_severity = symptom_severity
            if symptom_severity == "severe":
                state.safety.researcher_alert_required = True

        medication_changed = slots.get("medication_changed")
        if isinstance(medication_changed, str) and medication_changed in {"yes", "no", "uncertain"}:
            state.safety.medication_changed = medication_changed
            if medication_changed == "yes":
                state.safety.researcher_alert_required = True

        doctor_contacted = slots.get("doctor_contacted")
        if isinstance(doctor_contacted, str) and doctor_contacted in {"yes", "no", "uncertain"}:
            state.safety.doctor_contacted = doctor_contacted

        emergency_visit = slots.get("emergency_visit_or_hospitalization")
        if isinstance(emergency_visit, str) and emergency_visit in {"yes", "no", "uncertain"}:
            state.safety.emergency_visit_or_hospitalization = emergency_visit
            if emergency_visit == "yes":
                state.safety.researcher_alert_required = True

    def _advance_to_next_missing(self, state: ConversationState, after: str) -> None:
        ordered_steps = (
            "identity",
            "respondent_source",
            "average_pain_score",
            "current_pain_score",
            "pain_location",
            "functional_impact",
            "usual_comparison",
            "treatment_context",
            "side_effects",
            "side_effect_description",
            "side_effect_start",
            "side_effect_status",
            "side_effect_severity",
            "medication_changed",
            "doctor_contacted",
            "emergency_visit",
            "red_flags",
        )
        try:
            start = ordered_steps.index(after) + 1
        except ValueError:
            start = 0
        for step in ordered_steps[start:]:
            if self._step_missing(state, step):
                state.step = step
                self._ask_for_step(state, step)
                return
        self._complete(state)

    def _step_missing(self, state: ConversationState, step: str) -> bool:
        if step == "identity":
            return not state.identity.is_complete
        if step == "respondent_source":
            return state.respondent_source == "unknown"
        if step == "average_pain_score":
            return state.pain.average_24h_score is None
        if step == "current_pain_score":
            return state.pain.score is None
        if step == "pain_location":
            return not state.pain.location
        if step == "functional_impact":
            return not state.pain.functional_impact
        if step == "usual_comparison":
            return state.pain.usual_comparison == "unknown"
        if step == "treatment_context":
            return state.safety.medication_context is None
        if step == "side_effects":
            return state.safety.side_effect_screening_result == "unknown"
        if step == "side_effect_description":
            return state.safety.side_effect_screening_result in {"yes", "uncertain"} and not state.safety.reported_symptoms
        if step == "side_effect_start":
            return state.safety.side_effect_screening_result in {"yes", "uncertain"} and not state.safety.symptom_start_time
        if step == "side_effect_status":
            return state.safety.side_effect_screening_result in {"yes", "uncertain"} and state.safety.symptom_status == "unknown"
        if step == "side_effect_severity":
            return state.safety.side_effect_screening_result in {"yes", "uncertain"} and state.safety.symptom_severity == "unknown"
        if step == "medication_changed":
            return state.safety.side_effect_screening_result in {"yes", "uncertain"} and state.safety.medication_changed == "unknown"
        if step == "doctor_contacted":
            return state.safety.side_effect_screening_result in {"yes", "uncertain"} and state.safety.doctor_contacted == "unknown"
        if step == "emergency_visit":
            return (
                state.safety.side_effect_screening_result in {"yes", "uncertain"}
                and state.safety.emergency_visit_or_hospitalization == "unknown"
            )
        if step == "red_flags":
            return not state.complete
        return False

    def _ask_for_step(self, state: ConversationState, step: str) -> None:
        if step == "respondent_source":
            self._assistant(state, t(state.language, "respondent_source"))
        elif step == "average_pain_score":
            self._assistant(state, t(state.language, "average_pain_prompt"))
        elif step == "current_pain_score":
            self._assistant(state, t(state.language, "current_pain_prompt"))
        elif step == "pain_location":
            self._assistant(state, t(state.language, "pain_location"))
        elif step == "functional_impact":
            self._assistant(state, functional_anchor_prompt(state.pain.score, state.language))
        elif step == "usual_comparison":
            self._assistant(state, t(state.language, "comparison"))
        elif step == "treatment_context":
            self._assistant(state, t(state.language, "treatment"))
        elif step == "side_effects":
            self._assistant(state, t(state.language, "side_effects"))
        elif step == "side_effect_description":
            self._assistant(state, t(state.language, "side_effect_description"))
        elif step == "side_effect_start":
            self._assistant(state, t(state.language, "side_effect_start"))
        elif step == "side_effect_status":
            self._assistant(state, t(state.language, "side_effect_status"))
        elif step == "side_effect_severity":
            self._assistant(state, t(state.language, "side_effect_severity"))
        elif step == "medication_changed":
            self._assistant(state, t(state.language, "medication_changed"))
        elif step == "doctor_contacted":
            self._assistant(state, t(state.language, "doctor_contacted"))
        elif step == "emergency_visit":
            self._assistant(state, t(state.language, "emergency_visit"))
        elif step == "red_flags":
            self._assistant(state, t(state.language, "red_flags"))
        else:
            self._assistant(state, t(state.language, "continue"))

    def _apply_understood_identity(self, state: ConversationState, understood: UnderstandingResult | None) -> None:
        if not understood or not understood.identity or understood.confidence < 0.55:
            return
        identity = understood.identity
        name = identity.get("name")
        mobile = identity.get("mobile_number")
        age = identity.get("age")
        if isinstance(name, str) and name.strip():
            state.identity.name = name.strip()
        if isinstance(mobile, str) and mobile.strip():
            state.identity.mobile_number = mobile.strip()
        if isinstance(age, int) and 1 <= age <= 120:
            state.identity.age = age

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

        phone_match = re.search(r"(?:\+?\d(?:[\d().-]|\s(?!\d{1,3}\s*岁)){6,}\d)", cleaned)
        if phone_match:
            digits = re.sub(r"\D", "", phone_match.group(0))
            if 7 <= len(digits) <= 15:
                state.identity.mobile_number = digits

        name = self._extract_name(cleaned)
        if name:
            state.identity.name = name

    def _extract_name(self, text: str) -> str | None:
        zh_patterns = (
            r"(?:姓名|姓名是|名字|名字是)\s*[:：]?\s*([\u4e00-\u9fff]{2,8})",
            r"(?:我叫|我的名字是|姓名是|名字是)\s*([\u4e00-\u9fff]{2,8})",
            r"(?:我是)\s*([\u4e00-\u9fff]{2,8})",
        )
        for pattern in zh_patterns:
            match = re.search(pattern, text)
            if match:
                candidate = re.split(r"(?:手机|手机号|电话|号码|年龄|岁)", match.group(1))[0]
                if candidate:
                    return candidate

        zh_fallback = re.sub(r"(?:\+?\d(?:[\d\s().-]){6,}\d)", " ", text)
        zh_fallback = re.sub(r"\d{1,3}\s*岁|\b\d{1,3}\b", " ", zh_fallback)
        zh_fallback = re.sub(r"(?:姓名|名字|我叫|我是|手机号|手机|电话|号码|年龄|是|我的)", " ", zh_fallback)
        zh_candidates = re.findall(r"[\u4e00-\u9fff]{2,4}", zh_fallback)
        blocked_zh = {"手机号", "手机", "电话", "号码", "年龄", "姓名", "名字"}
        for candidate in zh_candidates:
            if candidate not in blocked_zh:
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
        friendly = self.ai.friendly_reply(state.language, message, state.transcript)
        if friendly:
            state.assistant(friendly)
            return
        state.assistant(self.llm.polish_assistant_reply(message))

    def _clarify(self, state: ConversationState, patient_text: str, clinical_prompt: str, reason: str) -> None:
        prompt = None
        clarification_reply = getattr(self.ai, "clarification_reply", None)
        if callable(clarification_reply):
            prompt = clarification_reply(
                state.language,
                state.step,
                patient_text,
                clinical_prompt,
                reason,
                state.transcript,
            )
        if prompt:
            state.assistant(prompt)
            return
        self._assistant(state, clinical_prompt)

    def _handle_pending_clarification(
        self,
        state: ConversationState,
        text: str,
        understood: UnderstandingResult | None,
    ) -> bool:
        pending = state.pending_clarification
        state.pending_clarification = None

        if pending in {"pain_zero_after_function", "pain_zero_after_worse", "severe_score_no_impact"}:
            score = _understood_pain_score(understood)
            score_validation = validate_pain_score_answer(text)
            if score is not None or score_validation.accepted:
                score = int(score if score is not None else score_validation.value)
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
            self._clarify(state, text, t(state.language, "clarify_score"), pending)
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


def _is_short_confirmation(text: str) -> bool:
    cleaned = text.lower().strip("。.!? ")
    compact = re.sub(r"\s+", "", cleaned)
    if compact in {"有", "是", "对", "对的", "是的", "没有", "没", "无", "不确定"}:
        return True
    return bool(re.fullmatch(r"(yes|yeah|yep|no|nope|none|not sure|unsure)", cleaned))


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


def _strict_readiness_enabled() -> bool:
    return os.getenv("STRICT_READINESS_FLOW", "").strip().lower() in {"1", "true", "yes"}


def _understood_yes_no(understood: UnderstandingResult | None) -> str | None:
    return _understood_choice(understood, {"yes", "no", "uncertain"})


def _understood_choice(understood: UnderstandingResult | None, choices: set[str]) -> str | None:
    if not understood or not understood.accepted or understood.confidence < 0.55:
        return None
    candidates = [understood.value, understood.answer_type]
    for candidate in candidates:
        text = str(candidate).strip() if candidate is not None else ""
        if text in choices:
            return text
    return None


def _understood_pain_score(understood: UnderstandingResult | None) -> int | None:
    if not understood or not understood.accepted or understood.confidence < 0.55:
        return None
    value = understood.value
    if isinstance(value, int) and 0 <= value <= 10:
        return value
    if isinstance(value, str) and value.isdigit():
        score = int(value)
        if 0 <= score <= 10:
            return score
    return None


def _understood_text(understood: UnderstandingResult | None) -> str | None:
    if not understood or not understood.accepted or understood.confidence < 0.55:
        return None
    return understood.text_value or (str(understood.value).strip() if understood.value is not None else None)


def _slot_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text and text.lower() != "unknown" else None


def _slot_choice(understood: UnderstandingResult | None, key: str, choices: set[str]) -> str | None:
    if not understood or not understood.slots or understood.confidence < 0.55:
        return None
    value = understood.slots.get(key)
    text = str(value).strip() if value is not None else ""
    return text if text in choices else None
