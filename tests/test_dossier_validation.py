import copy
import json
from pathlib import Path

import jsonschema

from mcp_server.tools.dossier_validation import validate_quote as validate_quote_tool
from scripts import dossier_agent
from scripts.dossier_validators import (
    run_control_matrix,
    validate_dimensioning_note,
    validate_dossier_cee,
    validate_invoice,
    validate_quote,
)


ROOT = Path(__file__).resolve().parents[1]


def full_dossier():
    return {
        "operation_id": "demo-unified-validation",
        "fiche_code": "BAR-TH-179",
        "operation_type": "standardized",
        "beneficiary": {
            "type": "copropriete",
            "name": "Syndicat Exemple",
            "address": "10 rue Exemple, 69000 Lyon",
        },
        "client": {
            "type": "copropriete",
            "name": "Syndicat Exemple",
            "address": "10 rue Exemple, 69000 Lyon",
        },
        "company": {
            "legal_name": "Installateur Exemple",
            "address": "1 avenue Pro, 69000 Lyon",
            "siret": "12345678900011",
        },
        "professional": {
            "name": "Installateur Exemple",
            "rge_required": True,
            "rge_certificate": "RGE-PAC-001",
        },
        "site": {
            "address": "10 rue Exemple, 69000 Lyon",
            "climate_zone": "H1",
            "building_type": "residentiel_collectif",
            "heated_surface_m2": 2200,
        },
        "operation": {
            "cee_code": "BAR-TH-179",
            "engagement_date": "2026-05-10",
            "completion_date": "2026-09-20",
            "usage": "chauffage_et_ecs",
            "etas_percent": 151,
            "pac_nominal_power_kw": 120,
            "chaufferie_useful_power_after_works_kw": 250,
            "backup_equipment_excluded": True,
            "application_temperature": "moyenne_haute_temperature",
        },
        "quote": {
            "number": "DEV-001",
            "issue_date": "2026-05-01",
            "signature_date": "2026-05-10",
            "signature_present": True,
            "payment_terms": "30 % acompte, solde a reception",
            "total_ht": 420000,
            "total_ttc": 462000,
            "lines": [
                {
                    "description": "Fourniture et pose PAC collective air/eau BAR-TH-179 avec regulation",
                    "quantity": 1,
                    "unit": "forfait",
                    "unit_price_ht": 420000,
                    "total_ht": 420000,
                }
            ],
        },
        "invoice": {
            "number": "FAC-001",
            "issue_date": "2026-09-22",
            "works_completion_date": "2026-09-20",
            "payment_terms": "Paiement a 30 jours",
            "total_ht": 420000,
            "total_ttc": 462000,
            "lines": [
                {
                    "description": "Fourniture et pose PAC collective air/eau BAR-TH-179, modele PAC-AW-120",
                    "quantity": 1,
                    "unit": "forfait",
                    "unit_price_ht": 420000,
                    "total_ht": 420000,
                }
            ],
        },
        "cadre_contribution": {"date": "2026-05-05", "status": "signed"},
        "documents": {
            "cadre_contribution": {"provided": True},
            "quote_or_order": {"provided": True, "signed": True},
            "proof_of_completion": {"provided": True},
            "attestation_honor": {"provided": True},
            "professional_qualification": {"provided": True},
            "annexe6_table": {"provided": True},
            "dimensioning_study": {"provided": True, "signed": True, "dated": True},
        },
        "technical": {
            "pac_brand": "Marque Exemple",
            "pac_reference": "PAC-AW-120",
            "etas_percent": 151,
            "heat_losses_kw_at_tbase": 110,
        },
        "building": {
            "type": "immeuble_collectif",
            "heated_area_m2": 2200,
            "emitters_type": "radiateurs",
        },
        "climate": {
            "t_base_c": -7,
            "t_setpoint_c": 19,
        },
        "generator": {
            "brand": "Marque Exemple",
            "model": "PAC-AW-120",
            "nominal_power_kw": 120,
            "etas_or_eta_percent": 151,
        },
        "boiler_room": {
            "total_useful_power_after_works_kw": 250,
        },
        "calculation": {
            "kwh_cumac": 5542000,
            "heat_losses_kw": 110,
        },
        "date_cadre_contribution": "2026-05-05",
        "date_engagement": "2026-05-10",
        "date_debut_travaux": "2026-05-15",
        "date_facture": "2026-09-20",
        "date_ah_signee": "2026-09-25",
        "date_depot_pncee": "2026-10-15",
        "qualification_rge_validite": "2027-01-01",
    }


def test_dossier_cee_schema_accepts_unified_payload():
    schema = json.loads((ROOT / "schemas" / "dossier_cee.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(full_dossier(), schema)


def test_validate_quote_blocks_unsigned_devis():
    dossier = full_dossier()
    dossier["quote"]["signature_present"] = False

    result = validate_quote(dossier, mode="strict")

    assert result["valid"] is False
    assert any(item["id"] == "quote_signature_not_confirmed" for item in result["blocking_points"])


def test_validate_invoice_blocks_missing_completion_date():
    dossier = full_dossier()
    dossier["invoice"].pop("works_completion_date")
    dossier["operation"].pop("completion_date")
    dossier.pop("date_facture")

    result = validate_invoice(dossier, mode="strict")

    assert result["valid"] is False
    assert "invoice.works_completion_date" in result["missing_fields"]


def test_validate_dimensioning_note_is_required_for_bar_th_179():
    dossier = full_dossier()
    dossier["calculation"].pop("heat_losses_kw")
    dossier["technical"].pop("heat_losses_kw_at_tbase")

    result = validate_dimensioning_note(dossier, mode="strict")

    assert result["required"] is True
    assert result["valid"] is False
    assert "calculation.heat_losses_kw" in result["missing_fields"]


def test_control_matrix_ready_when_all_documents_are_consistent():
    result = run_control_matrix(full_dossier(), mode="strict")

    assert result["status"] == "pret_predepot"
    assert result["blocking_points"] == []
    assert result["valid"] is True


def test_validate_dossier_cee_collects_document_validations():
    result = validate_dossier_cee(full_dossier(), mode="strict")

    assert result["status"] == "pret_predepot"
    assert set(result["document_validations"]) == {"quote", "invoice", "dimensioning_note", "dpt"}
    assert "controle_pncee" in result["competences_used"]


def test_dossier_agent_attaches_advisory_validation_without_changing_legacy_status():
    operation = json.loads((ROOT / "examples" / "dossier_agent" / "bar_th_179_complete.json").read_text(encoding="utf-8"))

    dossier = dossier_agent.build_dossier(operation)

    assert dossier["status"] == "pret_predepot"
    assert "document_validations" in dossier
    assert "control_matrix" in dossier
    assert "devis_cee" in dossier["competences_used"]


def test_dossier_agent_strict_mode_turns_documentary_gaps_into_questions():
    operation = json.loads((ROOT / "examples" / "dossier_agent" / "bar_th_179_complete.json").read_text(encoding="utf-8"))
    operation = copy.deepcopy(operation)
    operation["validation_mode"] = "strict"

    dossier = dossier_agent.build_dossier(operation)

    assert dossier["status"] == "incomplet_questions"
    assert any(item["id"].startswith("validation_") for item in dossier["missing_questions"])


def test_mcp_validate_quote_tool_exposes_same_engine():
    dossier = full_dossier()
    dossier["quote"]["signature_present"] = False

    result = validate_quote_tool("BAR-TH-179", dossier, mode="strict")

    assert result["code"] == "BAR-TH-179"
    assert result["valid"] is False
    assert any(item["field"] == "quote.signature_present" for item in result["blocking_points"])
