from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from app.pain_scale import parse_pain_score
from app.validators import classify_yes_no_unsure


@dataclass(frozen=True)
class QuestionnaireStep:
    key: str
    kind: str
    prompt_zh: str
    prompt_en: str
    clarification_zh: str
    clarification_en: str


SOURCE_MATERIALS = {
    "questionnaire_docx": "data/OA问卷-房山-简化-v2.docx",
    "sample_audio": "data/新录音 4.m4a",
    "sample_transcript": "data/新录音 4.txt",
    "audio_duration": "00:09:21.17",
    "audio_created_at": "2026-07-21T08:04:26Z",
}


QUESTIONNAIRE_STEPS: tuple[QuestionnaireStep, ...] = (
    QuestionnaireStep(
        "survey_id",
        "free_text",
        "开始了啊。先记录调查对象编号，请您说一下编号。",
        "Let's start. Please tell me the participant survey ID.",
        "请说一下调查对象编号；如果现在没有编号，也可以说暂时没有。",
        "Please provide the survey ID, or say it is not available.",
    ),
    QuestionnaireStep(
        "oa_diagnosis",
        "yes_no",
        "您是否被医生明确诊断为骨关节炎？",
        "Have you been clearly diagnosed with osteoarthritis by a doctor?",
        "这里需要确认是或否：医生是否明确诊断过骨关节炎？",
        "Please answer yes or no: has a doctor diagnosed osteoarthritis?",
    ),
    QuestionnaireStep(
        "affected_joints",
        "multi_choice",
        "主要受累的关节，也就是主要疼痛或不适的关节是哪些？比如膝关节、髋关节、手部、足部、肩关节，或者其他部位。",
        "Which joints are mainly affected? For example knee, hip, hand, foot, shoulder, or another joint.",
        "请说主要受累的关节，可以多选，比如膝关节、髋关节、手、足、肩，或其他。",
        "Please name the affected joints, such as knee, hip, hand, foot, shoulder, or other.",
    ),
    QuestionnaireStep(
        "symptom_duration",
        "free_text",
        "您的关节不适，比如疼痛、僵硬、肿胀等，已经持续多长时间了？",
        "How long have the joint symptoms, such as pain, stiffness, or swelling, lasted?",
        "请说一个大概时间，比如几个月或几年。",
        "Please give an approximate duration, such as months or years.",
    ),
    QuestionnaireStep(
        "last_flare_onset",
        "free_text",
        "关于最近一次疼痛发作，我问您几个问题。最近一次发作大概是什么时候？比如多久之前。",
        "Thinking about the most recent pain flare, about when did it start?",
        "请回忆最近一次发作大概是什么时候，比如半年前、上周或昨天。",
        "Please say roughly when the most recent flare started.",
    ),
    QuestionnaireStep(
        "last_flare_duration",
        "free_text",
        "那次发作或不适大概持续了多长时间？",
        "How long did that flare or discomfort last?",
        "请说那次发作持续了多久，比如几天、几周或几个月。",
        "Please say how long that flare lasted.",
    ),
    QuestionnaireStep(
        "last_flare_pain_score",
        "pain_score",
        "然后我们给那次发作的疼痛打个分。这个评分是0到10分：0分是一点都不疼，10分是痛不欲生。为了方便您判断，一般轻度疼痛是0到3分，通常不影响睡眠；4到6分左右是中度疼痛，可能会有一点影响睡眠；如果安静平卧时也会疼，通常就更重一些。您回忆那次疼痛，大概是几分？",
        "Please rate the pain during that flare from 0 to 10: 0 is no pain, 10 is unbearable. Mild pain is usually 0 to 3 and does not affect sleep; moderate pain is around 4 to 6 and may affect sleep a little; pain even while lying still is usually more severe. About what score was that pain?",
        "请按0到10分估计；如果不好直接给数字，可以说轻度、中度、是否影响睡眠、安静平卧会不会疼。",
        "Please estimate 0 to 10. If a number is hard, say mild/moderate/severe, whether it affected sleep, and whether it hurt while lying still.",
    ),
    QuestionnaireStep(
        "annual_flare_frequency",
        "flare_frequency",
        "过去一年内，这种疼痛大约发作过几次？可以说0次、1次、2次、3次、4次、5次、6到10次，或者超过10次。",
        "In the past year, about how many times has this pain flared: 0, 1, 2, 3, 4, 5, 6 to 10, or more than 10 times?",
        "请按次数回答：0、1、2、3、4、5、6到10次，或超过10次。",
        "Please choose 0, 1, 2, 3, 4, 5, 6 to 10, or more than 10.",
    ),
    QuestionnaireStep(
        "usual_pain_response",
        "usual_response",
        "当骨关节炎引发关节疼痛不适时，您通常会怎么处理？是立刻去医院门诊，先自行买止痛药或膏药，单纯忍着，去社区医院或理疗店，还是其他方式？",
        "When osteoarthritis causes joint pain, what do you usually do: go to hospital clinic, first buy pain medicine or patches yourself, endure it, use a community clinic or therapy shop, or something else?",
        "请说最常见的一种处理方式。",
        "Please say the one option that best describes what you usually do.",
    ),
    QuestionnaireStep(
        "oral_painkiller_used",
        "yes_no",
        "您疼痛发作时，是否口服过止疼药？",
        "During pain flares, have you taken oral pain medicine?",
        "这里需要确认是或否：疼痛发作时是否吃过口服止疼药？",
        "Please answer yes or no: have you taken oral pain medicine during flares?",
    ),
    QuestionnaireStep(
        "oral_painkiller_name",
        "free_text",
        "请您说一下口服止痛药的药品名称，记得多少说多少。",
        "Please tell me the name of the oral pain medicine, as much as you remember.",
        "请说药品名称；如果记不清，可以说记不清。",
        "Please say the medicine name, or say you do not remember.",
    ),
    QuestionnaireStep(
        "oral_painkiller_no_reason",
        "free_text",
        "没有口服止疼药的主要原因是什么？",
        "What is the main reason you have not taken oral pain medicine?",
        "请简单说一下没有口服止疼药的原因。",
        "Please briefly say why no oral pain medicine was used.",
    ),
    QuestionnaireStep(
        "adherence_to_doctor_order",
        "yes_no",
        "您服用口服止痛药时，能否严格遵从医嘱服药？",
        "When taking oral pain medicine, can you strictly follow the doctor's instructions?",
        "请回答能或不能；也可以说不确定。",
        "Please answer yes or no, or say uncertain.",
    ),
    QuestionnaireStep(
        "missed_doses",
        "yes_no",
        "口服止痛药期间，您有时候会忘记服药吗？",
        "While taking oral pain medicine, do you sometimes forget doses?",
        "请回答会或不会。",
        "Please answer yes or no.",
    ),
    QuestionnaireStep(
        "stopped_after_improvement",
        "yes_no",
        "疼痛好转后，您会不会直接自行停药，不再巩固服药？",
        "After the pain improves, do you stop the medicine yourself instead of continuing consolidation treatment?",
        "请回答会或不会。",
        "Please answer yes or no.",
    ),
    QuestionnaireStep(
        "difficulty_taking_as_directed",
        "yes_no",
        "您是否觉得坚持按时按量服药比较困难？",
        "Do you feel it is difficult to keep taking the medicine on time and at the directed dose?",
        "请回答是或否。",
        "Please answer yes or no.",
    ),
    QuestionnaireStep(
        "missed_dose_reasons",
        "multi_choice",
        "如果曾经忘记服药，最主要原因是什么？比如工作繁忙、记性差、担心副作用、自觉症状不重，或者其他原因。",
        "If you have forgotten doses, what were the main reasons: busy work, poor memory, concern about side effects, symptoms not severe, or other?",
        "请说忘记服药的主要原因，可以多选。",
        "Please say the main reasons for missed doses.",
    ),
    QuestionnaireStep(
        "adverse_reactions",
        "yes_no",
        "口服止痛药期间，是否出现过不良反应？",
        "While taking oral pain medicine, did you have any adverse reactions?",
        "请回答有或没有。",
        "Please answer yes or no.",
    ),
    QuestionnaireStep(
        "adverse_reaction_symptoms",
        "multi_choice",
        "如果有不良反应，具体有哪些？比如肠胃不适、头晕或嗜睡、皮肤过敏、肝肾功能异常、水肿或血压升高，或者其他。",
        "If yes, which reactions occurred: stomach discomfort, dizziness or drowsiness, skin allergy, liver or kidney abnormality, swelling or increased blood pressure, or other?",
        "请说具体不良反应，可以多选。",
        "Please name the adverse reaction symptoms.",
    ),
    QuestionnaireStep(
        "pain_improvement_after_meds",
        "improvement",
        "服用止痛药后，疼痛改善情况如何？是明显恶化、稍有恶化、无变化、稍有改善，还是明显改善？",
        "After taking pain medicine, how did the pain change: markedly worse, slightly worse, no change, slightly improved, or markedly improved?",
        "请从明显恶化、稍有恶化、无变化、稍有改善、明显改善中选择。",
        "Please choose markedly worse, slightly worse, no change, slightly improved, or markedly improved.",
    ),
    QuestionnaireStep(
        "function_improvement_after_meds",
        "improvement",
        "服用止痛药后，日常活动能力改善情况如何？是明显恶化、稍有恶化、无变化、稍有改善，还是明显改善？",
        "After taking pain medicine, how did daily activity ability change: markedly worse, slightly worse, no change, slightly improved, or markedly improved?",
        "请从明显恶化、稍有恶化、无变化、稍有改善、明显改善中选择。",
        "Please choose markedly worse, slightly worse, no change, slightly improved, or markedly improved.",
    ),
    QuestionnaireStep(
        "consolidation_medication_willingness",
        "willingness",
        "如果医生告诉您：不疼之后还要继续吃1到2周药进行巩固治疗，可以减少疼痛反复发作。您是否愿意继续吃药？愿意、无所谓，还是不愿意？",
        "If the doctor says continuing medicine for 1 to 2 weeks after pain stops can reduce repeated flares, would you be willing, neutral, or unwilling to continue?",
        "请回答愿意、无所谓，或不愿意。",
        "Please answer willing, neutral, or unwilling.",
    ),
    QuestionnaireStep(
        "non_oral_treatments",
        "multi_choice",
        "除了口服止疼药以外，您还做过哪些治疗？比如外敷膏药、注射治疗、理疗推拿按摩、运动康复、体重管理、护膝拐杖等辅助器具、针灸艾灸、其他，或者没有其他治疗。",
        "Other than oral pain medicine, what treatments have you used: patches, injections, physical therapy or massage, exercise rehab, weight management, assistive devices, acupuncture or moxibustion, other, or none?",
        "请说做过哪些其他治疗，可以多选；没有也可以说没有。",
        "Please say which other treatments were used, or say none.",
    ),
    QuestionnaireStep(
        "painkiller_channels",
        "multi_choice",
        "您主要通过什么渠道获取止痛药？比如医院门诊、社区医院、零售药店、线上药房、家人朋友代买，或者其他。",
        "What channels do you mainly use to obtain pain medicine: hospital clinic, community hospital, retail pharmacy, online pharmacy, family or friend purchase, or other?",
        "请说获取止痛药的渠道，可以多选。",
        "Please name the channels used to obtain pain medicine.",
    ),
    QuestionnaireStep(
        "doctor_counseling",
        "doctor_counseling",
        "您在医院或社区医院买止痛药时，医生有没有讲解用药注意事项？每次仔细交代、大部分时候简单说几句、很少讲解只是开药，还是完全没有讲解？",
        "When buying pain medicine at a hospital or community hospital, did the doctor explain precautions: detailed every time, brief most times, rarely explained, or no explanation?",
        "请从四种情况里选一种：每次仔细交代、大部分时候简单说几句、很少讲解、完全没有讲解。",
        "Please choose one: detailed every time, brief most times, rarely explained, or no explanation.",
    ),
    QuestionnaireStep(
        "retail_pharmacy_reasons",
        "multi_choice",
        "您选择在药店购买止痛药的主要原因是什么？比如去医院费时间、家附近有药店、手机下单送货、药店更便宜、长期吃药方便续药、觉得药店正规放心、药店人员会给建议，或者其他。",
        "What are the main reasons for buying pain medicine at a retail pharmacy: hospital visits take too much time, nearby pharmacy, mobile delivery, cheaper, convenient long-term refill, pharmacy seems trustworthy, staff advice, or other?",
        "请说在药店购买的主要原因，可以多选。",
        "Please say the main reasons for buying at a retail pharmacy.",
    ),
    QuestionnaireStep(
        "retail_pharmacy_purchase_method",
        "purchase_method",
        "您在药店一般怎么买止痛药？拿医生新处方、拿以前旧处方重复买、不用处方自己按疼痛挑，还是没有处方完全听药店人员推荐？",
        "At the pharmacy, how do you usually buy pain medicine: with a new doctor prescription, reuse an old prescription, self-select without prescription, or follow pharmacy staff recommendation without prescription?",
        "请从新处方、旧处方、自己挑选、听药店人员推荐中选择。",
        "Please choose new prescription, old prescription, self-select, or staff recommendation.",
    ),
    QuestionnaireStep(
        "pharmacy_guidance_contraindications",
        "guidance_frequency",
        "药店药师或销售人员是否询问过您有没有胃病、肾病等禁忌症？从未、偶尔，还是经常？",
        "Did pharmacy staff ask whether you have contraindications such as stomach or kidney disease: never, occasionally, or often?",
        "请回答从未、偶尔，或经常。",
        "Please answer never, occasionally, or often.",
    ),
    QuestionnaireStep(
        "pharmacy_guidance_dosage",
        "guidance_frequency",
        "药店药师或销售人员是否告知过具体用法用量，比如餐后服用？从未、偶尔，还是经常？",
        "Did pharmacy staff explain dosage and directions, such as taking after meals: never, occasionally, or often?",
        "请回答从未、偶尔，或经常。",
        "Please answer never, occasionally, or often.",
    ),
    QuestionnaireStep(
        "pharmacy_guidance_avoid_multiple_painkillers",
        "guidance_frequency",
        "药店药师或销售人员是否提醒过不要同时使用多种止痛药？从未、偶尔，还是经常？",
        "Did pharmacy staff remind you not to use multiple pain medicines at the same time: never, occasionally, or often?",
        "请回答从未、偶尔，或经常。",
        "Please answer never, occasionally, or often.",
    ),
    QuestionnaireStep(
        "pharmacy_guidance_long_term_risks",
        "guidance_frequency",
        "药店药师或销售人员是否告知过长期用药的风险？从未、偶尔，还是经常？",
        "Did pharmacy staff explain long-term medicine risks: never, occasionally, or often?",
        "请回答从未、偶尔，或经常。",
        "Please answer never, occasionally, or often.",
    ),
)


