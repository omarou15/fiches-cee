"""Validate inferred CEE project readiness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = REPO_ROOT / "rules"
CURATED_DIR = REPO_ROOT / "data" / "curated"
JSON_DIR = REPO_ROOT / "data" / "json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == "unknown"


def get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def reference_paths(code: str) -> dict[str, Path]:
    return {
        "rules": RULES_DIR / f"{code}.rules.json",
        "curated": CURATED_DIR / f"{code}.json",
        "json": JSON_DIR / f"{code}.json",
    }


def load_reference(code: str) -> tuple[dict[str, Any] | None, str, Path | None, list[dict[str, Any]]]:
    paths = reference_paths(code)
    warnings: list[dict[str, Any]] = []
    if paths["rules"].exists():
        return load_json(paths["rules"]), "rules", paths["rules"], warnings
    if paths["curated"].exists():
        warnings.append(
            {
                "id": "rules_not_found",
                "severity": "warning",
                "message": f"No machine-readable rules file found for {code}; validation used curated fiche data only.",
                "path": paths["curated"].relative_to(REPO_ROOT).as_posix(),
            }
        )
        return load_json(paths["curated"]), "curated", paths["curated"], warnings
    if paths["json"].exists():
        warnings.append(
            {
                "id": "rules_not_found",
                "severity": "warning",
                "message": f"No machine-readable rules file found for {code}; validation used extracted fiche data only.",
                "path": paths["json"].relative_to(REPO_ROOT).as_posix(),
            }
        )
        return load_json(paths["json"]), "json", paths["json"], warnings
    warnings.append(
        {
            "id": "reference_not_found",
            "severity": "warning",
            "message": f"No local rules, curated JSON, or extracted JSON reference found for {code}.",
            "path": None,
        }
    )
    return None, "missing", None, warnings


def normalize_blocking_point(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("field_path", "field", "id", "name"):
            if item.get(key):
                return str(item[key])
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def field_item_is_present(item: Any) -> bool:
    if isinstance(item, dict):
        if item.get("status") in {"missing", "blocking"}:
            return False
        if "value" in item:
            return not is_missing(item.get("value"))
        return True
    return not is_missing(item)


def project_has_required_field(project: dict[str, Any], field: str) -> bool:
    fields = project.get("fields", {})
    candidates = [
        field,
        f"operation.{field}",
        f"site.{field}",
        f"technical.{field}",
        f"calculation.{field}",
    ]
    for candidate in candidates:
        if isinstance(fields, dict) and candidate in fields:
            return field_item_is_present(fields[candidate])
        value = get_path(project, candidate)
        if not is_missing(value):
            return True
    return False


def document_is_present(project: dict[str, Any], document_id: str) -> bool:
    documents = project.get("documents")
    if not isinstance(documents, dict):
        return False
    item = documents.get(document_id)
    if isinstance(item, dict):
        return item.get("provided") is True or item.get("status") in {"received", "confirmed"}
    return item is True


def add_rules_blocking_points(project: dict[str, Any], rules: dict[str, Any], blocking: list[str]) -> None:
    for field in rules.get("required_fields", []):
        if not project_has_required_field(project, str(field)):
            blocking.append(str(field))
    for document_id in rules.get("strict_blocking_documents", []):
        if not document_is_present(project, str(document_id)):
            blocking.append(f"documents.{document_id}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--code", help="Optional fiche code used to load rules/{CODE}.rules.json or fiche JSON.")
    args = parser.parse_args()

    project = load_json(Path(args.input))
    code = str(args.code or project.get("code") or project.get("fiche_code") or "").strip().upper() or None
    blocking = [normalize_blocking_point(item) for item in (project.get("blocking_points") or [])]
    warnings: list[dict[str, Any]] = []
    reference_source = None
    reference_path = None
    reference_conditions_count = 0

    if args.strict:
        blocking.extend(
            name
            for name, item in project.get("fields", {}).items()
            if isinstance(item, dict) and item.get("status") in {"estimated", "assumption", "missing", "blocking"}
        )

    if code:
        reference, reference_source, reference_path, reference_warnings = load_reference(code)
        warnings.extend(reference_warnings)
        if reference_source == "rules" and isinstance(reference, dict):
            add_rules_blocking_points(project, reference, blocking)
        elif isinstance(reference, dict):
            conditions = reference.get("eligibility_conditions")
            if isinstance(conditions, list):
                reference_conditions_count = len(conditions)

    result = {
        "case_id": project.get("case_id"),
        "code": code or project.get("code"),
        "reference_source": reference_source,
        "reference_path": reference_path.relative_to(REPO_ROOT).as_posix() if reference_path else None,
        "reference_conditions_count": reference_conditions_count,
        "valid": not blocking,
        "blocking_points": sorted(set(blocking)),
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
