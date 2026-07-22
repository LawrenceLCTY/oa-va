#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_QWEN = "outputs/scoping_review/qwen_adjudication_fulltext_v3/qwen_record_adjudication.csv"
DEFAULT_OUTPUT_DIR = "outputs/scoping_review/final_main_evidence"

STUDY_METADATA = {
    "study_01_alley_ortho_companion": {
        "study_label": "alley ortho companion",
        "population": "Patients with knee or hip osteoarthritis",
        "setting": "Patient-accompanying perioperative orthopedic pathway",
        "design": "Randomized controlled multicenter trial protocol",
        "technology": "Patient-facing eHealth/mobile app",
        "clinical_function": "Information, organization, and emotional or empowerment support around orthopedic care",
        "evaluation_outcomes": "Protocol; planned functional and patient-experience outcomes",
        "safety_handoff_privacy_notes": "No direct home pain check-in or red-flag escalation evidence identified from the charted text",
        "evidence_role": "OA-adjacent digital support; retained as patient-facing interactive OA support evidence",
        "relevance_to_project": "Supports need for patient-facing OA support tools, but is not a voice assistant or longitudinal pain check-in system",
    },
    "study_02_llm_perioperative_anxiety": {
        "study_label": "LLM dialogue system for perioperative anxiety",
        "population": "Patients with osteoarthritis undergoing total knee replacement",
        "setting": "Perioperative total knee replacement pathway",
        "design": "Prospective randomized controlled trial registry record",
        "technology": "Large-language-model dialogue system",
        "clinical_function": "Emotional counselling and perioperative anxiety relief",
        "evaluation_outcomes": "Trial registry outcomes; completed results not available in exported metadata",
        "safety_handoff_privacy_notes": "Perioperative emotional-support use; no home OA pain red-flag workflow identified",
        "evidence_role": "OA-adjacent perioperative conversational evidence",
        "relevance_to_project": "Shows patient-facing LLM dialogue in an OA-related surgical pathway, but does not evaluate home symptom monitoring",
    },
    "study_03_nlp_home_rehab_adherence": {
        "study_label": "NLP/chatbot tool for home rehabilitation adherence",
        "population": "Osteoarthritis patients after major joint replacement surgeries",
        "setting": "Home rehabilitation after joint replacement",
        "design": "Conference/article record in Osteoarthritis and Cartilage metadata",
        "technology": "Smartphone chatbot or natural-language-processing tool",
        "clinical_function": "Exercise recommendations and compliance tracking for home rehabilitation",
        "evaluation_outcomes": "Adherence and rehabilitation support signals in metadata",
        "safety_handoff_privacy_notes": "No direct red-flag escalation or privacy architecture identified from exported metadata",
        "evidence_role": "OA-adjacent postoperative rehabilitation chatbot evidence",
        "relevance_to_project": "Relevant to conversational adherence support but not direct OA home pain check-in",
    },
    "study_04_line_chatbot_tka_rehab": {
        "study_label": "LINE chatbot after total knee arthroplasty",
        "population": "Osteoarthritis patients after total knee arthroplasty",
        "setting": "Postoperative rehabilitation",
        "design": "Randomized controlled trial registry record",
        "technology": "LINE mobile chatbot",
        "clinical_function": "Rehabilitation instructions after total knee arthroplasty",
        "evaluation_outcomes": "Trial registry outcomes; completed results not available in exported metadata",
        "safety_handoff_privacy_notes": "No direct OA red-flag home-monitoring workflow identified",
        "evidence_role": "OA-adjacent postoperative chatbot rehabilitation evidence",
        "relevance_to_project": "Relevant to chatbot-delivered rehab instructions, but not longitudinal nonsurgical OA pain monitoring",
    },
    "study_05_virtual_assistant_history_taking": {
        "study_label": "Virtual assistant for orthopedic consultation preparation",
        "population": "Older adults referred for knee or hip osteoarthritis",
        "setting": "Pre-consultation orthopedic care",
        "design": "Feasibility and acceptability study",
        "technology": "Avatar-based virtual assistant using speech recognition, Google Dialogflow, rule-based logic, and ChatGPT 3.5",
        "clinical_function": "Patient history taking before face-to-face orthopedic consultation",
        "evaluation_outcomes": "Feasibility and acceptability; 40 participants in exported abstract",
        "safety_handoff_privacy_notes": "Clinician-facing pre-consultation role implied; red-flag and audio privacy details not fully charted",
        "evidence_role": "Closest direct OA virtual-assistant evidence",
        "relevance_to_project": "Strongly relevant to conversational intake and clinician handoff, but not repeated home pain monitoring",
    },
    "study_06_llm_chatbot_exercise_adherence": {
        "study_label": "LLM chatbot for knee OA exercise adherence",
        "population": "People with knee osteoarthritis",
        "setting": "Exercise-based treatment/self-management",
        "design": "System development study",
        "technology": "Large-language-model chatbot with retrieval/reasoning methods",
        "clinical_function": "Evidence-based guidance and adherence support for exercise treatment",
        "evaluation_outcomes": "Response quality, relevance, consistency, and conversational coherence in metadata",
        "safety_handoff_privacy_notes": "Mentions hallucination mitigation; clinician handoff and red-flag workflow not established from exported metadata",
        "evidence_role": "Direct OA chatbot system-development evidence",
        "relevance_to_project": "Relevant to bounded LLM use and adherence support, but not a voice-first pain check-in assistant",
    },
    "study_07_chat_oa": {
        "study_label": "CHAT-OA",
        "population": "Patients with hip or knee osteoarthritis",
        "setting": "Before orthopedic clinic visit",
        "design": "Planned/open clinical trial registry record",
        "technology": "Generative-AI chatbot",
        "clinical_function": "Decision-making support, health literacy, anxiety, decisional conflict, and patient-reported outcomes",
        "evaluation_outcomes": "Planned decisional conflict, anxiety, health literacy, and patient-reported outcome measures",
        "safety_handoff_privacy_notes": "Structured pre-clinic interaction; safety, escalation, and privacy details not fully available in exported metadata",
        "evidence_role": "Direct OA chatbot trial evidence, but currently registry/planned evidence",
        "relevance_to_project": "Relevant to OA-specific patient-facing chatbot use, but not a home pain check-in workflow",
    },
    "study_08_llm_guided_degenerative_knee_rehab": {
        "study_label": "LLM-guided rehabilitation for degenerative knee disease",
        "population": "Adults with degenerative knee disease, including knee OA relevance",
        "setting": "Outpatient physiotherapy/rehabilitation",
        "design": "Randomized four-arm clinical trial registry record",
        "technology": "ChatGPT-5, Gemini 2.5 Pro, and DeepSeek V3.1 assisted exercise prescription",
        "clinical_function": "LLM-assisted rehabilitation-program planning reviewed by physiotherapists",
        "evaluation_outcomes": "Planned pain, function, quality of life, performance, strength, range of motion, and psychosocial outcomes",
        "safety_handoff_privacy_notes": "LLM suggestions reviewed by physiotherapists before implementation; no autonomous red-flag home monitoring identified",
        "evidence_role": "OA-relevant LLM-guided rehabilitation evidence",
        "relevance_to_project": "Supports clinician-supervised bounded LLM use; indirect for home voice monitoring",
    },
    "study_09_deeptherapy": {
        "study_label": "DeepTherapy",
        "population": "Osteoarthritis rehabilitation context; exported abstract reports OA patient evaluation and physiotherapist evaluation",
        "setting": "Mobile OA rehabilitation",
        "design": "AI platform development/evaluation study",
        "technology": "Mobile platform using deep learning exercise analysis and LLM feedback",
        "clinical_function": "Movement assessment, incorrect movement identification, and corrective rehabilitation feedback",
        "evaluation_outcomes": "Technical performance, agreement with expert assessment, Likert-rated feedback quality",
        "safety_handoff_privacy_notes": "Physiotherapist evaluation reported; no home pain red-flag escalation workflow identified",
        "evidence_role": "OA AI-guided rehabilitation platform evidence",
        "relevance_to_project": "Relevant to AI feedback and rehabilitation monitoring, but not conversational pain check-in",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build final main-evidence record and study-level tables for the OA scoping review.")
    parser.add_argument("--qwen", default=DEFAULT_QWEN)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = [row for row in read_csv(Path(args.qwen)) if row.get("qwen_decision") == "MAIN_EVIDENCE"]
    for row in rows:
        row["study_id"] = infer_study_id(row)
        row["human_final_main_evidence_status"] = "confirmed_main_evidence"
        row["study_level_duplicate_action"] = "retain_as_unique_study"
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["study_id"]].append(row)
    for group in groups.values():
        if len(group) > 1:
            for row in group:
                row["study_level_duplicate_action"] = "collapse_with_same_study_records"

    record_fields = [
        "study_id",
        "human_final_main_evidence_status",
        "study_level_duplicate_action",
        "citation_id",
        "record_id",
        "source_set",
        "source_database",
        "year",
        "title",
        "doi",
        "journal_or_venue",
        "main_evidence_type",
        "qwen_reason",
        "qwen_key_evidence",
        "full_text_source",
    ]
    write_csv(output_dir / "final_main_evidence_records.csv", rows, record_fields)

    study_rows = [make_study_row(study_id, group) for study_id, group in sorted(groups.items())]
    study_fields = [
        "study_id",
        "representative_title",
        "year",
        "doi",
        "source_databases",
        "source_records_collapsed_n",
        "study_label",
        "population",
        "setting",
        "design",
        "technology",
        "clinical_function",
        "evaluation_outcomes",
        "safety_handoff_privacy_notes",
        "evidence_role",
        "relevance_to_project",
        "record_titles_collapsed",
    ]
    write_csv(output_dir / "final_main_evidence_studies.csv", study_rows, study_fields)
    write_markdown(output_dir / "final_main_evidence_studies.md", study_rows)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "qwen_main_record_count": len(rows),
        "final_distinct_study_count": len(study_rows),
        "duplicate_record_count_collapsed": len(rows) - len(study_rows),
        "source": args.qwen,
        "outputs": {
            "records": str(output_dir / "final_main_evidence_records.csv"),
            "studies": str(output_dir / "final_main_evidence_studies.csv"),
            "markdown": str(output_dir / "final_main_evidence_studies.md"),
        },
        "note": "All Qwen MAIN_EVIDENCE rows are preserved in the record-level table; obvious same-study duplicate records are collapsed only in the study-level table.",
    }
    write_json(output_dir / "final_main_evidence_summary.json", summary)
    print(json.dumps(summary, indent=2))


