from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from mcp_server.utils.loader import FicheNotFoundError, error_response, require_known_code
from mcp_server.utils.paths import REPO_ROOT, relative


COMPETENCE_ROOT = REPO_ROOT / "competence_engine"
INDEX_PATH = COMPETENCE_ROOT / "index.json"


class CompetenceNotFoundError(ValueError):
    def __init__(self, competence_id: str) -> None:
        super().__init__(f"CEE competence not found: {competence_id}")
        self.competence_id = competence_id


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def competence_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        return {"competences": []}
    data = _read_json(INDEX_PATH)
    if not isinstance(data.get("competences"), list):
        return {"competences": []}
    return data


def _entry_path(entry: dict[str, Any]) -> Path:
    return REPO_ROOT / str(entry.get("path", ""))


def _load_competence(entry: dict[str, Any]) -> dict[str, Any]:
    path = _entry_path(entry)
    data = _read_json(path)
    return data


def _entry_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry.get("id"),
        "title": entry.get("title"),
        "category": entry.get("category"),
        "status": entry.get("status"),
        "applies_to": entry.get("applies_to") or [],
        "path": entry.get("path"),
        "notes": entry.get("notes"),
    }


def _all_entries() -> list[dict[str, Any]]:
    return [entry for entry in competence_index().get("competences", []) if isinstance(entry, dict)]


def _all_ids() -> list[str]:
    return sorted(str(entry.get("id")) for entry in _all_entries() if entry.get("id"))


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _applies_pattern_matches(pattern: str, code: str) -> bool:
    normalized_pattern = _normalize(pattern)
    normalized_code = _normalize(code)
    if normalized_pattern in {"*", "all"}:
        return True
    if normalized_pattern == normalized_code:
        return True
    if normalized_pattern.endswith("*"):
        return normalized_code.startswith(normalized_pattern[:-1])
    if normalized_pattern.endswith("_related_fiches") and normalized_pattern.split("_", 1)[0] in normalized_code:
        return True
    if normalized_pattern in {"dpt", "quote_review", "audit_scenarios"}:
        return False
    return False


def _entry_matches_code(entry: dict[str, Any], code: str) -> bool:
    return any(_applies_pattern_matches(str(pattern), code) for pattern in entry.get("applies_to") or [])


def _entry_matches_text(entry: dict[str, Any], text: str) -> bool:
    if not text:
        return True
    haystack = " ".join(
        str(value or "")
        for value in [
            entry.get("id"),
            entry.get("title"),
            entry.get("category"),
            entry.get("notes"),
            " ".join(entry.get("applies_to") or []),
        ]
    ).lower()
    return all(term in haystack for term in text.lower().split())


def list_competences(
    category: str | None = None,
    status: str | None = None,
    applies_to: str | None = None,
) -> dict[str, Any]:
    """List reusable CEE agent competences."""
    entries = _all_entries()
    if category:
        entries = [entry for entry in entries if entry.get("category") == category]
    if status:
        entries = [entry for entry in entries if entry.get("status") == status]
    if applies_to:
        try:
            code = require_known_code(applies_to)
        except FicheNotFoundError:
            code = applies_to
        entries = [entry for entry in entries if _entry_matches_code(entry, code)]

    return {
        "count": len(entries),
        "competences": [_entry_summary(entry) for entry in entries],
        "source_files": [relative(INDEX_PATH)] if INDEX_PATH.exists() else [],
    }


def get_competence(competence_id: str) -> dict[str, Any]:
    """Return a full CEE agent competence by id."""
    normalized = _normalize(competence_id)
    for entry in _all_entries():
        if _normalize(entry.get("id")) != normalized:
            continue
        path = _entry_path(entry)
        if not path.exists():
            raise CompetenceNotFoundError(competence_id)
        return {
            "id": entry.get("id"),
            "competence": _load_competence(entry),
            "source_files": [relative(path), relative(INDEX_PATH)],
        }
    return {
        "error": {
            "code": "competence_not_found",
            "message": f"CEE competence not found: {competence_id}",
            "requested_id": competence_id,
            "available_ids": _all_ids(),
        },
        "source_files": [relative(INDEX_PATH)] if INDEX_PATH.exists() else [],
    }


def find_competences(
    code: str | None = None,
    task: str | None = None,
) -> dict[str, Any]:
    """Find competences relevant to a fiche code and/or a task label."""
    entries = _all_entries()
    normalized_code: str | None = None
    if code:
        try:
            normalized_code = require_known_code(code)
        except FicheNotFoundError as exc:
            return error_response(exc.code)
        entries = [entry for entry in entries if _entry_matches_code(entry, normalized_code)]
    if task:
        entries = [entry for entry in entries if _entry_matches_text(entry, task)]
    return {
        "code": normalized_code,
        "task": task,
        "count": len(entries),
        "competences": [_entry_summary(entry) for entry in entries],
        "source_files": [relative(INDEX_PATH)] if INDEX_PATH.exists() else [],
    }
