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
        (r"\bchest pain\b", r"\bchest tightness\b", r"\bpressure in my chest\b"),
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
        ),
        True,
    ),
    SymptomRule(
        "vomiting blood",
        (
            r"\bvomit(?:ing)? blood\b",
            r"\bblood in vomit\b",
            r"\bcoffee ground\b",
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
        ),
        True,
    ),
    SymptomRule(
        "confusion",
        (r"\bconfused\b", r"\bconfusion\b", r"\bdisoriented\b"),
        True,
    ),
    SymptomRule(
        "fever with hot swollen joint",
        (
            r"\bfever\b.*\b(hot|swollen|red).*\bjoint\b",
            r"\b(hot|swollen|red).*\bjoint\b.*\bfever\b",
            r"\bjoint\b.*\bfeels hot\b.*\bfever\b",
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
        ),
        True,
    ),
    SymptomRule(
        "severe symptoms after injection or treatment",
        (
            r"\bafter (?:the )?injection\b.*\b(severe|worse|fever|swollen|red|hot)\b",
            r"\bsevere\b.*\bafter (?:the )?injection\b",
        ),
        True,
    ),
)


NON_URGENT_RULES: tuple[SymptomRule, ...] = (
    SymptomRule("stomach pain or heartburn", (r"\bstomach pain\b", r"\bheartburn\b", r"\bindigestion\b"), False),
    SymptomRule("nausea", (r"\bnausea\b", r"\bnauseous\b", r"\bsick to my stomach\b"), False),
    SymptomRule("leg, ankle, or foot swelling", (r"\bankle swelling\b", r"\bfoot swelling\b", r"\bleg swelling\b"), False),
    SymptomRule("reduced urination", (r"\bnot urinating\b", r"\bless urine\b", r"\breduced urination\b"), False),
    SymptomRule("rash or skin irritation", (r"\brash\b", r"\bitching\b", r"\bskin irritation\b"), False),
    SymptomRule("constipation", (r"\bconstipation\b", r"\bconstipated\b"), False),
    SymptomRule("drowsiness", (r"\bdrowsy\b", r"\bsleepy\b", r"\bsedated\b"), False),
    SymptomRule("yellow skin or eyes", (r"\byellow skin\b", r"\byellow eyes\b", r"\bjaundice\b"), False),
    SymptomRule("dark urine", (r"\bdark urine\b",), False),
    SymptomRule("unusual bruising or bleeding", (r"\bunusual bruising\b", r"\bunusual bleeding\b"), False),
)


NEGATION_PATTERNS = (
    r"\bno\b",
    r"\bnone\b",
    r"\bnot\b",
    r"\bnope\b",
    r"\bwithout\b",
    r"\bdon't have\b",
    r"\bdo not have\b",
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

    if re.search(r"\b(no|none|nothing|nope)\b", cleaned) and len(cleaned.split()) <= 8:
        return {"red_flags": [], "non_urgent": [], "uncertain": False}

    for rule in RED_FLAG_RULES:
        if _matches_rule(cleaned, rule):
            red_flags.append(rule.label)

    for rule in NON_URGENT_RULES:
        if _matches_rule(cleaned, rule):
            concerns.append(rule.label)

    uncertain = any(term in cleaned for term in ("not sure", "unsure", "maybe", "i think"))
    return {
        "red_flags": sorted(set(red_flags)),
        "non_urgent": sorted(set(concerns)),
        "uncertain": uncertain and not red_flags,
    }


def escalation_message() -> str:
    return (
        "I'm concerned about that. I can't diagnose it by phone, but it may need urgent care. "
        "Please call emergency services or seek urgent medical help now. "
        "If you are alone, please call someone nearby to stay with you."
    )


def side_effects_prompt() -> str:
    return (
        "Any side effects or new symptoms? For example stomach trouble, swelling, rash, dizziness, or breathing problems."
    )


def red_flags_prompt() -> str:
    return (
        "Last safety check. Any chest pain, trouble breathing, black stools, vomiting blood, fainting, confusion, or fever with a hot swollen joint?"
    )
