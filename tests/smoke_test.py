from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.conversation import ConversationEngine
from app.local_ai import LocalClinicalAI
from app.openai_client import UnderstandingResult
from app.private_pipeline import PrivateVoicePipeline


class FakeSlotAI:
    def understand(self, step: str, language: str, patient_text: str) -> UnderstandingResult | None:
        if "恶心" in patient_text:
            return UnderstandingResult(
                accepted=True,
                confidence=0.9,
                answer_type="free_text",
                text_value=patient_text,
                slots={
                    "respondent_source": None,
                    "average_24h_score": None,
                    "current_pain_score": None,
                    "pain_location": None,
                    "functional_impact": None,
                    "usual_comparison": None,
                    "treatment_context": None,
                    "side_effect_screening_result": "yes",
                    "side_effect_description": "恶心",
                    "symptom_start_time": "昨天晚上",
                    "symptom_status": "ongoing",
                    "symptom_severity": "mild",
                    "medication_changed": "no",
                    "doctor_contacted": "no",
                    "emergency_visit_or_hospitalization": "no",
                },
                red_flags=[],
                non_urgent_concerns=["nausea"],
            )
        if "膝盖" not in patient_text:
            return None
        return UnderstandingResult(
            accepted=True,
            confidence=0.9,
            answer_type="free_text",
            text_value=patient_text,
            identity={"name": "刘敏", "mobile_number": "13500135000", "age": 74},
            slots={
                "respondent_source": "participant_independently",
                "average_24h_score": 6,
                "current_pain_score": 7,
                "pain_location": "右膝盖",
                "functional_impact": None,
                "usual_comparison": None,
                "treatment_context": None,
                "side_effect_screening_result": None,
                "side_effect_description": None,
                "symptom_start_time": None,
                "symptom_status": None,
                "symptom_severity": None,
                "medication_changed": None,
                "doctor_contacted": None,
                "emergency_visit_or_hospitalization": None,
            },
            red_flags=[],
            non_urgent_concerns=[],
        )

    def friendly_reply(self, language: str, clinical_message: str, recent_transcript=None) -> str | None:
        return None


class FakeClarifyingAI:
    def __init__(self) -> None:
        self.calls = []

    def understand(self, step: str, language: str, patient_text: str) -> UnderstandingResult | None:
        return None

    def friendly_reply(self, language: str, clinical_message: str, recent_transcript=None) -> str | None:
        return None

    def clarification_reply(
        self,
        language: str,
        step: str,
        patient_text: str,
        clinical_prompt: str,
        reason: str,
        recent_transcript=None,
    ) -> str | None:
        self.calls.append((language, step, patient_text, clinical_prompt, reason))
        return "I hear that it feels bad. To record it consistently, please choose a number from 0 to 10."


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
    result = ai.understand("side_effects", "en", "I have chest pain and shortness of breath")

    assert result is not None
    assert "chest pain" in (result.red_flags or [])
    assert "trouble breathing" in (result.red_flags or [])
    assert ai.trace_events
    assert ai.trace_events[-1]["fallback"] == "rule_only_after_model_failure"


def run_private_pipeline_browser_transcript_fallback() -> None:
    engine = ConversationEngine()
    pipeline = PrivateVoicePipeline(engine, FakeSTT(), FakeTTS())
    state = engine.start(language="en")
    result = pipeline.process_turn(
        state,
        b"fake audio",
        filename="speech.webm",
        language="en",
        fallback_text="My name is Mary Tan, my mobile is 91234567, and I am 72 years old.",
    )

    assert result.transcript_source == "browser_transcript"
    assert state.identity.name == "Mary Tan"
    assert state.step == "respondent_source"
    assert "stt_ms" in result.timings
    assert "clinical_engine_ms" in result.timings
    assert state.model_events
    assert state.model_events[-1]["transcript_source"] == "browser_transcript"


def run_identity_phone_age_split() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")
    engine.handle_user_message(state, "王大明 01234567890 50")

    assert state.identity.name == "王大明"
    assert state.identity.mobile_number == "01234567890"
    assert state.identity.age == 50


