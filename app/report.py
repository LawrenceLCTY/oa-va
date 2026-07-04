from __future__ import annotations

import json
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
    if state.language == "zh-CN":
        return follow_up_priority_zh(state)
    if state.safety.red_flag_present:
        return "Emergency: severe red flag reported"
    if state.safety.researcher_alert_required:
        return "High priority: researcher follow-up required"
    if (state.pain.score is not None and state.pain.score >= 7) or _major_functional_decline(state):
        return "High priority: severe pain or major functional limitation reported"
    if state.safety.non_urgent_concerns or state.safety.red_flag_uncertain:
        return "High priority: concerning symptoms reported without urgent red flag confirmation"
    return "Routine: stable pain pattern and no urgent red flags reported"


def follow_up_priority_zh(state: ConversationState) -> str:
    if state.safety.red_flag_present:
        return "紧急：报告了严重危险信号"
    if state.safety.researcher_alert_required:
        return "高优先级：需要研究人员跟进"
    if (state.pain.score is not None and state.pain.score >= 7) or _major_functional_decline(state):
        return "高优先级：疼痛较重或活动明显受限"
    if state.safety.non_urgent_concerns or state.safety.red_flag_uncertain:
        return "高优先级：报告了需要医生查看的症状"
    return "常规：未报告紧急危险信号"


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
            "不能走",
            "走不了",
            "不能站",
            "站不起来",
            "需要帮忙",
            "睡不了",
        )
    )


def summary_for_doctor(state: ConversationState) -> str:
    if state.language == "zh-CN":
        return summary_for_doctor_zh(state)

    name = state.identity.name or "The patient"
    pain_score = "unknown" if state.pain.score is None else f"{state.pain.score}/10 current"
    average_score = "unknown" if state.pain.average_24h_score is None else f"{state.pain.average_24h_score}/10 average over 24h"
    location = state.pain.location or "unspecified joint area"
    comparison = state.pain.usual_comparison

    parts = [
        f"{name} completed a home osteoarthritis pain check-in with {average_score} and {pain_score} in {location}.",
    ]
    if state.pain.functional_impact:
        parts.append(f"Functional impact: {state.pain.functional_impact}.")
    if comparison != "unknown":
        parts.append(f"Pain compared with usual baseline was reported as {comparison}.")
    if state.safety.red_flag_present:
        parts.append(
            "Urgent red flag symptoms were reported and the patient was advised to seek urgent medical care."
        )
    elif state.safety.researcher_alert_required:
        parts.append("Researcher follow-up was flagged based on side-effect detail or healthcare use.")
    elif state.safety.non_urgent_concerns:
        parts.append("Non-urgent side effects or symptoms were reported for clinician review.")
    else:
        parts.append("No urgent red flags were reported during this check-in.")

    return " ".join(parts)


def summary_for_doctor_zh(state: ConversationState) -> str:
    name = state.identity.name or "患者"
    pain_score = "未知" if state.pain.score is None else f"{state.pain.score}/10（当前）"
    average_score = "未知" if state.pain.average_24h_score is None else f"{state.pain.average_24h_score}/10（过去24小时平均）"
    location = state.pain.location or "未说明部位"
    comparison_map = {"better": "较平时减轻", "same": "和平时差不多", "worse": "较平时加重", "unknown": "未知"}
    comparison = comparison_map.get(state.pain.usual_comparison, state.pain.usual_comparison)

    parts = [f"{name}完成了一次居家骨关节炎疼痛随访，报告{average_score}，{pain_score}，部位为{location}。"]
    if state.pain.functional_impact:
        parts.append(f"功能影响：{state.pain.functional_impact}。")
    if comparison != "未知":
        parts.append(f"与平时相比：{comparison}。")
    if state.safety.red_flag_present:
        parts.append("患者报告了紧急危险信号，已建议尽快就医。")
    elif state.safety.researcher_alert_required:
        parts.append("根据副作用细节或就医情况，已标记需要研究人员跟进。")
    elif state.safety.non_urgent_concerns:
        parts.append("患者报告了非紧急不适或副作用，建议医生查看。")
    else:
        parts.append("本次随访未报告紧急危险信号。")
    return "".join(parts)


def generate_report(state: ConversationState) -> str:
    return json.dumps(report_payload(state), ensure_ascii=False, indent=2)


def generate_report_zh(state: ConversationState) -> str:
    return generate_report(state)


def report_payload(state: ConversationState) -> dict[str, object]:
    red_flag_status = "yes" if state.safety.red_flag_present else "uncertain" if state.safety.red_flag_uncertain else "no"
    return {
        "report_type": "oa_home_pain_check_in",
        "schema_version": "1.0",
        "assistant_version": "v0.7",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "session": {
            "session_id": state.session_id,
            "created_at": state.created_at,
            "language": state.language,
            "complete": state.complete,
            "conversation_type": "Home monitoring OA pain check-in",
        },
        "patient_identity": {
            "name": state.identity.name,
            "mobile_number": state.identity.mobile_number,
            "age": state.identity.age,
            "status": state.identity.status,
        },
        "readiness": {
            "hearing_clear": state.readiness.get("hearing_clear", "unknown"),
            "suitable_time": state.readiness.get("suitable_time", "unknown"),
            "permission_to_continue": state.readiness.get("permission_to_continue", "unknown"),
            "respondent_source": state.respondent_source,
        },
        "pain_assessment": {
            "scale": "0-10 VAS/NRS with optional binary scenario anchoring",
            "average_24h_score": state.pain.average_24h_score,
            "average_24h_severity": state.pain.average_24h_severity,
            "average_24h_score_confirmed": state.pain.average_24h_score_confirmed,
            "average_24h_vas_trace": state.pain.average_24h_vas_trace,
            "current_score": state.pain.score,
            "current_severity": state.pain.severity,
            "current_score_confirmed": state.pain.current_score_confirmed,
            "current_vas_trace": state.pain.current_vas_trace,
            "location": state.pain.location,
            "functional_impact": state.pain.functional_impact,
            "usual_comparison": state.pain.usual_comparison,
            "patient_words": state.pain.patient_words,
        },
        "safety_assessment": {
            "side_effect_screening_result": state.safety.side_effect_screening_result,
            "reported_symptoms": state.safety.reported_symptoms,
            "symptom_start_time": state.safety.symptom_start_time,
            "symptom_status": state.safety.symptom_status,
            "symptom_severity": state.safety.symptom_severity,
            "medication_or_treatment_context": state.safety.medication_context,
            "medication_reduced_paused_or_stopped": state.safety.medication_changed,
            "doctor_contacted": state.safety.doctor_contacted,
            "emergency_visit_or_hospitalization": state.safety.emergency_visit_or_hospitalization,
            "non_urgent_concerns": state.safety.non_urgent_concerns,
            "researcher_alert_required": state.safety.researcher_alert_required,
            "red_flag_status": red_flag_status,
            "red_flag_present": state.safety.red_flag_present,
            "red_flag_uncertain": state.safety.red_flag_uncertain,
            "red_flag_symptoms": state.safety.red_flag_symptoms,
            "action_advised": state.safety.action_advised,
        },
        "doctor_summary": summary_for_doctor(state),
        "suggested_follow_up_priority": follow_up_priority(state),
        "limitations": [
            "Research prototype; not approved for clinical use.",
            "Voice self-report only.",
            "No physical exam performed.",
            "No diagnosis or medication adjustment made.",
        ],
        "model_events": state.model_events,
        "transcript": state.transcript,
    }
