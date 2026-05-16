"""Create a local operation_input skeleton for any structured CEE fiche."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_text(items: list[Any], limit: int = 8) -> list[str]:
    values: list[str] = []
    for item in items[:limit]:
        if isinstance(item, dict):
            text = item.get("text") or item.get("quote") or item.get("label")
        else:
            text = str(item)
        if text and text not in values:
            values.append(text)
    return values


def build_operation_input(fiche: dict[str, Any]) -> dict[str, Any]:
    code = fiche["code"]
    required_documents = evidence_text(fiche.get("required_documents") or [])
    if not required_documents:
        required_documents = [
            "devis signe",
            "facture finale",
            "attestation sur l'honneur signee",
            "preuve de realisation conforme",
            "documents techniques justificatifs",
        ]
    risks = evidence_text(fiche.get("compliance_risks") or fiche.get("risks") or [])
    if not risks:
        risks = [
            "Verifier les conditions d'eligibilite exactes de la fiche.",
            "Verifier les pieces justificatives avant signature ou depot.",
            "Verifier la formule de calcul et toutes les variables.",
        ]

    return {
        "operation": {
            "case_id": f"DRAFT-{code}",
            "cee_code": code,
            "description": fiche.get("title", code),
            "engagement_date": date.today().isoformat(),
            "completion_date": None,
            "status": "draft_to_complete",
        },
        "client": {
            "name": "A COMPLETER",
            "type": "A COMPLETER",
            "contact_name": "A COMPLETER",
            "email": "A COMPLETER",
            "phone": "A COMPLETER",
            "address": "A COMPLETER",
        },
        "site": {
            "address": "A COMPLETER",
            "postal_code": "A COMPLETER",
            "city": "A COMPLETER",
            "climate_zone": "A COMPLETER",
            "building_type": "A COMPLETER",
            "apartments_count": None,
            "heated_surface_m2": None,
        },
        "technical": {
            "usage": "A COMPLETER",
            "equipment_description": "A COMPLETER",
            "brand": "A COMPLETER",
            "reference": "A COMPLETER",
            "performance_value": "A COMPLETER",
            "notes": "A COMPLETER",
        },
        "calculation": {
            "formula_text": fiche.get("calculation", {}).get("formula_text") if isinstance(fiche.get("calculation"), dict) else None,
            "total_kwh_cumac": None,
            "status": "missing_inputs",
        },
        "quote": {
            "number": "A COMPLETER",
            "date": date.today().isoformat(),
            "valid_until": None,
            "status": "draft_to_complete",
            "total_ht": None,
            "total_ttc": None,
            "lines": [
                {
                    "description": "A COMPLETER",
                    "quantity": 1,
                    "unit": "forfait",
                    "unit_price_ht": None,
                    "total_ht": None,
                }
            ],
        },
        "invoice": {
            "number": "A COMPLETER",
            "date": "A COMPLETER",
            "due_date": None,
            "status": "draft_to_complete",
            "total_ht": None,
            "total_ttc": None,
            "lines": [],
        },
        "documents": {
            "available": [],
            "missing": required_documents,
            "non_compliant": [],
        },
        "compliance": {
            "eligibility_status": "draft_to_validate",
            "blocking_points": [
                "Operation client a completer et valider.",
                "Calcul CEE non confirme.",
            ],
            "risks": risks,
        },
        "mail": {
            "recipient": "A COMPLETER",
            "subject": f"Pieces manquantes dossier CEE {code}",
            "sender_name": "A COMPLETER",
        },
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Create a local operation_input JSON skeleton for any CEE fiche.")
    parser.add_argument("--code", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fiche_path = REPO_ROOT / "data" / "json" / f"{args.code}.json"
    if not fiche_path.exists():
        print(f"Unknown fiche code: {args.code}", file=sys.stderr)
        return 2

    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        print(f"Output already exists: {output_path}. Use --force to overwrite.", file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_operation_input(load_json(fiche_path)), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
