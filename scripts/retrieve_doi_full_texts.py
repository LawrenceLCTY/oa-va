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


DEFAULT_INPUT = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/pubmed_no_pmc_full_text_to_retrieve.csv"
DEFAULT_OUTPUT_DIR = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/doi_full_text"
DEFAULT_MANIFEST = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/doi_full_text_manifest.json"
DEFAULT_UPDATED = "outputs/scoping_review/pubmed_oa_voice_assistant_v2/pubmed_no_pmc_full_text_retrieval_status.csv"

USER_AGENT = "oa-va-scoping-review/1.0 (mailto:{email})"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve legally available full text for no-PMC records using DOI/Open Access metadata."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--updated-output", default=DEFAULT_UPDATED)
    parser.add_argument("--email", default=os.environ.get("UNPAYWALL_EMAIL") or os.environ.get("NCBI_EMAIL", ""))
    parser.add_argument("--allow-missing-email", action="store_true")
    parser.add_argument("--save-landing-pages", action="store_true")
    parser.add_argument("--try-doi-direct", action="store_true", help="Also try DOI redirects directly; slower and often paywalled.")
    parser.add_argument("--skip-crossref", action="store_true", help="Skip Crossref metadata calls; useful when network is slow or Unpaywall email is unavailable.")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not args.email and not args.allow_missing_email:
        raise SystemExit("Set UNPAYWALL_EMAIL/NCBI_EMAIL, pass --email, or rerun with --allow-missing-email.")

    rows = read_csv(Path(args.input))
    if args.limit:
        rows = rows[: args.limit]

    output_dir = Path(args.output_dir)
    pdf_dir = output_dir / "pdf"
    html_dir = output_dir / "html"
    meta_dir = output_dir / "metadata"
    for directory in (pdf_dir, html_dir, meta_dir):
        directory.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    updated_rows: list[dict[str, str]] = []
    for row in rows:
        result = retrieve_row(row, args=args, pdf_dir=pdf_dir, html_dir=html_dir, meta_dir=meta_dir)
        manifest.append(result)
        updated_rows.append(
            {
                **row,
                "doi_retrieval_status": result["status"],
                "doi_retrieval_source": result.get("source", ""),
                "doi_retrieval_url": result.get("url", ""),
                "doi_retrieval_local_path": result.get("local_path", ""),
                "doi_retrieval_error": result.get("error", ""),
            }
        )
        time.sleep(0.35)

    write_json(
        Path(args.manifest),
        {
            "created_at_utc": now_utc(),
            "input": args.input,
            "output_dir": args.output_dir,
            "record_count": len(rows),
            "status_counts": count_statuses(manifest),
            "records": manifest,
            "note": "Uses open-access metadata and DOI redirects only; does not bypass paywalls.",
        },
    )
    fields = list(updated_rows[0].keys()) if updated_rows else []
    write_csv(Path(args.updated_output), updated_rows, fields)

    print(f"Processed {len(rows)} records")
    print("Status counts:", count_statuses(manifest))
    print(f"Wrote {args.manifest}")
    print(f"Wrote {args.updated_output}")


def retrieve_row(
    row: dict[str, str],
    *,
    args: argparse.Namespace,
    pdf_dir: Path,
    html_dir: Path,
    meta_dir: Path,
) -> dict[str, Any]:
    pmid = row.get("pmid", "")
    doi = normalize_doi(row.get("doi", ""))
    if not doi:
        doi = find_doi_by_title(row, email=args.email)
        if doi:
            row["doi"] = doi
    if not doi:
        return base_result(row, "no_doi")

    slug = safe_slug(f"{pmid}_{doi}")
    metadata: dict[str, Any] = {}
    candidates: list[dict[str, str]] = []

    if args.email:
        unpaywall = fetch_unpaywall(doi, args.email, timeout=args.timeout)
        if unpaywall:
            metadata["unpaywall"] = unpaywall
            candidates.extend(unpaywall_candidates(unpaywall))

    if not args.skip_crossref:
        crossref = fetch_crossref_work(doi, args.email, timeout=args.timeout)
        if crossref:
            metadata["crossref"] = crossref
            candidates.extend(crossref_candidates(crossref))

    if metadata:
        write_json(meta_dir / f"{slug}.json", metadata)

    if args.try_doi_direct:
        candidates.append({"source": "doi_content_negotiation_pdf", "url": f"https://doi.org/{urllib.parse.quote(doi)}"})
    if args.save_landing_pages:
        candidates.append({"source": "doi_landing_page", "url": f"https://doi.org/{urllib.parse.quote(doi)}", "accept": "text/html"})

    seen_urls: set[str] = set()
    for candidate in candidates:
        url = candidate.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            downloaded = download_candidate(
                url,
                source=candidate.get("source", "unknown"),
                slug=slug,
                pdf_dir=pdf_dir,
                html_dir=html_dir,
                email=args.email,
                accept=candidate.get("accept", ""),
                timeout=args.timeout,
            )
        except Exception as exc:  # noqa: BLE001 - keep audit trail for each DOI
            continue
        if downloaded:
            return {
                **base_result(row, "downloaded"),
                "source": candidate.get("source", ""),
                "url": downloaded["url"],
                "local_path": downloaded["local_path"],
                "content_type": downloaded["content_type"],
            }

    if candidates:
        return {**base_result(row, "oa_link_found_but_not_downloaded"), "candidate_count": len(candidates)}
    return base_result(row, "no_open_full_text_link")


