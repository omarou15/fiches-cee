import json
import subprocess
import sys
from pathlib import Path

import jsonschema

from document_engine.generators.render_template import build_context, render_string


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_render_template_replaces_placeholders():
    company = load_json(ROOT / "document_engine/examples/synthetic_company_profile.json")
    operation = load_json(ROOT / "document_engine/examples/synthetic_operation_bar_th_179.json")
    rendered = render_string(
        "{{ company.name }} / {{ client.name }} / {{ operation.cee_code }} / {{ calculation.total_kwh_cumac }}",
        build_context(company, operation, "BAR-TH-179"),
    )
    assert "CEE Demo Installateur" in rendered
    assert "Syndicat fictif Residence des Lilas" in rendered
    assert "BAR-TH-179" in rendered
    assert "6200000" in rendered
    assert "{{" not in rendered


def test_document_engine_examples_validate_against_schemas():
    jsonschema.validate(
        load_json(ROOT / "document_engine/examples/synthetic_company_profile.json"),
        load_json(ROOT / "document_engine/schemas/company_profile.schema.json"),
    )
    jsonschema.validate(
        load_json(ROOT / "document_engine/examples/synthetic_operation_bar_th_179.json"),
        load_json(ROOT / "document_engine/schemas/operation_input.schema.json"),
    )


def test_generate_document_pack_from_operation_creates_expected_files(tmp_path):
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
    expected = [
        "00_SYNTHESE/synthese_dossier.md",
        "00_SYNTHESE/pieces_manquantes.md",
        "00_SYNTHESE/controle_eligibilite.md",
        "01_ADMIN/devis.md",
        "01_ADMIN/facture.md",
        "01_ADMIN/mail_pieces_manquantes.md",
        "02_CEE/attestation_honneur.md",
        "02_CEE/calcul_kwh_cumac.md",
        "02_CEE/checklist_cee.md",
        "03_TECHNIQUE/note_dimensionnement.md",
        "03_TECHNIQUE/dpt.md",
        "04_CONTROLE_INTERNE/rapport_controle_interne.md",
        "04_CONTROLE_INTERNE/risques_pncee.md",
        "dossier_manifest.json",
    ]
    for rel_path in expected:
        assert (output / rel_path).exists(), rel_path
    manifest = load_json(output / "dossier_manifest.json")
    assert manifest["source_type"] == "operation_input"
    assert manifest["code"] == "BAR-TH-179"
    assert manifest["template_profile"] == "specific"
    devis = (output / "01_ADMIN/devis.md").read_text(encoding="utf-8")
    assert "DEV-DEMO-2026-001" in devis
    assert "{{" not in devis
    ah = (output / "02_CEE/attestation_honneur.md").read_text(encoding="utf-8")
    assert "6200000" in ah
    assert "PAC-AW-180-DEMO" in ah


def test_generate_document_pack_for_generic_fiche(tmp_path):
    operation = tmp_path / "operation_bar_th_101.json"
    output = tmp_path / "demo_bar_th_101"
    init = subprocess.run(
        [
            sys.executable,
            "scripts/init_operation_input.py",
            "--code",
            "BAR-TH-101",
            "--output",
            str(operation),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert init.returncode == 0, init.stdout + init.stderr
    jsonschema.validate(load_json(operation), load_json(ROOT / "document_engine/schemas/operation_input.schema.json"))

    generate = subprocess.run(
        [
            sys.executable,
            "scripts/generate_document_pack.py",
            "--company",
            "document_engine/examples/synthetic_company_profile.json",
            "--operation",
            str(operation),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert generate.returncode == 0, generate.stdout + generate.stderr
    manifest = load_json(output / "dossier_manifest.json")
    assert manifest["code"] == "BAR-TH-101"
    assert manifest["template_profile"] == "generic"
    assert manifest["templates_used"]["ah"] == "ah/ah_generic.md"
    assert (output / "03_TECHNIQUE/dpt.md").exists()
    ah = (output / "02_CEE/attestation_honneur.md").read_text(encoding="utf-8")
    assert "brouillon generique" in ah
    assert "{{" not in ah


def test_document_engine_audit_supports_multiple_fiches():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_document_engine.py",
            "--code",
            "BAR-TH-179",
            "--code",
            "BAR-TH-101",
            "--code",
            "BAT-TH-116",
            "--fail-on-issues",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_private_and_outputs_are_not_tracked():
    result = subprocess.run(
        ["git", "ls-files", "private", "outputs", "clients", "dossiers"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
