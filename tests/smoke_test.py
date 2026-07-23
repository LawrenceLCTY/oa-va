from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.conversation import ConversationEngine
from app.local_ai import LocalClinicalAI
from app.private_pipeline import PrivateVoicePipeline
from app.questionnaire import parse_questionnaire_answer, questionnaire_step_schema, validate_questionnaire_interpretation
from app.stt import sanitize_transcript
from app.tts import _clean_text
from app.version import SCHEMA_VERSION


class FakeSTT:
    def status(self):
        return {"enabled": True, "engine": "fake"}

    def transcribe(self, audio: bytes, filename: str, language: str):
        return None, "fake stt unavailable"


class MetadataSTT:
    def status(self):
        return {"enabled": True, "engine": "metadata-fake"}

    def transcribe(self, audio: bytes, filename: str, language: str):
        return "<|zh|><|NEUTRAL|><|Speech|><|withitn|>。", None


class SlowFailingSTT:
    def __init__(self):
        self.called = False

    def status(self):
        return {"enabled": True, "engine": "slow-fake"}

    def transcribe(self, audio: bytes, filename: str, language: str):
        self.called = True
        return None, "should not be called when browser transcript exists"


class FakeTTS:
    def status(self):
        return {"enabled": True, "engine": "fake"}


class SemanticAI:
    def __init__(self, interpretation):
        self.interpretation = interpretation
        self.calls = []
        self.trace_events = []

    def understand(self, step: str, language: str, patient_text: str):
        return None

    def interpret_questionnaire_turn(self, **kwargs):
        self.calls.append(kwargs)
        return self.interpretation

    def friendly_reply(self, language: str, clinical_message: str, recent_transcript=None):
        return None

    def clarification_reply(
        self,
        language: str,
        step: str,
        patient_text: str,
        clinical_prompt: str,
        reason: str,
        recent_transcript=None,
    ):
        return None


def run_tts_internal_instruction_stripping() -> None:
    text = (
        "Say this next required clinical line naturally and briefly. "
        "The clinical intent is: collect affected joints. "
        "Required line: 主要疼痛或不适的关节是哪些？"
    )
    assert _clean_text(text) == "主要疼痛或不适的关节是哪些？"
    assert _clean_text("You are a helper<|endofprompt|>请回答。") == "You are a helper 请回答。"


def run_local_ai_rule_fallback() -> None:
    ai = LocalClinicalAI()
    ai.url = "http://127.0.0.1:9/v1/chat/completions"
    result = ai.understand("red_flags", "en", "I have chest pain and shortness of breath")

    assert result is not None
    assert "chest pain" in (result.red_flags or [])
    assert "trouble breathing" in (result.red_flags or [])
    assert ai.trace_events
    assert ai.trace_events[-1]["fallback"] == "rule_only_after_model_failure"


def run_private_pipeline_browser_transcript_fallback() -> None:
    engine = ConversationEngine()
    pipeline = PrivateVoicePipeline(engine, FakeSTT(), FakeTTS())
    state = engine.start(language="zh-CN")
    result = pipeline.process_turn(
        state,
        b"fake audio",
        filename="speech.webm",
        language="zh-CN",
        fallback_text="是",
    )

    assert result.transcript_source == "browser_transcript"
    assert state.questionnaire.answers["oa_diagnosis"]["value"] == "yes"
    assert state.step == "affected_joints"
    assert "stt_ms" in result.timings
    assert "clinical_engine_ms" in result.timings
    assert state.model_events


def run_private_pipeline_uses_browser_transcript_before_local_stt() -> None:
    engine = ConversationEngine()
    stt = SlowFailingSTT()
    pipeline = PrivateVoicePipeline(engine, stt, FakeTTS())
    state = engine.start(language="zh-CN")

    result = pipeline.process_turn(
        state,
        b"fake audio",
        filename="speech.webm",
        language="zh-CN",
        fallback_text="是",
    )

    assert result.transcript_source == "browser_transcript"
    assert stt.called is False
    assert state.questionnaire.answers["oa_diagnosis"]["value"] == "yes"


