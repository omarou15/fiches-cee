from __future__ import annotations

from typing import Any

from mcp_server.utils.loader import (
    FicheNotFoundError,
    all_codes,
    code_paths,
    error_response,
    existing_source_files,
    fiches_index,
    load_fiche,
    merged_fiche_metadata,
    needs_human_review,
    require_known_code,
    support_level,
)
from mcp_server.utils.paths import INDEXES_DIR, relative


SECTOR_ALIASES = {
    "BAR": {"BAR", "RESIDENTIEL", "RESIDENTIAL", "residentiel"},
    "BAT": {"BAT", "TERTIAIRE", "TERTIARY", "tertiaire"},
    "IND": {"IND", "INDUSTRIE", "INDUSTRY", "industrie"},
    "AGRI": {"AGRI", "AGRICULTURE", "agriculture"},
    "RES": {"RES", "RESEAUX", "RESEAUX_RES", "reseaux"},
    "TRA": {"TRA", "TRANSPORT", "transport"},
}


def _sector_matches(item: dict[str, Any], sector: str | None) -> bool:
    if not sector:
        return True
    requested = str(sector).strip().upper()
    code_prefix = str(item.get("code", "")).split("-")[0].upper()
    item_sector = str(item.get("sector", "")).strip()
    if requested == code_prefix or requested == item_sector.upper():
        return True
    aliases = SECTOR_ALIASES.get(requested, {requested})
    return code_prefix in aliases or item_sector in aliases or item_sector.upper() in aliases


def list_cee_fiches(
    sector: str | None = None,
    support_level_filter: str | None = None,
    family: str | None = None,
    support_level: str | None = None,
) -> dict[str, Any]:
    """List available CEE fiches with optional filters."""
    requested_support = support_level_filter or support_level
    fiches: list[dict[str, Any]] = []
    for item in fiches_index():
        code = str(item.get("code", "")).upper()
        if not code:
            continue
        level = merged_fiche_metadata(code)["support_level"]
        if requested_support and level != requested_support:
            continue
        if family and str(item.get("family", "")).upper() != str(family).upper():
            continue
        if not _sector_matches(item, sector):
            continue
        metadata = merged_fiche_metadata(code)
        fiches.append(
            {
                "code": metadata["code"],
                "title": metadata["title"],
                "sector": metadata["sector"],
                "family": metadata["family"],
                "support_level": level,
                "version": metadata["version"],
                "effective_date": metadata["effective_date"],
            }
        )
    return {
        "count": len(fiches),
        "fiches": fiches,
        "source_files": [relative(INDEXES_DIR / "fiches_cee_index.json")],
    }


def get_cee_fiche(code: str, level: str = "curated") -> dict[str, Any]:
    """Return a CEE fiche as curated JSON, extracted JSON, or raw text."""
    try:
        normalized = require_known_code(code)
        content, actual_level, path = load_fiche(normalized, level)
    except FicheNotFoundError as exc:
        return error_response(exc.code)

    paths = code_paths(normalized)
    metadata = merged_fiche_metadata(normalized)
    response: dict[str, Any] = {
        "code": normalized,
        "requested_level": level,
        "level": actual_level,
        "support_level": support_level(normalized),
        "metadata": metadata,
        "needs_human_review": needs_human_review(content),
        "source_files": existing_source_files(path),
    }
    if actual_level == "text":
        response["text"] = content
    else:
        response["fiche"] = content
    if actual_level == "curated" and paths["json"].exists():
        response["fallback_json_available"] = True
    response["available_codes_count"] = len(all_codes())
    return response

