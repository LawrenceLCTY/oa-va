from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SymptomRule:
    label: str
    patterns: tuple[str, ...]
    red_flag: bool


RED_FLAG_RULES: tuple[SymptomRule, ...] = (
    SymptomRule(
        "chest pain",
        (r"\bchest pain\b", r"\bchest tightness\b", r"\bpressure in my chest\b", r"胸痛", r"胸口痛", r"胸闷"),
        True,
    ),
    SymptomRule(
        "trouble breathing",
        (
            r"\btrouble breathing\b",
            r"\bshortness of breath\b",
            r"\bcan't breathe\b",
            r"\bcannot breathe\b",
            r"\bdifficulty breathing\b",
            r"喘不上气",
            r"呼吸困难",
            r"气短",
            r"不能呼吸",
        ),
        True,
    ),
    SymptomRule(
        "stroke-like symptoms",
        (
            r"\bslurred speech\b",
            r"\bone side\b.*\bweak",
            r"\bface droop",
            r"\bfacial droop",
            r"\bsudden numbness\b",
            r"\bsudden weakness\b",
            r"说话不清",
            r"口齿不清",
            r"一侧无力",
            r"半边.*无力",
            r"脸歪",
            r"突然麻木",
        ),
        True,
    ),
    SymptomRule(
        "severe allergic reaction",
        (
            r"\bface swelling\b",
            r"\blip swelling\b",
            r"\btongue swelling\b",
            r"\bthroat swelling\b",
            r"\bhives\b.*\bbreath",
            r"\ballergic reaction\b",
            r"脸肿",
            r"嘴唇肿",
            r"舌头肿",
            r"喉咙肿",
            r"过敏",
            r"荨麻疹.*喘",
        ),
        True,
    ),
    SymptomRule(
        "vomiting blood",
        (
            r"\bvomit(?:ing)? blood\b",
            r"\bblood in vomit\b",
            r"\bcoffee ground\b",
            r"吐血",
            r"呕血",
            r"咖啡色.*呕吐",
        ),
        True,
    ),
    SymptomRule(
        "black or bloody stools",
        (
            r"\bblack stool",
            r"\bblack stools",
            r"\btarry stool",
            r"\btarry stools",
            r"\bblood in (?:my )?stool",
            r"\bbloody stool",
            r"黑便",
            r"柏油样便",
            r"大便.*血",
            r"便血",
        ),
        True,
    ),
    SymptomRule(
        "fainting or severe dizziness",
        (
            r"\bfainted\b",
            r"\bfainting\b",
            r"\bpassed out\b",
            r"\bsevere dizziness\b",
            r"\bvery dizzy\b",
            r"晕倒",
            r"昏倒",
            r"晕厥",
            r"头晕得厉害",
        ),
        True,
    ),
    SymptomRule(
        "confusion",
        (r"\bconfused\b", r"\bconfusion\b", r"\bdisoriented\b", r"意识混乱", r"糊涂", r"神志不清"),
        True,
    ),
    SymptomRule(
        "fever with hot swollen joint",
        (
            r"\bfever\b.*\b(hot|swollen|red).*\bjoint\b",
            r"\b(hot|swollen|red).*\bjoint\b.*\bfever\b",
            r"\bjoint\b.*\bfeels hot\b.*\bfever\b",
            r"发烧.*关节.*(红|热|肿)",
            r"关节.*(红|热|肿).*发烧",
            r"发热.*关节.*(红|热|肿)",
        ),
        True,
    ),
    SymptomRule(
        "new inability to bear weight after injury or fall",
        (
            r"\b(?:fall|fell|injury|injured|trauma|accident)\b.*\bcan't (?:stand|walk|bear weight)\b",
            r"\b(?:fall|fell|injury|injured|trauma|accident)\b.*\bcannot (?:stand|walk|bear weight)\b",
            r"\b(?:fall|fell|injury|injured|trauma|accident)\b.*\bunable to (?:stand|walk|bear weight)\b",
            r"\bcan't (?:stand|walk|bear weight)\b.*\b(?:after|because of).*\b(?:fall|fell|injury|injured|trauma|accident)\b",
            r"\bcannot (?:stand|walk|bear weight)\b.*\b(?:after|because of).*\b(?:fall|fell|injury|injured|trauma|accident)\b",
            r"\bunable to (?:stand|walk|bear weight)\b.*\b(?:after|because of).*\b(?:fall|fell|injury|injured|trauma|accident)\b",
            r"\bfall\b.*\bcan't walk\b",
            r"(摔|跌倒|受伤|外伤|事故).*(不能走|走不了|不能站|站不起来)",
            r"(不能走|走不了|不能站|站不起来).*(摔|跌倒|受伤|外伤|事故)",
        ),
        True,
    ),
    SymptomRule(
        "severe symptoms after injection or treatment",
        (
            r"\bafter (?:the )?injection\b.*\b(severe|worse|fever|swollen|red|hot)\b",
            r"\bsevere\b.*\bafter (?:the )?injection\b",
            r"打针后.*(严重|更疼|发烧|红|肿|热)",
            r"注射后.*(严重|更疼|发烧|红|肿|热)",
        ),
        True,
    ),
)


