"""Audit the main PDF of each unique CEE fiche.

This intentionally checks only index_fiches_uniques.csv. It does not audit
Partie A files, annexes, recap spreadsheets, general documents or complements.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from extract_pdf import extract_pdf_pages


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = REPO_ROOT / "data" / "indexes"
DEFAULT_BUILD_TIMESTAMP = "2026-05-15T00:00:00+00:00"


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def audit_row(row: dict) -> dict:
    code = row["Code"]
    source_file = row["CheminDepot"]
    source_path = REPO_ROOT / source_file
    json_path = REPO_ROOT / "data" / "json" / f"{code}.json"
    markdown_path = REPO_ROOT / "data" / "markdown" / f"{code}.md"
    text_path = REPO_ROOT / "data" / "text" / f"{code}.txt"

    warnings: list[str] = []
    error: str | None = None
    pages: list[dict] = []
    extracted_text = ""

    if not source_path.exists():
        error = "missing source PDF"
    elif source_path.suffix.lower() != ".pdf":
        error = f"source is not a PDF: {source_path.suffix}"
    else:
        try:
            pages = extract_pdf_pages(source_path)
            extracted_text = "\n\n".join(page["text"] for page in pages if page["text"]).strip()
        except Exception as exc:  # pragma: no cover - depends on corrupt local files
            error = f"unreadable PDF: {exc}"

    page_count = len(pages)
    pages_with_text = sum(1 for page in pages if (page.get("text") or "").strip())
    text_length = len(extracted_text)
    code_found = bool(extracted_text and code in extracted_text)

    generated_json_exists = json_path.exists()
    generated_markdown_exists = markdown_path.exists()
    generated_text_exists = text_path.exists()
    generated_text_matches_pdf = False

    if not error:
        if page_count <= 0:
            warnings.append("PDF has no pages")
        if text_length <= 0:
            warnings.append("PDF text extraction is empty")
        if not code_found:
            warnings.append("fiche code not found in extracted PDF text")

    if not generated_json_exists:
        warnings.append("missing generated JSON")
    if not generated_markdown_exists:
        warnings.append("missing generated Markdown")
    if not generated_text_exists:
        warnings.append("missing generated text")
    elif not error:
        generated_text = read_text(text_path).strip()
        generated_text_matches_pdf = generated_text == extracted_text
        if not generated_text_matches_pdf:
            warnings.append("generated text does not match current PDF extraction")

    if error:
        status = "failed"
    elif warnings:
        status = "needs_review"
    else:
        status = "ok"

    return {
        "code": code,
        "sector": row["Secteur"],
        "source_file": source_file,
        "source_url": row.get("Url"),
        "exists": source_path.exists(),
        "page_count": page_count,
        "pages_with_text": pages_with_text,
        "text_length": text_length,
        "code_found_in_text": code_found,
        "generated_json_exists": generated_json_exists,
        "generated_markdown_exists": generated_markdown_exists,
        "generated_text_exists": generated_text_exists,
        "generated_text_matches_pdf": generated_text_matches_pdf,
        "status": status,
        "warnings": warnings,
        "error": error,
    }


def build_summary(items: list[dict]) -> dict:
    return {
        "total_unique_fiches": len(items),
        "pdf_checked": len(items),
        "ok": sum(1 for item in items if item["status"] == "ok"),
        "needs_review": sum(1 for item in items if item["status"] == "needs_review"),
        "failed": sum(1 for item in items if item["status"] == "failed"),
        "missing_pdf": sum(1 for item in items if not item["exists"]),
        "unreadable_pdf": sum(1 for item in items if (item.get("error") or "").startswith("unreadable PDF")),
        "empty_text": sum(1 for item in items if item["text_length"] == 0),
        "code_not_found_in_text": sum(1 for item in items if not item["code_found_in_text"]),
        "missing_generated_json": sum(1 for item in items if not item["generated_json_exists"]),
        "missing_generated_markdown": sum(1 for item in items if not item["generated_markdown_exists"]),
        "missing_generated_text": sum(1 for item in items if not item["generated_text_exists"]),
        "generated_text_mismatch": sum(1 for item in items if not item["generated_text_matches_pdf"]),
        "total_pages": sum(item["page_count"] for item in items),
        "total_text_length": sum(item["text_length"] for item in items),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/indexes/pdf_audit_unique_fiches.json")
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
        "scope": "unique_fiche_main_pdfs_only",
        "source_index": "index_fiches_uniques.csv",
        "excluded": [
            "partie_a",
            "annexes",
            "feuilles_recapitulatives",
            "documents_generaux",
            "cee_complements",
        ],
        "summary": build_summary(items),
        "items": items,
    }
    output_path = REPO_ROOT / args.output
    write_json(output_path, report)

    summary = report["summary"]
    print(
        "Audited {total_unique_fiches} unique fiche PDFs: {ok} ok, "
        "{needs_review} needs_review, {failed} failed.".format(**summary)
    )
    if args.fail_on_issues and (summary["needs_review"] or summary["failed"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
