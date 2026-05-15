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

    if errors:
        print("Validation failed:")
        for error in errors[:50]:
            print(f"- {error}")
        return 1
    print(f"Validation OK: {len(fiche_files)} fiche JSON files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
