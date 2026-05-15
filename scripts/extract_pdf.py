"""Extract text from PDF files with page metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF is required. Install with: pip install -r requirements.txt") from exc


def extract_pdf_pages(path: Path) -> list[dict]:
    pages: list[dict] = []
    with fitz.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
            pages.append({"page": index, "text": text})
    return pages


def extract_pdf(path: Path) -> dict:
    pages = extract_pdf_pages(path)
    text = "\n\n".join(page["text"] for page in pages if page["text"]).strip()
    return {
        "source_file": str(path),
        "format": "pdf",
        "page_count": len(pages),
        "text_length": len(text),
        "pages": pages,
        "text": text,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/extract_pdf.py <pdf> [output.json]", file=sys.stderr)
        return 2
    source = Path(argv[1])
    data = extract_pdf(source)
    if len(argv) >= 3:
        Path(argv[2]).parent.mkdir(parents=True, exist_ok=True)
        Path(argv[2]).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
