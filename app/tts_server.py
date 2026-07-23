from __future__ import annotations

import json
import os
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv

from app.conversation import ConversationEngine
from app.questionnaire import QUESTIONNAIRE_STEP_KEYS, clarification_for_step, prompt_for_step
from app.tts import LocalTTS


ROOT_DIR = Path(__file__).resolve().parent.parent

load_dotenv(ROOT_DIR / ".env")

TTS = LocalTTS(allow_remote_service=False)
WARMUP_LINES = {
    "zh-CN": "您好，我是骨关节炎疼痛随访助手。",
    "en": "Hello, I am your osteoarthritis pain check-in assistant.",
}
ENGINE = ConversationEngine()


def warmup_lines() -> list[tuple[str, str]]:
    lines = list(WARMUP_LINES.items())
    for language in ("zh-CN", "en"):
        state = ENGINE.start(language)
        assistant_messages = [
            item.get("text", "")
            for item in state.transcript
            if item.get("role") == "assistant"
        ]
        lines.extend((language, message) for message in assistant_messages if message)
        if _warmup_all_questionnaire_enabled():
            for step in QUESTIONNAIRE_STEP_KEYS:
                lines.append((language, prompt_for_step(step, language)))
                lines.append((language, clarification_for_step(step, language)))
    seen = set()
    deduped = []
    for language, text in lines:
        key = (language, text)
        if key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


class TTSRequestHandler(BaseHTTPRequestHandler):
    server_version = "OAVATTSService/0.1"

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json({"ok": True, "tts": TTS.status()})
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/api/warmup":
            results = warmup()
            ok = any(item.get("ok") for item in results)
            self._send_json({"ok": ok, "results": results, "tts": TTS.status()})
            return

        if self.path != "/api/tts":
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        started = time.perf_counter()
        data = self._read_json()
        text = str(data.get("text", ""))
        language = str(data.get("language", "en"))
        audio, content_type, err = TTS.synthesize(text, language)
        latency_ms = int((time.perf_counter() - started) * 1000)
        if not audio:
            self._send_json(
                {"error": err or "tts unavailable", "trace": TTS.last_trace, "latency_ms": latency_ms},
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return
        trace = TTS.last_trace if isinstance(TTS.last_trace, dict) else {}
        self._send_bytes(
            audio,
            content_type,
            headers={
                "X-TTS-Latency-Ms": str(latency_ms),
                "X-TTS-Engine": str(trace.get("engine") or "unknown"),
                "X-TTS-Cached": str(trace.get("cached", "")).lower(),
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(
        self,
        body: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


def _warmup_all_questionnaire_enabled() -> bool:
    return os.getenv("TTS_WARMUP_ALL_QUESTIONNAIRE", "").strip().lower() in {"1", "true", "yes", "on"}


def warmup() -> list[dict[str, object]]:
    results = []
    for language, text in warmup_lines():
        started = time.perf_counter()
        audio, content_type, err = TTS.synthesize(text, language)
        results.append(
            {
                "language": language,
                "text": text,
                "ok": bool(audio),
                "content_type": content_type,
                "audio_bytes": len(audio) if audio else 0,
                "error": err,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "trace": TTS.last_trace,
            }
        )
    return results


def run(host: str = "127.0.0.1", port: int = 8002) -> None:
    if os.getenv("TTS_WARMUP_ON_START", "").strip().lower() in {"1", "true", "yes", "on"}:
        print(json.dumps({"warmup": warmup()}, ensure_ascii=False, indent=2))
    server = ThreadingHTTPServer((host, port), TTSRequestHandler)
    print(f"OA TTS service running at http://{host}:{port}/api/tts")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run(os.getenv("TTS_HOST", "127.0.0.1"), int(os.getenv("TTS_PORT", "8002")))
