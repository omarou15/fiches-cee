import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_formula_audit_passes_against_unique_fiche_pdfs():
    result = subprocess.run(
        [sys.executable, "scripts/audit_formula_extraction.py", "--fail-on-issues"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads((ROOT / "data/indexes/formula_audit_report.json").read_text(encoding="utf-8"))
    summary = report["summary"]
    assert summary["total_unique_fiches"] == 217
    assert summary["ok"] == 216
    assert summary["known_missing_source"] == 1
    assert summary["needs_review"] == 0
    assert summary["failed"] == 0
    assert summary["total_missing_values"] == 0


def test_bar_th_101_formula_values_are_extracted():
    fiche = json.loads((ROOT / "data/json/BAR-TH-101.json").read_text(encoding="utf-8"))
    values = {(item["type"], item["normalized"]) for item in fiche["calculation"]["extracted_values"]}
    assert ("zone", "H1") in values
    assert ("zone", "H2") in values
    assert ("zone", "H3") in values
    assert ("number", "18500") in values
    assert ("number", "21000") in values
    assert ("number", "24200") in values