QUESTIONNAIRE_STEP_KEYS = tuple(step.key for step in QUESTIONNAIRE_STEPS)
_STEPS_BY_KEY = {step.key: step for step in QUESTIONNAIRE_STEPS}


def first_questionnaire_step() -> str:
    return required_steps({})[0]


def is_questionnaire_step(step: str) -> bool:
    return step in _STEPS_BY_KEY


def prompt_for_step(step: str, language: str) -> str:
    definition = _STEPS_BY_KEY[step]
    return definition.prompt_zh if language == "zh-CN" else definition.prompt_en


def clarification_for_step(step: str, language: str) -> str:
    definition = _STEPS_BY_KEY[step]
    return definition.clarification_zh if language == "zh-CN" else definition.clarification_en


def required_steps(answers: dict[str, Any]) -> list[str]:
    return [step.key for step in QUESTIONNAIRE_STEPS if should_ask_step(step.key, answers)]


def next_missing_step(answers: dict[str, Any], after: str | None = None) -> str | None:
    steps = required_steps(answers)
    start = 0
    if after in steps:
        start = steps.index(str(after)) + 1
    for key in steps[start:]:
        if key not in answers:
            return key
    return None


def should_ask_step(step: str, answers: dict[str, Any]) -> bool:
    if step == "survey_id":
        return _survey_id_enabled()

    oral_used = _answer_value(answers.get("oral_painkiller_used"))
    missed_doses = _answer_value(answers.get("missed_doses"))
    adverse_reactions = _answer_value(answers.get("adverse_reactions"))
    channels = _answer_values(answers.get("painkiller_channels"))

    if step == "oral_painkiller_name":
        return oral_used == "yes"
    if step == "oral_painkiller_no_reason":
        return oral_used == "no"
    if step in {
        "adherence_to_doctor_order",
        "missed_doses",
        "stopped_after_improvement",
        "difficulty_taking_as_directed",
        "adverse_reactions",
        "pain_improvement_after_meds",
        "function_improvement_after_meds",
    }:
        return oral_used == "yes"
    if step == "missed_dose_reasons":
        return oral_used == "yes" and missed_doses == "yes"
    if step == "adverse_reaction_symptoms":
        return oral_used == "yes" and adverse_reactions == "yes"
    if step == "doctor_counseling":
        return bool({"hospital_clinic", "community_hospital"} & set(channels))
    if step in {
        "retail_pharmacy_reasons",
        "retail_pharmacy_purchase_method",
        "pharmacy_guidance_contraindications",
        "pharmacy_guidance_dosage",
        "pharmacy_guidance_avoid_multiple_painkillers",
        "pharmacy_guidance_long_term_risks",
    }:
        return "retail_pharmacy" in channels
    return True


