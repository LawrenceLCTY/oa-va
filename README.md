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
