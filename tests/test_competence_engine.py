import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "competence_engine" / "schemas" / "competence.schema.json"
COMPETENCE_ROOT = ROOT / "competence_engine"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_competences_validate_schema():
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    competence_files = [
        path
        for path in COMPETENCE_ROOT.rglob("*.json")
        if "schemas" not in path.parts and path.name != "index.json"
    ]
    assert competence_files

    for path in competence_files:
        data = load_json(path)
        errors = sorted(validator.iter_errors(data), key=lambda err: err.path)
        assert not errors, f"{path}: {[error.message for error in errors]}"


def test_competence_index_points_to_existing_files():
    index = load_json(COMPETENCE_ROOT / "index.json")
    entries = index["competences"]
    assert entries
    for entry in entries:
        assert (ROOT / entry["path"]).exists()


def test_local_private_corpus_is_not_leaked_in_competences():
    scanned_files = list(COMPETENCE_ROOT.rglob("*.json")) + list((ROOT / "external_knowledge").rglob("*"))
    scanned_files = [path for path in scanned_files if path.is_file()]
    forbidden = [
        "C:\\Users\\omaro",
        "ENERGY" + "CO",
        "Energy" + "co",
        "energy" + "co_rag_base",
    ]

    for path in scanned_files:
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in text, f"{path} leaks private marker {marker}"


def test_private_corpus_example_requires_official_confirmation():
    config = load_json(ROOT / "external_knowledge" / "examples" / "local_corpus.example.json")

    assert config["visibility"] == "private_local_only"
    assert "absolute_local_path" in config["forbidden_outputs"]
    assert "legal_requirement" in config["source_policy"]["requires_official_confirmation_for"]
    assert "thermal_calculation" in config["source_policy"]["requires_professional_validation_for"]


def test_devis_cee_distinguishes_official_and_operator_practice():
    devis = load_json(COMPETENCE_ROOT / "common" / "devis_cee.json")
    source_types = {source["type"] for source in devis["source_references"]}

    assert "official" in source_types
    assert "legal_text" in source_types
    assert "operator_practice" in source_types
    assert devis["status"] == "draft_from_user_research"
    assert devis["source_policy"]["no_hallucination_rules"]


def test_devis_cee_has_core_blocking_fields():
    devis = load_json(COMPETENCE_ROOT / "common" / "devis_cee.json")
    fields = {item["field"] for item in devis["required_inputs"]}
    blocking_fields = {item["field"] for item in devis["blocking_missing_inputs"]}

    assert "quote.signature_date" in fields
    assert "quote.signature_present" in fields
    assert "site.address" in fields
    assert "operation.cee_code" in fields
    assert "operation.fiche_required_technical_fields" in fields
    assert "quote.signature_date" in blocking_fields
    assert "operation.cee_code" in blocking_fields


def test_devis_cee_has_cee_chronology_controls():
    devis = load_json(COMPETENCE_ROOT / "common" / "devis_cee.json")
    check_ids = {check["id"] for check in devis["chronology_checks"]}

    assert "chronology_rai_pp_copro" in check_ids
    assert "chronology_rai_pm" in check_ids
    assert "chronology_works_after_engagement" in check_ids
    assert "chronology_rge_at_engagement" in check_ids


def test_devis_cee_has_high_risk_rejection_matrix():
    devis = load_json(COMPETENCE_ROOT / "common" / "devis_cee.json")
    high_risks = {
        risk["id"]
        for risk in devis["compliance_risks"]
        if risk["severity"] == "high" and risk["blocking"]
    }

    assert "devis_absent_or_unsigned" in high_risks
    assert "rai_not_secured" in high_risks
    assert "works_before_engagement" in high_risks
    assert "fiche_or_technical_fields_missing" in high_risks


def test_facture_cee_distinguishes_official_and_operator_practice():
    facture = load_json(COMPETENCE_ROOT / "common" / "facture_cee.json")
    source_types = {source["type"] for source in facture["source_references"]}

    assert "official" in source_types
    assert "legal_text" in source_types
    assert "operator_practice" in source_types
    assert facture["status"] == "draft_from_user_research"
    assert facture["source_policy"]["no_hallucination_rules"]


