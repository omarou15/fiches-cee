import json
import subprocess
import sys
from pathlib import Path

import jsonschema
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_inferred(path):
    schema = load_json(ROOT / "inference_engine/schemas/inferred_project.schema.json")
    assumption_schema = load_json(ROOT / "inference_engine/schemas/assumption.schema.json")
    registry = Registry().with_resource(assumption_schema["$id"], Resource.from_contents(assumption_schema))
    jsonschema.Draft202012Validator(schema, registry=registry).validate(load_json(path))


def test_minimal_input_schema_does_not_require_technical_variables():
    schema = load_json(ROOT / "inference_engine/schemas/minimal_case_input.schema.json")
    required_root = set(schema["required"])
    assert {"client", "site", "visit", "objective"}.issubset(required_root)
    forbidden = {
        "pac_nominal_power_kw",
        "etas_percent",
        "tbase_c",
        "heat_losses_kw",
        "chaufferie_useful_power_after_works_kw",
        "apartment_count_heated_by_pac",
        "estimated_works_cost_eur_ht",
    }
    assert forbidden.isdisjoint(required_root)
    site_required = set(schema["properties"]["site"].get("required", []))
    visit_required = set(schema["properties"]["visit"].get("required", []))
    objective_required = set(schema["properties"]["objective"].get("required", []))
    assert forbidden.isdisjoint(site_required | visit_required | objective_required)


def test_infer_case_outputs_wrapped_values_and_estimated_quote(tmp_path):
    inferred = tmp_path / "inferred_project.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/infer_case.py",
            "--input",
            "inference_engine/examples/synthetic_minimal_case_bar_th_179.json",
            "--code",
            "BAR-TH-179",
            "--output",
            str(inferred),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    validate_inferred(inferred)
    project = load_json(inferred)
    assert project["code"] == "BAR-TH-179"
    for value in project["fields"].values():
        assert {"value", "status", "confidence", "source", "needs_human_validation"}.issubset(value)
    assert project["fields"]["estimated_works_cost_eur_ht"]["status"] == "estimated"
    assert project["fields"]["quote_lines"]["value"]
    assert project["calculation"]["status"] == "computed"
    assert project["blocking_points"] == []


def test_inferred_document_pack_generates_draft_with_missing_validation_points(tmp_path):
    inferred = tmp_path / "inferred_project.json"
    pack = tmp_path / "pack"
    subprocess.run(
        [
            sys.executable,
            "scripts/infer_case.py",
            "--input",
            "inference_engine/examples/synthetic_minimal_case_bar_th_179.json",
            "--code",
            "BAR-TH-179",
            "--output",
            str(inferred),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_document_pack.py",
            "--inferred",
            str(inferred),
            "--company",
            "document_engine/examples/synthetic_company_profile.json",
            "--mode",
            "draft",
            "--output",
            str(pack),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = load_json(pack / "dossier_manifest.json")
    assert manifest["source_type"] == "inferred_project"
    assert manifest["missing_documents"]
    devis = (pack / "01_ADMIN/devis.md").read_text(encoding="utf-8")
    assert "document généré automatiquement à valider" in devis or "document genere automatiquement a valider" in devis
    assert "{{" not in devis


def test_inference_prompts_exist():
    for name in ["visit_to_project_prompt.md", "photo_analysis_prompt.md", "assumptions_prompt.md"]:
        path = ROOT / "inference_engine" / "prompts" / name
        assert path.exists()
        assert "Ne jamais" in path.read_text(encoding="utf-8") or "hypothese" in path.read_text(encoding="utf-8").lower()
