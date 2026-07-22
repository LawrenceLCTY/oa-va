from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.clinical_rules import detect_symptoms


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_LLM_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_OPENAI_TTS_VOICE = "marin"
DEFAULT_OPENAI_REALTIME_MODEL = "gpt-realtime"
DEFAULT_OPENAI_REALTIME_VOICE = "marin"
DEFAULT_OPENAI_TRANSCRIBE_MODEL = "gpt-4o-mini-transcribe"


@dataclass(frozen=True)
class UnderstandingResult:
    accepted: bool = False
    confidence: float = 0.0
    answer_type: str = "unknown"
    value: str | int | None = None
    text_value: str | None = None
    identity: dict[str, str | int | None] | None = None
    red_flags: list[str] | None = None
    non_urgent_concerns: list[str] | None = None
    slots: dict[str, Any] | None = None
    needs_clarification: bool = False
    clarification_prompt: str | None = None
    raw: dict[str, Any] | None = None


class OpenAIClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")
        self.llm_model = os.getenv("OPENAI_LLM_MODEL", DEFAULT_OPENAI_LLM_MODEL)
        self.tts_model = os.getenv("OPENAI_TTS_MODEL", DEFAULT_OPENAI_TTS_MODEL)
        self.tts_voice = os.getenv("OPENAI_TTS_VOICE", DEFAULT_OPENAI_TTS_VOICE)
        self.realtime_model = os.getenv("OPENAI_REALTIME_MODEL", DEFAULT_OPENAI_REALTIME_MODEL)
        self.realtime_voice = os.getenv("OPENAI_REALTIME_VOICE", DEFAULT_OPENAI_REALTIME_VOICE)
        self.transcribe_model = os.getenv("OPENAI_TRANSCRIBE_MODEL", DEFAULT_OPENAI_TRANSCRIBE_MODEL)
        self.timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
        self.understanding_enabled = _env_enabled("ENABLE_OPENAI_UNDERSTANDING")
        self.reply_rewrite_enabled = _env_enabled("ENABLE_OPENAI_REPLY_REWRITE")
        self.tts_enabled = _env_enabled("ENABLE_OPENAI_TTS")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "llm_model": self.llm_model,
            "tts_model": self.tts_model,
            "tts_voice": self.tts_voice,
            "realtime_model": self.realtime_model,
            "realtime_voice": self.realtime_voice,
            "transcribe_model": self.transcribe_model,
            "base_url": self.base_url,
            "understanding_enabled": self.understanding_enabled,
            "reply_rewrite_enabled": self.reply_rewrite_enabled,
            "tts_enabled": self.tts_enabled,
        }

    def create_realtime_session(
        self,
        session_id: str,
        language: str,
        initial_prompt: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not self.enabled:
            return None, "OPENAI_API_KEY is not set"

        session = {
            "type": "realtime",
            "model": self.realtime_model,
            "instructions": _realtime_instructions(language, session_id, initial_prompt),
            "audio": {
                "input": {
                    "transcription": {"model": self.transcribe_model},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 650,
                        "create_response": True,
                        "interrupt_response": True,
                    },
                },
                "output": {"voice": self.realtime_voice},
            },
            "tools": [_submit_patient_answer_tool()],
            "tool_choice": "auto",
        }
        body = self._post_json("/realtime/client_secrets", {"session": session})
        if body and "error" in body:
            body = self._post_json("/realtime/client_secrets", {"session": _legacy_realtime_session(session)})
        if not body:
            return None, "Could not create OpenAI Realtime session"
        if "error" in body:
            error = body.get("error")
            if isinstance(error, dict):
                return None, _clean_error_message(error.get("message"))
            return None, _clean_error_message(error)
        body.setdefault("model", self.realtime_model)
        return body, None

    def understand(self, step: str, language: str, patient_text: str) -> UnderstandingResult | None:
        if not self.enabled or not self.understanding_enabled:
            return None

        schema = {
            "name": "clinical_answer_understanding",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "accepted": {"type": "boolean"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "answer_type": {
                        "type": "string",
                        "enum": [
                            "yes",
                            "no",
                            "uncertain",
                            "pain_score",
                            "identity",
                            "respondent_source",
                            "comparison",
                            "free_text",
                            "symptom_status",
                            "symptom_severity",
                            "unknown",
                        ],
                    },
                    "value": {
                        "type": ["string", "integer", "null"],
                        "description": "Canonical value for the current step. Use 0-10 integer for pain scores.",
                    },
                    "text_value": {
                        "type": ["string", "null"],
                        "description": "Short faithful summary of the patient's answer, in their language.",
                    },
                    "identity": {
                        "type": ["object", "null"],
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": ["string", "null"]},
                            "mobile_number": {"type": ["string", "null"]},
                            "age": {"type": ["integer", "null"], "minimum": 0, "maximum": 120},
                        },
                        "required": ["name", "mobile_number", "age"],
                    },
                    "red_flags": {"type": "array", "items": {"type": "string"}},
                    "non_urgent_concerns": {"type": "array", "items": {"type": "string"}},
                    "slots": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "respondent_source": {
                                "type": ["string", "null"],
                                "enum": [
                                    "participant_independently",
                                    "participant_with_caregiver_assistance",
                                    "caregiver_proxy",
                                    "unknown",
                                    None,
                                ],
                            },
                            "average_24h_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 10},
                            "current_pain_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 10},
                            "pain_location": {"type": ["string", "null"]},
                            "functional_impact": {"type": ["string", "null"]},
                            "usual_comparison": {
                                "type": ["string", "null"],
                                "enum": ["better", "worse", "same", "unknown", None],
                            },
                            "treatment_context": {"type": ["string", "null"]},
                            "side_effect_screening_result": {
                                "type": ["string", "null"],
                                "enum": ["yes", "no", "uncertain", "unknown", None],
                            },
                            "side_effect_description": {"type": ["string", "null"]},
                            "symptom_start_time": {"type": ["string", "null"]},
                            "symptom_status": {
                                "type": ["string", "null"],
                                "enum": ["ongoing", "resolved", "unknown", None],
                            },
                            "symptom_severity": {
                                "type": ["string", "null"],
                                "enum": ["mild", "moderate", "severe", "unknown", None],
                            },
                            "medication_changed": {
                                "type": ["string", "null"],
                                "enum": ["yes", "no", "uncertain", "unknown", None],
                            },
                            "doctor_contacted": {
                                "type": ["string", "null"],
                                "enum": ["yes", "no", "uncertain", "unknown", None],
                            },
                            "emergency_visit_or_hospitalization": {
                                "type": ["string", "null"],
                                "enum": ["yes", "no", "uncertain", "unknown", None],
                            },
                        },
                        "required": [
                            "respondent_source",
                            "average_24h_score",
                            "current_pain_score",
                            "pain_location",
                            "functional_impact",
                            "usual_comparison",
                            "treatment_context",
                            "side_effect_screening_result",
                            "side_effect_description",
                            "symptom_start_time",
                            "symptom_status",
                            "symptom_severity",
                            "medication_changed",
                            "doctor_contacted",
                            "emergency_visit_or_hospitalization",
                        ],
                    },
                    "needs_clarification": {"type": "boolean"},
                    "clarification_prompt": {"type": ["string", "null"]},
                },
                "required": [
                    "accepted",
                    "confidence",
                    "answer_type",
                    "value",
                    "text_value",
                    "identity",
                    "red_flags",
                    "non_urgent_concerns",
                    "slots",
                    "needs_clarification",
                    "clarification_prompt",
                ],
            },
            "strict": True,
        }
        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract structured answers for an osteoarthritis phone follow-up. "
                        "Do not diagnose or give advice. Preserve clinical safety. "
                        "Use canonical values: yes/no/uncertain; comparison better/worse/same/unknown; "
                        "respondent_source participant_independently/participant_with_caregiver_assistance/"
                        "caregiver_proxy/unknown; symptom_status ongoing/resolved/unknown; "
                        "symptom_severity mild/moderate/severe/unknown. "
                        "Also extract any clinical slots the patient volunteered, even if they are not the current step."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Language: {language}\n"
                        f"Current protocol step: {step}\n"
                        f"Patient answer: {patient_text}\n\n"
                        "Return only structured data. If the answer is too ambiguous for this step, "
                        "set accepted=false and needs_clarification=true."
                    ),
                },
            ],
            "response_format": {"type": "json_schema", "json_schema": schema},
            "temperature": 0.0,
        }
        body = self._post_json("/chat/completions", payload)
        if not body:
            return None
        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return None

        rule_detected = detect_symptoms(patient_text)
        red_flags = _merge_unique(parsed.get("red_flags"), rule_detected.get("red_flags"))
        non_urgent = _merge_unique(parsed.get("non_urgent_concerns"), rule_detected.get("non_urgent"))
        return UnderstandingResult(
            accepted=bool(parsed.get("accepted")),
            confidence=float(parsed.get("confidence") or 0),
            answer_type=str(parsed.get("answer_type") or "unknown"),
            value=parsed.get("value"),
            text_value=_optional_string(parsed.get("text_value")),
            identity=parsed.get("identity") if isinstance(parsed.get("identity"), dict) else None,
            red_flags=red_flags,
            non_urgent_concerns=non_urgent,
            slots=parsed.get("slots") if isinstance(parsed.get("slots"), dict) else None,
            needs_clarification=bool(parsed.get("needs_clarification")),
            clarification_prompt=_optional_string(parsed.get("clarification_prompt")),
            raw=parsed,
        )

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
            "model": self.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the voice of a warm, concise clinical research phone check-in. "
                        "Turn the required next protocol line into one natural spoken reply. "
                        "Briefly acknowledge the patient's last answer when useful, then ask the required next question. "
                        "Keep the same language as the required line. Keep all numbers, safety instructions, and clinical meaning. "
                        "Do not diagnose, prescribe, add new clinical questions, or remove urgent-care wording. "
                        "Use everyday speech, not form language. Return only what should be spoken."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Language: {language}\n"
                        f"Recent conversation:\n{context}\n\n"
                        f"Required next protocol line:\n{clinical_message}"
                    ),
                },
            ],
            "temperature": 0.65,
            "max_tokens": 140,
        }
        body = self._post_json("/chat/completions", payload)
        try:
            content = body["choices"][0]["message"]["content"].strip() if body else ""
        except (KeyError, IndexError, TypeError, AttributeError):
            return None
        return content or None

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
            "model": self.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a warm clinical research phone caller. The patient did not answer the current "
                        "protocol item in a usable way. Do not simply repeat the same question. Briefly acknowledge "
                        "what they said, explain in plain language what kind of answer is needed, and ask one clear "
                        "follow-up that helps them answer. Keep the same language as the prompt. Do not diagnose, "
                        "give medical advice, add extra clinical items, or skip the required data point. Return only "
                        "the spoken reply."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Language: {language}\n"
                        f"Current protocol step: {step}\n"
                        f"Recent conversation:\n{context}\n\n"
                        f"Patient answer that was hard to use: {patient_text}\n"
                        f"Validation issue: {reason}\n"
                        f"Required clinical prompt to preserve: {clinical_prompt}"
                    ),
                },
            ],
            "temperature": 0.7,
            "max_tokens": 160,
        }
        body = self._post_json("/chat/completions", payload)
        try:
            content = body["choices"][0]["message"]["content"].strip() if body else ""
        except (KeyError, IndexError, TypeError, AttributeError):
            return None
        return content or None

    def synthesize_speech(self, text: str, language: str) -> tuple[bytes | None, str, str | None]:
        if not self.enabled:
            return None, "audio/mpeg", "OPENAI_API_KEY is not set"
        if not self.tts_enabled:
            return None, "audio/mpeg", "OpenAI TTS is disabled"
        payload = {
            "model": self.tts_model,
            "voice": self.tts_voice,
            "input": text[:1200],
            "response_format": "mp3",
            "instructions": _tts_instructions(language),
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/audio/speech",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read(), "audio/mpeg", None
        except (urllib.error.URLError, TimeoutError) as exc:
            return None, "audio/mpeg", f"{type(exc).__name__}: {exc}"

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, Any] | None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                error_body = str(exc)
            return {"error": {"message": error_body, "status": exc.code}}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


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


