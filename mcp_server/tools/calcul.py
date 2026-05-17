from __future__ import annotations

from typing import Any

from mcp_server.utils.loader import (
    FicheNotFoundError,
    code_paths,
    error_response,
    existing_source_files,
    load_extracted_json,
    load_rules,
    require_known_code,
)


def _first_value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, "", "unknown"):
            return data[key]
    return None


def _normalize_usage(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if text in {"chauffage_et_ecs", "chauffage+ecs", "heating_and_dhw", "chauffage_et_eau_chaude_sanitaire"}:
        return "chauffage_et_ecs"
    if text in {"chauffage", "heating"}:
        return "chauffage"
    if "ecs" in text and "chauffage" in text:
        return "chauffage_et_ecs"
    if "chauffage" in text or "heating" in text:
        return "chauffage"
    return text


def _select_amount_row(rows: list[dict[str, Any]], zone: str, etas: float, usage: str | None) -> tuple[dict[str, Any] | None, bool]:
    matching: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("zone", "")).upper() != zone:
            continue
        etas_min = row.get("etas_min")
        etas_max = row.get("etas_max")
        if etas_min is None:
            continue
        if etas < float(etas_min):
            continue
        if etas_max is not None and etas >= float(etas_max):
            continue
        if usage and row.get("usage") != usage:
            continue
        matching.append(row)
    if not matching:
        return None, False
    if usage:
        return matching[0], False
    return min(matching, key=lambda item: float(item.get("kwh_cumac_per_apartment") or 0)), True


def compute_kwh_cumac(code: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Compute kWh cumac from machine-readable rules when possible."""
    try:
        normalized = require_known_code(code)
    except FicheNotFoundError as exc:
        return error_response(exc.code)

    rules, rules_path = load_rules(normalized)
    fiche, fiche_path = load_extracted_json(normalized)
    source_files = existing_source_files(rules_path, fiche_path)
    if not rules:
        return {
            "code": normalized,
            "kwh_cumac": None,
            "formula_used": None,
            "variables_used": {},
            "confidence": "low",
            "needs_human_review": True,
            "notes": "No rules/{code}.rules.json file is available; calculation refused instead of guessing.".format(code=normalized),
            "source_files": source_files,
        }
    if not isinstance(fiche, dict):
        return {
            "code": normalized,
            "kwh_cumac": None,
            "formula_used": None,
            "variables_used": {},
            "confidence": "low",
            "needs_human_review": True,
            "notes": "Extracted fiche JSON is missing; no calculation table can be read.",
            "source_files": source_files,
        }

    calculation = fiche.get("calculation") if isinstance(fiche.get("calculation"), dict) else {}
    formula = calculation.get("formula_text")
    amount_table = calculation.get("amount_table")
    if not isinstance(amount_table, list) or not amount_table:
        return {
            "code": normalized,
            "kwh_cumac": None,
            "formula_used": formula,
            "variables_used": {},
            "confidence": "low",
            "needs_human_review": True,
            "notes": "No structured amount_table is available for this fiche.",
            "source_files": source_files,
        }

    zone = _first_value(variables, "zone", "climate_zone", "zone_climatique")
    apartment_count = _first_value(variables, "apartment_count", "apartments", "apartment_count_heated_by_pac", "N")
    etas = _first_value(variables, "etas", "etas_percent")
    usage = _normalize_usage(_first_value(variables, "usage", "pac_usage"))
    missing = [
        name
        for name, value in {
            "zone": zone,
            "apartment_count": apartment_count,
            "etas": etas,
        }.items()
        if value in (None, "", "unknown")
    ]
    if missing:
        return {
            "code": normalized,
            "kwh_cumac": None,
            "formula_used": formula,
            "variables_used": {"zone": zone, "apartment_count": apartment_count, "etas": etas, "usage": usage},
            "confidence": "low",
            "needs_human_review": True,
            "notes": f"Missing critical calculation variables: {', '.join(missing)}.",
            "source_files": source_files,
        }

    row, inferred_usage = _select_amount_row(amount_table, str(zone).upper(), float(etas), usage)
    if row is None:
        return {
            "code": normalized,
            "kwh_cumac": None,
            "formula_used": formula,
            "variables_used": {"zone": zone, "apartment_count": apartment_count, "etas": etas, "usage": usage},
            "confidence": "low",
            "needs_human_review": True,
            "notes": "No matching amount_table row found for the provided zone, Etas and usage.",
            "source_files": source_files,
        }

    r_factor = _first_value(variables, "r_factor", "R")
    notes: list[str] = []
    needs_review = False
    confidence = "high"
    if r_factor is None:
        pac_power = _first_value(variables, "pac_nominal_power_kw", "pac_power_kw", "pac_power")
        boiler_power = _first_value(
            variables,
            "chaufferie_useful_power_after_works_kw",
            "boiler_room_useful_power_after_works_kw",
            "boiler_room_power_after_works_kw",
        )
        if pac_power is not None and boiler_power not in (None, 0, "0"):
            ratio = float(pac_power) / float(boiler_power)
            r_factor = ratio if ratio < 0.4 else 1.0
        else:
            r_factor = 1.0
            needs_review = True
            confidence = "medium"
            notes.append("R factor was not provided and PAC/boiler powers are missing; provisional R=1 used for a draft calculation.")
    if inferred_usage:
        needs_review = True
        confidence = "medium"
        notes.append("Usage was not provided; used the lowest matching amount row for a conservative draft value.")

    kwh = round(float(row["kwh_cumac_per_apartment"]) * float(apartment_count) * float(r_factor), 3)
    return {
        "code": normalized,
        "kwh_cumac": kwh,
        "formula_used": formula,
        "variables_used": {
            "zone": str(zone).upper(),
            "apartment_count": apartment_count,
            "etas": etas,
            "usage": usage or "minimum_matching_row",
            "r_factor": round(float(r_factor), 6),
            "amount_row": row,
        },
        "confidence": confidence,
        "needs_human_review": needs_review,
        "notes": " ".join(notes) if notes else "Calculation used structured amount_table and provided variables.",
        "source_files": source_files,
    }

