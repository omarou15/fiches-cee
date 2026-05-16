"""Generate strict CEE pre-deposit packs from client operation JSON.

The V1 dossier agent intentionally supports BAR-TH-179 only. It never invents
missing values: absent inputs become blocking questions and the dossier cannot
be marked ready for pre-deposit.
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
SUPPORTED_FICHE_CODES = {"BAR-TH-179"}

BAR_TH_179_SOURCE = "Residentiel_BAR/BAR-TH-179 vA81-2 à compter du 30-04-2026.pdf"
BAR_TH_179_EFFECTIVE_DATE = "2026-04-30"
BAR_TH_179_ENGAGEMENT_DEADLINE = "2030-12-31"


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
            return None
        current = current.get(part)
    return current


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
) -> None:
    value = get_path(operation, path)
    if value is True:
        add_check(checks, check_id, label, "pass", "Confirme dans les donnees client.")
    elif value is False:
        add_check(checks, check_id, label, "fail", fail_detail)
    else:
        add_check(checks, check_id, label, "missing", "Information non fournie.")
        add_question(questions, f"missing_{check_id}", path, missing_question, "true/false ou document justificatif")


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


def evaluate_document(
    operation: dict[str, Any],
    questions: list[dict[str, Any]],
    doc_id: str,
    label: str,
    required: bool = True,
    required_flags: list[str] | None = None,
    source: str | None = BAR_TH_179_SOURCE,
) -> dict[str, Any]:
    doc = (operation.get("documents") or {}).get(doc_id)
    if not required:
        return {"id": doc_id, "label": label, "required": False, "status": "not_required", "issues": [], "source": source}

    if not isinstance(doc, dict) or is_missing(doc.get("provided")):
        add_question(questions, f"missing_doc_{doc_id}", f"documents.{doc_id}", f"Merci de fournir : {label}.", "document ou confirmation explicite")
        return {"id": doc_id, "label": label, "required": True, "status": "missing", "issues": ["Document non fourni."], "source": source}

    if doc.get("provided") is not True:
        add_question(questions, f"missing_doc_{doc_id}", f"documents.{doc_id}", f"Merci de fournir : {label}.", "document requis")
        return {"id": doc_id, "label": label, "required": True, "status": "missing", "issues": ["Document absent."], "source": source}

    issues: list[str] = []
    for flag in required_flags or []:
        value = doc.get(flag)
        if value is not True:
            issues.append(f"Champ documentaire non conforme ou non confirme : {flag}.")
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
    )

    engagement = parse_iso_date(get_path(operation, "operation.engagement_date"))
    effective = parse_iso_date(BAR_TH_179_EFFECTIVE_DATE)
    deadline = parse_iso_date(BAR_TH_179_ENGAGEMENT_DEADLINE)
    if engagement is None:
        add_check(checks, "engagement_date", "Date d'engagement", "missing", "Date non fournie.")
        add_question(questions, "missing_engagement_date", "operation.engagement_date", "Quelle est la date d'engagement de l'operation ?", "date ISO AAAA-MM-JJ")
    elif effective and deadline and effective <= engagement <= deadline:
        add_check(checks, "engagement_date", "Date d'engagement", "pass", "Date dans la periode BAR-TH-179 vA81-2.")
    else:
        add_check(checks, "engagement_date", "Date d'engagement", "fail", "Date hors periode applicable BAR-TH-179 vA81-2.")

    usage = normalize_usage(get_path(operation, "operation.usage"))
    if usage == "unknown":
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
        add_check(checks, "pac_type", "Type de PAC", "missing", "Type de PAC non fourni.")
        add_question(questions, "missing_pac_type", "operation.pac_type", "La PAC est-elle bien de type air/eau ?", "air_eau")
    elif pac_type == "air_eau":
        add_check(checks, "pac_type", "Type de PAC", "pass", "PAC air/eau.")
    else:
        add_check(checks, "pac_type", "Type de PAC", "fail", "BAR-TH-179 exige une PAC air/eau.")

    pac_power = get_path(operation, "operation.pac_nominal_power_kw")
    if is_missing(pac_power):
        add_check(checks, "pac_power_max", "Puissance nominale PAC <= 400 kW", "missing", "Puissance PAC non fournie.")
        add_question(questions, "missing_pac_nominal_power", "operation.pac_nominal_power_kw", "Quelle est la puissance thermique nominale Prated a -10 deg C de la PAC ?", "kW")
    elif float(pac_power) <= 400:
        add_check(checks, "pac_power_max", "Puissance nominale PAC <= 400 kW", "pass", f"Puissance fournie : {pac_power} kW.")
    else:
        add_check(checks, "pac_power_max", "Puissance nominale PAC <= 400 kW", "fail", f"Puissance fournie : {pac_power} kW.")

    application = normalize_application(get_path(operation, "operation.application_temperature"))
    etas = get_path(operation, "operation.etas_percent")
    if application == "unknown":
        add_check(checks, "application_temperature", "Application basse / moyenne-haute temperature", "missing", "Application non fournie.")
        add_question(questions, "missing_application_temperature", "operation.application_temperature", "L'application PAC est-elle basse temperature ou moyenne/haute temperature ?", "basse_temperature | moyenne_haute_temperature")
    elif usage == "chauffage_et_ecs" and application != "moyenne_haute_temperature":
        add_check(checks, "application_temperature", "Application basse / moyenne-haute temperature", "fail", "Pour chauffage + ECS, la fiche retient une application moyenne/haute temperature.")
    else:
        add_check(checks, "application_temperature", "Application basse / moyenne-haute temperature", "pass", f"Application retenue : {application}.")

    if is_missing(etas):
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
    )

    uses_bar_th_169 = get_path(operation, "non_cumulation.uses_bar_th_169")
    if uses_bar_th_169 is True and usage == "chauffage_et_ecs":
        add_check(checks, "non_cumulation_bar_th_169", "Non-cumul BAR-TH-169", "fail", "Non-cumul detecte avec BAR-TH-169 pour chauffage + ECS.")
    elif uses_bar_th_169 is False:
        add_check(checks, "non_cumulation_bar_th_169", "Non-cumul BAR-TH-169", "pass", "Aucun cumul BAR-TH-169 declare.")
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
    )

    documents = [
        evaluate_document(
            operation,
            questions,
            "dimensioning_study",
            "Etude prealable de dimensionnement datee, signee et remise au beneficiaire",
            required_flags=["signed", "dated", "given_at_engagement"],
        ),
        evaluate_document(operation, questions, "proof_of_completion", "Preuve de realisation mentionnant marque, reference, Prated, usage, application et Etas"),
        evaluate_document(operation, questions, "professional_qualification", "Decision de qualification ou certification du professionnel"),
        evaluate_document(operation, questions, "manufacturer_datasheet", "Document fabricant ou equivalent pour verifier PAC, Prated et Etas"),
        evaluate_document(operation, questions, "attestation_honor", "Attestation sur l'honneur CEE"),
        evaluate_document(operation, questions, "quote_or_order", "Devis, bon de commande ou preuve d'engagement"),
        evaluate_document(operation, questions, "invoice", "Facture ou preuve de realisation finale"),
    ]
    document_check = {"operation_id": operation["operation_id"], "fiche_code": operation["fiche_code"], "documents": documents}

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
    bad_docs = [doc for doc in documents if doc["status"] in {"missing", "non_conform", "unknown"} and doc["required"]]

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
        "operation_id": operation["operation_id"],
        "fiche_code": operation["fiche_code"],
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


def build_dossier(operation: dict[str, Any]) -> dict[str, Any]:
    fiche_code = operation.get("fiche_code")
    if fiche_code not in SUPPORTED_FICHE_CODES:
        raise ValueError(f"Unsupported fiche_code for dossier V1: {fiche_code}. Supported: {sorted(SUPPORTED_FICHE_CODES)}")
    return build_bar_th_179_dossier(operation)


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
