from __future__ import annotations

from pathlib import Path

from .render_template import render_template_file


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = REPO_ROOT / "document_engine" / "templates" / "controle" / "checklist_pieces.md"


def generate(company: dict, operation: dict, output_path: Path, code: str = "BAR-TH-179") -> None:
    render_template_file(TEMPLATE, company, operation, output_path, code=code)
