#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = "inputs/scoping_review/scopus_api_export.csv"
DEFAULT_SUMMARY = "outputs/scoping_review/external_oa_voice_assistant/scopus_api_fetch_summary.json"
DEFAULT_QUERY = (
    'TITLE-ABS-KEY(osteoarthritis OR osteoarthrosis OR "degenerative joint disease" OR "degenerative arthritis") '
    'AND TITLE-ABS-KEY(chatbot OR "conversational agent" OR "voice assistant" OR "virtual assistant" '
    'OR "speech interface" OR "spoken dialogue system" OR "remote monitoring" OR telemonitoring '
    'OR mhealth OR "mobile health" OR "mobile app" OR smartphone) '
    'AND TITLE-ABS-KEY(pain OR symptom OR symptoms OR function OR functional OR "self-management" '
    'OR "patient-reported outcome" OR "home monitoring" OR monitoring)'
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Scopus metadata for the OA conversational/digital health scoping review.")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--max-records", type=int, default=1000)
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    api_key = load_api_key(Path(args.env))
    rows, fetch_log = fetch_all(args.query, api_key, args.max_records, args.page_size, args.sleep)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, rows, fields())

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "query": args.query,
        "output": str(output),
        "record_count": len(rows),
        "max_records": args.max_records,
        "page_size": args.page_size,
        "fetch_log": fetch_log,
        "note": "Fetched metadata only through the Scopus Search API. API key was read from .env and not stored in outputs.",
    }
    write_json(Path(args.summary), summary)
    print(f"Fetched Scopus API records: {len(rows)}")
    print(f"Wrote {output}")
    print(f"Wrote {args.summary}")


def load_api_key(env_path: Path) -> str:
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "SCOPUS_API_KEY" and value.strip():
                return value.strip().strip('"').strip("'")
    value = os.environ.get("SCOPUS_API_KEY", "").strip()
    if value:
        return value
    raise SystemExit("SCOPUS_API_KEY not found in .env or environment")


def fetch_all(query: str, api_key: str, max_records: int, page_size: int, sleep_s: float) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    rows: list[dict[str, str]] = []
    log: list[dict[str, Any]] = []
    start = 0
    total: int | None = None
    while len(rows) < max_records:
        page_count = min(page_size, max_records - len(rows))
        data = fetch_page(query, api_key, start, page_count)
        search_results = data.get("search-results", {})
        if total is None:
            total = int(search_results.get("opensearch:totalResults", "0") or 0)
        entries = search_results.get("entry", [])
        if not entries:
            break
        for entry in entries:
            if "error" in entry:
                continue
            rows.append(entry_to_row(entry))
        log.append({"start": start, "requested": page_count, "received": len(entries), "total": total})
        start += len(entries)
        if start >= total:
            break
        time.sleep(sleep_s)
    return rows, log


def fetch_page(query: str, api_key: str, start: int, count: int) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "query": query,
        "start": str(start),
        "count": str(count),
        "view": "COMPLETE",
        "httpAccept": "application/json",
        "apiKey": api_key,
    })
    url = f"https://api.elsevier.com/content/search/scopus?{params}"
    request = urllib.request.Request(
        url,
        headers={
            "X-ELS-APIKey": api_key,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def entry_to_row(entry: dict[str, Any]) -> dict[str, str]:
    title = value(entry, "dc:title")
    doi = normalize_doi(value(entry, "prism:doi"))
    authors = entry.get("author", [])
    author_names = "; ".join(a.get("authname", "") for a in authors if isinstance(a, dict) and a.get("authname"))
    return {
        "source_database": "Scopus API",
        "source_file": "scopus_api",
        "source_record_id": value(entry, "dc:identifier").replace("SCOPUS_ID:", ""),
        "record_type": value(entry, "subtypeDescription") or value(entry, "subtype"),
        "title": title,
        "authors": author_names,
        "year": extract_year(value(entry, "prism:coverDate") or value(entry, "prism:coverDisplayDate")),
        "journal_or_venue": value(entry, "prism:publicationName"),
        "doi": doi,
        "url": first_link(entry.get("link", [])),
        "abstract": value(entry, "dc:description"),
        "keywords": value(entry, "authkeywords"),
        "publication_types": value(entry, "subtypeDescription") or value(entry, "subtype"),
    }


def value(entry: dict[str, Any], key: str) -> str:
    raw = entry.get(key, "")
    if isinstance(raw, str):
        return re.sub(r"\s+", " ", raw).strip()
    return ""


def first_link(links: Any) -> str:
    if not isinstance(links, list):
        return ""
    for link in links:
        if isinstance(link, dict) and link.get("@href"):
            return link["@href"]
    return ""


def normalize_doi(value_: str) -> str:
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", value_ or "")
    if not match:
        return ""
    return match.group(0).rstrip(".,;").lower()


def extract_year(value_: str) -> str:
    match = re.search(r"(19|20)\d{2}", value_ or "")
    return match.group(0) if match else ""


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def fields() -> list[str]:
    return [
        "source_database",
        "source_file",
        "source_record_id",
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
    ]


if __name__ == "__main__":
    main()
