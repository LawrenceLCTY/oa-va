from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from app.clinical_rules import detect_symptoms
from app.openai_client import UnderstandingResult


DEFAULT_LOCAL_LLM_URL = "http://127.0.0.1:8001/v1/chat/completions"
DEFAULT_LOCAL_LLM_MODEL = "/home/lawrencelcty/huggingface/models/Qwen/Qwen3-0.6B-FP8"


class LocalClinicalAI:
    """Local OpenAI-compatible clinical extraction and wording adapter.

    This adapter is intentionally narrower than a general medical chatbot. It
    may extract slots and gently rewrite required lines, but it never owns the
    clinical protocol or safety escalation.
    """

    def __init__(self) -> None:
        self.url = os.getenv("LOCAL_LLM_URL", DEFAULT_LOCAL_LLM_URL).strip()
        self.model = os.getenv("LOCAL_LLM_MODEL", DEFAULT_LOCAL_LLM_MODEL).strip()
        self.timeout_seconds = float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "8"))
        self.understanding_enabled = _env_enabled("ENABLE_LOCAL_UNDERSTANDING", default=True)
        self.reply_rewrite_enabled = _env_enabled("ENABLE_LOCAL_REPLY_REWRITE", default=False)
        self.last_trace: dict[str, object] | None = None
        self.trace_events: list[dict[str, object]] = []

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.model)

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "understanding_enabled": self.understanding_enabled,
            "reply_rewrite_enabled": self.reply_rewrite_enabled,
            "url": self.url,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
        }

    def understand(self, step: str, language: str, patient_text: str) -> UnderstandingResult | None:
        self.last_trace = {
            "component": "local_clinical_ai",
            "operation": "understand",
            "enabled": self.enabled and self.understanding_enabled,
            "model": self.model,
            "url": self.url,
            "step": step,
            "language": language,
            "used_model": False,
        }
        if not self.enabled or not self.understanding_enabled:
            self.last_trace["fallback"] = "rule_only"
            self._record_trace(self.last_trace)
            return _rule_only_understanding(patient_text)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract structured answers for an osteoarthritis phone follow-up. "
                        "Return JSON only. Do not diagnose or give advice. Use null for missing values. "
                        "Canonical yes/no fields must use yes, no, uncertain, or unknown. "
                        "usual_comparison must use better, worse, same, or unknown. "
                        "respondent_source must use participant_independently, "
                        "participant_with_caregiver_assistance, caregiver_proxy, or unknown. "
                        "symptom_status must use ongoing, resolved, or unknown. "
                        "symptom_severity must use mild, moderate, severe, or unknown."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Language: {language}\n"
                        f"Current protocol step: {step}\n"
                        f"Patient answer: {patient_text}\n\n"
                        "Return exactly this JSON object shape:\n"
                        "{\n"
                        '  "accepted": true,\n'
                        '  "confidence": 0.0,\n'
                        '  "answer_type": "unknown",\n'
                        '  "value": null,\n'
                        '  "text_value": null,\n'
                        '  "identity": {"name": null, "mobile_number": null, "age": null},\n'
                        '  "red_flags": [],\n'
                        '  "non_urgent_concerns": [],\n'
                        '  "slots": {\n'
                        '    "respondent_source": null,\n'
                        '    "average_24h_score": null,\n'
                        '    "current_pain_score": null,\n'
                        '    "pain_location": null,\n'
                        '    "functional_impact": null,\n'
                        '    "usual_comparison": null,\n'
                        '    "treatment_context": null,\n'
                        '    "side_effect_screening_result": null,\n'
                        '    "side_effect_description": null,\n'
                        '    "symptom_start_time": null,\n'
                        '    "symptom_status": null,\n'
                        '    "symptom_severity": null,\n'
                        '    "medication_changed": null,\n'
                        '    "doctor_contacted": null,\n'
                        '    "emergency_visit_or_hospitalization": null\n'
                        "  },\n"
                        '  "needs_clarification": false,\n'
                        '  "clarification_prompt": null\n'
                        "}"
                    ),
                },
            ],
            "temperature": 0.0,
            "max_tokens": 700,
        }
        body = self._post_json(payload)
        parsed = _parse_model_json(body)
        if not parsed:
            self.last_trace["fallback"] = "rule_only_after_model_failure"
            self._record_trace(self.last_trace)
            return _rule_only_understanding(patient_text)
        self.last_trace.update(
            {
                "used_model": True,
                "accepted": bool(parsed.get("accepted")),
                "confidence": float(parsed.get("confidence") or 0),
                "answer_type": str(parsed.get("answer_type") or "unknown"),
                "slots_present": _present_slot_names(parsed.get("slots")),
                "red_flags": parsed.get("red_flags") if isinstance(parsed.get("red_flags"), list) else [],
                "non_urgent_concerns": (
                    parsed.get("non_urgent_concerns") if isinstance(parsed.get("non_urgent_concerns"), list) else []
                ),
            }
        )
        self._record_trace(self.last_trace)
        return _understanding_from_parsed(parsed, patient_text)

    def friendly_reply(
        self,
        language: str,
        clinical_message: str,
        recent_transcript: list[dict[str, str]] | None = None,
    ) -> str | None:
        if not self.enabled or not self.reply_rewrite_enabled:
            return None
        context = _format_recent_transcript(recent_transcript or [])
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Rewrite the required clinical protocol line as one natural spoken phone-call line. "
                        "Preserve all meaning, numbers, questions, and urgent-care instructions. "
                        "Do not add medical advice or extra questions. Return only the spoken line."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Language: {language}\n"
                        f"Recent conversation:\n{context}\n\n"
                        f"Required clinical line:\n{clinical_message}"
                    ),
                },
            ],
            "temperature": 0.4,
            "max_tokens": 160,
        }
        body = self._post_json(payload)
        text = _choice_text(body)
        self.last_trace = {
            "component": "local_clinical_ai",
            "operation": "friendly_reply",
            "enabled": True,
            "model": self.model,
            "url": self.url,
            "language": language,
            "used_model": bool(text),
            "fallback": None if text else "required_line",
        }
        self._record_trace(self.last_trace)
        return text

    def clarification_reply(
        self,
        language: str,
        step: str,
        patient_text: str,
        clinical_prompt: str,
        reason: str,
        recent_transcript: list[dict[str, str]] | None = None,
    ) -> str | None:
        if not self.enabled or not self.reply_rewrite_enabled:
            return None
        context = _format_recent_transcript(recent_transcript or [])
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "The patient answer was not usable for the current protocol step. "
                        "Briefly acknowledge and ask one clear clarification. Preserve the required clinical prompt. "
                        "Do not add medical advice or skip the required data point. Return only the spoken line."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Language: {language}\n"
                        f"Current step: {step}\n"
                        f"Recent conversation:\n{context}\n"
                        f"Patient answer: {patient_text}\n"
                        f"Validation issue: {reason}\n"
                        f"Required clinical prompt: {clinical_prompt}"
                    ),
                },
            ],
            "temperature": 0.45,
            "max_tokens": 180,
        }
        body = self._post_json(payload)
        text = _choice_text(body)
        self.last_trace = {
            "component": "local_clinical_ai",
            "operation": "clarification_reply",
            "enabled": True,
            "model": self.model,
            "url": self.url,
            "language": language,
            "step": step,
            "reason": reason,
            "used_model": bool(text),
            "fallback": None if text else "required_clarification",
        }
        self._record_trace(self.last_trace)
        return text

    def _record_trace(self, trace: dict[str, object]) -> None:
        self.trace_events.append(dict(trace))
        if len(self.trace_events) > 200:
            self.trace_events = self.trace_events[-200:]

    def _post_json(self, payload: dict[str, object]) -> dict[str, Any] | None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None