def download_candidate(
    url: str,
    *,
    source: str,
    slug: str,
    pdf_dir: Path,
    html_dir: Path,
    email: str,
    accept: str,
    timeout: float,
) -> dict[str, str] | None:
    headers = {"User-Agent": user_agent(email)}
    headers["Accept"] = accept or "application/pdf,application/octet-stream;q=0.9,text/html;q=0.5,*/*;q=0.1"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        content_type = response.headers.get("Content-Type", "").lower()
        data = response.read()

    if looks_like_pdf(data, content_type):
        out_path = pdf_dir / f"{slug}.pdf"
        out_path.write_bytes(data)
        return {"url": final_url, "local_path": str(out_path), "content_type": content_type}

    if "text/html" in content_type and accept == "text/html":
        out_path = html_dir / f"{slug}.html"
        out_path.write_bytes(data)
        return {"url": final_url, "local_path": str(out_path), "content_type": content_type}

    return None


def fetch_unpaywall(doi: str, email: str, *, timeout: float) -> dict[str, Any] | None:
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={urllib.parse.quote(email)}"
    try:
        return json_request(url, email=email, timeout=timeout)
    except Exception:
        return None


def fetch_crossref_work(doi: str, email: str, *, timeout: float) -> dict[str, Any] | None:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    try:
        data = json_request(url, email=email, timeout=timeout)
        return data.get("message", data)
    except Exception:
        return None


def find_doi_by_title(row: dict[str, str], *, email: str) -> str:
    title = row.get("title", "").strip()
    if not title:
        return ""
    params = {
        "query.title": title,
        "rows": "1",
        "select": "DOI,title,published-print,published-online,container-title",
    }
    url = f"https://api.crossref.org/works?{urllib.parse.urlencode(params)}"
    try:
        data = json_request(url, email=email, timeout=8.0)
    except Exception:
        return ""
    items = data.get("message", {}).get("items", [])
    if not items:
        return ""
    item = items[0]
    found_title = " ".join(item.get("title", []))
    if title_similarity(title, found_title) < 0.75:
        return ""
    return normalize_doi(item.get("DOI", ""))


def unpaywall_candidates(data: dict[str, Any]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    best = data.get("best_oa_location") or {}
    for location in [best] + list(data.get("oa_locations") or []):
        if not location:
            continue
        if location.get("url_for_pdf"):
            candidates.append({"source": "unpaywall_pdf", "url": location["url_for_pdf"]})
        if location.get("url"):
            candidates.append({"source": "unpaywall_url", "url": location["url"]})
    return candidates


def crossref_candidates(data: dict[str, Any]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for link in data.get("link", []) or []:
        url = link.get("URL", "")
        content_type = str(link.get("content-type", "")).lower()
        if url and ("pdf" in content_type or url.lower().endswith(".pdf")):
            candidates.append({"source": "crossref_pdf_link", "url": url})
    return candidates


def json_request(url: str, *, email: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent(email), "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def base_result(row: dict[str, str], status: str) -> dict[str, Any]:
    return {
        "pmid": row.get("pmid", ""),
        "doi": normalize_doi(row.get("doi", "")),
        "title": row.get("title", ""),
        "priority": row.get("priority", ""),
        "current_decision": row.get("current_decision", ""),
        "status": status,
    }


def title_similarity(a: str, b: str) -> float:
    aw = set(re.findall(r"[a-z0-9]+", a.lower()))
    bw = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not aw or not bw:
        return 0.0
    return len(aw & bw) / len(aw | bw)


def looks_like_pdf(data: bytes, content_type: str) -> bool:
    return data.startswith(b"%PDF") or "application/pdf" in content_type


def normalize_doi(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value.strip().rstrip(".")


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)[:180]


def user_agent(email: str) -> str:
    return USER_AGENT.format(email=email or "no-email-provided@example.invalid")


def count_statuses(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


if __name__ == "__main__":
    main()