def run_metadata_stt_rejected_without_state_advance() -> None:
    assert sanitize_transcript("<|zh|><|NEUTRAL|><|Speech|><|withitn|>。") == ""
    engine = ConversationEngine()
    pipeline = PrivateVoicePipeline(engine, MetadataSTT(), FakeTTS())
    state = engine.start(language="zh-CN")
    initial_step = state.step
    initial_answers = dict(state.questionnaire.answers)
    result = pipeline.process_turn(
        state,
        b"fake audio",
        filename="speech.webm",
        language="zh-CN",
        fallback_text="",
    )

    assert result.transcript == ""
    assert result.assistant_messages
    assert state.step == initial_step
    assert state.questionnaire.answers == initial_answers
    assert state.model_events[-1]["errors"]


def run_metadata_stt_prefers_clean_browser_transcript() -> None:
    engine = ConversationEngine()
    pipeline = PrivateVoicePipeline(engine, MetadataSTT(), FakeTTS())
    state = engine.start(language="zh-CN")
    result = pipeline.process_turn(
        state,
        b"fake audio",
        filename="speech.webm",
        language="zh-CN",
        fallback_text="是",
    )

    assert result.transcript == "是"
    assert result.transcript_source == "browser_transcript"
    assert state.questionnaire.answers["oa_diagnosis"]["value"] == "yes"


def run_reported_dumb_section_parser_regressions() -> None:
    accepted, _, reason = parse_questionnaire_answer("oa_diagnosis", "好，这里是")
    assert not accepted
    assert reason == "unclear_yes_no"
    accepted, _, reason = parse_questionnaire_answer("oa_diagnosis", "也就一下子我不做工，他就不疼了")
    assert not accepted
    assert reason == "unclear_yes_no"

    accepted, _, reason = parse_questionnaire_answer("adverse_reactions", "吃了就不疼了")
    assert not accepted
    assert reason == "unclear_yes_no"

    accepted, payload, _ = parse_questionnaire_answer("pain_improvement_after_meds", "还行吧，就有时候基本上吃一两颗就不疼了")
    assert accepted
    assert payload["value"] == "markedly_improved"

    accepted, _, reason = parse_questionnaire_answer("pain_improvement_after_meds", "改善哎，你这本就不大聪明了呀")
    assert not accepted
    assert reason == "user_feedback_not_answer"

    accepted, payload, _ = parse_questionnaire_answer("painkiller_channels", "没有没有，我没有补药，我就当医生开给我")
    assert accepted
    assert "hospital_clinic" in payload["values"]
    assert "none" not in payload["values"]

    accepted, _, reason = parse_questionnaire_answer(
        "consolidation_medication_willingness",
        "要不贵就愿意呗，如果贵得要死我怎么可能吃",
    )
    assert not accepted
    assert reason == "unclear_choice"


def run_v093_fuzzy_semantic_interpretation() -> None:
    accepted, payload, _ = parse_questionnaire_answer("oa_diagnosis", "医生说我这是骨关节炎")
    assert accepted
    assert payload["value"] == "yes"
    assert payload["interpretation"]["strategy"] == "fuzzy_diagnosis_evidence"
    assert payload["interpretation"]["fuzzy"] is True

    accepted, payload, _ = parse_questionnaire_answer("pain_improvement_after_meds", "还行吧，吃一两颗就不疼了")
    assert accepted
    assert payload["value"] == "markedly_improved"
    assert payload["interpretation"]["strategy"] == "fuzzy_effect_description"
    assert payload["interpretation"]["confidence"] >= 0.8

    accepted, _, reason = parse_questionnaire_answer("pain_improvement_after_meds", "改善哎，你这本就不大聪明了呀")
    assert not accepted
    assert reason == "user_feedback_not_answer"

    accepted, payload, _ = parse_questionnaire_answer("painkiller_channels", "医生开给我的")
    assert accepted
    assert payload["values"] == ["hospital_clinic"]
    assert payload["interpretation"]["strategy"] == "fuzzy_doctor_channel"

    accepted, _, reason = parse_questionnaire_answer("adverse_reactions", "吃了就不疼了")
    assert not accepted
    assert reason == "unclear_yes_no"

    accepted, _, reason = parse_questionnaire_answer("consolidation_medication_willingness", "要是不贵就愿意，贵了就不吃")
    assert not accepted
    assert reason == "unclear_choice"


