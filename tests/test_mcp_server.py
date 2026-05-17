from __future__ import annotations

import json
from pathlib import Path

from mcp_server.tools.calcul import compute_kwh_cumac
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
