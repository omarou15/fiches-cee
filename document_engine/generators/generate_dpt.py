from __future__ import annotations

from .render_template import header


def render(project: dict, company: dict, mode: str) -> str:
    return (
        header("DPT - brouillon", project, company)
        + "- Objet: preparation des donnees techniques pour dossier CEE.\n"
        + "- Statut: brouillon a completer avec les documents et plans reels.\n"
    )