def run_v095_ai_interpreter_first_for_questionnaire() -> None:
    ai = SemanticAI(
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": "yes", "values": [], "other_text": None},
            "confidence": 0.91,
            "evidence": "医生说我这是骨关节炎",
            "reason": "doctor diagnosis evidence answers the current diagnosis question",
            "clarification_prompt": None,
            "safety_flags": [],
        }
    )
    engine = ConversationEngine(ai=ai)
    state = engine.start(language="zh-CN")

    engine.handle_user_message(state, "医生说我这是骨关节炎")

    assert ai.calls
    assert ai.calls[0]["step"] == "oa_diagnosis"
    assert ai.calls[0]["question"] == "您是否被医生明确诊断为骨关节炎？"
    assert ai.calls[0]["schema"]["allowed_values"] == ["yes", "no"]
    answer = state.questionnaire.answers["oa_diagnosis"]
    assert answer["value"] == "yes"
    assert answer["interpretation"]["strategy"] == "ai_semantic_interpreter"
    assert state.step == "affected_joints"


def run_v095_direct_literal_still_uses_qwen_gate() -> None:
    ai = SemanticAI(
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": "yes", "values": [], "other_text": None},
            "confidence": 0.94,
            "evidence": "是",
            "reason": "direct yes answer",
            "clarification_prompt": None,
            "safety_flags": [],
        }
    )
    engine = ConversationEngine(ai=ai)
    state = engine.start(language="zh-CN")

    engine.handle_user_message(state, "是")

    assert ai.calls
    answer = state.questionnaire.answers["oa_diagnosis"]
    assert answer["value"] == "yes"
    assert answer["interpretation"]["strategy"] == "ai_semantic_interpreter"


def run_v095_qwen_timeout_fallback_is_audited() -> None:
    ai = SemanticAI(None)
    engine = ConversationEngine(ai=ai)
    state = engine.start(language="zh-CN")

    engine.handle_user_message(state, "是")

    assert ai.calls
    answer = state.questionnaire.answers["oa_diagnosis"]
    assert answer["value"] == "yes"
    assert answer["interpretation"]["semantic_gate"] == "semantic_gate_unavailable_or_timeout"
    assert answer["interpretation"]["needs_review"] is True
    assert answer["interpretation"]["confidence"] <= 0.6



def run_v095_ai_non_answer_blocks_rule_fallback() -> None:
    ai = SemanticAI(
        {
            "turn_type": "complaint",
            "answers_current_question": False,
            "normalized": {"value": None, "values": [], "other_text": None},
            "confidence": 0.9,
            "evidence": "医生说我这是骨关节炎",
            "reason": "patient is not answering the current question",
            "clarification_prompt": None,
            "safety_flags": [],
        }
    )
    engine = ConversationEngine(ai=ai)
    state = engine.start(language="zh-CN")

    engine.handle_user_message(state, "医生说我这是骨关节炎")

    assert ai.calls
    assert state.step == "oa_diagnosis"
    assert "oa_diagnosis" not in state.questionnaire.answers


