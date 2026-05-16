import copy
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import dossier_agent  # noqa: E402


def load_example(name):
    return json.loads((ROOT / "examples" / "dossier_agent" / name).read_text(encoding="utf-8"))


def build(name):
    return dossier_agent.build_dossier(load_example(name))


def check_by_id(dossier, check_id):
    return next(item for item in dossier["eligibility"]["checks"] if item["id"] == check_id)


def document_by_id(dossier, document_id):
    return next(item for item in dossier["document_check"]["documents"] if item["id"] == document_id)


def validate_dossier_schema(dossier):
    schema = json.loads((ROOT / "schemas" / "dossier_predepot.schema.json").read_text(encoding="utf-8"))
    document_schema = json.loads((ROOT / "schemas" / "document_check.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        document_schema["$id"],
        Resource.from_contents(document_schema),
    )
    jsonschema.Draft202012Validator(schema, registry=registry).validate(dossier)
    jsonschema.validate(dossier["document_check"], document_schema)


def test_complete_bar_th_179_is_ready_and_calculated():
    dossier = build("bar_th_179_complete.json")

    assert dossier["status"] == "pret_predepot"
    assert dossier["eligibility"]["eligible"] is True
    assert dossier["missing_questions"] == []
    assert dossier["calculation"]["status"] == "computed"
    assert dossier["calculation"]["kwh_cumac"] == 5542000.0
    assert dossier["calculation"]["amount_row"]["kwh_cumac_per_apartment"] == 163000
    assert dossier["calculation"]["r_factor"]["value"] == 1.0
    assert all(doc["status"] == "received" for doc in dossier["document_check"]["documents"])
    assert dossier["no_hallucination"]["invented_values"] is False
    assert dossier["no_hallucination"]["unknown_fields"] == []
    validate_dossier_schema(dossier)


def test_incomplete_bar_th_179_asks_questions_without_inventing_values():
    dossier = build("bar_th_179_incomplete.json")
    fields = {item["field_path"] for item in dossier["missing_questions"]}

    assert dossier["status"] == "incomplet_questions"
    assert dossier["eligibility"]["eligible"] is None
    assert dossier["calculation"]["status"] == "missing_inputs"
    assert dossier["calculation"]["kwh_cumac"] is None
    assert "operation.etas_percent" in fields
    assert "operation.backup_equipment_excluded" in fields
    assert "documents.dimensioning_study" in fields
    assert "professional.rge_quality_sign" in fields
    assert document_by_id(dossier, "dimensioning_study")["status"] == "missing"
    assert dossier["no_hallucination"]["invented_values"] is False
    assert set(dossier["no_hallucination"]["unknown_fields"]) == fields


def test_ecs_only_is_non_eligible_for_bar_th_179():
    dossier = build("bar_th_179_ecs_only_non_eligible.json")

    assert dossier["status"] == "non_eligible"
    assert dossier["eligibility"]["eligible"] is False
    assert check_by_id(dossier, "usage")["status"] == "fail"
    assert dossier["calculation"]["status"] == "not_applicable"
    assert dossier["calculation"]["kwh_cumac"] is None


def test_r_factor_is_applied_when_pac_power_is_below_40_percent():
    operation = load_example("bar_th_179_complete.json")
    operation["operation_id"] = "demo-r-factor"
    operation["operation"]["usage"] = "chauffage"
    operation["site"]["climate_zone"] = "H2"
    operation["site"]["apartment_count_heated_by_pac"] = 10
    operation["operation"]["etas_percent"] = 130
    operation["operation"]["pac_nominal_power_kw"] = 80
    operation["operation"]["chaufferie_useful_power_after_works_kw"] = 300

    dossier = dossier_agent.build_dossier(operation)

    assert dossier["status"] == "pret_predepot"
    assert dossier["calculation"]["amount_row"]["kwh_cumac_per_apartment"] == 89000
    assert dossier["calculation"]["r_factor"]["value"] == 0.266667
    assert dossier["calculation"]["kwh_cumac"] == 237333.333
    assert any(risk["id"] == "r_factor_applied" for risk in dossier["risks"])


def test_missing_zone_blocks_ready_status():
    operation = load_example("bar_th_179_complete.json")
    operation["operation_id"] = "demo-missing-zone"
    operation["site"]["climate_zone"] = None

    dossier = dossier_agent.build_dossier(operation)
    fields = {item["field_path"] for item in dossier["missing_questions"]}

    assert dossier["status"] == "incomplet_questions"
    assert dossier["calculation"]["kwh_cumac"] is None
    assert "site.climate_zone" in fields
    assert dossier["no_hallucination"]["invented_values"] is False


def test_missing_dimensioning_study_blocks_ready_status():
    operation = load_example("bar_th_179_complete.json")
    operation["operation_id"] = "demo-missing-study"
    operation["documents"]["dimensioning_study"] = {"provided": False}

    dossier = dossier_agent.build_dossier(operation)

    assert dossier["status"] == "incomplet_questions"
    assert document_by_id(dossier, "dimensioning_study")["status"] == "missing"
    assert any(item["field_path"] == "documents.dimensioning_study" for item in dossier["missing_questions"])


def test_missing_professional_qualification_blocks_ready_status():
    operation = load_example("bar_th_179_complete.json")
    operation["operation_id"] = "demo-missing-qualification"
    operation["documents"]["professional_qualification"] = {"provided": False}

    dossier = dossier_agent.build_dossier(operation)

    assert dossier["status"] == "incomplet_questions"
    assert document_by_id(dossier, "professional_qualification")["status"] == "missing"


def test_non_cumulation_bar_th_169_is_detected():
    operation = load_example("bar_th_179_complete.json")
    operation["operation_id"] = "demo-non-cumulation"
    operation["non_cumulation"]["uses_bar_th_169"] = True

    dossier = dossier_agent.build_dossier(operation)

    assert dossier["status"] == "non_eligible"
    assert check_by_id(dossier, "non_cumulation_bar_th_169")["status"] == "fail"


def test_engagement_date_outside_validity_is_non_eligible():
    operation = load_example("bar_th_179_complete.json")
    operation["operation_id"] = "demo-outside-validity"
    operation["operation"]["engagement_date"] = "2031-01-01"

    dossier = dossier_agent.build_dossier(operation)

    assert dossier["status"] == "non_eligible"
    assert check_by_id(dossier, "engagement_date")["status"] == "fail"


def test_cli_writes_local_pack(tmp_path):
    output_dir = tmp_path / "pack"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/dossier_agent.py",
            "examples/dossier_agent/bar_th_179_complete.json",
            "--output",
            str(output_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (output_dir / "dossier_predepot.md").exists()
    assert (output_dir / "calcul_kwh_cumac.json").exists()
    assert (output_dir / "checklist_pieces.json").exists()
    assert (output_dir / "questions_manquantes.md").exists()
    assert (output_dir / "risques_pncee.md").exists()
    assert (output_dir / "sources_reglementaires.md").exists()
    generated = json.loads((output_dir / "dossier_predepot.json").read_text(encoding="utf-8"))
    assert generated["status"] == "pret_predepot"


def test_fiche_without_rules_generates_generic_draft_without_invented_blockers():
    operation = load_example("bar_th_179_complete.json")
    operation["operation_id"] = "demo-generic-no-rules"
    operation["fiche_code"] = "BAR-TH-113"

    dossier = dossier_agent.build_dossier(operation)

    assert dossier["fiche_code"] == "BAR-TH-113"
    assert dossier["status"] == "draft_generic_no_rules"
    assert dossier["eligibility"]["eligible"] is None
    assert dossier["missing_questions"] == []
    assert dossier["calculation"]["missing_inputs"] == []
    assert dossier["no_hallucination"]["invented_values"] is False
    assert dossier["no_hallucination"]["unknown_fields"] == []
    validate_dossier_schema(dossier)


def test_inferred_bar_th_179_project_with_document_list_generates_ready_dossier(tmp_path):
    inferred = tmp_path / "inferred_project.json"
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

    result = subprocess.run(
        [sys.executable, "scripts/dossier_agent.py", str(inferred), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    dossier = json.loads(result.stdout)
    assert dossier["operation_id"] == "synthetic-bar-th-179-minimal"
    assert dossier["fiche_code"] == "BAR-TH-179"
    assert dossier["status"] == "pret_predepot"
    assert dossier["calculation"]["status"] == "computed"
    assert dossier["calculation"]["kwh_cumac"] == 5542000.0
    assert dossier["missing_questions"] == []
    assert all(doc["status"] == "unknown" for doc in dossier["document_check"]["documents"])
    validate_dossier_schema(dossier)


def test_build_dossier_does_not_mutate_input():
    operation = load_example("bar_th_179_complete.json")
    original = copy.deepcopy(operation)

    dossier_agent.build_dossier(operation)

    assert operation == original