def test_facture_cee_has_core_blocking_fields():
    facture = load_json(COMPETENCE_ROOT / "common" / "facture_cee.json")
    fields = {item["field"] for item in facture["required_inputs"]}
    blocking_fields = {item["field"] for item in facture["blocking_missing_inputs"]}

    assert "invoice.number" in fields
    assert "invoice.issue_date" in fields
    assert "invoice.works_completion_date" in fields
    assert "site.address" in fields
    assert "operation.fiche_required_technical_fields" in fields
    assert "invoice.works_completion_date" in blocking_fields
    assert "operation.fiche_required_technical_fields" in blocking_fields


def test_facture_cee_has_cee_chronology_controls():
    facture = load_json(COMPETENCE_ROOT / "common" / "facture_cee.json")
    check_ids = {check["id"] for check in facture["chronology_checks"]}

    assert "chronology_invoice_after_engagement" in check_ids
    assert "chronology_ah_after_invoice_completion" in check_ids
    assert "chronology_deposit_within_12_months" in check_ids
    assert "chronology_rge_at_engagement" in check_ids


def test_facture_cee_has_high_risk_rejection_matrix():
    facture = load_json(COMPETENCE_ROOT / "common" / "facture_cee.json")
    high_risks = {
        risk["id"]
        for risk in facture["compliance_risks"]
        if risk["severity"] == "high" and risk["blocking"]
    }

    assert "invoice_missing_final_invoice" in high_risks
    assert "invoice_too_global" in high_risks
    assert "technical_mentions_missing" in high_risks
    assert "completion_after_deposit_deadline" in high_risks


def test_note_dimensionnement_has_professional_validation_rules():
    note = load_json(COMPETENCE_ROOT / "technical" / "note_dimensionnement_chauffage.json")

    assert note["category"] == "technical_method"
    assert note["professional_validation"]["required"] is True
    assert "Tbase retenue" in note["professional_validation"]["must_validate"]
    assert "signature/cachet" in note["professional_validation"]["signature_block"]


def test_note_dimensionnement_has_estimation_and_official_methods():
    note = load_json(COMPETENCE_ROOT / "technical" / "note_dimensionnement_chauffage.json")
    methods = {method["id"]: method for method in note["calculation_methods"]}

    assert methods["heat_loss_simple_gvdt"]["status"] == "estimation"
    assert methods["bar_th_179_factor_r"]["status"] == "official_or_fiche"
    assert "Ne doit pas etre presentee comme calcul EN 12831." in methods["heat_loss_simple_gvdt"]["limits"]


def test_note_dimensionnement_has_bar_th_179_factor_r_controls():
    note = load_json(COMPETENCE_ROOT / "technical" / "note_dimensionnement_chauffage.json")
    consistency_ids = {check["id"] for check in note["consistency_checks"]}
    risk_ids = {risk["id"] for risk in note["compliance_risks"]}

    assert "bar_th_179_factor_r_consistency" in consistency_ids
    assert "bar_th_179_wrong_factor_r" in risk_ids
    assert "BAR-TH-179" in note["applies_to"]


def test_note_dimensionnement_does_not_mark_solar_as_systematic():
    note = load_json(COMPETENCE_ROOT / "technical" / "note_dimensionnement_chauffage.json")
    requirements = {item["code"]: item for item in note["fiche_specific_requirements"]}

    assert requirements["BAR-TH-168"]["status"] == "to_confirm"
    assert requirements["BAT-TH-116"]["status"] == "not_systematic"


def test_new_technical_competences_are_indexed():
    index = load_json(COMPETENCE_ROOT / "index.json")
    indexed_ids = {entry["id"] for entry in index["competences"]}

    assert {
        "pac_hydraulic_integration",
        "building_heat_losses",
        "ecs_dimensioning",
        "gtb_bacs_method",
        "audit_nf_en_16247",
        "cvc_cost_estimation",
    } <= indexed_ids


def test_pac_hydraulic_integration_blocks_catalog_power_at_tbase():
    pac = load_json(COMPETENCE_ROOT / "technical" / "pac_hydraulic_integration.json")
    method_ids = {method["id"] for method in pac["calculation_methods"]}
    risk_ids = {risk["id"] for risk in pac["compliance_risks"]}
    blocking_fields = {item["field"] for item in pac["blocking_missing_inputs"]}

    assert "power_derating_at_tbase" in method_ids
    assert "buffer_tank_volume_estimate" in method_ids
    assert "catalog_power_used_as_tbase_power" in risk_ids
    assert "generator.power_at_tbase_kw" in blocking_fields
    assert any("A7/W35" in rule for rule in pac["source_policy"]["no_hallucination_rules"])


