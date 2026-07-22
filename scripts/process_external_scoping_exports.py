#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_INPUT_DIR = "inputs/scoping_review"
DEFAULT_PUBMED_RECORDS = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/pubmed_records.csv"
DEFAULT_OUTPUT_DIR = "outputs/scoping_review/external_oa_voice_assistant"

OA_TERMS = (
    "osteoarthritis",
    "osteoarthrosis",
    "degenerative joint disease",
    "degenerative arthritis",
    "knee oa",
    "hip oa",
    "hand oa",
)

CONVERSATIONAL_TERMS = (
    "chatbot",
    "chatbots",
    "conversational agent",
    "conversational agents",
    "voice assistant",
    "voice assistants",
    "virtual assistant",
    "virtual assistants",
    "spoken dialogue",
    "spoken dialog",
    "dialogue system",
    "dialog system",
    "speech interface",
    "speech interfaces",
    "speech recognition",
    "voice recognition",
    "text messaging chatbot",
    "sms chatbot",
)

DIGITAL_TERMS = (
    "remote monitoring",
    "telemonitoring",
    "remote assessment",
    "home monitoring",
    "mobile app",
    "mobile application",
    "smartphone",
    "mhealth",
    "mobile health",
    "digital health",
    "web-based",
    "web based",
    "internet-based",
    "internet based",
    "website",
    "online",
    "telehealth",
    "telemedicine",
    "telerehabilitation",
    "tele-rehabilitation",
    "telephone",
    "sms",
    "text message",
    "wearable",
    "sensor",
    "accelerometer",
    "activity tracker",
    "smartwatch",
    "patient-reported outcome",
    "patient reported outcome",
    "electronic patient-reported",
    "epro",
    "clinical portal",
    "dashboard",
)

SELF_MANAGEMENT_TERMS = (
    "pain",
    "symptom",
    "symptoms",
    "function",
    "functional",
    "self-management",
    "self management",
    "rehabilitation",
    "exercise",
    "physical activity",
    "adherence",
    "patient-reported",
    "patient reported",
    "home",
    "monitoring",
)

REVIEW_TERMS = (
    "review",
    "systematic review",
    "scoping review",
    "meta-analysis",
    "meta analysis",
    "literature review",
)

POSTOP_TERMS = (
    "total knee arthroplasty",
    "total hip arthroplasty",
    "total joint arthroplasty",
    "knee arthroplasty",
    "hip arthroplasty",
    "joint replacement",
    "knee replacement",
    "hip replacement",
    "tka",
    "tha",
    "postoperative",
    "post-operative",
    "after surgery",
    "following surgery",
)

CLINICIAN_OR_DIAGNOSTIC_ONLY_TERMS = (
    "x-ray",
    "x ray",
    "radiograph",
    "radiographic",
    "mri",
    "magnetic resonance",
    "segmentation",
    "image classification",
    "diagnosis using cnn",
    "detecting knee osteoarthritis",
    "diagnostic accuracy",
)

CLINICAL_PATIENT_TERMS = (
    "patient",
    "patients",
    "participant",
    "participants",
    "older adult",
    "older adults",
    "home",
    "self-management",
    "self management",
    "patient-reported",
    "patient reported",
    "caregiver",
    "arthroplasty patients",
)

TECH_CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "chatbot_or_conversational_agent": CONVERSATIONAL_TERMS,
    "mobile_app_or_smartphone": ("mobile app", "mobile application", "smartphone", "mhealth", "mobile health"),
    "web_or_internet": ("web-based", "web based", "internet-based", "internet based", "website", "online", "portal"),
    "telehealth_or_telerehabilitation": ("telehealth", "telemedicine", "telerehabilitation", "tele-rehabilitation", "videoconference"),
    "telephone_or_sms": ("telephone", "phone call", "text message", "sms"),
    "wearable_sensor_or_activity_tracker": ("wearable", "sensor", "accelerometer", "activity tracker", "smartwatch", "inertial"),
    "electronic_patient_reported_outcome": ("patient-reported outcome", "patient reported outcome", "electronic questionnaire", "epro"),
    "imaging_or_diagnostic_ai": ("x-ray", "radiograph", "mri", "cnn", "deep learning", "segmentation", "classification"),
}

