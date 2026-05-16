from __future__ import annotations

import json
from pathlib import Path

from . import generate_ah, generate_devis, generate_dpt, generate_facture, generate_note_dimensionnement
from .render_template import build_context, field_line, header, markdown_list, render_template_file


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_ROOT = REPO_ROOT / "document_engine" / "templates"

OPERATION_TEMPLATE_OUTPUTS = [
    ("controle/controle_eligibilite_bar_th_179.md", "00_SYNTHESE/controle_eligibilite.md"),
    ("devis/devis_pac_collective.md", "01_ADMIN/devis.md"),
    ("facture/facture_pac_collective.md", "01_ADMIN/facture.md"),
    ("emails/mail_pieces_manquantes.md", "01_ADMIN/mail_pieces_manquantes.md"),
    ("ah/ah_bar_th_179.md", "02_CEE/attestation_honneur.md"),
    ("controle/checklist_pieces.md", "02_CEE/checklist_cee.md"),
    ("note_dimensionnement/note_dimensionnement_bar_th_179.md", "03_TECHNIQUE/note_dimensionnement.md"),
    ("dpt/dpt_bar_th_179.md", "03_TECHNIQUE/dpt.md"),
]


def write(path: Path, text: str, files: list[str], root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    files.append(path.relative_to(root).as_posix())


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


def render_operation_summary(operation: dict, company: dict, code: str) -> str:
    ctx = build_context(company, operation, code)
    return (
        "# Synthese dossier CEE\n\n"
        f"- Dossier: {ctx['operation'].get('case_id', 'A COMPLETER')}\n"
        f"- Fiche: {ctx['operation'].get('cee_code', code)}\n"
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


def render_operation_calculation(operation: dict) -> str:
    calculation = operation.get("calculation", {})
    return (
        "# Calcul kWh cumac\n\n"
        f"- Formule: {calculation.get('formula_text', 'A COMPLETER')}\n"
        f"- Montant unitaire: {calculation.get('amount_per_apartment_kwh_cumac', 'A COMPLETER')} kWh cumac/appartement\n"
        f"- Nombre d'appartements: {calculation.get('apartments_count', 'A COMPLETER')}\n"
        f"- Facteur R: {calculation.get('r_factor', 'A COMPLETER')}\n"
        f"- Total: {calculation.get('total_kwh_cumac', 'A COMPLETER')} kWh cumac\n"
        f"- Statut: {calculation.get('status', 'A COMPLETER')}\n"
    )


def render_operation_internal_report(operation: dict, company: dict, code: str) -> str:
    return (
        render_operation_summary(operation, company, code)
        + "\n## Controle interne\n\n"
        "- Verifier la coherence devis/facture/AH.\n"
        "- Verifier les justificatifs techniques et la qualification professionnelle.\n"
        "- Verifier que les documents signes reels remplacent les placeholders.\n"
        "- Verifier la derniere version officielle de la fiche avant depot.\n"
    )


def render_operation_pncee_risks(operation: dict) -> str:
    return "# Risques PNCEE / conformite\n\n" + markdown_list(operation.get("compliance", {}).get("risks")) + "\n"


def generate_pack_from_operation(company: dict, operation: dict, code: str, output_dir: Path, mode: str = "draft") -> dict:
    documents = operation.get("documents", {})
    compliance = operation.get("compliance", {})
    blocking_points = list(compliance.get("blocking_points") or [])
    missing_documents = list(documents.get("missing") or [])
    non_compliant_documents = list(documents.get("non_compliant") or [])
    if mode == "strict" and (blocking_points or missing_documents or non_compliant_documents):
        raise ValueError("Strict mode blocked: operation contains missing, non-compliant or blocking items.")

    files: list[str] = []
    write(output_dir / "00_SYNTHESE" / "synthese_dossier.md", render_operation_summary(operation, company, code), files, output_dir)
    write(output_dir / "00_SYNTHESE" / "pieces_manquantes.md", render_operation_missing(operation), files, output_dir)
    for template_rel, output_rel in OPERATION_TEMPLATE_OUTPUTS:
        destination = output_dir / output_rel
        render_template_file(TEMPLATES_ROOT / template_rel, company, operation, destination, code=code)
        files.append(destination.relative_to(output_dir).as_posix())
    write(output_dir / "02_CEE" / "calcul_kwh_cumac.md", render_operation_calculation(operation), files, output_dir)
    write(output_dir / "04_CONTROLE_INTERNE" / "rapport_controle_interne.md", render_operation_internal_report(operation, company, code), files, output_dir)
    write(output_dir / "04_CONTROLE_INTERNE" / "risques_pncee.md", render_operation_pncee_risks(operation), files, output_dir)

    case_id = operation.get("operation", {}).get("case_id", "A_COMPLETER")
    manifest = {
        "case_id": case_id,
        "code": operation.get("operation", {}).get("cee_code", code),
        "mode": mode,
        "source_type": "operation_input",
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
    files: list[str] = []
    write(output_dir / "00_SYNTHESE" / "synthese_dossier.md", render_summary(project, company), files, output_dir)
    write(output_dir / "00_SYNTHESE" / "pieces_manquantes.md", render_missing(project), files, output_dir)
    write(output_dir / "00_SYNTHESE" / "controle_eligibilite.md", render_summary(project, company), files, output_dir)
    write(output_dir / "01_ADMIN" / "devis.md", generate_devis.render(project, company, mode), files, output_dir)
    write(output_dir / "01_ADMIN" / "facture.md", generate_facture.render(project, company, mode), files, output_dir)
    write(output_dir / "01_ADMIN" / "mail_pieces_manquantes.md", render_missing(project), files, output_dir)
    write(output_dir / "02_CEE" / "attestation_honneur.md", generate_ah.render(project, company, mode), files, output_dir)
    write(output_dir / "02_CEE" / "calcul_kwh_cumac.md", json.dumps(project.get("calculation", {}), ensure_ascii=False, indent=2) + "\n", files, output_dir)
    write(output_dir / "02_CEE" / "checklist_cee.md", render_missing(project), files, output_dir)
    write(output_dir / "03_TECHNIQUE" / "note_dimensionnement.md", generate_note_dimensionnement.render(project, company, mode), files, output_dir)
    write(output_dir / "03_TECHNIQUE" / "dpt.md", generate_dpt.render(project, company, mode), files, output_dir)
    write(output_dir / "04_CONTROLE_INTERNE" / "rapport_controle_interne.md", render_summary(project, company), files, output_dir)
    write(output_dir / "04_CONTROLE_INTERNE" / "risques_pncee.md", render_risks(project), files, output_dir)
    manifest = {"case_id": project["case_id"], "code": project["code"], "mode": mode, "source_type": "inferred_project", "files": files, "blocking_points": project.get("blocking_points", [])}
    (output_dir / "dossier_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest
