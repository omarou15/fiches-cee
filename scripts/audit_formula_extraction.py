"""Audit formula extraction against the main PDF of each unique CEE fiche."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

from extract_pdf import extract_pdf_pages
from normalize_fiche import extract_formula_values, parse_sections


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD_TIMESTAMP = "2026-05-15T00:00:00+00:00"


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def normalize_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def value_keys(values: list[dict]) -> set[tuple[str, str, int]]:
    return {
        (item.get("type"), item.get("normalized"), item.get("line"))
        for item in values
        if item.get("type") and item.get("normalized") and item.get("line") is not None
    }


def known_missing_reason(row: dict, section5: dict | None) -> str | None:
    blob = f"{row.get('LibellePrincipal', '')} {row.get('CheminDepot', '')}".lower()
    if not section5 and "partie a" in blob:
        return "PDF principal indexe comme Partie A uniquement, sans section 5 de calcul."
    return None


def audit_row(row: dict) -> dict:
    code = row["Code"]
    source_file = row["CheminDepot"]
    source_path = REPO_ROOT / source_file
    json_path = REPO_ROOT / "data" / "json" / f"{code}.json"
    warnings: list[str] = []
    error: str | None = None
    section5: dict | None = None
    source_values: list[dict] = []
    json_values: list[dict] = []
    calculation: dict = {}

    try:
        pages = extract_pdf_pages(source_path)
        sections = parse_sections(pages)
        section5 = next((section for section in sections if section.get("number") == "5"), None)
    except Exception as exc:  # pragma: no cover - depends on local file corruption
        error = f"PDF read/parse error: {exc}"
        pages = []

    if json_path.exists():
        calculation = (load_json(json_path).get("calculation") or {})
        json_values = calculation.get("extracted_values") or []
    else:
        warnings.append("missing fiche JSON")

    reason = known_missing_reason(row, section5)
    if section5:
        source_text = section5.get("text") or ""
        source_values = extract_formula_values(source_text)
        if normalize_text(calculation.get("formula_section_text")) != normalize_text(source_text):
            warnings.append("formula_section_text does not match PDF section 5")
        missing_values = sorted(
            value_keys(source_values) - value_keys(json_values),
            key=lambda item: (item[2], item[0], item[1]),
        )
        if missing_values:
            warnings.append(f"{len(missing_values)} section 5 values missing from calculation.extracted_values")
        if calculation.get("formula_status") not in {"extracted", "validated"}:
            warnings.append(f"unexpected formula_status for present section 5: {calculation.get('formula_status')}")
    elif not reason:
        warnings.append("missing section 5 in source PDF")
        if calculation.get("formula_status") != "missing_section":
            warnings.append(f"formula_status should be missing_section, got {calculation.get('formula_status')}")

    if error:
        status = "failed"
    elif warnings:
        status = "needs_review"
    elif reason:
        status = "known_missing_source"
    else:
        status = "ok"

    return {
        "code": code,
        "sector": row["Secteur"],
        "source_file": source_file,
        "source_url": row.get("Url"),
        "page_count": len(pages),
        "section5_found": section5 is not None,
        "section5_page_start": section5.get("page_start") if section5 else None,
        "section5_page_end": section5.get("page_end") if section5 else None,
        "formula_status": calculation.get("formula_status"),
        "formula_text": calculation.get("formula_text"),
        "source_value_count": len(source_values),
        "json_value_count": len(json_values),
        "missing_value_count": max(0, len(value_keys(source_values) - value_keys(json_values))),
        "known_missing_reason": reason,
        "status": status,
        "warnings": warnings,
        "error": error,
    }


def build_summary(items: list[dict]) -> dict:
    return {
        "total_unique_fiches": len(items),
        "pdf_checked": len(items),
        "ok": sum(1 for item in items if item["status"] == "ok"),
        "known_missing_source": sum(1 for item in items if item["status"] == "known_missing_source"),
        "needs_review": sum(1 for item in items if item["status"] == "needs_review"),
        "failed": sum(1 for item in items if item["status"] == "failed"),
        "section5_found": sum(1 for item in items if item["section5_found"]),
        "section5_missing": sum(1 for item in items if not item["section5_found"]),
        "total_source_values": sum(item["source_value_count"] for item in items),
        "total_json_values": sum(item["json_value_count"] for item in items),
        "total_missing_values": sum(item["missing_value_count"] for item in items),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/indexes/formula_audit_report.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--fail-on-issues", action="store_true")
    args = parser.parse_args(argv)

    rows = read_csv(REPO_ROOT / "index_fiches_uniques.csv")
    selected = [row for row in rows if not args.only or row["Code"] in args.only]
    if args.limit:
        selected = selected[: args.limit]

    items = [audit_row(row) for row in selected]
    report = {
        "generated_at": os.environ.get("CEE_BUILD_TIMESTAMP", DEFAULT_BUILD_TIMESTAMP),
        "scope": "unique_fiche_main_pdf_formula_sections",
        "source_index": "index_fiches_uniques.csv",
        "summary": build_summary(items),
        "items": items,
    }
    write_json(REPO_ROOT / args.output, report)
    summary = report["summary"]
    print(
        "Audited {total_unique_fiches} formula sections: {ok} ok, "
        "{known_missing_source} known_missing_source, {needs_review} needs_review, "
        "{failed} failed, {total_missing_values} missing values.".format(**summary)
    )
    if args.fail_on_issues and (summary["needs_review"] or summary["failed"] or summary["total_missing_values"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
