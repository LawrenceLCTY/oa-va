from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.clinical_rules import detect_symptoms
from app.pain_scale import comparison_from_text, parse_pain_score
from app.schemas import ConversationState


class ValidationAction(str, Enum):
    ACCEPT = "accept"
    ASK_AGAIN = "ask_again"
    CLARIFY = "clarify"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class ValidationResult:
    action: ValidationAction
    confidence: float
    reason: str
    clarification_prompt: str | None = None
    value: object | None = None

    @property
    def accepted(self) -> bool:
        return self.action == ValidationAction.ACCEPT


PAIN_WORDS = (
    "pain",
    "hurt",
    "hurts",
    "aching",
    "ache",
    "sore",
    "sharp",
    "burning",
    "throbbing",
    "stiff",
    "swollen",
    "hell",
    "terrible",
    "awful",
    "bad",
    "severe",
    "unbearable",
)

FUNCTION_WORDS = (
    "walk",
    "walking",
    "stairs",
    "stand",
    "standing",
    "sleep",
    "sleeping",
    "dress",
    "dressing",
    "hands",
    "grip",
    "work",
    "cook",
    "drive",
    "sit",
    "bend",
    "move",
    "activity",
    "activities",
    "normal",
    "manageable",
    "help",
    "home",
)

NONSENSE_WORDS = (
    "coffee",
    "banana",
    "purple",
    "blue",
    "pizza",
    "weather",
    "football",
    "computer",
)

YES_WORDS = ("yes", "yeah", "yep", "have", "had", "some", "a little")
NO_WORDS = ("no", "none", "nope", "nothing", "not really")
UNSURE_WORDS = ("not sure", "unsure", "maybe", "i don't know", "i do not know")


def validate_pain_score_answer(text: str) -> ValidationResult:
    score = parse_pain_score(text)
    cleaned = _clean(text)

    if score is not None:
        return ValidationResult(ValidationAction.ACCEPT, 0.98, "valid_pain_score", value=score)

    if _contains_any(cleaned, PAIN_WORDS):
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.55,
            "ambiguous_pain_description",
            "That sounds painful. What number from 0 to 10 should I record?",
        )

    return ValidationResult(
        ValidationAction.ASK_AGAIN,
        0.1,
        "invalid_pain_score",
        "I need a number from 0 to 10.",
    )


def validate_pain_location_answer(text: str) -> ValidationResult:
    cleaned = _clean(text)
    if len(cleaned) < 2 or _contains_any(cleaned, NONSENSE_WORDS):
        return ValidationResult(
            ValidationAction.ASK_AGAIN,
            0.2,
            "invalid_pain_location",
            "Where is the pain? For example knee, hip, hand, or back.",
        )
    return ValidationResult(ValidationAction.ACCEPT, 0.9, "valid_pain_location", value=text.strip())


def validate_functional_impact_answer(state: ConversationState, text: str) -> ValidationResult:
    cleaned = _clean(text)
    if len(cleaned) < 2 or _contains_any(cleaned, NONSENSE_WORDS):
        return ValidationResult(
            ValidationAction.ASK_AGAIN,
            0.2,
            "invalid_functional_impact",
            "How is the pain affecting you today?",
        )

    severe_impact = has_severe_functional_impact(text)
    no_impact = has_no_functional_impact(text)

    if state.pain.score == 0 and severe_impact:
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.5,
            "pain_zero_conflicts_with_functional_impact",
            "Just checking. You said zero pain, but also trouble with activities. Is your pain still zero?",
        )

    if state.pain.score is not None and state.pain.score >= 9 and no_impact:
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.55,
            "severe_score_conflicts_with_no_impact",
            "Just checking. You said severe pain, but no effect on activities. Is the pain score still correct?",
        )

    if _contains_any(cleaned, PAIN_WORDS) or _contains_any(cleaned, FUNCTION_WORDS) or _is_yes_no_or_unsure(cleaned):
        return ValidationResult(ValidationAction.ACCEPT, 0.85, "valid_functional_impact", value=text.strip())

    return ValidationResult(
        ValidationAction.CLARIFY,
        0.45,
        "unclear_functional_impact",
        "Could you say how it affects walking, sleep, hands, or daily activities?",
    )


