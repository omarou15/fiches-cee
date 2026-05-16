from __future__ import annotations

from .render_template import field_line, header


def render(project: dict, company: dict, mode: str) -> str:
    return (
        header("Attestation sur l'honneur - brouillon", project, company)
        + "Ce brouillon ne doit pas etre signe sans verification des champs officiels applicables.\n\n"
        + field_line(project, "usage", "Usage PAC")
        + "\n"
        + field_line(project, "climate_zone", "Zone climatique")
        + "\n"
        + field_line(project, "apartment_count_heated_by_pac", "Nombre d'appartements")
        + "\n"
    )
