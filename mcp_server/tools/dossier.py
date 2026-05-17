from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from mcp_server.tools.calcul import compute_kwh_cumac
from mcp_server.tools.eligibility import check_eligibility, normalize_operation_for_agent
from mcp_server.utils.loader import (
    FicheNotFoundError,
    error_response,
    existing_source_files,
    load_curated,
    load_extracted_json,
    load_rules,
    require_known_code,
)
from mcp_server.utils.paths import REPO_ROOT


def _blocking_texts(eligibility: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for item in eligibility.get("blocking_points") or []:
        if isinstance(item, dict):
            values.append(str(item.get("text") or item.get("question") or item.get("field") or item.get("field_path") or item.get("id")))
        else:
            values.append(str(item))
    return [value for value in values if value]


def _operation_input_from_mcp(code: str, operation: dict[str, Any], dossier: dict[str, Any], kwh_cumac: Any) -> dict[str, Any]:
    if isinstance(operation.get("operation"), dict) and isinstance(operation.get("client"), dict):
        prepared = dict(operation)
        prepared.setdefault("compliance", {})
        prepared.setdefault("documents", {})
        prepared.setdefault("calculation", {})
        prepared["operation"]["cee_code"] = prepared["operation"].get("cee_code") or code
        prepared["compliance"]["eligibility_status"] = dossier.get("status")
        prepared["compliance"]["blocking_points"] = _blocking_texts({"blocking_points": dossier.get("blocking_points", [])})
        prepared["calculation"]["total_kwh_cumac"] = prepared["calculation"].get("total_kwh_cumac") or kwh_cumac
        return prepared

    site = operation.get("site") if isinstance(operation.get("site"), dict) else {}
    client = operation.get("client") if isinstance(operation.get("client"), dict) else {}
    technical = operation.get("technical") if isinstance(operation.get("technical"), dict) else {}
    return {
        "operation": {
            "case_id": operation.get("case_id") or operation.get("operation_id") or f"MCP-{code}",
            "cee_code": code,
            "description": operation.get("description") or "Operation generee depuis une requete MCP.",
            "engagement_date": operation.get("engagement_date") or "[A COMPLETER]",
            "completion_date": operation.get("completion_date"),
            "status": "draft_from_mcp",
        },
        "client": {
            "name": client.get("name") or operation.get("client_name") or "[A COMPLETER]",
            "type": client.get("type") or "[A COMPLETER]",
            "contact_name": client.get("contact_name") or "[A COMPLETER]",
            "email": client.get("email") or operation.get("client_email") or "[A COMPLETER]",
            "phone": client.get("phone") or "[A COMPLETER]",
            "address": client.get("address") or "[A COMPLETER]",
        },
        "site": {
            "address": site.get("address") or operation.get("site_address") or "[A COMPLETER]",
            "postal_code": site.get("postal_code") or operation.get("postal_code") or "[A COMPLETER]",
            "city": site.get("city") or operation.get("city") or "[A COMPLETER]",
            "climate_zone": operation.get("climate_zone") or operation.get("zone") or site.get("climate_zone") or "[A COMPLETER]",
            "building_type": operation.get("building_type") or site.get("building_type") or "[A COMPLETER]",
            "apartments_count": operation.get("apartment_count") or operation.get("apartment_count_heated_by_pac"),
            "heated_surface_m2": operation.get("heated_surface_m2"),
            "emitters": operation.get("emitters") or "[A COMPLETER]",
            "base_temperature_c": operation.get("tbase_c"),
        },
        "technical": {
            "usage": operation.get("usage") or technical.get("usage") or "[A COMPLETER]",
            "equipment_description": operation.get("pac_type") or technical.get("equipment_description") or "[A COMPLETER]",
            "brand": operation.get("brand") or "[A COMPLETER]",
            "reference": operation.get("reference") or "[A COMPLETER]",
            "performance_value": operation.get("etas") or operation.get("etas_percent") or technical.get("etas_percent") or "[A COMPLETER]",
            "etas_percent": operation.get("etas") or operation.get("etas_percent") or technical.get("etas_percent"),
            "application_temperature": operation.get("application_temperature") or technical.get("application_temperature") or "[A COMPLETER]",
            "pac_power_kw_prated_minus_10": operation.get("pac_nominal_power_kw") or operation.get("pac_power_kw"),
            "chaufferie_useful_power_after_works_kw": operation.get("chaufferie_useful_power_after_works_kw"),
            "backup_equipment_excluded": operation.get("backup_equipment_excluded"),
            "r_factor": operation.get("r_factor"),
            "notes": "Donnees MCP a valider avant signature.",
        },
        "calculation": {
            "formula_text": dossier.get("calculation", {}).get("formula_text"),
            "total_kwh_cumac": kwh_cumac,
            "status": dossier.get("calculation", {}).get("status"),
        },
        "quote": {
            "number": f"DRAFT-{operation.get('case_id') or code}",
            "date": "[A COMPLETER]",
            "status": "document genere automatiquement a valider",
            "total_ht": operation.get("total_ht"),
            "total_ttc": operation.get("total_ttc"),
            "lines": operation.get("quote_lines") or [],
        },
        "invoice": {
            "number": f"DRAFT-FAC-{operation.get('case_id') or code}",
            "date": "[A COMPLETER]",
            "status": "brouillon a remplacer par facture finale",
            "total_ht": operation.get("total_ht"),
            "total_ttc": operation.get("total_ttc"),
            "lines": operation.get("quote_lines") or [],
        },
        "documents": {
            "available": operation.get("available_documents") or [],
            "missing": _blocking_texts({"blocking_points": dossier.get("missing_questions", [])}),
            "non_compliant": [],
        },
        "compliance": {
            "eligibility_status": dossier.get("status"),
            "blocking_points": _blocking_texts({"blocking_points": dossier.get("missing_questions", [])}),
            "risks": [str(item.get("text")) for item in dossier.get("risks", []) if isinstance(item, dict) and item.get("text")],
        },
        "mail": {
            "recipient": client.get("email") or operation.get("client_email") or "[A COMPLETER]",
            "subject": f"Pieces manquantes dossier CEE {code}",
            "sender_name": "[A COMPLETER]",
        },
    }


def generate_dossier(code: str, operation: dict[str, Any], company: dict[str, Any], mode: str = "draft") -> dict[str, Any]:
    """Generate an inline CEE document pack from operation and company data."""
    try:
        normalized_code = require_known_code(code)
    except FicheNotFoundError as exc:
        return error_response(exc.code)

    from document_engine.generators.generate_document_pack import generate_pack_from_operation
    from scripts import dossier_agent

    rules, rules_path = load_rules(normalized_code)
    curated, curated_path = load_curated(normalized_code)
    extracted, extracted_path = load_extracted_json(normalized_code)
    source_files = existing_source_files(rules_path, curated_path, extracted_path)

    prepared_for_agent = normalize_operation_for_agent(normalized_code, operation)
    dossier = dossier_agent.build_dossier(prepared_for_agent)
    variables = dict(operation)
    if isinstance(operation.get("operation"), dict):
        variables.update(operation["operation"])
    if isinstance(operation.get("site"), dict):
        variables.update(operation["site"])
    kwh = compute_kwh_cumac(normalized_code, variables)
    blocking_points = [
        item.get("question") or item.get("field_path")
        for item in dossier.get("missing_questions", [])
        if isinstance(item, dict)
    ]
    if mode == "strict" and (blocking_points or dossier.get("status") != "pret_predepot"):
        return {
            "code": normalized_code,
            "status": "blocked",
            "blocking_points": [point for point in blocking_points if point],
            "documents": {},
            "kwh_cumac": kwh.get("kwh_cumac"),
            "warnings": ["Strict mode blocked generation because the dossier is not pret_predepot."],
            "source_files": source_files,
        }

    operation_input = _operation_input_from_mcp(normalized_code, operation, dossier, kwh.get("kwh_cumac"))
    with tempfile.TemporaryDirectory(prefix="cee_mcp_pack_") as tmp:
        output_dir = Path(tmp)
        manifest = generate_pack_from_operation(company, operation_input, normalized_code, output_dir, mode)
        documents: dict[str, str] = {}
        for rel_path in manifest.get("files", []):
            path = output_dir / rel_path
            if path.exists() and path.suffix.lower() == ".md":
                documents[rel_path] = path.read_text(encoding="utf-8")
        manifest_path = output_dir / "dossier_manifest.json"
        if manifest_path.exists():
            documents["dossier_manifest.json"] = manifest_path.read_text(encoding="utf-8")

    status = dossier.get("status")
    if status in {"incomplet_questions", "non_eligible"} and mode == "draft":
        response_status = "draft"
    else:
        response_status = status or "draft"
    return {
        "code": normalized_code,
        "status": response_status,
        "blocking_points": [point for point in blocking_points if point],
        "documents": documents,
        "kwh_cumac": kwh.get("kwh_cumac"),
        "warnings": [warning.get("text") or warning.get("message") for warning in check_eligibility(normalized_code, operation).get("warnings", [])],
        "source_files": source_files,
    }


def get_cadre_contribution(code: str, operation: dict[str, Any], company: dict[str, Any]) -> dict[str, Any]:
    """Render the annexe 8 contribution frame as Markdown."""
    try:
        normalized_code = require_known_code(code)
    except FicheNotFoundError as exc:
        return error_response(exc.code)
    from document_engine.generators.generate_document_pack import load_fiche
    from document_engine.generators.render_template import build_context, render_string

    template_path = REPO_ROOT / "document_engine" / "templates" / "cadre_contribution" / "cadre_contribution_generic.md"
    prepared_operation = _operation_input_from_mcp(normalized_code, operation, {}, None)
    fiche = load_fiche(normalized_code)
    markdown = render_string(template_path.read_text(encoding="utf-8"), build_context(company, prepared_operation, normalized_code, fiche))
    return {
        "code": normalized_code,
        "document": markdown,
        "source_files": [template_path.relative_to(REPO_ROOT).as_posix()],
    }


def _get_nested(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def get_annexe6_row(code: str, operation: dict[str, Any]) -> dict[str, Any]:
    """Return the annexe 6 recap row for an operation."""
    try:
        normalized_code = require_known_code(code)
    except FicheNotFoundError as exc:
        return error_response(exc.code)
    curated, curated_path = load_curated(normalized_code)
    extracted, extracted_path = load_extracted_json(normalized_code)
    fiche = extracted or curated or {}
    op = operation.get("operation", {}) if isinstance(operation.get("operation"), dict) else operation
    client = operation.get("client", {}) if isinstance(operation.get("client"), dict) else {}
    site = operation.get("site", {}) if isinstance(operation.get("site"), dict) else {}
    company = operation.get("company", {}) if isinstance(operation.get("company"), dict) else {}
    technical = operation.get("technical", {}) if isinstance(operation.get("technical"), dict) else {}
    invoice = operation.get("invoice", {}) if isinstance(operation.get("invoice"), dict) else {}
    calculation = operation.get("calculation", {}) if isinstance(operation.get("calculation"), dict) else {}
    compliance = operation.get("compliance", {}) if isinstance(operation.get("compliance"), dict) else {}
    contribution = operation.get("contribution", {}) if isinstance(operation.get("contribution"), dict) else {}

    row = {
        "reference_interne_demandeur": op.get("case_id") or operation.get("case_id"),
        "code_fiche": normalized_code,
        "secteur": fiche.get("sector"),
        "beneficiaire_nom": client.get("name") or operation.get("client_name"),
        "beneficiaire_adresse_complete": ", ".join(str(part) for part in [site.get("address"), site.get("postal_code"), site.get("city")] if part),
        "beneficiaire_telephone": client.get("phone"),
        "beneficiaire_email": client.get("email"),
        "beneficiaire_siret_si_pm": client.get("siret"),
        "date_engagement": op.get("engagement_date") or operation.get("date_engagement"),
        "date_achevement": invoice.get("date") or op.get("completion_date") or operation.get("date_facture"),
        "montant_kwh_cumac": calculation.get("total_kwh_cumac") or operation.get("kwh_cumac"),
        "professionnel_raison_sociale": company.get("legal_name") or operation.get("professional_name"),
        "professionnel_siret": company.get("siret") or operation.get("professional_siret"),
        "qualification_rge_reference": technical.get("professional_qualification") or operation.get("rge_reference"),
        "qualification_rge_organisme": technical.get("rge_qualifier") or operation.get("rge_qualifier"),
        "qualification_rge_validite": technical.get("rge_valid_until") or operation.get("qualification_rge_validite"),
        "montant_contribution_eur": contribution.get("amount") or operation.get("contribution_amount"),
        "precarite_energetique": compliance.get("precarity_status") or "non",
        "coup_de_pouce": compliance.get("coup_de_pouce_status") or "non",
        "type_coup_de_pouce": compliance.get("coup_de_pouce_type"),
    }
    return {
        "code": normalized_code,
        "annexe6_row": row,
        "source_files": existing_source_files(curated_path, extracted_path),
    }
