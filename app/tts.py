from __future__ import annotations

import hashlib
import json
import math
import tempfile
import wave
from pathlib import Path
from typing import Any


KOKORO_REPO_ID = "hexgrad/Kokoro-82M-v1.1-zh"
KOKORO_LOCAL_DIR = "/home/lawrencelcty/huggingface/models/hexgrad/Kokoro-82M-v1.1-zh"
KOKORO_SAMPLE_RATE = 24000
KOKORO_ZH_VOICE = "zf_001"
KOKORO_EN_VOICE = "af_maple"
DEFAULT_TTS_CACHE_DIR = Path(tempfile.gettempdir()) / "oa_voice_assistant_tts"


class LocalTTS:
    """Kokoro local TTS adapter."""

    def __init__(self) -> None:
        self.cache_dir = DEFAULT_TTS_CACHE_DIR
        self._pipelines: dict[str, Any] = {}

    def status(self) -> dict[str, object]:
        return {
            "enabled": True,
            "engine": "kokoro",
            "repo_id": KOKORO_REPO_ID,
            "local_dir": KOKORO_LOCAL_DIR,
            "local_dir_found": Path(KOKORO_LOCAL_DIR).exists(),
            "sample_rate": KOKORO_SAMPLE_RATE,
            "zh_voice": KOKORO_ZH_VOICE,
            "en_voice": KOKORO_EN_VOICE,
            "loaded_languages": sorted(self._pipelines),
        }

    @property
    def enabled(self) -> bool:
        return True

    def synthesize(self, text: str, language: str) -> tuple[bytes | None, str, str | None]:
        cleaned = _clean_text(text)
        if not cleaned:
            return None, "audio/wav", "empty tts text"

        lang_code = _kokoro_lang_code(language)
        voice = _kokoro_voice(language)
        cache_path = self._cache_path(cleaned, lang_code, voice)
        if cache_path.exists():
            return cache_path.read_bytes(), "audio/wav", None

        try:
            audio = self._synthesize_kokoro(cleaned, lang_code, voice)
            self._write_cache(cache_path, audio)
            return audio, "audio/wav", None
        except Exception as exc:
            return None, "audio/wav", f"{type(exc).__name__}: {exc}"

    def _synthesize_kokoro(self, text: str, lang_code: str, voice: str) -> bytes:
        pipeline = self._pipeline(lang_code)
        chunks = []
        generator = pipeline(text, voice=voice, speed=1, split_pattern=r"\n+")
        for _, _, audio in generator:
            chunks.append(audio)
        return _chunks_to_wav(chunks)

    def _pipeline(self, lang_code: str) -> Any:
        if lang_code not in self._pipelines:
            try:
                from kokoro import KPipeline
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Kokoro TTS is not installed. Install with: "
                    "python3 -m pip install 'kokoro>=0.9.4' 'misaki[zh]>=0.8.2' soundfile"
                ) from exc
            self._pipelines[lang_code] = KPipeline(lang_code=lang_code, repo_id=KOKORO_REPO_ID)
        return self._pipelines[lang_code]

    def preload(self, languages: tuple[str, ...] = ("zh-CN", "en")) -> None:
        for language in languages:
            self._pipeline(_kokoro_lang_code(language))

    def _cache_path(self, text: str, lang_code: str, voice: str) -> Path:
        key = json.dumps(
            {"text": text, "lang_code": lang_code, "voice": voice, "repo_id": KOKORO_REPO_ID},
            sort_keys=True,
            ensure_ascii=False,
        )
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{digest}.wav"

    def _write_cache(self, path: Path, data: bytes) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())[:500]


def _kokoro_lang_code(language: str) -> str:
    return "z" if language == "zh-CN" else "a"


def _kokoro_voice(language: str) -> str:
    return KOKORO_ZH_VOICE if language == "zh-CN" else KOKORO_EN_VOICE


def _chunks_to_wav(chunks: list[Any]) -> bytes:
    import io

    import numpy as np

    if not chunks:
        return _silent_wav()

    arrays = [np.asarray(chunk, dtype=np.float32).reshape(-1) for chunk in chunks]
    audio = np.concatenate(arrays)
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16).tobytes()
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(KOKORO_SAMPLE_RATE)
            wav.writeframes(pcm)
        return buffer.getvalue()


def _silent_wav(sample_rate: int = KOKORO_SAMPLE_RATE, duration_seconds: float = 0.1) -> bytes:
    import io

    frames = b"".join(
        int(0).to_bytes(2, byteorder="little", signed=True)
        for _ in range(math.ceil(sample_rate * duration_seconds))
    )
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(frames)
        return buffer.getvalue()