def run_pinyin_comparison_and_unclear_treatment() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")
    for message in (
        "王大明 01234567890 50",
        "自己",
        "5",
        "5",
        "膝盖",
        "睡觉",
        "chabuduo",
    ):
        engine.handle_user_message(state, message)

    assert state.pain.usual_comparison == "same"
    assert state.step == "treatment_context"

    engine.handle_user_message(state, "不懂")
    assert state.step == "treatment_context"
    assert state.safety.medication_context is None


def run_natural_start_check_in() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")

    assert state.step == "identity"
    assert state.readiness["hearing_clear"] == "assumed"
    assert "听清楚" not in state.transcript[-1]["text"]

    engine.handle_user_message(state, "我叫陈芳，手机号是13600136000，年龄73岁")
    assert state.identity.name == "陈芳"
    assert state.step == "respondent_source"

    for text in (
        "王丽，手机号13800138000，72岁",
        "姓名王丽 手机号13800138000 年龄72岁",
        "王丽 13800138000 72岁",
    ):
        state = engine.start(language="zh-CN")
        engine.handle_user_message(state, text)
        assert state.identity.name == "王丽"
        assert state.identity.mobile_number == "13800138000"
        assert state.identity.age == 72
        assert state.step == "respondent_source"


def run_llm_slot_filling_check_in() -> None:
    engine = ConversationEngine(ai=FakeSlotAI())
    state = engine.start(language="zh-CN")

    engine.handle_user_message(state, "我是刘敏，手机号13500135000，74岁，自己答。过去一天六分，现在七分，右膝盖疼。")

    assert state.identity.name == "刘敏"
    assert state.respondent_source == "participant_independently"
    assert state.pain.average_24h_score == 6
    assert state.pain.score == 7
    assert state.pain.location == "右膝盖"
    assert state.step == "functional_impact"
    assert "影响" in state.transcript[-1]["text"] or "活动" in state.transcript[-1]["text"]

    state.step = "side_effects"
    state.safety.side_effect_screening_result = "unknown"
    engine.handle_user_message(state, "有点恶心，昨天晚上开始的，现在还有，轻微，没有停药，没联系医生，也没去急诊。")

    assert state.safety.side_effect_screening_result == "yes"
    assert "恶心" in state.safety.reported_symptoms
    assert state.safety.symptom_start_time == "昨天晚上"
    assert state.safety.symptom_status == "ongoing"
    assert state.safety.symptom_severity == "mild"
    assert state.safety.medication_changed == "no"
    assert state.safety.doctor_contacted == "no"
    assert state.safety.emergency_visit_or_hospitalization == "no"
    assert state.step == "red_flags"


def run_llm_guided_clarification() -> None:
    ai = FakeClarifyingAI()
    engine = ConversationEngine(ai=ai)
    state = engine.start()
    state.step = "current_pain_score"

    engine.handle_user_message(state, "It is pretty bad today")

    assert state.step == "current_pain_score"
    assert ai.calls
    assert ai.calls[-1][1] == "current_pain_score"
    assert "feels bad" in state.transcript[-1]["text"]


def run_routine_check_in() -> None:
    engine = ConversationEngine()
    state = engine.start()

    for message in (
        "yes",
        "yes",
        "yes",
        "My name is Mary Tan, my mobile is 91234567, and I am 72 years old.",
        "participant alone",
        "Four",
        "Five",
        "My right knee",
        "It makes climbing stairs slow but I can still walk at home.",
        "About the same",
        "I use paracetamol and a pain relief cream.",
        "No side effects.",
        "No.",
    ):
        engine.handle_user_message(state, message)

    assert state.complete
    assert state.identity.name == "Mary Tan"
    assert state.identity.mobile_number == "91234567"
    assert state.identity.age == 72
    assert state.pain.score == 5
    assert not state.safety.red_flag_present
    report = json.loads(state.report or "{}")
    assert report["report_type"] == "oa_home_pain_check_in"
    assert report["patient_identity"]["name"] == "Mary Tan"
    assert report["pain_assessment"]["current_score"] == 5
    assert report["safety_assessment"]["red_flag_present"] is False
    assert report["suggested_follow_up_priority"].startswith(("Routine", "High priority"))


