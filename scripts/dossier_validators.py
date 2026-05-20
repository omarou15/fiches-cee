"""Shared CEE dossier validation helpers.

The competence engine stores the business/regulatory knowledge. This module
turns that knowledge into deterministic checks over a normalized dossier object.
It deliberately keeps unknown values unknown: missing critical fields become
blocking points in strict mode, never inferred facts.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.validate_operation import has_chronology_inputs, validate_chronology
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from validate_operation import has_chronology_inputs, validate_chronology


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPETENCE_DIR = REPO_ROOT / "competence_engine"
COMPETENCE_PATHS = {
    "devis_cee": COMPETENCE_DIR / "common" / "devis_cee.json",
    "facture_cee": COMPETENCE_DIR / "common" / "facture_cee.json",
    "dpt_cee": COMPETENCE_DIR / "common" / "dpt_cee.json",
    "controle_pncee": COMPETENCE_DIR / "common" / "controle_pncee.json",
    "note_dimensionnement_chauffage": COMPETENCE_DIR / "technical" / "note_dimensionnement_chauffage.json",
}

MISSING_STRINGS = {
    "",
    "unknown",
    "null",
    "none",
    "n/a",
    "na",
    "[a completer]",
    "[a compléter]",
    "a completer",
    "a compléter",
}


FIELD_ALIASES: dict[str, list[str]] = {
    "operation.cee_code": ["operation.cee_code", "fiche_code", "code", "target_code"],
    "dossier.operation_type": ["dossier.operation_type", "operation_type"],
    "beneficiary.identity": ["beneficiary.name", "client.name", "beneficiary.identity.name"],
    "beneficiary.type": ["beneficiary.type", "client.type", "cee.beneficiaire.type"],
    "cee_applicant.identity": ["cee_applicant.identity", "demandeur.raison_sociale", "company.legal_name", "company.name"],
    "company.legal_name": ["company.legal_name", "company.name", "professional.name"],
    "company.address": ["company.address", "professional.address"],
    "company.siret": ["company.siret", "company.siren", "professional.siret", "professional.siren"],
    "client.name": ["client.name", "beneficiary.name"],
    "client.address": ["client.address", "client.adresse", "beneficiary.address"],
    "site.address": ["site.address", "chantier.address", "chantier.adresse", "site.adresse"],
    "quote.number": ["quote.number", "quote.numero", "devis.number", "devis.numero"],
    "quote.issue_date": ["quote.issue_date", "quote.date", "quote.date_edition", "devis.date"],
    "quote.signature_date": [
        "quote.signature_date",
        "quote.date_signature_beneficiaire",
        "quote.signed_at",
        "devis.date_signature_beneficiaire",
        "operation.engagement_date",
        "date_engagement",
    ],
    "quote.signature_present": [
        "quote.signature_present",
        "quote.signature_beneficiaire_present",
        "quote.signed",
        "quote.accepted",
        "documents.quote_or_order.signed",
        "documents.quote_or_order.provided",
    ],
    "quote.lines": ["quote.lines", "devis.lines", "lignes_travaux"],
    "quote.totals": ["quote.totals", "devis.totals", "totaux_devis"],
    "quote.payment_terms": ["quote.payment_terms", "quote.conditions_paiement", "devis.conditions_paiement"],
    "operation.fiche_required_technical_fields": ["operation.fiche_required_technical_fields", "technical.characteristics"],
    "contribution.amount_estimated": [
        "contribution.amount_estimated",
        "contribution.amount",
        "contribution_amount",
        "cee.contribution_financiere.montant_estime_eur_ht",
    ],
    "professional.rge_certificate": [
        "professional.rge_certificate",
        "professional.rge_reference",
        "professional.qualification_document_provided",
        "documents.professional_qualification.provided",
    ],
    "invoice.number": ["invoice.number", "invoice.numero", "facture.number", "facture.numero"],
    "invoice.issue_date": ["invoice.issue_date", "invoice.date", "facture.date", "date_facture"],
    "invoice.works_completion_date": [
        "invoice.works_completion_date",
        "invoice.completion_date",
        "invoice.date_achevement",
        "operation.completion_date",
        "date_facture",
    ],
    "invoice.lines": ["invoice.lines", "facture.lines"],
    "invoice.totals": ["invoice.totals", "facture.totals"],
    "invoice.payment_terms": ["invoice.payment_terms", "invoice.conditions_paiement", "facture.conditions_paiement"],
    "related_quote.number": ["related_quote.number", "invoice.quote_number", "quote.number"],
    "building.type": ["building.type", "site.building_type"],
    "building.heated_area_m2": ["building.heated_area_m2", "site.heated_surface_m2", "heated_surface_m2"],
    "building.emitters_type": ["building.emitters_type", "site.emitters", "operation.emitter_types"],
    "climate.t_base_c": ["climate.t_base_c", "site.base_temperature_c", "tbase_c"],
    "climate.t_setpoint_c": ["climate.t_setpoint_c", "technical.indoor_setpoint_c", "indoor_setpoint_c"],
    "calculation.heat_losses_kw": ["calculation.heat_losses_kw", "technical.heat_losses_kw_at_tbase"],
    "calculation.kwh_cumac": ["calculation.kwh_cumac", "calculation.total_kwh_cumac", "kwh_cumac"],
    "generator.brand": ["generator.brand", "technical.pac_brand", "operation.brand", "brand"],
    "generator.model": ["generator.model", "technical.pac_reference", "operation.reference", "reference"],
    "generator.nominal_power_kw": [
        "generator.nominal_power_kw",
        "generator.pac_nominal_power_kw",
        "operation.pac_nominal_power_kw",
        "technical.pac_power_kw_prated_minus_10",
        "pac_nominal_power_kw",
    ],
    "generator.etas_or_eta_percent": ["generator.etas_or_eta_percent", "operation.etas_percent", "technical.etas_percent", "etas_percent"],
    "generator.brand_model": ["generator.brand_model"],
    "boiler_room.total_useful_power_after_works_kw": [
        "boiler_room.total_useful_power_after_works_kw",
        "operation.chaufferie_useful_power_after_works_kw",
        "technical.chaufferie_useful_power_after_works_kw",
    ],
    "documents.cadre_contribution": ["documents.cadre_contribution.provided", "cadre_contribution.status", "cadre_contribution.date"],
    "documents.engagement_proof": ["documents.engagement_proof.provided", "documents.quote_or_order.provided", "quote.number"],
    "documents.realisation_proof": ["documents.realisation_proof.provided", "documents.proof_of_completion.provided", "invoice.number"],
    "documents.attestation_honneur": ["documents.attestation_honneur.provided", "documents.attestation_honor.provided", "ah.present"],
    "documents.annexe6_table": ["documents.annexe6_table.provided", "annexe6.present"],
    "technical.characteristics": ["technical.characteristics"],
}


TECHNICAL_VALUE_PATHS = [
    "technical.etas_percent",
    "technical.pac_power_kw_prated_minus_10",
    "technical.pac_reference",
    "technical.heat_losses_kw_at_tbase",
    "operation.etas_percent",
    "operation.pac_nominal_power_kw",
    "operation.application_temperature",
    "operation.usage",
    "operation.collector_area_m2",
    "operation.heated_surface_s_m2",
    "generator.nominal_power_kw",
    "generator.model",
    "generator.etas_or_eta_percent",
]


def load_competence(competence_id: str) -> dict[str, Any]:
    path = COMPETENCE_PATHS[competence_id]
    return json.loads(path.read_text(encoding="utf-8"))


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in MISSING_STRINGS
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def get_value(data: dict[str, Any], field: str) -> Any:
    if field == "generator.brand_model":
        brand = get_value(data, "generator.brand")
        model = get_value(data, "generator.model")
        return None if is_missing(brand) or is_missing(model) else f"{brand} {model}"
    if field in {"operation.fiche_required_technical_fields", "technical.characteristics"}:
        return True if has_technical_fields(data) else None
    if field == "quote.totals":
        return get_path(data, "quote.totals") or totals_from(data, "quote")
    if field == "invoice.totals":
        return get_path(data, "invoice.totals") or totals_from(data, "invoice")

    for alias in FIELD_ALIASES.get(field, [field]):
        value = get_path(data, alias)
        if not is_missing(value):
            return value
    return None


def totals_from(data: dict[str, Any], document: str) -> dict[str, Any] | None:
    values = {
        "total_ht": get_path(data, f"{document}.total_ht"),
        "total_tva": get_path(data, f"{document}.total_tva"),
        "total_ttc": get_path(data, f"{document}.total_ttc"),
    }
    if any(not is_missing(value) for value in values.values()):
        return values
    return None


def has_technical_fields(data: dict[str, Any]) -> bool:
    direct = get_path(data, "operation.fiche_required_technical_fields") or get_path(data, "technical.characteristics")
    if not is_missing(direct):
        return True
    return any(not is_missing(get_path(data, path)) for path in TECHNICAL_VALUE_PATHS)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def source_files(*competence_ids: str) -> list[str]:
    files: list[str] = []
    for competence_id in competence_ids:
        path = COMPETENCE_PATHS.get(competence_id)
        if path:
            files.append(path.relative_to(REPO_ROOT).as_posix())
    return files


def issue(
    *,
    issue_id: str,
    document: str,
    field: str,
    text: str,
    severity: str = "high",
    blocking: bool = True,
    source: str | None = None,
    competence_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": issue_id,
        "document": document,
        "field": field,
        "text": text,
        "severity": severity,
        "blocking": blocking,
        "source": source,
        "competence_id": competence_id,
    }


def question_from_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "field_path": item["field"],
        "question": item["text"],
        "expected_input": "valeur exacte issue d'une piece source ou confirmation de non-applicabilite",
        "blocking": bool(item.get("blocking")),
    }


def _field_applicable(data: dict[str, Any], field: str, item: dict[str, Any]) -> bool:
    if field == "professional.rge_certificate":
        return bool(
            get_path(data, "requires_rge")
            or get_path(data, "rge_required")
            or get_path(data, "professional.rge_required")
            or not is_missing(get_value(data, field))
        )
    if field == "contribution.amount_estimated":
        return is_missing(get_value(data, "documents.cadre_contribution"))
    if field == "related_quote.number":
        return not is_missing(get_path(data, "quote")) or not is_missing(get_value(data, field))
    if item.get("if_applicable") and "Si " in str(item.get("if_applicable")):
        return not is_missing(get_value(data, field))
    return True


def validate_required_inputs(
    data: dict[str, Any],
    competence_id: str,
    document: str,
    mode: str = "strict",
    *,
    fields: list[dict[str, Any]] | None = None,
    force_fields: set[str] | None = None,
) -> dict[str, Any]:
    competence = load_competence(competence_id)
    strict_fields = set(competence.get("output_contract", {}).get("strict_mode", {}).get("block_if_missing", []))
    strict_fields.update(force_fields or set())
    checks: list[dict[str, Any]] = []
    blocking_points: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for item in fields if fields is not None else competence.get("required_inputs", []):
        field = item["field"]
        if not _field_applicable(data, field, item):
            checks.append({"id": f"{document}_{slug(field)}", "field": field, "status": "not_applicable"})
            continue

        value = get_value(data, field)
        if is_missing(value):
            must_block = mode == "strict" and (field in strict_fields or item.get("status") == "required")
            target = blocking_points if must_block else warnings
            target.append(
                issue(
                    issue_id=f"{document}_missing_{slug(field)}",
                    document=document,
                    field=field,
                    text=f"{item.get('label', field)} manquant : {item.get('ai_instruction') or item.get('reason') or field}",
                    severity="high" if must_block else "medium",
                    blocking=must_block,
                    source=", ".join(item.get("source_refs") or []),
                    competence_id=competence_id,
                )
            )
            checks.append({"id": f"{document}_{slug(field)}", "field": field, "status": "missing"})
        else:
            checks.append({"id": f"{document}_{slug(field)}", "field": field, "status": "pass"})

    return {
        "document": document,
        "mode": mode,
        "valid": not blocking_points,
        "checks": checks,
        "blocking_points": blocking_points,
        "warnings": warnings,
        "missing_fields": sorted({item["field"] for item in blocking_points + warnings}),
        "competence_id": competence_id,
        "source_files": source_files(competence_id),
    }


def _line_descriptions(lines: Any) -> list[str]:
    if not isinstance(lines, list):
        return []
    descriptions = []
    for item in lines:
        if isinstance(item, dict):
            descriptions.append(str(item.get("description") or item.get("label") or ""))
        else:
            descriptions.append(str(item))
    return [value.strip().lower() for value in descriptions if value.strip()]


def validate_quote(data: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    result = validate_required_inputs(data, "devis_cee", "quote", mode)
    if get_value(data, "quote.signature_present") is not True:
        target = result["blocking_points"] if mode == "strict" else result["warnings"]
        target.append(
            issue(
                issue_id="quote_signature_not_confirmed",
                document="quote",
                field="quote.signature_present",
                text="Le devis doit etre signe ou accepte par le beneficiaire pour prouver l'engagement.",
                severity="high" if mode == "strict" else "medium",
                blocking=mode == "strict",
                source="FAQ_CEE_MTE, ARRETE_2014_09_04",
                competence_id="devis_cee",
            )
        )
    lines = get_value(data, "quote.lines")
    if isinstance(lines, list) and lines:
        descriptions = _line_descriptions(lines)
        if descriptions and all(len(text) < 12 or text in {"travaux", "renovation", "cee"} for text in descriptions):
            result["warnings"].append(
                issue(
                    issue_id="quote_lines_too_vague",
                    document="quote",
                    field="quote.lines",
                    text="Les lignes du devis sont trop generales pour rattacher clairement l'operation a la fiche CEE.",
                    severity="medium",
                    blocking=False,
                    source="FICHE_CEE_SOURCE",
                    competence_id="devis_cee",
                )
            )
    result["valid"] = not result["blocking_points"]
    return result


def validate_invoice(data: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    result = validate_required_inputs(data, "facture_cee", "invoice", mode)
    lines = get_value(data, "invoice.lines")
    descriptions = _line_descriptions(lines)
    if descriptions and all(any(token in text for token in {"travaux", "renovation", "forfait"}) and len(text) < 40 for text in descriptions):
        target = result["blocking_points"] if mode == "strict" else result["warnings"]
        target.append(
            issue(
                issue_id="invoice_too_global",
                document="invoice",
                field="invoice.lines",
                text="Facture trop globale : elle doit detailler les prestations, quantites et informations techniques utiles a la fiche.",
                severity="high" if mode == "strict" else "medium",
                blocking=mode == "strict",
                source="SERVICE_PUBLIC_FACTURE, FICHE_CEE_SOURCE",
                competence_id="facture_cee",
            )
        )
    result["valid"] = not result["blocking_points"]
    return result


def note_requirement_for_code(code: str | None) -> dict[str, Any] | None:
    competence = load_competence("note_dimensionnement_chauffage")
    for item in competence.get("fiche_specific_requirements", []):
        if item.get("code") == code:
            return item
    return None


def validate_dimensioning_note(data: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    code = str(get_value(data, "operation.cee_code") or "").upper() or None
    requirement = note_requirement_for_code(code)
    required = bool(requirement and requirement.get("status") == "explicit_in_fiche")
    if not required and is_missing(get_path(data, "documents.dimensioning_study.provided")):
        return {
            "document": "dimensioning_note",
            "mode": mode,
            "required": False,
            "valid": True,
            "checks": [],
            "blocking_points": [],
            "warnings": [],
            "missing_fields": [],
            "competence_id": "note_dimensionnement_chauffage",
            "source_files": source_files("note_dimensionnement_chauffage"),
            "requirement": requirement,
        }

    competence = load_competence("note_dimensionnement_chauffage")
    result = validate_required_inputs(
        data,
        "note_dimensionnement_chauffage",
        "dimensioning_note",
        mode,
        fields=competence.get("blocking_missing_inputs", []),
    )
    result["required"] = required
    result["requirement"] = requirement

    signed = get_path(data, "documents.dimensioning_study.signed")
    dated = get_path(data, "documents.dimensioning_study.dated")
    if mode == "strict" and required and (signed is not True or dated is not True):
        result["blocking_points"].append(
            issue(
                issue_id="dimensioning_note_not_signed_or_dated",
                document="dimensioning_note",
                field="documents.dimensioning_study",
                text="La note de dimensionnement obligatoire doit etre datee et signee par le professionnel.",
                severity="high",
                blocking=True,
                source="FICHE_CEE_SOURCE",
                competence_id="note_dimensionnement_chauffage",
            )
        )

    heat_losses = get_value(data, "calculation.heat_losses_kw")
    power = get_value(data, "generator.nominal_power_kw")
    if not is_missing(heat_losses) and not is_missing(power):
        try:
            ratio = float(power) / float(heat_losses)
        except (TypeError, ValueError, ZeroDivisionError):
            ratio = None
        if ratio is not None:
            result["dimensioning_ratio"] = round(ratio, 3)
            if ratio < 0.8 or ratio > 1.5:
                result["warnings"].append(
                    issue(
                        issue_id="dimensioning_ratio_needs_review",
                        document="dimensioning_note",
                        field="generator.nominal_power_kw",
                        text="Ratio puissance/deperditions atypique : validation thermicien requise avant conclusion.",
                        severity="medium",
                        blocking=False,
                        source="OPERATOR_PRACTICE_DIMENSIONING",
                        competence_id="note_dimensionnement_chauffage",
                    )
                )

    result["valid"] = not result["blocking_points"]
    return result


def validate_dpt(data: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    result = validate_required_inputs(data, "dpt_cee", "dpt", mode)
    archive_years = get_path(data, "dpt.archive_years") or get_path(data, "archive_years") or get_path(data, "generated_output_mentions_archive_years")
    if archive_years == 6:
        result["warnings"].append(
            issue(
                issue_id="dpt_archive_duration_obsolete",
                document="dpt",
                field="dpt.archive_years",
                text="Le DPT mentionne 6 ans d'archivage ; la base P6 du toolkit retient 9 ans selon R.222-4.",
                severity="medium",
                blocking=False,
                source="CODE_ENERGIE_R222_4",
                competence_id="dpt_cee",
            )
        )
    if get_path(data, "dpt.claims_official_document") is True:
        result["warnings"].append(
            issue(
                issue_id="dpt_claimed_as_official_document",
                document="dpt",
                field="dpt.claims_official_document",
                text="Le DPT doit etre presente comme dossier interne de preuves, pas comme document officiel remplacant les pieces CEE.",
                severity="medium",
                blocking=False,
                source="MTE_MODALITES_DEPOT",
                competence_id="dpt_cee",
            )
        )
    result["valid"] = not result["blocking_points"]
    return result


def chronology_flags(data: dict[str, Any]) -> list[dict[str, Any]]:
    if not has_chronology_inputs(data):
        return []
    chronology = validate_chronology(data)
    flags: list[dict[str, Any]] = []
    for item in chronology.get("blocking_points", []):
        text = str(item.get("text") or "")
        risk_id = "R1_RAI_INVALID_FOR_BENEFICIARY_TYPE"
        if "devis" in text or "travaux" in text:
            risk_id = "R3_TRAVAUX_AVANT_ENGAGEMENT"
        if "12 mois" in text:
            risk_id = "R4_DEPOT_HORS_DELAI"
        if "RGE" in text:
            risk_id = "R5_RGE_EXPIRE_OU_NON_PROUVE"
        flags.append(
            {
                "risk_id": risk_id,
                "title": text,
                "severity": item.get("severity", "high"),
                "blocking": True,
                "source": item.get("source"),
                "field": item.get("field"),
            }
        )
    return flags


def _risk_flag(risk_id: str, title: str, source: str, *, severity: str = "high", field: str | None = None) -> dict[str, Any]:
    return {
        "risk_id": risk_id,
        "title": title,
        "severity": severity,
        "blocking": severity == "high",
        "source": source,
        "field": field,
    }


def run_control_matrix(data: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    quote = validate_quote(data, mode)
    invoice = validate_invoice(data, mode)
    note = validate_dimensioning_note(data, mode)
    dpt = validate_dpt(data, mode)
    validations = {
        "quote": quote,
        "invoice": invoice,
        "dimensioning_note": note,
        "dpt": dpt,
    }

    risk_flags: list[dict[str, Any]] = []
    for item in quote["blocking_points"]:
        risk_id = "R2_DEVIS_NON_SIGNE_OU_NON_DATE" if "signature" in item["field"] else "R11_PIECE_OBLIGATOIRE_ABSENTE"
        risk_flags.append(_risk_flag(risk_id, item["text"], item.get("source") or "devis_cee", field=item["field"]))
    for item in invoice["blocking_points"]:
        risk_flags.append(_risk_flag("R9_FACTURE_NON_CONFORME", item["text"], item.get("source") or "facture_cee", field=item["field"]))
    for item in note["blocking_points"]:
        risk_flags.append(_risk_flag("R11_PIECE_OBLIGATOIRE_ABSENTE", item["text"], item.get("source") or "note_dimensionnement_chauffage", field=item["field"]))
    for item in dpt["blocking_points"]:
        risk_flags.append(_risk_flag("R11_PIECE_OBLIGATOIRE_ABSENTE", item["text"], item.get("source") or "dpt_cee", field=item["field"]))
    risk_flags.extend(chronology_flags(data))

    if get_path(data, "duplicate_detected") is True:
        risk_flags.append(_risk_flag("R12_NON_CUMUL_INCOHERENT", "Doublon ou double valorisation detecte.", "controle_pncee"))
    if get_path(data, "beneficiary_or_site_mismatch_between_documents") is True:
        risk_flags.append(_risk_flag("R7_INCOHERENCE_IDENTITE_ADRESSE", "Incoherence beneficiaire ou adresse entre pieces.", "controle_pncee"))
    if get_path(data, "strong_fraud_signals") is True:
        risk_flags.append(_risk_flag("R22_SIGNAUX_FRAUDE_OU_FAUX_TRAVAUX", "Signaux forts a escalader en revue humaine.", "controle_pncee"))

    warnings = []
    for validation in validations.values():
        warnings.extend(validation.get("warnings", []))

    blocking_points = [flag for flag in risk_flags if flag.get("blocking")]
    status = "pret_predepot"
    if blocking_points:
        status = "incomplet_questions"
    elif any(item.get("severity") in {"medium", "high"} for item in warnings):
        status = "a_risque"

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": mode,
        "status": status,
        "valid": not blocking_points,
        "risk_flags": risk_flags,
        "blocking_points": blocking_points,
        "warnings": warnings,
        "document_validations": validations,
        "competence_id": "controle_pncee",
        "source_files": source_files("controle_pncee", "devis_cee", "facture_cee", "note_dimensionnement_chauffage", "dpt_cee"),
    }


def validate_dossier_cee(data: dict[str, Any], mode: str = "strict") -> dict[str, Any]:
    payload = deepcopy(data or {})
    matrix = run_control_matrix(payload, mode)
    return {
        "generated_at": matrix["generated_at"],
        "mode": mode,
        "status": matrix["status"],
        "valid": matrix["valid"],
        "blocking_points": matrix["blocking_points"],
        "warnings": matrix["warnings"],
        "document_validations": matrix["document_validations"],
        "control_matrix": {
            "status": matrix["status"],
            "risk_flags": matrix["risk_flags"],
            "source_files": matrix["source_files"],
        },
        "competences_used": ["devis_cee", "facture_cee", "note_dimensionnement_chauffage", "dpt_cee", "controle_pncee"],
        "needs_human_review": bool(matrix["blocking_points"] or matrix["warnings"]),
        "no_hallucination": {
            "invented_values": False,
            "rule": "Les champs absents restent manquants et sont remontes en questions ou risques.",
        },
    }
