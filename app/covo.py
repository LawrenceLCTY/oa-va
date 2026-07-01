from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DEFAULT_COVO_MODEL_DIR = "/hdd-storage/lawrencelcty/huggingface/models/Covo-Audio/covoaudio"
DEFAULT_COVO_DEVICE = "cuda:2,cuda:3"


@dataclass
class CovoTurnResult:
    transcript: str | None = None
    audio: bytes | None = None
    content_type: str = "audio/wav"
    error: str | None = None
    raw: dict[str, object] | None = None


class CovoClient:
    """Adapter for an experimental Covo half-duplex service.

    The OA app does not load the Covo model directly. A separate GPU service can
    implement this contract and return a patient transcript plus optional audio.
    """

    def __init__(self) -> None:
        self.endpoint = os.getenv("COVO_ENDPOINT", "").strip().rstrip("/")
        self.model_dir = os.getenv("COVO_MODEL_DIR", DEFAULT_COVO_MODEL_DIR)
        self.device = os.getenv("COVO_DEVICE", DEFAULT_COVO_DEVICE)
        self.timeout = float(os.getenv("COVO_TIMEOUT_SECONDS", "120"))

    @property
    def enabled(self) -> bool:
        return _env_enabled("ENABLE_COVO") and bool(self.endpoint)

    def status(self) -> dict[str, object]:
        model_path = Path(self.model_dir)
        return {
            "enabled": self.enabled,
            "configured": bool(self.endpoint),
            "endpoint": self.endpoint,
            "mode": "half_duplex_experimental",
            "model_dir": str(model_path),
            "model_dir_found": model_path.exists(),
            "device": self.device,
            "timeout_seconds": self.timeout,
            "contract": {
                "turn_endpoint": "POST {COVO_ENDPOINT}/turn",
                "returns": "JSON with transcript and optional base64 audio",
            },
        }

    def process_turn(
        self,
        audio: bytes,
        *,
        filename: str,
        language: str,
        session_id: str,
        prompt: str,
        state: dict[str, object],
    ) -> CovoTurnResult:
        if not self.enabled:
            return CovoTurnResult(error="Covo half-duplex service is not configured")
        if not audio:
            return CovoTurnResult(error="empty audio")

        payload = {
            "session_id": session_id,
            "language": language,
            "filename": filename,
            "audio_b64": base64.b64encode(audio).decode("ascii"),
            "audio_content_type": _content_type_for_filename(filename),
            "clinical_prompt": prompt,
            "state": state,
        }
        try:
            req = urllib.request.Request(
                f"{self.endpoint}/turn",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read()
                data = json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return CovoTurnResult(error=f"Covo service HTTP {exc.code}: {detail[:300]}")
        except Exception as exc:
            return CovoTurnResult(error=f"{type(exc).__name__}: {exc}")

        if not isinstance(data, dict):
            return CovoTurnResult(error="Covo service returned invalid JSON")

        transcript = _clean_text(str(data.get("transcript") or data.get("text") or ""))
        audio_b64 = str(data.get("audio_b64") or "")
        audio_bytes = None
        if audio_b64:
            try:
                audio_bytes = base64.b64decode(audio_b64)
            except Exception:
                audio_bytes = None
        return CovoTurnResult(
            transcript=transcript or None,
            audio=audio_bytes,
            content_type=str(data.get("audio_content_type") or data.get("content_type") or "audio/wav"),
            raw=data,
        )


def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())


def _content_type_for_filename(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".wav"):
        return "audio/wav"
    if lower.endswith(".mp3"):
        return "audio/mpeg"
    if lower.endswith(".ogg") or lower.endswith(".opus"):
        return "audio/ogg"
    return "audio/webm"


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
