from __future__ import annotations

import unicodedata
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


def _slug(value: Any) -> str | None:
    if value in (None, "", "unknown"):
        return None
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().strip()
    for old, new in {
        "œ": "oe",
        "æ": "ae",
        "/": "_",
        "+": "_et_",
        "&": "_et_",
        "'": "_",
        "’": "_",
        "-": "_",
        " ": "_",
    }.items():
        text = text.replace(old, new)
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def _number(value: Any) -> float | None:
    if value in (None, "", "unknown"):
        return None
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return None


def _value_by_alias(data: dict[str, Any], *keys: str) -> Any:
    value = _first_value(data, *keys)
    if value is not None:
        return value
    for container_key in ("operation", "site", "technical", "calculation"):
        nested = data.get(container_key)
        if isinstance(nested, dict):
            value = _first_value(nested, *keys)
            if value is not None:
                return value
    return None


def _normalize_usage(value: Any) -> str | None:
    text = _slug(value)
    if text is None:
        return None
    if text in {"chauffage_et_ecs", "chauffage+ecs", "heating_and_dhw", "chauffage_et_eau_chaude_sanitaire"}:
        return "chauffage_et_ecs"
    if text in {"eau_chaude_sanitaire_et_chauffage", "ecs_et_chauffage", "chauffage_solaire_et_ecs"}:
        return "ecs_et_chauffage"
    if text in {"eau_chaude_sanitaire", "ecs", "dhw"}:
        return "ecs"
    if text in {"chauffage", "heating"}:
        return "chauffage"
    if "ecs" in text and "chauffage" in text:
        return "ecs_et_chauffage"
    if "chauffage" in text or "heating" in text:
        return "chauffage"
    return text


def _normalize_dwelling(value: Any) -> str | None:
    text = _slug(value)
    if text in {"appartement", "apartment", "collectif", "logement_collectif"}:
        return "appartement"
    if text in {"maison", "maison_individuelle", "house", "individual_house"}:
        return "maison_individuelle"
    return text


def _normalize_gtb_class(value: Any) -> str | None:
    text = _slug(value)
    if text in {"a", "classe_a", "class_a"}:
        return "A"
    if text in {"b", "classe_b", "class_b"}:
        return "B"
    return str(value).strip().upper() if value not in (None, "", "unknown") else None


def _normalize_sector(value: Any) -> str | None:
    text = _slug(value)
    mapping = {
        "bureau": "bureaux",
        "bureaux": "bureaux",
        "enseignement": "enseignement",
        "commerce": "commerces",
        "commerces": "commerces",
        "hotellerie": "hotellerie_restauration",
        "hotellerie_restauration": "hotellerie_restauration",
        "hotel_restaurant": "hotellerie_restauration",
        "sante": "sante",
        "autre": "autres",
        "autres": "autres",
    }
    return mapping.get(text or "", text)


def _normalize_rule_usage(value: Any, *, solar: bool = False) -> str | None:
    usage = _normalize_usage(value)
    if solar and usage == "chauffage_et_ecs":
        return "ecs_et_chauffage"
    if not solar and usage == "ecs_et_chauffage":
        return "chauffage_et_ecs"
    mapping = {
        "refroidissement_climatisation": "refroidissement_climatisation",
        "refroidissement": "refroidissement_climatisation",
        "climatisation": "refroidissement_climatisation",
        "eclairage": "eclairage",
        "auxiliaire": "auxiliaire",
        "auxiliaires": "auxiliaire",
    }
    return mapping.get(usage or "", usage)


def _is_between(value: float, lower: Any, upper: Any) -> bool:
    if lower is not None and value < float(lower):
        return False
    if upper is not None and value >= float(upper):
        return False
    return True


def _missing_result(
    code: str,
    formula: str | None,
    variables_used: dict[str, Any],
    missing: list[str],
    source_files: list[str],
    notes: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "kwh_cumac": None,
        "formula_used": formula,
        "variables_used": variables_used,
        "confidence": "low",
        "needs_human_review": True,
        "notes": notes or f"Missing critical calculation variables: {', '.join(missing)}.",
        "source_files": source_files,
    }


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