def run_red_flag_check_in() -> None:
    engine = ConversationEngine()
    state = engine.start()
    for message in ("yes", "yes", "yes", "My name is John Lee, phone 92345678, age 68.", "participant alone", "7"):
        engine.handle_user_message(state, message)
    engine.handle_user_message(state, "8")
    engine.handle_user_message(state, "left hip")
    engine.handle_user_message(state, "I need help standing")
    engine.handle_user_message(state, "worse")
    engine.handle_user_message(state, "ibuprofen")
    engine.handle_user_message(state, "I have chest pain and shortness of breath")

    assert state.safety.red_flag_present
    assert "chest pain" in state.safety.red_flag_symptoms
    assert "trouble breathing" in state.safety.red_flag_symptoms
    assert not state.complete
    assert "urgent medical" in state.transcript[-1]["text"].lower()


def run_validation_check_in() -> None:
    engine = ConversationEngine()
    state = engine.start()
    for message in ("yes", "yes", "yes", "My name is Sara Lim, phone 93456789, age 70.", "participant alone", "3"):
        engine.handle_user_message(state, message)

    engine.handle_user_message(state, "coffee")
    assert state.step == "current_pain_score"
    assert "0 to 10" in state.transcript[-1]["text"]

    engine.handle_user_message(state, "hurts like")
    assert state.step == "current_pain_score"
    assert "What number" in state.transcript[-1]["text"] or "0 to 10" in state.transcript[-1]["text"]

    engine.handle_user_message(state, "0")
    assert state.step == "pain_location"
    engine.handle_user_message(state, "knee")
    assert state.step == "functional_impact"

    engine.handle_user_message(state, "I cannot walk and need help")
    assert state.step == "functional_impact"
    assert state.pending_clarification == "pain_zero_after_function"
    assert "zero pain" in state.transcript[-1]["text"].lower()

    engine.handle_user_message(state, "7")
    assert state.pain.score == 7
    assert state.step == "functional_impact"

    engine.handle_user_message(state, "I need help walking")
    engine.handle_user_message(state, "coffee")
    assert state.step == "usual_comparison"
    assert "better" in state.transcript[-1]["text"].lower()

    engine.handle_user_message(state, "worse")
    engine.handle_user_message(state, "no")
    engine.handle_user_message(state, "coffee")
    assert state.step == "side_effects"
    assert "side effects" in state.transcript[-1]["text"].lower()


def run_vas_binary_calibration() -> None:
    engine = ConversationEngine()
    state = engine.start()

    for message in (
        "yes",
        "yes",
        "yes",
        "My name is Ravi Tan, phone 95678901, age 76.",
        "participant alone",
    ):
        engine.handle_user_message(state, message)

    assert state.step == "average_pain_score"
    assert state.pain.active_vas_period == "average_24h"
    assert "closer to" in state.transcript[-1]["text"].lower()

    for message in ("higher", "lower", "higher"):
        engine.handle_user_message(state, message)

    assert state.pain.average_24h_score == 8
    assert state.pain.average_24h_score_confirmed
    assert len(state.pain.average_24h_vas_trace) == 3
    assert state.step == "current_pain_score"

    for message in ("lower", "higher", "lower", "lower"):
        engine.handle_user_message(state, message)

    assert state.pain.score == 3
    assert state.pain.current_score_confirmed
    assert len(state.pain.current_vas_trace) == 4
    assert state.step == "pain_location"

    for message in (
        "right knee",
        "It slows me on stairs.",
        "same",
        "paracetamol",
        "no",
        "no",
    ):
        engine.handle_user_message(state, message)

    assert state.complete
    report = json.loads(state.report or "{}")
    assert report["pain_assessment"]["average_24h_score"] == 8
    assert report["pain_assessment"]["current_score"] == 3
    assert len(report["pain_assessment"]["average_24h_vas_trace"]) == 3
    assert len(report["pain_assessment"]["current_vas_trace"]) == 4


def run_zero_worse_contradiction() -> None:
    engine = ConversationEngine()
    state = engine.start()
    for message in (
        "yes",
        "yes",
        "yes",
        "My name is Peter Ong, phone 94567890, age 80.",
        "participant alone",
        "0",
        "0",
        "hip",
        "No problem walking",
    ):
        engine.handle_user_message(state, message)

    engine.handle_user_message(state, "worse")
    assert state.step == "usual_comparison"
    assert state.pending_clarification == "pain_zero_after_worse"
    assert "zero pain" in state.transcript[-1]["text"].lower()

    engine.handle_user_message(state, "4")
    assert state.pain.score == 4
    assert state.pain.usual_comparison == "worse"
    assert state.step == "treatment_context"


