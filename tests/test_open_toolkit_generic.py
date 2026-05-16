import json
import subprocess
import sys
from pathlib import Path

import jsonschema
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_inferred_project(path):
    schema = load_json(ROOT / "inference_engine/schemas/inferred_project.schema.json")
    assumption_schema = load_json(ROOT / "inference_engine/schemas/assumption.schema.json")
    registry = Registry().with_resource(assumption_schema["$id"], Resource.from_contents(assumption_schema))
    jsonschema.Draft202012Validator(schema, registry=registry).validate(load_json(path))


def test_infer_case_and_generate_document_pack(tmp_path):
    inferred = tmp_path / "inferred_project.json"
    pack = tmp_path / "pack"
    infer = subprocess.run(
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
    assert infer.returncode == 0, infer.stdout + infer.stderr
    validate_inferred_project(inferred)
    project = load_json(inferred)
    assert project["code"] == "BAR-TH-179"
    assert project["fields"]["climate_zone"]["value"] == "H1"
    assert project["fields"]["estimated_works_cost_eur_ht"]["status"] == "estimated"
    assert project["fields"]["estimated_works_cost_eur_ht"]["needs_human_validation"] is True
    assert project["calculation"]["status"] == "computed"
    assert project["calculation"]["kwh_cumac"] == 5542000.0

    generate = subprocess.run(
        [
            sys.executable,
            "scripts/generate_document_pack.py",
            "--company",
            "document_engine/examples/synthetic_company_profile.json",
            "--inferred",
            str(inferred),
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
    assert generate.returncode == 0, generate.stdout + generate.stderr
    manifest = load_json(pack / "dossier_manifest.json")
    assert manifest["mode"] == "draft"
    assert "00_SYNTHESE/synthese_dossier.md" in manifest["files"]
    assert "03_TECHNIQUE/note_dimensionnement.md" in manifest["files"]


def test_common_use_cases_index_is_generic():
    index = load_json(ROOT / "data/indexes/common_use_cases_index.json")
    assert any(item["code"] == "BAR-TH-179" for item in index)
    assert all("common_use_cases" in item for item in index)
    legacy_name = "energy" + "co_priority_index.json"
    assert not (ROOT / "data/indexes" / legacy_name).exists()


def test_public_repo_has_no_vendor_specific_references():
    vendor_pattern = "Energy" + "co|energy" + "co|ENERGY" + "CO|priority-energy" + "co"
    result = subprocess.run(
        ["rg", "-n", "-S", "-e", vendor_pattern, "--glob", "!tests/test_open_toolkit_generic.py", "."],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