def _understanding_from_parsed(parsed: dict[str, Any], patient_text: str) -> UnderstandingResult:
    rule_detected = detect_symptoms(patient_text)
    return UnderstandingResult(
        accepted=bool(parsed.get("accepted")),
        confidence=float(parsed.get("confidence") or 0),
        answer_type=str(parsed.get("answer_type") or "unknown"),
        value=parsed.get("value"),
        text_value=_optional_string(parsed.get("text_value")),
        identity=parsed.get("identity") if isinstance(parsed.get("identity"), dict) else None,
        red_flags=_merge_unique(parsed.get("red_flags"), rule_detected.get("red_flags")),
        non_urgent_concerns=_merge_unique(parsed.get("non_urgent_concerns"), rule_detected.get("non_urgent")),
        slots=parsed.get("slots") if isinstance(parsed.get("slots"), dict) else None,
        needs_clarification=bool(parsed.get("needs_clarification")),
        clarification_prompt=_optional_string(parsed.get("clarification_prompt")),
        raw=parsed,
    )


def _rule_only_understanding(patient_text: str) -> UnderstandingResult | None:
    detected = detect_symptoms(patient_text)
    red_flags = detected.get("red_flags")
    non_urgent = detected.get("non_urgent")
    if not red_flags and not non_urgent:
        return None
    return UnderstandingResult(
        accepted=True,
        confidence=0.55,
        answer_type="free_text",
        text_value=patient_text,
        red_flags=red_flags if isinstance(red_flags, list) else [],
        non_urgent_concerns=non_urgent if isinstance(non_urgent, list) else [],
    )


def _parse_model_json(body: dict[str, Any] | None) -> dict[str, Any] | None:
    content = _choice_text(body)
    if not content:
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _choice_text(body: dict[str, Any] | None) -> str | None:
    try:
        text = body["choices"][0]["message"]["content"].strip() if body else ""
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
    return text or None


def _format_recent_transcript(transcript: list[dict[str, str]]) -> str:
    recent = transcript[-6:]
    return "\n".join(f"{item.get('role', 'unknown')}: {item.get('text', '')}" for item in recent)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _merge_unique(*values: object) -> list[str]:
    merged: list[str] = []
    for value in values:
        if isinstance(value, list):
            for item in value:
                text = str(item).strip()
                if text and text not in merged:
                    merged.append(text)
    return merged


def _present_slot_names(slots: object) -> list[str]:
    if not isinstance(slots, dict):
        return []
    present = []
    for key, value in slots.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() in {"", "unknown"}:
            continue
        present.append(str(key))
    return sorted(present)


def _env_enabled(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}
