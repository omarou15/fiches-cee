import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_bar_th_179():
    return json.loads((ROOT / "data/json/BAR-TH-179.json").read_text(encoding="utf-8"))


def load_curated_bar_th_179():
    return json.loads((ROOT / "data/curated/BAR-TH-179.json").read_text(encoding="utf-8"))


def test_bar_th_179_core_dates_and_lifetime():
    fiche = load_bar_th_179()
    assert fiche["effective_date"] == "2026-04-30"
    assert fiche["validity"]["engagement_deadline"] == "2030-12-31"
    assert fiche["lifetime_years"] == 22


def test_bar_th_179_structured_requirements():
    fiche = load_bar_th_179()
    requirements = fiche["technical_requirements_structured"]
    assert requirements["pac_nominal_power_max_kw"] == 400
    assert requirements["professional_required"] is True
    assert requirements["rge_quality_sign_required"] is True
    assert {"application": "moyenne_haute_temperature", "etas_min_percent": 111} in requirements["etas_thresholds"]
    assert {"application": "basse_temperature", "etas_min_percent": 126} in requirements["etas_thresholds"]
    assert fiche["dimensioning_study"]["required"] is True
    assert "étude préalable de dimensionnement" in fiche["specific_supporting_documents"]


def test_bar_th_179_calculation_table_and_r_factor():
    fiche = load_bar_th_179()
    table = fiche["calculation"]["amount_table"]
    assert table
    assert {row["zone"] for row in table} == {"H1", "H2", "H3"}
    assert any(row["etas_min"] == 111 and row["etas_max"] == 126 and row["usage"] == "chauffage" and row["zone"] == "H1" and row["kwh_cumac_per_apartment"] == 100000 for row in table)
    assert any(row["etas_min"] == 190 and row["etas_max"] is None and row["usage"] == "chauffage_et_ecs" and row["zone"] == "H3" and row["kwh_cumac_per_apartment"] == 117000 for row in table)
    assert fiche["calculation"]["r_factor"]["exclude_backup_equipment"] is True
    assert "R =" in fiche["calculation"]["r_factor"]["formula"]


def test_bar_th_179_exclusions_and_non_cumulation():
    fiche = load_bar_th_179()
    assert any("eau chaude sanitaire" in item for item in fiche["excluded_uses"])
    assert any(item["code"] == "BAR-TH-169" for item in fiche["non_cumulation"])
    curated = load_curated_bar_th_179()
    assert any(item["text"] == "PAC ECS seule non éligible" and item["severity"] == "high" for item in curated["compliance_risks"])
    assert all({"text", "severity"}.issubset(item) for item in curated["compliance_risks"])
    assert fiche["extraction"]["status"] == "validated"
    assert fiche["extraction"]["needs_human_review"] is False