def questionnaire_step_schema(step: str, language: str = "zh-CN") -> dict[str, Any]:
    definition = _STEPS_BY_KEY[step]
    schema: dict[str, Any] = {
        "step": step,
        "kind": definition.kind,
        "question": prompt_for_step(step, language),
        "clarification": clarification_for_step(step, language),
    }
    options = _allowed_options(step)
    if options:
        schema["allowed_values"] = options
        schema["options"] = _option_specs(step)
    if definition.kind == "pain_score":
        schema["value_type"] = "integer_0_to_10"
        schema["pain_anchor_rubric"] = _pain_anchor_rubric(language)
    elif definition.kind == "multi_choice":
        schema["value_type"] = "array"
    else:
        schema["value_type"] = "string"
    return schema


def questionnaire_context(answers: dict[str, Any]) -> dict[str, Any]:
    return {
        "answered_steps": sorted(answers),
        "answers": answers,
        "required_steps": required_steps(answers),
        "skipped_if_now": mark_not_applicable(answers),
    }


def validate_questionnaire_interpretation(
    step: str,
    interpretation: dict[str, Any] | None,
    raw: str,
    *,
    min_confidence: float = 0.72,
) -> tuple[bool, dict[str, Any] | None, str]:
    if not isinstance(interpretation, dict):
        return False, None, "missing_ai_interpretation"
    turn_type = str(interpretation.get("turn_type") or "unknown")
    if turn_type != "answer":
        return False, None, f"ai_turn_{turn_type}"
    if interpretation.get("answers_current_question") is not True:
        return False, None, "ai_answer_wrong_question"
    try:
        confidence = float(interpretation.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < min_confidence:
        return False, None, "ai_low_confidence"
    normalized = interpretation.get("normalized")
    if not isinstance(normalized, dict):
        return False, None, "ai_missing_normalized_answer"

    accepted, payload, reason = _validate_normalized_answer(step, normalized, raw)
    if not accepted or payload is None:
        return accepted, payload, reason
    payload = dict(payload)
    payload["interpretation"] = {
        "accepted": True,
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
        "strategy": "ai_semantic_interpreter",
        "fuzzy": True,
        "needs_review": confidence < 0.82,
        "evidence": str(interpretation.get("evidence") or raw),
        "turn_type": turn_type,
        "answers_current_question": True,
        "reason": str(interpretation.get("reason") or ""),
        "validator": "questionnaire_schema",
    }
    clarification = interpretation.get("clarification_prompt")
    if clarification:
        payload["interpretation"]["model_clarification_prompt"] = str(clarification)
    return True, payload, "valid_ai_interpretation"


def parse_questionnaire_answer(step: str, text: str) -> tuple[bool, dict[str, Any] | None, str]:
    definition = _STEPS_BY_KEY[step]
    raw = _clean(text)
    if not raw:
        return False, None, "empty_answer"
    if _looks_like_user_feedback(raw):
        return False, None, "user_feedback_not_answer"

    if definition.kind == "free_text":
        return True, _with_interpretation({"value": raw}, raw, 0.9, "free_text"), "valid_free_text"
    if definition.kind == "yes_no":
        if step == "oa_diagnosis":
            value = _parse_oa_diagnosis_yes_no(raw)
        elif step == "adverse_reactions":
            value = _parse_adverse_reaction_yes_no(raw)
        else:
            value = _parse_yes_no(raw, step)
        if value == "unknown":
            return False, None, "unclear_yes_no"
        confidence, strategy, fuzzy = _yes_no_interpretation(raw, step)
        return True, _with_interpretation({"value": value}, raw, confidence, strategy, fuzzy), "valid_yes_no"
    if definition.kind == "pain_score":
        score = parse_pain_score(raw)
        if score is None and step == "last_flare_pain_score":
            score = _parse_qualitative_pain_score(raw)
            if score is not None:
                return True, _with_interpretation(
                    {"value": score, "scale": "0-10", "method": "qualitative_anchor"},
                    raw,
                    0.78,
                    "qualitative_anchor",
                    fuzzy=True,
                    needs_review=True,
                ), "valid_qualitative_pain_score"
        if score is None:
            return False, None, "invalid_pain_score"
        return True, _with_interpretation(
            {"value": score, "scale": "0-10", "method": "direct_numeric"},
            raw,
            0.96,
            "direct_numeric",
        ), "valid_pain_score"
    if definition.kind == "flare_frequency":
        value = _parse_flare_frequency(raw)
        if value is None:
            return False, None, "invalid_flare_frequency"
        confidence, strategy, fuzzy = _frequency_interpretation(raw)
        return True, _with_interpretation({"value": value}, raw, confidence, strategy, fuzzy), "valid_flare_frequency"
    if definition.kind == "usual_response":
        return _choice_result(_parse_usual_response(raw), raw)
    if definition.kind == "multi_choice":
        labels = _parse_multi_choice(step, raw)
        if not labels:
            return False, None, "unclear_multi_choice"
        confidence, strategy, fuzzy = _multi_choice_interpretation(step, raw, labels)
        return True, _with_interpretation(
            {"values": labels, "other_text": raw if "other" in labels else None},
            raw,
            confidence,
            strategy,
            fuzzy,
            needs_review="other" in labels,
        ), "valid_multi_choice"
    if definition.kind == "improvement":
        return _choice_result(_parse_improvement(raw), raw)
    if definition.kind == "willingness":
        return _choice_result(_parse_willingness(raw), raw)
    if definition.kind == "doctor_counseling":
        return _choice_result(_parse_doctor_counseling(raw), raw)
    if definition.kind == "purchase_method":
        return _choice_result(_parse_purchase_method(raw), raw)
    if definition.kind == "guidance_frequency":
        return _choice_result(_parse_guidance_frequency(raw), raw)
    return True, _with_interpretation({"value": raw}, raw, 0.72, "fallback", fuzzy=True, needs_review=True), "valid_fallback"


def mark_not_applicable(answers: dict[str, Any]) -> dict[str, str]:
    skipped: dict[str, str] = {}
    for step in QUESTIONNAIRE_STEP_KEYS:
        if step not in answers and not should_ask_step(step, answers):
            skipped[step] = "not_applicable_by_prior_answer"
    return skipped


def completion_summary(answers: dict[str, Any]) -> dict[str, Any]:
    required = required_steps(answers)
    complete = [key for key in required if key in answers]
    missing = [key for key in required if key not in answers]
    return {
        "required_count": len(required),
        "complete_count": len(complete),
        "missing_required_fields": missing,
        "complete": not missing,
    }


def _validate_normalized_answer(step: str, normalized: dict[str, Any], raw: str) -> tuple[bool, dict[str, Any] | None, str]:
    definition = _STEPS_BY_KEY[step]
    if definition.kind == "free_text":
        value = _normalized_string(normalized)
        if not value:
            return False, None, "ai_empty_free_text"
        return True, {"value": value}, "valid_ai_free_text"
    if definition.kind == "yes_no":
        value = _normalize_ai_yes_no_value(_normalized_string(normalized), step)
        if value not in {"yes", "no"}:
            return False, None, "ai_invalid_yes_no"
        return True, {"value": value}, "valid_ai_yes_no"
    if definition.kind == "pain_score":
        score, method = _normalize_ai_pain_score(step, normalized, raw)
        if score is None or not 0 <= score <= 10:
            return False, None, "ai_invalid_pain_score"
        return True, {"value": score, "scale": "0-10", "method": method}, "valid_ai_pain_score"
    if definition.kind in {"flare_frequency", "usual_response", "improvement", "willingness", "doctor_counseling", "purchase_method", "guidance_frequency"}:
        value = _normalize_ai_choice_value(step, _normalized_string(normalized))
        allowed = set(_allowed_options(step))
        if value not in allowed:
            return False, None, "ai_invalid_choice"
        payload: dict[str, Any] = {"value": value}
        if value == "other":
            payload["other_text"] = str(normalized.get("other_text") or raw)
        return True, payload, "valid_ai_choice"
    if definition.kind == "multi_choice":
        values = normalized.get("values")
        if values is None and normalized.get("value") is not None:
            values = [normalized.get("value")]
        if not isinstance(values, list):
            return False, None, "ai_invalid_multi_choice"
        labels = [
            normalized_label
            for value in values
            if (normalized_label := _normalize_ai_choice_value(step, str(value).strip()))
        ]
        allowed = set(_allowed_options(step))
        if not labels or any(label not in allowed for label in labels):
            return False, None, "ai_invalid_multi_choice"
        if "none" in labels and len(labels) > 1:
            return False, None, "ai_invalid_multi_choice"
        return True, {"values": labels, "other_text": str(normalized.get("other_text") or raw) if "other" in labels else None}, "valid_ai_multi_choice"
    return False, None, "ai_unsupported_step_kind"


def _pain_anchor_rubric(language: str = "zh-CN") -> dict[str, object]:
    if language == "zh-CN":
        return {
            "scale": "0到10分",
            "anchors": [
                {"score": 0, "label": "一点都不疼"},
                {"range": "0-3", "label": "轻度疼痛", "signals": ["通常不影响睡眠", "安静平卧不疼", "咳嗽深呼吸不疼", "翻身不疼", "走路有点疼/僵硬"]},
                {"range": "4-6", "label": "中度疼痛", "signals": ["可能轻微影响睡眠", "休息或平卧有时也疼"]},
                {"range": "7-10", "label": "重度疼痛", "signals": ["明显影响睡眠", "安静平卧也明显疼", "痛不欲生接近10分"]},
            ],
            "instruction": "先让受访者按锚点自我定位；若只描述功能/睡眠影响，可据证据估计一个整数并标注为anchor_based。",
        }
    return {
        "scale": "0 to 10",
        "anchors": [
            {"score": 0, "label": "no pain"},
            {"range": "0-3", "label": "mild", "signals": ["usually does not affect sleep", "no pain lying still", "walking discomfort/stiffness only"]},
            {"range": "4-6", "label": "moderate", "signals": ["may affect sleep a little", "sometimes hurts at rest"]},
            {"range": "7-10", "label": "severe", "signals": ["clearly affects sleep", "hurts even lying still", "unbearable is near 10"]},
        ],
        "instruction": "Ask the participant to self-place on the anchored scale; if they give anchor evidence, estimate an integer and mark anchor_based.",
    }


def _normalize_ai_pain_score(step: str, normalized: dict[str, Any], raw: str) -> tuple[int | None, str]:
    candidates = [
        normalized.get("value"),
        normalized.get("score"),
        normalized.get("pain_score"),
        normalized.get("range"),
        normalized.get("severity"),
        normalized.get("severity_band"),
        normalized.get("label"),
        raw,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        score = _parse_direct_score_value(candidate)
        if score is not None:
            return score, "ai_semantic_direct_numeric"
    if step == "last_flare_pain_score":
        for candidate in candidates:
            if candidate is None:
                continue
            score = _parse_anchored_pain_score(str(candidate))
            if score is not None:
                return score, "ai_semantic_anchor_based"
    return None, "ai_semantic"


def _parse_direct_score_value(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        score = int(value)
        return score if 0 <= score <= 10 else None
    text = str(value).strip()
    if not text:
        return None
    compact = re.sub(r"\s+", "", text.lower())
    if compact in {"0-3", "0到3", "零到三", "轻度", "mild"}:
        return None
    if compact in {"4-6", "4到6", "四到六", "中度", "moderate"}:
        return None
    if compact in {"7-10", "7到10", "七到十", "重度", "severe"}:
        return None
    score = parse_pain_score(text)
    return score if score is not None and 0 <= score <= 10 else None


def _parse_anchored_pain_score(text: str) -> int | None:
    compact = re.sub(r"\s+", "", text.lower())
    if not compact:
        return None
    if any(term in compact for term in ("一点都不疼", "完全不疼", "一点不疼", "不疼痛", "无痛", "nopain")):
        return 0

    mild_signals = (
        "轻度", "0-3", "0到3", "零到三", "不影响睡眠", "不影响休息", "睡眠不受影响",
        "平卧不疼", "安静平卧不疼", "休息不疼", "翻身不疼", "咳嗽深呼吸不疼",
        "走路有点", "走路僵硬", "轻微", "mild",
    )
    if any(term in compact for term in mild_signals):
        return 2

    if any(term in compact for term in ("痛不欲生", "无法忍受", "不能忍", "最严重", "unbearable", "worst")):
        return 10
    if any(term in compact for term in ("重度", "严重影响睡眠", "睡不了", "睡不着", "疼醒", "平卧也明显疼", "安静也明显疼", "severe")):
        return 8
    if any(term in compact for term in ("中度", "轻微影响睡眠", "有点影响睡眠", "睡眠受影响", "平卧有时候疼", "安静平卧有时候疼", "休息时也疼", "moderate")):
        return 5
    if "影响睡眠" in compact and not any(term in compact for term in ("不影响睡眠", "没有影响睡眠", "没影响睡眠")):
        return 5
    return None


def _normalize_ai_yes_no_value(value: str | None, step: str | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"yes", "no"}:
        return text
    parsed = _parse_oa_diagnosis_yes_no(text) if step == "oa_diagnosis" else _parse_yes_no(text, step)
    return parsed if parsed in {"yes", "no"} else text


def _option_specs(step: str) -> list[dict[str, str]]:
    aliases = _choice_aliases(step)
    specs = []
    for value in _allowed_options(step):
        terms = aliases.get(value, ())
        zh = next((term for term in terms if _has_cjk(term)), value)
        en = next((term for term in terms if not _has_cjk(term)), value)
        specs.append({"value": value, "zh": zh, "en": en})
    return specs


def _choice_aliases(step: str) -> dict[str, tuple[str, ...]]:
    definition = _STEPS_BY_KEY[step]
    if definition.kind == "yes_no":
        return {"yes": ("是", "有", "会", "能", "吃过", "用过", "yes"), "no": ("否", "不是", "没有", "不会", "不能", "没吃过", "no")}
    if definition.kind == "flare_frequency":
        return {"0": ("0次", "零次", "没有", "none"), "1": ("1次", "一次", "one"), "2": ("2次", "两次", "二次", "two"), "3": ("3次", "三次", "three"), "4": ("4次", "四次", "four"), "5": ("5次", "五次", "five"), "1-2": ("一两次", "一到两次", "1-2", "1 to 2"), "6-10": ("六到十次", "6到10次", "6-10", "6 to 10"), ">10": ("超过十次", "十多次", "很多次", "more than 10")}
    if definition.kind == "usual_response":
        return {"hospital_clinic_immediately": ("立刻去医院门诊", "马上去医院", "hospital clinic"), "self_medicate_then_hospital_if_needed": ("先自行买止痛药或膏药", "自己买药", "self medicate"), "endure_no_treatment": ("单纯忍着", "忍着", "endure"), "community_or_physical_therapy": ("社区医院或理疗店", "社区", "理疗", "community clinic"), "other": ("其他", "other")}
    if definition.kind == "improvement":
        return {"markedly_worse": ("明显恶化", "显著恶化", "much worse"), "slightly_worse": ("稍有恶化", "有点恶化", "slightly worse"), "no_change": ("无变化", "没有变化", "没变化", "no change"), "slightly_improved": ("稍有改善", "有点改善", "slightly improved"), "markedly_improved": ("明显改善", "显著改善", "好多了", "不疼了", "markedly improved")}
    if definition.kind == "willingness":
        return {"willing": ("愿意", "可以", "willing"), "neutral": ("无所谓", "都行", "neutral"), "unwilling": ("不愿意", "不想", "unwilling")}
    if definition.kind == "doctor_counseling":
        return {"detailed_every_time": ("每次仔细交代", "详细讲解", "detailed every time"), "brief_most_times": ("大部分时候简单说几句", "简单说", "brief most times"), "rarely_explained": ("很少讲解", "只是开药", "rarely explained"), "none": ("完全没有讲解", "没有", "none")}
    if definition.kind == "purchase_method":
        return {"new_prescription": ("拿医生新处方", "新处方", "new prescription"), "old_prescription_reuse": ("拿以前旧处方重复买", "旧处方", "old prescription"), "self_select_without_prescription": ("不用处方自己挑", "自己按疼痛挑", "self select"), "staff_recommendation_without_prescription": ("听药店人员推荐", "店员推荐", "staff recommendation")}
    if definition.kind == "guidance_frequency":
        return {"never": ("从未", "没有", "never"), "occasionally": ("偶尔", "有时候", "occasionally"), "often": ("经常", "常常", "often")}
    if step == "affected_joints":
        return {"knee": ("膝关节", "膝盖", "腿", "knee"), "hip": ("髋关节", "胯", "hip"), "hand": ("手部", "手", "hand"), "foot": ("足部", "脚", "foot"), "shoulder": ("肩关节", "肩", "shoulder"), "other": ("其他", "other")}
    if step == "missed_dose_reasons":
        return {"busy_work": ("工作繁忙", "工作忙", "busy work"), "poor_memory": ("记性差", "忘记", "poor memory"), "side_effect_concern": ("担心副作用", "副作用", "side effects"), "symptoms_not_severe": ("自觉症状不重", "不严重", "symptoms not severe"), "other": ("其他", "other")}
    if step == "adverse_reaction_symptoms":
        return {"gastrointestinal_discomfort": ("肠胃不适", "胃不舒服", "gastrointestinal discomfort"), "dizziness_or_drowsiness": ("头晕或嗜睡", "头晕", "嗜睡", "dizziness or drowsiness"), "skin_allergy": ("皮肤过敏", "过敏", "skin allergy"), "liver_or_kidney_abnormality": ("肝肾功能异常", "肝", "肾", "liver or kidney abnormality"), "edema_or_blood_pressure": ("水肿或血压升高", "水肿", "血压", "edema or blood pressure"), "other": ("其他", "other")}
    if step == "non_oral_treatments":
        return {"topical_patch": ("外敷膏药", "膏药", "patch"), "injection": ("注射治疗", "打针", "injection"), "physical_therapy": ("理疗推拿按摩", "理疗", "按摩", "physical therapy"), "exercise_therapy": ("运动康复", "锻炼", "exercise therapy"), "weight_management": ("体重管理", "减重", "weight management"), "assistive_device": ("护膝拐杖", "护膝", "拐杖", "assistive device"), "acupuncture_moxibustion": ("针灸艾灸", "针灸", "艾灸", "acupuncture"), "other": ("其他", "other"), "none": ("没有其他治疗", "没有", "none")}
    if step == "painkiller_channels":
        return {"hospital_clinic": ("医院门诊", "医生开", "医院", "hospital clinic"), "community_hospital": ("社区医院", "社区", "community hospital"), "retail_pharmacy": ("零售药店", "药店", "retail pharmacy"), "online_pharmacy": ("线上药房", "网上", "online pharmacy"), "family_or_friend": ("家人朋友代买", "家人", "朋友", "family or friend"), "other": ("其他", "other"), "none": ("没有", "none")}
    if step == "retail_pharmacy_reasons":
        return {"hospital_inconvenient": ("去医院费时间", "医院费时间", "hospital inconvenient"), "nearby_pharmacy": ("家附近有药店", "附近", "nearby pharmacy"), "online_delivery": ("手机下单送货", "送货", "online delivery"), "cheaper": ("药店更便宜", "便宜", "cheaper"), "long_term_refill": ("长期吃药方便续药", "续药", "long term refill"), "trust_formal": ("药店正规放心", "正规", "放心", "trust formal"), "staff_advice": ("药店人员会给建议", "药师建议", "staff advice"), "other": ("其他", "other")}
    return {}


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _normalize_ai_choice_value(step: str, value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text in set(_allowed_options(step)):
        return text
    compact = re.sub(r"\s+", "", text.lower())
    aliases = _choice_aliases(step)
    for canonical, terms in aliases.items():
        for term in terms:
            if compact == re.sub(r"\s+", "", term.lower()):
                return canonical
    ordered_terms = sorted(
        ((canonical, term) for canonical, terms in aliases.items() for term in terms),
        key=lambda item: len(item[1]),
        reverse=True,
    )
    for canonical, term in ordered_terms:
        term_compact = re.sub(r"\s+", "", term.lower())
        if term_compact and term_compact in compact:
            return canonical
    return text


def _normalized_string(normalized: dict[str, Any]) -> str | None:
    value = normalized.get("value")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _allowed_options(step: str) -> list[str]:
    definition = _STEPS_BY_KEY[step]
    if definition.kind == "yes_no":
        return ["yes", "no"]
    if definition.kind == "flare_frequency":
        return ["0", "1", "2", "3", "4", "5", "1-2", "6-10", ">10"]
    if definition.kind == "usual_response":
        return ["hospital_clinic_immediately", "self_medicate_then_hospital_if_needed", "endure_no_treatment", "community_or_physical_therapy", "other"]
    if definition.kind == "improvement":
        return ["markedly_worse", "slightly_worse", "no_change", "slightly_improved", "markedly_improved"]
    if definition.kind == "willingness":
        return ["willing", "neutral", "unwilling"]
    if definition.kind == "doctor_counseling":
        return ["detailed_every_time", "brief_most_times", "rarely_explained", "none"]
    if definition.kind == "purchase_method":
        return ["new_prescription", "old_prescription_reuse", "self_select_without_prescription", "staff_recommendation_without_prescription"]
    if definition.kind == "guidance_frequency":
        return ["never", "occasionally", "often"]
    if step == "affected_joints":
        return ["knee", "hip", "hand", "foot", "shoulder", "other"]
    if step == "missed_dose_reasons":
        return ["busy_work", "poor_memory", "side_effect_concern", "symptoms_not_severe", "other"]
    if step == "adverse_reaction_symptoms":
        return ["gastrointestinal_discomfort", "dizziness_or_drowsiness", "skin_allergy", "liver_or_kidney_abnormality", "edema_or_blood_pressure", "other"]
    if step == "non_oral_treatments":
        return ["topical_patch", "injection", "physical_therapy", "exercise_therapy", "weight_management", "assistive_device", "acupuncture_moxibustion", "other", "none"]
    if step == "painkiller_channels":
        return ["hospital_clinic", "community_hospital", "retail_pharmacy", "online_pharmacy", "family_or_friend", "other", "none"]
    if step == "retail_pharmacy_reasons":
        return ["hospital_inconvenient", "nearby_pharmacy", "online_delivery", "cheaper", "long_term_refill", "trust_formal", "staff_advice", "other"]
    return []


def _choice_result(value: str | None, raw: str) -> tuple[bool, dict[str, Any] | None, str]:
    if value is None:
        return False, None, "unclear_choice"
    payload: dict[str, Any] = {"value": value}
    if value == "other":
        payload["other_text"] = raw
    confidence, strategy, fuzzy, needs_review = _choice_interpretation(raw, value)
    return True, _with_interpretation(payload, raw, confidence, strategy, fuzzy, needs_review), "valid_choice"


def _with_interpretation(
    payload: dict[str, Any],
    raw: str,
    confidence: float,
    strategy: str,
    fuzzy: bool = False,
    needs_review: bool = False,
) -> dict[str, Any]:
    result = dict(payload)
    result["interpretation"] = {
        "accepted": True,
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
        "strategy": strategy,
        "fuzzy": bool(fuzzy),
        "needs_review": bool(needs_review),
        "evidence": raw,
    }
    return result


def _yes_no_interpretation(raw: str, step: str) -> tuple[float, str, bool]:
    compact = re.sub(r"\s+", "", raw.lower())
    direct = {
        "是", "是的", "对", "对的", "有", "否", "不是", "没有", "没", "无",
        "会", "不会", "能", "不能", "用过", "吃过", "没用过", "没吃过",
    }
    if compact in direct:
        return 0.96, "direct_yes_no", False
    if step == "oa_diagnosis" and any(term in compact for term in ("医生", "诊断", "骨关节炎")):
        return 0.86, "fuzzy_diagnosis_evidence", True
    if step == "adverse_reactions":
        if any(term in compact for term in ("没有不良反应", "没不良反应", "没有副作用", "没副作用", "没有反应", "没反应", "都没有")):
            return 0.94, "direct_adverse_reaction_absence", False
        if any(term in compact for term in ("副作用", "不良反应", "肠胃", "头晕", "过敏", "水肿", "血压")):
            return 0.88, "symptom_evidence", True
    return 0.84, "fuzzy_yes_no", True


def _frequency_interpretation(raw: str) -> tuple[float, str, bool]:
    compact = re.sub(r"\s+", "", raw.lower())
    if re.fullmatch(r"\d+", compact):
        return 0.96, "direct_numeric", False
    return 0.86, "fuzzy_frequency", True


def _multi_choice_interpretation(step: str, raw: str, labels: list[str]) -> tuple[float, str, bool]:
    compact = re.sub(r"\s+", "", raw.lower())
    if labels == ["none"]:
        return 0.94, "direct_none", False
    if step == "painkiller_channels" and any(term in compact for term in ("医生开", "医生给", "医生", "开给我", "开药")):
        return 0.87, "fuzzy_doctor_channel", True
    if step == "affected_joints" and any(term in compact for term in ("气关节", "七关节", "器官节")):
        return 0.76, "stt_fuzzy_joint", True
    if "other" in labels:
        return 0.72, "other_choice", True
    return 0.88, "keyword_multi_choice", len(raw) > 4


def _choice_interpretation(raw: str, value: str) -> tuple[float, str, bool, bool]:
    compact = re.sub(r"\s+", "", raw.lower())
    if value == "other":
        return 0.72, "other_choice", True, True
    if value in {
        "markedly_improved",
        "slightly_improved",
        "markedly_worse",
        "slightly_worse",
        "no_change",
    }:
        if any(term in compact for term in ("明显改善", "稍有改善", "明显恶化", "稍有恶化", "无变化", "没变化")):
            return 0.96, "direct_improvement_choice", False, False
        if any(term in compact for term in ("不疼", "管用", "有效", "吃一两颗就不疼")):
            return 0.86, "fuzzy_effect_description", True, False
        return 0.74, "fuzzy_improvement_description", True, True
    if value in {"willing", "neutral", "unwilling"}:
        return 0.94, "direct_willingness_choice", False, False
    return 0.88, "keyword_choice", len(raw) > 4, False


def _answer_value(answer: Any) -> str | None:
    if isinstance(answer, dict):
        value = answer.get("value")
        return str(value) if value is not None else None
    if isinstance(answer, str):
        return answer
    return None


def _answer_values(answer: Any) -> list[str]:
    if isinstance(answer, dict):
        values = answer.get("values")
        if isinstance(values, list):
            return [str(value) for value in values]
        value = answer.get("value")
        return [str(value)] if value is not None else []
    return []



def _looks_like_user_feedback(text: str) -> bool:
    compact = re.sub(r"\s+", "", text.lower())
    feedback_terms = (
        "不聪明",
        "不大聪明",
        "太笨",
        "很笨",
        "听不懂",
        "没听懂",
        "没听明白",
        "答非所问",
        "问错",
        "乱问",
        "不是这个",
        "你搞错",
        "你错了",
        "wrongquestion",
        "notwhatimean",
    )
    return any(term in compact for term in feedback_terms)

def _parse_oa_diagnosis_yes_no(text: str) -> str:
    compact = re.sub(r"\s+", "", text.lower())
    if compact in {"是", "是的", "对", "对的", "有", "诊断过"}:
        return "yes"
    if compact in {"否", "不是", "没有", "没", "没诊断", "没有诊断", "没诊断过", "不知道", "不清楚"}:
        return "no" if compact not in {"不知道", "不清楚"} else "unknown"
    if any(term in compact for term in ("明确诊断", "医生说是", "医生诊断", "诊断为骨关节炎", "骨关节炎")):
        if any(term in compact for term in ("没有", "没", "不是", "否")):
            return "no"
        return "yes"
    return "unknown"


def _parse_yes_no(text: str, step: str | None = None) -> str:
    compact = re.sub(r"\s+", "", text.lower())
    if step == "oa_diagnosis" and any(term in compact for term in ("这里是", "这是", "是北京", "是研究")):
        return "unknown"
    if compact in {"不会", "不能", "不是", "不用", "不愿意", "没用过", "没吃过"}:
        return "no"
    if compact in {"会", "会的", "能", "能的", "愿意", "用过", "吃过", "是", "是的", "对", "对的", "有"}:
        return "yes"
    if any(term in compact for term in ("不会", "不能", "没有", "没", "无", "否")):
        return "no"
    yes_terms = ("会的", "可以", "能", "有", "是的", "对的", "明确诊断", "医生说是", "用过", "吃过")
    if any(term in compact for term in yes_terms):
        return "yes"
    if step != "oa_diagnosis" and any(term in compact for term in ("会", "是", "对")):
        return "yes"
    return classify_yes_no_unsure(text)


def _parse_adverse_reaction_yes_no(text: str) -> str:
    compact = re.sub(r"\s+", "", text.lower())
    if any(term in compact for term in ("没有不良反应", "没不良反应", "没有副作用", "没副作用", "没有反应", "没反应", "都没有")):
        return "no"
    if any(term in compact for term in ("不良反应", "副作用", "肠胃", "胃不舒服", "胃疼", "恶心", "头晕", "嗜睡", "皮疹", "瘙痒", "过敏", "水肿", "血压")):
        return "yes"
    if compact in {"没有", "没", "无", "没有的", "没有没有"}:
        return "no"
    if any(term in compact for term in ("不疼", "止疼", "改善", "有效", "管用")):
        return "unknown"
    return _parse_yes_no(text)


def _parse_qualitative_pain_score(text: str) -> int | None:
    return _parse_anchored_pain_score(text)


def _parse_flare_frequency(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text.lower())
    if "零售" in compact:
        return None
    if any(term in compact for term in ("超过10", "超过十", ">10", "大于10", "大于十", "十多", "很多")):
        return ">10"
    if any(term in compact for term in ("6-10", "6–10", "6到10", "六到十", "六至十")):
        return "6-10"
    if any(term in compact for term in ("一两", "1-2", "一二")):
        return "1-2"
    for value in ("0", "1", "2", "3", "4", "5"):
        if re.search(rf"(?<!\d){value}(?!\d)", compact):
            return value
    number_words = {"零": "0", "一": "1", "二": "2", "两": "2", "三": "3", "四": "4", "五": "5"}
    for word, value in number_words.items():
        if word in compact:
            return value
    return None


def _parse_usual_response(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text.lower())
    if any(term in compact for term in ("社区", "理疗店", "推拿", "按摩")):
        return "community_or_physical_therapy"
    if any(term in compact for term in ("忍", "不采取", "不治疗", "不去医院")):
        return "endure_no_treatment"
    if any(term in compact for term in ("自行", "自己", "止痛药", "止疼药", "膏药", "买药", "效果不好")):
        return "self_medicate_then_hospital_if_needed"
    if any(term in compact for term in ("立刻", "马上", "医院", "门诊", "医生")):
        return "hospital_clinic_immediately"
    if any(term in compact for term in ("other", "其他")):
        return "other"
    return None


def _parse_multi_choice(step: str, text: str) -> list[str]:
    compact = re.sub(r"\s+", "", text.lower())
    if step == "affected_joints":
        mapping = {
            "knee": ("膝", "腿", "气关节", "七关节", "器官节", "knee"),
            "hip": ("髋", "胯", "hip"),
            "hand": ("手", "hand"),
            "foot": ("足", "脚", "foot"),
            "shoulder": ("肩", "shoulder"),
        }
    elif step == "missed_dose_reasons":
        mapping = {
            "busy_work": ("工作忙", "工作繁忙", "忙", "busy"),
            "poor_memory": ("记性差", "忘", "记不住", "memory"),
            "side_effect_concern": ("副作用", "不良反应", "担心", "side effect"),
            "symptoms_not_severe": ("症状不重", "不严重", "不疼", "symptom"),
        }
    elif step == "adverse_reaction_symptoms":
        mapping = {
            "gastrointestinal_discomfort": ("胃", "肠胃", "胃不舒服", "恶心", "heartburn", "stomach"),
            "dizziness_or_drowsiness": ("头晕", "嗜睡", "dizzy", "drows"),
            "skin_allergy": ("皮疹", "瘙痒", "过敏", "rash", "itch"),
            "liver_or_kidney_abnormality": ("肝", "肾", "liver", "kidney"),
            "edema_or_blood_pressure": ("水肿", "血压", "肿", "swelling", "blood pressure"),
        }
    elif step == "non_oral_treatments":
        if _parse_yes_no(text) == "no" or any(term in compact for term in ("没有其他", "未进行", "没做过")):
            return ["none"]
        mapping = {
            "topical_patch": ("膏药", "外敷", "patch"),
            "injection": ("注射", "打针", "玻璃酸钠", "injection"),
            "physical_therapy": ("理疗", "推拿", "按摩", "physical", "massage"),
            "exercise_therapy": ("康复训练", "运动", "游泳", "太极", "exercise"),
            "weight_management": ("减重", "体重", "weight"),
            "assistive_device": ("护膝", "护腕", "拐杖", "辅助器具", "呼吸", "brace", "cane"),
            "acupuncture_moxibustion": ("针灸", "艾灸", "acupuncture"),
        }
    elif step == "painkiller_channels":
        mapping = {
            "hospital_clinic": ("医院门诊", "门诊", "医院", "医生开", "医生给", "医生", "开给我", "开药", "hospital"),
            "community_hospital": ("社区", "community"),
            "retail_pharmacy": ("零售药店", "药店", "pharmacy"),
            "online_pharmacy": ("线上", "网上", "京东", "阿里", "叮当", "online"),
            "family_or_friend": ("家人", "朋友", "代买", "family", "friend"),
        }
    elif step == "retail_pharmacy_reasons":
        mapping = {
            "hospital_inconvenient": ("医院", "折腾", "费时间", "挂号", "inconvenient"),
            "nearby_pharmacy": ("附近", "家附近", "出门", "nearby"),
            "online_delivery": ("手机", "下单", "送货", "delivery"),
            "cheaper": ("便宜", "价格", "cheap"),
            "long_term_refill": ("常年", "续药", "长期", "refill"),
            "trust_formal": ("正规", "放心", "trust"),
            "staff_advice": ("工作人员", "药师", "建议", "advice"),
        }
    else:
        mapping = {}
    labels = [label for label, terms in mapping.items() if any(term in compact for term in terms)]
    if step == "painkiller_channels" and not labels and (_parse_yes_no(text) == "no" or any(term in compact for term in ("没买过", "未购买"))):
        return ["none"]
    if not labels and any(term in compact for term in ("其他", "other")):
        labels.append("other")
    return labels


def _parse_improvement(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text.lower())
    if any(term in compact for term in ("明显恶化", "muchworse", "markedlyworse")):
        return "markedly_worse"
    if any(term in compact for term in ("稍有恶化", "有点恶化", "slightlyworse")):
        return "slightly_worse"
    if any(term in compact for term in ("无变化", "没变化", "一样", "nochange")):
        return "no_change"
    if any(term in compact for term in ("明显改善", "明显好", "不疼了", "不疼", "管用", "有效", "吃一两颗就不疼", "markedlyimproved", "muchbetter")):
        return "markedly_improved"
    if any(term in compact for term in ("稍有改善", "有点改善", "好一点", "还行", "改善", "slightlyimproved", "abitbetter")):
        return "slightly_improved"
    return None


def _parse_willingness(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text.lower())
    conditional = any(term in compact for term in ("要不贵", "如果不贵", "贵", "太贵", "讹"))
    if conditional and any(term in compact for term in ("愿意", "不可能", "不吃")):
        return None
    if any(term in compact for term in ("不愿意", "不想", "不可能", "unwilling")):
        return "unwilling"
    if any(term in compact for term in ("无所谓", "都可以", "随便", "neutral")):
        return "neutral"
    if any(term in compact for term in ("愿意", "可以", "willing")):
        return "willing"
    return None


def _parse_doctor_counseling(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text.lower())
    if any(term in compact for term in ("完全没有", "没有讲", "noexplanation")):
        return "none"
    if any(term in compact for term in ("很少", "简单开药", "rare")):
        return "rarely_explained"
    if any(term in compact for term in ("大部分", "简单说", "brief")):
        return "brief_most_times"
    if any(term in compact for term in ("每次", "仔细", "detailed")):
        return "detailed_every_time"
    if compact in {"1", "一"}:
        return "detailed_every_time"
    if compact in {"2", "二", "两"}:
        return "brief_most_times"
    if compact in {"3", "三"}:
        return "rarely_explained"
    if compact in {"4", "四"}:
        return "none"
    return None


def _parse_purchase_method(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text.lower())
    if any(term in compact for term in ("新处方", "刚开", "newprescription")):
        return "new_prescription"
    if any(term in compact for term in ("旧处方", "留存", "重复", "oldprescription")):
        return "old_prescription_reuse"
    if any(term in compact for term in ("自己", "挑选", "不用处方", "self")):
        return "self_select_without_prescription"
    if any(term in compact for term in ("工作人员", "药师", "推荐", "staff")):
        return "staff_recommendation_without_prescription"
    return None


def _parse_guidance_frequency(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text.lower())
    if any(term in compact for term in ("从未", "没有", "never")):
        return "never"
    if any(term in compact for term in ("偶尔", "有时候", "occasionally", "sometimes")):
        return "occasionally"
    if any(term in compact for term in ("经常", "常常", "often", "frequent")):
        return "often"
    return None


def _survey_id_enabled() -> bool:
    return os.getenv("ASK_SURVEY_ID", "").strip().lower() in {"1", "true", "yes", "on"}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())
