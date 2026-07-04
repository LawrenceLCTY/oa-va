from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv

from app.conversation import ConversationEngine
from app.covo import CovoClient
from app.i18n import intent
from app.local_ai import LocalClinicalAI
from app.openai_client import OpenAIClient
from app.private_pipeline import PrivateVoicePipeline
from app.schemas import ConversationState
from app.stt import LocalSTT
from app.tts import LocalTTS


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
REPORTS_DIR = ROOT_DIR / "reports"

load_dotenv(ROOT_DIR / ".env")

SESSIONS: dict[str, ConversationState] = {}
LOCAL_AI = LocalClinicalAI()
ENGINE = ConversationEngine(ai=LOCAL_AI)
TTS = LocalTTS()
STT = LocalSTT()
OPENAI = OpenAIClient()
COVO = CovoClient()
PRIVATE_PIPELINE = PrivateVoicePipeline(ENGINE, STT, TTS)


class OARequestHandler(BaseHTTPRequestHandler):
    server_version = "OAHomePainAssistant/0.3"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "sessions": len(SESSIONS)})
            return
        if parsed.path == "/api/voice_status":
            openai_status = OPENAI.status()
            self._send_json(
                {
                    "tts": TTS.status(),
                    "stt": STT.status(),
                    "openai": openai_status,
                    "realtime": {
                        "enabled": bool(openai_status.get("enabled")),
                        "model": openai_status.get("realtime_model"),
                        "voice": openai_status.get("realtime_voice"),
                    },
                    "covo": COVO.status(),
                    "private_pipeline": PRIVATE_PIPELINE.status(),
                    "local_ai": LOCAL_AI.status(),
                    "fallback": {
                        "enabled": True,
                        "mode": "v0.7 private explainable pipeline with deterministic clinical conversation, local STT/TTS, and browser transcript fallback",
                    },
                }
            )
            return
        if parsed.path == "/api/state":
            query = parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            state = SESSIONS.get(session_id)
            if not state:
                self._send_json({"error": "session not found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(state.to_dict())
            return
        if parsed.path == "/":
            self._send_static(STATIC_DIR / "index.html")
            return
        if parsed.path.startswith("/static/"):
            relative = parsed.path.removeprefix("/static/")
            self._send_static(STATIC_DIR / relative)
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/start":
            data = self._read_json()
            language = str(data.get("language", "en"))
            state = ENGINE.start(language=language)
            SESSIONS[state.session_id] = state
            self._send_json(
                {
                    "session_id": state.session_id,
                    "assistant_messages": [
                        item["text"]
                        for item in state.transcript
                        if item.get("role") == "assistant"
                    ],
                    "state": state.to_dict(),
                }
            )
            return

        if parsed.path == "/api/realtime/start":
            data = self._read_json()
            language = str(data.get("language", "en"))
            state = ENGINE.start(language=language)
            SESSIONS[state.session_id] = state
            assistant_messages = [
                item["text"]
                for item in state.transcript
                if item.get("role") == "assistant"
            ]
            session, err = OPENAI.create_realtime_session(
                state.session_id,
                state.language,
                " ".join(assistant_messages),
            )
            if not session:
                self._send_json({"error": err or "realtime unavailable"}, HTTPStatus.SERVICE_UNAVAILABLE)
                return
            self._send_json(
                {
                    "session_id": state.session_id,
                    "realtime": session,
                    "assistant_messages": assistant_messages,
                    "state": state.to_dict(),
                }
            )
            return

        if parsed.path == "/api/message":
            data = self._read_json()
            session_id = str(data.get("session_id", ""))
            text = str(data.get("text", ""))
            state = SESSIONS.get(session_id)
            if not state:
                self._send_json({"error": "session not found"}, HTTPStatus.NOT_FOUND)
                return

            before = len(state.transcript)
            ENGINE.handle_user_message(state, text)
            assistant_messages = [
                item["text"]
                for item in state.transcript[before:]
                if item.get("role") == "assistant"
            ]
            self._send_json(
                {
                    "session_id": state.session_id,
                    "assistant_messages": assistant_messages,
                    "state": state.to_dict(),
                }
            )
            return

        if parsed.path == "/api/realtime/tool":
            data = self._read_json()
            name = str(data.get("name", ""))
            arguments = data.get("arguments", {})
            if name != "submit_patient_answer":
                self._send_json({"error": "unknown tool"}, HTTPStatus.BAD_REQUEST)
                return
            if not isinstance(arguments, dict):
                self._send_json({"error": "invalid tool arguments"}, HTTPStatus.BAD_REQUEST)
                return
            session_id = str(arguments.get("session_id", ""))
            text = str(arguments.get("answer", ""))
            state = SESSIONS.get(session_id)
            if not state:
                self._send_json({"error": "session not found"}, HTTPStatus.NOT_FOUND)
                return

            before = len(state.transcript)
            ENGINE.handle_user_message(state, text)
            assistant_messages = [
                item["text"]
                for item in state.transcript[before:]
                if item.get("role") == "assistant"
            ]
            self._send_json(
                {
                    "ok": True,
                    "session_id": state.session_id,
                    "assistant_messages": assistant_messages,
                    "spoken_instruction": _spoken_instruction(assistant_messages, state.step, state.complete),
                    "state": state.to_dict(),
                }
            )
            return

        if parsed.path == "/api/private/start":
            data = self._read_json()
            language = str(data.get("language", "en"))
            state = ENGINE.start(language=language)
            SESSIONS[state.session_id] = state
            assistant_messages = [
                item["text"]
                for item in state.transcript
                if item.get("role") == "assistant"
            ]
            self._send_json(
                {
                    "session_id": state.session_id,
                    "assistant_messages": assistant_messages,
                    "spoken_instruction": _spoken_instruction(assistant_messages, state.step, state.complete),
                    "state": state.to_dict(),
                    "pipeline": PRIVATE_PIPELINE.status(),
                }
            )
            return

        if parsed.path == "/api/private/turn":
            audio, filename = self._read_audio_upload()
            session_id = self.headers.get("X-Session-Id", "")
            language = self.headers.get("X-Language", "en")
            fallback_text = unquote(self.headers.get("X-Transcript", ""))
            state = SESSIONS.get(session_id)
            if not state:
                self._send_json({"error": "session not found"}, HTTPStatus.NOT_FOUND)
                return

            result = PRIVATE_PIPELINE.process_turn(
                state,
                audio,
                filename=filename,
                language=language,
                fallback_text=fallback_text,
            )
            if not result.transcript:
                self._send_json(
                    {
                        "error": "; ".join(result.errors) or "private pipeline did not produce a transcript",
                        "pipeline": PRIVATE_PIPELINE.status(),
                        "timings": result.timings,
                    },
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return

            self._send_json(
                {
                    "ok": True,
                    "session_id": state.session_id,
                    "transcript": result.transcript,
                    "transcript_source": result.transcript_source,
                    "assistant_messages": result.assistant_messages,
                    "spoken_instruction": _spoken_instruction(result.assistant_messages, state.step, state.complete),
                    "state": state.to_dict(),
                    "pipeline": {
                        "mode": "private_explainable_pipeline",
                        "errors": result.errors,
                        "timings": result.timings,
                        "model_event": state.model_events[-1] if state.model_events else None,
                    },
                }
            )
            return

        if parsed.path == "/api/covo/start":
            data = self._read_json()
            language = str(data.get("language", "en"))
            state = ENGINE.start(language=language)
            SESSIONS[state.session_id] = state
            assistant_messages = [
                item["text"]
                for item in state.transcript
                if item.get("role") == "assistant"
            ]
            self._send_json(
                {
                    "session_id": state.session_id,
                    "assistant_messages": assistant_messages,
                    "spoken_instruction": _spoken_instruction(assistant_messages, state.step, state.complete),
                    "state": state.to_dict(),
                    "covo": COVO.status(),
                }
            )
            return

        if parsed.path == "/api/covo/turn":
            audio, filename = self._read_audio_upload()
            session_id = self.headers.get("X-Session-Id", "")
            language = self.headers.get("X-Language", "en")
            fallback_text = unquote(self.headers.get("X-Transcript", ""))
            state = SESSIONS.get(session_id)
            if not state:
                self._send_json({"error": "session not found"}, HTTPStatus.NOT_FOUND)
                return

            covo_result = None
            if COVO.enabled:
                last_prompt = _last_assistant_message(state)
                covo_result = COVO.process_turn(
                    audio,
                    filename=filename,
                    language=language,
                    session_id=session_id,
                    prompt=last_prompt,
                    state=state.to_dict(),
                )
            transcript = (covo_result.transcript if covo_result else None) or fallback_text.strip()
            if not transcript:
                self._send_json(
                    {
                        "error": (covo_result.error if covo_result else None) or "Covo did not return a transcript",
                        "covo": COVO.status(),
                    },
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return

            before = len(state.transcript)
            ENGINE.handle_user_message(state, transcript)
            assistant_messages = [
                item["text"]
                for item in state.transcript[before:]
                if item.get("role") == "assistant"
            ]
            self._send_json(
                {
                    "ok": True,
                    "session_id": state.session_id,
                    "transcript": transcript,
                    "assistant_messages": assistant_messages,
                    "spoken_instruction": _spoken_instruction(assistant_messages, state.step, state.complete),
                    "state": state.to_dict(),
                    "covo": {
                        "used": bool(covo_result and covo_result.transcript),
                        "error": covo_result.error if covo_result else None,
                        "audio_available": bool(covo_result and covo_result.audio),
                        "content_type": covo_result.content_type if covo_result else "audio/wav",
                    },
                }
            )
            return

        if parsed.path == "/api/save_report":
            data = self._read_json()
            session_id = str(data.get("session_id", ""))
            state = SESSIONS.get(session_id)
            if not state:
                self._send_json({"error": "session not found"}, HTTPStatus.NOT_FOUND)
                return
            if not state.report:
                self._send_json({"error": "report is not ready"}, HTTPStatus.BAD_REQUEST)
                return

            REPORTS_DIR.mkdir(exist_ok=True)
            filename = f"oa-report-{state.created_at.replace(':', '-')}-{state.session_id[:8]}.json"
            path = REPORTS_DIR / filename
            path.write_text(state.report, encoding="utf-8")
            self._send_json({"saved": True, "path": str(path)})
            return

        if parsed.path == "/api/tts":
            data = self._read_json()
            text = str(data.get("text", ""))
            language = str(data.get("language", "en"))
            audio, content_type, err = TTS.synthesize(text, language)
            if not audio:
                self._send_json({"error": err or "tts unavailable"}, HTTPStatus.SERVICE_UNAVAILABLE)
                return
            self._send_bytes(audio, content_type)
            return

        if parsed.path == "/api/stt":
            audio, filename = self._read_audio_upload()
            language = self.headers.get("X-Language", "en")
            text, err = STT.transcribe(audio, filename, language)
            if not text:
                self._send_json({"error": err or "stt unavailable"}, HTTPStatus.SERVICE_UNAVAILABLE)
                return
            self._send_json({"text": text})
            return

        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        if isinstance(data, dict):
            return data
        return {}

    def _read_audio_upload(self) -> tuple[bytes, str]:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b""
        filename = self.headers.get("X-Filename", "speech.webm")
        return body, filename

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path: Path) -> None:
        safe_path = path.resolve()
        if not str(safe_path).startswith(str(STATIC_DIR.resolve())):
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        if not safe_path.is_file():
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(str(safe_path))[0] or "application/octet-stream"
        body = safe_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), OARequestHandler)
    print(f"OA Home Pain Check-in Assistant running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


def _spoken_instruction(assistant_messages: list[str], step: str, complete: bool) -> str:
    required = " ".join(message.strip() for message in assistant_messages if message.strip())
    if complete:
        return f"Say this closing message naturally, then stop: {required}"
    slot_intent = intent(_prompt_key_for_step(step))
    intent_clause = f" The clinical intent is: {slot_intent}." if slot_intent else ""
    return (
        "Say this next required clinical line naturally and briefly. Preserve all clinical meaning, "
        f"numbers, and safety wording.{intent_clause} Required line: {required}"
    )


def _last_assistant_message(state: ConversationState) -> str:
    for item in reversed(state.transcript):
        if item.get("role") == "assistant":
            return item.get("text", "")
    return ""


def _prompt_key_for_step(step: str) -> str:
    return {
        "readiness_hearing": "hearing_check",
        "readiness_time": "time_check",
        "permission": "permission_check",
        "identity": "identity_prompt",
        "respondent_source": "respondent_source",
        "average_pain_score": "average_pain_prompt",
        "current_pain_score": "current_pain_prompt",
        "pain_location": "pain_location",
        "functional_impact": "functional_impact",
        "usual_comparison": "comparison",
        "treatment_context": "treatment",
        "side_effects": "side_effects",
        "side_effect_description": "side_effect_description",
        "side_effect_start": "side_effect_start",
        "side_effect_status": "side_effect_status",
        "side_effect_severity": "side_effect_severity",
        "medication_changed": "medication_changed",
        "doctor_contacted": "doctor_contacted",
        "emergency_visit": "emergency_visit",
        "red_flags": "red_flags",
    }.get(step, step)


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    run(host, port)
