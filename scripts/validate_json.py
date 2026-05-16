"""Validate generated fiche JSON files and index integrity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    schema_path = REPO_ROOT / "schemas" / "fiche_cee.schema.json"
    schema = load_json(schema_path)
    json_dir = REPO_ROOT / "data" / "json"
    index_path = REPO_ROOT / "data" / "indexes" / "fiches_cee_index.json"
    chunks_path = REPO_ROOT / "data" / "indexes" / "chunks_cee.jsonl"
    report_path = REPO_ROOT / "data" / "indexes" / "extraction_report.json"
    pdf_audit_path = REPO_ROOT / "data" / "indexes" / "pdf_audit_unique_fiches.json"
    formulas_index_path = REPO_ROOT / "data" / "indexes" / "formulas_cee_index.json"
    formula_audit_path = REPO_ROOT / "data" / "indexes" / "formula_audit_report.json"
    dossier_examples_dir = REPO_ROOT / "examples" / "dossier_agent"
    minimal_case_path = REPO_ROOT / "inference_engine" / "examples" / "synthetic_minimal_case_bar_th_179.json"
    synthetic_company_path = REPO_ROOT / "document_engine" / "examples" / "synthetic_company_profile.json"

    fiche_files = sorted(json_dir.glob("*.json"))
    if not fiche_files:
        errors.append("No fiche JSON files found.")

    for path in fiche_files:
        data = load_json(path)
        if jsonschema:
            try:
                jsonschema.validate(data, schema)
            except Exception as exc:
                errors.append(f"{path.name}: schema error: {exc}")
        for field in ["code", "sector", "family", "title", "source_files"]:
            if not data.get(field):
                errors.append(f"{path.name}: missing {field}")

    if index_path.exists():
        index = load_json(index_path)
        indexed_codes = {item["code"] for item in index}
        json_codes = {path.stem for path in fiche_files}
        missing = sorted(indexed_codes - json_codes)
        if missing:
            errors.append(f"Index codes missing JSON: {missing[:10]}")
    else:
        errors.append("Missing data/indexes/fiches_cee_index.json")

    if chunks_path.exists():
        with chunks_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                chunk = json.loads(line)
                for field in ["chunk_id", "code", "source_file", "document_type", "text"]:
                    if not chunk.get(field):
                        errors.append(f"chunk line {line_no}: missing {field}")
    else:
        errors.append("Missing data/indexes/chunks_cee.jsonl")

    if report_path.exists() and jsonschema:
        try:
            jsonschema.validate(
                load_json(report_path),
                load_json(REPO_ROOT / "schemas" / "extraction_report.schema.json"),
            )
        except Exception as exc:
            errors.append(f"extraction_report.json: schema error: {exc}")
    elif not report_path.exists():
        errors.append("Missing data/indexes/extraction_report.json")

    if pdf_audit_path.exists() and jsonschema:
        try:
            jsonschema.validate(
                load_json(pdf_audit_path),
                load_json(REPO_ROOT / "schemas" / "pdf_audit.schema.json"),
            )
        except Exception as exc:
            errors.append(f"pdf_audit_unique_fiches.json: schema error: {exc}")

    if formulas_index_path.exists() and jsonschema:
        try:
            jsonschema.validate(
                load_json(formulas_index_path),
                load_json(REPO_ROOT / "schemas" / "formulas_cee_index.schema.json"),
            )
        except Exception as exc:
            errors.append(f"formulas_cee_index.json: schema error: {exc}")

    if formula_audit_path.exists():
        report = load_json(formula_audit_path)
        if jsonschema:
            try:
                jsonschema.validate(
                    report,
                    load_json(REPO_ROOT / "schemas" / "formula_audit.schema.json"),
                )
            except Exception as exc:
                errors.append(f"formula_audit_report.json: schema error: {exc}")
        summary = report.get("summary", {})
        if summary.get("needs_review") or summary.get("failed") or summary.get("total_missing_values"):
            errors.append("formula_audit_report.json: unresolved formula audit issues")

    if dossier_examples_dir.exists() and jsonschema:
        client_operation_schema = load_json(REPO_ROOT / "schemas" / "client_operation.schema.json")
        for example_path in sorted(dossier_examples_dir.glob("*.json")):
            try:
                jsonschema.validate(load_json(example_path), client_operation_schema)
            except Exception as exc:
                errors.append(f"{example_path.name}: client operation schema error: {exc}")

    if minimal_case_path.exists() and jsonschema:
        try:
            jsonschema.validate(
                load_json(minimal_case_path),
                load_json(REPO_ROOT / "inference_engine" / "schemas" / "minimal_case_input.schema.json"),
            )
        except Exception as exc:
            errors.append(f"{minimal_case_path.name}: minimal case schema error: {exc}")

    if synthetic_company_path.exists() and jsonschema:
        try:
            jsonschema.validate(
                load_json(synthetic_company_path),
                load_json(REPO_ROOT / "document_engine" / "schemas" / "company_profile.schema.json"),
            )
        except Exception as exc:
            errors.append(f"{synthetic_company_path.name}: company profile schema error: {exc}")

    if errors:
        print("Validation failed:")
        for error in errors[:50]:
            print(f"- {error}")
        return 1
    print(f"Validation OK: {len(fiche_files)} fiche JSON files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
