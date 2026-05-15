import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_search_supports_sector_family_and_code_filters():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/search_fiches.py",
            "PAC collective",
            "--sector",
            "residentiel",
            "--family",
            "TH",
            "--code",
            "BAR-TH-179",
            "--limit",
            "3",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rows = json.loads(result.stdout)
    assert rows
    assert rows[0]["code"] == "BAR-TH-179"
    assert rows[0]["best_chunk"]["source_file"]
    assert rows[0]["best_chunk"]["page_start"]