def _tts_instructions(language: str) -> str:
    if language == "zh-CN":
        return (
            "自然的普通话电话随访声音。语气温和、像真人护士或研究助理，"
            "有轻微停顿和自然语调，不要像播报、客服脚本或机器人。语速稍慢但不要拖。"
        )
    return (
        "Natural phone-call voice for an older adult check-in. Warm, human, lightly conversational, "
        "with natural pauses and intonation. Do not sound like a script, announcer, IVR, or robot."
    )


def _realtime_instructions(language: str, session_id: str, initial_prompt: str) -> str:
    if language == "zh-CN":
        language_rule = "Speak Mandarin Chinese unless the patient clearly switches language."
    else:
        language_rule = "Speak English unless the patient clearly switches language."
    return (
        "You are a warm, concise voice assistant conducting an osteoarthritis medication and treatment questionnaire. "
        "This is a research prototype, not emergency care. Sound natural in a live phone conversation: "
        "short acknowledgements, one question at a time, no long monologues. "
        f"{language_rule} "
        "A deterministic clinical engine controls the protocol, safety escalation, and report. "
        "After each patient answer, call submit_patient_answer with the exact session_id and the patient's answer. "
        "Then use the tool result's assistant_messages as the next required clinical line. You may make the wording "
        "slightly more conversational, but preserve clinical meaning, numbers, and urgent-care instructions. "
        "Do not diagnose, prescribe, ask unrelated questions, or skip required protocol items. "
        "If the patient reports possible urgent symptoms, keep the urgent-care wording from the tool result. "
        f"The clinical session id is {session_id}. "
        f"Start the conversation by saying this required first line naturally: {initial_prompt}"
    )


