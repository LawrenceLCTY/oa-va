from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_MODEL_PATH = "/home/lawrencelcty/huggingface/models/Qwen/Qwen3-0.6B-FP8"
ROOT_DIR = Path(__file__).resolve().parent.parent

load_dotenv(ROOT_DIR / ".env")


class QwenModel:
    def __init__(self) -> None:
        self.model_path = os.getenv("LOCAL_LLM_MODEL", DEFAULT_MODEL_PATH)
        self.max_new_tokens = int(os.getenv("LOCAL_LLM_MAX_NEW_TOKENS", "220"))
        self.temperature = float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.3"))
        self._tokenizer: Any | None = None
        self._model: Any | None = None

    def load(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"model path not found: {self.model_path}")

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        cuda_available = torch.cuda.is_available()
        print(f"Loading Qwen model from {self.model_path}")
        print(f"CUDA available: {cuda_available}")
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
        model_kwargs: dict[str, object] = {
            "torch_dtype": "auto",
            "trust_remote_code": True,
        }
        if cuda_available:
            model_kwargs["device_map"] = "auto"
        self._model = AutoModelForCausalLM.from_pretrained(self.model_path, **model_kwargs)
        if not cuda_available:
            self._model.to("cpu")
        self._model.eval()

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        self.load()
        assert self._tokenizer is not None
        assert self._model is not None

        import torch

        try:
            prompt = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            prompt = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        inputs = self._tokenizer([prompt], return_tensors="pt").to(self._model.device)
        request_max_tokens = max_new_tokens if max_new_tokens is not None else self.max_new_tokens
        request_temperature = temperature if temperature is not None else self.temperature
        generation_kwargs: dict[str, object] = {
            "max_new_tokens": max(1, request_max_tokens),
            "do_sample": request_temperature > 0,
        }
        if request_temperature > 0:
            generation_kwargs["temperature"] = request_temperature
        with torch.inference_mode():
            generated = self._model.generate(
                **inputs,
                **generation_kwargs,
            )
        new_tokens = generated[:, inputs.input_ids.shape[-1] :]
        return self._tokenizer.batch_decode(new_tokens, skip_special_tokens=True)[0].strip()


MODEL = QwenModel()


class QwenHandler(BaseHTTPRequestHandler):
    server_version = "QwenLocalOpenAICompat/0.3"

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"ok": True, "model": MODEL.model_path})
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        data = self._read_json()
        raw_messages = data.get("messages", [])
        if not isinstance(raw_messages, list):
            self._send_json({"error": "messages must be a list"}, HTTPStatus.BAD_REQUEST)
            return

        messages = [
            {"role": str(item.get("role", "user")), "content": str(item.get("content", ""))}
            for item in raw_messages
            if isinstance(item, dict)
        ]
        max_new_tokens = _request_int(data, "max_tokens", MODEL.max_new_tokens)
        temperature = _request_float(data, "temperature", MODEL.temperature)
        try:
            content = MODEL.chat(messages, max_new_tokens=max_new_tokens, temperature=temperature)
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json(
            {
                "id": "local-qwen",
                "object": "chat.completion",
                "model": MODEL.model_path,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
            }
        )

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return


def _request_int(data: dict[str, object], key: str, fallback: int) -> int:
    try:
        return max(1, int(data.get(key, fallback)))
    except (TypeError, ValueError):
        return fallback


def _request_float(data: dict[str, object], key: str, fallback: float) -> float:
    try:
        return max(0.0, float(data.get(key, fallback)))
    except (TypeError, ValueError):
        return fallback


def run(host: str = "127.0.0.1", port: int = 8001) -> None:
    MODEL.load()
    server = ThreadingHTTPServer((host, port), QwenHandler)
    print(f"Qwen model ready.")
    print(f"Qwen OpenAI-compatible server running at http://{host}:{port}/v1/chat/completions")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run(os.getenv("LOCAL_LLM_HOST", "127.0.0.1"), int(os.getenv("LOCAL_LLM_PORT", "8001")))
