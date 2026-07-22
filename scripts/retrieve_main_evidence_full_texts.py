#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_INPUT = "outputs/scoping_review/final_main_evidence/final_main_evidence_studies.csv"
DEFAULT_OUTPUT_DIR = "outputs/scoping_review/main_evidence_full_text"

# Registry URLs that are not recoverable from DOI metadata.
REGISTRY_URLS = {
    "study_02_llm_perioperative_anxiety": [
        "https://trialsearch.who.int/Trial2.aspx?TrialID=ChiCTR2500099927",
    ],
    "study_04_line_chatbot_tka_rehab": [
        "https://trialsearch.who.int/Trial2.aspx?TrialID=TCTR20240507004",
    ],
    "study_07_chat_oa": [
        "https://clinicaltrials.gov/study/NCT06778486",
        "https://clinicaltrials.gov/api/v2/studies/NCT06778486",
    ],
    "study_08_llm_guided_degenerative_knee_rehab": [
        "https://clinicaltrials.gov/study/NCT07267962",
        "https://clinicaltrials.gov/api/v2/studies/NCT07267962",
    ],
}

# Publisher-specific PDF endpoints worth trying before generic DOI redirects.
KNOWN_PDF_URLS = {
    "10.1186/s13063-022-06662-6": [
        "https://trialsjournal.biomedcentral.com/counter/pdf/10.1186/s13063-022-06662-6.pdf",
    ],
    "10.1016/j.pecinn.2025.100446": [
        "https://www.sciencedirect.com/science/article/pii/S2772628225000012/pdfft?isDTMRedir=true&download=true",
    ],
    "10.3390/technologies13040140": [
        "https://www.mdpi.com/2227-7080/13/4/140/pdf",
        "https://www.mdpi.com/2227-7080/13/4/140/pdf?download=1",
    ],
    "10.18621/eurj.1672422": [
        "https://dergipark.org.tr/en/download/article-file/4707064",
    ],
}

USER_AGENT = "oa-va-main-evidence-retriever/1.0"


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve available full text or registry pages for the 9 main scoping-review studies.")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--email", default=os.environ.get("UNPAYWALL_EMAIL") or os.environ.get("NCBI_EMAIL", ""))
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--sleep", type=float, default=0.4)
    parser.add_argument("--try-doi-direct", action="store_true", help="Try DOI redirects after OA metadata and known PDF URLs.")
    parser.add_argument("--skip-unpaywall", action="store_true")
    parser.add_argument("--skip-crossref", action="store_true")
    args = parser.parse_args()

    out = Path(args.output_dir)
    pdf_dir = out / "pdf"
    html_dir = out / "html"
    json_dir = out / "json"
    meta_dir = out / "metadata"
    for d in (pdf_dir, html_dir, json_dir, meta_dir):
        d.mkdir(parents=True, exist_ok=True)

    studies = read_csv(Path(args.input))
    manifest = []
    for study in studies:
        result = retrieve_study(study, args=args, pdf_dir=pdf_dir, html_dir=html_dir, json_dir=json_dir, meta_dir=meta_dir)
        manifest.append(result)
        print(f"{result['study_id']}: {result['status']} -> {result.get('local_path') or result.get('url') or result.get('note', '')}")
        time.sleep(args.sleep)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input": args.input,
        "output_dir": args.output_dir,
        "study_count": len(studies),
        "status_counts": count_statuses(manifest),
        "records": manifest,
        "note": "Downloads only open/legal full text or public registry pages. Paywalled articles remain marked for manual retrieval.",
    }
    write_json(out / "main_evidence_full_text_manifest.json", summary)
    write_csv(out / "main_evidence_full_text_status.csv", flatten_records(manifest), status_fields())
    print("Status counts:", summary["status_counts"])
    print("Wrote", out / "main_evidence_full_text_manifest.json")
    print("Wrote", out / "main_evidence_full_text_status.csv")


