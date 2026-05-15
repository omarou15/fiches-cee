"""Search generated CEE fiche indexes and chunks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = REPO_ROOT / "data" / "indexes"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def score_text(query_terms: list[str], text: str) -> int:
    low = text.lower()
    return sum(low.count(term) for term in query_terms)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="code or text query")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    fiches_path = INDEX_DIR / "fiches_cee_index.json"
    chunks_path = INDEX_DIR / "chunks_cee.jsonl"
    if not fiches_path.exists():
        raise SystemExit("Run scripts/build_indexes.py first.")

    fiches = load_json(fiches_path)
    query = args.query.strip()
    terms = [term.lower() for term in re.findall(r"[\wÀ-ÿ-]+", query)]
    results: dict[str, dict] = {}

    for fiche in fiches:
        haystack = f"{fiche['code']} {fiche['title']} {fiche.get('family', '')}".lower()
        score = 100 if fiche["code"].lower() == query.lower() else score_text(terms, haystack) * 10
        if score:
            results[fiche["code"]] = {
                "code": fiche["code"],
                "title": fiche["title"],
                "score": score,
                "json_path": fiche["json_path"],
                "markdown_path": fiche["markdown_path"],
                "source_files": fiche["source_files"],
                "excerpt": "",
            }

    if chunks_path.exists():
        with chunks_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                score = score_text(terms, chunk.get("text", "").lower())
                if score:
                    code = chunk["code"]
                    current = results.get(code, {
                        "code": code,
                        "title": chunk.get("title"),
                        "score": 0,
                        "json_path": f"data/json/{code}.json",
                        "markdown_path": f"data/markdown/{code}.md",
                        "source_files": [chunk.get("source_file")],
                        "excerpt": "",
                    })
                    current["score"] += score
                    if not current["excerpt"]:
                        text = chunk.get("text", "").replace("\n", " ")
                        current["excerpt"] = text[:350]
                    results[code] = current

    ordered = sorted(results.values(), key=lambda item: item["score"], reverse=True)[: args.limit]
    print(json.dumps(ordered, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
