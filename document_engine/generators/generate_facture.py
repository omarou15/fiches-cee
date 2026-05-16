from __future__ import annotations

from .render_template import header


def render(project: dict, company: dict, mode: str) -> str:
    amount = project["fields"].get("estimated_works_cost_eur_ht", {}).get("value")
    return (
        header("Facture brouillon", project, company)
        + "Facture de brouillon a remplacer par la facture reelle signee.\n\n"
        + f"- Montant estimatif HT: {amount} EUR\n"
        + "- Statut: a valider avant tout usage reglementaire.\n"
    )
