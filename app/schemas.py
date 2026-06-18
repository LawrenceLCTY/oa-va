from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


QUESTION_STEPS = (
    "intro",
    "identity",
    "pain_score",
    "pain_location",
    "functional_impact",
    "usual_comparison",
    "treatment_context",
    "side_effects",
    "red_flags",
    "closing",
    "complete",
)


@dataclass
class PatientIdentity:
    name: str | None = None
    mobile_number: str | None = None
    age: int | None = None

    @property
    def is_complete(self) -> bool:
        return bool(self.name and self.mobile_number and self.age is not None)

    @property
    def status(self) -> str:
        return "complete" if self.is_complete else "incomplete"


@dataclass
class PainAssessment:
    score: int | None = None
    severity: str = "unknown"
    location: str | None = None
    functional_impact: str | None = None
    usual_comparison: str = "unknown"
    patient_words: list[str] = field(default_factory=list)


@dataclass
class SafetyAssessment:
    reported_symptoms: list[str] = field(default_factory=list)
    medication_context: str | None = None
    non_urgent_concerns: list[str] = field(default_factory=list)
    red_flag_present: bool = False
    red_flag_uncertain: bool = False
    red_flag_symptoms: list[str] = field(default_factory=list)
    action_advised: str = "no urgent escalation"


@dataclass
class ConversationState:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    step: str = "intro"
    identity: PatientIdentity = field(default_factory=PatientIdentity)
    pain: PainAssessment = field(default_factory=PainAssessment)
    safety: SafetyAssessment = field(default_factory=SafetyAssessment)
    transcript: list[dict[str, str]] = field(default_factory=list)
    report: str | None = None
    complete: bool = False
    escalation_message_spoken: bool = False
    pending_clarification: str | None = None

    def assistant(self, message: str) -> None:
        self.transcript.append({"role": "assistant", "text": message})

    def user(self, message: str) -> None:
        self.transcript.append({"role": "user", "text": message})

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "step": self.step,
            "complete": self.complete,
            "identity": {
                "name": self.identity.name,
                "mobile_number": self.identity.mobile_number,
                "age": self.identity.age,
                "status": self.identity.status,
            },
            "pain": {
                "score": self.pain.score,
                "severity": self.pain.severity,
                "location": self.pain.location,
                "functional_impact": self.pain.functional_impact,
                "usual_comparison": self.pain.usual_comparison,
                "patient_words": self.pain.patient_words,
            },
            "safety": {
                "reported_symptoms": self.safety.reported_symptoms,
                "medication_context": self.safety.medication_context,
                "non_urgent_concerns": self.safety.non_urgent_concerns,
                "red_flag_present": self.safety.red_flag_present,
                "red_flag_uncertain": self.safety.red_flag_uncertain,
                "red_flag_symptoms": self.safety.red_flag_symptoms,
                "action_advised": self.safety.action_advised,
            },
            "transcript": self.transcript,
            "report": self.report,
            "pending_clarification": self.pending_clarification,
        }
