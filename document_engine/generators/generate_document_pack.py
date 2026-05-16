from __future__ import annotations

import json
from pathlib import Path

from . import generate_ah, generate_devis, generate_dpt, generate_facture, generate_note_dimensionnement
from .render_template import build_context, field_line, header, markdown_list, render_template_file


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_ROOT = REPO_ROOT / "document_engine" / "templates"
FICHE_JSON_ROOT = REPO_ROOT / "data" / "json"

GENERIC_OPERATION_TEMPLATES = {
    "controle": "controle/controle_eligibilite_generic.md",
    "devis": "devis/devis_generic.md",
    "facture": "facture/facture_generic.md",
    "mail": "emails/mail_pieces_manquantes.md",
    "ah": "ah/ah_generic.md",
    "checklist": "controle/checklist_pieces.md",
    "note": "note_dimensionnement/note_dimensionnement_generic.md",
    "dpt": "dpt/dpt_generic.md",
}

SPECIFIC_OPERATION_TEMPLATES = {
    "BAR-TH-179": {
        "controle": "controle/controle_eligibilite_bar_th_179.md",
        "devis": "devis/devis_pac_collective.md",
        "facture": "facture/facture_pac_collective.md",
        "ah": "ah/ah_bar_th_179.md",
        "note": "note_dimensionnement/note_dimensionnement_bar_th_179.md",
        "dpt": "dpt/dpt_bar_th_179.md",
    }
}

OPERATION_OUTPUTS = [
    ("controle", "00_SYNTHESE/controle_eligibilite.md"),
    ("devis", "01_ADMIN/devis.md"),
    ("facture", "01_ADMIN/facture.md"),
    ("mail", "01_ADMIN/mail_pieces_manquantes.md"),
    ("ah", "02_CEE/attestation_honneur.md"),
    ("checklist", "02_CEE/checklist_cee.md"),
    ("note", "03_TECHNIQUE/note_dimensionnement.md"),
    ("dpt", "03_TECHNIQUE/dpt.md"),
]