def test_building_heat_losses_has_core_formulas_and_r_u_guardrail():
    heat = load_json(COMPETENCE_ROOT / "technical" / "building_heat_losses.json")
    methods = {method["id"]: method for method in heat["calculation_methods"]}
    risk_ids = {risk["id"] for risk in heat["compliance_risks"]}
    check_ids = {check["id"] for check in heat["validation_checks"]}

    assert methods["r_value_from_lambda"]["formula_or_method"] == "R = e / lambda."
    assert "U = 1 /" in methods["u_value_from_r_sum"]["formula_or_method"]
    assert "Q_W = U x A x DeltaT." in methods["transmission_losses"]["formula_or_method"]
    assert "wrong_unit_r_u" in risk_ids
    assert "r_and_u_not_confused" in check_ids


def test_ecs_dimensioning_tracks_legionella_and_low_temp_sources():
    ecs = load_json(COMPETENCE_ROOT / "technical" / "ecs_dimensioning.json")
    method_ids = {method["id"] for method in ecs["calculation_methods"]}
    risk_ids = {risk["id"] for risk in ecs["compliance_risks"]}
    check_ids = {check["id"] for check in ecs["validation_checks"]}

    assert {"v60_conversion", "instant_power", "storage_volume", "accumulation_power"} <= method_ids
    assert "legionella_risk_unaddressed" in risk_ids
    assert "post_heating_for_low_temp_source" in check_ids


def test_gtb_bacs_method_requires_class_evidence_not_guessing():
    gtb = load_json(COMPETENCE_ROOT / "technical" / "gtb_bacs_method.json")
    risk_ids = {risk["id"] for risk in gtb["compliance_risks"]}
    blocking_fields = {item["field"] for item in gtb["blocking_missing_inputs"]}

    assert "class_declared_without_proof" in risk_ids
    assert "supervision_only_declared_as_gtb" in risk_ids
    assert "gtb.regulation_class" in blocking_fields
    assert any("Ne jamais attribuer une classe" in rule for rule in gtb["source_policy"]["no_hallucination_rules"])


def test_audit_nf_en_16247_preserves_process_and_data_quality():
    audit = load_json(COMPETENCE_ROOT / "technical" / "audit_nf_en_16247.json")
    step_ids = {step["id"] for step in audit["method_steps"]}
    risk_ids = {risk["id"] for risk in audit["compliance_risks"]}
    check_ids = {check["id"] for check in audit["validation_checks"]}

    assert {"preliminary_contact", "kickoff", "data_collection", "field_work", "analysis", "report"} <= step_ids
    assert "audit_without_field_work" in risk_ids
    assert "savings_without_source" in risk_ids
    assert "results_source_marked" in check_ids


def test_cvc_cost_estimation_never_treats_estimate_as_contractual():
    costs = load_json(COMPETENCE_ROOT / "technical" / "cvc_cost_estimation.json")
    check_ids = {check["id"] for check in costs["validation_checks"]}
    risk_ids = {risk["id"] for risk in costs["compliance_risks"]}

    assert "estimate_not_contractual" in check_ids
    assert "three_quotes_recommended" in check_ids
    assert "estimate_used_as_invoice" in risk_ids
    assert costs["output_contract"]["strict_mode"]["never_use_as_invoice_or_signed_quote"] is True


def test_dpt_cee_declares_dpt_as_business_usage_not_official_term():
    dpt = load_json(COMPETENCE_ROOT / "common" / "dpt_cee.json")

    assert dpt["scope"]["official_definition"]["dpt_defined_by_cee_regulation"] is False
    assert "dossier technique pour operations specifiques" in dpt["scope"]["official_definition"]["official_terms"]
    assert "dpt_term_not_official" in {check["id"] for check in dpt["validation_checks"]}


def test_dpt_cee_uses_current_archive_duration():
    dpt = load_json(COMPETENCE_ROOT / "common" / "dpt_cee.json")
    risk_ids = {risk["id"] for risk in dpt["compliance_risks"]}

    assert dpt["scope"]["archive_rule"]["duration_years"] == 9
    assert dpt["scope"]["archive_rule"]["source_ref"] == "CODE_ENERGIE_R222_4"
    assert "wrong_archive_duration" in risk_ids


