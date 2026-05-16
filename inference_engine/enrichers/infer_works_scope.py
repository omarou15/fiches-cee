from __future__ import annotations

from .common import field


def infer_works_scope(project: dict) -> dict:
    return {
        "works_scope": field(
            [
                "fourniture PAC collective air/eau",
                "pose PAC",
                "raccordement hydraulique",
                "regulation",
                "electricite et protections",
                "adaptation chaufferie",
                "etude dimensionnement",
                "mise en service",
                "dossier CEE",
            ],
            "assumption",
            "medium",
            "scope generique BAR-TH-179",
        )
    }
