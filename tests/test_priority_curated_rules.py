import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import dossier_agent  # noqa: E402


PRIORITY_CODES = ["BAR-TH-171", "BAR-TH-168", "BAT-TH-116", "BAT-TH-162", "BAT-TH-163"]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@pytest.mark.parametrize("code", PRIORITY_CODES)
def test_priority_curated_json_validates_schema(code):
    schema = load_json(ROOT / "schemas/fiche_cee.schema.json")
    curated = load_json(ROOT / "data/curated" / f"{code}.json")

    jsonschema.Draft202012Validator(schema).validate(curated)
    assert curated["code"] == code
    assert curated["extraction"]["status"] == "validated"
    assert curated["calculation"]["formula_text"]
    assert curated["calculation"]["tables"]
    assert curated["eligibility_conditions"]
    assert curated["technical_requirements"]
    assert curated["required_documents"]
    assert curated["control_points"]


@pytest.mark.parametrize("code", PRIORITY_CODES)
def test_priority_code_is_supported_full(code):
    assert dossier_agent.detect_support_level(code) == "supported_full"


@pytest.mark.parametrize("code", PRIORITY_CODES)
def test_validate_operation_uses_rules_without_rules_not_found_warning(code, tmp_path):
    rules = load_json(ROOT / "rules" / f"{code}.rules.json")
    inferred_project = {
        "case_id": f"synthetic-{code.lower()}",
        "code": code,
        "fields": {
            field: {
                "value": "confirmed",
                "status": "confirmed",
                "confidence": "high",
                "source": "synthetic test",
                "needs_human_validation": False,
            }
            for field in rules["required_fields"]
        },
        "documents": {document_id: {"provided": True} for document_id in rules["strict_blocking_documents"]},
        "blocking_points": [],
    }
    input_path = tmp_path / f"{code}.inferred_project.json"
    input_path.write_text(json.dumps(inferred_project, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_operation.py", "--input", str(input_path), "--code", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["reference_source"] == "rules"
    assert not any(warning["id"] == "rules_not_found" for warning in payload["warnings"])
