from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.i18n import DEFAULT_LANGUAGE


QUESTION_STEPS = (
    "intro",
    "readiness_hearing",
    "readiness_time",
    "permission",
    "survey_id",
    "oa_diagnosis",
    "affected_joints",
    "symptom_duration",
    "last_flare_onset",
    "last_flare_duration",
    "last_flare_pain_score",
    "annual_flare_frequency",
    "usual_pain_response",
    "oral_painkiller_used",
    "oral_painkiller_name",
    "oral_painkiller_no_reason",
    "adherence_to_doctor_order",
    "missed_doses",
    "stopped_after_improvement",
    "difficulty_taking_as_directed",
    "missed_dose_reasons",
    "adverse_reactions",
    "adverse_reaction_symptoms",
    "pain_improvement_after_meds",
    "function_improvement_after_meds",
    "consolidation_medication_willingness",
    "non_oral_treatments",
    "painkiller_channels",
    "doctor_counseling",
    "retail_pharmacy_reasons",
    "retail_pharmacy_purchase_method",
    "pharmacy_guidance_contraindications",
    "pharmacy_guidance_dosage",
    "pharmacy_guidance_avoid_multiple_painkillers",
    "pharmacy_guidance_long_term_risks",
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
    average_24h_score: int | None = None
    average_24h_severity: str = "unknown"
    current_score_confirmed: bool = False
    average_24h_score_confirmed: bool = False
    location: str | None = None
    functional_impact: str | None = None
    usual_comparison: str = "unknown"
    patient_words: list[str] = field(default_factory=list)
    active_vas_period: str | None = None
    active_vas_low: int | None = None
    active_vas_high: int | None = None
    average_24h_vas_trace: list[dict[str, object]] = field(default_factory=list)
    current_vas_trace: list[dict[str, object]] = field(default_factory=list)


@dataclass
class SafetyAssessment:
    reported_symptoms: list[str] = field(default_factory=list)
    medication_context: str | None = None
    side_effect_screening_result: str = "unknown"
    symptom_start_time: str | None = None
    symptom_status: str = "unknown"
    symptom_severity: str = "unknown"
    medication_changed: str = "unknown"
    doctor_contacted: str = "unknown"
    emergency_visit_or_hospitalization: str = "unknown"
    researcher_alert_required: bool = False
    non_urgent_concerns: list[str] = field(default_factory=list)
    red_flag_present: bool = False
    red_flag_uncertain: bool = False
    red_flag_symptoms: list[str] = field(default_factory=list)
    action_advised: str = "no urgent escalation"


@dataclass
class QuestionnaireAssessment:
    source_materials: dict[str, str] = field(default_factory=dict)
    answers: dict[str, Any] = field(default_factory=dict)
    raw_answers: dict[str, str] = field(default_factory=dict)
    skipped: dict[str, str] = field(default_factory=dict)
    completion: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    language: str = DEFAULT_LANGUAGE
    step: str = "intro"
    identity: PatientIdentity = field(default_factory=PatientIdentity)
    readiness: dict[str, str] = field(
        default_factory=lambda: {
            "hearing_clear": "unknown",
            "suitable_time": "unknown",
            "permission_to_continue": "unknown",
        }
    )
    respondent_source: str = "unknown"
    questionnaire: QuestionnaireAssessment = field(default_factory=QuestionnaireAssessment)
    pain: PainAssessment = field(default_factory=PainAssessment)
    safety: SafetyAssessment = field(default_factory=SafetyAssessment)
    transcript: list[dict[str, str]] = field(default_factory=list)
    model_events: list[dict[str, object]] = field(default_factory=list)
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
            "language": self.language,
            "step": self.step,
            "complete": self.complete,
            "identity": {
                "name": self.identity.name,
                "mobile_number": self.identity.mobile_number,
                "age": self.identity.age,
                "status": self.identity.status,
            },
            "readiness": self.readiness,
            "respondent_source": self.respondent_source,
            "questionnaire": {
                "source_materials": self.questionnaire.source_materials,
                "answers": self.questionnaire.answers,
                "raw_answers": self.questionnaire.raw_answers,
                "skipped": self.questionnaire.skipped,
                "completion": self.questionnaire.completion,
            },
            "pain": {
                "score": self.pain.score,
                "severity": self.pain.severity,
                "average_24h_score": self.pain.average_24h_score,
                "average_24h_severity": self.pain.average_24h_severity,
                "current_score_confirmed": self.pain.current_score_confirmed,
                "average_24h_score_confirmed": self.pain.average_24h_score_confirmed,
                "location": self.pain.location,
                "functional_impact": self.pain.functional_impact,
                "usual_comparison": self.pain.usual_comparison,
                "patient_words": self.pain.patient_words,
                "active_vas_period": self.pain.active_vas_period,
                "active_vas_low": self.pain.active_vas_low,
                "active_vas_high": self.pain.active_vas_high,
                "average_24h_vas_trace": self.pain.average_24h_vas_trace,
                "current_vas_trace": self.pain.current_vas_trace,
            },
            "safety": {
                "reported_symptoms": self.safety.reported_symptoms,
                "medication_context": self.safety.medication_context,
                "side_effect_screening_result": self.safety.side_effect_screening_result,
                "symptom_start_time": self.safety.symptom_start_time,
                "symptom_status": self.safety.symptom_status,
                "symptom_severity": self.safety.symptom_severity,
                "medication_changed": self.safety.medication_changed,
                "doctor_contacted": self.safety.doctor_contacted,
                "emergency_visit_or_hospitalization": self.safety.emergency_visit_or_hospitalization,
                "researcher_alert_required": self.safety.researcher_alert_required,
                "non_urgent_concerns": self.safety.non_urgent_concerns,
                "red_flag_present": self.safety.red_flag_present,
                "red_flag_uncertain": self.safety.red_flag_uncertain,
                "red_flag_symptoms": self.safety.red_flag_symptoms,
                "action_advised": self.safety.action_advised,
            },
            "transcript": self.transcript,
            "model_events": self.model_events,
            "report": self.report,
            "pending_clarification": self.pending_clarification,
        }
