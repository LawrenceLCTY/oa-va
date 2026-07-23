from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

from app.openai_client import OpenAIClient


KOKORO_REPO_ID = "hexgrad/Kokoro-82M-v1.1-zh"
KOKORO_LOCAL_DIR = "/home/lawrencelcty/huggingface/models/hexgrad/Kokoro-82M-v1.1-zh"
KOKORO_SAMPLE_RATE = 24000
KOKORO_ZH_VOICE = "zf_001"
KOKORO_EN_VOICE = "af_maple"
COSYVOICE_MODEL_DIR = "/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512"
COSYVOICE_REPO_DIR = "/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/CosyVoice"
COSYVOICE_PROMPT_WAV = "/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/CosyVoice/asset/zero_shot_prompt.wav"
COSYVOICE_PROMPT_TEXT = "希望你以后能够做的比我还好呦。"
QWEN_TTS_MODEL_DIR = "/home/lawrencelcty/huggingface/models/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
QWEN_TTS_ZH_SPEAKER = "Vivian"
QWEN_TTS_EN_SPEAKER = "Ryan"
QWEN_TTS_DEVICE = "cuda:0"
QWEN_TTS_DTYPE = "bfloat16"
DEFAULT_TTS_CACHE_DIR = Path(tempfile.gettempdir()) / "oa_voice_assistant_tts"
DEFAULT_NUMBA_CACHE_DIR = Path(tempfile.gettempdir()) / "oa_voice_assistant_numba_cache"


