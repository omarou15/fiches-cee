from __future__ import annotations

from typing import Any

from mcp_server.utils.loader import FicheNotFoundError, error_response, require_known_code
from scripts.dossier_validators import (
    run_control_matrix as run_control_matrix_core,
    validate_dimensioning_note as validate_dimensioning_note_core,
    validate_dossier_cee as validate_dossier_cee_core,
    validate_dpt as validate_dpt_core,
    validate_invoice as validate_invoice_core,
    validate_quote as validate_quote_core,
)


def _with_code(code: str, data: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    try:
        normalized_code = require_known_code(code)
    except FicheNotFoundError as exc:
        return None, error_response(exc.code)
    payload = dict(data or {})
    payload.setdefault("fiche_code", normalized_code)
    payload.setdefault("operation", {})
    if isinstance(payload["operation"], dict):
        payload["operation"].setdefault("cee_code", normalized_code)
    return normalized_code, payload


def validate_quote(code: str, dossier: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    normalized_code, payload = _with_code(code, dossier)
    if normalized_code is None:
        return payload
    result = validate_quote_core(payload, mode=mode)
    result["code"] = normalized_code
    return result


def validate_invoice(code: str, dossier: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    normalized_code, payload = _with_code(code, dossier)
    if normalized_code is None:
        return payload
    result = validate_invoice_core(payload, mode=mode)
    result["code"] = normalized_code
    return result


def validate_dimensioning_note(code: str, dossier: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    normalized_code, payload = _with_code(code, dossier)
    if normalized_code is None:
        return payload
    result = validate_dimensioning_note_core(payload, mode=mode)
    result["code"] = normalized_code
    return result


def validate_dpt(code: str, dossier: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    normalized_code, payload = _with_code(code, dossier)
    if normalized_code is None:
        return payload
    result = validate_dpt_core(payload, mode=mode)
    result["code"] = normalized_code
    return result


def run_control_matrix(code: str, dossier: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    normalized_code, payload = _with_code(code, dossier)
    if normalized_code is None:
        return payload
    result = run_control_matrix_core(payload, mode=mode)
    result["code"] = normalized_code
    return result


def validate_dossier_cee(code: str, dossier: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    normalized_code, payload = _with_code(code, dossier)
    if normalized_code is None:
        return payload
    result = validate_dossier_cee_core(payload, mode=mode)
    result["code"] = normalized_code
    return result
