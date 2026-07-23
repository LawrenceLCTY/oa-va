# OA Medication Questionnaire Voice Assistant

Local prototype for an osteoarthritis medication and treatment questionnaire voice assistant.

v0.9.5 uses the local DOCX questionnaire, sample voice recording, and transcript in `data/` as the active protocol guidance. The DOCX defines the required fields; the sample conversation defines the target phone-interview style. v0.9.5 makes local Qwen the first semantic interpreter for questionnaire turns, while deterministic code validates schema, branching, safety, and reporting.

## Run

```bash
python3 -m app.main
```

Open:

```text
http://127.0.0.1:8000
```

The browser UI is voice-first. The current v0.9.5 flow collects the structured OA questionnaire one question at a time:

```text
browser recorded patient turn
  -> local STT through SenseVoiceSmall when available
  -> local Qwen-compatible semantic turn interpretation when available
  -> deterministic DOCX-guided questionnaire engine
  -> local Qwen3-TTS or browser speech output
```

The deterministic engine controls protocol flow, questionnaire validation, conditional branching, red-flag escalation, and report generation. Model layers are adapters for transcription, structured extraction, wording, and speech. Browser transcript capture remains a development fallback when local STT is unavailable.

v0.2 adds a language selector for:

- Chinese (`zh-CN`)
- English (`en`)

Chinese mode uses an independent Chinese UI, Chinese call script, Chinese speech recognition language setting, Chinese text-to-speech voice preference, and Chinese-aware validation/red-flag rules.

Final reports are generated as formatted JSON with stable English keys. The primary v0.9.5 section is `questionnaire_response`, which stores normalized answers, raw participant wording, skipped conditional fields, completion status, source-material metadata, and per-answer interpretation metadata for accepted fuzzy answers.

## v0.9.5 Semantic Turn Interpreter

v0.9.5 changes the questionnaire architecture so human intent is interpreted by the local Qwen-compatible model before the rulebook sees an answer:

- Qwen receives the current step key, exact question, allowed schema/options, branch context, recent transcript, and raw human response.
- Qwen returns a JSON turn classification: answer, correction, complaint, off-topic, safety, or unclear.
- Deterministic code validates the normalized value against the step schema before advancing state.
- Invalid, low-confidence, wrong-question, complaint, correction, and unclear turns ask for clarification without falling through to keyword parsing.
- If Qwen is unavailable, the existing deterministic parser remains a safe fallback for simple local/dev runs.
- Reports retain raw wording plus model confidence, evidence, turn type, and validator metadata for accepted AI-interpreted answers.

The UI call layout was also restored to the pre-v0.9 visual structure after the v0.9.4 dock experiment reduced transcript visibility. Auto-scroll remains contained to the transcript panel.

## v0.9.4 Sticky Live Voice Dock

v0.9.4 keeps the v0.9.3 questionnaire semantics and changes the live-call surface so conversation history does not push active controls away:

- Transcript history auto-scrolls inside its own panel.
- The live voice dock remains visible with the current prompt, listening/speaking/processing state, mic meter, timer, and start/stop controls.
- Desktop uses independently scrolling assistant and handoff panels.
- Mobile keeps the dock at the bottom of the call surface while the transcript scrolls above it.

## v0.9.3 Fuzzy Interpretation Update

v0.9.3 keeps the v0.9.0 DOCX/audio questionnaire as the active protocol, the v0.9.2 STT reliability baseline, and adds auditable fuzzy Chinese interpretation:

- Accepted answers now include `interpretation` metadata with confidence, strategy, fuzzy, needs-review, and evidence fields.
- Fuzzy-but-logical answers such as doctor-described OA diagnosis, doctor-prescribed medicine channels, and effect descriptions like “吃一两颗就不疼了” can be accepted without repeating the same question.
- Wrong-bucket answers still clarify: benefit-only answers do not answer adverse reactions, and cost-conditional willingness does not become a clean willingness value.
- Report quality metrics count fuzzy, low-confidence, and review-needed interpretations so formal completion does not hide semantic risk.
- Smoke tests include v0.9.3 fuzzy semantic regressions plus the v0.9.2 STT artifact and replay checks.

## v0.9.2 Questionnaire Reliability Update

v0.9.2 keeps the v0.9.0 DOCX/audio questionnaire as the active protocol and adds reliability fixes for local voice runs:

