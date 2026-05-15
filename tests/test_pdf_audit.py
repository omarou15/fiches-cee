import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_unique_fiche_pdf_audit_passes():
    result = subprocess.run(
        [sys.executable, "scripts/audit_unique_fiches.py", "--fail-on-issues"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads((ROOT / "data/indexes/pdf_audit_unique_fiches.json").read_text(encoding="utf-8"))
    summary = report["summary"]
    assert report["scope"] == "unique_fiche_main_pdfs_only"
    assert summary["total_unique_fiches"] == 217
    assert summary["pdf_checked"] == 217
    assert summary["failed"] == 0
    assert summary["needs_review"] == 0
    assert summary["empty_text"] == 0
    assert summary["missing_generated_json"] == 0
    assert summary["missing_generated_markdown"] == 0
    assert summary["missing_generated_text"] == 0
    assert summary["generated_text_mismatch"] == 0
