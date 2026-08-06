from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
_MAX_RETRIES = 3
_BACKOFF_BASE = 2


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _parse_date_parts(date_obj: dict | None) -> str:
    if not date_obj:
        return ""
    parts = date_obj.get("date-parts", [[]])[0]
    if not parts:
        return ""
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    for item in payload.get("message", {}).get("items", []):
        doi = item.get("DOI", "")
        raw_title = item.get("title", [])
        raw_abstract = item.get("abstract", "")
        if not doi or not raw_title or not raw_abstract:
            continue

        title = normalize_whitespace(_strip_html(raw_title[0]))
        summary = normalize_whitespace(_strip_html(raw_abstract))
        if not title or not summary:
            continue

        authors = []
        for a in item.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        categories = item.get("subject", [])
        primary_category = categories[0] if categories else ""

        published = _parse_date_parts(item.get("published"))
        updated = _parse_date_parts(item.get("deposited"))

        abs_url = item.get("URL", "")
        links = item.get("link", [])
        pdf_url = links[0].get("URL", "") if links else ""

        records.append(PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment="",
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    resp = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.get(CROSSREF_API_URL, params=params, timeout=60)
        except requests.exceptions.Timeout:
            time.sleep(_BACKOFF_BASE ** (attempt + 1))
            continue
        if resp.status_code in (429, 503):
            time.sleep(_BACKOFF_BASE ** (attempt + 1))
            continue
        resp.raise_for_status()
        break
    else:
        if resp is not None:
            resp.raise_for_status()
        else:
            raise requests.exceptions.ConnectionError("All retry attempts timed out.")

    payload = resp.json()
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    data = read_json(path)
    return [PaperRecord(**item) for item in data]
