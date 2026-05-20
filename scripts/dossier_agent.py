"""Generate strict CEE pre-deposit packs from client operation JSON.

BAR-TH-179 keeps its full strict evaluator. Other fiche codes are accepted as
generic drafts: the agent exposes available reference material but never invents
eligibility, blocking points, or calculation values when machine-readable rules
are absent.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = REPO_ROOT / "rules"
CURATED_DIR = REPO_ROOT / "data" / "curated"
JSON_DIR = REPO_ROOT / "data" / "json"

BAR_TH_179_SOURCE = "Residentiel_BAR/BAR-TH-179 vA81-2 à compter du 30-04-2026.pdf"
BAR_TH_179_EFFECTIVE_DATE = "2026-04-30"
BAR_TH_179_ENGAGEMENT_DEADLINE = "2030-12-31"

try:
    from scripts.validate_operation import has_chronology_inputs, validate_chronology
    from scripts.dossier_validators import validate_dossier_cee
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from validate_operation import has_chronology_inputs, validate_chronology
    from dossier_validators import validate_dossier_cee


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == "unknown"


def get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            current = None
            break
        current = current.get(part)
    if not is_missing(current):
        return current
    return get_inferred_field_value(data, path)


def is_inferred_project(data: dict[str, Any]) -> bool:
    return isinstance(data.get("fields"), dict) and ("code" in data or "case_id" in data)


def get_inferred_field_value(data: dict[str, Any], path: str) -> Any:
    fields = data.get("fields")
    if not isinstance(fields, dict):
        return None
    candidates = [path, path.split(".")[-1]]
    for candidate in candidates:
        item = fields.get(candidate)
        if isinstance(item, dict) and "value" in item:
            return item.get("value")
        if item is not None:
            return item
    return None


def get_operation_fiche_code(operation: dict[str, Any]) -> str:
    value = (
        operation.get("fiche_code")
        or operation.get("code")
        or operation.get("target_code")
        or get_path(operation, "operation.cee_code")
        or get_path(operation, "objective.cee_code")
    )
    return str(value or "").strip().upper()


def get_operation_id(operation: dict[str, Any], fiche_code: str) -> str:
    return str(operation.get("operation_id") or operation.get("case_id") or f"draft-{fiche_code.lower()}")


def relative_repo_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def reference_paths(fiche_code: str) -> dict[str, Path]:
    return {
        "rules": RULES_DIR / f"{fiche_code}.rules.json",
        "curated": CURATED_DIR / f"{fiche_code}.json",
        "json": JSON_DIR / f"{fiche_code}.json",
    }


def detect_support_level(fiche_code: str) -> str:
    paths = reference_paths(fiche_code)
    has_rules = paths["rules"].exists()
    has_curated = paths["curated"].exists()
    has_json = paths["json"].exists()
    if has_rules and has_curated:
        return "supported_full"
    if has_curated or has_json:
        return "supported_partial"
    return "supported_generic"


def load_reference_fiche(fiche_code: str) -> tuple[dict[str, Any] | None, str, Path | None]:
    paths = reference_paths(fiche_code)
    if paths["curated"].exists():
        return load_json(paths["curated"]), "curated", paths["curated"]
    if paths["json"].exists():
        return load_json(paths["json"]), "json", paths["json"]
    return None, "none", None


def source_from_item(item: Any, fallback: str | None = None) -> str | None:
    if isinstance(item, dict):
        return item.get("source_file") or item.get("source") or fallback
    return fallback


def text_from_item(item: Any) -> str:
    if isinstance(item, dict):
        value = item.get("text") or item.get("label") or item.get("quote") or item.get("description")
        return str(value or "").strip()
    return str(item or "").strip()


def reference_items(fiche: dict[str, Any] | None, key: str) -> list[Any]:
    if not isinstance(fiche, dict):
        return []
    items = fiche.get(key)
    return items if isinstance(items, list) else []


def normalize_text(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def normalize_usage(value: Any) -> str:
    text = normalize_text(value)
    mapping = {
        "chauffage": "chauffage",
        "heating": "chauffage",
        "chauffage_et_ecs": "chauffage_et_ecs",
        "chauffage+ecs": "chauffage_et_ecs",
        "chauffage_et_eau_chaude_sanitaire": "chauffage_et_ecs",
        "ecs": "ecs_only",
        "ecs_only": "ecs_only",
        "eau_chaude_sanitaire": "ecs_only",
        "production_eau_chaude_sanitaire": "ecs_only",
    }
    return mapping.get(text, text or "unknown")


def normalize_pac_type(value: Any) -> str:
    text = normalize_text(value)
    mapping = {
        "air/eau": "air_eau",
        "air_eau": "air_eau",
        "air_eau_collective": "air_eau",
        "eau/eau": "eau_eau",
        "eau_eau": "eau_eau",
    }
    return mapping.get(text, text or "unknown")


def normalize_application(value: Any) -> str:
    text = normalize_text(value)
    mapping = {
        "basse": "basse_temperature",
        "basse_temperature": "basse_temperature",
        "low_temperature": "basse_temperature",
        "moyenne": "moyenne_haute_temperature",
        "haute": "moyenne_haute_temperature",
        "moyenne_haute": "moyenne_haute_temperature",
        "moyenne_haute_temperature": "moyenne_haute_temperature",
        "medium_high": "moyenne_haute_temperature",
    }
    return mapping.get(text, text or "unknown")


def parse_iso_date(value: Any) -> datetime | None:
    if is_missing(value):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def add_question(
    questions: list[dict[str, Any]],
    question_id: str,
    field_path: str,
    question: str,
    expected_input: str | None = None,
) -> None:
    if any(item["id"] == question_id for item in questions):
        return
    questions.append(
        {
            "id": question_id,
            "field_path": field_path,
            "question": question,
            "expected_input": expected_input,
            "blocking": True,
        }
    )


def add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    label: str,
    status: str,
    detail: str | None = None,
    source: str | None = BAR_TH_179_SOURCE,
    blocking: bool = True,
) -> None:
    checks.append(
        {
            "id": check_id,
            "label": label,
            "status": status,
            "detail": detail,
            "source": source,
            "blocking": blocking,
        }
    )


def require_bool_check(
    operation: dict[str, Any],
    checks: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    path: str,
    check_id: str,
    label: str,
    missing_question: str,
    fail_detail: str,
    block_missing: bool = True,
) -> None:
    value = get_path(operation, path)
    if value is True:
        add_check(checks, check_id, label, "pass", "Confirme dans les donnees client.")
    elif value is False:
        add_check(checks, check_id, label, "fail", fail_detail)
    elif block_missing:
        add_check(checks, check_id, label, "missing", "Information non fournie.")
        add_question(questions, f"missing_{check_id}", path, missing_question, "true/false ou document justificatif")
    else:
        add_check(checks, check_id, label, "warning", "Information non fournie dans l'inferred_project.", blocking=False)


def select_bar_th_179_amount_row(fiche: dict[str, Any], usage: str, zone: str, etas: float) -> dict[str, Any] | None:
    for row in fiche.get("calculation", {}).get("amount_table", []):
        if row.get("usage") != usage or row.get("zone") != zone:
            continue
        etas_min = row.get("etas_min")
        etas_max = row.get("etas_max")
        if etas_min is None:
            continue
        if etas >= etas_min and (etas_max is None or etas < etas_max):
            return row
    return None


def compute_bar_th_179(
    operation: dict[str, Any],
    fiche: dict[str, Any],
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    missing_inputs: list[str] = []
    usage = normalize_usage(get_path(operation, "operation.usage"))
    zone = get_path(operation, "site.climate_zone")
    apartments = get_path(operation, "site.apartment_count_heated_by_pac")
    etas = get_path(operation, "operation.etas_percent")
    pac_power = get_path(operation, "operation.pac_nominal_power_kw")
    chaufferie_power = get_path(operation, "operation.chaufferie_useful_power_after_works_kw")
    backup_excluded = get_path(operation, "operation.backup_equipment_excluded")

    required = {
        "operation.usage": usage if usage != "unknown" else None,
        "site.climate_zone": zone,
        "site.apartment_count_heated_by_pac": apartments,
        "operation.etas_percent": etas,
        "operation.pac_nominal_power_kw": pac_power,
        "operation.chaufferie_useful_power_after_works_kw": chaufferie_power,
        "operation.backup_equipment_excluded": backup_excluded,
    }
    for path, value in required.items():
        if is_missing(value):
            missing_inputs.append(path)
            add_question(
                questions,
                f"missing_calc_{path.replace('.', '_')}",
                path,
                f"Merci de fournir la valeur obligatoire pour {path}.",
                "valeur exacte issue du client ou du document technique",
            )

    if backup_excluded is False:
        missing_inputs.append("operation.backup_equipment_excluded")

    formula = fiche.get("calculation", {}).get("formula_text")
    base = {
        "status": "missing_inputs",
        "formula_text": formula,
        "kwh_cumac": None,
        "unit": "kWh cumac",
        "inputs": {
            "usage": usage,
            "zone": zone,
            "apartment_count_heated_by_pac": apartments,
            "etas_percent": etas,
            "pac_nominal_power_kw": pac_power,
            "chaufferie_useful_power_after_works_kw": chaufferie_power,
            "backup_equipment_excluded": backup_excluded,
        },
        "amount_row": None,
        "r_factor": None,
        "missing_inputs": missing_inputs,
    }

    if missing_inputs:
        return base
    if usage not in {"chauffage", "chauffage_et_ecs"}:
        base["status"] = "not_applicable"
        base["missing_inputs"] = ["operation.usage"]
        return base

    row = select_bar_th_179_amount_row(fiche, usage, str(zone), float(etas))
    if not row:
        base["missing_inputs"] = ["operation.etas_percent"]
        add_question(
            questions,
            "missing_valid_etas_range",
            "operation.etas_percent",
            "L'Etas fourni ne permet pas de trouver une ligne de calcul BAR-TH-179 valide.",
            "Etas admissible selon application PAC",
        )
        return base

    if float(chaufferie_power) <= 0:
        base["missing_inputs"] = ["operation.chaufferie_useful_power_after_works_kw"]
        add_question(
            questions,
            "missing_valid_chaufferie_power",
            "operation.chaufferie_useful_power_after_works_kw",
            "La puissance utile de chaufferie apres travaux doit etre strictement positive.",
            "kW > 0",
        )
        return base

    power_ratio = float(pac_power) / float(chaufferie_power)
    if power_ratio < 0.4:
        r_value = round(power_ratio, 6)
        r_value_for_calculation = power_ratio
        r_detail = "Facteur R applique car puissance PAC / puissance chaufferie < 40%."
    else:
        r_value = 1.0
        r_value_for_calculation = 1.0
        r_detail = "Facteur R = 1 car puissance PAC / puissance chaufferie >= 40%."

    kwh = round(float(row["kwh_cumac_per_apartment"]) * float(apartments) * r_value_for_calculation, 3)
    base.update(
        {
            "status": "computed",
            "kwh_cumac": kwh,
            "amount_row": deepcopy(row),
            "r_factor": {
                "value": r_value,
                "power_ratio": round(power_ratio, 6),
                "detail": r_detail,
                "formula": "R = puissance PAC / puissance utile chaufferie apres travaux si ratio < 40%, sinon R = 1",
            },
            "missing_inputs": [],
        }
    )
    return base


def normalize_document_key(value: Any) -> str:
    return normalize_text(value).replace("/", "_")


def document_matches_id(document: dict[str, Any], doc_id: str) -> bool:
    expected = normalize_document_key(doc_id)
    candidates = [
        document.get("id"),
        document.get("document_id"),
        document.get("type"),
        document.get("name"),
        document.get("label"),
        document.get("path_or_label"),
    ]
    return any(normalize_document_key(candidate) == expected for candidate in candidates if candidate)


def lookup_document(operation: dict[str, Any], doc_id: str) -> dict[str, Any] | None:
    documents = operation.get("documents") or {}
    if isinstance(documents, dict):
        item = documents.get(doc_id)
        return item if isinstance(item, dict) else None
    if isinstance(documents, list):
        for item in documents:
            if isinstance(item, dict) and document_matches_id(item, doc_id):
                return item
    return None


def document_is_provided(doc: dict[str, Any]) -> bool:
    if doc.get("provided") is True:
        return True
    status = normalize_text(doc.get("status"))
    return status in {"available", "received", "confirmed", "provided"}


def evaluate_document(
    operation: dict[str, Any],
    questions: list[dict[str, Any]],
    doc_id: str,
    label: str,
    required: bool = True,
    required_flags: list[str] | None = None,
    source: str | None = BAR_TH_179_SOURCE,
    block_missing: bool = True,
) -> dict[str, Any]:
    doc = lookup_document(operation, doc_id)
    if not required:
        return {"id": doc_id, "label": label, "required": False, "status": "not_required", "issues": [], "source": source}

    if not isinstance(doc, dict):
        if block_missing:
            add_question(questions, f"missing_doc_{doc_id}", f"documents.{doc_id}", f"Merci de fournir : {label}.", "document ou confirmation explicite")
            return {"id": doc_id, "label": label, "required": True, "status": "missing", "issues": ["Document non fourni."], "source": source}
        return {"id": doc_id, "label": label, "required": True, "status": "unknown", "issues": ["Document non controle dans l'inferred_project."], "source": source}

    if not document_is_provided(doc):
        if block_missing:
            add_question(questions, f"missing_doc_{doc_id}", f"documents.{doc_id}", f"Merci de fournir : {label}.", "document requis")
            return {"id": doc_id, "label": label, "required": True, "status": "missing", "issues": ["Document absent."], "source": source}
        return {"id": doc_id, "label": label, "required": True, "status": "unknown", "issues": ["Document a valider depuis l'inferred_project."], "source": source}

    issues: list[str] = []
    for flag in required_flags or []:
        value = doc.get(flag)
        if value is not True:
            issues.append(f"Champ documentaire non conforme ou non confirme : {flag}.")
            if block_missing:
                add_question(
                    questions,
                    f"non_conform_doc_{doc_id}_{flag}",
                    f"documents.{doc_id}.{flag}",
                    f"Merci de confirmer/corriger le champ {flag} pour : {label}.",
                    "true avec preuve documentaire",
                )

    status = "received" if not issues else "non_conform"
    return {"id": doc_id, "label": label, "required": True, "status": status, "issues": issues, "source": source}


def build_bar_th_179_dossier(operation: dict[str, Any]) -> dict[str, Any]:
    fiche = load_json(REPO_ROOT / "data" / "json" / "BAR-TH-179.json")
    fiche_code = get_operation_fiche_code(operation)
    operation_id = get_operation_id(operation, fiche_code)
    inferred_input = is_inferred_project(operation)
    questions: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []

    require_bool_check(
        operation,
        checks,
        questions,
        "site.residential_collective",
        "residential_collective",
        "Batiment residentiel collectif",
        "Le batiment est-il bien residentiel collectif ?",
        "BAR-TH-179 vise les batiments residentiels collectifs.",
        block_missing=not inferred_input,
    )
    require_bool_check(
        operation,
        checks,
        questions,
        "site.existing_building",
        "existing_building",
        "Batiment existant",
        "Le batiment est-il existant ?",
        "BAR-TH-179 vise les batiments existants.",
        block_missing=not inferred_input,
    )
    require_bool_check(
        operation,
        checks,
        questions,
        "operation.heating_system_collective",
        "collective_heating",
        "Systeme de chauffage collectif",
        "Le systeme concerne-t-il bien un chauffage collectif ?",
        "La fiche vise un systeme de chauffage collectif.",
        block_missing=not inferred_input,
    )

    engagement = parse_iso_date(get_path(operation, "operation.engagement_date"))
    effective = parse_iso_date(BAR_TH_179_EFFECTIVE_DATE)
    deadline = parse_iso_date(BAR_TH_179_ENGAGEMENT_DEADLINE)
    if engagement is None:
        if inferred_input:
            add_check(checks, "engagement_date", "Date d'engagement", "warning", "Date non fournie dans l'inferred_project.", blocking=False)
        else:
            add_check(checks, "engagement_date", "Date d'engagement", "missing", "Date non fournie.")
            add_question(questions, "missing_engagement_date", "operation.engagement_date", "Quelle est la date d'engagement de l'operation ?", "date ISO AAAA-MM-JJ")
    elif effective and deadline and effective <= engagement <= deadline:
        add_check(checks, "engagement_date", "Date d'engagement", "pass", "Date dans la periode BAR-TH-179 vA81-2.")
    else:
        add_check(checks, "engagement_date", "Date d'engagement", "fail", "Date hors periode applicable BAR-TH-179 vA81-2.")

    usage = normalize_usage(get_path(operation, "operation.usage"))
    if usage == "unknown":
        if inferred_input:
            add_check(checks, "usage", "Usage PAC", "warning", "Usage non fourni dans l'inferred_project.", blocking=False)
        else:
            add_check(checks, "usage", "Usage PAC", "missing", "Usage non fourni.")
            add_question(questions, "missing_usage", "operation.usage", "La PAC sert-elle au chauffage seul, au chauffage + ECS, ou uniquement a l'ECS ?", "chauffage | chauffage_et_ecs | ecs_only")
    elif usage == "ecs_only":
        add_check(checks, "usage", "Usage PAC", "fail", "Les PAC utilisees uniquement pour l'ECS sont exclues.")
    elif usage in {"chauffage", "chauffage_et_ecs"}:
        add_check(checks, "usage", "Usage PAC", "pass", f"Usage retenu : {usage}.")
    else:
        add_check(checks, "usage", "Usage PAC", "missing", f"Usage non reconnu : {usage}.")
        add_question(questions, "missing_usage", "operation.usage", "Merci de normaliser l'usage PAC.", "chauffage | chauffage_et_ecs | ecs_only")

    pac_type = normalize_pac_type(get_path(operation, "operation.pac_type"))
    if pac_type == "unknown":
        if inferred_input:
            add_check(checks, "pac_type", "Type de PAC", "warning", "Type de PAC non fourni dans l'inferred_project.", blocking=False)
        else:
            add_check(checks, "pac_type", "Type de PAC", "missing", "Type de PAC non fourni.")
            add_question(questions, "missing_pac_type", "operation.pac_type", "La PAC est-elle bien de type air/eau ?", "air_eau")
    elif pac_type == "air_eau":
        add_check(checks, "pac_type", "Type de PAC", "pass", "PAC air/eau.")
    else:
        add_check(checks, "pac_type", "Type de PAC", "fail", "BAR-TH-179 exige une PAC air/eau.")

    pac_power = get_path(operation, "operation.pac_nominal_power_kw")
    if is_missing(pac_power):
        if inferred_input:
            add_check(checks, "pac_power_max", "Puissance nominale PAC <= 400 kW", "warning", "Puissance PAC non fournie dans l'inferred_project.", blocking=False)
        else:
            add_check(checks, "pac_power_max", "Puissance nominale PAC <= 400 kW", "missing", "Puissance PAC non fournie.")
            add_question(questions, "missing_pac_nominal_power", "operation.pac_nominal_power_kw", "Quelle est la puissance thermique nominale Prated a -10 deg C de la PAC ?", "kW")
    elif float(pac_power) <= 400:
        add_check(checks, "pac_power_max", "Puissance nominale PAC <= 400 kW", "pass", f"Puissance fournie : {pac_power} kW.")
    else:
        add_check(checks, "pac_power_max", "Puissance nominale PAC <= 400 kW", "fail", f"Puissance fournie : {pac_power} kW.")

    application = normalize_application(get_path(operation, "operation.application_temperature"))
    etas = get_path(operation, "operation.etas_percent")
    if application == "unknown":
        if inferred_input:
            add_check(checks, "application_temperature", "Application basse / moyenne-haute temperature", "warning", "Application non fournie dans l'inferred_project.", blocking=False)
        else:
            add_check(checks, "application_temperature", "Application basse / moyenne-haute temperature", "missing", "Application non fournie.")
            add_question(questions, "missing_application_temperature", "operation.application_temperature", "L'application PAC est-elle basse temperature ou moyenne/haute temperature ?", "basse_temperature | moyenne_haute_temperature")
    elif usage == "chauffage_et_ecs" and application != "moyenne_haute_temperature":
        add_check(checks, "application_temperature", "Application basse / moyenne-haute temperature", "fail", "Pour chauffage + ECS, la fiche retient une application moyenne/haute temperature.")
    else:
        add_check(checks, "application_temperature", "Application basse / moyenne-haute temperature", "pass", f"Application retenue : {application}.")

    if is_missing(etas):
        if inferred_input:
            add_check(checks, "etas_threshold", "Seuil Etas", "warning", "Etas non fourni dans l'inferred_project.", blocking=False)
        else:
            add_check(checks, "etas_threshold", "Seuil Etas", "missing", "Etas non fourni.")
            add_question(questions, "missing_etas", "operation.etas_percent", "Quel est l'Etas de la PAC selon l'application retenue ?", "%")
    elif application == "basse_temperature" and float(etas) >= 126:
        add_check(checks, "etas_threshold", "Seuil Etas", "pass", "Etas >= 126% pour basse temperature.")
    elif application == "moyenne_haute_temperature" and float(etas) >= 111:
        add_check(checks, "etas_threshold", "Seuil Etas", "pass", "Etas >= 111% pour moyenne/haute temperature.")
    elif application != "unknown":
        add_check(checks, "etas_threshold", "Seuil Etas", "fail", f"Etas insuffisant : {etas}%.")

    require_bool_check(
        operation,
        checks,
        questions,
        "operation.backup_equipment_excluded",
        "backup_equipment_excluded",
        "Equipements de secours exclus de la puissance chaufferie",
        "La puissance de chaufferie apres travaux exclut-elle les equipements de secours ?",
        "La fiche demande de ne pas comptabiliser les equipements de secours.",
        block_missing=not inferred_input,
    )

    uses_bar_th_169 = get_path(operation, "non_cumulation.uses_bar_th_169")
    if uses_bar_th_169 is True and usage == "chauffage_et_ecs":
        add_check(checks, "non_cumulation_bar_th_169", "Non-cumul BAR-TH-169", "fail", "Non-cumul detecte avec BAR-TH-169 pour chauffage + ECS.")
    elif uses_bar_th_169 is False:
        add_check(checks, "non_cumulation_bar_th_169", "Non-cumul BAR-TH-169", "pass", "Aucun cumul BAR-TH-169 declare.")
    elif inferred_input:
        add_check(checks, "non_cumulation_bar_th_169", "Non-cumul BAR-TH-169", "warning", "Information non fournie dans l'inferred_project.", blocking=False)
    else:
        add_check(checks, "non_cumulation_bar_th_169", "Non-cumul BAR-TH-169", "missing", "Information non fournie.")
        add_question(questions, "missing_non_cumulation_bar_th_169", "non_cumulation.uses_bar_th_169", "Cette operation est-elle aussi valorisee en BAR-TH-169 ?", "true/false")

    require_bool_check(
        operation,
        checks,
        questions,
        "professional.rge_quality_sign",
        "rge_quality_sign",
        "Signe de qualite professionnel",
        "Le professionnel dispose-t-il du signe de qualite requis ?",
        "Le signe de qualite requis n'est pas confirme.",
        block_missing=not inferred_input,
    )

    documents = [
        evaluate_document(
            operation,
            questions,
            "dimensioning_study",
            "Etude prealable de dimensionnement datee, signee et remise au beneficiaire",
            required_flags=["signed", "dated", "given_at_engagement"],
            block_missing=not inferred_input,
        ),
        evaluate_document(operation, questions, "proof_of_completion", "Preuve de realisation mentionnant marque, reference, Prated, usage, application et Etas", block_missing=not inferred_input),
        evaluate_document(operation, questions, "professional_qualification", "Decision de qualification ou certification du professionnel", block_missing=not inferred_input),
        evaluate_document(operation, questions, "manufacturer_datasheet", "Document fabricant ou equivalent pour verifier PAC, Prated et Etas", block_missing=not inferred_input),
        evaluate_document(operation, questions, "attestation_honor", "Attestation sur l'honneur CEE", block_missing=not inferred_input),
        evaluate_document(operation, questions, "quote_or_order", "Devis, bon de commande ou preuve d'engagement", block_missing=not inferred_input),
        evaluate_document(operation, questions, "invoice", "Facture ou preuve de realisation finale", block_missing=not inferred_input),
    ]
    document_check = {"operation_id": operation_id, "fiche_code": fiche_code, "documents": documents}

    calculation = compute_bar_th_179(operation, fiche, questions)
    if calculation["status"] == "computed" and calculation["r_factor"] and calculation["r_factor"]["value"] < 1:
        risks.append(
            {
                "id": "r_factor_applied",
                "severity": "medium",
                "text": "Facteur R inferieur a 1 applique : verifier soigneusement les puissances PAC et chaufferie.",
                "source": BAR_TH_179_SOURCE,
            }
        )

    for risk_text in fiche.get("compliance_risks", []):
        risks.append({"id": "compliance_reference_risk", "severity": "medium", "text": risk_text, "source": BAR_TH_179_SOURCE})

    failed = [check for check in checks if check["status"] == "fail" and check.get("blocking")]
    missing = [check for check in checks if check["status"] == "missing" and check.get("blocking")]
    bad_docs = [] if inferred_input else [doc for doc in documents if doc["status"] in {"missing", "non_conform", "unknown"} and doc["required"]]

    if failed:
        status = "non_eligible"
        eligible: bool | None = False
        summary = "Dossier non eligible ou incompatible avec BAR-TH-179 selon les donnees fournies."
    elif missing or bad_docs or calculation["status"] != "computed" or questions:
        status = "incomplet_questions"
        eligible = None
        summary = "Dossier incomplet : l'agent doit demander les informations ou documents manquants avant pre-depot."
    else:
        status = "pret_predepot"
        eligible = True
        summary = "Dossier pret pour controle pre-depot, sous reserve de validation humaine et du depot par un acteur habilite."

    unknown_fields = sorted({item["field_path"] for item in questions})
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "operation_id": operation_id,
        "fiche_code": fiche_code,
        "status": status,
        "summary": summary,
        "eligibility": {"eligible": eligible, "checks": checks},
        "calculation": calculation,
        "document_check": document_check,
        "missing_questions": questions,
        "risks": risks,
        "sources": [
            {"label": "Fiche BAR-TH-179 JSON", "path": "data/json/BAR-TH-179.json", "page": None, "section": None},
            {"label": "PDF officiel BAR-TH-179", "path": BAR_TH_179_SOURCE, "page": 1, "section": "Denomination"},
            {"label": "PDF officiel BAR-TH-179", "path": BAR_TH_179_SOURCE, "page": 3, "section": "Montant de certificats en kWh cumac"},
        ],
        "no_hallucination": {
            "invented_values": False,
            "unknown_fields": unknown_fields,
            "rule": "Toute donnee absente reste inconnue et devient une question bloquante.",
        },
    }


def build_generic_draft_dossier(operation: dict[str, Any], fiche_code: str, support_level: str) -> dict[str, Any]:
    fiche, reference_type, reference_path = load_reference_fiche(fiche_code)
    paths = reference_paths(fiche_code)
    operation_id = str(operation.get("operation_id") or operation.get("case_id") or f"draft-{fiche_code.lower()}")

    checks: list[dict[str, Any]] = []
    conditions = reference_items(fiche, "eligibility_conditions")
    if conditions:
        for index, item in enumerate(conditions, start=1):
            text = text_from_item(item)
            if not text:
                continue
            checks.append(
                {
                    "id": f"reference_condition_{index:03d}",
                    "label": "Condition issue de la fiche a valider",
                    "status": "warning",
                    "detail": f"[A VALIDER] {text}",
                    "source": source_from_item(item, relative_repo_path(reference_path) if reference_path else None),
                    "blocking": False,
                }
            )
    else:
        detail = (
            "[A VALIDER] Aucune condition exploitable automatiquement sans rules.json."
            if reference_path
            else "[A VALIDER] Aucune fiche structuree locale disponible pour ce code."
        )
        checks.append(
            {
                "id": "reference_conditions_unavailable",
                "label": "Conditions fiche non evaluables automatiquement",
                "status": "warning",
                "detail": detail,
                "source": relative_repo_path(reference_path) if reference_path else None,
                "blocking": False,
            }
        )

    required_documents = reference_items(fiche, "required_documents")
    documents: list[dict[str, Any]] = []
    for index, item in enumerate(required_documents, start=1):
        text = text_from_item(item)
        if not text:
            continue
        documents.append(
            {
                "id": f"reference_document_{index:03d}",
                "label": text,
                "required": True,
                "status": "unknown",
                "issues": ["[A VALIDER] Piece issue de la fiche, non controlee sans rules.json."],
                "source": source_from_item(item, relative_repo_path(reference_path) if reference_path else None),
            }
        )
    if not documents:
        documents.append(
            {
                "id": "documents_to_validate",
                "label": "Pieces a determiner depuis la fiche officielle",
                "required": True,
                "status": "unknown",
                "issues": ["[A VALIDER] Aucune liste documentaire exploitable automatiquement."],
                "source": relative_repo_path(reference_path) if reference_path else None,
            }
        )

    risks: list[dict[str, Any]] = []
    for index, item in enumerate(reference_items(fiche, "compliance_risks"), start=1):
        text = text_from_item(item)
        if text:
            risks.append(
                {
                    "id": f"reference_risk_{index:03d}",
                    "severity": "medium",
                    "text": f"[A VALIDER] {text}",
                    "source": source_from_item(item, relative_repo_path(reference_path) if reference_path else None),
                }
            )
    for index, item in enumerate(reference_items(fiche, "control_points"), start=1):
        text = text_from_item(item)
        if text:
            risks.append(
                {
                    "id": f"reference_control_point_{index:03d}",
                    "severity": "medium",
                    "text": f"[A VALIDER] Point de controle fiche : {text}",
                    "source": source_from_item(item, relative_repo_path(reference_path) if reference_path else None),
                }
            )
    if not risks:
        risks.append(
            {
                "id": "generic_rules_missing",
                "severity": "medium",
                "text": "[A VALIDER] Aucun rules.json machine-readable : controle humain obligatoire avant pre-depot.",
                "source": relative_repo_path(reference_path) if reference_path else None,
            }
        )

    calculation_ref = fiche.get("calculation", {}) if isinstance(fiche, dict) else {}
    formula_text = calculation_ref.get("formula_text") if isinstance(calculation_ref, dict) else None
    sources: list[dict[str, Any]] = []
    if paths["rules"].exists():
        sources.append({"label": f"Rules {fiche_code}", "path": relative_repo_path(paths["rules"]), "page": None, "section": None})
    if reference_path:
        sources.append({"label": f"Fiche {fiche_code} {reference_type}", "path": relative_repo_path(reference_path), "page": None, "section": None})

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "operation_id": operation_id,
        "fiche_code": fiche_code,
        "status": "draft_generic_no_rules",
        "summary": (
            f"Brouillon generique {fiche_code} ({support_level}) : aucune regle machine-readable complete "
            "n'a ete appliquee. Tous les elements marques [A VALIDER] doivent etre controles humainement."
        ),
        "eligibility": {"eligible": None, "checks": checks},
        "calculation": {
            "status": "missing_inputs",
            "formula_text": formula_text,
            "kwh_cumac": None,
            "unit": "kWh cumac",
            "inputs": {},
            "amount_row": None,
            "r_factor": None,
            "missing_inputs": [],
        },
        "document_check": {"operation_id": operation_id, "fiche_code": fiche_code, "documents": documents},
        "missing_questions": [],
        "risks": risks,
        "sources": sources,
        "no_hallucination": {
            "invented_values": False,
            "unknown_fields": [],
            "rule": "Sans rules.json complet, le dossier reste un brouillon generique et aucun blocking point n'est invente.",
        },
    }


def build_dossier(operation: dict[str, Any]) -> dict[str, Any]:
    fiche_code = get_operation_fiche_code(operation)
    if not fiche_code:
        raise ValueError("Missing fiche_code in operation JSON.")

    support_level = detect_support_level(fiche_code)
    if fiche_code == "BAR-TH-179" and support_level == "supported_full":
        dossier = build_bar_th_179_dossier(operation)
    else:
        dossier = build_generic_draft_dossier(operation, fiche_code, support_level)
    if has_chronology_inputs(operation):
        apply_chronology_result(dossier, validate_chronology(operation))
    apply_documentary_validation(dossier, operation)
    return dossier


def apply_documentary_validation(dossier: dict[str, Any], operation: dict[str, Any]) -> None:
    validation_mode = str(operation.get("dossier_validation_mode") or operation.get("validation_mode") or "advisory")
    engine_mode = "strict" if validation_mode == "strict" else "advisory"
    validation = validate_dossier_cee(operation, mode=engine_mode)
    dossier["document_validations"] = validation["document_validations"]
    dossier["control_matrix"] = validation["control_matrix"]
    dossier["competences_used"] = validation["competences_used"]
    if validation_mode != "strict" or not validation.get("blocking_points"):
        return

    existing_ids = {item.get("id") for item in dossier.get("missing_questions", []) if isinstance(item, dict)}
    for item in validation.get("blocking_points", []):
        question_id = f"validation_{item.get('risk_id') or item.get('id')}"
        if question_id in existing_ids:
            continue
        dossier.setdefault("missing_questions", []).append(
            {
                "id": question_id,
                "field_path": item.get("field", "dossier"),
                "question": item.get("title") or item.get("text") or "Validation documentaire bloquante.",
                "expected_input": "piece source conforme ou justification de non-applicabilite",
                "blocking": True,
            }
        )
        dossier.setdefault("risks", []).append(
            {
                "id": item.get("risk_id") or "documentary_validation_blocking_point",
                "severity": item.get("severity", "high"),
                "text": item.get("title") or item.get("text") or "Validation documentaire bloquante.",
                "source": item.get("source"),
            }
        )
    if dossier.get("status") == "pret_predepot":
        dossier["status"] = "incomplet_questions"
    if isinstance(dossier.get("eligibility"), dict) and dossier["eligibility"].get("eligible") is True:
        dossier["eligibility"]["eligible"] = None


def apply_chronology_result(dossier: dict[str, Any], chronology: dict[str, Any]) -> None:
    dossier["chronology"] = chronology
    for item in chronology.get("blocking_points", []):
        dossier.setdefault("missing_questions", []).append(
            {
                "id": f"chronology_{len(dossier.get('missing_questions', [])) + 1}",
                "field_path": item.get("field", "chronology"),
                "question": item.get("text", "Chronologie documentaire non conforme."),
                "expected_input": "dates ISO AAAA-MM-JJ coherentes avec la chronologie CEE",
                "blocking": True,
            }
        )
        dossier.setdefault("risks", []).append(
            {
                "id": "chronology_blocking_point",
                "severity": item.get("severity", "high"),
                "text": item.get("text", "Chronologie documentaire non conforme."),
                "source": item.get("source"),
            }
        )
    if chronology.get("blocking_points"):
        dossier["status"] = "incomplet_questions" if dossier.get("status") == "pret_predepot" else dossier.get("status", "incomplet_questions")
        if isinstance(dossier.get("eligibility"), dict):
            dossier["eligibility"]["eligible"] = None if dossier["eligibility"].get("eligible") is True else dossier["eligibility"].get("eligible")



def render_markdown(dossier: dict[str, Any]) -> str:
    lines = [
        f"# Dossier CEE pre-depot - {dossier['operation_id']}",
        "",
        f"- Fiche: {dossier['fiche_code']}",
        f"- Statut: {dossier['status']}",
        f"- Synthese: {dossier['summary']}",
        "",
        "## Eligibilite",
    ]
    for check in dossier["eligibility"]["checks"]:
        lines.append(f"- [{check['status']}] {check['label']} - {check.get('detail') or ''}")
    lines.extend(["", "## Calcul"])
    calc = dossier["calculation"]
    lines.append(f"- Statut calcul: {calc['status']}")
    lines.append(f"- Formule: {calc.get('formula_text') or 'non disponible'}")
    if calc.get("kwh_cumac") is not None:
        lines.append(f"- Volume: {calc['kwh_cumac']} kWh cumac")
    if calc.get("missing_inputs"):
        lines.append(f"- Entrees manquantes: {', '.join(calc['missing_inputs'])}")
    lines.extend(["", "## Pieces"])
    for doc in dossier["document_check"]["documents"]:
        lines.append(f"- [{doc['status']}] {doc['label']}")
    lines.extend(["", "## Questions"])
    if dossier["missing_questions"]:
        for question in dossier["missing_questions"]:
            lines.append(f"- {question['question']} ({question['field_path']})")
    else:
        lines.append("- Aucune question bloquante.")
    lines.extend(["", "## Risques"])
    for risk in dossier["risks"]:
        lines.append(f"- [{risk['severity']}] {risk['text']}")
    lines.extend(["", "## Sources"])
    for source in dossier["sources"]:
        page = f", page {source['page']}" if source.get("page") else ""
        section = f", section {source['section']}" if source.get("section") else ""
        lines.append(f"- {source['label']}: `{source['path']}`{page}{section}")
    return "\n".join(lines) + "\n"


def render_questions(dossier: dict[str, Any]) -> str:
    lines = [f"# Questions manquantes - {dossier['operation_id']}", ""]
    if not dossier["missing_questions"]:
        lines.append("Aucune question bloquante.")
    for item in dossier["missing_questions"]:
        lines.append(f"- {item['question']}")
        lines.append(f"  - Champ: `{item['field_path']}`")
        if item.get("expected_input"):
            lines.append(f"  - Attendu: {item['expected_input']}")
    return "\n".join(lines) + "\n"


def render_risks(dossier: dict[str, Any]) -> str:
    lines = [f"# Risques PNCEE - {dossier['operation_id']}", ""]
    for risk in dossier["risks"]:
        lines.append(f"- [{risk['severity']}] {risk['text']}")
    return "\n".join(lines) + "\n"


def render_sources(dossier: dict[str, Any]) -> str:
    lines = [f"# Sources reglementaires - {dossier['operation_id']}", ""]
    for source in dossier["sources"]:
        page = f" page {source['page']}" if source.get("page") else ""
        section = f" section {source['section']}" if source.get("section") else ""
        lines.append(f"- {source['label']}: `{source['path']}`{page}{section}")
    return "\n".join(lines) + "\n"


def write_pack(dossier: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "dossier_predepot.json").write_text(dump_json(dossier), encoding="utf-8")
    (output_dir / "dossier_predepot.md").write_text(render_markdown(dossier), encoding="utf-8")
    (output_dir / "calcul_kwh_cumac.json").write_text(dump_json(dossier["calculation"]), encoding="utf-8")
    (output_dir / "checklist_pieces.json").write_text(dump_json(dossier["document_check"]), encoding="utf-8")
    (output_dir / "questions_manquantes.md").write_text(render_questions(dossier), encoding="utf-8")
    (output_dir / "risques_pncee.md").write_text(render_risks(dossier), encoding="utf-8")
    (output_dir / "sources_reglementaires.md").write_text(render_sources(dossier), encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Generate a strict CEE pre-deposit dossier pack.")
    parser.add_argument("operation_json", help="Path to a client_operation JSON file.")
    parser.add_argument("--output", help="Directory where the local pre-deposit pack will be written.")
    parser.add_argument("--json", action="store_true", help="Print the dossier JSON to stdout.")
    args = parser.parse_args()

    operation = load_json(Path(args.operation_json))
    try:
        dossier = build_dossier(operation)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.output:
        write_pack(dossier, Path(args.output))
    if args.json or not args.output:
        print(dump_json(dossier), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
