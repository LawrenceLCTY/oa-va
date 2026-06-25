from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


DEFAULT_MODEL_PATH = "/home/lawrencelcty/huggingface/models/Qwen/Qwen3-0.6B-FP8"
DEFAULT_LLM_URL = "http://127.0.0.1:8001/v1/chat/completions"


class LocalLLM:
    """Small optional wrapper around a local OpenAI-compatible chat endpoint.

    The app defaults to the bundled Qwen server URL. If that server is not
    running, wording polish falls back to the deterministic scripted message.
    """

    def __init__(self) -> None:
        self.url = os.getenv("LOCAL_LLM_URL", DEFAULT_LLM_URL).strip()
        self.model = os.getenv("LOCAL_LLM_MODEL", DEFAULT_MODEL_PATH)
        self.timeout_seconds = float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "8"))
        self.polish_enabled = _env_enabled("ENABLE_LLM_PROMPT_POLISH")

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def polish_assistant_reply(self, message: str) -> str:
        if not self.enabled or not self.polish_enabled:
            return message

        prompt = (
            "Rewrite the following phone-call line for an older adult patient. "
            "Make it warm, natural, and suitable for a real phone call. Preserve the "
            "meaning, safety instruction, question intent, numbers, and language. "
            "Do not add clinical advice, remove urgent-care wording, or ask extra questions. "
            "Return only the rewritten line.\n\n"
            f"Message: {message}"
        )
        return self._chat(prompt, fallback=message)

    def summarize_report(self, structured_report: str) -> str:
        if not self.enabled:
            return structured_report

        prompt = (
            "You are helping draft a concise doctor-readable report from structured "
            "home osteoarthritis monitoring data. Do not diagnose, prescribe, or remove "
            "any red-flag warnings. Keep all safety flags intact.\n\n"
            f"Report:\n{structured_report}"
        )
        return self._chat(prompt, fallback=structured_report)

    def _chat(self, prompt: str, fallback: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a careful assistant that improves wording only. "
                        "Clinical safety rules are determined by the calling app."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 220,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
            return fallback

        try:
            content = body["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            return fallback

        return content or fallback


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
