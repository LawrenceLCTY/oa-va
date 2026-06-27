from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VASAnchor:
    score: int
    en: str
    zh: str


@dataclass(frozen=True)
class VASQuestion:
    low: int
    high: int
    midpoint: int
    text: str


ANCHORS: tuple[VASAnchor, ...] = (
    VASAnchor(0, "no joint pain", "没有关节疼痛"),
    VASAnchor(1, "very mild discomfort that is easy to ignore", "很轻微的不适，基本可以忽略"),
    VASAnchor(2, "mild pain you notice, but it does not slow you down", "能感觉到疼，但基本不影响活动"),
    VASAnchor(3, "mild pain that makes you a little careful with movement", "轻度疼痛，活动时会稍微注意"),
    VASAnchor(4, "moderate pain that slows walking, stairs, or hand use", "中等疼痛，会让走路、上下楼或用手变慢"),
    VASAnchor(5, "moderate pain that interrupts some daily tasks", "中等疼痛，会影响一部分日常事情"),
    VASAnchor(6, "strong pain that makes normal activities clearly difficult", "较明显的疼痛，正常活动会比较困难"),
    VASAnchor(7, "severe pain that limits activity and is hard to ignore", "较重疼痛，明显限制活动，很难忽略"),
    VASAnchor(8, "very severe pain; moving or resting is difficult", "很重的疼痛，活动或休息都很困难"),
    VASAnchor(9, "extreme pain; you can barely do normal activities", "极重疼痛，几乎难以进行正常活动"),
    VASAnchor(10, "the worst pain you can imagine", "能想象到的最严重疼痛"),
)


def start_range() -> tuple[int, int]:
    return (0, 10)


def question(low: int, high: int, language: str, period: str) -> VASQuestion:
    midpoint = (low + high) // 2
    low_anchor = describe(low, language)
    high_anchor = describe(high, language)
    if language == "zh-CN":
        period_text = "过去一天的平均疼痛" if period == "average_24h" else "现在这一刻的疼痛"
        text = (
            f"为了更准确记录{period_text}，请比较两个描述。"
            f"它更接近 {midpoint}分以下：{low_anchor}，"
            f"还是 {midpoint + 1}分以上：{high_anchor}？"
        )
    else:
        period_text = "your average pain over the past day" if period == "average_24h" else "your pain right now"
        text = (
            f"To record {period_text} more accurately, please compare two descriptions. "
            f"Is it closer to {midpoint} or below: {low_anchor}, "
            f"or {midpoint + 1} or above: {high_anchor}?"
        )
    return VASQuestion(low=low, high=high, midpoint=midpoint, text=text)


def describe(score: int, language: str) -> str:
    anchor = ANCHORS[max(0, min(10, score))]
    return anchor.zh if language == "zh-CN" else anchor.en


def parse_choice(text: str, language: str) -> str | None:
    cleaned = text.lower().strip()
    compact = "".join(cleaned.split())

    lower_words = (
        "lower",
        "low",
        "less",
        "milder",
        "mild",
        "first",
        "a",
        "below",
        "left",
        "前",
        "前面",
        "低",
        "低一点",
        "轻",
        "轻一些",
        "轻一点",
        "下面",
        "以下",
        "第一个",
        "a",
    )
    higher_words = (
        "higher",
        "high",
        "more",
        "worse",
        "severe",
        "second",
        "b",
        "above",
        "right",
        "后",
        "后面",
        "高",
        "高一点",
        "重",
        "重一些",
        "重一点",
        "上面",
        "以上",
        "第二个",
        "b",
    )

    if any(word in cleaned for word in lower_words) or any(word in compact for word in lower_words if _has_cjk(word)):
        return "lower"
    if any(word in cleaned for word in higher_words) or any(word in compact for word in higher_words if _has_cjk(word)):
        return "higher"
    return None


def next_range(low: int, high: int, choice: str) -> tuple[int, int]:
    midpoint = (low + high) // 2
    if choice == "lower":
        return low, midpoint
    return midpoint + 1, high


def is_complete(low: int, high: int) -> bool:
    return low == high


def result_score(low: int, high: int) -> int:
    return max(0, min(10, low if low == high else round((low + high) / 2)))


def trace_entry(low: int, high: int, choice: str, language: str, period: str) -> dict[str, object]:
    prompt = question(low, high, language, period)
    return {
        "low": low,
        "high": high,
        "midpoint": prompt.midpoint,
        "choice": choice,
        "lower_anchor": describe(low, language),
        "higher_anchor": describe(high, language),
    }


def final_summary(score: int, language: str) -> str:
    if language == "zh-CN":
        return f"我会记录为{score}分，接近：{describe(score, language)}。"
    return f"I'll record that as {score} out of 10, closest to: {describe(score, language)}."


def clarification(language: str) -> str:
    if language == "zh-CN":
        return "为了记录0到10分，请告诉我更接近前一个较轻的描述，还是后一个较重的描述。"
    return "To record the 0 to 10 score, please tell me whether it is closer to the first, milder description, or the second, stronger description."


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)