def infer_study_id(row: dict[str, str]) -> str:
    title = normalize(row.get("title", ""))
    if "alley ortho companion" in title:
        return "study_01_alley_ortho_companion"
    if "perioperative anxiety" in title and "large language model dialogue" in title:
        return "study_02_llm_perioperative_anxiety"
    if "natural language processing tool" in title and "home rehabilitation" in title:
        return "study_03_nlp_home_rehab_adherence"
    if "mobile application" in title and "total knee arthroplasty" in title:
        return "study_04_line_chatbot_tka_rehab"
    if "human interaction with a virtual assistant" in title:
        return "study_05_virtual_assistant_history_taking"
    if "chatbot based on large language model" in title:
        return "study_06_llm_chatbot_exercise_adherence"
    if "conversations in health literacy" in title or "chat oa" in title:
        return "study_07_chat_oa"
    if "chatgpt 5" in title and "deepseek" in title:
        return "study_08_llm_guided_degenerative_knee_rehab"
    if "deeptherapy" in title:
        return "study_09_deeptherapy"
    return "study_unmapped_" + re.sub(r"[^a-z0-9]+", "_", title)[:50].strip("_")


def make_study_row(study_id: str, group: list[dict[str, str]]) -> dict[str, str]:
    representative = pick_representative(group)
    meta = STUDY_METADATA.get(study_id, {})
    titles = sorted({row.get("title", "") for row in group if row.get("title")})
    sources = sorted({row.get("source_database", "") for row in group if row.get("source_database")})
    dois = sorted({row.get("doi", "") for row in group if row.get("doi")})
    return {
        "study_id": study_id,
        "representative_title": representative.get("title", ""),
        "year": representative.get("year", ""),
        "doi": "; ".join(dois),
        "source_databases": "; ".join(sources),
        "source_records_collapsed_n": str(len(group)),
        "record_titles_collapsed": " | ".join(titles),
        **meta,
    }


def pick_representative(group: list[dict[str, str]]) -> dict[str, str]:
    def score(row: dict[str, str]) -> tuple[int, int, int]:
        return (
            1 if row.get("doi") else 0,
            1 if row.get("full_text_source") else 0,
            len(row.get("title", "")),
        )
    return max(group, key=score)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["study_label", "year", "population", "design", "technology", "clinical_function", "evidence_role"]
    lines = [
        "| Study | Year | Population | Design | Technology | Clinical function | Evidence role |",
        "| ----- | ---- | ---------- | ------ | ---------- | ----------------- | ------------- |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(escape_md(row.get(field, "")) for field in fields) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def escape_md(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ")

def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (value or "").lower())).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
