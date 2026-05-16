from __future__ import annotations

from .render_template import field_line, header


def render(project: dict, company: dict, mode: str) -> str:
    lines = [header("Note de dimensionnement - brouillon", project, company)]
    for name, label in [
        ("heated_surface_m2", "Surface chauffee"),
        ("emitter_types", "Emetteurs"),
        ("tbase_c", "Tbase"),
        ("heat_losses_kw", "Deperditions"),
        ("pac_nominal_power_kw", "Puissance PAC proposee"),
        ("chaufferie_useful_power_after_works_kw", "Puissance chaufferie apres travaux"),
    ]:
        lines.append(field_line(project, name, label))
    return "\n".join(lines) + "\n"
