from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.conversation import ConversationEngine
from app.schemas import ConversationState
from app.stt import LocalSTT
from app.tts import LocalTTS


@dataclass
class PipelineTiming:
    started_at: float = field(default_factory=time.perf_counter)
    marks: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        self.marks[name] = time.perf_counter()

    def to_dict(self) -> dict[str, int]:
        previous = self.started_at
        durations: dict[str, int] = {}
        for name, value in self.marks.items():
            durations[f"{name}_ms"] = int((value - previous) * 1000)
            previous = value
        durations["total_ms"] = int((time.perf_counter() - self.started_at) * 1000)
        return durations


@dataclass
class PipelineTurnResult:
    transcript: str
    transcript_source: str
    assistant_messages: list[str]
    spoken_instruction: str
    state: ConversationState
    timings: dict[str, int]
    errors: list[str] = field(default_factory=list)


class PrivateVoicePipeline:
    """Explainable private voice-agent pipeline.

    The pipeline keeps model responsibilities narrow:
    STT turns patient audio into text, ConversationEngine owns clinical state
    and safety, and TTS is handled by the existing /api/tts endpoint.
    """

    def __init__(self, engine: ConversationEngine, stt: LocalSTT, tts: LocalTTS) -> None:
        self.engine = engine
        self.stt = stt
        self.tts = tts

    def status(self) -> dict[str, Any]:
        return {
            "version": "v0.7",
            "mode": "private_explainable_pipeline",
            "production_target": True,
            "stages": {
                "audio_input": {
                    "engine": "browser MediaRecorder/WebRTC constraints",
                    "streaming_target": "WebRTC audio frames in a later runtime",
                },
                "vad_endpointing": {
                    "engine": "browser/manual turn endpointing for v0.7",
                    "planned": "WebRTC VAD or Silero VAD",
                },
                "stt": self.stt.status(),
                "structured_extraction": {
                    "engine": "local Qwen-compatible extractor when ConversationEngine AI is configured",
                    "clinical_authority": False,
                },
                "clinical_controller": {
                    "engine": "ConversationEngine deterministic OA rulebook",
                    "clinical_authority": True,
                },
                "verbalizer": {
                    "engine": "deterministic required line with optional constrained local rewrite",
                    "clinical_authority": False,
                },
                "tts": self.tts.status(),
            },
            "research_side_notes": {
                "covo": "archived half-duplex V2V experiment, not v0.7 production path",
                "glm4voice": "future research candidate for native V2V interface, not v0.7 production path",
            },
        }

    def process_turn(
        self,
        state: ConversationState,
        audio: bytes,
        *,
        filename: str,
        language: str,
        fallback_text: str,
    ) -> PipelineTurnResult:
        timing = PipelineTiming()
        errors: list[str] = []
        transcript = ""
        transcript_source = "none"

        if audio:
            transcript, err = self.stt.transcribe(audio, filename, language)
            timing.mark("stt")
            if transcript:
                transcript_source = "local_stt"
            elif err:
                errors.append(f"stt: {err}")
        else:
            timing.mark("stt")

        if not transcript and fallback_text.strip():
            transcript = fallback_text.strip()
            transcript_source = "browser_transcript"

        if not transcript:
            return PipelineTurnResult(
                transcript="",
                transcript_source=transcript_source,
                assistant_messages=[],
                spoken_instruction="",
                state=state,
                timings=timing.to_dict(),
                errors=errors or ["no transcript produced"],
            )

        before = len(state.transcript)
        self.engine.handle_user_message(state, transcript)
        timing.mark("clinical_engine")
        assistant_messages = [
            item["text"]
            for item in state.transcript[before:]
            if item.get("role") == "assistant"
        ]
        return PipelineTurnResult(
            transcript=transcript,
            transcript_source=transcript_source,
            assistant_messages=assistant_messages,
            spoken_instruction="",
            state=state,
            timings=timing.to_dict(),
            errors=errors,
        )
