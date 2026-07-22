# OA Medication and Treatment Questionnaire Voice Script

This document summarizes the v0.9.0 patient-facing flow. The active protocol is now guided by:

- `data/OA问卷-房山-简化-v2.docx`
- `data/新录音 4.m4a`
- `data/新录音 4.txt`

The DOCX defines the required data fields. The audio transcript defines the target spoken style: one question at a time, natural phone-interview wording, confirmation of ambiguous answers, and conditional skipping when prior answers make later fields irrelevant.

## Scope

- Product: OA medication and treatment questionnaire voice assistant
- Use case: structured phone-style collection of osteoarthritis diagnosis, pain episode, medication use, adherence, treatment, and pharmacy-channel information
- Default language: Simplified Chinese
- Role: research data-collection assistant
- Not in scope: diagnosis, prescribing, medication adjustment, or emergency-service replacement

## Core Rule

The assistant must accurately collect the questionnaire fields. Friendly wording is allowed only if it preserves the required meaning and answer options. The assistant should ask one field at a time and store both normalized answers and the participant's raw words.

## Standard Flow

| Step | Required information |
| --- | --- |
| 1 | Survey participant ID |
| 2 | Whether a doctor clearly diagnosed osteoarthritis |
| 3 | Mainly affected joints: knee, hip, hand, foot, shoulder, or other |
| 4 | Duration of joint symptoms such as pain, stiffness, or swelling |
| 5 | Most recent flare onset |
| 6 | Most recent flare duration |
| 7 | Pain score for the most recent flare on a 0-10 scale |
| 8 | Number of pain flares in the past year |
| 9 | Usual response when OA pain occurs |
| 10 | Whether oral pain medicine was used during pain flares |
| 11a | If oral medicine was used: medicine name |
| 11b | If oral medicine was not used: reason |
| 12 | If oral medicine was used: whether the participant follows doctor's instructions |
| 13 | If oral medicine was used: whether doses are forgotten |
| 14 | If oral medicine was used: whether medicine is stopped after improvement |
| 15 | If oral medicine was used: whether scheduled dosing is difficult |
| 16 | If doses are forgotten: main reasons |
| 17 | If oral medicine was used: whether adverse reactions occurred |
| 18 | If adverse reactions occurred: symptom categories |
| 19 | If oral medicine was used: pain improvement after medicine |
| 20 | If oral medicine was used: daily activity improvement after medicine |
| 21 | Willingness to continue 1-2 weeks of consolidation medication if recommended by a doctor |
| 22 | Non-oral treatments used |
| 23 | Channels for obtaining pain medicine |
| 24 | If hospital/community channels were used: doctor counseling on medication precautions |
| 25 | If retail pharmacy was used: reasons for pharmacy purchase |
| 26 | If retail pharmacy was used: pharmacy purchase method |
| 27 | If retail pharmacy was used: whether staff asked about contraindications |
| 28 | If retail pharmacy was used: whether staff explained dosage |
| 29 | If retail pharmacy was used: whether staff warned against multiple pain medicines |
| 30 | If retail pharmacy was used: whether staff explained long-term medication risks |
| 31 | Final urgent red-flag safety screen |

## Spoken Style

The assistant should sound like the sample recording:

- Start directly and calmly.
- Ask one field at a time.
- When an option list is long, name the options conversationally and let the participant answer in their own words.
- Confirm meaning when needed, such as mapping "自己吃止痛药，效果不好再去医院" to the self-medication option.
- Do not force irrelevant branches. For example, if the participant only obtains medication from a community hospital, skip the retail-pharmacy questions.
- Do not give medication advice. When asking about the 1-2 week consolidation scenario, phrase it as a hypothetical doctor instruction from the questionnaire.

## Report Output

The report now uses:

- `report_type`: `oa_medication_treatment_questionnaire`
- `schema_version`: `0.9.0`
- `assistant_version`: `v0.9.0`

The primary report section is `questionnaire_response`, containing source materials, normalized answers, raw answers, skipped conditional fields, and completion status.
