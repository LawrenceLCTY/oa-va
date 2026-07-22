#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


DEFAULT_MODEL = "/hdd-storage/lawrencelcty/huggingface/models/Qwen/Qwen3-8B"
DEFAULT_OUTPUT_DIR = "outputs/scoping_review/qwen_adjudication"
DEFAULT_PUBMED_CONTEXT = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/pubmed_context_appendix_chart.csv"
DEFAULT_PUBMED_RECORDS = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/pubmed_records.csv"
DEFAULT_EXTERNAL_CONTEXT = "outputs/scoping_review/external_oa_voice_assistant/external_context_appendix_candidates.csv"
DEFAULT_EXTERNAL_STRICT = "outputs/scoping_review/external_oa_voice_assistant/external_strict_main_candidates.csv"
DEFAULT_EXTERNAL_MAIN = "outputs/scoping_review/external_oa_voice_assistant/external_main_evidence_human_adjudicated.csv"
DEFAULT_PMC_DIR = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/pmc_full_text"
DEFAULT_REGISTRY_PATH = "outputs/scoping_review/master_adjudication_registry.csv"
DEFAULT_PDF_DIRS = [
    "outputs/scoping_review/pubmed_oa_voice_assistant_v2/doi_full_text/pdf",
    "outputs/scoping_review/external_oa_voice_assistant/full_text/pdf",
]


DECISIONS = {
    "MAIN_EVIDENCE",
    "CONTEXT_APPENDIX",
    "EXCLUDE",
    "UNCERTAIN_FULL_TEXT_NEEDED",
}


