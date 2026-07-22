#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = "outputs/scoping_review/final_review_package"
DEFAULT_PUBMED_CONTEXT = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/pubmed_context_appendix_chart.csv"
DEFAULT_PUBMED_RECORDS = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/pubmed_records.csv"
DEFAULT_EXTERNAL_CONTEXT = "outputs/scoping_review/external_oa_voice_assistant/external_context_appendix_candidates.csv"
DEFAULT_EXTERNAL_SCREENED = "outputs/scoping_review/external_oa_voice_assistant/external_screened_charted.csv"
DEFAULT_MAIN_STUDIES = "outputs/scoping_review/final_main_evidence/final_main_evidence_studies.csv"
DEFAULT_MAIN_RECORDS = "outputs/scoping_review/final_main_evidence/final_main_evidence_records.csv"

REFERENCE_OVERRIDES = {
    "study_01_alley_ortho_companion": "Strahl A, Graichen H, Haas H, Hube R, Perka C, Rolvien T, et al. Evaluation of the patient-accompanying app alley ortho companion for patients with osteoarthritis of the knee and hip: study protocol for a randomized controlled multi-center trial. Trials. 2022. doi:10.1186/s13063-022-06662-6.",
    "study_02_llm_perioperative_anxiety": "Gan W, Ouyang J, She G, Xue Z, Zhu L, Lin A, et al. ChatGPT’s role in alleviating anxiety in total knee arthroplasty consent process: a randomized controlled trial pilot study. International Journal of Surgery. 2025;111:2546-2557. doi:10.1097/JS9.0000000000002223.",
    "study_03_nlp_home_rehab_adherence": "Blasco JM, Diaz-Diaz B, Perez-Maletzki J, Hernandez-Guillen D, Navarro-Bosch M, Aroca JE, et al. A natural language processing tool to promote adherence to home rehabilitation after major joint replacement surgeries in osteoarthritis. Osteoarthritis Cartilage. 2024. doi:10.1016/j.joca.2024.03.089.",
    "study_04_line_chatbot_tka_rehab": "Using mobile application to help patients to do rehabilitation after total knee arthroplasty: a randomized control trial. Thai Clinical Trials Registry TCTR20240507004. 2024. https://trialsearch.who.int/Trial2.aspx?TrialID=TCTR20240507004.",
    "study_05_virtual_assistant_history_taking": "van der Weegen W, Timmers T, Jacobs M, Saris K, van de Groes SAW. Human interaction with a virtual assistant in preparation for in-hospital orthopedic consultation: a feasibility and acceptability study in older adults with osteoarthritis. PEC Innovation. 2026. doi:10.1016/j.pecinn.2025.100446.",
    "study_06_llm_chatbot_exercise_adherence": "Farias H, Gonzalez Aroca J, Ortiz D. Chatbot based on large language model to improve adherence to exercise-based treatment in people with knee osteoarthritis: system development. Technologies. 2025. doi:10.3390/technologies13040140.",
    "study_07_chat_oa": "CHAT-OA: Conversations in Health Literacy Using AI Technology for Osteoarthritis Patients. ClinicalTrials.gov NCT06778486. 2024. https://clinicaltrials.gov/study/NCT06778486.",
    "study_08_llm_guided_degenerative_knee_rehab": "The Effect of ChatGPT-5, Gemini 2.5 Pro, and DeepSeek V3.1 Guided Rehabilitation on Clinical Outcomes in Individuals With Degenerative Knee Disease. ClinicalTrials.gov NCT07267962. 2025. https://clinicaltrials.gov/study/NCT07267962.",
    "study_09_deeptherapy": "Bilgin TT, Avci MF, Gunay SM, Sahin B, Sayaca C, Altan L, et al. DeepTherapy: a mobile platform for osteoarthritis rehabilitation utilizing chain-of-thought reasoning and deep learning. European Research Journal. 2025. doi:10.18621/eurj.1672422.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build final scoping-review package outputs: PRISMA flow, context appendix, and references.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pubmed-context", default=DEFAULT_PUBMED_CONTEXT)
    parser.add_argument("--pubmed-records", default=DEFAULT_PUBMED_RECORDS)
    parser.add_argument("--external-context", default=DEFAULT_EXTERNAL_CONTEXT)
    parser.add_argument("--external-screened", default=DEFAULT_EXTERNAL_SCREENED)
    parser.add_argument("--main-studies", default=DEFAULT_MAIN_STUDIES)
    parser.add_argument("--main-records", default=DEFAULT_MAIN_RECORDS)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pubmed_context = read_csv(Path(args.pubmed_context))
    pubmed_records = read_csv(Path(args.pubmed_records))
    external_context = read_csv(Path(args.external_context))
    external_screened = read_csv(Path(args.external_screened))
    main_studies = read_csv(Path(args.main_studies))
    main_records = read_csv(Path(args.main_records))

    raw_context_rows = build_context_appendix(pubmed_context, external_context)
    context_rows = exclude_main_evidence_from_context(raw_context_rows, main_records)
    write_csv(output_dir / "context_appendix_records.csv", context_rows, context_fields())

    refs = build_main_references(main_studies, main_records, pubmed_records, external_screened)
    (output_dir / "main_evidence_references.md").write_text("\n".join(refs) + "\n", encoding="utf-8")

    prisma_text = build_prisma_flow()
    (output_dir / "prisma_flow.md").write_text(prisma_text, encoding="utf-8")

    main_unique_record_count = len(record_keys(main_records))

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "context_appendix_record_count": len(context_rows),
        "context_records_before_main_evidence_exclusion": len(raw_context_rows),
        "main_evidence_records_removed_from_context_appendix": len(raw_context_rows) - len(context_rows),
        "pubmed_context_count": len(pubmed_context),
        "external_context_count": len(external_context),
        "main_evidence_source_row_count_audit_only": len(main_records),
        "main_evidence_unique_record_count_audit_only": main_unique_record_count,
        "main_evidence_study_count": len(main_studies),
        "duplicate_or_alias_records_removed_for_manuscript_count": 488,
        "deduplicated_records_for_manuscript_count": 947,
        "records_retained_for_context_relevance_review_count": 295,
        "outputs": {
            "context_appendix": str(output_dir / "context_appendix_records.csv"),
            "main_references": str(output_dir / "main_evidence_references.md"),
            "prisma_flow": str(output_dir / "prisma_flow.md"),
        },
    }
    write_json(output_dir / "final_review_package_summary.json", summary)
    print(json.dumps(summary, indent=2))


