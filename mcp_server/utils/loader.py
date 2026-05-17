from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .paths import CURATED_DIR, INDEXES_DIR, JSON_DIR, RULES_DIR, TEXT_DIR, relative


class FicheNotFoundError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Fiche CEE not found: {code}")
        self.code = code


def normalize_code(code: str) -> str:
    return str(code or "").strip().upper()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def fiches_index() -> list[dict[str, Any]]:
    path = INDEXES_DIR / "fiches_cee_index.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


@lru_cache(maxsize=1)
def index_by_code() -> dict[str, dict[str, Any]]:
    return {normalize_code(item.get("code")): item for item in fiches_index() if item.get("code")}


def all_codes() -> list[str]:
    codes = set(index_by_code())
    codes.update(path.stem.upper() for path in JSON_DIR.glob("*.json"))
    codes.update(path.stem.upper() for path in CURATED_DIR.glob("*.json"))
    return sorted(code for code in codes if code)


def require_known_code(code: str) -> str:
    normalized = normalize_code(code)
    if not normalized or normalized not in set(all_codes()):
        raise FicheNotFoundError(normalized or code)
    return normalized


def code_paths(code: str) -> dict[str, Path]:
    normalized = normalize_code(code)
    return {
        "rules": RULES_DIR / f"{normalized}.rules.json",
        "curated": CURATED_DIR / f"{normalized}.json",
        "json": JSON_DIR / f"{normalized}.json",
        "text": TEXT_DIR / f"{normalized}.txt",
    }


def support_level(code: str) -> str:
    paths = code_paths(code)
    if paths["rules"].exists() and paths["curated"].exists():
        return "supported_full"
    if paths["curated"].exists() or paths["json"].exists():
        return "supported_partial"
    return "supported_generic"


def existing_source_files(*paths: Path | None) -> list[str]:
    return [relative(path) for path in paths if path and path.exists()]


def load_rules(code: str) -> tuple[dict[str, Any] | None, Path | None]:
    path = code_paths(code)["rules"]
    if not path.exists():
        return None, None
    return read_json(path), path


def load_curated(code: str) -> tuple[dict[str, Any] | None, Path | None]:
    path = code_paths(code)["curated"]
    if not path.exists():
        return None, None
    return read_json(path), path


def load_extracted_json(code: str) -> tuple[dict[str, Any] | None, Path | None]:
    path = code_paths(code)["json"]
    if not path.exists():
        return None, None
    return read_json(path), path


def load_text(code: str) -> tuple[str | None, Path | None]:
    path = code_paths(code)["text"]
    if not path.exists():
        return None, None
    return path.read_text(encoding="utf-8", errors="replace"), path


def load_fiche(code: str, level: str = "curated") -> tuple[Any, str, Path | None]:
    normalized = require_known_code(code)
    requested = str(level or "curated").lower()
    if requested == "text":
        text, path = load_text(normalized)
        if text is None:
            raise FicheNotFoundError(normalized)
        return text, "text", path
    if requested == "json":
        data, path = load_extracted_json(normalized)
        if data is None:
            raise FicheNotFoundError(normalized)
        return data, "json", path
    if requested != "curated":
        requested = "curated"
    curated, curated_path = load_curated(normalized)
    if curated is not None:
        return curated, "curated", curated_path
    data, path = load_extracted_json(normalized)
    if data is None:
        raise FicheNotFoundError(normalized)
    return data, "json", path


def merged_fiche_metadata(code: str) -> dict[str, Any]:
    normalized = normalize_code(code)
    entry = index_by_code().get(normalized, {})
    curated, _ = load_curated(normalized)
    extracted, _ = load_extracted_json(normalized)
    source = extracted or curated or entry
    return {
        "code": normalized,
        "title": source.get("title") or source.get("title_clean") or entry.get("title"),
        "sector": source.get("sector") or entry.get("sector"),
        "family": source.get("family") or entry.get("family"),
        "version": source.get("version") or entry.get("version"),
        "effective_date": source.get("effective_date") or entry.get("effective_date"),
        "support_level": support_level(normalized),
    }


def needs_human_review(fiche: Any) -> bool:
    if not isinstance(fiche, dict):
        return False
    extraction = fiche.get("extraction")
    if isinstance(extraction, dict):
        return bool(extraction.get("needs_human_review"))
    return False


def error_response(code: str, message: str | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": "fiche_not_found",
            "message": message or f"Fiche CEE not found: {code}",
            "requested_code": normalize_code(code),
            "available_codes": all_codes(),
        },
        "source_files": [],
    }