def run_chinese_routine_check_in() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")
    assert state.language == "zh-CN"
    assert any("北京大学" in item["text"] for item in state.transcript)

    for message in (
        "有",
        "有",
        "有",
        "我叫王丽，手机号是13800138000，年龄72岁",
        "本人回答",
        "四分",
        "五分",
        "右膝盖",
        "上下楼有点困难",
        "差不多",
        "吃止痛药，也贴膏药",
        "没有",
        "没有",
    ):
        engine.handle_user_message(state, message)

    assert state.complete
    assert state.identity.name == "王丽"
    assert state.identity.mobile_number == "13800138000"
    assert state.identity.age == 72
    assert state.pain.score == 5
    assert not state.safety.red_flag_present
    report = json.loads(state.report or "{}")
    assert report["session"]["language"] == "zh-CN"
    assert report["patient_identity"]["name"] == "王丽"
    assert report["pain_assessment"]["current_score"] == 5


def run_chinese_validation_and_red_flag() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")
    for message in ("有", "有", "有", "我叫李强，手机号13900139000，年龄68岁", "本人回答", "7"):
        engine.handle_user_message(state, message)

    engine.handle_user_message(state, "咖啡")
    assert state.step == "current_pain_score"
    assert "0到10" in state.transcript[-1]["text"]

    engine.handle_user_message(state, "疼死了")
    assert state.step == "current_pain_score"
    assert "0到10" in state.transcript[-1]["text"]

    for message in (
        "8",
        "左髋",
        "走路需要人扶",
        "重了",
        "布洛芬",
    ):
        engine.handle_user_message(state, message)

    engine.handle_user_message(state, "我胸痛，还喘不上气")
    assert state.safety.red_flag_present
    assert "chest pain" in state.safety.red_flag_symptoms
    assert "trouble breathing" in state.safety.red_flag_symptoms
    assert "急诊" in state.transcript[-1]["text"] or "急救" in state.transcript[-1]["text"]


def run_side_effect_detail_check_in() -> None:
    engine = ConversationEngine()
    state = engine.start(language="zh-CN")
    for message in (
        "有",
        "有",
        "有",
        "我叫赵敏，手机号13700137000，年龄75岁",
        "家属帮忙",
        "6",
        "7",
        "膝盖",
        "走路慢",
        "重了",
        "布洛芬",
        "有",
        "恶心和头晕",
        "昨天晚上",
        "还在",
        "重度",
        "停药了",
        "联系了医生",
        "去了急诊",
        "没有",
    ):
        engine.handle_user_message(state, message)

    assert state.complete
    assert state.respondent_source == "participant_with_caregiver_assistance"
    assert state.safety.side_effect_screening_result == "yes"
    assert state.safety.symptom_start_time == "昨天晚上"
    assert state.safety.symptom_status == "ongoing"
    assert state.safety.symptom_severity == "severe"
    assert state.safety.medication_changed == "yes"
    assert state.safety.doctor_contacted == "yes"
    assert state.safety.emergency_visit_or_hospitalization == "yes"
    assert state.safety.researcher_alert_required
    report = json.loads(state.report or "{}")
    assert report["safety_assessment"]["researcher_alert_required"] is True
    assert "需要研究人员跟进" in report["suggested_follow_up_priority"]


if __name__ == "__main__":
    run_local_ai_rule_fallback()
    run_private_pipeline_browser_transcript_fallback()
    run_identity_phone_age_split()
    run_pinyin_comparison_and_unclear_treatment()
    run_natural_start_check_in()
    run_llm_slot_filling_check_in()
    run_llm_guided_clarification()
    os.environ["STRICT_READINESS_FLOW"] = "1"
    try:
        run_routine_check_in()
        run_red_flag_check_in()
        run_validation_check_in()
        run_vas_binary_calibration()
        run_zero_worse_contradiction()
        run_chinese_routine_check_in()
        run_chinese_validation_and_red_flag()
        run_side_effect_detail_check_in()
    finally:
        os.environ.pop("STRICT_READINESS_FLOW", None)
    print("Smoke tests passed.")
