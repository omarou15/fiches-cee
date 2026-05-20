from __future__ import annotations

import json
from pathlib import Path

from mcp_server.tools.calcul import compute_kwh_cumac
from mcp_server.tools.competences import find_competences, get_competence, list_competences
from mcp_server.tools.dossier import generate_dossier
from mcp_server.tools.eligibility import check_eligibility, find_control_risks
from mcp_server.tools.fiches import get_cee_fiche, list_cee_fiches
from mcp_server.tools.search import search_cee


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_list_cee_fiches_returns_all_extracted_fiches():
    result = list_cee_fiches()

    assert result["count"] >= 217
    assert len(result["fiches"]) >= 217
    assert "data/indexes/fiches_cee_index.json" in result["source_files"]


def test_get_cee_fiche_bar_th_179_returns_formula_text():
    result = get_cee_fiche("BAR-TH-179")

    assert result["code"] == "BAR-TH-179"
    assert result["fiche"]["calculation"]["formula_text"]
    assert result["source_files"]


def test_get_cee_fiche_curated_reports_supported_full():
    result = get_cee_fiche("BAR-TH-179", level="curated")

    assert result["level"] == "curated"
    assert result["support_level"] == "supported_full"


def test_check_eligibility_bar_th_179_rejects_low_etas():
    result = check_eligibility("BAR-TH-179", {"etas": 50})

    assert result["support_level"] == "supported_full"
    assert result["eligible"] is False
    assert any("Etas" in item["text"] for item in result["blocking_points"])


def test_compute_kwh_cumac_bar_th_179_returns_positive_value():
    result = compute_kwh_cumac("BAR-TH-179", {"zone": "H1", "apartment_count": 34, "etas": 126})

    assert result["kwh_cumac"] > 0
    assert result["formula_used"]
    assert result["variables_used"]["zone"] == "H1"
    assert result["source_files"]


def test_compute_kwh_cumac_bar_th_171_uses_structured_rules_lookup_table():
    result = compute_kwh_cumac(
        "BAR-TH-171",
        {
            "dwelling_type": "appartement",
            "heated_surface_s_m2": 50,
            "climate_zone": "H2",
            "etas_percent": 126,
        },
    )

    assert result["kwh_cumac"] == 34090
    assert result["confidence"] == "high"
    assert result["needs_human_review"] is False
    assert result["variables_used"]["surface_factor_row"]["factor"] == 0.7


def test_compute_kwh_cumac_bar_th_168_uses_structured_rules_lookup_table():
    result = compute_kwh_cumac(
        "BAR-TH-168",
        {"climate_zone": "H1", "usage": "ecs", "collector_area_m2": 10},
    )

    assert result["kwh_cumac"] == 60000
    assert result["variables_used"]["amount_row"]["value_kwh_cumac_per_m2"] == 6000


def test_compute_kwh_cumac_bat_th_116_uses_structured_rules_lookup_table():
    result = compute_kwh_cumac(
        "BAT-TH-116",
        {
            "gtb_class_after": "A",
            "managed_surface_m2": 100,
            "climate_zone": "H1",
            "sector_activity": "bureaux",
            "usage": "chauffage",
        },
    )

    assert result["kwh_cumac"] == 39600
    assert result["variables_used"]["amount_rows"][0]["value_kwh_cumac_per_m2"] == 360


def test_compute_kwh_cumac_bat_heat_pump_surface_rules():
    bat_th_162 = compute_kwh_cumac(
        "BAT-TH-162",
        {
            "climate_zone": "H1",
            "sector_activity": "bureaux",
            "heated_surface_s_m2": 100,
            "pac_nominal_power_kw": 300,
            "etas_percent": 120,
            "usage": "chauffage",
        },
    )
    bat_th_163 = compute_kwh_cumac(
        "BAT-TH-163",
        {
            "climate_zone": "H1",
            "sector_activity": "bureaux",
            "heated_surface_s_m2": 100,
            "pac_nominal_power_kw": 300,
            "etas_percent": 120,
        },
    )

    assert bat_th_162["kwh_cumac"] == 168000
    assert bat_th_163["kwh_cumac"] == 132000


def test_compute_kwh_cumac_rules_missing_inputs_refuses_to_guess():
    result = compute_kwh_cumac("BAR-TH-171", {"dwelling_type": "appartement"})

    assert result["kwh_cumac"] is None
    assert result["needs_human_review"] is True
    assert "heated_surface_s_m2" in result["notes"]


def test_find_control_risks_bar_th_179_high_returns_risks():
    result = find_control_risks("BAR-TH-179", severity="high")

    assert len(result["risks"]) >= 1
    assert all(item["severity"] == "high" for item in result["risks"])


def test_search_cee_pac_collective_returns_bar_th_179():
    result = search_cee("PAC collective")

    assert any(item["code"] == "BAR-TH-179" for item in result["results"])


def test_get_cee_fiche_unknown_code_returns_clear_error():
    result = get_cee_fiche("CODE-INEXISTANT")

    assert result["error"]["code"] == "fiche_not_found"
    assert result["error"]["requested_code"] == "CODE-INEXISTANT"
    assert "BAR-TH-179" in result["error"]["available_codes"]


def test_generate_dossier_returns_inline_markdown_documents():
    company = load_json(ROOT / "document_engine/examples/synthetic_company_profile.json")
    operation = load_json(ROOT / "document_engine/examples/synthetic_operation_bar_th_179.json")

    result = generate_dossier("BAR-TH-179", operation, company, mode="draft")

    assert result["status"] in {"pret_predepot", "draft", "draft_generic_no_rules"}
    assert "01_ADMIN/devis.md" in result["documents"]
    assert "02_CEE/attestation_honneur.md" in result["documents"]
    assert result["source_files"]


def test_list_competences_returns_runtime_index():
    result = list_competences()

    assert result["count"] >= 11
    assert any(item["id"] == "devis_cee" for item in result["competences"])
    assert "competence_engine/index.json" in result["source_files"]


def test_get_competence_returns_full_contract():
    result = get_competence("devis_cee")

    assert result["id"] == "devis_cee"
    assert result["competence"]["purpose"]
    assert result["competence"]["source_policy"]["no_hallucination_rules"]


def test_find_competences_for_fiche_and_task():
    result = find_competences(code="BAR-TH-179", task="dimensionnement")
    ids = {item["id"] for item in result["competences"]}

    assert "note_dimensionnement_chauffage" in ids
    assert result["code"] == "BAR-TH-179"


def test_get_competence_unknown_returns_clear_error():
    result = get_competence("competence-inconnue")

    assert result["error"]["code"] == "competence_not_found"
    assert "devis_cee" in result["error"]["available_ids"]
