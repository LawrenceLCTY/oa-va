from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_SENSEVOICE_MODEL = "/home/lawrencelcty/huggingface/models/FunAudioLLM/SenseVoiceSmall"


class LocalSTT:
    """Lazy local SenseVoiceSmall speech-to-text adapter."""

    def __init__(self) -> None:
        self.model_path = os.getenv("SENSEVOICE_MODEL", DEFAULT_SENSEVOICE_MODEL)
        self.device = os.getenv("SENSEVOICE_DEVICE", "cuda")
        self.prefer_local = _env_enabled("PREFER_LOCAL_STT")
        self._model: Any | None = None

    def status(self) -> dict[str, object]:
        model_found = Path(self.model_path).exists()
        return {
            "enabled": self.prefer_local and model_found,
            "prefer_local": self.prefer_local,
            "engine": "SenseVoiceSmall",
            "model_path": self.model_path,
            "model_path_found": model_found,
            "device": self.device,
            "loaded": self._model is not None,
        }

    def transcribe(self, audio: bytes, filename: str, language: str) -> tuple[str | None, str | None]:
        if not self.prefer_local:
            return None, "local STT is disabled"
        if not audio:
            return None, "empty audio"
        suffix = _suffix(filename)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as handle:
            handle.write(audio)
            handle.flush()
            return self._transcribe_file(Path(handle.name), language)

    def _transcribe_file(self, path: Path, language: str) -> tuple[str | None, str | None]:
        try:
            model = self._load_model()
            result = model.generate(
                input=str(path),
                cache={},
                language="zh" if language == "zh-CN" else "en",
                use_itn=True,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15,
            )
            return _extract_text(result), None
        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}"

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"SenseVoice model path not found: {self.model_path}")
        try:
            from funasr import AutoModel
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "FunASR is not installed. Install with: python3 -m pip install funasr modelscope torchaudio"
            ) from exc
        self._model = AutoModel(
            model=self.model_path,
            trust_remote_code=True,
            device=self.device,
            disable_update=True,
        )
        return self._model


def _suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac"} else ".webm"


def _extract_text(result: object) -> str:
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict):
            return str(first.get("text", "")).strip()
    if isinstance(result, dict):
        return str(result.get("text", "")).strip()
    return str(result).strip()


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
