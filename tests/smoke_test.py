from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.conversation import ConversationEngine


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
    run_routine_check_in()
    run_red_flag_check_in()
    run_validation_check_in()
    run_zero_worse_contradiction()
    run_chinese_routine_check_in()
    run_chinese_validation_and_red_flag()
    run_side_effect_detail_check_in()
    print("Smoke tests passed.")