NON_URGENT_RULES: tuple[SymptomRule, ...] = (
    SymptomRule("stomach pain or heartburn", (r"\bstomach pain\b", r"\bheartburn\b", r"\bindigestion\b"), False),
    SymptomRule("nausea", (r"\bnausea\b", r"\bnauseous\b", r"\bsick to my stomach\b", r"恶心", r"想吐"), False),
    SymptomRule("leg, ankle, or foot swelling", (r"\bankle swelling\b", r"\bfoot swelling\b", r"\bleg swelling\b", r"脚肿", r"腿肿", r"踝.*肿"), False),
    SymptomRule("reduced urination", (r"\bnot urinating\b", r"\bless urine\b", r"\breduced urination\b", r"尿少", r"小便少"), False),
    SymptomRule("rash or skin irritation", (r"\brash\b", r"\bitching\b", r"\bskin irritation\b", r"皮疹", r"瘙痒", r"皮肤痒"), False),
    SymptomRule("constipation", (r"\bconstipation\b", r"\bconstipated\b", r"便秘"), False),
    SymptomRule("drowsiness", (r"\bdrowsy\b", r"\bsleepy\b", r"\bsedated\b", r"嗜睡", r"很困"), False),
    SymptomRule("yellow skin or eyes", (r"\byellow skin\b", r"\byellow eyes\b", r"\bjaundice\b", r"皮肤黄", r"眼睛黄", r"黄疸"), False),
    SymptomRule("dark urine", (r"\bdark urine\b", r"尿色深", r"尿很深"), False),
    SymptomRule("unusual bruising or bleeding", (r"\bunusual bruising\b", r"\bunusual bleeding\b", r"异常出血", r"容易淤青"), False),
)


NEGATION_PATTERNS = (
    r"\bno\b",
    r"\bnone\b",
    r"\bnot\b",
    r"\bnope\b",
    r"\bwithout\b",
    r"\bdon't have\b",
    r"\bdo not have\b",
    r"没有",
    r"没",
    r"无",
    r"不是",
)


def _has_negation_near(text: str, start: int) -> bool:
    prefix = text[max(0, start - 35):start]
    return any(re.search(pattern, prefix) for pattern in NEGATION_PATTERNS)


def _matches_rule(text: str, rule: SymptomRule) -> bool:
    for pattern in rule.patterns:
        match = re.search(pattern, text)
        if match and not _has_negation_near(text, match.start()):
            return True
    return False


def detect_symptoms(text: str) -> dict[str, list[str] | bool]:
    cleaned = text.lower()
    red_flags: list[str] = []
    concerns: list[str] = []

    if _is_short_negative(cleaned):
        return {"red_flags": [], "non_urgent": [], "uncertain": False}

    for rule in RED_FLAG_RULES:
        if _matches_rule(cleaned, rule):
            red_flags.append(rule.label)

    for rule in NON_URGENT_RULES:
        if _matches_rule(cleaned, rule):
            concerns.append(rule.label)

    uncertain = any(term in cleaned for term in ("not sure", "unsure", "maybe", "i think", "不确定", "不知道", "说不清", "可能"))
    return {
        "red_flags": sorted(set(red_flags)),
        "non_urgent": sorted(set(concerns)),
        "uncertain": uncertain and not red_flags,
    }


def _is_short_negative(text: str) -> bool:
    if re.search(r"\b(no|none|nothing|nope)\b", text) and len(text.split()) <= 8:
        return True
    compact = re.sub(r"\s+", "", text)
    return compact in {"没有", "没", "无", "没有不舒服", "没有症状", "没事", "没有这些"}
