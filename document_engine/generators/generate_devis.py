from __future__ import annotations

from .render_template import field_line, header


def render(project: dict, company: dict, mode: str) -> str:
    amount = project["fields"].get("estimated_works_cost_eur_ht", {}).get("value")
    return (
        header("Devis brouillon", project, company)
        + "Document de brouillon non contractuel. Toutes les valeurs estimees doivent etre validees.\n\n"
        + field_line(project, "works_scope", "Perimetre travaux")
        + "\n"
        + field_line(project, "pac_nominal_power_kw", "Puissance PAC")
        + "\n"
        + f"- Montant estimatif HT: {amount} EUR\n"
    )
