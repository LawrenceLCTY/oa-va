# Version Logs

This folder records implementation-level changes for each prototype version.

Use this folder to backtrack:

- what changed in each version
- why the change was made
- which files were touched
- known limitations
- tests or checks run
- follow-up work planned

## Index

| Version | Date | Summary |
| --- | --- | --- |
| [v0.9.5](./v0.9.5.md) | 2026-07-23 | Implements Qwen-first questionnaire turn interpretation with deterministic schema validation and restores the pre-v0.9 call layout. |
| [v0.9.4](./v0.9.4.md) | 2026-07-22 | Pins the live voice dock while keeping transcript auto-scroll inside a contained conversation history panel. |
| [v0.9.3](./v0.9.3.md) | 2026-07-22 | Adds fuzzy Chinese interpretation metadata, confidence/review flags, and semantic parser regressions while preserving deterministic step control. |
| [v0.9.2](./v0.9.2.md) | 2026-07-22 | Hardens STT sanitation/fallback, centralizes version metadata, aligns default questionnaire start, and adds replay/regression tests. |
| [v0.9.1](./v0.9.1.md) | 2026-07-22 | Improves server TTS latency handling, adds warmed TTS sidecar behavior, and reduces private voice turn-taking friction. |
| [v0.9.0](./v0.9.0.md) | 2026-07-22 | Replaces the active flow with the DOCX/audio-guided OA medication and treatment questionnaire. |
| [v0.8.4](./v0.8.4.md) | 2026-07-09 | Adapts the v0.8 visual theme around PKU red with restrained clinical-support colors. |
| [v0.8.3](./v0.8.3.md) | 2026-07-09 | Removes confusing demo/trust phrases and keeps the interface focused on the actual check-in workflow. |
| [v0.8.2](./v0.8.2.md) | 2026-07-09 | Improves the doctor-report preview with summary metrics, clinical sections, review signals, and copy/export affordances. |
| [v0.8.1](./v0.8.1.md) | 2026-07-09 | Adds voice interaction polish with recording timer, microphone activity meter, and clearer turn-state cleanup. |
| [v0.8.0](./v0.8.0.md) | 2026-07-09 | Redesigns the frontend as a polished clinical voice-assistant interface with protocol progress and formatted report preview. |
| [v0.5](./v0.5.md) | 2026-06-29 | Adds OpenAI Realtime plus Qwen3-TTS fallback, and records the pivot toward true full-duplex V2V after stakeholder UX review. |
| [v0.4.2](./v0.4.2.md) | 2026-06-25 | Adds guided VAS/NRS pain-score calibration using binary comparisons against concrete OA pain scenarios. |
| [v0.4.1](./v0.4.1.md) | 2026-06-25 | Refines bilingual spoken prompts with explicit clinical intent metadata while preserving deterministic validation and safety flow. |
| [v0.4](./v0.4.md) | 2026-06-24 | Adds hybrid local STT plus OpenAI structured understanding and TTS for more natural voice calls. |
| [v0.3](./v0.3.md) | 2026-06-18 | Adds optional local/private LLM wording polish and backend TTS audio pipeline with browser fallback. |
| [v0.2.1](./v0.2.1.md) | 2026-06-18 | Adds autonomous call readiness/permission checks, caregiver respondent source, 24-hour average plus current pain scores, expanded side-effect detail, and researcher alert flags. |
| [v0.2](./v0.2.md) | 2026-06-18 | First-class bilingual implementation with default Chinese UI, Chinese voice flow, Chinese validation, Chinese red-flag rules, and Chinese reports. |
| [v0.1](./v0.1.md) | 2026-06-18 | First local OA pain check-in prototype with browser UI, voice support, deterministic safety rules, validation layer, and report generation. |

## Suggested Format for Future Logs

Each version log should include:

- Version
- Date
- Goal
- User-facing changes
- Backend changes
- Safety/clinical-rule changes
- Validation changes
- Files changed
- Tests run
- Known limitations
- Follow-up candidates