def _lookup(rows: list[dict[str, Any]], table: str | None = None, **criteria: Any) -> dict[str, Any] | None:
    for row in rows:
        if table is not None and row.get("table") != table:
            continue
        matched = True
        for key, value in criteria.items():
            if value is None:
                continue
            if row.get(key) != value:
                matched = False
                break
        if matched:
            return row
    return None


def _rule_formula(rules: dict[str, Any], fiche: dict[str, Any] | None) -> str | None:
    calculation = rules.get("calculation") if isinstance(rules.get("calculation"), dict) else {}
    formula = calculation.get("formula")
    if formula:
        return str(formula)
    fiche_calculation = fiche.get("calculation") if isinstance(fiche, dict) and isinstance(fiche.get("calculation"), dict) else {}
    return fiche_calculation.get("formula_text")


def _compute_bar_th_168_from_rules(code: str, rules: dict[str, Any], fiche: dict[str, Any], variables: dict[str, Any], source_files: list[str]) -> dict[str, Any]:
    formula = _rule_formula(rules, fiche)
    rows = rules["calculation"]["lookup_table"]
    zone = str(_value_by_alias(variables, "climate_zone", "zone", "zone_climatique") or "").upper()
    usage = _normalize_rule_usage(_value_by_alias(variables, "usage", "operation_usage"), solar=True)
    surface = _number(_value_by_alias(variables, "collector_area_m2", "surface_capteurs_m2", "solar_collector_area_m2", "S"))
    values = {"zone": zone or None, "usage": usage, "collector_area_m2": surface}
    missing = [name for name, value in values.items() if value in (None, "", "unknown")]
    if missing:
        return _missing_result(code, formula, values, missing, source_files)
    row = _lookup(rows, zone=zone, usage=usage)
    if row is None:
        return _missing_result(code, formula, values, [], source_files, "No matching BAR-TH-168 rule row found for zone and usage.")
    kwh = round(float(row["value_kwh_cumac_per_m2"]) * float(surface), 3)
    return {
        "code": code,
        "kwh_cumac": kwh,
        "formula_used": formula,
        "variables_used": {**values, "amount_row": row},
        "confidence": "high",
        "needs_human_review": False,
        "notes": "Calculation used rules lookup_table: value_kwh_cumac_per_m2 * collector_area_m2.",
        "source_files": source_files,
    }


def _compute_bar_th_171_from_rules(code: str, rules: dict[str, Any], fiche: dict[str, Any], variables: dict[str, Any], source_files: list[str]) -> dict[str, Any]:
    formula = _rule_formula(rules, fiche)
    rows = rules["calculation"]["lookup_table"]
    dwelling = _normalize_dwelling(_value_by_alias(variables, "dwelling_type", "logement_type", "building_type"))
    surface = _number(_value_by_alias(variables, "heated_surface_s_m2", "heated_surface_m2", "surface_chauffee_m2", "S"))
    zone = str(_value_by_alias(variables, "climate_zone", "zone", "zone_climatique") or "").upper()
    etas = _number(_value_by_alias(variables, "etas_percent", "etas"))
    values = {"dwelling_type": dwelling, "heated_surface_s_m2": surface, "climate_zone": zone or None, "etas_percent": etas}
    missing = [name for name, value in values.items() if value in (None, "", "unknown")]
    if missing:
        return _missing_result(code, formula, values, missing, source_files)
    amount_row = next(
        (
            row
            for row in rows
            if row.get("table") == "amount_by_dwelling_and_etas"
            and row.get("dwelling_type") == dwelling
            and _is_between(float(etas), row.get("etas_min"), row.get("etas_max"))
        ),
        None,
    )
    surface_row = next(
        (
            row
            for row in rows
            if row.get("table") == "surface_factor"
            and row.get("dwelling_type") == dwelling
            and _is_between(float(surface), row.get("s_min_m2"), row.get("s_max_m2"))
        ),
        None,
    )
    zone_row = _lookup(rows, table="zone_factor", zone=zone)
    if not amount_row or not surface_row or not zone_row:
        return _missing_result(code, formula, values, [], source_files, "No matching BAR-TH-171 rule row found for dwelling, Etas, surface and zone.")
    kwh = round(float(amount_row["value_kwh_cumac"]) * float(surface_row["factor"]) * float(zone_row["factor"]), 3)
    return {
        "code": code,
        "kwh_cumac": kwh,
        "formula_used": formula,
        "variables_used": {**values, "amount_row": amount_row, "surface_factor_row": surface_row, "zone_factor_row": zone_row},
        "confidence": "high",
        "needs_human_review": False,
        "notes": "Calculation used rules lookup_table: amount_by_dwelling_and_etas * surface_factor * zone_factor.",
        "source_files": source_files,
    }


