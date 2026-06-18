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

## Optional Local LLM

The app works without a local model. To enable response/report polishing through a local OpenAI-compatible endpoint, set:

```bash
export LOCAL_LLM_URL="http://127.0.0.1:8001/v1/chat/completions"
export LOCAL_LLM_MODEL="/home/lawrencelcty/huggingface/models/Qwen/Qwen3-4B-Instruct-2507-FP8"
```

Clinical red-flag detection and escalation remain deterministic and rule-based even when the LLM is enabled.

## Test

```bash
python3 tests/smoke_test.py
```
