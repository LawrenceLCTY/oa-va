#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chart_pmc_full_text import PATTERNS, matching_categories, matching_terms, infer_countries, yes_no

DEFAULT_RECORDS = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/pubmed_no_pmc_full_text_to_retrieve.csv"
DEFAULT_PDF_DIR = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/doi_full_text/pdf"
DEFAULT_OUTPUT = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/doi_pdf_full_text_chart.csv"
DEFAULT_MATCH_INDEX = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/doi_pdf_local_match_index.csv"
DEFAULT_SUMMARY = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/doi_pdf_full_text_summary.json"

MANUAL_LINKS = [
    {
        "pmid": "26314289",
        "doi": "10.1002/acr.22709",
        "url": "https://acrjournals.onlinelibrary.wiley.com/doi/epdf/10.1002/acr.22709",
        "note": "User-provided Wiley ePDF link; accessible as link-only unless PDF is saved locally.",
    }
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Chart locally retrieved DOI PDFs for the OA scoping review.")
    parser.add_argument("--records", default=DEFAULT_RECORDS)
    parser.add_argument("--pdf-dir", default=DEFAULT_PDF_DIR)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--match-index", default=DEFAULT_MATCH_INDEX)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    records = {row["pmid"]: row for row in read_csv(Path(args.records))}
    pdf_rows, rejected_rows = match_pdfs(Path(args.pdf_dir), records)
    chart_rows = [chart_pdf(row, records[row["matched_pmid"]]) for row in pdf_rows]
    chart_rows.extend(chart_manual_link(link, records) for link in MANUAL_LINKS if link["pmid"] in records)

    write_csv(Path(args.match_index), pdf_rows + rejected_rows, match_fields())
    write_csv(Path(args.output), chart_rows, chart_fields())
    summary = summarize(chart_rows, pdf_rows, rejected_rows, args)
    write_json(Path(args.summary_output), summary)

    print(f"Matched PDF files: {len(pdf_rows)}")
    print(f"Rejected/duplicate PDF files: {len(rejected_rows)}")
    print(f"Chart rows: {len(chart_rows)}")
    print("Access counts:", summary["access_type_counts"])
    print("Technology counts:", summary["technology_counts"])
    print(f"Wrote {args.match_index}")
    print(f"Wrote {args.output}")
    print(f"Wrote {args.summary_output}")


def match_pdfs(pdf_dir: Path, records: dict[str, dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    accepted: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    seen_pmids: set[str] = set()

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        text = extract_pdf_text(pdf_path)
        text_head = text[:20000]
        detected_doi = detect_doi(text_head)
        candidate = best_record_match(pdf_path, text_head, detected_doi, records)
        base = {
            "local_pdf_path": str(pdf_path),
            "pdf_file": pdf_path.name,
            "size_bytes": str(pdf_path.stat().st_size),
            "doi_detected_in_pdf": detected_doi,
            "match_status": "",
            "matched_pmid": "",
            "matched_doi_from_table": "",
            "matched_title": "",
            "match_score": "0.000",
            "reject_reason": "",
        }
        if not candidate:
            rejected.append({**base, "match_status": "rejected", "reject_reason": "no_confident_pmid_or_doi_match"})
            continue
        score, pmid, record = candidate
        if pmid in seen_pmids:
            rejected.append({
                **base,
                "match_status": "duplicate_rejected",
                "matched_pmid": pmid,
                "matched_doi_from_table": record.get("doi", ""),
                "matched_title": record.get("title", ""),
                "match_score": f"{score:.3f}",
                "reject_reason": "duplicate_pdf_for_same_pmid",
            })
            continue
        seen_pmids.add(pmid)
        accepted.append({
            **base,
            "match_status": "matched",
            "matched_pmid": pmid,
            "matched_doi_from_table": record.get("doi", ""),
            "matched_title": record.get("title", ""),
            "match_score": f"{score:.3f}",
            "reject_reason": "",
        })
    return accepted, rejected


def best_record_match(pdf_path: Path, text: str, detected_doi: str, records: dict[str, dict[str, str]]) -> tuple[float, str, dict[str, str]] | None:
    lower = text.lower()
    filename = pdf_path.name.lower()
    candidates: list[tuple[float, str, dict[str, str]]] = []
    for pmid, record in records.items():
        doi = normalize_doi(record.get("doi", ""))
        score = title_score(text, record.get("title", ""))
        if doi and detected_doi and doi == detected_doi:
            score = max(score, 1.0)
        elif detected_doi and doi and detected_doi != doi:
            # Avoid false matches where a PDF cites a target paper but is actually a different article.
            score = 0.0
        if pmid in filename:
            score = max(score, 1.0)
        if doi and doi.replace("/", "_").replace(".", "_").lower() in filename.replace(".", "_"):
            score = max(score, 0.95)
        if score >= 0.55:
            candidates.append((score, pmid, record))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0]


def chart_pdf(match: dict[str, str], record: dict[str, str]) -> dict[str, str]:
    text = extract_pdf_text(Path(match["local_pdf_path"]))
    normalized = normalize(text)
    matches = {group: matching_categories(normalized, patterns) for group, patterns in PATTERNS.items()}
    if not matches["technology"]:
        matches["technology"] = ["unclear_or_noninteractive_digital_component"]
    if not matches["clinical_assessment"]:
        matches["clinical_assessment"] = ["unclear_clinical_assessment"]
    if not matches["study_design"]:
        matches["study_design"] = ["unclear_or_other"]
    matched_terms = {group: "; ".join(matching_terms(normalized, patterns)) for group, patterns in PATTERNS.items()}
    return {
        "pmid": match["matched_pmid"],
        "doi": record.get("doi", ""),
        "year": record.get("year", ""),
        "title": record.get("title", ""),
        "journal": record.get("journal", ""),
        "current_decision": record.get("current_decision", ""),
        "current_reason": record.get("current_reason", ""),
        "full_text_access_type": "local_pdf",
        "local_pdf_path": match["local_pdf_path"],
        "manual_url": "",
        "country_or_region_inferred": "; ".join(infer_countries(text[:60000])),
        "study_design_pdf": "; ".join(matches["study_design"]),
        "oa_joint_or_population_pdf": "; ".join(matches["oa_joint"]),
        "technology_category_pdf": "; ".join(matches["technology"]),
        "clinical_assessment_content_pdf": "; ".join(matches["clinical_assessment"]),
        "safety_privacy_handoff_pdf": "; ".join(matches["safety_privacy_handoff"]),
        "evaluation_outcomes_pdf": "; ".join(matches["evaluation_outcome"]),
        "has_conversational_or_chatbot_signal_pdf": yes_no("chatbot_or_conversational_agent" in matches["technology"]),
        "has_voice_or_speech_signal_pdf": yes_no("voice_or_speech_interface" in matches["technology"]),
        "has_red_flag_or_escalation_signal_pdf": yes_no("red_flag_or_escalation" in matches["safety_privacy_handoff"]),
        "has_privacy_or_security_signal_pdf": yes_no("privacy_or_confidentiality" in matches["safety_privacy_handoff"]),
        "has_clinician_handoff_signal_pdf": yes_no("clinician_review_or_handoff" in matches["safety_privacy_handoff"]),
        "matched_technology_terms_pdf": matched_terms["technology"],
        "matched_clinical_terms_pdf": matched_terms["clinical_assessment"],
        "matched_safety_privacy_handoff_terms_pdf": matched_terms["safety_privacy_handoff"],
        "matched_evaluation_terms_pdf": matched_terms["evaluation_outcome"],
        "chart_note": "Machine-assisted chart from locally retrieved DOI PDF; confirm manually before final manuscript claims.",
    }


def chart_manual_link(link: dict[str, str], records: dict[str, dict[str, str]]) -> dict[str, str]:
    record = records[link["pmid"]]
    return {
        "pmid": link["pmid"],
        "doi": link["doi"],
        "year": record.get("year", ""),
        "title": record.get("title", ""),
        "journal": record.get("journal", ""),
        "current_decision": record.get("current_decision", ""),
        "current_reason": record.get("current_reason", ""),
        "full_text_access_type": "manual_link_only",
        "local_pdf_path": "",
        "manual_url": link["url"],
        "country_or_region_inferred": "",
        "study_design_pdf": "not_charted_link_only",
        "oa_joint_or_population_pdf": "not_charted_link_only",
        "technology_category_pdf": "not_charted_link_only",
        "clinical_assessment_content_pdf": "not_charted_link_only",
        "safety_privacy_handoff_pdf": "not_charted_link_only",
        "evaluation_outcomes_pdf": "not_charted_link_only",
        "has_conversational_or_chatbot_signal_pdf": "unknown",
        "has_voice_or_speech_signal_pdf": "unknown",
        "has_red_flag_or_escalation_signal_pdf": "unknown",
        "has_privacy_or_security_signal_pdf": "unknown",
        "has_clinician_handoff_signal_pdf": "unknown",
        "matched_technology_terms_pdf": "",
        "matched_clinical_terms_pdf": "",
        "matched_safety_privacy_handoff_terms_pdf": "",
        "matched_evaluation_terms_pdf": "",
        "chart_note": link["note"],
    }


def summarize(chart_rows: list[dict[str, str]], pdf_rows: list[dict[str, str]], rejected_rows: list[dict[str, str]], args: argparse.Namespace) -> dict[str, Any]:
    pdf_chart_rows = [row for row in chart_rows if row["full_text_access_type"] == "local_pdf"]
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records_input": args.records,
        "pdf_dir": args.pdf_dir,
        "chart_output": args.output,
        "match_index_output": args.match_index,
        "pdf_files_matched": len(pdf_rows),
        "pdf_files_rejected_or_duplicate": len(rejected_rows),
        "chart_record_count": len(chart_rows),
        "local_pdf_chart_count": len(pdf_chart_rows),
        "manual_link_only_count": sum(row["full_text_access_type"] == "manual_link_only" for row in chart_rows),
        "unique_pmids_charted": len({row["pmid"] for row in chart_rows}),
        "access_type_counts": dict(Counter(row["full_text_access_type"] for row in chart_rows)),
        "technology_counts": count_semicolon_field(pdf_chart_rows, "technology_category_pdf"),
        "clinical_assessment_counts": count_semicolon_field(pdf_chart_rows, "clinical_assessment_content_pdf"),
        "safety_privacy_handoff_counts": count_semicolon_field(pdf_chart_rows, "safety_privacy_handoff_pdf"),
        "evaluation_outcome_counts": count_semicolon_field(pdf_chart_rows, "evaluation_outcomes_pdf"),
        "conversational_or_chatbot_signal_count": sum(row["has_conversational_or_chatbot_signal_pdf"] == "yes" for row in pdf_chart_rows),
        "voice_or_speech_signal_count": sum(row["has_voice_or_speech_signal_pdf"] == "yes" for row in pdf_chart_rows),
        "note": "Machine-assisted chart for newly accessible DOI PDFs/link-only record. Human confirmation still required for final manuscript claims.",
    }


def extract_pdf_text(path: Path) -> str:
    try:
        out = subprocess.check_output(["pdftotext", str(path), "-"], stderr=subprocess.DEVNULL, timeout=20)
        return out.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def detect_doi(text: str) -> str:
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text)
    if not match:
        return ""
    return normalize_doi(match.group(0))


