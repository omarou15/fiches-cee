from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from mcp_server.tools.chronology import check_chronology
from mcp_server.tools.dossier import get_annexe6_row
from mcp_server.tools.eligibility import list_required_documents
from scripts.validate_operation import validate_chronology


ROOT = Path(__file__).resolve().parents[1]
CURATED_CODES = ["BAR-TH-179", "BAR-TH-171", "BAR-TH-168", "BAT-TH-116", "BAT-TH-162", "BAT-TH-163"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def valid_dates(**overrides):
    data = {
        "beneficiary_type": "copropriete",
        "date_cadre_contribution": "2026-05-25",
        "date_engagement": "2026-05-20",
        "date_debut_travaux": "2026-06-10",
        "date_facture": "2026-09-30",
        "date_ah_signee": "2026-10-02",
        "date_depot_pncee": "2027-02-01",
        "qualification_rge_validite": "2026-12-31",
    }
    data.update(overrides)
    return data


def generate_pack(tmp_path: Path) -> Path:
    output = tmp_path / "demo_bar_th_179"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_document_pack.py",
            "--code",
            "BAR-TH-179",
            "--company",
            "document_engine/examples/synthetic_company_profile.json",
            "--operation",
            "document_engine/examples/synthetic_operation_bar_th_179.json",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return output


def test_ah_has_5_parts():
    for rel in ["document_engine/templates/ah/ah_bar_th_179.md", "document_engine/templates/ah/ah_generic.md"]:
        text = read(ROOT / rel)
        assert "Partie Demandeur" in text
        assert "Partie A1" in text
        assert "Partie B" in text
        assert "Partie C" in text
        assert "Partie finale" in text


def test_ah_has_cnil_mention():
    text = read(ROOT / "document_engine/templates/ah/ah_bar_th_179.md")
    assert "CNIL" in text


def test_ah_has_penal_sanctions():
    text = read(ROOT / "document_engine/templates/ah/ah_bar_th_179.md")
    assert "441-7" in text
    assert "15 000" in text


def test_ah_has_telephone_email_fields():
    text = read(ROOT / "document_engine/templates/ah/ah_bar_th_179.md")
    assert "*Téléphone" in text
    assert "*Email" in text


def test_cadre_contribution_generated(tmp_path):
    output = generate_pack(tmp_path)
    assert (output / "00_ENGAGEMENT/cadre_contribution.md").exists()


def test_cadre_contribution_has_warning(tmp_path):
    output = generate_pack(tmp_path)
    text = read(output / "00_ENGAGEMENT/cadre_contribution.md")
    assert "CE DOCUMENT DOIT ÊTRE ÉTABLI AVANT OU AU MAXIMUM 14 JOURS" in text


def test_cadre_contribution_in_manifest(tmp_path):
    output = generate_pack(tmp_path)
    manifest = load_json(output / "dossier_manifest.json")
    assert "00_ENGAGEMENT/cadre_contribution.md" in manifest["files"]


def test_chronology_valid_case():
    result = validate_chronology(valid_dates())
    assert result["valid"] is True
    assert result["blocking_points"] == []


def test_chronology_rai_after_engagement():
    result = validate_chronology(valid_dates(date_cadre_contribution="2026-06-10"))
    assert result["valid"] is False
    assert any("cadre de contribution" in item["text"] for item in result["blocking_points"])


def test_chronology_works_before_devis():
    result = validate_chronology(valid_dates(date_debut_travaux="2026-05-10"))
    assert result["valid"] is False
    assert any("devis" in item["text"] for item in result["blocking_points"])


def test_chronology_rge_expired():
    result = validate_chronology(valid_dates(qualification_rge_validite="2026-05-01"))
    assert result["valid"] is False
    assert any("RGE" in item["text"] for item in result["blocking_points"])


def test_chronology_depot_too_late():
    result = validate_chronology(valid_dates(date_depot_pncee="2027-10-05"))
    assert result["valid"] is False
    assert any("12 mois" in item["text"] for item in result["blocking_points"])


def test_chronology_mcp_tool():
    result = check_chronology("BAR-TH-179", valid_dates(date_debut_travaux="2026-05-10"))
    assert result["valid"] is False
    assert result["source"] == "Annexe 5 arrete 4 septembre 2014"


def test_annexe6_generated(tmp_path):
    output = generate_pack(tmp_path)
    assert (output / "05_EMMY/tableau_recap_annexe6.md").exists()


def test_annexe6_has_all_columns(tmp_path):
    output = generate_pack(tmp_path)
    text = read(output / "05_EMMY/tableau_recap_annexe6.md")
    for label in [
        "Référence interne du demandeur",
        "Code de la fiche d'opération standardisée",
        "Secteur",
        "Identité du bénéficiaire",
        "Date d'engagement",
        "Date d'achèvement",
        "Montant en kWh cumac",
        "Identité du professionnel",
        "Qualification RGE",
        "Montant de la contribution",
        "Précarité énergétique",
        "Coup de pouce",
    ]:
        assert label in text


def test_annexe6_mcp_tool():
    operation = load_json(ROOT / "document_engine/examples/synthetic_operation_bar_th_179.json")
    result = get_annexe6_row("BAR-TH-179", operation)
    row = result["annexe6_row"]
    for key in [
        "reference_interne_demandeur",
        "code_fiche",
        "secteur",
        "beneficiaire_nom",
        "date_engagement",
        "date_achevement",
        "montant_kwh_cumac",
        "professionnel_raison_sociale",
        "qualification_rge_reference",
        "montant_contribution_eur",
        "precarite_energetique",
        "coup_de_pouce",
    ]:
        assert key in row


def test_required_docs_structure():
    for code in CURATED_CODES:
        curated = load_json(ROOT / "data/curated" / f"{code}.json")
        assert set(curated["required_documents"]) == {
            "common_pieces_annexe5",
            "specific_pieces_fiche",
            "pieces_precarite",
            "pieces_coup_de_pouce",
        }


def test_required_docs_common_pieces():
    required_names = ["Cadre de contribution", "Devis", "Attestation sur l'honneur", "Facture", "RGE"]
    for code in CURATED_CODES:
        curated = load_json(ROOT / "data/curated" / f"{code}.json")
        common_text = " ".join(item["document"] for item in curated["required_documents"]["common_pieces_annexe5"])
        for expected in required_names:
            assert expected in common_text


def test_list_required_documents_mcp():
    result = list_required_documents("BAR-TH-179")
    docs = result["required_documents"]
    assert "common_pieces_annexe5" in docs
    assert "specific_pieces_fiche" in docs
    assert any("Cadre de contribution" in item["document"] for item in docs["common_pieces_annexe5"])