CLINICAL_CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "pain_intensity": ("pain score", "pain intensity", "pain severity", "visual analogue", "visual analog", "vas", "numeric rating", "nrs"),
    "pain_location_or_flare": ("pain location", "flare", "flares", "painful joint"),
    "function_or_disability": ("function", "functional", "disability", "activities of daily living", "adl", "womac", "koos", "hoos", "stairs", "walking"),
    "quality_of_life": ("quality of life", "qol", "eq-5d", "eq5d", "sf-12", "sf-36", "promis"),
    "physical_activity_or_exercise": ("physical activity", "exercise", "steps", "step count", "walking time"),
    "medication_or_treatment_use": ("analgesic", "medication", "medicine", "nsaid", "treatment", "injection"),
    "adherence_or_engagement": ("adherence", "engagement", "retention", "usage", "compliance"),
    "mental_health_or_sleep": ("depression", "anxiety", "sleep", "fatigue", "catastrophizing", "catastrophising"),
}

SAFETY_PATTERNS: dict[str, tuple[str, ...]] = {
    "adverse_events_or_harms": ("adverse event", "adverse events", "side effect", "side effects", "safety", "harm"),
    "red_flag_or_escalation": ("red flag", "urgent", "emergency", "escalation", "escalate", "seek medical", "medical attention"),
    "clinician_review_or_handoff": ("clinician", "physician", "doctor", "general practitioner", "provider", "dashboard", "portal", "report", "feedback"),
    "privacy_or_confidentiality": ("privacy", "confidentiality", "data protection", "data security", "encrypted", "hipaa", "gdpr"),
    "ethics_or_consent": ("ethics", "ethical approval", "institutional review board", "irb", "informed consent", "consent"),
}

EVALUATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "clinical_effectiveness": ("effectiveness", "efficacy", "randomized", "randomised", "between-group", "improved pain"),
    "feasibility_or_acceptability": ("feasibility", "acceptable", "acceptability", "pilot", "satisfaction"),
    "usability_or_user_experience": ("usability", "user experience", "ease of use", "system usability scale", "sus"),
    "adherence_or_engagement": ("adherence", "engagement", "retention", "completion rate", "response rate"),
    "technical_performance": ("accuracy", "sensitivity", "specificity", "precision", "recall", "classification"),
    "implementation_or_workflow": ("workflow", "implementation", "clinician workload", "cost", "resource"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import, deduplicate, screen, and chart external scoping-review exports.")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--pubmed-records", default=DEFAULT_PUBMED_RECORDS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_records = load_exports(input_dir)
    pubmed_records = read_csv(Path(args.pubmed_records)) if Path(args.pubmed_records).is_file() else []
    normalized = [normalize_record(row) for row in raw_records]
    deduped, duplicate_rows = dedupe_records(normalized, pubmed_records)
    screened = [screen_and_chart(row) for row in deduped]

    strict_rows = [row for row in screened if row["final_eligibility_decision"] == "strict_main_candidate"]
    context_rows = [row for row in screened if row["final_eligibility_decision"] == "context_appendix"]
    exclude_rows = [row for row in screened if row["final_eligibility_decision"] == "exclude"]

    write_csv(output_dir / "external_records_normalized.csv", normalized, normalized_fields())
    write_csv(output_dir / "external_duplicate_records.csv", duplicate_rows, duplicate_fields())
    write_csv(output_dir / "external_records_deduplicated.csv", deduped, normalized_fields())
    write_csv(output_dir / "external_screened_charted.csv", screened, screened_fields())
    write_csv(output_dir / "external_strict_main_candidates.csv", strict_rows, screened_fields())
    write_csv(output_dir / "external_context_appendix_candidates.csv", context_rows, screened_fields())
    write_csv(output_dir / "external_excluded_records.csv", exclude_rows, screened_fields())

    summary = summarize(raw_records, normalized, deduped, duplicate_rows, screened, pubmed_records, args)
    write_json(output_dir / "external_scoping_summary.json", summary)

    print(f"Imported external records: {len(raw_records)}")
    print(f"Deduplicated external records: {len(deduped)}")
    print(f"Duplicates removed or matched to PubMed: {len(duplicate_rows)}")
    print("Decision counts:", summary["decision_counts"])
    print("Strict candidate count:", len(strict_rows))
    print(f"Wrote outputs to {output_dir}")


def load_exports(input_dir: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        source = infer_source_database(path.name)
        if suffix in {".ris"}:
            records.extend(parse_ris(path, source))
        elif suffix in {".bib", ".bibtex"}:
            records.extend(parse_bibtex(path, source))
        elif suffix == ".csv":
            records.extend(parse_csv_export(path, source))
    return records


def parse_ris(path: Path, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current: dict[str, list[str]] = defaultdict(list)
    last_tag = ""
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^([A-Z0-9]{2})  -\s?(.*)$", raw_line)
        if match:
            tag = match.group(1)
            value = match.group(2).strip()
            last_tag = tag
            if tag == "TY":
                current = defaultdict(list)
                current[tag].append(value)
            elif tag == "ER":
                rows.append(ris_to_record(current, path, source))
                current = defaultdict(list)
                last_tag = ""
            else:
                current[tag].append(value)
        elif last_tag and raw_line.strip() and current.get(last_tag):
            current[last_tag][-1] = (current[last_tag][-1] + " " + raw_line.strip()).strip()
    if current:
        rows.append(ris_to_record(current, path, source))
    return [row for row in rows if row.get("title")]


def ris_to_record(data: dict[str, list[str]], path: Path, source: str) -> dict[str, str]:
    return {
        "source_database": source,
        "source_file": str(path),
        "source_record_id": first(data, "U2") or first(data, "ID") or first(data, "UR"),
        "record_type": first(data, "TY") or first(data, "M3"),
        "title": first(data, "TI") or first(data, "T1"),
        "authors": "; ".join(data.get("AU", []) or data.get("A1", [])),
        "year": first(data, "PY") or first(data, "Y1"),
        "journal_or_venue": first(data, "T2") or first(data, "JF") or first(data, "JO") or first(data, "BT"),
        "doi": normalize_doi(first(data, "DO") or first(data, "L2")),
        "url": first(data, "UR") or first(data, "L2"),
        "abstract": first(data, "AB") or first(data, "N2"),
        "keywords": "; ".join(data.get("KW", [])),
        "publication_types": first(data, "M3") or first(data, "TY"),
    }


def parse_bibtex(path: Path, source: str) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    entries = split_bibtex_entries(text)
    return [bibtex_to_record(entry, path, source) for entry in entries if entry.strip()]


def parse_csv_export(path: Path, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            rows.append({
                "source_database": row.get("source_database") or source,
                "source_file": row.get("source_file") or str(path),
                "source_record_id": row.get("source_record_id", ""),
                "record_type": row.get("record_type", ""),
                "title": row.get("title", ""),
                "authors": row.get("authors", ""),
                "year": row.get("year", ""),
                "journal_or_venue": row.get("journal_or_venue", ""),
                "doi": row.get("doi", ""),
                "url": row.get("url", ""),
                "abstract": row.get("abstract", ""),
                "keywords": row.get("keywords", ""),
                "publication_types": row.get("publication_types", ""),
            })
    return [row for row in rows if row.get("title")]


def split_bibtex_entries(text: str) -> list[str]:
    entries: list[str] = []
    start = -1
    depth = 0
    for idx, char in enumerate(text):
        if char == "@" and depth == 0:
            start = idx
        if start >= 0:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    entries.append(text[start : idx + 1])
                    start = -1
    return entries


def bibtex_to_record(entry: str, path: Path, source: str) -> dict[str, str]:
    header = re.match(r"@(\w+)\s*\{\s*([^,\s]+)", entry)
    fields = parse_bibtex_fields(entry)
    return {
        "source_database": source,
        "source_file": str(path),
        "source_record_id": header.group(2) if header else "",
        "record_type": header.group(1) if header else "",
        "title": clean_bibtex_value(fields.get("title", "")),
        "authors": clean_bibtex_value(fields.get("author", "")),
        "year": clean_bibtex_value(fields.get("year", "")),
        "journal_or_venue": clean_bibtex_value(fields.get("journal", "") or fields.get("booktitle", "") or fields.get("series", "")),
        "doi": normalize_doi(clean_bibtex_value(fields.get("doi", ""))),
        "url": clean_bibtex_value(fields.get("url", "")),
        "abstract": clean_bibtex_value(fields.get("abstract", "")),
        "keywords": clean_bibtex_value(fields.get("keywords", "")),
        "publication_types": clean_bibtex_value(fields.get("articletype", "") or (header.group(1) if header else "")),
    }


def parse_bibtex_fields(entry: str) -> dict[str, str]:
    body_start = entry.find(",")
    body = entry[body_start + 1 : entry.rfind("}")] if body_start >= 0 else entry
    fields: dict[str, str] = {}
    idx = 0
    while idx < len(body):
        match = re.search(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", body[idx:])
        if not match:
            break
        key = match.group(1).lower()
        idx += match.end()
        while idx < len(body) and body[idx].isspace():
            idx += 1
        if idx >= len(body):
            break
        value, idx = read_bibtex_value(body, idx)
        fields[key] = value
    return fields


def read_bibtex_value(text: str, idx: int) -> tuple[str, int]:
    if text[idx] == "{":
        depth = 0
        start = idx + 1
        while idx < len(text):
            if text[idx] == "{":
                depth += 1
            elif text[idx] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:idx], idx + 1
            idx += 1
    if text[idx] == '"':
        start = idx + 1
        idx += 1
        escaped = False
        while idx < len(text):
            if text[idx] == '"' and not escaped:
                return text[start:idx], idx + 1
            escaped = text[idx] == "\\" and not escaped
            idx += 1
    start = idx
    while idx < len(text) and text[idx] not in ",\n":
        idx += 1
    return text[start:idx].strip(), idx + 1


def normalize_record(row: dict[str, str]) -> dict[str, str]:
    title = normalize_space(row.get("title", ""))
    year = extract_year(row.get("year", ""))
    doi = normalize_doi(row.get("doi", ""))
    authors = normalize_space(row.get("authors", ""))
    return {
        **row,
        "title": title,
        "authors": authors,
        "year": year,
        "journal_or_venue": normalize_space(row.get("journal_or_venue", "")),
        "doi": doi,
        "url": normalize_space(row.get("url", "")),
        "abstract": normalize_space(row.get("abstract", "")),
        "keywords": normalize_space(row.get("keywords", "")),
        "publication_types": normalize_space(row.get("publication_types", "")),
        "normalized_title": normalize_title(title),
        "canonical_citation_id": canonical_citation_id({**row, "title": title, "authors": authors, "year": year, "doi": doi}),
        "record_hash": stable_hash([row.get("source_database", ""), title, year, doi]),
    }


def dedupe_records(rows: list[dict[str, str]], pubmed_records: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    pubmed_by_doi = {normalize_doi(row.get("doi", "")): row for row in pubmed_records if normalize_doi(row.get("doi", ""))}
    pubmed_by_title = {normalize_title(row.get("title", "")): row for row in pubmed_records if normalize_title(row.get("title", ""))}

    kept: list[dict[str, str]] = []
    duplicates: list[dict[str, str]] = []
    seen_doi: dict[str, dict[str, str]] = {}
    seen_title: dict[str, dict[str, str]] = {}

    for row in rows:
        doi = row["doi"]
        title_key = row["normalized_title"]
        duplicate_of = ""
        duplicate_basis = ""
        matched_pubmed_id = ""

        if doi and doi in pubmed_by_doi:
            duplicate_of = "pubmed"
            duplicate_basis = "doi"
            matched_pubmed_id = pubmed_by_doi[doi].get("pmid", "")
        elif title_key and title_key in pubmed_by_title:
            duplicate_of = "pubmed"
            duplicate_basis = "normalized_title"
            matched_pubmed_id = pubmed_by_title[title_key].get("pmid", "")
        elif doi and doi in seen_doi:
            duplicate_of = seen_doi[doi]["record_hash"]
            duplicate_basis = "doi"
        elif title_key and title_key in seen_title:
            duplicate_of = seen_title[title_key]["record_hash"]
            duplicate_basis = "normalized_title"

        if duplicate_of:
            duplicates.append({
                **row,
                "duplicate_of": duplicate_of,
                "duplicate_basis": duplicate_basis,
                "matched_pubmed_pmid": matched_pubmed_id,
            })
            continue

        kept.append(row)
        if doi:
            seen_doi[doi] = row
        if title_key:
            seen_title[title_key] = row

    return kept, duplicates


def screen_and_chart(row: dict[str, str]) -> dict[str, str]:
    title_abs = norm(" ".join([
        row.get("title", ""),
        row.get("abstract", ""),
    ]))
    text = norm(" ".join([
        row.get("title", ""),
        row.get("abstract", ""),
        row.get("keywords", ""),
        row.get("publication_types", ""),
        row.get("journal_or_venue", ""),
    ]))
    title = norm(row.get("title", ""))
    publication_type = norm(row.get("publication_types", ""))

    oa = has_any(text, OA_TERMS)
    oa_title_abs = has_any(title_abs, OA_TERMS)
    conversational = has_any(text, CONVERSATIONAL_TERMS)
    conversational_title_abs = has_any(title_abs, CONVERSATIONAL_TERMS)
    digital = has_any(text, DIGITAL_TERMS)
    self_management = has_any(text, SELF_MANAGEMENT_TERMS)
    patient_facing = has_any(text, CLINICAL_PATIENT_TERMS)
    review = has_any(title + " " + publication_type, REVIEW_TERMS)
    background_type = is_background_type(title, publication_type)
    postop_only = has_postop_only(title, text)
    diagnostic_only = is_diagnostic_only(title, text)
    registry_record = "clinicaltrials.gov" in norm(row.get("journal_or_venue", "")) or row.get("source_record_id", "").startswith("LNCT")
    protocol = "protocol" in title or "protocol" in publication_type or "study protocol" in text or registry_record

    notes: list[str] = []
    if not oa:
        decision = "exclude"
        reason = "wrong_population_or_no_oa_focus"
        notes.append("No clear OA population or OA-specific subgroup in title/abstract/keywords.")
    elif background_type or (review and not protocol):
        decision = "exclude"
        reason = "review_background_or_model_only"
        notes.append("Review, editorial, letter, abstract collection, or background record; useful only for citation chasing.")
    elif postop_only and not (conversational_title_abs and oa_title_abs):
        decision = "exclude"
        reason = "post_arthroplasty_only"
        notes.append("Post-arthroplasty/TKA focus without conversational monitoring signal.")
    elif diagnostic_only and not patient_facing_monitoring(text):
        decision = "exclude"
        reason = "diagnostic_or_clinician_facing_only"
        notes.append("Diagnostic/imaging/model study rather than patient-facing OA monitoring.")
    elif is_medical_education_or_benchmark_only(title, text):
        decision = "exclude"
        reason = "medical_education_or_benchmark_only"
        notes.append("LLM or AI benchmark/education study rather than patient-facing OA monitoring.")
    elif is_non_oa_pain_or_loneliness_trial(title, text):
        decision = "exclude"
        reason = "wrong_population_or_no_oa_focus"
        notes.append("OA appears as background; enrolled population is broader pain/loneliness rather than OA-specific.")
    elif conversational_title_abs and oa_title_abs and patient_facing and protocol:
        decision = "context_appendix"
        reason = "planned_or_protocol_context"
        notes.append("Planned OA chatbot/conversational system; chart as context until a completed study report is available.")
    elif conversational_title_abs and oa_title_abs and patient_facing and not review:
        decision = "strict_main_candidate"
        reason = ""
        notes.append("OA-relevant patient-facing chatbot/conversational/voice signal; requires full-text confirmation.")
    elif conversational and patient_facing and (not conversational_title_abs or not oa_title_abs):
        decision = "exclude"
        reason = "keyword_only_conversational_or_oa_signal"
        notes.append("Conversational or OA signal appears only in database indexing/keywords, not enough for strict inclusion.")
    elif digital and patient_facing and self_management:
        decision = "context_appendix"
        reason = "non_conversational_digital_health_context"
        notes.append("OA digital health, monitoring, telehealth, ePRO, wearable, or app evidence relevant as context.")
    elif digital and self_management:
        decision = "context_appendix"
        reason = "digital_self_management_context"
        notes.append("Digital OA self-management or monitoring signal; patient-facing role should be checked.")
    elif protocol and digital:
        decision = "context_appendix"
        reason = "planned_or_protocol_context"
        notes.append("Digital OA protocol; relevant as context, not completed evidence.")
    else:
        decision = "exclude"
        reason = "not_patient_facing_conversational_or_monitoring"
        notes.append("Does not meet strict main concept and is not strong enough for context charting.")

    return {
        **row,
        "final_eligibility_decision": decision,
        "final_exclusion_or_context_reason": reason,
        "screening_notes": " ".join(notes),
        "needs_full_text_confirmation": yes_no(decision == "strict_main_candidate" or (decision == "context_appendix" and conversational)),
        "has_oa_signal": yes_no(oa),
        "has_conversational_signal": yes_no(conversational),
        "has_oa_title_abstract_signal": yes_no(oa_title_abs),
        "has_conversational_title_abstract_signal": yes_no(conversational_title_abs),
        "has_digital_health_signal": yes_no(digital),
        "has_patient_facing_signal": yes_no(patient_facing),
        "technology_categories": "; ".join(match_categories(text, TECH_CATEGORY_PATTERNS)) or "unclear_or_none",
        "clinical_assessment_categories": "; ".join(match_categories(text, CLINICAL_CATEGORY_PATTERNS)) or "unclear_or_none",
        "safety_privacy_handoff_categories": "; ".join(match_categories(text, SAFETY_PATTERNS)) or "unclear_or_none",
        "evaluation_outcome_categories": "; ".join(match_categories(text, EVALUATION_PATTERNS)) or "unclear_or_none",
    }


def summarize(
    raw_records: list[dict[str, str]],
    normalized: list[dict[str, str]],
    deduped: list[dict[str, str]],
    duplicates: list[dict[str, str]],
    screened: list[dict[str, str]],
    pubmed_records: list[dict[str, str]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_dir": args.input_dir,
        "pubmed_records_input": args.pubmed_records,
        "output_dir": args.output_dir,
        "external_raw_record_count": len(raw_records),
        "external_normalized_record_count": len(normalized),
        "external_deduplicated_record_count": len(deduped),
        "duplicate_or_pubmed_match_count": len(duplicates),
        "pubmed_reference_record_count": len(pubmed_records),
        "source_counts_raw": dict(Counter(row["source_database"] for row in raw_records)),
        "source_counts_deduplicated": dict(Counter(row["source_database"] for row in deduped)),
        "duplicate_basis_counts": dict(Counter(row["duplicate_basis"] for row in duplicates)),
        "duplicates_matched_to_pubmed": sum(row["duplicate_of"] == "pubmed" for row in duplicates),
        "decision_counts": dict(Counter(row["final_eligibility_decision"] for row in screened)),
        "reason_counts": dict(Counter(row["final_exclusion_or_context_reason"] for row in screened if row["final_exclusion_or_context_reason"])),
        "strict_main_candidate_count": sum(row["final_eligibility_decision"] == "strict_main_candidate" for row in screened),
        "context_appendix_candidate_count": sum(row["final_eligibility_decision"] == "context_appendix" for row in screened),
        "conversational_signal_count": sum(row["has_conversational_signal"] == "yes" for row in screened),
        "conversational_title_abstract_signal_count": sum(row["has_conversational_title_abstract_signal"] == "yes" for row in screened),
        "voice_or_speech_title_abstract_count": sum("voice" in norm(row.get("title", "") + " " + row.get("abstract", "")) or "speech" in norm(row.get("title", "") + " " + row.get("abstract", "")) for row in screened),
        "technology_counts": count_semicolon_field(screened, "technology_categories"),
        "clinical_assessment_counts": count_semicolon_field(screened, "clinical_assessment_categories"),
        "safety_privacy_handoff_counts": count_semicolon_field(screened, "safety_privacy_handoff_categories"),
        "evaluation_outcome_counts": count_semicolon_field(screened, "evaluation_outcome_categories"),
        "note": "Machine-assisted import, deduplication, screening, and charting of external database exports. Strict candidates require full-text confirmation before final included-study claims.",
    }


def infer_source_database(filename: str) -> str:
    name = filename.lower()
    if "scopus" in name:
        return "Scopus"
    if "embase" in name:
        return "Embase"
    if "ieee" in name:
        return "IEEE Xplore"
    if "acm" in name:
        return "ACM Digital Library"
    if "ebsco" in name or "cinahl" in name:
        return "EBSCO/CINAHL"
    return "External"


def has_postop_only(title: str, text: str) -> bool:
    if not has_any(text, POSTOP_TERMS):
        return False
    if any(term in title for term in ("arthroplasty", "replacement", "postoperative", "post-operative", "after knee replacement")):
        return True
    non_surgical = ("knee osteoarthritis", "hip osteoarthritis", "hand osteoarthritis", "osteoarthritis management")
    return not has_any(text, non_surgical)


def is_diagnostic_only(title: str, text: str) -> bool:
    if not has_any(text, CLINICIAN_OR_DIAGNOSTIC_ONLY_TERMS):
        return False
    monitoring_terms = ("home monitoring", "remote monitoring", "self-management", "self management", "patient-reported", "rehabilitation")
    if has_any(text, monitoring_terms):
        return False
    return any(term in title for term in ("detect", "diagnos", "classification", "segmentation", "x-ray", "cnn"))


def is_background_type(title: str, publication_type: str) -> bool:
    if any(term in publication_type for term in ("editorial", "letter")):
        return True
    if "conference abstract" in publication_type:
        return True
    if any(term in title for term in ("poster abstracts", "editor's awards", "publication honors")):
        return True
    return False


def is_medical_education_or_benchmark_only(title: str, text: str) -> bool:
    if "evaluating llms against students" in title:
        return True
    if "physiotherapy students" in text and "clinical questions" in text:
        return True
    if "responses were evaluated" in text and "clinical questions" in text and "students" in text:
        return True
    return False


def is_non_oa_pain_or_loneliness_trial(title: str, text: str) -> bool:
    if "loneliness epidemic" not in title:
        return False
    if "self-report pain" in text and "patients with hip and knee osteoarthritis" not in text and "osteoarthritis patients" not in text:
        return True
    return False


def patient_facing_monitoring(text: str) -> bool:
    return has_any(text, CLINICAL_PATIENT_TERMS) and has_any(text, DIGITAL_TERMS) and has_any(text, SELF_MANAGEMENT_TERMS)


def match_categories(text: str, patterns: dict[str, tuple[str, ...]]) -> list[str]:
    return [category for category, terms in patterns.items() if has_any(text, terms)]


def count_semicolon_field(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        for value in row.get(field, "").split(";"):
            value = value.strip()
            if value and value != "unclear_or_none":
                counter[value] += 1
    return dict(counter)


def first(data: dict[str, list[str]], key: str) -> str:
    values = data.get(key, [])
    return values[0] if values else ""


def clean_bibtex_value(value: str) -> str:
    value = value.replace('\\"', '"')
    value = re.sub(r"\\[&%_$#{}]", lambda match: match.group(0)[1:], value)
    value = re.sub(r"\\[A-Za-z]+", "", value)
    value = value.replace("{", "").replace("}", "")
    return normalize_space(value)


def canonical_citation_id(row: dict[str, str]) -> str:
    doi = normalize_doi(row.get("doi", ""))
    if doi:
        return f"doi:{doi}"
    source_record_id = normalize_space(row.get("source_record_id", ""))
    if source_record_id and re.search(r"(scopus|embase|clinicaltrials|pmc|pubmed)", source_record_id, flags=re.I):
        return f"source:{source_record_id}"
    title_key = normalize_title(row.get("title", ""))
    year = extract_year(row.get("year", ""))
    authors = normalize_title((row.get("authors", "") or "").split(";")[0])
    return f"external:{stable_hash([title_key, year, authors])}"


def normalize_doi(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", value)
    if not match:
        return ""
    return match.group(0).rstrip(".,;").lower()


def extract_year(value: str) -> str:
    match = re.search(r"(19|20)\d{2}", value or "")
    return match.group(0) if match else ""


def normalize_title(value: str) -> str:
    value = clean_bibtex_value(value)
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    stop = {"a", "an", "the", "of", "for", "and", "or", "to", "in", "on", "with"}
    tokens = [token for token in value.split() if token not in stop]
    return " ".join(tokens)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def stable_hash(parts: list[str]) -> str:
    return hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()[:12]


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def norm(value: str) -> str:
    return normalize_space(value).lower()


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def normalized_fields() -> list[str]:
    return [
        "source_database",
        "source_file",
        "source_record_id",
        "canonical_citation_id",
        "record_hash",
        "record_type",
        "title",
        "authors",
        "year",
        "journal_or_venue",
        "doi",
        "url",
        "abstract",
        "keywords",
        "publication_types",
        "normalized_title",
    ]


def duplicate_fields() -> list[str]:
    return normalized_fields() + ["duplicate_of", "duplicate_basis", "matched_pubmed_pmid"]


def screened_fields() -> list[str]:
    return normalized_fields() + [
        "final_eligibility_decision",
        "final_exclusion_or_context_reason",
        "screening_notes",
        "needs_full_text_confirmation",
        "has_oa_signal",
        "has_conversational_signal",
        "has_oa_title_abstract_signal",
        "has_conversational_title_abstract_signal",
        "has_digital_health_signal",
        "has_patient_facing_signal",
        "technology_categories",
        "clinical_assessment_categories",
        "safety_privacy_handoff_categories",
        "evaluation_outcome_categories",
    ]


if __name__ == "__main__":
    main()