- SenseVoice metadata tags such as `<|zh|><|NEUTRAL|><|Speech|><|withitn|>` are stripped and rejected when no patient content remains.
- Rejected STT turns ask the participant to repeat without advancing the questionnaire state.
- Browser transcript fallback is preferred when local STT output is unusable.
- Report and pipeline metadata are centralized through `app/version.py`.
- The default spoken flow starts from OA diagnosis to match the reference call; set `ASK_SURVEY_ID=1` to restore the survey-ID-first workflow.
- `last_flare_pain_score` accepts narrow qualitative anchors such as mild/no sleep impact and maps them to an auditable 0-10 value.
- Smoke tests include STT artifact rejection and a reference-style transcript replay.

## v0.9.0 DOCX/Audio Questionnaire Flow

v0.9.0 replaced the active short pain-check-in with the questionnaire defined by:

- `data/OA问卷-房山-简化-v2.docx`
- `data/新录音 4.m4a`
- `data/新录音 4.txt`

The active flow collects diagnosis status, affected joints, symptom duration, recent flare details, past-year flare frequency, usual pain response, oral analgesic use, adherence behavior, adverse reactions, improvement after medication, consolidation-medication willingness, non-oral treatments, medicine acquisition channels, hospital/community doctor counseling, and retail-pharmacy guidance fields when applicable.

## v0.8 Visual Refresh

v0.8 made the browser UI stakeholder-demo ready while keeping the existing clinical and privacy architecture intact:

- Voice-call surface with a large assistant presence and clearer listening/speaking/processing states.
- v0.8.1 adds a per-turn recording timer, microphone activity meter, and clearer recording/processing cleanup.
- Protocol progress rail for identity, pain, function, treatment, side effects, red flags, and report completion.
- Formatted doctor-report preview with raw JSON available as an audit/export view.
- v0.8.2 expands the report preview with priority, pain, safety, research-review, quality, audit, and copy controls.
- v0.8.3 adds client-side stakeholder demo states for ready, listening, urgent, and completed-report views.
- Older-adult friendly spacing, contrast, tap targets, and responsive layout.

## v0.7 Private Explainable Pipeline

v0.7 is the production architecture target for private data:

- Browser records one patient answer turn at a time.
- The backend sends audio to local STT (`SenseVoiceSmall`) when configured.
- The browser transcript is accepted as a fallback for development.
- A local Qwen-compatible model can extract structured slots.
- The deterministic OA engine decides the next required clinical step.
- The required next clinical line is spoken using local/server TTS, then browser TTS fallback.

Start the optional local Qwen-compatible extractor:

```bash
python3 -m app.qwen_server
```

Then start the main app in another terminal:

```bash
export ENABLE_LOCAL_UNDERSTANDING=1
export PREFER_LOCAL_STT=1
export PREFER_SERVER_TTS=1
python3 -m app.main
```

Useful local model settings:

```bash
export LOCAL_LLM_URL="http://127.0.0.1:8001/v1/chat/completions"
export LOCAL_LLM_MODEL="/home/lawrencelcty/huggingface/models/Qwen/Qwen3-0.6B-FP8"
export ENABLE_LOCAL_REPLY_REWRITE=0
```

Server CosyVoice3 settings:

```bash
export ENABLE_COSYVOICE_TTS=1
export COSYVOICE_MODEL_DIR="/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512"
export COSYVOICE_REPO_DIR="/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/CosyVoice"
export COSYVOICE_PROMPT_WAV="/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/CosyVoice/asset/zero_shot_prompt.wav"
export COSYVOICE_MODE="instruct2"
```

If the default prompt wav is not present on the server, set `COSYVOICE_PROMPT_WAV` to a short consented bot-voice reference wav.

See `docs/v0.7-private-pipeline.md` for model contracts, streaming roadmap, and Covo/GLM research notes. See `docs/tts-latency-service.md` for the warmed server-TTS sidecar and latency-measurement runbook.

## v0.6 Covo Half-Duplex Experiment

v0.6 is now a research/legacy path. It explored a hybrid voice-to-voice architecture:

- Browser records one patient turn at a time.
- The backend sends audio to an optional Covo half-duplex service.
- The returned transcript is passed into the deterministic OA clinical engine.
- The required next clinical line is spoken using server TTS or browser TTS.
- The Covo model is treated as the voice interface, not the clinical authority.

