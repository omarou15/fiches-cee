import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_formulas_index():
    return json.loads((ROOT / "data/indexes/formulas_cee_index.json").read_text(encoding="utf-8"))


def by_code(index, code):
    return next(item for item in index if item["code"] == code)


def test_formulas_index_covers_all_unique_fiches():
    index = load_formulas_index()
    assert len(index) == 217

    extracted = [item for item in index if item["formula_status"] == "extracted"]
    missing = [item for item in index if item["formula_status"] == "missing_section"]

    assert len(extracted) == 216
    assert [item["code"] for item in missing] == ["AGRI-TH-118"]
    assert "Partie A" in missing[0]["source_file"]

    for item in extracted:
        assert item["formula_text"]
        assert item["formula_section_text"]
        assert item["source_file"]
        assert item["json_path"].endswith(f"{item['code']}.json")


def test_formula_extraction_handles_table_and_direct_expression_shapes():
    index = load_formulas_index()

    bar_th_179 = by_code(index, "BAR-TH-179")
    assert bar_th_179["formula_status"] == "extracted"
    assert bar_th_179["amount_table_count"] == 30
    assert "N" in bar_th_179["variable_names"]
    assert "R" in bar_th_179["variable_names"]

    bar_th_135 = by_code(index, "BAR-TH-135")
    assert "0,148 x B x T" in bar_th_135["formula_text"]
    assert "0,086 x B x (T" in bar_th_135["formula_text"]

    tra_eq_127 = by_code(index, "TRA-EQ-127")
    assert "121,59 x R x W" in tra_eq_127["expressions"]
    assert {"R", "W"} <= set(tra_eq_127["variable_names"])

    tra_se_113 = by_code(index, "TRA-SE-113")
    assert tra_se_113["formula_status"] == "extracted"
    assert "N" in tra_se_113["variable_names"]