def retrieve_study(study: dict[str, str], *, args: argparse.Namespace, pdf_dir: Path, html_dir: Path, json_dir: Path, meta_dir: Path) -> dict[str, Any]:
    study_id = study.get("study_id", "")
    title = study.get("representative_title", "")
    doi = normalize_doi(study.get("doi", ""))
    slug = safe_slug(f"{study_id}_{doi or title}")

    attempts: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}

    # Public registry records are legitimate full source records even when no article PDF exists.
    for url in REGISTRY_URLS.get(study_id, []):
        downloaded = try_download(url, slug=slug, pdf_dir=pdf_dir, html_dir=html_dir, json_dir=json_dir, timeout=args.timeout)
        attempts.append({"source": "registry", "url": url, **downloaded})
        if downloaded.get("downloaded"):
            return base(study, "registry_record_downloaded", downloaded, attempts)

    candidates: list[dict[str, str]] = []
    if doi:
        for url in KNOWN_PDF_URLS.get(doi, []):
            candidates.append({"source": "known_pdf_endpoint", "url": url})

        if not args.skip_unpaywall and args.email:
            data = fetch_json(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={urllib.parse.quote(args.email)}", timeout=args.timeout)
            if data:
                metadata["unpaywall"] = data
                candidates.extend(unpaywall_candidates(data))

        if not args.skip_crossref:
            data = fetch_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}", timeout=args.timeout)
            if data:
                metadata["crossref"] = data.get("message", data)
                candidates.extend(crossref_candidates(data.get("message", data)))

        if args.try_doi_direct:
            candidates.append({"source": "doi_direct", "url": f"https://doi.org/{urllib.parse.quote(doi)}"})

    if metadata:
        write_json(meta_dir / f"{slug}.json", metadata)

    seen = set()
    for c in candidates:
        url = c.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        downloaded = try_download(url, slug=slug, pdf_dir=pdf_dir, html_dir=html_dir, json_dir=json_dir, timeout=args.timeout)
        attempts.append({"source": c.get("source", "unknown"), "url": url, **downloaded})
        if downloaded.get("downloaded") and downloaded.get("kind") == "pdf":
            return base(study, "pdf_downloaded", downloaded, attempts)
        if downloaded.get("downloaded") and downloaded.get("kind") in {"html", "json"}:
            return base(study, "landing_or_metadata_downloaded", downloaded, attempts)

    if doi:
        return base(study, "manual_retrieval_needed", {"note": "No open PDF was downloaded automatically."}, attempts)
    return base(study, "registry_or_manual_retrieval_needed", {"note": "No DOI; use registry/database URL or manual export."}, attempts)


def try_download(url: str, *, slug: str, pdf_dir: Path, html_dir: Path, json_dir: Path, timeout: float) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,text/html,application/json,*/*;q=0.5"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final_url = resp.geturl()
            ctype = resp.headers.get("Content-Type", "").lower()
            data = resp.read()
    except urllib.error.HTTPError as e:
        return {"downloaded": False, "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:  # noqa: BLE001 - keep manifest complete
        return {"downloaded": False, "error": str(e)}

    if looks_like_pdf(data, ctype):
        path = pdf_dir / f"{slug}.pdf"
        path.write_bytes(data)
        return {"downloaded": True, "kind": "pdf", "url": final_url, "local_path": str(path), "content_type": ctype, "bytes": len(data)}
    if "json" in ctype or data[:1] in {b"{", b"["}:
        path = json_dir / f"{slug}.json"
        path.write_bytes(data)
        return {"downloaded": True, "kind": "json", "url": final_url, "local_path": str(path), "content_type": ctype, "bytes": len(data)}
    if "html" in ctype or b"<html" in data[:300].lower() or b"<!doctype html" in data[:300].lower():
        path = html_dir / f"{slug}.html"
        path.write_bytes(data)
        return {"downloaded": True, "kind": "html", "url": final_url, "local_path": str(path), "content_type": ctype, "bytes": len(data)}
    return {"downloaded": False, "url": final_url, "content_type": ctype, "bytes": len(data), "error": "unsupported content type"}


def unpaywall_candidates(data: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    best = data.get("best_oa_location") or {}
    for key in ("url_for_pdf", "url_for_landing_page"):
        if best.get(key):
            out.append({"source": f"unpaywall_best_{key}", "url": best[key]})
    for loc in data.get("oa_locations") or []:
        for key in ("url_for_pdf", "url_for_landing_page"):
            if loc.get(key):
                out.append({"source": f"unpaywall_{key}", "url": loc[key]})
    return out


def crossref_candidates(data: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for link in data.get("link") or []:
        url = link.get("URL")
        if url:
            out.append({"source": "crossref_link", "url": url})
    for url in data.get("URL", "").split():
        out.append({"source": "crossref_url", "url": url})
    return out


def base(study: dict[str, str], status: str, downloaded: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "study_id": study.get("study_id", ""),
        "study_label": study.get("study_label", ""),
        "title": study.get("representative_title", ""),
        "doi": normalize_doi(study.get("doi", "")),
        "status": status,
        "local_path": downloaded.get("local_path", ""),
        "url": downloaded.get("url", ""),
        "kind": downloaded.get("kind", ""),
        "note": downloaded.get("note", ""),
        "attempts": attempts,
    }


def fetch_json(url: str, *, timeout: float) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def looks_like_pdf(data: bytes, content_type: str) -> bool:
    return data.startswith(b"%PDF") or "application/pdf" in content_type


def normalize_doi(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value.strip(" .;")


def safe_slug(value: str, max_len: int = 120) -> str:
    value = normalize_doi(value) or "record"
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return value[:max_len] or "record"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def flatten_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for r in records:
        rows.append({
            "study_id": r.get("study_id", ""),
            "study_label": r.get("study_label", ""),
            "title": r.get("title", ""),
            "doi": r.get("doi", ""),
            "status": r.get("status", ""),
            "kind": r.get("kind", ""),
            "local_path": r.get("local_path", ""),
            "url": r.get("url", ""),
            "note": r.get("note", ""),
            "attempt_count": len(r.get("attempts") or []),
        })
    return rows


def status_fields() -> list[str]:
    return ["study_id", "study_label", "title", "doi", "status", "kind", "local_path", "url", "note", "attempt_count"]


def count_statuses(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


if __name__ == "__main__":
    main()
