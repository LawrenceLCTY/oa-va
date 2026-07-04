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
    clarification_prompts: dict[str, str] | None = None
    value: object | None = None

    @property
    def accepted(self) -> bool:
        return self.action == ValidationAction.ACCEPT

    def prompt(self, language: str) -> str | None:
        if self.clarification_prompts and language in self.clarification_prompts:
            return self.clarification_prompts[language]
        return self.clarification_prompt


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
    "疼",
    "痛",
    "酸",
    "胀",
    "刺痛",
    "酸痛",
    "很疼",
    "很痛",
    "疼死",
    "痛死",
    "受不了",
    "厉害",
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
    "走路",
    "上下楼",
    "上楼",
    "下楼",
    "站",
    "站立",
    "睡觉",
    "穿衣",
    "用手",
    "拿东西",
    "做饭",
    "活动",
    "日常",
    "正常",
    "影响",
    "帮忙",
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
    "咖啡",
    "香蕉",
    "紫色",
    "蓝色",
    "披萨",
    "天气",
    "电脑",
)

YES_WORDS = ("yes", "yeah", "yep", "have", "had", "some", "a little")
NO_WORDS = ("no", "none", "nope", "nothing", "not really")
UNSURE_WORDS = ("not sure", "unsure", "maybe", "i don't know", "i do not know")
YES_ZH = ("有", "是", "对", "对的", "有的", "嗯", "是的", "联系了", "去了")
NO_ZH = ("没有", "没", "无", "不是", "不", "没事", "没有不舒服")
UNSURE_ZH = ("不确定", "不知道", "说不清", "可能")


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
            {"zh-CN": "听起来很疼。请说一个0到10的数字。"},
        )

    return ValidationResult(
        ValidationAction.ASK_AGAIN,
        0.1,
        "invalid_pain_score",
        "I need a number from 0 to 10.",
        {"zh-CN": "请说一个0到10的数字。"},
    )


def validate_pain_location_answer(text: str) -> ValidationResult:
    cleaned = _clean(text)
    if len(cleaned) < 2 or _contains_any(cleaned, NONSENSE_WORDS):
        return ValidationResult(
            ValidationAction.ASK_AGAIN,
            0.2,
            "invalid_pain_location",
            "Where is the pain? For example knee, hip, hand, or back.",
            {"zh-CN": "哪里疼？比如膝盖、髋部、手，或者腰背。"},
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
            {"zh-CN": "今天疼痛影响您做什么事？"},
        )

    severe_impact = has_severe_functional_impact(text)
    no_impact = has_no_functional_impact(text)

    if state.pain.score == 0 and severe_impact:
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.5,
            "pain_zero_conflicts_with_functional_impact",
            "Just checking. You said zero pain, but also trouble with activities. Is your pain still zero?",
            {"zh-CN": "确认一下，您刚才说0分，但又说活动受影响。现在疼痛还是0分吗？"},
        )

    if state.pain.score is not None and state.pain.score >= 9 and no_impact:
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.55,
            "severe_score_conflicts_with_no_impact",
            "Just checking. You said severe pain, but no effect on activities. Is the pain score still correct?",
            {"zh-CN": "确认一下，您说疼痛很重，但活动不受影响。刚才的疼痛分数还准确吗？"},
        )

    if _contains_any(cleaned, PAIN_WORDS) or _contains_any(cleaned, FUNCTION_WORDS) or _is_yes_no_or_unsure(cleaned):
        return ValidationResult(ValidationAction.ACCEPT, 0.85, "valid_functional_impact", value=text.strip())

    return ValidationResult(
        ValidationAction.CLARIFY,
        0.45,
        "unclear_functional_impact",
        "Could you say how it affects walking, sleep, hands, or daily activities?",
        {"zh-CN": "请说一下它怎么影响走路、睡觉、用手，或者日常活动。"},
    )


def validate_comparison_answer(state: ConversationState, text: str) -> ValidationResult:
    cleaned = _clean(text)
    comparison = comparison_from_text(text)

    if comparison == "unknown" and not _contains_any(cleaned, UNSURE_WORDS) and not _contains_any(cleaned, UNSURE_ZH):
        return ValidationResult(
            ValidationAction.ASK_AGAIN,
            0.25,
            "invalid_comparison",
            "Is it better, worse, or about the same as usual?",
            {"zh-CN": "和您平时相比，是轻了、重了，还是差不多？"},
        )

    if state.pain.score == 0 and comparison == "worse":
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.5,
            "pain_zero_conflicts_with_worse_comparison",
            "Just checking. You said zero pain, but worse than usual. Is there pain today?",
            {"zh-CN": "确认一下，您说疼痛0分，但又说比平时重。今天到底有疼痛吗？"},
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
            {"zh-CN": "现在有用什么止痛办法吗？"},
        )
    if _contains_any(cleaned, ("don't know", "do not know", "not sure")) or _contains_any(cleaned, ("不懂", "不知道", "不清楚")):
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.35,
            "unclear_treatment_answer",
            "Are you using any medicine, cream, injections, therapy, or nothing for the pain?",
            {"zh-CN": "您现在有没有用药片、药膏、针剂、康复治疗，还是没有用任何止痛办法？"},
        )
    if _contains_any(cleaned, NONSENSE_WORDS) and not _is_yes_no_or_unsure(cleaned):
        return ValidationResult(
            ValidationAction.CLARIFY,
            0.35,
            "unclear_treatment_answer",
            "Do you mean no treatment, or are you using medicine, cream, injections, or therapy?",
            {"zh-CN": "您的意思是没有治疗，还是用了药片、药膏、针剂或康复治疗？"},
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
            {"zh-CN": "有没有不舒服或新的症状？没有也可以说没有。"},
        )

    return ValidationResult(
        ValidationAction.CLARIFY,
        0.45,
        "unclear_side_effect_answer",
        "Sorry, is that a symptom or side effect, or should I record no symptoms?",
        {"zh-CN": "不好意思，这是不舒服的症状吗？还是记录为没有不舒服？"},
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
            {"zh-CN": "请回答有或没有。有没有胸痛、喘不上气、黑便或晕倒？"},
        )

    return ValidationResult(
        ValidationAction.CLARIFY,
        0.45,
        "unclear_red_flag_answer",
        "Sorry, is that a yes or a no for the safety symptoms?",
        {"zh-CN": "不好意思，安全症状这里是有，还是没有？"},
    )


