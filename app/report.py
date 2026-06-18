from __future__ import annotations

from datetime import datetime

from app.schemas import ConversationState


def _line_value(value: object | None, fallback: str = "not provided") -> str:
    if value is None:
        return fallback
    if isinstance(value, str) and not value.strip():
        return fallback
    return str(value)


def _list_value(values: list[str], fallback: str = "none reported") -> str:
    if not values:
        return fallback
    return "; ".join(values)


def follow_up_priority(state: ConversationState) -> str:
    if state.safety.red_flag_present:
        return "Emergency: severe red flag reported"
    if (state.pain.score is not None and state.pain.score >= 7) or _major_functional_decline(state):
        return "High priority: severe pain or major functional limitation reported"
    if state.safety.non_urgent_concerns or state.safety.red_flag_uncertain:
        return "High priority: concerning symptoms reported without urgent red flag confirmation"
    return "Routine: stable pain pattern and no urgent red flags reported"


def _major_functional_decline(state: ConversationState) -> bool:
    text = (state.pain.functional_impact or "").lower()
    return any(
        phrase in text
        for phrase in (
            "cannot walk",
            "can't walk",
            "unable to walk",
            "cannot stand",
            "can't stand",
            "unable to stand",
            "bed",
            "need help",
            "needs help",
            "can't sleep",
            "cannot sleep",
        )
    )


def summary_for_doctor(state: ConversationState) -> str:
    name = state.identity.name or "The patient"
    pain_score = "unknown" if state.pain.score is None else f"{state.pain.score}/10"
    location = state.pain.location or "unspecified joint area"
    comparison = state.pain.usual_comparison

    parts = [
        f"{name} completed a home osteoarthritis pain check-in with a reported pain score of {pain_score} in {location}.",
    ]
    if state.pain.functional_impact:
        parts.append(f"Functional impact: {state.pain.functional_impact}.")
    if comparison != "unknown":
        parts.append(f"Pain compared with usual baseline was reported as {comparison}.")
    if state.safety.red_flag_present:
        parts.append(
            "Urgent red flag symptoms were reported and the patient was advised to seek urgent medical care."
        )
    elif state.safety.non_urgent_concerns:
        parts.append("Non-urgent side effects or symptoms were reported for clinician review.")
    else:
        parts.append("No urgent red flags were reported during this check-in.")

    return " ".join(parts)


def generate_report(state: ConversationState) -> str:
    red_flag_status = "yes" if state.safety.red_flag_present else "uncertain" if state.safety.red_flag_uncertain else "no"
    now = datetime.now().isoformat(timespec="seconds")

    return "\n".join(
        [
            "OA Home Pain Check-in Report",
            "",
            "Patient Identity",
            f"- Name: {_line_value(state.identity.name)}",
            f"- Mobile number: {_line_value(state.identity.mobile_number)}",
            f"- Age: {_line_value(state.identity.age)}",
            f"- Identity status: {state.identity.status}",
            "",
            "Call Metadata",
            f"- Date/time: {now}",
            "- Conversation type: Home monitoring OA pain check-in",
            "- Assistant version: v0.1",
            f"- Session ID: {state.session_id}",
            "",
            "Pain Assessment",
            f"- Pain score: {_line_value(state.pain.score, 'unknown')}/10",
            "- Scale used: 0-10 Numeric Rating Scale with functional anchoring",
            f"- Pain severity band: {state.pain.severity}",
            f"- Pain location(s): {_line_value(state.pain.location)}",
            f"- Functional impact: {_line_value(state.pain.functional_impact)}",
            f"- Compared with usual pain: {state.pain.usual_comparison}",
            f"- Patient's own words: {_list_value(state.pain.patient_words, 'not captured')}",
            "",
            "Side Effects / Symptoms Reported",
            f"- Reported symptoms: {_list_value(state.safety.reported_symptoms)}",
            f"- Medication or treatment context: {_line_value(state.safety.medication_context)}",
            f"- Non-urgent concerns: {_list_value(state.safety.non_urgent_concerns)}",
            "",
            "Urgent Red Flags",
            f"- Red flag present: {red_flag_status}",
            f"- Red flag symptom(s): {_list_value(state.safety.red_flag_symptoms)}",
            f"- Action advised: {state.safety.action_advised}",
            "",
            "Summary for Doctor",
            f"- {summary_for_doctor(state)}",
            "",
            "Suggested Follow-up Priority",
            f"- {follow_up_priority(state)}",
            "",
            "Limitations",
            "- Voice self-report only.",
            "- No physical exam performed.",
            "- No diagnosis or medication adjustment made.",
        ]
    )