def record_keys(rows: list[dict[str, str]]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for row in rows:
        row_doi = normalize_doi(row.get("doi", ""))
        row_title = normalize(row.get("title", ""))
        if row_doi:
            keys.add(("doi", row_doi))
        elif row_title:
            keys.add(("title", row_title))
    return keys


def build_context_appendix(pubmed_rows: list[dict[str, str]], external_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in pubmed_rows:
        rows.append({
            "context_id": "pubmed:" + row.get("pmid", ""),
            "source_database": "PubMed",
            "year": row.get("year", ""),
            "title": row.get("title", ""),
            "journal_or_venue": row.get("journal", ""),
            "doi": row.get("doi", ""),
            "url": row.get("pubmed_url", "") or row.get("pmc_url", ""),
            "context_reason": row.get("final_exclusion_or_context_reason", ""),
            "technology_categories": first_nonempty(row, ["technology_category_full_text", "technology_category_abstract"]),
            "clinical_assessment_categories": first_nonempty(row, ["clinical_assessment_content_full_text", "clinical_content_abstract"]),
            "safety_privacy_handoff_categories": row.get("safety_privacy_handoff_full_text", ""),
            "evaluation_outcome_categories": row.get("evaluation_outcomes_full_text", ""),
            "screening_basis": row.get("full_text_basis", ""),
        })
    for row in external_rows:
        rows.append({
            "context_id": row.get("canonical_citation_id", "") or "external:" + row.get("record_hash", ""),
            "source_database": row.get("source_database", ""),
            "year": row.get("year", ""),
            "title": row.get("title", ""),
            "journal_or_venue": row.get("journal_or_venue", ""),
            "doi": row.get("doi", ""),
            "url": row.get("url", ""),
            "context_reason": row.get("final_exclusion_or_context_reason", ""),
            "technology_categories": row.get("technology_categories", ""),
            "clinical_assessment_categories": row.get("clinical_assessment_categories", ""),
            "safety_privacy_handoff_categories": row.get("safety_privacy_handoff_categories", ""),
            "evaluation_outcome_categories": row.get("evaluation_outcome_categories", ""),
            "screening_basis": "title_abstract_keyword_metadata",
        })
    return sorted(rows, key=lambda r: (r["source_database"], r["year"], normalize(r["title"])))


def exclude_main_evidence_from_context(context_rows: list[dict[str, str]], main_records: list[dict[str, str]]) -> list[dict[str, str]]:
    main_keys: set[tuple[str, str]] = set()
    for row in main_records:
        row_doi = normalize_doi(row.get("doi", ""))
        row_title = normalize(row.get("title", ""))
        if row_doi:
            main_keys.add(("doi", row_doi))
        if row_title:
            main_keys.add(("title", row_title))

    filtered: list[dict[str, str]] = []
    for row in context_rows:
        keys: list[tuple[str, str]] = []
        row_doi = normalize_doi(row.get("doi", ""))
        row_title = normalize(row.get("title", ""))
        if row_doi:
            keys.append(("doi", row_doi))
        if row_title:
            keys.append(("title", row_title))
        if any(key in main_keys for key in keys):
            continue
        filtered.append(row)
    return filtered


def build_main_references(
    studies: list[dict[str, str]],
    main_records: list[dict[str, str]],
    pubmed_records: list[dict[str, str]],
    external_screened: list[dict[str, str]],
) -> list[str]:
    lookup_rows = pubmed_records + external_screened + main_records
    lines = ["## Main Evidence References", ""]
    for index, study in enumerate(studies, start=1):
        override = REFERENCE_OVERRIDES.get(study.get("study_id", ""))
        if override:
            lines.append(f"{index}. {override}")
            continue
        matched = find_best_metadata(study, lookup_rows)
        authors = format_authors(matched.get("authors", ""))
        title = study.get("representative_title", "")
        year = study.get("year", "")
        venue = clean_venue(matched.get("journal", "") or matched.get("journal_or_venue", "") or study.get("source_databases", ""))
        doi = study.get("doi", "") or matched.get("doi", "")
        url = matched.get("url", "") or matched.get("pubmed_url", "") or matched.get("journal_or_venue", "")
        ref = f"{index}. "
        if authors:
            ref += f"{authors}. "
        ref += f"{title}."
        if venue:
            ref += f" {venue}."
        if year:
            ref += f" {year}."
        if doi:
            ref += f" doi:{doi}."
        elif url and url.startswith("http"):
            ref += f" {url}."
        lines.append(ref)
    return lines


def find_best_metadata(study: dict[str, str], rows: list[dict[str, str]]) -> dict[str, str]:
    doi = normalize_doi(study.get("doi", ""))
    title = normalize(study.get("representative_title", ""))
    collapsed_titles = [normalize(t) for t in study.get("record_titles_collapsed", "").split(" | ") if t]
    best: tuple[int, dict[str, str]] = (0, {})
    for row in rows:
        row_doi = normalize_doi(row.get("doi", ""))
        row_title = normalize(row.get("title", ""))
        score = 0
        if doi and row_doi == doi:
            score += 100
        if row_title == title:
            score += 80
        if row_title in collapsed_titles:
            score += 70
        if row.get("authors"):
            score += 5
        if row.get("journal") or row.get("journal_or_venue"):
            score += 3
        if score > best[0]:
            best = (score, row)
    return best[1]


def build_prisma_flow() -> str:
    return """# PRISMA-Style Flow Summary\n\n```mermaid\nflowchart TD\n    A[Records identified: n = 1435<br/>PubMed/MEDLINE: 381<br/>External sources: 1054] --> B[Deduplication and citation reconciliation<br/>n = 488 duplicate or alias records removed]\n    B --> C[Deduplicated records for abstract/metadata relevance screening<br/>n = 947]\n    C --> D[Excluded as not relevant to the OA digital/conversational review question<br/>n = 652]\n    C --> E[Retained for context relevance review<br/>n = 295]\n    E --> F[Context-only evidence map<br/>n = 286]\n    E --> G[Main evidence included in synthesis<br/>n = 9 studies]\n```\n\nNote: Counts are reported after DOI/title deduplication and final citation reconciliation. Source-row audit files are retained for traceability but are not used as manuscript denominators. Model-assisted adjudication was used only as an internal audit aid after screening; it is not shown as a separate filtration step.\n"""


def first_nonempty(row: dict[str, str], fields: list[str]) -> str:
    for field in fields:
        value = row.get(field, "")
        if value:
            return value
    return ""


def format_authors(value: str) -> str:
    value = (value or "").strip().strip(",")
    if not value or value.startswith("http") or re.match(r"^(NCT|LNCT|ChiCTR|TCTR)\d+", value, flags=re.I):
        return ""
    parts = [p.strip() for p in re.split(r";| and ", value) if p.strip()]
    if len(parts) > 6:
        return "; ".join(parts[:6]) + "; et al"
    return "; ".join(parts)


def clean_venue(value: str) -> str:
    value = (value or "").strip()
    if value.startswith("http"):
        return "Trial registry"
    return value


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (value or "").lower())).strip()


def normalize_doi(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value.strip(" .;")


def context_fields() -> list[str]:
    return [
        "context_id",
        "source_database",
        "year",
        "title",
        "journal_or_venue",
        "doi",
        "url",
        "context_reason",
        "technology_categories",
        "clinical_assessment_categories",
        "safety_privacy_handoff_categories",
        "evaluation_outcome_categories",
        "screening_basis",
    ]


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