def _submit_patient_answer_tool() -> dict[str, object]:
    return {
        "type": "function",
        "name": "submit_patient_answer",
        "description": (
            "Submit the patient's latest answer to the clinical protocol engine. "
            "Call this once after each patient answer before asking the next clinical question."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The clinical session id supplied by the app.",
                },
                "answer": {
                    "type": "string",
                    "description": "A faithful transcript or concise summary of the patient's answer.",
                },
            },
            "required": ["session_id", "answer"],
        },
    }


def _legacy_realtime_session(session: dict[str, object]) -> dict[str, object]:
    audio = session.get("audio") if isinstance(session.get("audio"), dict) else {}
    audio_input = audio.get("input") if isinstance(audio.get("input"), dict) else {}
    audio_output = audio.get("output") if isinstance(audio.get("output"), dict) else {}
    return {
        "model": session.get("model"),
        "voice": audio_output.get("voice"),
        "modalities": ["audio", "text"],
        "instructions": session.get("instructions"),
        "input_audio_transcription": audio_input.get("transcription"),
        "turn_detection": audio_input.get("turn_detection"),
        "tools": session.get("tools"),
        "tool_choice": session.get("tool_choice"),
    }


def _format_recent_transcript(transcript: list[dict[str, str]], limit: int = 6) -> str:
    items = transcript[-limit:]
    if not items:
        return "(none)"
    lines = []
    for item in items:
        role = item.get("role", "unknown")
        text = item.get("text", "")
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _clean_error_message(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "Could not create OpenAI Realtime session"
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    error = parsed.get("error") if isinstance(parsed, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or text)
    return text
