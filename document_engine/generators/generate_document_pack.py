from __future__ import annotations

import json
from pathlib import Path

from . import generate_ah, generate_devis, generate_dpt, generate_facture, generate_note_dimensionnement
from .render_template import field_line, header


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
    write(output_dir / "04_CONTROLE_INTERNE" / "risques_conformite.md", render_risks(project), files, output_dir)
    manifest = {"case_id": project["case_id"], "code": project["code"], "mode": mode, "files": files, "blocking_points": project.get("blocking_points", [])}
    (output_dir / "dossier_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest
