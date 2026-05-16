from __future__ import annotations

from .common import field


def infer_works_scope(project: dict) -> dict:
    return {
        "works_scope": field(
            [
                "mise en place PAC collective air/eau",
                "adaptation hydraulique chaufferie",
                "regulation et raccordements",
                "etudes et mise en service",
            ],
            "assumption",
            "medium",
            "scope generique BAR-TH-179",
        )
    }
