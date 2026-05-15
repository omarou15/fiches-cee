"""Build extracted text, Markdown, JSON fiches, chunks and global indexes."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import unicodedata
from pathlib import Path

from extract_office import extract_office
from extract_pdf import extract_pdf_pages
from normalize_fiche import normalize_fiche


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
TEXT_DIR = DATA_DIR / "text"
MARKDOWN_DIR = DATA_DIR / "markdown"
JSON_DIR = DATA_DIR / "json"
INDEX_DIR = DATA_DIR / "indexes"
CURATED_DIR = DATA_DIR / "curated"
DEFAULT_BUILD_TIMESTAMP = "2026-05-15T00:00:00+00:00"


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def apply_curated_override(fiche: dict) -> dict:
    path = CURATED_DIR / f"{fiche['code']}.json"
    if not path.exists():
        return fiche
    return deep_merge(fiche, load_json(path))


def normalize_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def term_matches(text: str, term: str) -> bool:
    if term == "PAC":
        return re.search(r"\bPAC\b", text) is not None or "pompe à chaleur" in text.lower() or "pompe a chaleur" in normalize_ascii(text)
    if term in {"ECS", "GTB"}:
        return re.search(rf"\b{term}\b", text) is not None
    return normalize_ascii(term) in normalize_ascii(text)


def classify_document(label: str, path: str) -> str:
    blob = f"{label} {path}".lower()
    if "partie a" in blob:
        return "partie_a"
    if "annexe" in blob:
        return "annexe"
    if "feuille" in blob or path.lower().endswith((".xls", ".xlsx")):
        return "feuille_recapitulative"
    if path.lower().endswith(".pdf"):
        return "fiche_principale"
    return "other"


def extract_text(path: Path) -> tuple[str, list[dict], list[str]]:
    warnings: list[str] = []
    if not path.exists():
        return "", [], [f"missing file: {path}"]
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            pages = extract_pdf_pages(path)
            text = "\n\n".join(page["text"] for page in pages if page["text"]).strip()
            return text, pages, warnings
        if suffix in {".docx", ".xlsx"}:
            text = extract_office(path)
            return text, [{"page": 1, "text": text}], warnings
        if suffix in {".html", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            return text, [{"page": 1, "text": text}], warnings
    except Exception as exc:
        return "", [], [str(exc)]
    return "", [], [f"unsupported format: {suffix}"]


def split_chunks(text: str, code: str, meta: dict, source_file: str, pages: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    if pages:
        for page in pages:
            page_text = (page.get("text") or "").strip()
            if not page_text:
                continue
            parts = re.split(r"\n\s*\n", page_text)
            buffer = ""
            chunk_no = 1
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if len(buffer) + len(part) > 1800 and buffer:
                    chunks.append(make_chunk(code, meta, source_file, page["page"], page["page"], chunk_no, buffer))
                    chunk_no += 1
                    buffer = part
                else:
                    buffer = f"{buffer}\n\n{part}".strip()
            if buffer:
                chunks.append(make_chunk(code, meta, source_file, page["page"], page["page"], chunk_no, buffer))
    elif text:
        chunks.append(make_chunk(code, meta, source_file, None, None, 1, text[:1800]))
    return chunks


def make_chunk(code: str, meta: dict, source_file: str, page_start: int | None, page_end: int | None, chunk_no: int, text: str) -> dict:
    section_title = infer_section_title(text)
    return {
        "chunk_id": f"{code}__{meta.get('document_type', 'document')}__p{page_start or 0}__{chunk_no:03d}",
        "code": code,
        "sector": meta.get("sector"),
        "family": meta.get("family"),
        "title": meta.get("title"),
        "document_type": meta.get("document_type"),
        "source_file": source_file,
        "source_url": meta.get("source_url"),
        "page_start": page_start,
        "page_end": page_end,
        "section_title": section_title,
        "text": text,
        "keywords": infer_keywords(text),
        "extraction_confidence": "medium",
    }


def infer_section_title(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if 5 <= len(line) <= 90 and not line.endswith("."):
            return line
    return None


def infer_keywords(text: str) -> list[str]:
    candidates = [
        "PAC", "pompe à chaleur", "chauffage", "collectif", "hybride", "gaz", "ECS",
        "chaudière", "calorifugeage", "réseau de chaleur", "GTB", "régulation",
        "ventilation", "isolation", "cumac", "contrôle", "attestation",
    ]
    low = text.lower()
    return [keyword for keyword in candidates if keyword.lower() in low]


def markdown_for_fiche(fiche: dict, main_text: str) -> str:
    sections = [
        f"# {fiche['code']} - {fiche['title']}",
        f"- Secteur: {fiche['sector']}",
        f"- Famille: {fiche['family']}",
        f"- Version: {fiche.get('document_version') or 'unknown'}",
        f"- Date d'application: {fiche.get('effective_date') or 'unknown'}",
        "",
        "## Documents sources",
        "\n".join(f"- `{path}`" for path in fiche["source_files"]),
        "",
        "## Extraction automatique",
        f"- Statut: {fiche['extraction']['status']}",
        f"- Revue humaine requise: {fiche['extraction']['needs_human_review']}",
        f"- Notes: {fiche['extraction'].get('notes') or ''}",
        "",
        "## Conditions detectees",
        "\n".join(f"- {item['text']}" for item in fiche.get("eligibility_conditions", [])) or "_Non detecte automatiquement._",
        "",
        "## Exigences techniques detectees",
        "\n".join(f"- {item['text']}" for item in fiche.get("technical_requirements", [])) or "_Non detecte automatiquement._",
        "",
        "## Pieces justificatives detectees",
        "\n".join(f"- {item['text']}" for item in fiche.get("required_documents", [])) or "_Non detecte automatiquement._",
        "",
        "## Formules / calcul detectes",
        "\n".join(f"- {item['text']}" for item in fiche.get("formulas", [])) or "_Non detecte automatiquement._",
        "",
        "## Sections officielles detectees",
        "\n".join(f"- {section['number']}. {section['title']} (pages {section.get('page_start')}-{section.get('page_end')})" for section in fiche.get("sections", [])) or "_Non detecte automatiquement._",
        "",
        "## Donnees Energyco structurees",
        f"- Titre propre: {fiche.get('title_clean') or ''}",
        f"- Secteur d'application: {fiche.get('application_sector') or ''}",
        f"- Duree de vie: {fiche.get('lifetime_years') or ''}",
        f"- Date limite engagement: {(fiche.get('validity') or {}).get('engagement_deadline') or ''}",
        "",
        "## Texte extrait",
        main_text,
    ]
    return "\n".join(sections).strip() + "\n"


def build_keyword_hits_index(fiches: list[dict]) -> list[dict]:
    priority_terms = {
        "PAC": ["PAC", "pompe à chaleur", "pompe a chaleur"],
        "PAC collective": ["collective", "collectif"],
        "chaudière": ["chaudière", "chaudiere"],
        "système hybride PAC + gaz": ["hybride", "gaz"],
        "chauffage collectif": ["chauffage", "collectif"],
        "ECS": ["eau chaude sanitaire", "ECS"],
        "calorifugeage": ["calorifugeage"],
        "réseau de chaleur": ["réseau de chaleur", "reseau de chaleur"],
        "régulation": ["régulation", "regulation"],
        "GTB": ["GTB", "gestion technique"],
        "ventilation": ["ventilation"],
        "isolation": ["isolation"],
        "résidentiel collectif": ["résidentiel", "residentiel", "collectif"],
        "tertiaire": ["tertiaire"],
    }
    entries: list[dict] = []
    for fiche in fiches:
        blob = f"{fiche['code']} {fiche['title']} {fiche.get('title_clean', '')}"
        tags = [tag for tag, terms in priority_terms.items() if any(term_matches(blob, term) for term in terms)]
        if tags:
            entries.append({
                "code": fiche["code"],
                "sector": fiche["sector"],
                "family": fiche["family"],
                "keyword_hits": tags,
                "title": fiche["title"],
                "json_path": f"data/json/{fiche['code']}.json",
                "markdown_path": f"data/markdown/{fiche['code']}.md",
            })
    return entries


def build_energyco_priority(fiches: list[dict], keyword_hits: list[dict]) -> list[dict]:
    allowed_prefixes = {"BAR", "BAT", "RES"}
    explicit_high = {"BAR-TH-179", "BAR-TH-163", "BAR-TH-137", "BAT-TH-116", "BAT-TH-163", "BAT-TH-164", "RES-CH-106"}
    hit_by_code = {item["code"]: item["keyword_hits"] for item in keyword_hits}
    entries: list[dict] = []
    for fiche in fiches:
        prefix = fiche["code"].split("-", 1)[0]
        tags = hit_by_code.get(fiche["code"], [])
        in_scope = prefix in allowed_prefixes
        has_energyco_tag = any(tag in tags for tag in [
            "PAC", "chaudière", "système hybride PAC + gaz", "chauffage collectif", "ECS",
            "calorifugeage", "réseau de chaleur", "régulation", "GTB", "ventilation",
            "isolation", "résidentiel collectif", "tertiaire",
        ])
        if fiche["code"] in explicit_high or (in_scope and has_energyco_tag):
            entries.append({
                "code": fiche["code"],
                "priority": "high" if fiche["code"] in explicit_high or {"PAC", "chauffage collectif", "GTB", "calorifugeage"} & set(tags) else "medium",
                "energyco_use_cases": tags,
                "why_important": "Fiche liée aux cas Energyco chauffage, PAC, régulation, réseaux ou enveloppe.",
                "required_site_data": fiche.get("site_data_requirements", []),
                "energyco_site_data_requirements": fiche.get("energyco_site_data_requirements", []),
                "risk_points": fiche.get("risks", []),
                "energyco_risks": fiche.get("energyco_risks", []),
                "json_path": f"data/json/{fiche['code']}.json",
                "markdown_path": f"data/markdown/{fiche['code']}.md",
            })
    return entries


def build_formulas_index(fiches: list[dict]) -> list[dict]:
    entries: list[dict] = []
    for fiche in fiches:
        calculation = fiche.get("calculation") or {}
        variables = calculation.get("variables") or []
        entries.append({
            "code": fiche["code"],
            "sector": fiche["sector"],
            "family": fiche["family"],
            "title": fiche["title"],
            "formula_status": calculation.get("formula_status") or "unknown",
            "formula_text": calculation.get("formula_text"),
            "unit": calculation.get("unit"),
            "variables": variables,
            "variable_names": [variable.get("name") for variable in variables if variable.get("name")],
            "expressions": calculation.get("expressions") or [],
            "calculation_methods": calculation.get("calculation_methods") or [],
            "amount_table_count": len(calculation.get("amount_table") or []),
            "formula_section_title": calculation.get("formula_section_title"),
            "formula_section_text": calculation.get("formula_section_text"),
            "page_start": calculation.get("formula_section_page_start"),
            "page_end": calculation.get("formula_section_page_end"),
            "source_file": calculation.get("source_file") or (fiche.get("source_files") or [None])[0],
            "confidence": calculation.get("confidence"),
            "needs_human_review": fiche.get("extraction", {}).get("needs_human_review"),
            "json_path": f"data/json/{fiche['code']}.json",
            "markdown_path": f"data/markdown/{fiche['code']}.md",
        })
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="limit number of unique fiches, for testing")
    parser.add_argument("--only", nargs="*", default=[], help="specific fiche codes")
    args = parser.parse_args()

    for directory in [TEXT_DIR, MARKDOWN_DIR, JSON_DIR, INDEX_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    unique_rows = read_csv(REPO_ROOT / "index_fiches_uniques.csv")
    doc_rows = read_csv(REPO_ROOT / "index_fiches_cee.csv")
    rows_by_code: dict[str, list[dict]] = {}
    for row in doc_rows:
        match = re.match(r"^(AGRI|BAR|BAT|IND|RES|TRA)-[A-Z]+-\d+", row.get("Libelle", ""))
        code = match.group(0) if match else None
        if code:
            row["DocumentType"] = classify_document(row.get("Libelle", ""), row.get("CheminDepot", ""))
            rows_by_code.setdefault(code, []).append(row)

    selected = [row for row in unique_rows if not args.only or row["Code"] in args.only]
    if args.limit:
        selected = selected[: args.limit]

    fiches_index: list[dict] = []
    documents_index: list[dict] = []
    chunks: list[dict] = []
    report_items: list[dict] = []
    fiches: list[dict] = []

    for row in selected:
        code = row["Code"]
        related = rows_by_code.get(code, [])
        main_path = REPO_ROOT / row["CheminDepot"]
        main_text, main_pages, warnings = extract_text(main_path)
        (TEXT_DIR / f"{code}.txt").write_text(main_text, encoding="utf-8", newline="\n")
        fiche = normalize_fiche(row, related, main_text, main_pages)
        fiche = apply_curated_override(fiche)
        write_json(JSON_DIR / f"{code}.json", fiche)
        (MARKDOWN_DIR / f"{code}.md").write_text(markdown_for_fiche(fiche, main_text), encoding="utf-8", newline="\n")
        fiches.append(fiche)

        meta = {
            "sector": fiche["sector"],
            "family": fiche["family"],
            "title": fiche["title"],
            "document_type": "fiche_principale",
            "source_url": row.get("Url"),
        }
        chunks.extend(split_chunks(main_text, code, meta, row["CheminDepot"], main_pages))
        fiches_index.append({
            "code": code,
            "sector": fiche["sector"],
            "family": fiche["family"],
            "title": fiche["title"],
            "title_clean": fiche.get("title_clean"),
            "version": fiche.get("document_version"),
            "effective_date": fiche.get("effective_date"),
            "json_path": f"data/json/{code}.json",
            "markdown_path": f"data/markdown/{code}.md",
            "text_path": f"data/text/{code}.txt",
            "source_files": fiche["source_files"],
            "extraction_status": fiche["extraction"]["status"],
            "needs_human_review": fiche["extraction"]["needs_human_review"],
        })
        for doc in fiche["related_documents"]:
            documents_index.append(doc)
        report_items.append({
            "source_file": row["CheminDepot"],
            "output_files": [f"data/text/{code}.txt", f"data/markdown/{code}.md", f"data/json/{code}.json"],
            "status": fiche["extraction"]["status"],
            "text_length": len(main_text),
            "warnings": warnings,
            "error": None,
        })

    write_json(INDEX_DIR / "fiches_cee_index.json", fiches_index)
    write_json(INDEX_DIR / "documents_cee_index.json", documents_index)
    (INDEX_DIR / "chunks_cee.jsonl").write_text(
        "\n".join(json.dumps(chunk, ensure_ascii=False) for chunk in chunks) + ("\n" if chunks else ""),
        encoding="utf-8",
        newline="\n",
    )
    keyword_hits = build_keyword_hits_index(fiches)
    write_json(INDEX_DIR / "keyword_hits_index.json", keyword_hits)
    write_json(INDEX_DIR / "energyco_priority_index.json", build_energyco_priority(fiches, keyword_hits))
    write_json(INDEX_DIR / "formulas_cee_index.json", build_formulas_index(fiches))

    failed = [item for item in report_items if item["status"] == "failed"]
    needs_review = [item for item in report_items if item["status"] == "needs_review"]
    report = {
        "generated_at": os.environ.get("CEE_BUILD_TIMESTAMP", DEFAULT_BUILD_TIMESTAMP),
        "tool_version": "0.1.0",
        "summary": {
            "total_documents": len(doc_rows),
            "total_unique_fiches": len(unique_rows),
            "processed_unique_fiches": len(selected),
            "total_pdf": sum(1 for row in doc_rows if row.get("CheminDepot", "").lower().endswith(".pdf")),
            "total_office": sum(1 for row in doc_rows if row.get("CheminDepot", "").lower().endswith((".doc", ".docx", ".xls", ".xlsx"))),
            "total_html": len(list((REPO_ROOT / "_CEE_complements").glob("**/*.html"))) if (REPO_ROOT / "_CEE_complements").exists() else 0,
            "fiches_with_json": len(fiches_index),
            "fiches_with_markdown": len(fiches_index),
            "fiches_with_empty_text": sum(1 for item in report_items if not item["text_length"]),
            "fiches_needing_review": len(needs_review),
            "fiches_missing_required_documents": sum(1 for fiche in fiches if not fiche.get("required_documents")),
            "fiches_missing_calculation": sum(1 for fiche in fiches if not fiche.get("formulas")),
            "extracted": len(report_items) - len(failed),
            "failed": len(failed),
            "needs_review": len(needs_review),
        },
        "priority_failures": [
            {"code": item["source_file"], "reason": "; ".join(item["warnings"]) or "needs review", "severity": "high"}
            for item in report_items
            if item["status"] in {"failed", "needs_review"} and any(code in item["source_file"] for code in ["BAR-TH-179", "BAT-TH-116", "RES-CH-106"])
        ],
        "items": report_items,
    }
    write_json(INDEX_DIR / "extraction_report.json", report)
    print(f"Built {len(fiches_index)} fiche JSON files and {len(chunks)} chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
