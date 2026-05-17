from __future__ import annotations

import re
import unicodedata
from typing import Any

from mcp_server.utils.loader import fiches_index, load_text, merged_fiche_metadata, support_level
from mcp_server.utils.paths import INDEXES_DIR, relative


def _normalize(value: Any) -> str:
    text = str(value or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text


def _terms(query: str) -> list[str]:
    return [term for term in re.split(r"\W+", _normalize(query)) if term]


def _excerpt(text: str, terms: list[str], size: int = 220) -> str:
    normalized = _normalize(text)
    positions = [normalized.find(term) for term in terms if normalized.find(term) >= 0]
    if not positions:
        return text[:size].replace("\n", " ").strip()
    start = max(0, min(positions) - 60)
    end = min(len(text), start + size)
    return text[start:end].replace("\n", " ").strip()


def search_cee(query: str, sector: str | None = None, max_results: int = 10) -> dict[str, Any]:
    """Search CEE fiches by code, title and extracted text."""
    terms = _terms(query)
    requested_sector = str(sector).upper() if sector else None
    results: list[dict[str, Any]] = []
    source_files = {relative(INDEXES_DIR / "fiches_cee_index.json")}

    for item in fiches_index():
        code = str(item.get("code", "")).upper()
        if not code:
            continue
        if requested_sector:
            prefix = code.split("-")[0].upper()
            item_sector = str(item.get("sector", "")).upper()
            if requested_sector not in {prefix, item_sector}:
                continue
        metadata = merged_fiche_metadata(code)
        title = str(metadata.get("title") or item.get("title") or "")
        haystack = _normalize(" ".join([code, title, " ".join(map(str, item.get("keywords", []) or []))]))
        score = 0.0
        if _normalize(query) == _normalize(code):
            score += 100.0
        if _normalize(query) and _normalize(query) in haystack:
            score += 30.0
        score += sum(8.0 for term in terms if term and term in _normalize(code))
        score += sum(5.0 for term in terms if term and term in _normalize(title))

        text, text_path = load_text(code)
        excerpt = title
        if text:
            text_norm = _normalize(text)
            text_hits = sum(1 for term in terms if term in text_norm)
            score += min(text_hits * 3.0, 15.0)
            if text_hits:
                excerpt = _excerpt(text, terms)
                if text_path:
                    source_files.add(relative(text_path))

        if score <= 0:
            continue
        results.append(
            {
                "code": code,
                "title": title,
                "score": round(score, 3),
                "excerpt": excerpt,
                "support_level": support_level(code),
            }
        )

    results.sort(key=lambda item: (-item["score"], item["code"]))
    limit = max(1, int(max_results or 10))
    return {
        "query": query,
        "count": min(len(results), limit),
        "results": results[:limit],
        "source_files": sorted(source_files),
    }

