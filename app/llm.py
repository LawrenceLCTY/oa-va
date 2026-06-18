from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


DEFAULT_MODEL_PATH = "/home/lawrencelcty/huggingface/models/Qwen/Qwen3-4B-Instruct-2507-FP8"


class LocalLLM:
    """Small optional wrapper around a local OpenAI-compatible chat endpoint.

    The app remains fully functional when no local model server is running. Set
    LOCAL_LLM_URL to an endpoint such as http://localhost:8001/v1/chat/completions
    and LOCAL_LLM_MODEL to the served model name to enable polishing.
    """

    def __init__(self) -> None:
        self.url = os.getenv("LOCAL_LLM_URL", "").strip()
        self.model = os.getenv("LOCAL_LLM_MODEL", DEFAULT_MODEL_PATH)
        self.timeout_seconds = float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "8"))

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def polish_assistant_reply(self, message: str) -> str:
        if not self.enabled:
            return message

        prompt = (
            "Rewrite the following phone-call line for an older adult patient. "
            "Make it sound like a real human call, not an AI assistant. Keep it under "
            "20 words when possible. Do not add clinical advice.\n\n"
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
            "temperature": 0.2,
            "max_tokens": 500,
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
