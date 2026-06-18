from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.conversation import ConversationEngine


def run_routine_check_in() -> None:
    engine = ConversationEngine()
    state = engine.start()

    for message in (
        "My name is Mary Tan, my mobile is 91234567, and I am 72 years old.",
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
    assert state.report and "OA Home Pain Check-in Report" in state.report
    assert "Routine" in state.report or "High priority" in state.report


def run_red_flag_check_in() -> None:
    engine = ConversationEngine()
    state = engine.start()
    engine.handle_user_message(state, "My name is John Lee, phone 92345678, age 68.")
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
    engine.handle_user_message(state, "My name is Sara Lim, phone 93456789, age 70.")

    engine.handle_user_message(state, "coffee")
    assert state.step == "pain_score"
    assert "0 to 10" in state.transcript[-1]["text"]

    engine.handle_user_message(state, "hurts like")
    assert state.step == "pain_score"
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
        "My name is Peter Ong, phone 94567890, age 80.",
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


if __name__ == "__main__":
    run_routine_check_in()
    run_red_flag_check_in()
    run_validation_check_in()
    run_zero_worse_contradiction()
    print("Smoke tests passed.")