def write(path: Path, text: str, files: list[str], root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    files.append(path.relative_to(root).as_posix())


def load_fiche(code: str) -> dict:
    path = FICHE_JSON_ROOT / f"{code}.json"
    if not path.exists():
        return {"code": code, "title": "Fiche inconnue", "source_files": []}
    return json.loads(path.read_text(encoding="utf-8"))


def template_for(code: str, key: str) -> tuple[str, bool]:
    specific = SPECIFIC_OPERATION_TEMPLATES.get(code, {}).get(key)
    if specific and (TEMPLATES_ROOT / specific).exists():
        return specific, True
    return GENERIC_OPERATION_TEMPLATES[key], False


def render_summary(project: dict, company: dict) -> str:
    calc = project.get("calculation", {})
    return (
        header("Synthese dossier CEE", project, company)
        + field_line(project, "climate_zone", "Zone climatique")
        + "\n"
        + field_line(project, "usage", "Usage")
        + "\n"
        + f"- Calcul CEE: {calc.get('status')} / {calc.get('kwh_cumac')} kWh cumac\n"
    )


def render_missing(project: dict) -> str:
    lines = ["# Pieces et donnees manquantes", ""]
    for item in project.get("blocking_points") or []:
        lines.append(f"- {item}")
    for name, field in sorted(project.get("fields", {}).items()):
        if field.get("needs_human_validation"):
            lines.append(f"- A valider: {name} = {field.get('value')} ({field.get('status')}, {field.get('confidence')})")
    return "\n".join(lines) + "\n"


def render_risks(project: dict) -> str:
    return "# Risques conformite\n\n- Toute donnee estimee ou en hypothese doit etre confirmee avant signature ou depot.\n- Le depot EMMY/PNCEE n'est pas automatise par ce pack.\n"


def inferred_value(project: dict, name: str, default=None):
    return (project.get("fields", {}).get(name) or {}).get("value", default)


def inferred_needs_validation(project: dict) -> list[str]:
    lines: list[str] = []
    for name, item in sorted(project.get("fields", {}).items()):
        if item.get("needs_human_validation"):
            value = item.get("value")
            if value is None or value == "":
                display = "[A COMPLETER]"
                marker = "[A COMPLETER]"
            elif name == "quote_lines":
                display = f"{len(value)} lignes estimatives"
                marker = "[HYPOTHESE A VALIDER]"
            elif isinstance(value, dict):
                display = json.dumps(value, ensure_ascii=False)
                marker = "[HYPOTHESE A VALIDER]"
            else:
                display = value
                marker = "[HYPOTHESE A VALIDER]" if item.get("status") in {"estimated", "assumption"} else "[A VALIDER]"
            lines.append(f"{marker} {name}: {display} ({item.get('status')}, {item.get('confidence')})")
    return lines


def operation_from_inferred(project: dict) -> dict:
    cost = inferred_value(project, "estimated_works_cost_eur_ht")
    quote_lines = []
    for line in inferred_value(project, "quote_lines", []) or []:
        quote_lines.append(
            {
                "description": line.get("description", "Ligne estimative"),
                "quantity": line.get("quantity", 1),
                "unit": line.get("unit", "forfait"),
                "unit_price_ht": line.get("unit_price_ht_typical"),
                "total_ht": line.get("total_ht_typical"),
            }
        )
    if not quote_lines:
        quote_lines = [
            {
                "description": "[A COMPLETER] Travaux a chiffrer",
                "quantity": 1,
                "unit": "forfait",
                "unit_price_ht": None,
                "total_ht": None,
            }
        ]

    site = project.get("site", {})
    client = project.get("client", {})
    missing = inferred_needs_validation(project)
    missing.extend(project.get("calculation", {}).get("missing_inputs", []) or [])
    blocking_points = list(project.get("blocking_points") or [])
    if project.get("calculation", {}).get("status") != "computed":
        blocking_points.append("Calcul CEE incomplet ou non confirme.")

    return {
        "operation": {
            "case_id": project.get("case_id", "A_COMPLETER"),
            "cee_code": project.get("code", "A_COMPLETER"),
            "description": project.get("visit", {}).get("notes", "Operation inferee depuis visite technique."),
            "engagement_date": "[A COMPLETER]",
            "completion_date": None,
            "status": "draft_from_inference",
        },
        "client": {
            "name": client.get("name", "[A COMPLETER]"),
            "type": client.get("type", "[A COMPLETER]"),
            "contact_name": client.get("contact_name", "[A COMPLETER]"),
            "email": client.get("contact_email") or client.get("email") or "[A COMPLETER]",
            "phone": client.get("phone", "[A COMPLETER]"),
            "address": client.get("address", "[A COMPLETER]"),
        },
        "site": {
            "address": site.get("address", "[A COMPLETER]"),
            "postal_code": site.get("postal_code", "[A COMPLETER]"),
            "city": site.get("city", "[A COMPLETER]"),
            "climate_zone": inferred_value(project, "climate_zone", "[A COMPLETER]"),
            "building_type": inferred_value(project, "building_type", "[A COMPLETER]"),
            "apartments_count": inferred_value(project, "apartment_count_heated_by_pac"),
            "heated_surface_m2": inferred_value(project, "heated_surface_m2"),
            "emitters": inferred_value(project, "emitters", "[A COMPLETER]"),
            "base_temperature_c": inferred_value(project, "tbase_c"),
        },
        "technical": {
            "usage": inferred_value(project, "usage", "[A COMPLETER]"),
            "equipment_description": inferred_value(project, "pac_type", "[A COMPLETER]"),
            "brand": "[A COMPLETER]",
            "reference": "[A COMPLETER]",
            "performance_value": inferred_value(project, "etas_percent", "[A COMPLETER]"),
            "etas_percent": inferred_value(project, "etas_percent"),
            "application_temperature": inferred_value(project, "application_temperature", "[A COMPLETER]"),
            "pac_power_kw_prated_minus_10": inferred_value(project, "pac_nominal_power_kw"),
            "chaufferie_useful_power_after_works_kw": inferred_value(project, "chaufferie_useful_power_after_works_kw"),
            "backup_equipment_excluded": inferred_value(project, "backup_equipment_excluded"),
            "r_factor": inferred_value(project, "r_factor"),
            "annual_heating_coverage_percent": "[A COMPLETER]",
            "heat_losses_kw_at_tbase": inferred_value(project, "heat_losses_kw"),
            "flow_temperature_c": inferred_value(project, "flow_temperature_c"),
            "indoor_setpoint_c": inferred_value(project, "indoor_setpoint_temperature_c"),
            "professional_qualification": "[A COMPLETER]",
            "dimensioning_study_status": "[A COMPLETER]",
            "notes": "Donnees inferees automatiquement, a valider humainement.",
        },
        "calculation": {
            "formula_text": project.get("calculation", {}).get("formula_text"),
            "amount_per_apartment_kwh_cumac": (project.get("calculation", {}).get("details", {}).get("amount_row") or {}).get("kwh_cumac_per_apartment"),
            "apartments_count": inferred_value(project, "apartment_count_heated_by_pac"),
            "r_factor": inferred_value(project, "r_factor"),
            "total_kwh_cumac": project.get("calculation", {}).get("kwh_cumac"),
            "status": project.get("calculation", {}).get("status", "missing_inputs"),
        },
        "quote": {
            "number": f"DRAFT-{project.get('case_id', 'CEE')}",
            "date": "[A COMPLETER]",
            "valid_until": None,
            "status": "document genere automatiquement a valider",
            "total_ht": cost,
            "total_ttc": round(float(cost) * 1.1, 2) if cost is not None else None,
            "lines": quote_lines,
        },
        "invoice": {
            "number": f"DRAFT-FAC-{project.get('case_id', 'CEE')}",
            "date": "[A COMPLETER]",
            "due_date": None,
            "status": "brouillon a remplacer par facture finale",
            "total_ht": cost,
            "total_ttc": round(float(cost) * 1.1, 2) if cost is not None else None,
            "lines": quote_lines,
        },
        "documents": {
            "available": ["donnees minimales et notes de visite fournies"],
            "missing": sorted(set(missing)) or ["verification humaine finale"],
            "non_compliant": [],
        },
        "compliance": {
            "eligibility_status": "draft_to_validate",
            "blocking_points": sorted(set(blocking_points)),
            "risks": [
                "Toute donnee estimee ou en hypothese doit etre validee avant signature.",
                "Verifier les justificatifs reglementaires exacts de la fiche.",
                "Verifier la derniere version officielle avant depot.",
            ],
        },
        "mail": {
            "recipient": client.get("contact_email") or client.get("email") or "[A COMPLETER]",
            "subject": f"Pieces manquantes dossier CEE {project.get('code', '')}",
            "sender_name": "[A COMPLETER]",
        },
    }


def render_operation_summary(operation: dict, company: dict, code: str, fiche: dict | None = None) -> str:
    ctx = build_context(company, operation, code, fiche)
    return (
        "# Synthese dossier CEE\n\n"
        f"- Dossier: {ctx['operation'].get('case_id', 'A COMPLETER')}\n"
        f"- Fiche: {ctx['operation'].get('cee_code', code)}\n"
        f"- Intitule fiche: {ctx['fiche'].get('title', 'A COMPLETER')}\n"
        f"- Gabarit documentaire: {'specifique' if code in SPECIFIC_OPERATION_TEMPLATES else 'generique'}\n"
        f"- Client: {ctx['client'].get('name', 'A COMPLETER')}\n"
        f"- Site: {ctx['site'].get('address', 'A COMPLETER')}, {ctx['site'].get('postal_code', '')} {ctx['site'].get('city', '')}\n"
        f"- Entreprise: {ctx['company'].get('name', 'A COMPLETER')}\n"
        f"- Statut eligibilite: {ctx['compliance'].get('eligibility_status', 'A COMPLETER')}\n"
        f"- Total CEE: {ctx['calculation'].get('total_kwh_cumac', 'A COMPLETER')} kWh cumac\n"
        f"- Devis: {ctx['quote'].get('number', 'A COMPLETER')} / {ctx['quote'].get('total_ht_formatted', 'A COMPLETER')} HT\n"
        f"- Facture: {ctx['invoice'].get('number', 'A COMPLETER')} / {ctx['invoice'].get('status', 'A COMPLETER')}\n"
        "\nCe pack est un brouillon professionnel a valider, completer et signer localement avant tout depot.\n"
    )


def render_operation_missing(operation: dict) -> str:
    docs = operation.get("documents", {})
    compliance = operation.get("compliance", {})
    return (
        "# Pieces manquantes\n\n"
        "## Documents manquants\n\n"
        f"{markdown_list(docs.get('missing'))}\n\n"
        "## Pieces non conformes\n\n"
        f"{markdown_list(docs.get('non_compliant'))}\n\n"
        "## Points bloquants\n\n"
        f"{markdown_list(compliance.get('blocking_points'))}\n"
    )


def render_operation_calculation(operation: dict, fiche: dict | None = None) -> str:
    calculation = operation.get("calculation", {})
    fiche_formula = (fiche or {}).get("calculation", {}).get("formula_text") if isinstance((fiche or {}).get("calculation"), dict) else None
    return (
        "# Calcul kWh cumac\n\n"
        f"- Formule operation: {calculation.get('formula_text', 'A COMPLETER')}\n"
        f"- Formule fiche: {fiche_formula or 'A COMPLETER'}\n"
        f"- Montant unitaire: {calculation.get('amount_per_apartment_kwh_cumac', 'A COMPLETER')} kWh cumac/appartement\n"
        f"- Nombre d'appartements: {calculation.get('apartments_count', 'A COMPLETER')}\n"
        f"- Facteur R: {calculation.get('r_factor', 'A COMPLETER')}\n"
        f"- Total: {calculation.get('total_kwh_cumac', 'A COMPLETER')} kWh cumac\n"
        f"- Statut: {calculation.get('status', 'A COMPLETER')}\n"
    )


def render_operation_internal_report(operation: dict, company: dict, code: str) -> str:
    return (
        render_operation_summary(operation, company, code, load_fiche(code))
        + "\n## Controle interne\n\n"
        "- Verifier la coherence devis/facture/AH.\n"
        "- Verifier les justificatifs techniques et la qualification professionnelle.\n"
        "- Verifier que les documents signes reels remplacent les placeholders.\n"
        "- Verifier la derniere version officielle de la fiche avant depot.\n"
    )


def render_operation_pncee_risks(operation: dict) -> str:
    return "# Risques PNCEE / conformite\n\n" + markdown_list(operation.get("compliance", {}).get("risks")) + "\n"


def generate_pack_from_operation(company: dict, operation: dict, code: str | None, output_dir: Path, mode: str = "draft") -> dict:
    operation_code = operation.get("operation", {}).get("cee_code")
    code = operation_code or code or "UNKNOWN"
    fiche = load_fiche(code)
    documents = operation.get("documents", {})
    compliance = operation.get("compliance", {})
    blocking_points = list(compliance.get("blocking_points") or [])
    missing_documents = list(documents.get("missing") or [])
    non_compliant_documents = list(documents.get("non_compliant") or [])
    if mode == "strict" and (blocking_points or missing_documents or non_compliant_documents):
        raise ValueError("Strict mode blocked: operation contains missing, non-compliant or blocking items.")

    files: list[str] = []
    templates_used: dict[str, str] = {}
    specific_templates_used: list[str] = []
    write(output_dir / "00_SYNTHESE" / "synthese_dossier.md", render_operation_summary(operation, company, code, fiche), files, output_dir)
    write(output_dir / "00_SYNTHESE" / "pieces_manquantes.md", render_operation_missing(operation), files, output_dir)
    for template_key, output_rel in OPERATION_OUTPUTS:
        template_rel, is_specific = template_for(code, template_key)
        templates_used[template_key] = template_rel
        if is_specific:
            specific_templates_used.append(template_key)
        destination = output_dir / output_rel
        render_template_file(TEMPLATES_ROOT / template_rel, company, operation, destination, code=code, fiche=fiche)
        files.append(destination.relative_to(output_dir).as_posix())
    write(output_dir / "02_CEE" / "calcul_kwh_cumac.md", render_operation_calculation(operation, fiche), files, output_dir)
    write(output_dir / "04_CONTROLE_INTERNE" / "rapport_controle_interne.md", render_operation_internal_report(operation, company, code), files, output_dir)
    write(output_dir / "04_CONTROLE_INTERNE" / "risques_pncee.md", render_operation_pncee_risks(operation), files, output_dir)

    case_id = operation.get("operation", {}).get("case_id", "A_COMPLETER")
    manifest = {
        "case_id": case_id,
        "code": operation.get("operation", {}).get("cee_code", code),
        "mode": mode,
        "source_type": "operation_input",
        "template_profile": "specific" if specific_templates_used else "generic",
        "templates_used": templates_used,
        "specific_templates_used": sorted(specific_templates_used),
        "files": sorted(files),
        "blocking_points": blocking_points,
        "missing_documents": missing_documents,
        "non_compliant_documents": non_compliant_documents,
    }
    (output_dir / "dossier_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def generate_pack(project: dict, company: dict, mode: str, output_dir: Path) -> dict:
    if mode == "strict" and project.get("blocking_points"):
        raise ValueError("Strict mode blocked: inferred project contains blocking points.")
    if mode == "strict" and project.get("calculation", {}).get("status") != "computed":
        raise ValueError("Strict mode blocked: inferred project calculation is not complete.")
    manifest = generate_pack_from_operation(company, operation_from_inferred(project), project.get("code"), output_dir, mode)
    manifest["source_type"] = "inferred_project"
    (output_dir / "dossier_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest
