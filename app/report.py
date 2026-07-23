from __future__ import annotations

import json
from datetime import datetime

from app.schemas import ConversationState
from app.version import APP_VERSION, REPORT_TYPE, SCHEMA_VERSION


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
    if state.questionnaire.answers:
        survey_id = _questionnaire_value(state, "survey_id", "not provided")
        diagnosis = _questionnaire_value(state, "oa_diagnosis", "unknown")
        joints = _questionnaire_values(state, "affected_joints")
        oral_used = _questionnaire_value(state, "oral_painkiller_used", "unknown")
        medication = _questionnaire_value(state, "oral_painkiller_name", "not specified")
        channels = _questionnaire_values(state, "painkiller_channels")
        completion = state.questionnaire.completion or {}
        return (
            f"OA medication/treatment questionnaire completed for survey ID {survey_id}. "
            f"Physician-diagnosed OA: {diagnosis}. Affected joints: {_list_value(joints)}. "
            f"Oral pain medicine use: {oral_used}; medicine: {medication}. "
            f"Pain-medicine channels: {_list_value(channels)}. "
            f"Questionnaire completeness: {completion.get('complete_count', 0)}/{completion.get('required_count', 0)} required fields."
        )

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
    if state.questionnaire.answers:
        survey_id = _questionnaire_value(state, "survey_id", "未提供")
        diagnosis = _questionnaire_value(state, "oa_diagnosis", "未知")
        joints = _questionnaire_values(state, "affected_joints")
        oral_used = _questionnaire_value(state, "oral_painkiller_used", "未知")
        medication = _questionnaire_value(state, "oral_painkiller_name", "未说明")
        channels = _questionnaire_values(state, "painkiller_channels")
        completion = state.questionnaire.completion or {}
        return (
            f"已完成骨关节炎用药与治疗情况问卷，调查对象编号：{survey_id}。"
            f"医生明确诊断骨关节炎：{diagnosis}。主要受累关节：{_list_value(joints, '未说明')}。"
            f"疼痛发作时口服止痛药：{oral_used}；药品名称：{medication}。"
            f"止痛药获取渠道：{_list_value(channels, '未说明')}。"
            f"问卷完成度：{completion.get('complete_count', 0)}/{completion.get('required_count', 0)}个必填字段。"
        )

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
    payload = {
        "report_type": REPORT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "assistant_version": APP_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "session": {
            "session_id": state.session_id,
            "created_at": state.created_at,
            "language": state.language,
            "complete": state.complete,
            "conversation_type": "OA medication and treatment questionnaire voice interview",
        },
        "questionnaire_response": {
            "source_materials": state.questionnaire.source_materials,
            "answers": state.questionnaire.answers,
            "raw_answers": state.questionnaire.raw_answers,
            "skipped": state.questionnaire.skipped,
            "completion": state.questionnaire.completion,
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
            f"{APP_VERSION} follows the DOCX questionnaire content and sample phone transcript style; it is not a validated survey instrument implementation.",
        ],
        "medical_research_review": medical_research_review(state),
        "conversation_trace": conversation_trace(state),
        "ai_iteration": ai_iteration_section(state),
        "audit_metadata": audit_metadata(state),
        "model_events": state.model_events,
        "transcript": state.transcript,
    }
    return payload


def medical_research_review(state: ConversationState) -> dict[str, object]:
    missing = missing_required_fields(state)
    questionnaire_completion = state.questionnaire.completion or {}
    return {
        "clinical_completeness": {
            "identity_complete": state.identity.is_complete,
            "questionnaire_complete": bool(questionnaire_completion.get("complete")),
            "questionnaire_required_count": questionnaire_completion.get("required_count", 0),
            "questionnaire_complete_count": questionnaire_completion.get("complete_count", 0),
            "pain_scores_complete": state.pain.average_24h_score is not None and state.pain.score is not None,
            "pain_location_complete": bool(state.pain.location),
            "functional_anchor_complete": bool(state.pain.functional_impact),
            "usual_comparison_complete": state.pain.usual_comparison != "unknown",
            "treatment_context_complete": state.safety.medication_context is not None,
            "side_effect_screen_complete": state.safety.side_effect_screening_result != "unknown",
            "red_flag_screen_complete": state.complete or state.safety.red_flag_present,
        },
        "clinical_concerns": {
            "urgent_red_flag": state.safety.red_flag_present,
            "high_pain": bool(state.pain.score is not None and state.pain.score >= 7),
            "researcher_alert_required": state.safety.researcher_alert_required,
            "uncertain_red_flag": state.safety.red_flag_uncertain,
            "missing_or_suspect_fields": missing,
        },
        "research_quality": {
            "usable_for_study": not missing and not state.safety.red_flag_uncertain,
            "requires_callback": bool(
                state.safety.red_flag_present
                or state.safety.researcher_alert_required
                or state.safety.red_flag_uncertain
                or missing
            ),
            "review_status": "unreviewed",
        },
    }


