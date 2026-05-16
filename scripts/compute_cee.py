"""Compute generic CEE amounts from inferred projects."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def unwrap(fields: dict[str, dict], name: str) -> Any:
    item = fields.get(name) or {}
    return item.get("value")


def select_amount_row(fiche: dict, usage: str, zone: str, etas: float) -> dict | None:
    for row in fiche.get("calculation", {}).get("amount_table", []):
        if row.get("usage") != usage or row.get("zone") != zone:
            continue
        etas_min = row.get("etas_min")
        etas_max = row.get("etas_max")
        if etas_min is not None and etas >= etas_min and (etas_max is None or etas < etas_max):
            return row
    return None


def compute_project(project: dict) -> dict:
    if project.get("code") != "BAR-TH-179":
        return {"status": "not_applicable", "kwh_cumac": None, "formula_text": None, "missing_inputs": ["unsupported_code"], "details": {}}

    fields = project.get("fields", {})
    required = [
        "climate_zone",
        "apartment_count_heated_by_pac",
        "usage",
        "etas_percent",
        "pac_nominal_power_kw",
        "chaufferie_useful_power_after_works_kw",
        "backup_equipment_excluded",
    ]
    missing = [name for name in required if unwrap(fields, name) in {None, "", "unknown"}]
    if missing:
        return {"status": "missing_inputs", "kwh_cumac": None, "formula_text": None, "missing_inputs": missing, "details": {}}

    fiche = load_json(REPO_ROOT / "data" / "json" / "BAR-TH-179.json")
    usage = unwrap(fields, "usage")
    if usage == "ecs_only":
        return {"status": "not_applicable", "kwh_cumac": None, "formula_text": fiche["calculation"]["formula_text"], "missing_inputs": ["usage"], "details": {"reason": "PAC ECS seule exclue"}}

    zone = unwrap(fields, "climate_zone")
    etas = float(unwrap(fields, "etas_percent"))
    apartments = float(unwrap(fields, "apartment_count_heated_by_pac"))
    pac_power = float(unwrap(fields, "pac_nominal_power_kw"))
    boiler_power = float(unwrap(fields, "chaufferie_useful_power_after_works_kw"))
    if boiler_power <= 0:
        return {"status": "missing_inputs", "kwh_cumac": None, "formula_text": fiche["calculation"]["formula_text"], "missing_inputs": ["chaufferie_useful_power_after_works_kw"], "details": {}}

    row = select_amount_row(fiche, usage, zone, etas)
    if row is None:
        return {"status": "missing_inputs", "kwh_cumac": None, "formula_text": fiche["calculation"]["formula_text"], "missing_inputs": ["etas_percent"], "details": {"reason": "aucune ligne de montant trouvee"}}

    ratio = pac_power / boiler_power
    r_factor = ratio if ratio < 0.4 else 1.0
    kwh = round(float(row["kwh_cumac_per_apartment"]) * apartments * r_factor, 3)
    return {
        "status": "computed",
        "kwh_cumac": kwh,
        "formula_text": fiche["calculation"]["formula_text"],
        "missing_inputs": [],
        "details": {
            "amount_row": row,
            "r_factor": round(r_factor, 6),
            "power_ratio": round(ratio, 6),
        },
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = compute_project(load_json(Path(args.input)))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