def _as_usage_list(value: Any) -> list[str | None]:
    if isinstance(value, list):
        return [_normalize_rule_usage(item) for item in value]
    return [_normalize_rule_usage(value)]


def _compute_bat_th_116_from_rules(code: str, rules: dict[str, Any], fiche: dict[str, Any], variables: dict[str, Any], source_files: list[str]) -> dict[str, Any]:
    formula = _rule_formula(rules, fiche)
    rows = rules["calculation"]["lookup_table"]
    gtb_class = _normalize_gtb_class(_value_by_alias(variables, "gtb_class_after", "gtb_class", "class_after"))
    surface = _number(_value_by_alias(variables, "managed_surface_m2", "surface_geree_m2", "S"))
    zone = str(_value_by_alias(variables, "climate_zone", "zone", "zone_climatique") or "").upper()
    sector = _normalize_sector(_value_by_alias(variables, "sector_activity", "activity_sector", "secteur_activite"))
    usages = [usage for usage in _as_usage_list(_value_by_alias(variables, "usage", "usages")) if usage]
    values = {"gtb_class_after": gtb_class, "managed_surface_m2": surface, "climate_zone": zone or None, "sector_activity": sector, "usage": usages}
    missing = [name for name, value in values.items() if value in (None, "", [], "unknown")]
    if missing:
        return _missing_result(code, formula, values, missing, source_files)
    zone_row = _lookup(rows, table="zone_factor", zone=zone)
    if zone_row is None:
        return _missing_result(code, formula, values, [], source_files, "No matching BAT-TH-116 zone factor row found.")
    usage_rows: list[dict[str, Any]] = []
    total_per_m2 = 0.0
    for usage in usages:
        row = _lookup(rows, table="amount_by_class_sector_usage", gtb_class=gtb_class, sector_activity=sector, usage=usage)
        if row is None or row.get("value_kwh_cumac_per_m2") is None:
            return _missing_result(code, formula, values, [], source_files, f"No matching BAT-TH-116 amount row found for usage {usage}.")
        usage_rows.append(row)
        total_per_m2 += float(row["value_kwh_cumac_per_m2"])
    kwh = round(total_per_m2 * float(zone_row["factor"]) * float(surface), 3)
    return {
        "code": code,
        "kwh_cumac": kwh,
        "formula_used": formula,
        "variables_used": {**values, "amount_rows": usage_rows, "zone_factor_row": zone_row},
        "confidence": "high",
        "needs_human_review": False,
        "notes": "Calculation used rules lookup_table: sum(value_kwh_cumac_per_m2 by usage) * zone_factor * managed_surface_m2.",
        "source_files": source_files,
    }


def _power_regime(variables: dict[str, Any]) -> str | None:
    explicit = _slug(_value_by_alias(variables, "power_regime"))
    if explicit in {"le_400_kw", "gt_400_kw"}:
        return explicit
    power = _number(_value_by_alias(variables, "pac_nominal_power_kw", "pac_power_kw", "power_kw", "P"))
    if power is None:
        return None
    return "le_400_kw" if power <= 400 else "gt_400_kw"