def conversation_trace(state: ConversationState) -> dict[str, object]:
    metrics = quality_metrics(state)
    return {
        "turn_count": len(state.transcript),
        "turns": [
            {
                "turn_index": index + 1,
                "role": item.get("role", "unknown"),
                "text": item.get("text", ""),
            }
            for index, item in enumerate(state.transcript)
        ],
        "model_events": state.model_events,
        "quality_metrics": metrics,
    }


def ai_iteration_section(state: ConversationState) -> dict[str, object]:
    tags = failure_tags(state)
    return {
        "review_status": "unreviewed",
        "approved_for_training": False,
        "failure_tags": tags,
        "training_candidates": training_candidates(state, tags),
        "privacy": {
            "raw_audio_included": False,
            "requires_human_review_before_training": True,
            "contains_phi": True,
        },
    }


def audit_metadata(state: ConversationState) -> dict[str, object]:
    models = []
    for event in state.model_events:
        for trace in event.get("ai_traces", []) if isinstance(event, dict) else []:
            if isinstance(trace, dict) and trace.get("model"):
                models.append(str(trace.get("model")))
    return {
        "review_status": "unreviewed",
        "raw_audio_retention": "not_stored_by_default",
        "model_names_observed": sorted(set(models)),
        "model_event_count": len(state.model_events),
        "report_single_file_policy": True,
    }


def missing_required_fields(state: ConversationState) -> list[str]:
    if state.questionnaire.answers:
        completion = state.questionnaire.completion or {}
        return [str(item) for item in completion.get("missing_required_fields", [])]

    missing = []
    if not state.identity.is_complete:
        missing.append("identity")
    if state.pain.average_24h_score is None:
        missing.append("average_24h_score")
    if state.pain.score is None:
        missing.append("current_pain_score")
    if not state.pain.location:
        missing.append("pain_location")
    if not state.pain.functional_impact:
        missing.append("functional_impact")
    if state.pain.usual_comparison == "unknown":
        missing.append("usual_comparison")
    if state.safety.medication_context is None:
        missing.append("treatment_context")
    if state.safety.side_effect_screening_result == "unknown":
        missing.append("side_effect_screen")
    if not state.complete and not state.safety.red_flag_present:
        missing.append("completion_or_escalation")
    return missing


def _questionnaire_value(state: ConversationState, key: str, fallback: str) -> str:
    answer = state.questionnaire.answers.get(key)
    if isinstance(answer, dict):
        value = answer.get("value")
        if value is not None:
            return str(value)
    return fallback


def _questionnaire_values(state: ConversationState, key: str) -> list[str]:
    answer = state.questionnaire.answers.get(key)
    if isinstance(answer, dict):
        values = answer.get("values")
        if isinstance(values, list):
            return [str(value) for value in values]
        value = answer.get("value")
        if value is not None:
            return [str(value)]
    return []


def quality_metrics(state: ConversationState) -> dict[str, object]:
    clarification_count = sum(
        1
        for item in state.transcript
        if item.get("role") == "assistant" and _looks_like_clarification(item.get("text", ""))
    )
    fallback_count = 0
    extraction_count = 0
    rewrite_count = 0
    tts_failure_count = 0
    latencies = []
    stt_latencies = []
    engine_latencies = []
    for event in state.model_events:
        if not isinstance(event, dict):
            continue
        if event.get("transcript_source") == "browser_transcript":
            fallback_count += 1
        timings = event.get("timings")
        if isinstance(timings, dict):
            if isinstance(timings.get("total_ms"), int):
                latencies.append(timings["total_ms"])
            if isinstance(timings.get("stt_ms"), int):
                stt_latencies.append(timings["stt_ms"])
            if isinstance(timings.get("clinical_engine_ms"), int):
                engine_latencies.append(timings["clinical_engine_ms"])
        for trace in event.get("ai_traces", []):
            if not isinstance(trace, dict):
                continue
            if trace.get("operation") == "understand" and trace.get("used_model"):
                extraction_count += 1
            if trace.get("operation") in {"friendly_reply", "clarification_reply"} and trace.get("used_model"):
                rewrite_count += 1
        if "tts" in failure_tags_from_event(event):
            tts_failure_count += 1
    interpretation_flags = questionnaire_interpretation_flags(state)
    fuzzy_count = sum(1 for item in interpretation_flags if item.get("fuzzy"))
    low_confidence_count = sum(1 for item in interpretation_flags if float(item.get("confidence") or 0) < 0.8)
    review_count = sum(1 for item in interpretation_flags if item.get("needs_review"))
    return {
        "turn_count": len(state.transcript),
        "clarification_count": clarification_count,
        "fallback_transcript_count": fallback_count,
        "model_extraction_count": extraction_count,
        "model_rewrite_count": rewrite_count,
        "tts_failure_count": tts_failure_count,
        "avg_turn_latency_ms": int(sum(latencies) / len(latencies)) if latencies else None,
        "max_turn_latency_ms": max(latencies) if latencies else None,
        "avg_stt_latency_ms": int(sum(stt_latencies) / len(stt_latencies)) if stt_latencies else None,
        "max_stt_latency_ms": max(stt_latencies) if stt_latencies else None,
        "avg_clinical_engine_latency_ms": int(sum(engine_latencies) / len(engine_latencies)) if engine_latencies else None,
        "max_clinical_engine_latency_ms": max(engine_latencies) if engine_latencies else None,
        "fuzzy_answer_count": fuzzy_count,
        "low_confidence_answer_count": low_confidence_count,
        "interpretation_review_count": review_count,
        "questionnaire_interpretation_flags": interpretation_flags,
        "missing_required_fields": missing_required_fields(state),
    }


