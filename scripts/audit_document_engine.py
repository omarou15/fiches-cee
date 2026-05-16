"""Audit that the document engine can render packs for CEE fiche codes."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from document_engine.generators.generate_document_pack import generate_pack_from_operation  # noqa: E402
from scripts.init_operation_input import build_operation_input  # noqa: E402


EXPECTED_FILES = [
    "00_SYNTHESE/synthese_dossier.md",
    "00_SYNTHESE/pieces_manquantes.md",
    "00_SYNTHESE/controle_eligibilite.md",
    "01_ADMIN/devis.md",
    "01_ADMIN/facture.md",
    "01_ADMIN/mail_pieces_manquantes.md",
    "02_CEE/attestation_honneur.md",
    "02_CEE/calcul_kwh_cumac.md",
    "02_CEE/checklist_cee.md",
    "03_TECHNIQUE/note_dimensionnement.md",
    "03_TECHNIQUE/dpt.md",
    "04_CONTROLE_INTERNE/rapport_controle_interne.md",
    "04_CONTROLE_INTERNE/risques_pncee.md",
    "dossier_manifest.json",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_code(code: str, company: dict, root: Path) -> list[str]:
    errors: list[str] = []
    fiche_path = REPO_ROOT / "data" / "json" / f"{code}.json"
    if not fiche_path.exists():
        return [f"{code}: missing fiche JSON"]
    operation = build_operation_input(load_json(fiche_path))
    output = root / code
    manifest = generate_pack_from_operation(company, operation, code, output, "draft")
    if manifest["code"] != code:
        errors.append(f"{code}: manifest code mismatch")
    for rel_path in EXPECTED_FILES:
        path = output / rel_path
        if not path.exists():
            errors.append(f"{code}: missing {rel_path}")
        elif path.suffix == ".md" and "{{" in path.read_text(encoding="utf-8"):
            errors.append(f"{code}: unresolved placeholder in {rel_path}")
    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", action="append")
    parser.add_argument("--all-codes", action="store_true")
    parser.add_argument("--fail-on-issues", action="store_true")
    args = parser.parse_args()

    if args.all_codes:
        codes = sorted(path.stem for path in (REPO_ROOT / "data" / "json").glob("*.json"))
    else:
        codes = args.code or ["BAR-TH-179"]

    company = load_json(REPO_ROOT / "document_engine" / "examples" / "synthetic_company_profile.json")
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cee-document-engine-") as tmp:
        tmp_root = Path(tmp)
        for code in codes:
            errors.extend(audit_code(code, company, tmp_root))

    print(f"Audited document engine for {len(codes)} fiche codes: {len(codes) - len({e.split(':', 1)[0] for e in errors})} ok, {len(errors)} issues.")
    for error in errors[:50]:
        print(f"- {error}")
    return 1 if errors and args.fail_on_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