class LocalTTS:
    """OpenAI TTS adapter with local Qwen/Kokoro fallbacks."""

    def __init__(self, *, allow_remote_service: bool = True) -> None:
        self.cache_dir = DEFAULT_TTS_CACHE_DIR
        self._pipelines: dict[str, Any] = {}
        self._qwen_model: Any | None = None
        self._cosyvoice_model: Any | None = None
        self._cosyvoice_sample_rate: int | None = None
        self.last_trace: dict[str, object] | None = None
        self.openai = OpenAIClient()
        self.prefer_local = _env_enabled("PREFER_SERVER_TTS")
        self.allow_remote_service = allow_remote_service
        self.remote_service_url = os.getenv("TTS_SERVICE_URL", "").strip().rstrip("/")
        self.remote_timeout_seconds = float(os.getenv("TTS_SERVICE_TIMEOUT_SECONDS", "3.0"))

    def status(self) -> dict[str, object]:
        qwen_path = _qwen_model_dir()
        cosy_path = _cosyvoice_model_dir()
        cosy_prompt = _cosyvoice_prompt_wav()
        return {
            "enabled": self.enabled,
            "prefer_local": self.prefer_local,
            "engine": "cosyvoice3+openai+qwen3tts",
            "remote_service": {
                "enabled": bool(self.allow_remote_service and self.remote_service_url),
                "url": self.remote_service_url,
                "timeout_seconds": self.remote_timeout_seconds,
            },
            "openai": self.openai.status(),
            "cosyvoice3": {
                "enabled": _cosyvoice_enabled(),
                "model_dir": str(cosy_path),
                "model_dir_found": cosy_path.exists(),
                "repo_dir": str(_cosyvoice_repo_dir()),
                "repo_dir_found": _cosyvoice_repo_dir().exists(),
                "prompt_wav": str(cosy_prompt),
                "prompt_wav_found": cosy_prompt.exists(),
                "mode": _cosyvoice_mode(),
                "fp16": _cosyvoice_fp16_enabled(),
                "load_jit": _cosyvoice_jit_enabled(),
                "load_trt": _cosyvoice_trt_enabled(),
                "loaded": self._cosyvoice_model is not None,
            },
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
            "last_trace": self.last_trace,
        }

    @property
    def enabled(self) -> bool:
        return bool(self.allow_remote_service and self.remote_service_url) or self.prefer_local or _cosyvoice_enabled() or _qwen_enabled(self.openai.enabled)

    def synthesize(self, text: str, language: str) -> tuple[bytes | None, str, str | None]:
        if not self.enabled:
            self.last_trace = {"engine": "none", "success": False, "error": "server TTS is disabled"}
            return None, "audio/mpeg", "server TTS is disabled"
        cleaned = _clean_text(text)
        if not cleaned:
            self.last_trace = {"engine": "none", "success": False, "error": "empty tts text"}
            return None, "audio/wav", "empty tts text"

        remote_err = None
        if self.allow_remote_service and self.remote_service_url:
            audio, content_type, remote_err = self._synthesize_remote_service(cleaned, language)
            if audio:
                return audio, content_type, None

        err = None
        if _cosyvoice_enabled():
            cache_path = self._cache_path(cleaned, _cosyvoice_language(language), _cosyvoice_mode(), "cosyvoice3")
            if cache_path.exists():
                self.last_trace = {"engine": "cosyvoice3", "success": True, "cached": True}
                return cache_path.read_bytes(), "audio/wav", None
            try:
                audio = self._synthesize_cosyvoice(cleaned, language)
                self._write_cache(cache_path, audio)
                self.last_trace = {"engine": "cosyvoice3", "success": True, "cached": False}
                return audio, "audio/wav", None
            except Exception as exc:
                err = f"CosyVoice3 {type(exc).__name__}: {exc}"
                self.last_trace = {"engine": "cosyvoice3", "success": False, "error": err}

        audio, content_type, openai_err = self.openai.synthesize_speech(cleaned, language)
        if audio:
            self.last_trace = {"engine": "openai_tts", "success": True}
            return audio, content_type, None
        err = err or remote_err or openai_err
        if _qwen_enabled(self.openai.enabled):
            content_type = "audio/wav"
            cache_path = self._cache_path(cleaned, _qwen_language(language), _qwen_speaker(language), "qwen3tts")
            if cache_path.exists():
                self.last_trace = {"engine": "qwen3tts", "success": True, "cached": True}
                return cache_path.read_bytes(), "audio/wav", None
            try:
                audio = self._synthesize_qwen(cleaned, language)
                self._write_cache(cache_path, audio)
                self.last_trace = {"engine": "qwen3tts", "success": True, "cached": False}
                return audio, "audio/wav", None
            except Exception as exc:
                err = f"{type(exc).__name__}: {exc}"
                self.last_trace = {"engine": "qwen3tts", "success": False, "error": err}
        if not _kokoro_fallback_enabled():
            if not self.last_trace or self.last_trace.get("success") is not False:
                self.last_trace = {"engine": "none", "success": False, "error": err}
            return None, content_type, err

        lang_code = _kokoro_lang_code(language)
        voice = _kokoro_voice(language)
        cache_path = self._cache_path(cleaned, lang_code, voice)
        if cache_path.exists():
            self.last_trace = {"engine": "kokoro", "success": True, "cached": True}
            return cache_path.read_bytes(), "audio/wav", None

        try:
            audio = self._synthesize_kokoro(cleaned, lang_code, voice)
            self._write_cache(cache_path, audio)
            self.last_trace = {"engine": "kokoro", "success": True, "cached": False}
            return audio, "audio/wav", None
        except Exception as exc:
            self.last_trace = {"engine": "kokoro", "success": False, "error": f"{type(exc).__name__}: {exc}"}
            return None, "audio/wav", f"{type(exc).__name__}: {exc}"

    def _synthesize_remote_service(self, text: str, language: str) -> tuple[bytes | None, str, str | None]:
        payload = json.dumps({"text": text, "language": language}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.remote_service_url}/api/tts",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.remote_timeout_seconds) as response:
                audio = response.read()
                content_type = response.headers.get("Content-Type", "audio/wav")
                self.last_trace = {
                    "engine": "remote_tts_service",
                    "success": True,
                    "service_url": self.remote_service_url,
                    "content_type": content_type,
                    "audio_bytes": len(audio),
                    "service_engine": response.headers.get("X-TTS-Engine", ""),
                    "service_latency_ms": response.headers.get("X-TTS-Latency-Ms", ""),
                }
                return audio, content_type, None
        except (urllib.error.URLError, TimeoutError) as exc:
            err = f"remote TTS service unavailable: {type(exc).__name__}: {exc}"
            self.last_trace = {
                "engine": "remote_tts_service",
                "success": False,
                "service_url": self.remote_service_url,
                "error": err,
            }
            return None, "audio/wav", err

    def _synthesize_cosyvoice(self, text: str, language: str) -> bytes:
        model = self._cosyvoice_pipeline()
        chunks = []
        mode = _cosyvoice_mode()
        prompt_wav = str(_cosyvoice_prompt_wav())
        if mode == "instruct2":
            generator = model.inference_instruct2(
                text,
                _cosyvoice_prompt_with_end_marker(_cosyvoice_instruction(language)),
                prompt_wav,
                stream=_cosyvoice_stream_enabled(),
            )
        else:
            generator = model.inference_zero_shot(
                text,
                _cosyvoice_prompt_with_end_marker(_cosyvoice_prompt_text()),
                prompt_wav,
                stream=_cosyvoice_stream_enabled(),
            )
        for item in generator:
            if isinstance(item, dict) and "tts_speech" in item:
                chunks.append(item["tts_speech"])
        sample_rate = int(self._cosyvoice_sample_rate or getattr(model, "sample_rate", 24000))
        return _chunks_to_wav_at_rate(chunks, sample_rate)

    def _cosyvoice_pipeline(self) -> Any:
        if self._cosyvoice_model is not None:
            return self._cosyvoice_model
        model_dir = _cosyvoice_model_dir()
        if not model_dir.exists():
            raise FileNotFoundError(f"CosyVoice3 model path not found: {model_dir}")
        prompt_wav = _cosyvoice_prompt_wav()
        if not prompt_wav.exists():
            raise FileNotFoundError(f"CosyVoice3 prompt wav not found: {prompt_wav}")
        repo_dir = _cosyvoice_repo_dir()
        if repo_dir.exists():
            sys.path.insert(0, str(repo_dir))
            matcha_dir = repo_dir / "third_party" / "Matcha-TTS"
            if matcha_dir.exists():
                sys.path.insert(0, str(matcha_dir))
        try:
            from cosyvoice.cli.cosyvoice import AutoModel
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "CosyVoice is not importable. Install the FunAudioLLM/CosyVoice runtime in this environment "
                "or set COSYVOICE_REPO_DIR to the cloned CosyVoice repo."
            ) from exc
        kwargs = {
            "model_dir": str(model_dir),
            "load_trt": _cosyvoice_trt_enabled(),
            "fp16": _cosyvoice_fp16_enabled(),
        }
        if (model_dir / "cosyvoice.yaml").exists() or (model_dir / "cosyvoice2.yaml").exists():
            kwargs["load_jit"] = _cosyvoice_jit_enabled()
        kwargs = _accepted_kwargs(AutoModel, kwargs)
        if "model_dir" in kwargs:
            self._cosyvoice_model = AutoModel(**kwargs)
        else:
            self._cosyvoice_model = AutoModel(str(model_dir))
        self._cosyvoice_sample_rate = int(getattr(self._cosyvoice_model, "sample_rate", 24000))
        return self._cosyvoice_model

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
            {
                "text": text,
                "lang_code": lang_code,
                "voice": voice,
                "engine": engine,
                "cache_version": _tts_cache_version(),
                "cosyvoice_mode": _cosyvoice_mode() if engine == "cosyvoice3" else None,
                "cosyvoice_prompt_text": _cosyvoice_prompt_text() if engine == "cosyvoice3" else None,
                "cosyvoice_instruction": _cosyvoice_cache_instruction(lang_code) if engine == "cosyvoice3" else None,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{digest}.wav"

    def _write_cache(self, path: Path, data: bytes) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _clean_text(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    cleaned = cleaned.replace("<|endofprompt|>", " ").strip()
    cleaned = _strip_internal_tts_instruction(cleaned)
    return " ".join(cleaned.split())[:500]


def _strip_internal_tts_instruction(text: str) -> str:
    patterns = (
        r"(?is)^say this closing message naturally, then stop:\s*(.+)$",
        r"(?is)^say this next required clinical line naturally.*?required line:\s*(.+)$",
        r"(?is)^continue the clinical check-in using this required next content:\s*(.+)$",
        r"(?is)^the patient typed a backup answer\.\s*continue with this required next content:\s*(.+)$",
        r"(?is)^.*?required line:\s*(.+)$",
        r"(?is)^.*?required next content:\s*(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            return match.group(1).strip()
    return text


def _tts_cache_version() -> str:
    return os.getenv("TTS_CACHE_VERSION", "v3-clean-prompt-marker")


def _cosyvoice_cache_instruction(lang_code: str) -> str | None:
    if _cosyvoice_mode() != "instruct2":
        return None
    language = "zh-CN" if lang_code == "zh" else "en"
    return _cosyvoice_instruction(language)


def _kokoro_fallback_enabled() -> bool:
    return _env_enabled("ENABLE_KOKORO_TTS_FALLBACK")


def _cosyvoice_enabled() -> bool:
    override = os.getenv("ENABLE_COSYVOICE_TTS", "").strip().lower()
    if override in {"0", "false", "no", "off"}:
        return False
    if override in {"1", "true", "yes", "on"}:
        return True
    return _cosyvoice_model_dir().exists()


def _cosyvoice_model_dir() -> Path:
    return Path(os.getenv("COSYVOICE_MODEL_DIR", COSYVOICE_MODEL_DIR))


def _cosyvoice_repo_dir() -> Path:
    return Path(os.getenv("COSYVOICE_REPO_DIR", COSYVOICE_REPO_DIR))


def _cosyvoice_prompt_wav() -> Path:
    return Path(os.getenv("COSYVOICE_PROMPT_WAV", COSYVOICE_PROMPT_WAV))



def _cosyvoice_prompt_with_end_marker(text: str) -> str:
    text = text.strip()
    return text if "<|endofprompt|>" in text else f"{text}<|endofprompt|>"

def _cosyvoice_prompt_text() -> str:
    return os.getenv("COSYVOICE_PROMPT_TEXT", COSYVOICE_PROMPT_TEXT)


def _cosyvoice_mode() -> str:
    mode = os.getenv("COSYVOICE_MODE", "zero_shot").strip().lower()
    return mode if mode in {"instruct2", "zero_shot"} else "zero_shot"


def _cosyvoice_stream_enabled() -> bool:
    return _env_enabled("COSYVOICE_STREAM")


def _cosyvoice_fp16_enabled() -> bool:
    return _env_enabled("COSYVOICE_FP16", default=True)


def _cosyvoice_jit_enabled() -> bool:
    return _env_enabled("COSYVOICE_LOAD_JIT")


def _cosyvoice_trt_enabled() -> bool:
    return _env_enabled("COSYVOICE_LOAD_TRT")


def _cosyvoice_language(language: str) -> str:
    return "zh" if language == "zh-CN" else "en"


def _cosyvoice_instruction(language: str) -> str:
    if language == "zh-CN":
        return os.getenv(
            "COSYVOICE_ZH_INSTRUCTION",
            "用温和、清晰、自然的普通话电话随访语气说话，语速稍慢，像研究助理，不要夸张表演。",
        )
    return os.getenv(
        "COSYVOICE_EN_INSTRUCTION",
        "Speak in a warm, clear, natural phone check-in voice, slightly slow and professional.",
    )


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


def _env_enabled(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _accepted_kwargs(callable_obj: Any, values: dict[str, object]) -> dict[str, object]:
    try:
        parameters = inspect.signature(callable_obj).parameters
    except (TypeError, ValueError):
        return values
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()):
        return values
    return {key: value for key, value in values.items() if key in parameters}


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


def _chunks_to_wav_at_rate(chunks: list[Any], sample_rate: int) -> bytes:
    import numpy as np

    if not chunks:
        return _silent_wav(sample_rate)

    arrays = []
    for chunk in chunks:
        if hasattr(chunk, "detach"):
            chunk = chunk.detach().cpu().numpy()
        arrays.append(np.asarray(chunk, dtype=np.float32).reshape(-1))
    audio = np.concatenate(arrays)
    return _float_audio_to_wav(audio, sample_rate)


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