def classify_yes_no_unsure(text: str) -> str:
    cleaned = _clean(text)
    if _contains_any(cleaned, UNSURE_WORDS) or _contains_any(cleaned, UNSURE_ZH):
        return "uncertain"
    if _contains_any(cleaned, NO_WORDS) or _contains_any(cleaned, NO_ZH):
        return "no"
    if _contains_any(cleaned, YES_WORDS) or _contains_any(cleaned, YES_ZH):
        return "yes"
    return "unknown"


def classify_respondent_source(text: str) -> str:
    cleaned = _clean(text)
    if any(term in cleaned for term in ("caregiver proxy", "caregiver answering", "proxy")) or any(
        term in cleaned for term in ("家属代答", "家人代答", "照护者代答", "代答")
    ):
        return "caregiver_proxy"
    if any(term in cleaned for term in ("caregiver help", "with caregiver", "family help")) or any(
        term in cleaned for term in ("家属帮忙", "家人帮忙", "照护者帮忙", "有人帮")
    ):
        return "participant_with_caregiver_assistance"
    if any(term in cleaned for term in ("alone", "by myself", "participant")) or any(
        term in cleaned for term in ("本人", "自己", "我自己", "本人回答")
    ):
        return "participant_independently"
    if _contains_any(cleaned, UNSURE_WORDS) or _contains_any(cleaned, UNSURE_ZH):
        return "unknown"
    return "unknown"


def classify_symptom_status(text: str) -> str:
    cleaned = _clean(text)
    if any(term in cleaned for term in ("ongoing", "still", "continues", "not resolved")) or any(
        term in cleaned for term in ("还在", "持续", "没好", "没有好")
    ):
        return "ongoing"
    if any(term in cleaned for term in ("resolved", "gone", "better now", "stopped")) or any(
        term in cleaned for term in ("好了", "已经好", "缓解", "没有了")
    ):
        return "resolved"
    if _contains_any(cleaned, UNSURE_WORDS) or _contains_any(cleaned, UNSURE_ZH):
        return "unknown"
    return "unknown"


def classify_symptom_severity(text: str) -> str:
    cleaned = _clean(text)
    if any(term in cleaned for term in ("severe", "serious", "very bad")) or any(term in cleaned for term in ("重度", "严重", "很重")):
        return "severe"
    if any(term in cleaned for term in ("moderate", "medium")) or any(term in cleaned for term in ("中度", "中等")):
        return "moderate"
    if any(term in cleaned for term in ("mild", "slight", "minor")) or any(term in cleaned for term in ("轻度", "轻微", "一点")):
        return "mild"
    if _contains_any(cleaned, UNSURE_WORDS) or _contains_any(cleaned, UNSURE_ZH):
        return "unknown"
    return "unknown"


def classify_medication_changed(text: str) -> str:
    cleaned = _clean(text)
    if any(term in cleaned for term in ("stopped", "stop", "paused", "reduced", "lowered dose")) or any(
        term in cleaned for term in ("停药", "停了", "暂停", "减量", "少吃")
    ):
        return "yes"
    return classify_yes_no_unsure(text)


def classify_emergency_visit(text: str) -> str:
    cleaned = _clean(text)
    if any(term in cleaned for term in ("emergency", "hospital", "hospitalization", "admitted")) or any(
        term in cleaned for term in ("急诊", "医院", "住院")
    ):
        return "yes"
    return classify_yes_no_unsure(text)


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
            "不能走",
            "走不了",
            "不能站",
            "站不起来",
            "需要帮忙",
            "要人扶",
            "下不了床",
            "睡不了",
            "受不了",
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
            "没影响",
            "不影响",
            "正常",
            "没问题",
            "还好",
            "都可以",
        )
    )


def _is_yes_no_or_unsure(cleaned: str) -> bool:
    return (
        _contains_any(cleaned, YES_WORDS)
        or _contains_any(cleaned, NO_WORDS)
        or _contains_any(cleaned, UNSURE_WORDS)
        or _contains_any(cleaned, YES_ZH)
        or _contains_any(cleaned, NO_ZH)
        or _contains_any(cleaned, UNSURE_ZH)
    )


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    for term in terms:
        if _has_cjk(term):
            if term in text:
                return True
        elif re.search(rf"\b{re.escape(term)}\b", text):
            return True
    return False


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)