def run_v095_ai_schema_validation_blocks_invalid_normalized_answer() -> None:
    ai = SemanticAI(
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": "maybe", "values": [], "other_text": None},
            "confidence": 0.95,
            "evidence": "医生说我这是骨关节炎",
            "reason": "invalid canonical yes/no value",
            "clarification_prompt": None,
            "safety_flags": [],
        }
    )
    engine = ConversationEngine(ai=ai)
    state = engine.start(language="zh-CN")

    engine.handle_user_message(state, "医生说我这是骨关节炎")

    assert state.step == "oa_diagnosis"
    assert "oa_diagnosis" not in state.questionnaire.answers


def run_v095_anchored_pain_score_prompt_and_validation() -> None:
    schema = questionnaire_step_schema("last_flare_pain_score", "zh-CN")
    assert "轻度疼痛" in schema["pain_anchor_rubric"]["anchors"][1]["label"]
    assert "不影响睡眠" in schema["question"]
    assert "安静平卧" in schema["question"]

    accepted, payload, reason = validate_questionnaire_interpretation(
        "last_flare_pain_score",
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": "轻度", "values": [], "other_text": None},
            "confidence": 0.86,
            "evidence": "不影响睡眠，走路有点僵硬",
            "reason": "anchor-based mild pain placement",
        },
        "不影响睡眠，走路有点僵硬",
    )
    assert accepted, reason
    assert payload["value"] == 2
    assert payload["method"] == "ai_semantic_anchor_based"

    accepted, payload, reason = validate_questionnaire_interpretation(
        "last_flare_pain_score",
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": "4到6", "values": [], "other_text": None},
            "confidence": 0.86,
            "evidence": "有点影响睡眠，平卧有时候疼",
            "reason": "anchor-based moderate pain placement",
        },
        "有点影响睡眠，平卧有时候疼",
    )
    assert accepted, reason
    assert payload["value"] == 5
    assert payload["method"] == "ai_semantic_anchor_based"


def run_v095_ai_schema_guides_basic_fuzzy_outputs() -> None:
    schema = questionnaire_step_schema("affected_joints", "zh-CN")
    assert {item["value"] for item in schema["options"]} >= {"knee", "hip", "hand", "foot", "shoulder", "other"}
    assert any(item["zh"] == "膝关节" for item in schema["options"])

    accepted, payload, reason = validate_questionnaire_interpretation(
        "oa_diagnosis",
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": "是", "values": [], "other_text": None},
            "confidence": 0.9,
            "evidence": "是",
            "reason": "direct Chinese yes",
        },
        "是",
    )
    assert accepted, reason
    assert payload["value"] == "yes"

    accepted, payload, reason = validate_questionnaire_interpretation(
        "affected_joints",
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": None, "values": ["膝盖"], "other_text": None},
            "confidence": 0.9,
            "evidence": "膝盖疼",
            "reason": "colloquial knee label",
        },
        "膝盖疼",
    )
    assert accepted, reason
    assert payload["values"] == ["knee"]

    accepted, payload, reason = validate_questionnaire_interpretation(
        "last_flare_pain_score",
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": "三分", "values": [], "other_text": None},
            "confidence": 0.9,
            "evidence": "三分",
            "reason": "Chinese score phrase",
        },
        "三分",
    )
    assert accepted, reason
    assert payload["value"] == 3

    accepted, payload, reason = validate_questionnaire_interpretation(
        "painkiller_channels",
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": None, "values": ["医生开给我的"], "other_text": None},
            "confidence": 0.9,
            "evidence": "医生开给我的",
            "reason": "fuzzy hospital channel",
        },
        "医生开给我的",
    )
    assert accepted, reason
    assert payload["values"] == ["hospital_clinic"]


def run_v095_ai_chinese_choice_labels_are_validated() -> None:
    accepted, payload, reason = validate_questionnaire_interpretation(
        "pain_improvement_after_meds",
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": "明显改善", "values": [], "other_text": None},
            "confidence": 0.9,
            "evidence": "明显改善",
            "reason": "direct Chinese option label",
        },
        "明显改善",
    )

    assert accepted, reason
    assert payload["value"] == "markedly_improved"
    assert payload["interpretation"]["strategy"] == "ai_semantic_interpreter"


