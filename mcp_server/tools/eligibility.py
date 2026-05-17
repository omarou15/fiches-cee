from __future__ import annotations

from copy import deepcopy
from typing import Any

from mcp_server.utils.loader import (
    FicheNotFoundError,
    error_response,
    existing_source_files,
    load_curated,
    load_extracted_json,
    load_rules,
    needs_human_review,
    require_known_code,
    support_level,
)


def _set_nested(target: dict[str, Any], section: str, key: str, value: Any) -> None:
    if value in (None, "", "unknown"):
        return
    target.setdefault(section, {})
    if isinstance(target[section], dict) and key not in target[section]:
        target[section][key] = value


def _first_value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, "", "unknown"):
            return data[key]
    return None


def normalize_operation_for_agent(code: str, operation: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(operation)
    normalized["fiche_code"] = code
    normalized.setdefault("operation_id", operation.get("operation_id") or operation.get("case_id") or f"mcp-{code.lower()}")

    _set_nested(normalized, "site", "climate_zone", _first_value(operation, "zone", "climate_zone", "zone_climatique"))
    _set_nested(
        normalized,
        "site",
        "apartment_count_heated_by_pac",
        _first_value(operation, "apartment_count", "apartments", "apartment_count_heated_by_pac", "N"),
    )
    _set_nested(normalized, "site", "residential_collective", _first_value(operation, "residential_collective"))
    _set_nested(normalized, "site", "existing_building", _first_value(operation, "existing_building"))
    _set_nested(normalized, "operation", "usage", _first_value(operation, "usage", "pac_usage"))
    _set_nested(normalized, "operation", "etas_percent", _first_value(operation, "etas", "etas_percent"))
    _set_nested(normalized, "operation", "pac_type", _first_value(operation, "pac_type"))
    _set_nested(normalized, "operation", "application_temperature", _first_value(operation, "application_temperature"))
    _set_nested(
        normalized,
        "operation",
        "pac_nominal_power_kw",
        _first_value(operation, "pac_nominal_power_kw", "pac_power_kw", "pac_power"),
    )
    _set_nested(
        normalized,
        "operation",
        "chaufferie_useful_power_after_works_kw",
        _first_value(
            operation,
            "chaufferie_useful_power_after_works_kw",
            "boiler_room_useful_power_after_works_kw",
            "boiler_room_power_after_works_kw",
        ),
    )
    _set_nested(normalized, "operation", "backup_equipment_excluded", _first_value(operation, "backup_equipment_excluded"))
    _set_nested(normalized, "operation", "engagement_date", _first_value(operation, "engagement_date"))
    _set_nested(normalized, "operation", "heating_system_collective", _first_value(operation, "heating_system_collective"))
    return normalized


def _text_from_question(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "field": item.get("field_path"),
        "text": item.get("question"),
        "blocking": bool(item.get("blocking", True)),
    }


def _minimum_etas_threshold(code: str) -> tuple[float | None, str | None]:
    curated, curated_path = load_curated(code)
    if not isinstance(curated, dict):
        return None, None
    thresholds = (
        curated.get("technical_requirements_structured", {}).get("etas_thresholds")
        if isinstance(curated.get("technical_requirements_structured"), dict)
        else None
    )
    if not isinstance(thresholds, list) or not thresholds:
        return None, None
    values = [item.get("etas_min_percent") for item in thresholds if isinstance(item, dict) and item.get("etas_min_percent") is not None]
    if not values:
        return None, None
    return float(min(values)), curated_path.as_posix() if curated_path else None


def _value_from_operation(operation: dict[str, Any], *keys: str) -> Any:
    value = _first_value(operation, *keys)
    if value is not None:
        return value
    nested = operation.get("operation")
    if isinstance(nested, dict):
        return _first_value(nested, *keys)
    return None


def check_eligibility(code: str, operation: dict[str, Any]) -> dict[str, Any]:
    """Check operation eligibility against available CEE rules."""
    try:
        normalized_code = require_known_code(code)
    except FicheNotFoundError as exc:
        return error_response(exc.code)

    rules, rules_path = load_rules(normalized_code)
    curated, curated_path = load_curated(normalized_code)
    extracted, extracted_path = load_extracted_json(normalized_code)
    source_files = existing_source_files(rules_path, curated_path, extracted_path)

    from scripts import dossier_agent

    dossier = dossier_agent.build_dossier(normalize_operation_for_agent(normalized_code, operation))
    blocking_points: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    missing_fields: set[str] = set()

    for question in dossier.get("missing_questions", []):
        if isinstance(question, dict):
            blocking_points.append(_text_from_question(question))
            if question.get("field_path"):
                missing_fields.add(str(question["field_path"]))

    for check in dossier.get("eligibility", {}).get("checks", []):
        status = check.get("status")
        item = {
            "id": check.get("id"),
            "field": check.get("id"),
            "text": check.get("detail") or check.get("label"),
            "source": check.get("source"),
        }
        if status == "fail":
            blocking_points.append({**item, "blocking": True})
        elif status in {"missing", "warning"}:
            warnings.append({**item, "severity": "warning"})

    for field in dossier.get("calculation", {}).get("missing_inputs") or []:
        missing_fields.add(str(field))

    etas = _value_from_operation(operation, "etas", "etas_percent")
    min_etas, _ = _minimum_etas_threshold(normalized_code)
    forced_eligible: bool | None = dossier.get("eligibility", {}).get("eligible")
    if etas is not None and min_etas is not None and float(etas) < min_etas:
        forced_eligible = False
        blocking_points.append(
            {
                "id": "etas_below_minimum_threshold",
                "field": "operation.etas_percent",
                "text": f"Etas {etas}% is below the minimum threshold {min_etas:g}% found in the curated fiche.",
                "blocking": True,
                "source": "technical_requirements_structured.etas_thresholds",
            }
        )

    eligible: bool | str
    if forced_eligible is True:
        eligible = True
    elif forced_eligible is False:
        eligible = False
    else:
        eligible = "unknown"

    if support_level(normalized_code) != "supported_full":
        warnings.append(
            {
                "id": "limited_support",
                "severity": "warning",
                "text": "No complete rules + curated pair is available; eligibility cannot be fully automated.",
            }
        )

    return {
        "code": normalized_code,
        "support_level": support_level(normalized_code),
        "eligible": eligible,
        "status": dossier.get("status"),
        "blocking_points": blocking_points,
        "warnings": warnings,
        "missing_fields": sorted(missing_fields),
        "needs_human_review": needs_human_review(curated or extracted),
        "source_files": source_files,
    }


def find_control_risks(code: str, severity: str = "all") -> dict[str, Any]:
    """Return PNCEE rejection/control risks for a fiche."""
    try:
        normalized_code = require_known_code(code)
    except FicheNotFoundError as exc:
        return error_response(exc.code)

    curated, curated_path = load_curated(normalized_code)
    extracted, extracted_path = load_extracted_json(normalized_code)
    fiche = curated or extracted or {}
    requested = str(severity or "all").lower()
    risks: list[dict[str, Any]] = []
    for item in fiche.get("compliance_risks") or []:
        if isinstance(item, dict):
            risk = {
                "text": item.get("text"),
                "severity": item.get("severity") or "medium",
                "source": item.get("source") or item.get("source_file"),
            }
        else:
            risk = {"text": str(item), "severity": "medium", "source": None}
        if requested != "all" and risk["severity"] != requested:
            continue
        risks.append(risk)
    return {
        "code": normalized_code,
        "risks": risks,
        "source_files": existing_source_files(curated_path, extracted_path),
    }


def list_required_documents(code: str) -> dict[str, Any]:
    """List required supporting documents for a fiche."""
    try:
        normalized_code = require_known_code(code)
    except FicheNotFoundError as exc:
        return error_response(exc.code)

    curated, curated_path = load_curated(normalized_code)
    extracted, extracted_path = load_extracted_json(normalized_code)
    fiche = curated or extracted or {}
    documents: list[dict[str, Any]] = []
    for item in fiche.get("required_documents") or []:
        if isinstance(item, dict):
            documents.append(
                {
                    "document": item.get("text") or item.get("label"),
                    "required": True,
                    "source": item.get("source_file") or item.get("source"),
                    "note": item.get("quote") or item.get("section_title"),
                }
            )
        else:
            documents.append({"document": str(item), "required": True, "source": None, "note": None})
    return {
        "code": normalized_code,
        "required_documents": documents,
        "source_files": existing_source_files(curated_path, extracted_path),
    }

