# OA Home Pain Check-in Assistant

Local prototype for an osteoarthritis home pain monitoring voice assistant.

## Run

```bash
export OPENAI_API_KEY="sk-..."
python3 -m app.main
```

Open:

```text
http://127.0.0.1:8000
```

The browser UI supports typed input and browser speech input/output. The low-latency browser path is the default; local SenseVoiceSmall STT, OpenAI language understanding, prompt rewriting, and server-side TTS are opt-in.

v0.2 adds a language selector for:

- Chinese (`zh-CN`)
- English (`en`)

Chinese mode uses an independent Chinese UI, Chinese call script, Chinese speech recognition language setting, Chinese text-to-speech voice preference, and Chinese-aware validation/red-flag rules.

Final doctor reports are generated as formatted JSON with stable English keys for easier downstream machine processing.

## v0.4 Voice Pipeline

v0.4 can use a hybrid architecture:

- Browser voice: default speech recognition and speech synthesis path.
- Local STT: optional SenseVoiceSmall through `/api/stt`.
- Cloud LLM: optional OpenAI structured answer extraction and friendly prompt rewriting.
- Cloud TTS: optional OpenAI speech generation through `/api/tts`.
- Clinical control: the local deterministic state machine still owns step progression, red-flag escalation, and report generation.

Required for OpenAI:

```bash
export OPENAI_API_KEY="sk-..."
```

Optional overrides:

```bash
export OPENAI_LLM_MODEL="gpt-4o-mini"
export OPENAI_TTS_MODEL="gpt-4o-mini-tts"
export OPENAI_TTS_VOICE="alloy"
```

Latency-sensitive defaults:

```bash
# Leave these unset for the fastest browser-first UX.
export PREFER_LOCAL_STT=1
export PREFER_SERVER_TTS=1
export ENABLE_OPENAI_UNDERSTANDING=1
export ENABLE_OPENAI_REPLY_REWRITE=1
export ENABLE_OPENAI_TTS=1
```

The app still accepts typed input if STT is not installed, and browser speech recognition/synthesis remains the default fallback when optional local or server voice is unavailable.

## Local LLM

Start the included lightweight Qwen OpenAI-compatible server:

```bash
python3 -m app.qwen_server
```

Then start the main app in another terminal:

```bash
python3 -m app.main
```

Clinical red-flag detection and escalation remain deterministic and rule-based even when the LLM is enabled.

The default model path is:

```text
/home/lawrencelcty/huggingface/models/Qwen/Qwen3-0.6B-FP8
```

## Local TTS

v0.4 uses OpenAI TTS by default for `/api/tts`. Kokoro local TTS is no longer required.

Only enable the old Kokoro fallback if you intentionally reinstall the model:

```bash
export ENABLE_KOKORO_TTS_FALLBACK=1
```

## Local STT: SenseVoiceSmall

`hf download` only downloads model files. SenseVoiceSmall also needs the FunASR runtime and audio dependencies.

Install:

```bash
python3 -m pip install -U funasr modelscope torchaudio soundfile librosa
```

Download the model into the path expected by the app:

```bash
export HTTP_PROXY=http://crs.datummed.com:8080
export HTTPS_PROXY=http://crs.datummed.com:8080

huggingface-cli download FunAudioLLM/SenseVoiceSmall \
  --local-dir /home/lawrencelcty/huggingface/models/FunAudioLLM/SenseVoiceSmall
```

If `huggingface-cli download` is blocked, use ModelScope:

```bash
python3 - <<'PY'
from modelscope import snapshot_download

snapshot_download(
    "iic/SenseVoiceSmall",
    local_dir="/home/lawrencelcty/huggingface/models/FunAudioLLM/SenseVoiceSmall",
)
PY
```

Override the model path or device:

```bash
export SENSEVOICE_MODEL="/path/to/SenseVoiceSmall"
export SENSEVOICE_DEVICE="cuda"
```

Quick local check:

```bash
python3 - <<'PY'
from funasr import AutoModel

model = AutoModel(
    model="/home/lawrencelcty/huggingface/models/FunAudioLLM/SenseVoiceSmall",
    trust_remote_code=True,
    device="cuda",
    disable_update=True,
)
print("SenseVoiceSmall ready")
PY
```

## Test

```bash
python3 tests/smoke_test.py
```