def run_v095_questionnaire_step_uses_single_qwen_gate() -> None:
    ai = SemanticAI(
        {
            "turn_type": "answer",
            "answers_current_question": True,
            "normalized": {"value": "明显改善", "values": [], "other_text": None},
            "confidence": 0.9,
            "evidence": "明显改善",
            "reason": "direct Chinese option label",
        }
    )
    engine = ConversationEngine(ai=ai)
    state = engine.start(language="zh-CN")
    state.step = "pain_improvement_after_meds"

    engine.handle_user_message(state, "明显改善")

    assert ai.calls
    assert len(ai.calls) == 1
    assert state.questionnaire.answers["pain_improvement_after_meds"]["value"] == "markedly_improved"



def run_community_hospital_questionnaire() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")

    answers = (
        "是",
        "膝关节",
        "三十多年",
        "半年前",
        "持续六个月",
        "三分",
        "一两次",
        "先自行吃止痛药，效果不好再去医院",
        "是",
        "双氯芬酸",
        "不能严格遵从医嘱，疼了才吃",
        "不会",
        "会，疼痛好转后就停药",
        "是，坚持按时按量困难",
        "没有不良反应",
        "稍有改善",
        "稍有改善",
        "不愿意",
        "外敷膏药，注射治疗，偶尔用护膝",
        "社区医院",
        "很少讲解，只是简单开药",
        "没有",
    )
    for answer in answers:
        engine.handle_user_message(state, answer)

    assert state.complete
    report = json.loads(state.report or "{}")
    q = report["questionnaire_response"]
    assert report["report_type"] == "oa_medication_treatment_questionnaire"
    assert report["schema_version"] == SCHEMA_VERSION
    assert q["completion"]["complete"] is True
    assert q["answers"]["affected_joints"]["values"] == ["knee"]
    assert q["answers"]["oral_painkiller_name"]["value"] == "双氯芬酸"
    assert q["answers"]["doctor_counseling"]["value"] == "rarely_explained"
    assert q["skipped"]["retail_pharmacy_purchase_method"] == "not_applicable_by_prior_answer"
    assert report["safety_assessment"]["red_flag_present"] is False


def run_retail_pharmacy_questionnaire() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")

    answers = (
        "是",
        "膝关节和手部关节",
        "五年",
        "上周",
        "三天",
        "六分",
        "超过十次",
        "先自行买止痛药",
        "是",
        "布洛芬",
        "能遵从医嘱",
        "会忘记",
        "不会好转后自行停药",
        "否，不困难",
        "记性差，也担心副作用",
        "有",
        "肠胃不适，头晕嗜睡",
        "明显改善",
        "稍有改善",
        "愿意",
        "外敷膏药和运动康复",
        "零售药店，也会线上药房",
        "家附近有药店，价格便宜，工作人员会给建议",
        "不用处方，自己根据疼痛情况挑选药品",
        "偶尔",
        "经常",
        "从未",
        "偶尔",
        "没有",
    )
    for answer in answers:
        engine.handle_user_message(state, answer)

    assert state.complete
    report = json.loads(state.report or "{}")
    q = report["questionnaire_response"]
    assert q["completion"]["complete"] is True
    assert set(q["answers"]["affected_joints"]["values"]) == {"knee", "hand"}
    assert "retail_pharmacy" in q["answers"]["painkiller_channels"]["values"]
    assert "online_pharmacy" in q["answers"]["painkiller_channels"]["values"]
    assert q["answers"]["retail_pharmacy_purchase_method"]["value"] == "self_select_without_prescription"
    assert q["answers"]["pharmacy_guidance_dosage"]["value"] == "often"
    assert q["answers"]["pharmacy_guidance_avoid_multiple_painkillers"]["value"] == "never"
    assert "doctor_counseling" in q["skipped"]


