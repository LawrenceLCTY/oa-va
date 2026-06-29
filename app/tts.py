from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import wave
from pathlib import Path
from typing import Any

from app.openai_client import OpenAIClient


KOKORO_REPO_ID = "hexgrad/Kokoro-82M-v1.1-zh"
KOKORO_LOCAL_DIR = "/home/lawrencelcty/huggingface/models/hexgrad/Kokoro-82M-v1.1-zh"
KOKORO_SAMPLE_RATE = 24000
KOKORO_ZH_VOICE = "zf_001"
KOKORO_EN_VOICE = "af_maple"
QWEN_TTS_MODEL_DIR = "/home/lawrencelcty/huggingface/models/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
QWEN_TTS_ZH_SPEAKER = "Vivian"
QWEN_TTS_EN_SPEAKER = "Ryan"
QWEN_TTS_DEVICE = "cuda:0"
QWEN_TTS_DTYPE = "bfloat16"
DEFAULT_TTS_CACHE_DIR = Path(tempfile.gettempdir()) / "oa_voice_assistant_tts"
DEFAULT_NUMBA_CACHE_DIR = Path(tempfile.gettempdir()) / "oa_voice_assistant_numba_cache"


class LocalTTS:
    """OpenAI TTS adapter with local Qwen/Kokoro fallbacks."""

    def __init__(self) -> None:
        self.cache_dir = DEFAULT_TTS_CACHE_DIR
        self._pipelines: dict[str, Any] = {}
        self._qwen_model: Any | None = None
        self.openai = OpenAIClient()
        self.prefer_local = _env_enabled("PREFER_SERVER_TTS")

    def status(self) -> dict[str, object]:
        qwen_path = _qwen_model_dir()
        return {
            "enabled": self.prefer_local or _qwen_enabled(self.openai.enabled),
            "prefer_local": self.prefer_local,
            "engine": "openai+qwen3tts",
            "openai": self.openai.status(),
            "qwen3tts": {
                "enabled": _qwen_enabled(self.openai.enabled),
                "auto_enabled": _qwen_auto_enabled(self.openai.enabled),
                "model_dir": str(qwen_path),
                "model_dir_found": qwen_path.exists(),
                "device": _qwen_device(),
                "dtype": _qwen_dtype_name(),
                "zh_speaker": _qwen_speaker("zh-CN"),
                "en_speaker": _qwen_speaker("en"),
                "loaded": self._qwen_model is not None,
            },
            "kokoro_fallback_enabled": _kokoro_fallback_enabled(),
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
        return self.prefer_local or _qwen_enabled(self.openai.enabled)

    def synthesize(self, text: str, language: str) -> tuple[bytes | None, str, str | None]:
        if not self.enabled:
            return None, "audio/mpeg", "server TTS is disabled"
        cleaned = _clean_text(text)
        if not cleaned:
            return None, "audio/wav", "empty tts text"

        audio, content_type, err = self.openai.synthesize_speech(cleaned, language)
        if audio:
            return audio, content_type, None
        if _qwen_enabled(self.openai.enabled):
            content_type = "audio/wav"
            cache_path = self._cache_path(cleaned, _qwen_language(language), _qwen_speaker(language), "qwen3tts")
            if cache_path.exists():
                return cache_path.read_bytes(), "audio/wav", None
            try:
                audio = self._synthesize_qwen(cleaned, language)
                self._write_cache(cache_path, audio)
                return audio, "audio/wav", None
            except Exception as exc:
                err = f"{type(exc).__name__}: {exc}"
        if not _kokoro_fallback_enabled():
            return None, content_type, err

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

    def _synthesize_qwen(self, text: str, language: str) -> bytes:
        model = self._qwen_pipeline()
        wavs, sample_rate = model.generate_custom_voice(
            text=text,
            language=_qwen_language(language),
            speaker=_qwen_speaker(language),
            instruct=_qwen_instruct(language),
        )
        if not wavs:
            return _silent_wav()
        return _array_to_wav(wavs[0], int(sample_rate))

    def _qwen_pipeline(self) -> Any:
        if self._qwen_model is not None:
            return self._qwen_model
        model_dir = _qwen_model_dir()
        if not model_dir.exists():
            raise FileNotFoundError(f"Qwen3-TTS model path not found: {model_dir}")
        try:
            os.environ.setdefault("NUMBA_CACHE_DIR", str(DEFAULT_NUMBA_CACHE_DIR))
            DEFAULT_NUMBA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            import torch
            from qwen_tts import Qwen3TTSModel
        except ModuleNotFoundError as exc:
            raise RuntimeError("Qwen3-TTS is not installed. Install with: python3 -m pip install -U qwen-tts") from exc

        kwargs: dict[str, Any] = {
            "device_map": _qwen_device(),
            "dtype": _qwen_dtype(torch),
        }
        if _env_enabled("QWEN_TTS_FLASH_ATTENTION"):
            kwargs["attn_implementation"] = "flash_attention_2"
        self._qwen_model = Qwen3TTSModel.from_pretrained(str(model_dir), **kwargs)
        return self._qwen_model

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

    def _cache_path(self, text: str, lang_code: str, voice: str, engine: str = "kokoro") -> Path:
        key = json.dumps(
            {"text": text, "lang_code": lang_code, "voice": voice, "engine": engine},
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


def _kokoro_fallback_enabled() -> bool:
    return _env_enabled("ENABLE_KOKORO_TTS_FALLBACK")


def _qwen_enabled(openai_enabled: bool) -> bool:
    override = os.getenv("ENABLE_QWEN_TTS", "").strip().lower()
    if override in {"0", "false", "no", "off"}:
        return False
    if override in {"1", "true", "yes", "on"}:
        return True
    return _qwen_auto_enabled(openai_enabled)


def _qwen_auto_enabled(openai_enabled: bool) -> bool:
    return _qwen_model_dir().exists()


def _qwen_model_dir() -> Path:
    return Path(os.getenv("QWEN_TTS_MODEL", QWEN_TTS_MODEL_DIR))


def _qwen_device() -> str:
    return os.getenv("QWEN_TTS_DEVICE", QWEN_TTS_DEVICE)


def _qwen_dtype_name() -> str:
    return os.getenv("QWEN_TTS_DTYPE", QWEN_TTS_DTYPE)


def _qwen_dtype(torch: Any) -> Any:
    name = _qwen_dtype_name().strip().lower()
    if name in {"float16", "fp16", "half"}:
        return torch.float16
    if name in {"float32", "fp32"}:
        return torch.float32
    return torch.bfloat16


def _qwen_language(language: str) -> str:
    return "Chinese" if language == "zh-CN" else "English"


def _qwen_speaker(language: str) -> str:
    env_name = "QWEN_TTS_ZH_SPEAKER" if language == "zh-CN" else "QWEN_TTS_EN_SPEAKER"
    default = QWEN_TTS_ZH_SPEAKER if language == "zh-CN" else QWEN_TTS_EN_SPEAKER
    return os.getenv(env_name, default)


def _qwen_instruct(language: str) -> str:
    if language == "zh-CN":
        return os.getenv(
            "QWEN_TTS_ZH_INSTRUCT",
            "用温和、清晰、自然的普通话电话随访语气说，语速稍慢，适合老年人听。",
        )
    return os.getenv(
        "QWEN_TTS_EN_INSTRUCT",
        "Speak in a warm, clear, natural phone check-in voice, slightly slow and suitable for an older adult.",
    )


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _kokoro_lang_code(language: str) -> str:
    return "z" if language == "zh-CN" else "a"


def _kokoro_voice(language: str) -> str:
    return KOKORO_ZH_VOICE if language == "zh-CN" else KOKORO_EN_VOICE


def _chunks_to_wav(chunks: list[Any]) -> bytes:
    import numpy as np

    if not chunks:
        return _silent_wav()

    arrays = [np.asarray(chunk, dtype=np.float32).reshape(-1) for chunk in chunks]
    audio = np.concatenate(arrays)
    return _float_audio_to_wav(audio, KOKORO_SAMPLE_RATE)


def _array_to_wav(audio: Any, sample_rate: int) -> bytes:
    import numpy as np

    return _float_audio_to_wav(np.asarray(audio, dtype=np.float32).reshape(-1), sample_rate)


def _float_audio_to_wav(audio: Any, sample_rate: int) -> bytes:
    import io

    import numpy as np

    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16).tobytes()
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
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