def test_dpt_cee_has_required_sections_and_outputs():
    dpt = load_json(COMPETENCE_ROOT / "common" / "dpt_cee.json")
    sections = set(dpt["output_contract"]["sections"])
    outputs = set(dpt["output_contract"]["required_outputs"])

    assert "Metadonnees dossier et operation" in sections
    assert "Pieces justificatives et preuves" in sections
    assert "Controles internes et risques PNCEE" in sections
    assert "dpt.md" in outputs
    assert "evidence_map.json" in outputs


def test_dpt_cee_separates_standardized_and_specific_operations():
    dpt = load_json(COMPETENCE_ROOT / "common" / "dpt_cee.json")
    requirements = {item["code"]: item for item in dpt["fiche_specific_requirements"]}
    check_ids = {check["id"] for check in dpt["validation_checks"]}

    assert requirements["*"]["source_refs"] == ["ARRETE_2014_09_04", "MTE_STANDARDIZED_OPERATIONS"]
    assert "GUIDE_SPECIFIC_2025" in requirements["SPE-*"]["source_refs"]
    assert "operation_type_loaded" in check_ids


def test_controle_pncee_has_full_risk_matrix():
    controle = load_json(COMPETENCE_ROOT / "common" / "controle_pncee.json")
    risk_ids = {risk["id"] for risk in controle["compliance_risks"]}

    assert controle["category"] == "common_control"
    assert len(risk_ids) >= 22
    assert "R1_RAI_INVALID_FOR_BENEFICIARY_TYPE" in risk_ids
    assert "R5_RGE_EXPIRE_OU_NON_PROUVE" in risk_ids
    assert "R16_PRE_CONTROL_MANQUANT_SI_REQUIS" in risk_ids
    assert "R22_SIGNAUX_FRAUDE_OU_FAUX_TRAVAUX" in risk_ids


def test_controle_pncee_preserves_pp_copro_rai_tolerance():
    controle = load_json(COMPETENCE_ROOT / "common" / "controle_pncee.json")
    check = {
        item["id"]: item
        for item in controle["validation_checks"]
    }["rai_tolerance_pp_copro"]
    risk = {
        item["id"]: item
        for item in controle["compliance_risks"]
    }["R1_RAI_INVALID_FOR_BENEFICIARY_TYPE"]

    assert "date_engagement + 14 jours" in check["logic"]
    assert "date_debut_travaux" in check["logic"]
    assert "engagement_date + 14 days" in risk["trigger_condition"]
    assert "works_start_date" in risk["trigger_condition"]


def test_controle_pncee_uses_current_archive_duration():
    controle = load_json(COMPETENCE_ROOT / "common" / "controle_pncee.json")
    risk_ids = {risk["id"] for risk in controle["compliance_risks"]}

    assert controle["scope"]["archive_rule"]["duration_years"] == 9
    assert controle["scope"]["archive_rule"]["source_ref"] == "CODE_ENERGIE_R222_4"
    assert "R21_ARCHIVAGE_OBSOLETE_6_ANS" in risk_ids


def test_controle_pncee_fraud_signals_require_human_review():
    controle = load_json(COMPETENCE_ROOT / "common" / "controle_pncee.json")
    risk = {
        item["id"]: item
        for item in controle["compliance_risks"]
    }["R22_SIGNAUX_FRAUDE_OU_FAUX_TRAVAUX"]

    assert risk["blocking"] is True
    assert "revue humaine" in risk["correction_action"]
    assert any(
        "Ne jamais conclure a une fraude" in rule
        for rule in controle["source_policy"]["no_hallucination_rules"]
    )


def test_controle_pncee_strict_mode_blocks_high_risks():
    controle = load_json(COMPETENCE_ROOT / "common" / "controle_pncee.json")

    assert controle["output_contract"]["strict_mode"]["block_if_high_risk_blocking"] is True
    assert controle["output_contract"]["status_mapping"]["high_blocking"] == "blocked"
    assert controle["output_contract"]["status_mapping"]["no_blocking_no_medium"] == "pret_predepot"


def test_competence_source_refs_are_declared():
    competence_files = [
        path
        for path in COMPETENCE_ROOT.rglob("*.json")
        if "schemas" not in path.parts and path.name != "index.json"
    ]

    for path in competence_files:
        data = load_json(path)
        declared = {source["id"] for source in data["source_references"]}
        referenced = set()

        def walk(value):
            if isinstance(value, dict):
                if "source_refs" in value:
                    referenced.update(value["source_refs"])
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(data)
        assert referenced <= declared, f"{path}: missing refs {sorted(referenced - declared)}"
