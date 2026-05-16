"""Infer a generic CEE project from minimal local case information."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compute_cee import compute_project


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from inference_engine.enrichers.common import field  # noqa: E402
from inference_engine.enrichers.estimate_works_cost import estimate_works_cost  # noqa: E402
from inference_engine.enrichers.infer_building_from_visit import infer_building_from_visit  # noqa: E402
from inference_engine.enrichers.infer_climate_zone import infer_climate_zone  # noqa: E402
from inference_engine.enrichers.infer_heat_losses import infer_heat_losses  # noqa: E402
from inference_engine.enrichers.infer_pac_sizing import infer_pac_sizing  # noqa: E402
from inference_engine.enrichers.infer_systems_from_visit import infer_systems_from_visit  # noqa: E402
from inference_engine.enrichers.infer_works_scope import infer_works_scope  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_pricebook() -> dict:
    merged = {"name": "Merged generic draft pricebook", "currency": "EUR", "items": {}}
    for path in sorted((REPO_ROOT / "inference_engine" / "pricebooks").glob("*.pricebook.json")):
        data = load_json(path)
        merged["items"].update(data.get("items", {}))
    return merged


def build_project(case: dict, code: str) -> dict:
    if code != "BAR-TH-179":
        raise ValueError("V1 inference supports BAR-TH-179 only.")
    fields: dict[str, dict] = {
        "climate_zone": infer_climate_zone(case),
    }
    fields.update(infer_building_from_visit(case))
    fields.update(infer_systems_from_visit(case))

    # Default draft assumptions where the visit notes do not provide values.
    if fields["heated_surface_m2"]["value"] is None and fields["apartment_count_heated_by_pac"]["value"]:
        fields["heated_surface_m2"] = field(fields["apartment_count_heated_by_pac"]["value"] * 65, "estimated", "low", "65 m2/logement")
    if fields["etas_percent"]["value"] is None:
        fields["etas_percent"] = field(151, "assumption", "low", "valeur de brouillon BAR-TH-179 a valider")

    project = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "case_id": case["case_id"],
        "code": code,
        "client": case["client"],
        "site": case["site"],
        "visit": case.get("visit", {}),
        "fields": fields,
        "calculation": {"status": "missing_inputs", "kwh_cumac": None, "formula_text": None, "missing_inputs": [], "details": {}},
        "assumptions": [],
        "blocking_points": [],
    }
    project["fields"].update(infer_heat_losses(project))
    project["fields"].update(infer_pac_sizing(project))
    project["fields"].update(infer_works_scope(project))
    project["fields"].update(estimate_works_cost(project, load_pricebook()))
    project["calculation"] = compute_project(project)
    project["assumptions"] = [
        f"{name}: {item['status']} ({item['confidence']})"
        for name, item in sorted(project["fields"].items())
        if item.get("needs_human_validation")
    ]
    project["blocking_points"] = [
        name for name, item in sorted(project["fields"].items()) if item.get("status") == "blocking"
    ] + project["calculation"].get("missing_inputs", [])
    return project


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        project = build_project(load_json(Path(args.input)), args.code)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote inferred project to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