def run_red_flag_interrupts_questionnaire() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")

    engine.handle_user_message(state, "我胸痛，还喘不上气")

    assert state.safety.red_flag_present
    assert "chest pain" in state.safety.red_flag_symptoms
    assert "trouble breathing" in state.safety.red_flag_symptoms
    assert not state.complete
    assert "急诊" in state.transcript[-1]["text"] or "急救" in state.transcript[-1]["text"]


def run_reference_style_transcript_replay() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")

    answers = (
        "是",
        "膝关节",
        "持续了三十多年",
        "大概半年前",
        "持续了六个月",
        "轻度，不影响睡眠，走路有点僵硬",
        "一两次",
        "先自行吃止痛药，效果不好再去医院",
        "吃过",
        "双氯芬酸",
        "不能严格遵从医嘱，疼了才吃",
        "不会忘记服药",
        "会，疼痛好转后就停药",
        "是，坚持按时按量困难",
        "没有不良反应",
        "稍有改善",
        "稍有改善",
        "不愿意",
        "外敷膏药，关节腔注射，偶尔用护膝",
        "社区医院",
        "很少讲解，只是简单开药",
        "没有",
    )
    for answer in answers:
        engine.handle_user_message(state, answer)

    assert state.complete
    report = json.loads(state.report or "{}")
    q = report["questionnaire_response"]
    assert q["answers"]["last_flare_pain_score"]["method"] == "qualitative_anchor"
    assert q["answers"]["last_flare_pain_score"]["value"] == 2
    assert q["answers"]["annual_flare_frequency"]["value"] == "1-2"
    assert q["answers"]["oral_painkiller_name"]["value"] == "双氯芬酸"
    assert q["answers"]["doctor_counseling"]["value"] == "rarely_explained"
    assert q["skipped"]["retail_pharmacy_purchase_method"] == "not_applicable_by_prior_answer"
    metrics = report["conversation_trace"]["quality_metrics"]
    assert metrics["fuzzy_answer_count"] >= 1
    assert metrics["interpretation_review_count"] >= 1


def run_clarification_for_wrong_bucket() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")

    for answer in ("是", "膝关节", "两年", "昨天", "一天"):
        engine.handle_user_message(state, answer)

    assert state.step == "last_flare_pain_score"
    engine.handle_user_message(state, "挺疼的")
    assert state.step == "last_flare_pain_score"
    assert "0到10" in state.transcript[-1]["text"]


if __name__ == "__main__":
    run_tts_internal_instruction_stripping()
    run_local_ai_rule_fallback()
    run_private_pipeline_browser_transcript_fallback()
    run_private_pipeline_uses_browser_transcript_before_local_stt()
    run_metadata_stt_rejected_without_state_advance()
    run_metadata_stt_prefers_clean_browser_transcript()
    run_reported_dumb_section_parser_regressions()
    run_v093_fuzzy_semantic_interpretation()
    run_v095_ai_interpreter_first_for_questionnaire()
    run_v095_direct_literal_still_uses_qwen_gate()
    run_v095_qwen_timeout_fallback_is_audited()
    run_v095_ai_non_answer_blocks_rule_fallback()
    run_v095_ai_schema_validation_blocks_invalid_normalized_answer()
    run_v095_anchored_pain_score_prompt_and_validation()
    run_v095_ai_schema_guides_basic_fuzzy_outputs()
    run_v095_ai_chinese_choice_labels_are_validated()
    run_v095_questionnaire_step_uses_single_qwen_gate()
    run_community_hospital_questionnaire()
    run_retail_pharmacy_questionnaire()
    run_red_flag_interrupts_questionnaire()
    run_reference_style_transcript_replay()
    run_clarification_for_wrong_bucket()
    print("Smoke tests passed.")
