from __future__ import annotations


def field_line(project: dict, name: str, label: str | None = None) -> str:
    item = project.get("fields", {}).get(name, {})
    value = item.get("value")
    status = item.get("status", "missing")
    confidence = item.get("confidence", "low")
    marker = "A VALIDER" if item.get("needs_human_validation") else "CONFIRME"
    return f"- {label or name}: {value} ({status}, {confidence}, {marker})"


def header(title: str, project: dict, company: dict) -> str:
    return f"# {title}\n\n- Dossier: {project['case_id']}\n- Fiche: {project['code']}\n- Entreprise: {company['company_name']}\n\n"