The public Tencent Covo-Audio release currently supports half-duplex/offline inference, not the unreleased `Covo-Audio-Chat-FD` runtime. The OA app therefore integrates through a lightweight HTTP service contract instead of loading the 7B model in the main app process.

Optional Covo settings:

```bash
export ENABLE_COVO=1
export COVO_ENDPOINT="http://api.datummed.com:PORT"
export COVO_MODEL_DIR="/hdd-storage/lawrencelcty/huggingface/models/Covo-Audio/covoaudio"
export COVO_DEVICE="cuda:2,cuda:3"
export COVO_TIMEOUT_SECONDS=120
```

Expected Covo service contract:

```text
POST {COVO_ENDPOINT}/turn
Content-Type: application/json
```

Request JSON:

```json
{
  "session_id": "uuid",
  "language": "zh-CN",
  "filename": "speech.webm",
  "audio_b64": "...",
  "audio_content_type": "audio/webm",
  "clinical_prompt": "last required OA prompt",
  "state": {}
}
```

Response JSON:

```json
{
  "transcript": "patient answer text",
  "audio_b64": "optional assistant audio",
  "audio_content_type": "audio/wav"
}
```

Until `COVO_ENDPOINT` is available, `/api/covo/turn` can use the browser-captured transcript to exercise the same OA state-machine path without GPU inference.

## v0.5 Realtime Voice Pipeline

v0.5 uses a realtime architecture:

- Browser WebRTC streams microphone audio directly to OpenAI Realtime.
- OpenAI Realtime streams assistant audio back with interruption/barge-in support.
- A browser data channel receives transcripts and tool calls.
- The model calls `submit_patient_answer` after each patient answer.
- The Python app runs the existing clinical state machine and returns the required next clinical line.
- The final doctor report is still generated locally from structured state.

Required:

```bash
export OPENAI_API_KEY="sk-..."
```

Optional realtime overrides:

```bash
export OPENAI_REALTIME_MODEL="gpt-realtime"
export OPENAI_REALTIME_VOICE="marin"
export OPENAI_TRANSCRIBE_MODEL="gpt-4o-mini-transcribe"
```

## v0.4 Legacy Voice Pipeline

v0.4 can use a hybrid architecture:

- Browser voice: default speech recognition and speech synthesis path.
- Local STT: optional SenseVoiceSmall through `/api/stt`.
- Cloud LLM: optional OpenAI structured answer extraction and friendly prompt rewriting.
- Cloud TTS: optional OpenAI speech generation through `/api/tts`.
- Clinical control: the local deterministic state machine still owns step progression, red-flag escalation, and report generation.

Required for legacy OpenAI features:

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

v0.5 uses Qwen3-TTS as the local server speech fallback for `/api/tts` when the model exists locally. The default path is:

```text
/home/lawrencelcty/huggingface/models/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
```

Install the runtime in the Python environment that runs the app:

```bash
python3 -m pip install -U qwen-tts
```

Optional local TTS overrides:

```bash
export QWEN_TTS_MODEL="/path/to/Qwen3-TTS-12Hz-1.7B-CustomVoice"
export QWEN_TTS_DEVICE="cuda:0"
export QWEN_TTS_DTYPE="bfloat16"
export QWEN_TTS_ZH_SPEAKER="Vivian"
export QWEN_TTS_EN_SPEAKER="Ryan"
export QWEN_TTS_FLASH_ATTENTION=1
```

OpenAI TTS is still tried first when `ENABLE_OPENAI_TTS=1` and `OPENAI_API_KEY` is set. Set `ENABLE_QWEN_TTS=0` to disable the Qwen fallback.

Kokoro local TTS is no longer required.

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
  --local-dir /hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/SenseVoiceSmall
```

If `huggingface-cli download` is blocked, use ModelScope:

```bash
python3 - <<'PY'
from modelscope import snapshot_download

snapshot_download(
    "iic/SenseVoiceSmall",
    local_dir="/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/SenseVoiceSmall",
)
PY
```

Override the model path or device:

```bash
export SENSEVOICE_MODEL="/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/SenseVoiceSmall"
export SENSEVOICE_DEVICE="cuda"
# Keep this off for the local FunASR-format model unless you have a model.py remote-code checkout.
export SENSEVOICE_TRUST_REMOTE_CODE=0
```

Quick local check:

```bash
python3 - <<'PY'
from funasr import AutoModel

model = AutoModel(
    model="/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/SenseVoiceSmall",
    trust_remote_code=False,
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