@dataclass
class Record:
    record_id: str
    citation_id: str
    source_set: str
    source_database: str
    title: str
    year: str
    doi: str
    url: str
    journal_or_venue: str
    abstract: str
    keywords: str
    metadata: dict[str, str]
    current_decision: str
    full_text: str = ""
    full_text_source: str = ""
    input_fingerprint: str = ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Use a local Qwen model to adjudicate scoping-review records as main evidence, context appendix, or exclude."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pubmed-context", default=DEFAULT_PUBMED_CONTEXT)
    parser.add_argument("--pubmed-records", default=DEFAULT_PUBMED_RECORDS)
    parser.add_argument("--external-context", default=DEFAULT_EXTERNAL_CONTEXT)
    parser.add_argument("--external-strict", default=DEFAULT_EXTERNAL_STRICT)
    parser.add_argument("--external-main", default=DEFAULT_EXTERNAL_MAIN)
    parser.add_argument("--pmc-dir", default=DEFAULT_PMC_DIR)
    parser.add_argument("--registry-path", default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--pdf-dir", action="append", default=DEFAULT_PDF_DIRS)
    parser.add_argument("--include-existing-main", action="store_true", help="Also re-adjudicate current human main evidence.")
    parser.add_argument("--include-full-text", action="store_true", help="Add PMC XML/PDF text where available.")
    parser.add_argument("--metadata-only", action="store_true", help="Force metadata/abstract-only adjudication.")
    parser.add_argument("--incremental", action="store_true", help="Skip citations already present in the master registry unless their prompt-relevant input fingerprint changed.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--max-input-chars", type=int, default=24000)
    parser.add_argument("--max-full-text-chars", type=int, default=18000)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--device-map", default="auto", help="Use auto with accelerate installed, or none to load normally without accelerate.")
    parser.add_argument("--torch-dtype", default="auto", choices=("auto", "float16", "bfloat16", "float32"))
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Skip records already present in output JSONL.")
    args = parser.parse_args()

    if args.metadata_only:
        args.include_full_text = False

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "qwen_record_adjudication.jsonl"
    csv_path = output_dir / "qwen_record_adjudication.csv"
    summary_path = output_dir / "qwen_record_adjudication_summary.json"
    registry_path = Path(args.registry_path)

    records = load_review_records(args)
    if args.include_full_text:
        add_full_text(records, args)
    for record in records:
        record.input_fingerprint = build_input_fingerprint(record, args.max_full_text_chars)

    selected = records[args.start :]
    if args.limit:
        selected = selected[: args.limit]

    already_done = read_done_ids(jsonl_path) if args.resume else set()
    registry_index = read_registry_index(registry_path) if args.incremental else {}
    skipped_resume = 0
    skipped_incremental = 0
    to_run: list[Record] = []
    for record in selected:
        if record.record_id in already_done:
            skipped_resume += 1
            continue
        prior = registry_index.get(record.citation_id)
        if prior and prior.get("input_fingerprint", "") == record.input_fingerprint:
            skipped_incremental += 1
            continue
        to_run.append(record)

    if not to_run:
        all_rows = read_jsonl(jsonl_path)
        write_csv(csv_path, all_rows, output_fields())
        write_json(summary_path, summarize(all_rows, args, records, skipped_resume, skipped_incremental, 0))
        print("No new or changed citations to adjudicate.")
        print(f"Wrote {csv_path}")
        print(f"Wrote {summary_path}")
        return

    model, tokenizer = load_model(args)

    output_rows: list[dict[str, str]] = []
    with jsonl_path.open("a" if args.resume else "w", encoding="utf-8") as jsonl_file:
        for index, record in enumerate(to_run, start=1):
            prompt = build_prompt(record, args.max_input_chars, args.max_full_text_chars)
            raw = generate(model, tokenizer, prompt, args)
            parsed = parse_model_json(raw)
            row = make_output_row(index, record, parsed, raw)
            jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")
            jsonl_file.flush()
            output_rows.append(row)
            print(f"{index}/{len(to_run)} {record.record_id} {row['qwen_decision']} {record.title[:100]}")

    all_rows = read_jsonl(jsonl_path)
    write_csv(csv_path, all_rows, output_fields())
    if args.incremental:
        write_registry_csv(registry_path, update_registry(registry_index, output_rows))
    write_json(summary_path, summarize(all_rows, args, records, skipped_resume, skipped_incremental, len(output_rows)))
    print(f"Wrote {jsonl_path}")
    print(f"Wrote {csv_path}")
    if args.incremental:
        print(f"Wrote {registry_path}")
    print(f"Wrote {summary_path}")


def load_review_records(args: argparse.Namespace) -> list[Record]:
    pubmed_lookup = {row["pmid"]: row for row in read_csv(Path(args.pubmed_records))}
    records: list[Record] = []
    records.extend(load_pubmed_context(Path(args.pubmed_context), pubmed_lookup))
    if Path(args.external_strict).is_file():
        records.extend(load_external(Path(args.external_strict), "external_strict_candidate"))
    if Path(args.external_context).is_file():
        records.extend(load_external(Path(args.external_context), "external_context"))
    if args.include_existing_main and Path(args.external_main).is_file():
        records.extend(load_external(Path(args.external_main), "external_main_human_adjudicated"))
    return dedupe_records_by_citation(records)


def load_pubmed_context(path: Path, pubmed_lookup: dict[str, dict[str, str]]) -> list[Record]:
    rows: list[Record] = []
    for row in read_csv(path):
        pmid = row.get("pmid", "")
        pubmed = pubmed_lookup.get(pmid, {})
        title = row.get("title", "") or pubmed.get("title", "")
        merged = {**pubmed, **row}
        rows.append(
            Record(
                record_id=f"pubmed:{pmid}",
                citation_id=canonical_citation_id(merged, fallback_prefix="pubmed"),
                source_set="pubmed_context",
                source_database="PubMed",
                title=title,
                year=row.get("year", "") or pubmed.get("year", ""),
                doi=row.get("doi", "") or pubmed.get("doi", ""),
                url=row.get("pubmed_url", "") or pubmed.get("pubmed_url", ""),
                journal_or_venue=row.get("journal", "") or pubmed.get("journal", ""),
                abstract=pubmed.get("abstract", ""),
                keywords=pubmed.get("mesh_terms", ""),
                metadata=merged,
                current_decision="context_appendix",
            )
        )
    return rows


def load_external(path: Path, source_set: str) -> list[Record]:
    rows: list[Record] = []
    for row in read_csv(path):
        citation_id = canonical_citation_id(row, fallback_prefix="external")
        record_id = row.get("record_hash") or row.get("source_record_id") or citation_id
        current = row.get("human_final_decision") or row.get("final_eligibility_decision") or source_set
        rows.append(
            Record(
                record_id=f"{source_set}:{record_id}",
                citation_id=citation_id,
                source_set=source_set,
                source_database=row.get("source_database", "External"),
                title=row.get("title", ""),
                year=row.get("year", ""),
                doi=row.get("doi", ""),
                url=row.get("url", ""),
                journal_or_venue=row.get("journal_or_venue", ""),
                abstract=row.get("abstract", ""),
                keywords=row.get("keywords", ""),
                metadata=row,
                current_decision=current,
            )
        )
    return rows


def add_full_text(records: list[Record], args: argparse.Namespace) -> None:
    pmc_dir = Path(args.pmc_dir)
    pdf_dirs = [Path(p) for p in args.pdf_dir]
    for record in records:
        pmcid = record.metadata.get("pmcid", "")
        if pmcid:
            xml_path = pmc_dir / f"{pmcid}.xml"
            if xml_path.is_file():
                record.full_text = extract_xml_text(xml_path)
                record.full_text_source = str(xml_path)
                continue
        pdf_path = find_pdf(record, pdf_dirs)
        if pdf_path:
            record.full_text = extract_pdf_text(pdf_path)
            record.full_text_source = str(pdf_path)


def find_pdf(record: Record, pdf_dirs: list[Path]) -> Path | None:
    doi_norm = normalize_for_match(record.doi)
    title_words = title_word_set(record.title)
    best: tuple[float, Path] | None = None
    for pdf_dir in pdf_dirs:
        if not pdf_dir.is_dir():
            continue
        for pdf in pdf_dir.glob("*.pdf"):
            name = normalize_for_match(pdf.name)
            score = 0.0
            if record.metadata.get("pmid") and record.metadata["pmid"] in pdf.name:
                score = max(score, 1.0)
            if doi_norm and doi_norm in name:
                score = max(score, 0.95)
            if title_words:
                file_words = title_word_set(pdf.stem)
                score = max(score, len(title_words & file_words) / max(len(title_words), 1))
            if score >= 0.55 and (best is None or score > best[0]):
                best = (score, pdf)
    return best[1] if best else None


def build_prompt(record: Record, max_input_chars: int, max_full_text_chars: int) -> str:
    full_text = truncate_middle(record.full_text, max_full_text_chars) if record.full_text else ""
    payload = {
        "record_id": record.record_id,
        "citation_id": record.citation_id,
        "source_set": record.source_set,
        "source_database": record.source_database,
        "current_pipeline_decision": record.current_decision,
        "title": record.title,
        "year": record.year,
        "journal_or_venue": record.journal_or_venue,
        "doi": record.doi,
        "url": record.url,
        "abstract": record.abstract,
        "keywords_or_mesh": record.keywords,
        "technology_categories": record.metadata.get("technology_categories")
        or record.metadata.get("technology_category_abstract", ""),
        "clinical_categories": record.metadata.get("clinical_assessment_categories")
        or record.metadata.get("clinical_content_abstract", ""),
        "safety_privacy_handoff_categories": record.metadata.get("safety_privacy_handoff_categories")
        or record.metadata.get("safety_privacy_handoff_full_text", ""),
        "notes": record.metadata.get("screening_notes") or record.metadata.get("final_eligibility_notes", ""),
        "full_text_source": record.full_text_source,
        "full_text_excerpt": full_text,
    }
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
    payload_text = truncate_middle(payload_text, max_input_chars)
    return f"""You are adjudicating records for a medical scoping review.

Review topic:
Patient-facing voice assistants, chatbots, conversational agents, virtual assistants, LLM-guided tools, or AI-supported interactive systems for osteoarthritis or degenerative knee disease. The project focus is an OA home pain check-in voice assistant, but adjacent OA patient-facing AI/conversational/LLM systems should be counted as MAIN_EVIDENCE.

Decision labels:
- MAIN_EVIDENCE: OA/degenerative knee disease population or OA-specific patient information context AND patient-facing or patient-oriented chatbot, voice assistant, virtual assistant, conversational agent, LLM-guided tool, AI-generated patient guidance, AI-supported rehabilitation, decision support, education, monitoring, symptom/history capture, or clinical interaction.
- CONTEXT_APPENDIX: OA digital health, telehealth, app, wearable, sensor, electronic PRO, remote monitoring, or rehabilitation technology that is useful background but not patient-facing AI/conversational/LLM/voice/virtual-assistant evidence.
- EXCLUDE: wrong population, not OA/degenerative knee disease, post-arthroplasty only without OA relevance, clinician-only diagnostics/imaging/modeling, review/editorial only, or not digital/patient-facing.
- UNCERTAIN_FULL_TEXT_NEEDED: metadata is insufficient or ambiguous and full text is needed before deciding.

Important:
- Do not rely only on keywords. Use title, abstract, metadata, and full-text excerpt if present.
- Trial registry/protocol records can be MAIN_EVIDENCE if they describe a directly relevant OA chatbot/LLM/virtual-assistant intervention, but mark completed_study=false.
- Answer only valid JSON. No markdown.

Required JSON schema:
{{
  "decision": "MAIN_EVIDENCE | CONTEXT_APPENDIX | EXCLUDE | UNCERTAIN_FULL_TEXT_NEEDED",
  "confidence": 0.0,
  "is_oa_or_degenerative_knee_population": true,
  "is_patient_facing_or_patient_oriented": true,
  "has_ai_llm_chatbot_voice_or_virtual_assistant": true,
  "is_completed_study": true,
  "main_evidence_type": "virtual_assistant | chatbot | voice_assistant | llm_answer_guidance | ai_guided_rehabilitation | ai_patient_education | monitoring_checkin | other | none",
  "reason": "short rationale grounded in the record",
  "key_evidence": ["short evidence phrase 1", "short evidence phrase 2"],
  "needs_human_review": false
}}

Record:
{payload_text}
"""


def load_model(args: argparse.Namespace) -> tuple[Any, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    dtype_map = {
        "auto": "auto",
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=args.trust_remote_code)
    model_kwargs = {
        "torch_dtype": dtype_map[args.torch_dtype],
        "trust_remote_code": args.trust_remote_code,
    }
    if args.device_map.lower() not in {"none", "", "cpu"}:
        model_kwargs["device_map"] = args.device_map
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    if args.device_map.lower() in {"none", ""} and torch.cuda.is_available():
        model = model.to("cuda")
    elif args.device_map.lower() == "cpu":
        model = model.to("cpu")
    model.eval()
    return model, tokenizer


def generate(model: Any, tokenizer: Any, prompt: str, args: argparse.Namespace) -> str:
    import torch

    messages = [
        {"role": "system", "content": "You are a careful medical scoping-review adjudicator. Return only valid JSON."},
        {"role": "user", "content": prompt},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        text = prompt
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    do_sample = args.temperature > 0
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=do_sample,
            temperature=args.temperature if do_sample else None,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = output[0][inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def parse_model_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if match:
        cleaned = match.group(0)
    try:
        parsed = json.loads(cleaned)
    except Exception:
        return {
            "decision": "UNCERTAIN_FULL_TEXT_NEEDED",
            "confidence": 0.0,
            "reason": "Model did not return parseable JSON.",
            "needs_human_review": True,
            "parse_error": True,
        }
    decision = str(parsed.get("decision", "")).strip().upper()
    if decision not in DECISIONS:
        parsed["decision"] = "UNCERTAIN_FULL_TEXT_NEEDED"
        parsed["needs_human_review"] = True
    else:
        parsed["decision"] = decision
    return parsed


def make_output_row(index: int, record: Record, parsed: dict[str, Any], raw: str) -> dict[str, str]:
    return {
        "run_index": str(index),
        "record_id": record.record_id,
        "citation_id": record.citation_id,
        "source_set": record.source_set,
        "source_database": record.source_database,
        "year": record.year,
        "title": record.title,
        "doi": record.doi,
        "journal_or_venue": record.journal_or_venue,
        "current_decision": record.current_decision,
        "input_fingerprint": record.input_fingerprint,
        "full_text_source": record.full_text_source,
        "qwen_decision": str(parsed.get("decision", "")),
        "qwen_confidence": str(parsed.get("confidence", "")),
        "is_oa_or_degenerative_knee_population": str(parsed.get("is_oa_or_degenerative_knee_population", "")),
        "is_patient_facing_or_patient_oriented": str(parsed.get("is_patient_facing_or_patient_oriented", "")),
        "has_ai_llm_chatbot_voice_or_virtual_assistant": str(parsed.get("has_ai_llm_chatbot_voice_or_virtual_assistant", "")),
        "is_completed_study": str(parsed.get("is_completed_study", "")),
        "main_evidence_type": str(parsed.get("main_evidence_type", "")),
        "qwen_reason": str(parsed.get("reason", "")),
        "qwen_key_evidence": "; ".join(str(x) for x in parsed.get("key_evidence", []) if x),
        "needs_human_review": str(parsed.get("needs_human_review", "")),
        "raw_model_output": raw,
    }


def summarize(
    rows: list[dict[str, str]],
    args: argparse.Namespace,
    records: list[Record],
    skipped_resume: int,
    skipped_incremental: int,
    adjudicated_this_run: int,
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": args.model,
        "record_count_loaded": len(records),
        "distinct_citation_count_loaded": len({record.citation_id for record in records}),
        "record_count_adjudicated": len(rows),
        "adjudicated_this_run": adjudicated_this_run,
        "skipped_existing_output_count": skipped_resume,
        "skipped_incremental_registry_count": skipped_incremental,
        "include_full_text": bool(args.include_full_text),
        "metadata_only": bool(args.metadata_only),
        "incremental": bool(args.incremental),
        "decision_counts": count_field(rows, "qwen_decision"),
        "source_set_counts": count_field(rows, "source_set"),
        "main_evidence_type_counts": count_field(rows, "main_evidence_type"),
        "needs_human_review_count": sum(row.get("needs_human_review", "").lower() == "true" for row in rows),
        "note": "Model-assisted adjudication. Use as an audit aid; final inclusion decisions remain human reviewer decisions.",
    }


def extract_xml_text(path: Path) -> str:
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return ""
    return normalize_space(" ".join(root.itertext()))


def extract_pdf_text(path: Path) -> str:
    try:
        out = subprocess.check_output(["pdftotext", str(path), "-"], stderr=subprocess.DEVNULL, timeout=30)
        return normalize_space(out.decode("utf-8", errors="ignore"))
    except Exception:
        return ""


def truncate_middle(text: str, limit: int) -> str:
    text = normalize_space(text)
    if limit <= 0 or len(text) <= limit:
        return text
    head = limit // 2
    tail = limit - head
    return text[:head] + "\n...[TRUNCATED]...\n" + text[-tail:]


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_for_match(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (value or "").lower())).strip()


def normalize_doi(value: str) -> str:
    value = normalize_space(value).lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value.strip(" .;")


def stable_hash(parts: list[str]) -> str:
    material = "||".join(normalize_space(part) for part in parts)
    return hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]


def extract_year(value: str) -> str:
    match = re.search(r"(19|20)\d{2}", value or "")
    return match.group(0) if match else ""


def canonical_citation_id(row: dict[str, str], fallback_prefix: str) -> str:
    existing = normalize_space(row.get("canonical_citation_id", ""))
    if existing:
        return existing
    doi = normalize_doi(row.get("doi", ""))
    if doi:
        return f"doi:{doi}"
    pmid = normalize_space(row.get("pmid", ""))
    if pmid:
        return f"pmid:{pmid}"
    source_record_id = normalize_space(row.get("source_record_id", ""))
    if source_record_id and re.search(r"(scopus|embase|clinicaltrials|pmc|pubmed)", source_record_id, flags=re.I):
        return f"source:{source_record_id}"
    title_key = normalize_title(row.get("title", ""))
    year = extract_year(row.get("year", ""))
    authors = normalize_title((row.get("authors", "") or "").split(";")[0])
    return f"{fallback_prefix}:{stable_hash([title_key, year, authors])}"


def build_input_fingerprint(record: Record, max_full_text_chars: int) -> str:
    truncated_full_text = truncate_middle(record.full_text, max_full_text_chars) if record.full_text else ""
    return stable_hash(
        [
            record.citation_id,
            record.source_set,
            record.current_decision,
            record.title,
            record.year,
            record.doi,
            record.journal_or_venue,
            record.abstract,
            record.keywords,
            record.metadata.get("technology_categories", ""),
            record.metadata.get("clinical_assessment_categories", ""),
            record.metadata.get("safety_privacy_handoff_categories", ""),
            record.metadata.get("screening_notes", ""),
            truncated_full_text,
        ]
    )


def title_word_set(value: str) -> set[str]:
    stop = {"a", "an", "the", "of", "for", "and", "or", "to", "in", "on", "with", "using"}
    return {w for w in re.findall(r"[a-z0-9]+", (value or "").lower()) if len(w) > 2 and w not in stop}


def dedupe_records_by_citation(records: list[Record]) -> list[Record]:
    priority = {
        "external_main_human_adjudicated": 4,
        "external_strict_candidate": 3,
        "external_context": 2,
        "pubmed_context": 1,
    }
    kept: dict[str, Record] = {}
    for record in records:
        existing = kept.get(record.citation_id)
        if existing is None:
            kept[record.citation_id] = record
            continue
        if priority.get(record.source_set, 0) > priority.get(existing.source_set, 0):
            kept[record.citation_id] = merge_record_fields(record, existing)
        else:
            kept[record.citation_id] = merge_record_fields(existing, record)
    return list(kept.values())


def merge_record_fields(primary: Record, secondary: Record) -> Record:
    for field in ("title", "year", "doi", "url", "journal_or_venue", "abstract", "keywords"):
        if not getattr(primary, field) and getattr(secondary, field):
            setattr(primary, field, getattr(secondary, field))
    primary.metadata = {**secondary.metadata, **primary.metadata}
    return primary


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_done_ids(path: Path) -> set[str]:
    return {row.get("record_id", "") for row in read_jsonl(path)}


def read_registry_index(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row.get("citation_id", ""): row for row in read_csv(path) if row.get("citation_id")}


def update_registry(existing: dict[str, dict[str, str]], new_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    registry = dict(existing)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for row in new_rows:
        citation_id = row.get("citation_id", "")
        if not citation_id:
            continue
        prior = registry.get(citation_id, {})
        times_seen = int(prior.get("times_seen", "0") or "0") + 1
        registry[citation_id] = {
            "citation_id": citation_id,
            "record_id": row.get("record_id", ""),
            "source_set": row.get("source_set", ""),
            "source_database": row.get("source_database", ""),
            "title": row.get("title", ""),
            "year": row.get("year", ""),
            "doi": row.get("doi", ""),
            "journal_or_venue": row.get("journal_or_venue", ""),
            "current_decision": row.get("current_decision", ""),
            "qwen_decision": row.get("qwen_decision", ""),
            "main_evidence_type": row.get("main_evidence_type", ""),
            "needs_human_review": row.get("needs_human_review", ""),
            "input_fingerprint": row.get("input_fingerprint", ""),
            "full_text_source": row.get("full_text_source", ""),
            "first_seen_at_utc": prior.get("first_seen_at_utc", created_at),
            "updated_at_utc": created_at,
            "times_seen": str(times_seen),
        }
    return sorted(registry.values(), key=lambda row: row.get("citation_id", ""))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_registry_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(path, rows, registry_fields())


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def count_field(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    return dict(Counter((row.get(field, "") or "") for row in rows))


def output_fields() -> list[str]:
    return [
        "run_index",
        "record_id",
        "citation_id",
        "source_set",
        "source_database",
        "year",
        "title",
        "doi",
        "journal_or_venue",
        "current_decision",
        "input_fingerprint",
        "full_text_source",
        "qwen_decision",
        "qwen_confidence",
        "is_oa_or_degenerative_knee_population",
        "is_patient_facing_or_patient_oriented",
        "has_ai_llm_chatbot_voice_or_virtual_assistant",
        "is_completed_study",
        "main_evidence_type",
        "qwen_reason",
        "qwen_key_evidence",
        "needs_human_review",
        "raw_model_output",
    ]


def registry_fields() -> list[str]:
    return [
        "citation_id",
        "record_id",
        "source_set",
        "source_database",
        "title",
        "year",
        "doi",
        "journal_or_venue",
        "current_decision",
        "qwen_decision",
        "main_evidence_type",
        "needs_human_review",
        "input_fingerprint",
        "full_text_source",
        "first_seen_at_utc",
        "updated_at_utc",
        "times_seen",
    ]


if __name__ == "__main__":
    main()