def questionnaire_interpretation_flags(state: ConversationState) -> list[dict[str, object]]:
    flags: list[dict[str, object]] = []
    for step, answer in state.questionnaire.answers.items():
        if not isinstance(answer, dict):
            continue
        interpretation = answer.get("interpretation")
        if not isinstance(interpretation, dict):
            continue
        confidence = float(interpretation.get("confidence") or 0)
        fuzzy = bool(interpretation.get("fuzzy"))
        needs_review = bool(interpretation.get("needs_review"))
        if not fuzzy and confidence >= 0.8 and not needs_review:
            continue
        flags.append(
            {
                "step": step,
                "confidence": confidence,
                "strategy": interpretation.get("strategy"),
                "fuzzy": fuzzy,
                "needs_review": needs_review,
                "evidence": interpretation.get("evidence"),
            }
        )
    return flags


def failure_tags(state: ConversationState) -> list[str]:
    tags = set()
    if missing_required_fields(state):
        tags.add("missing_required_field")
    interpretation_flags = questionnaire_interpretation_flags(state)
    if any(float(item.get("confidence") or 0) < 0.8 for item in interpretation_flags):
        tags.add("low_confidence_interpretation")
    if any(item.get("needs_review") for item in interpretation_flags):
        tags.add("semantic_review_required")
    if not state.model_events:
        tags.add("model_not_used")
    if state.safety.red_flag_uncertain:
        tags.add("medical_review_required")
    if state.safety.red_flag_present:
        tags.add("medical_review_required")
    for event in state.model_events:
        if not isinstance(event, dict):
            continue
        if event.get("transcript_source") == "browser_transcript":
            tags.add("browser_transcript_fallback")
        timings = event.get("timings")
        if isinstance(timings, dict) and int(timings.get("total_ms") or 0) > 2500:
            tags.add("latency_high")
        errors = event.get("errors")
        if isinstance(errors, list) and errors:
            if any("stt" in str(error).lower() for error in errors):
                tags.add("stt_misheard")
        for trace in event.get("ai_traces", []):
            if isinstance(trace, dict) and trace.get("operation") == "understand" and not trace.get("used_model"):
                tags.add("model_not_used")
            if isinstance(trace, dict) and trace.get("operation") in {"friendly_reply", "clarification_reply"} and not trace.get("used_model"):
                tags.add("reply_too_static")
    if quality_metrics(state)["clarification_count"] >= 3:
        tags.add("rulebook_overclarified")
        tags.add("patient_confused")
    return sorted(tags)


def failure_tags_from_event(event: dict[str, object]) -> list[str]:
    tags = []
    errors = event.get("errors")
    if isinstance(errors, list) and any("tts" in str(error).lower() for error in errors):
        tags.append("tts")
    return tags


def training_candidates(state: ConversationState, tags: list[str]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    if "rulebook_overclarified" in tags or "patient_confused" in tags:
        candidates.append(
            {
                "type": "response_preference",
                "requires_human_review": True,
                "reason": "Conversation required repeated clarification or showed patient confusion.",
                "context": state.transcript[-8:],
                "preferred_behavior": (
                    "Acknowledge the patient's confusion, ask the same clinical item in simpler words, "
                    "and preserve required clinical meaning."
                ),
            }
        )
    if "browser_transcript_fallback" in tags or "stt_misheard" in tags:
        candidates.append(
            {
                "type": "stt_review",
                "requires_human_review": True,
                "reason": "Audio understanding used fallback or reported STT errors.",
                "context": state.transcript[-8:],
                "preferred_behavior": "Review transcript accuracy and add corrected transcript to an approved eval set.",
            }
        )
    if "model_not_used" in tags:
        candidates.append(
            {
                "type": "system_configuration",
                "requires_human_review": False,
                "reason": "No usable model trace was observed.",
                "preferred_behavior": "Verify local Qwen service, ENABLE_LOCAL_UNDERSTANDING, and model trace logging.",
            }
        )
    if "semantic_review_required" in tags or "low_confidence_interpretation" in tags:
        candidates.append(
            {
                "type": "semantic_parser_review",
                "requires_human_review": True,
                "reason": "One or more questionnaire answers were accepted from fuzzy or low-confidence wording.",
                "context": questionnaire_interpretation_flags(state),
                "preferred_behavior": "Review whether the accepted normalized answer matches the participant's intended meaning before using it for analysis.",
            }
        )
    return candidates


def _looks_like_clarification(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "could you",
            "please",
            "sorry",
            "just checking",
            "请",
            "不好意思",
            "确认一下",
            "您的意思",
            "有没有",
        )
    )
