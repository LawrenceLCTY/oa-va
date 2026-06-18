from __future__ import annotations

import re


NUMBER_WORDS = {
    "zero": 0,
    "none": 0,
    "no pain": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def parse_pain_score(text: str) -> int | None:
    cleaned = text.strip().lower()

    for phrase, value in NUMBER_WORDS.items():
        if re.search(rf"\b{re.escape(phrase)}\b", cleaned):
            return value

    match = re.search(r"\b(10|[0-9])\b", cleaned)
    if not match:
        return None

    value = int(match.group(1))
    if 0 <= value <= 10:
        return value
    return None


def pain_severity(score: int | None) -> str:
    if score is None:
        return "unknown"
    if score == 0:
        return "none"
    if 1 <= score <= 3:
        return "mild"
    if 4 <= score <= 6:
        return "moderate"
    return "severe"


def comparison_from_text(text: str) -> str:
    cleaned = text.lower()
    if any(term in cleaned for term in ("worse", "worst", "more painful", "increased", "higher")):
        return "worse"
    if any(term in cleaned for term in ("better", "improved", "less painful", "lower")):
        return "better"
    if any(term in cleaned for term in ("same", "similar", "usual", "unchanged", "no change")):
        return "same"
    if any(term in cleaned for term in ("not sure", "unsure", "don't know", "do not know")):
        return "unknown"
    return "unknown"


def pain_prompt() -> str:
    return (
        "What number is your joint pain now, from 0 to 10? "
        "Zero is no pain. Ten is the worst pain."
    )


def functional_anchor_prompt(score: int | None) -> str:
    if score is not None and score >= 9:
        return (
            "Is the pain stopping your normal activities today, or still manageable?"
        )
    return (
        "How is it affecting you today? For example walking, stairs, sleep, or using your hands."
    )
