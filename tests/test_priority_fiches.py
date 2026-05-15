import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_energyco_priority_contains_bar_th_179():
    priority = json.loads((ROOT / "data/indexes/energyco_priority_index.json").read_text(encoding="utf-8"))
    codes = {item["code"] for item in priority}
    assert "BAR-TH-179" in codes
    assert "RES-CH-106" in codes


def test_energyco_priority_excludes_non_building_sectors_without_whitelist():
    priority = json.loads((ROOT / "data/indexes/energyco_priority_index.json").read_text(encoding="utf-8"))
    prefixes = {item["code"].split("-", 1)[0] for item in priority}
    assert "AGRI" not in prefixes
    assert "TRA" not in prefixes
    assert "IND" not in prefixes


def test_priority_fiches_need_review_or_have_core_fields():
    priority = json.loads((ROOT / "data/indexes/energyco_priority_index.json").read_text(encoding="utf-8"))
    for item in priority:
        fiche = json.loads((ROOT / item["json_path"]).read_text(encoding="utf-8"))
        has_core = fiche["required_documents"] or fiche["technical_requirements"] or fiche["formulas"]
        assert has_core or fiche["extraction"]["needs_human_review"]
