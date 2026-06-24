# OA Home Pain Check-in Assistant

Local prototype for an osteoarthritis home pain monitoring voice assistant.

## Run

```bash
python3 -m app.main
```

Open:

```text
http://127.0.0.1:8000
```

The browser UI supports typed input and browser speech input/output when the browser supports the Web Speech APIs.

v0.2 adds a language selector for:

- Chinese (`zh-CN`)
- English (`en`)

Chinese mode uses an independent Chinese UI, Chinese call script, Chinese speech recognition language setting, Chinese text-to-speech voice preference, and Chinese-aware validation/red-flag rules.

Final doctor reports are generated as formatted JSON with stable English keys for easier downstream machine processing.

## Voice Quality

The current prototype uses browser text-to-speech, so voice quality depends on the browser and operating system voices available on the test machine. For a friendlier, less robotic voice, the next implementation step is to replace browser speech synthesis with a dedicated TTS engine:

- Local/offline: Piper or Coqui-style local TTS for data control, with more setup and voice tuning.
- Cloud/API: OpenAI TTS, Azure Neural TTS, or ElevenLabs for more natural voices, with external-service/privacy review needed.

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

v0.3 uses Kokoro local TTS for `/api/tts`.

Install:

```bash
python3 -m pip install "kokoro>=0.9.4" "misaki[zh]>=0.8.2" soundfile
```

Download/cache the model:

```bash
python3 - <<'PY'
from kokoro import KPipeline
pipeline = KPipeline(lang_code="z", repo_id="hexgrad/Kokoro-82M-v1.1-zh")
print("Kokoro zh model ready")
PY
```

Default model:

```text
hexgrad/Kokoro-82M-v1.1-zh
```

Default voices:

- Chinese: `zf_001`
- English: `af_maple`

## Test

```bash
python3 tests/smoke_test.py
```
