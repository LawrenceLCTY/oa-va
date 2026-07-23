# Low-Latency TTS Sidecar

The main OA app can now call a warmed server-side TTS process through `TTS_SERVICE_URL`. This keeps the clinical app responsive and avoids loading CosyVoice inside the request path.

## Runtime Shape

```text
app.main /api/tts
  -> TTS_SERVICE_URL /api/tts when configured
  -> in-process LocalTTS fallback if the sidecar is unavailable
  -> browser speech fallback in the UI if server TTS fails
```

The browser reads `X-TTS-Latency-Ms` and `X-TTS-Engine` headers and logs them with total browser fetch time.

## Local Configuration

`.env` should include:

```bash
TTS_SERVICE_URL=http://127.0.0.1:8002
TTS_SERVICE_TIMEOUT_SECONDS=3.0
TTS_WARMUP_ON_START=1

PREFER_SERVER_TTS=1
ENABLE_COSYVOICE_TTS=1
COSYVOICE_MODEL_DIR=/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512
COSYVOICE_REPO_DIR=/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/CosyVoice
COSYVOICE_PROMPT_WAV=/hdd-storage/lawrencelcty/huggingface/models/FunAudioLLM/CosyVoice/asset/zero_shot_prompt.wav
```

## Start Order

Start the TTS service first:

```bash
python3 -m app.tts_server
```

Then start the main app:

```bash
python3 -m app.main
```

Health check:

```bash
python3 - <<"PY"
import urllib.request
print(urllib.request.urlopen("http://127.0.0.1:8002/api/health", timeout=3).read().decode())
PY
```

Manual warmup:

```bash
python3 - <<"PY"
import urllib.request
req = urllib.request.Request("http://127.0.0.1:8002/api/warmup", data=b"{}", method="POST")
print(urllib.request.urlopen(req, timeout=60).read().decode())
PY
```

## Dependency Boundary

CosyVoice should run in a dedicated TTS environment or service. Avoid installing the full CosyVoice requirements directly into `oava` unless you intend to retest the whole app environment, because the upstream requirements pin heavy packages such as Torch, ONNX Runtime, DeepSpeed, and Transformers.

The current local blocker is missing CosyVoice runtime dependencies, including at least:

```text
hyperpyyaml
conformer
diffusers
onnxruntime
wetext
pyworld
deepspeed
openai-whisper
inflect
```

Do not install this list with unconstrained `pip install` inside `oava`: pip may backtrack into older Torch wheels. Use a dedicated TTS env, or install the inference packages with Torch explicitly constrained to the env version and validate imports before running the service.

Once those are installed in the TTS service environment, run `/api/warmup` before a demo to load the model and seed the cache. The service also warms the actual opening prompts on startup when `TTS_WARMUP_ON_START=1`, because the first uncached CosyVoice prompt can exceed a few seconds even after the model is loaded.