def _compute_bat_heat_pump_surface_from_rules(code: str, rules: dict[str, Any], fiche: dict[str, Any], variables: dict[str, Any], source_files: list[str]) -> dict[str, Any]:
    formula = _rule_formula(rules, fiche)
    rows = rules["calculation"]["lookup_table"]
    zone = str(_value_by_alias(variables, "climate_zone", "zone", "zone_climatique") or "").upper()
    sector = _normalize_sector(_value_by_alias(variables, "sector_activity", "activity_sector", "secteur_activite"))
    surface = _number(_value_by_alias(variables, "heated_surface_s_m2", "managed_surface_m2", "surface_chauffee_m2", "S"))
    regime = _power_regime(variables)
    metric = "etas" if regime == "le_400_kw" else "cop" if regime == "gt_400_kw" else None
    metric_value = _number(_value_by_alias(variables, "etas_percent", "etas")) if metric == "etas" else _number(_value_by_alias(variables, "cop")) if metric == "cop" else None
    usage = _normalize_rule_usage(_value_by_alias(variables, "usage", "operation_usage"))
    values = {
        "climate_zone": zone or None,
        "sector_activity": sector,
        "surface_m2": surface,
        "power_regime": regime,
        "metric": metric,
        "metric_value": metric_value,
    }
    if code == "BAT-TH-162":
        values["usage"] = usage
    missing = [name for name, value in values.items() if value in (None, "", "unknown")]
    if missing:
        return _missing_result(code, formula, values, missing, source_files)
    sector_row = _lookup(rows, table="sector_factor", sector_activity=sector)
    amount_table = "amount_by_power_metric_zone_usage" if code == "BAT-TH-162" else "amount_by_power_metric_zone"
    amount_row = next(
        (
            row
            for row in rows
            if row.get("table") == amount_table
            and row.get("power_regime") == regime
            and row.get("metric") == metric
            and row.get("zone") == zone
            and (code != "BAT-TH-162" or row.get("usage") == usage)
            and _is_between(float(metric_value), row.get("min"), row.get("max"))
        ),
        None,
    )
    if sector_row is None or amount_row is None:
        return _missing_result(code, formula, values, [], source_files, f"No matching {code} rule row found.")
    kwh = round(float(amount_row["value_kwh_cumac_per_m2"]) * float(sector_row["factor"]) * float(surface), 3)
    return {
        "code": code,
        "kwh_cumac": kwh,
        "formula_used": formula,
        "variables_used": {**values, "amount_row": amount_row, "sector_factor_row": sector_row},
        "confidence": "high",
        "needs_human_review": False,
        "notes": "Calculation used rules lookup_table: amount_by_power_metric_zone * sector_factor * surface_m2.",
        "source_files": source_files,
    }


def _compute_from_rules(code: str, rules: dict[str, Any], fiche: dict[str, Any], variables: dict[str, Any], source_files: list[str]) -> dict[str, Any] | None:
    if not isinstance(rules.get("calculation"), dict) or not isinstance(rules["calculation"].get("lookup_table"), list):
        return None
    calculators = {
        "BAR-TH-168": _compute_bar_th_168_from_rules,
        "BAR-TH-171": _compute_bar_th_171_from_rules,
        "BAT-TH-116": _compute_bat_th_116_from_rules,
        "BAT-TH-162": _compute_bat_heat_pump_surface_from_rules,
        "BAT-TH-163": _compute_bat_heat_pump_surface_from_rules,
    }
    calculator = calculators.get(code)
    if calculator is None:
        return None
    return calculator(code, rules, fiche, variables, source_files)


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

    if rules:
        rules_result = _compute_from_rules(normalized, rules, fiche, variables, source_files)
        if rules_result is not None:
            return rules_result

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