def validate_comparison_answer(state: ConversationState, text: str) -> ValidationResult:
    cleaned = _clean(text)
    comparison = comparison_from_text(text)

    if comparison == "unknown" and not _contains_any(cleaned, UNSURE_WORDS):
        return ValidationResult(
            ValidationAction.ASK_AGAIN,
            0.25,
            "invalid_comparison",
            "Is it better, worse, or about the same as usual?",
        )

    if state.pain.score == 0 and comparison == "worse":
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.5,
            "pain_zero_conflicts_with_worse_comparison",
            "Just checking. You said zero pain, but worse than usual. Is there pain today?",
        )

    return ValidationResult(ValidationAction.ACCEPT, 0.9, "valid_comparison", value=comparison)


def validate_treatment_answer(text: str) -> ValidationResult:
    cleaned = _clean(text)
    if not cleaned:
        return ValidationResult(
            ValidationAction.ASK_AGAIN,
            0.1,
            "empty_treatment_answer",
            "Are you using anything for the pain now?",
        )
    if _contains_any(cleaned, NONSENSE_WORDS) and not _is_yes_no_or_unsure(cleaned):
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.35,
            "unclear_treatment_answer",
            "Do you mean no treatment, or are you using medicine, cream, injections, or therapy?",
        )
    return ValidationResult(ValidationAction.ACCEPT, 0.85, "valid_treatment_answer", value=text.strip())


def validate_side_effect_answer(text: str) -> ValidationResult:
    cleaned = _clean(text)
    detected = detect_symptoms(text)
    red_flags = detected.get("red_flags", [])
    non_urgent = detected.get("non_urgent", [])

    if isinstance(red_flags, list) and red_flags:
        return ValidationResult(ValidationAction.ESCALATE, 1.0, "red_flag_detected", value=detected)

    if isinstance(non_urgent, list) and non_urgent:
        return ValidationResult(ValidationAction.ACCEPT, 0.95, "symptoms_detected", value=detected)

    if _is_yes_no_or_unsure(cleaned) or _contains_any(cleaned, PAIN_WORDS):
        return ValidationResult(ValidationAction.ACCEPT, 0.85, "valid_side_effect_answer", value=detected)

    if len(cleaned) < 2 or _contains_any(cleaned, NONSENSE_WORDS):
        return ValidationResult(
            ValidationAction.ASK_AGAIN,
            0.2,
            "invalid_side_effect_answer",
            "Any side effects or new symptoms? You can say no.",
        )

    return ValidationResult(
        ValidationAction.CLARIFY,
        0.45,
        "unclear_side_effect_answer",
        "Sorry, is that a symptom or side effect, or should I record no symptoms?",
    )


def validate_red_flags_answer(text: str) -> ValidationResult:
    cleaned = _clean(text)
    detected = detect_symptoms(text)
    red_flags = detected.get("red_flags", [])

    if isinstance(red_flags, list) and red_flags:
        return ValidationResult(ValidationAction.ESCALATE, 1.0, "red_flag_detected", value=detected)

    if _is_yes_no_or_unsure(cleaned):
        return ValidationResult(ValidationAction.ACCEPT, 0.9, "valid_red_flag_answer", value=detected)

    if len(cleaned) < 2 or _contains_any(cleaned, NONSENSE_WORDS):
        return ValidationResult(
            ValidationAction.ASK_AGAIN,
            0.2,
            "invalid_red_flag_answer",
            "Please answer yes or no. Any chest pain, breathing trouble, black stools, or fainting?",
        )

    return ValidationResult(
        ValidationAction.CLARIFY,
        0.45,
        "unclear_red_flag_answer",
        "Sorry, is that a yes or a no for the safety symptoms?",
    )


def has_severe_functional_impact(text: str) -> bool:
    cleaned = _clean(text)
    return any(
        phrase in cleaned
        for phrase in (
            "can't walk",
            "cannot walk",
            "unable to walk",
            "can't stand",
            "cannot stand",
            "unable to stand",
            "need help",
            "need someone",
            "bed bound",
            "in bed",
            "can't sleep",
            "cannot sleep",
            "unbearable",
        )
    )


def has_no_functional_impact(text: str) -> bool:
    cleaned = _clean(text)
    return any(
        phrase in cleaned
        for phrase in (
            "no effect",
            "no problem",
            "normal",
            "fine",
            "can do everything",
            "not affecting",
            "doesn't affect",
            "does not affect",
        )
    )


def _is_yes_no_or_unsure(cleaned: str) -> bool:
    return _contains_any(cleaned, YES_WORDS) or _contains_any(cleaned, NO_WORDS) or _contains_any(cleaned, UNSURE_WORDS)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())
