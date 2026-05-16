import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_validate_operation_with_code_without_rules_warns_but_does_not_block(tmp_path):
    inferred_project = {
        "case_id": "demo-validate-no-rules",
        "code": "BAR-TH-113",
        "fields": {},
        "blocking_points": [],
    }
    input_path = tmp_path / "inferred_project.json"
    input_path.write_text(json.dumps(inferred_project, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_operation.py",
            "--input",
            str(input_path),
            "--code",
            "BAR-TH-113",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["blocking_points"] == []
    assert payload["reference_source"] == "json"
    assert any(warning["id"] == "rules_not_found" for warning in payload["warnings"])
