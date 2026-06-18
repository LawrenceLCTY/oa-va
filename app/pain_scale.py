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
    "零": 0,
    "〇": 0,
    "没有": 0,
    "不疼": 0,
    "无痛": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def parse_pain_score(text: str) -> int | None:
    cleaned = text.strip().lower()

    for phrase, value in NUMBER_WORDS.items():
        if _has_cjk(phrase):
            if phrase in cleaned:
                return value
        elif re.search(rf"\b{re.escape(phrase)}\b", cleaned):
            return value

    match = re.search(r"\b(10|[0-9])\b", cleaned)
    if not match:
        return None

    value = int(match.group(1))
    if 0 <= value <= 10:
        return value
    return None


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


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
    if any(term in cleaned for term in ("更疼", "更痛", "严重", "重了", "加重", "变重", "厉害", "恶化")):
        return "worse"
    if any(term in cleaned for term in ("better", "improved", "less painful", "lower")):
        return "better"
    if any(term in cleaned for term in ("好些", "好多", "减轻", "轻了", "缓解", "改善")):
        return "better"
    if any(term in cleaned for term in ("same", "similar", "usual", "unchanged", "no change")):
        return "same"
    if any(term in cleaned for term in ("差不多", "一样", "差不多一样", "没变化", "没有变化", "和平时一样")):
        return "same"
    if any(term in cleaned for term in ("not sure", "unsure", "don't know", "do not know")):
        return "unknown"
    if any(term in cleaned for term in ("不确定", "不知道", "说不清")):
        return "unknown"
    return "unknown"


def pain_prompt(language: str = "en") -> str:
    if language == "zh-CN":
        return "现在关节疼痛是0到10分的几分？0是不疼，10是最疼。"
    return (
        "What number is your joint pain now, from 0 to 10? "
        "Zero is no pain. Ten is the worst pain."
    )


def functional_anchor_prompt(score: int | None, language: str = "en") -> str:
    if score is not None and score >= 9:
        if language == "zh-CN":
            return "这个疼痛今天影响您正常活动吗？还是还能忍受？"
        return (
            "Is the pain stopping your normal activities today, or still manageable?"
        )
    if language == "zh-CN":
        return "今天影响您做什么事？比如走路、上下楼、睡觉，或者用手。"
    return (
        "How is it affecting you today? For example walking, stairs, sleep, or using your hands."
    )
