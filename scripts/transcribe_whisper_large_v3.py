#!/usr/bin/env python3
"""Transcribe data/新录音 4.m4a with a local Whisper large-v3 model.

Dependencies:
  pip install torch transformers accelerate safetensors numpy

ffmpeg must also be available on PATH to decode .m4a input files.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


DEFAULT_MODEL_DIR = Path("/hdd-storage/lawrencelcty/huggingface/models/openai/whisper-large-v3")
DEFAULT_AUDIO = Path("data") / "新录音 4.m4a"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO, help="Audio file to transcribe.")
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help="Local Hugging Face Whisper model directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Transcript path. Defaults to the audio path with a .txt suffix.",
    )
    parser.add_argument(
        "--language",
        default="zh",
        help="Spoken language hint for Whisper. Use an empty string for auto-detect.",
    )
    parser.add_argument("--batch-size", type=int, default=8, help="ASR batch size.")
    return parser.parse_args()


def require_inputs(audio: Path, model_dir: Path) -> None:
    if not audio.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio}")
    if not model_dir.is_dir():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to decode .m4a audio, but it was not found on PATH.")


def decode_audio(audio: Path):
    import numpy as np

    command = [
        "ffmpeg",
        "-nostdin",
        "-i",
        str(audio),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "f32le",
        "-hide_banner",
        "-loglevel",
        "error",
        "pipe:1",
    ]
    completed = subprocess.run(command, check=True, stdout=subprocess.PIPE)
    samples = np.frombuffer(completed.stdout, dtype=np.float32)
    if samples.size == 0:
        raise RuntimeError(f"ffmpeg decoded no audio samples from {audio}")
    return {"array": samples, "sampling_rate": 16000}


def main() -> None:
    args = parse_args()
    audio = args.audio
    model_dir = args.model_dir
    output = args.output or audio.with_suffix(".txt")

    require_inputs(audio, model_dir)

    try:
        import numpy  # noqa: F401
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    except ImportError as exc:
        raise SystemExit(
            "Missing Python dependency. Install with:\n"
            "  pip install torch transformers accelerate safetensors numpy"
        ) from exc

    use_cuda = torch.cuda.is_available()
    device = "cuda:0" if use_cuda else "cpu"
    pipeline_device = 0 if use_cuda else -1
    torch_dtype = torch.float16 if use_cuda else torch.float32

    processor = AutoProcessor.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_dir,
        local_files_only=True,
        low_cpu_mem_usage=True,
        dtype=torch_dtype,
        use_safetensors=True,
    )
    model.to(device)

    transcriber = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        dtype=torch_dtype,
        device=pipeline_device,
        chunk_length_s=30,
        batch_size=args.batch_size,
    )

    generate_kwargs = {"task": "transcribe"}
    if args.language:
        generate_kwargs["language"] = args.language

    result = transcriber(decode_audio(audio), generate_kwargs=generate_kwargs)
    text = result["text"].strip()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote transcript to {output}")


if __name__ == "__main__":
    main()
