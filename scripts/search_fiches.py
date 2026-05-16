"""Search generated CEE fiche indexes and chunks."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = REPO_ROOT / "data" / "indexes"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def query_terms(query: str) -> list[str]:
    return [normalize(term) for term in re.findall(r"[\wÀ-ÿ-]+", query) if term.strip()]


def score_text(terms: list[str], text: str, weight: int = 1) -> int:
    low = normalize(text)
    return sum(low.count(term) for term in terms) * weight


def load_chunks(path: Path) -> list[dict]:
    if not path.exists():
        return []
    chunks: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks


def filter_fiche(fiche: dict, args: argparse.Namespace, priority_codes: set[str]) -> bool:
    if args.code and fiche["code"] != args.code:
        return False
    if args.sector and fiche.get("sector") != args.sector:
        return False
    if args.family and fiche.get("family") != args.family:
        return False
    if args.common_use_cases and fiche["code"] not in priority_codes:
        return False
    return True


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="", help="code or text query")
    parser.add_argument("--code", help="restrict to one fiche code")
    parser.add_argument("--sector", help="filter by normalized sector, e.g. residentiel")
    parser.add_argument("--family", help="filter by family, e.g. TH")
    parser.add_argument("--common-use-cases", action="store_true", help="search only common installer use-case fiches")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument("--markdown", action="store_true", help="emit Markdown output")
    args = parser.parse_args()

    fiches_path = INDEX_DIR / "fiches_cee_index.json"
    chunks_path = INDEX_DIR / "chunks_cee.jsonl"
    priority_path = INDEX_DIR / "common_use_cases_index.json"
    if not fiches_path.exists():
        raise SystemExit("Run scripts/build_indexes.py first.")

    fiches = load_json(fiches_path)
    chunks = load_chunks(chunks_path)
    priority_codes = {item["code"] for item in load_json(priority_path)} if priority_path.exists() else set()
    terms = query_terms(args.query or args.code or "")
    exact_query = (args.query or args.code or "").strip().upper()
    results: dict[str, dict] = {}

    for fiche in fiches:
        if not filter_fiche(fiche, args, priority_codes):
            continue
        haystack_title = f"{fiche['code']} {fiche['title']} {fiche.get('title_clean') or ''} {fiche.get('family', '')}"
        score = 0
        if fiche["code"].upper() == exact_query:
            score += 10000
        score += score_text(terms, haystack_title, weight=30)
        if score:
            results[fiche["code"]] = {
                "code": fiche["code"],
                "title": fiche["title"],
                "score": score,
                "json_path": fiche["json_path"],
                "markdown_path": fiche["markdown_path"],
                "source_files": fiche["source_files"],
                "best_chunk": None,
                "excerpt": "",
            }

    fiche_by_code = {fiche["code"]: fiche for fiche in fiches if filter_fiche(fiche, args, priority_codes)}
    for chunk in chunks:
        code = chunk["code"]
        if code not in fiche_by_code:
            continue
        score = score_text(terms, f"{chunk.get('section_title') or ''} {chunk.get('text') or ''}", weight=2)
        score += score_text(terms, " ".join(chunk.get("keywords") or []), weight=8)
        if score:
            fiche = fiche_by_code[code]
            current = results.get(code, {
                "code": code,
                "title": fiche.get("title") or chunk.get("title"),
                "score": 0,
                "json_path": fiche.get("json_path", f"data/json/{code}.json"),
                "markdown_path": fiche.get("markdown_path", f"data/markdown/{code}.md"),
                "source_files": fiche.get("source_files", [chunk.get("source_file")]),
                "best_chunk": None,
                "excerpt": "",
            })
            current["score"] += score
            if not current["best_chunk"] or score > current["best_chunk"]["score"]:
                text = (chunk.get("text") or "").replace("\n", " ")
                current["best_chunk"] = {
                    "score": score,
                    "source_file": chunk.get("source_file"),
                    "page_start": chunk.get("page_start"),
                    "page_end": chunk.get("page_end"),
                    "section_title": chunk.get("section_title"),
                    "chunk_id": chunk.get("chunk_id"),
                }
                current["excerpt"] = text[:500]
            results[code] = current

    ordered = sorted(results.values(), key=lambda item: item["score"], reverse=True)[: args.limit]
    if args.markdown and not args.json:
        for item in ordered:
            chunk = item.get("best_chunk") or {}
            print(f"## {item['code']} - {item['title']}")
            print(f"- Score: {item['score']}")
            print(f"- JSON: `{item['json_path']}`")
            print(f"- Markdown: `{item['markdown_path']}`")
            if chunk:
                print(f"- Source: `{chunk.get('source_file')}` page {chunk.get('page_start')}")
                print(f"- Section: {chunk.get('section_title') or ''}")
            print()
            if item.get("excerpt"):
                print(item["excerpt"])
                print()
        return 0

    print(json.dumps(ordered, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
