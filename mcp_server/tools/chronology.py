from __future__ import annotations

from typing import Any

from scripts.validate_operation import validate_chronology


def check_chronology(code: str, dates: dict[str, Any]) -> dict[str, Any]:
    """Validate the documentary chronology of a CEE operation."""
    operation = dict(dates or {})
    operation["fiche_code"] = code
    result = validate_chronology(operation)
    return {
        "code": code,
        "valid": result["valid"],
        "blocking_points": result["blocking_points"],
        "warnings": result["warnings"],
        "source": result["source"],
    }

