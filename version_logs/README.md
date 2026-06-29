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