def title_score(text: str, title: str) -> float:
    tw = set(re.findall(r"[a-z0-9]+", title.lower()))
    if not tw:
        return 0.0
    xw = set(re.findall(r"[a-z0-9]+", text[:20000].lower()))
    return len(tw & xw) / len(tw)


def count_semicolon_field(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        for item in row.get(field, "").split("; "):
            if item:
                counter[item] += 1
    return dict(counter)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def normalize_doi(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value.strip().rstrip(".,;)")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def chart_fields() -> list[str]:
    return [
        "pmid", "doi", "year", "title", "journal", "current_decision", "current_reason",
        "full_text_access_type", "local_pdf_path", "manual_url", "country_or_region_inferred",
        "study_design_pdf", "oa_joint_or_population_pdf", "technology_category_pdf",
        "clinical_assessment_content_pdf", "safety_privacy_handoff_pdf", "evaluation_outcomes_pdf",
        "has_conversational_or_chatbot_signal_pdf", "has_voice_or_speech_signal_pdf",
        "has_red_flag_or_escalation_signal_pdf", "has_privacy_or_security_signal_pdf",
        "has_clinician_handoff_signal_pdf", "matched_technology_terms_pdf", "matched_clinical_terms_pdf",
        "matched_safety_privacy_handoff_terms_pdf", "matched_evaluation_terms_pdf", "chart_note",
    ]


def match_fields() -> list[str]:
    return [
        "local_pdf_path", "pdf_file", "size_bytes", "doi_detected_in_pdf", "match_status",
        "matched_pmid", "matched_doi_from_table", "matched_title", "match_score", "reject_reason",
    ]


if __name__ == "__main__":
    main()
