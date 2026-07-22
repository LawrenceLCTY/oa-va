from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.conversation import ConversationEngine
from app.local_ai import LocalClinicalAI
from app.private_pipeline import PrivateVoicePipeline


class FakeSTT:
    def status(self):
        return {"enabled": True, "engine": "fake"}

    def transcribe(self, audio: bytes, filename: str, language: str):
        return None, "fake stt unavailable"


class FakeTTS:
    def status(self):
        return {"enabled": True, "engine": "fake"}


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
        fallback_text="CG260009",
    )

    assert result.transcript_source == "browser_transcript"
    assert state.questionnaire.answers["survey_id"]["value"] == "CG260009"
    assert state.step == "oa_diagnosis"
    assert "stt_ms" in result.timings
    assert "clinical_engine_ms" in result.timings
    assert state.model_events


def run_community_hospital_questionnaire() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")

    answers = (
        "CG260001",
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
    assert report["schema_version"] == "0.9.0"
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
        "CG260002",
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

    engine.handle_user_message(state, "CG260003")
    engine.handle_user_message(state, "我胸痛，还喘不上气")

    assert state.safety.red_flag_present
    assert "chest pain" in state.safety.red_flag_symptoms
    assert "trouble breathing" in state.safety.red_flag_symptoms
    assert not state.complete
    assert "急诊" in state.transcript[-1]["text"] or "急救" in state.transcript[-1]["text"]


def run_clarification_for_wrong_bucket() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")

    for answer in ("CG260004", "是", "膝关节", "两年", "昨天", "一天"):
        engine.handle_user_message(state, answer)

    assert state.step == "last_flare_pain_score"
    engine.handle_user_message(state, "挺疼的")
    assert state.step == "last_flare_pain_score"
    assert "0到10" in state.transcript[-1]["text"]


if __name__ == "__main__":
    run_local_ai_rule_fallback()
    run_private_pipeline_browser_transcript_fallback()
    run_community_hospital_questionnaire()
    run_retail_pharmacy_questionnaire()
    run_red_flag_interrupts_questionnaire()
    run_clarification_for_wrong_bucket()
    print("Smoke tests passed.")
