"""Validate inferred CEE project readiness."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = REPO_ROOT / "rules"
CURATED_DIR = REPO_ROOT / "data" / "curated"
JSON_DIR = REPO_ROOT / "data" / "json"
CHRONOLOGY_SOURCE = "Annexe 5 arrete 4 septembre 2014"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == "unknown"


def get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def first_present(data: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value = get_path(data, path) if "." in path else data.get(path)
        if not is_missing(value):
            return value
    return None


def parse_date(value: Any) -> datetime | None:
    if is_missing(value):
        return None
    try:
        return datetime.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def beneficiary_allows_rai_grace_period(operation: dict[str, Any]) -> bool:
    value = first_present(operation, "beneficiary_type", "client.type", "beneficiary.type")
    normalized = str(value or "").strip().lower()
    return normalized in {"pp", "personne_physique", "particulier", "copropriete", "copropriété", "syndicat_coproprietaires", "syndicat_de_coproprietaires"}


def chronology_dates(operation: dict[str, Any]) -> dict[str, Any]:
    return {
        "date_cadre_contribution": first_present(operation, "date_cadre_contribution", "contribution.date", "rai.date", "cadre_contribution.date"),
        "date_engagement": first_present(operation, "date_engagement", "operation.engagement_date", "quote.signed_date", "quote.date"),
        "date_debut_travaux": first_present(operation, "date_debut_travaux", "operation.start_date", "works.start_date"),
        "date_facture": first_present(operation, "date_facture", "invoice.date", "operation.completion_date"),
        "date_ah_signee": first_present(operation, "date_ah_signee", "ah.signature_date", "attestation_honor.signature_date"),
        "date_depot_pncee": first_present(operation, "date_depot_pncee", "pncee_submission.date", "emmy.submission_date"),
        "qualification_rge_validite": first_present(operation, "qualification_rge_validite", "technical.rge_valid_until", "professional.rge_valid_until"),
    }


def has_chronology_inputs(operation: dict[str, Any]) -> bool:
    explicit_keys = {
        "date_cadre_contribution",
        "date_engagement",
        "date_debut_travaux",
        "date_facture",
        "date_ah_signee",
        "date_depot_pncee",
        "qualification_rge_validite",
    }
    return (
        any(key in operation for key in explicit_keys)
        or isinstance(operation.get("timeline"), dict)
        or isinstance(operation.get("cadre_contribution"), dict)
        or isinstance(operation.get("rai"), dict)
        or isinstance(operation.get("ah"), dict)
        or isinstance(operation.get("pncee_submission"), dict)
    )


def chronology_block(field: str, text: str) -> dict[str, Any]:
    return {
        "field": field,
        "text": text,
        "severity": "high",
        "rejet": "automatique",
        "source": CHRONOLOGY_SOURCE,
    }


def chronology_warning(field: str, text: str) -> dict[str, Any]:
    return {
        "field": field,
        "text": text,
        "severity": "warning",
        "source": CHRONOLOGY_SOURCE,
    }


def validate_chronology(operation: dict[str, Any]) -> dict[str, Any]:
    dates_raw = chronology_dates(operation)
    dates = {name: parse_date(value) for name, value in dates_raw.items()}
    blocking_points: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for required in ("date_engagement", "date_facture"):
        if dates_raw[required] is None:
            blocking_points.append(
                chronology_block(required, f"{required} est obligatoire pour verifier la chronologie du dossier CEE.")
            )
        elif dates[required] is None:
            blocking_points.append(chronology_block(required, f"{required} n'est pas une date ISO valide."))

    for optional in ("date_cadre_contribution", "date_debut_travaux", "date_ah_signee", "date_depot_pncee", "qualification_rge_validite"):
        if dates_raw[optional] is None:
            warnings.append(chronology_warning(optional, f"{optional} absent : controle chronologique incomplet."))
        elif dates[optional] is None:
            warnings.append(chronology_warning(optional, f"{optional} n'est pas une date ISO valide."))

    contribution = dates["date_cadre_contribution"]
    engagement = dates["date_engagement"]
    start = dates["date_debut_travaux"]
    invoice = dates["date_facture"]
    ah = dates["date_ah_signee"]
    submission = dates["date_depot_pncee"]
    rge_valid_until = dates["qualification_rge_validite"]

    if contribution and engagement:
        latest_contribution = engagement + timedelta(days=14) if beneficiary_allows_rai_grace_period(operation) else engagement
        if contribution > latest_contribution:
            blocking_points.append(
                chronology_block(
                    "date_cadre_contribution,date_engagement",
                    "Le cadre de contribution est posterieur au delai autorise par rapport au devis signe.",
                )
            )
    if contribution and start and contribution >= start:
        blocking_points.append(
            chronology_block(
                "date_cadre_contribution,date_debut_travaux",
                "Le cadre de contribution doit etre etabli avant le debut des travaux.",
            )
        )
    if engagement and start and engagement >= start:
        blocking_points.append(
            chronology_block(
                "date_engagement,date_debut_travaux",
                "Le devis signe et date par le beneficiaire doit etre anterieur au debut des travaux.",
            )
        )
    if start and invoice and start > invoice:
        blocking_points.append(
            chronology_block("date_debut_travaux,date_facture", "La facture ne peut pas etre anterieure au debut des travaux.")
        )
    if invoice and ah and invoice > ah:
        blocking_points.append(
            chronology_block("date_facture,date_ah_signee", "L'attestation sur l'honneur doit etre signee apres les travaux et la facture.")
        )
    if invoice and submission and submission > invoice + timedelta(days=365):
        blocking_points.append(
            chronology_block("date_facture,date_depot_pncee", "Le depot PNCEE doit intervenir dans les 12 mois suivant la facture.")
        )
    if rge_valid_until and engagement and rge_valid_until < engagement:
        blocking_points.append(
            chronology_block("qualification_rge_validite,date_engagement", "La qualification RGE est expiree a la date d'engagement.")
        )

    return {
        "valid": not blocking_points,
        "blocking_points": blocking_points,
        "warnings": warnings,
        "dates": dates_raw,
        "source": CHRONOLOGY_SOURCE,
    }


def reference_paths(code: str) -> dict[str, Path]:
    return {
        "rules": RULES_DIR / f"{code}.rules.json",
        "curated": CURATED_DIR / f"{code}.json",
        "json": JSON_DIR / f"{code}.json",
    }


def load_reference(code: str) -> tuple[dict[str, Any] | None, str, Path | None, list[dict[str, Any]]]:
    paths = reference_paths(code)
    warnings: list[dict[str, Any]] = []
    if paths["rules"].exists():
        return load_json(paths["rules"]), "rules", paths["rules"], warnings
    if paths["curated"].exists():
        warnings.append(
            {
                "id": "rules_not_found",
                "severity": "warning",
                "message": f"No machine-readable rules file found for {code}; validation used curated fiche data only.",
                "path": paths["curated"].relative_to(REPO_ROOT).as_posix(),
            }
        )
        return load_json(paths["curated"]), "curated", paths["curated"], warnings
    if paths["json"].exists():
        warnings.append(
            {
                "id": "rules_not_found",
                "severity": "warning",
                "message": f"No machine-readable rules file found for {code}; validation used extracted fiche data only.",
                "path": paths["json"].relative_to(REPO_ROOT).as_posix(),
            }
        )
        return load_json(paths["json"]), "json", paths["json"], warnings
    warnings.append(
        {
            "id": "reference_not_found",
            "severity": "warning",
            "message": f"No local rules, curated JSON, or extracted JSON reference found for {code}.",
            "path": None,
        }
    )
    return None, "missing", None, warnings


def normalize_blocking_point(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("field_path", "field", "id", "name"):
            if item.get(key):
                return str(item[key])
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def field_item_is_present(item: Any) -> bool:
    if isinstance(item, dict):
        if item.get("status") in {"missing", "blocking"}:
            return False
        if "value" in item:
            return not is_missing(item.get("value"))
        return True
    return not is_missing(item)


def project_has_required_field(project: dict[str, Any], field: str) -> bool:
    fields = project.get("fields", {})
    candidates = [
        field,
        f"operation.{field}",
        f"site.{field}",
        f"technical.{field}",
        f"calculation.{field}",
    ]
    for candidate in candidates:
        if isinstance(fields, dict) and candidate in fields:
            return field_item_is_present(fields[candidate])
        value = get_path(project, candidate)
        if not is_missing(value):
            return True
    return False


def document_is_present(project: dict[str, Any], document_id: str) -> bool:
    documents = project.get("documents")
    if not isinstance(documents, dict):
        return False
    item = documents.get(document_id)
    if isinstance(item, dict):
        return item.get("provided") is True or item.get("status") in {"received", "confirmed"}
    return item is True


def add_rules_blocking_points(project: dict[str, Any], rules: dict[str, Any], blocking: list[str]) -> None:
    for field in rules.get("required_fields", []):
        if not project_has_required_field(project, str(field)):
            blocking.append(str(field))
    for document_id in rules.get("strict_blocking_documents", []):
        if not document_is_present(project, str(document_id)):
            blocking.append(f"documents.{document_id}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--code", help="Optional fiche code used to load rules/{CODE}.rules.json or fiche JSON.")
    args = parser.parse_args()

    project = load_json(Path(args.input))
    code = str(args.code or project.get("code") or project.get("fiche_code") or "").strip().upper() or None
    blocking = [normalize_blocking_point(item) for item in (project.get("blocking_points") or [])]
    warnings: list[dict[str, Any]] = []
    reference_source = None
    reference_path = None
    reference_conditions_count = 0

    if args.strict:
        blocking.extend(
            name
            for name, item in project.get("fields", {}).items()
            if isinstance(item, dict) and item.get("status") in {"estimated", "assumption", "missing", "blocking"}
        )

    if code:
        reference, reference_source, reference_path, reference_warnings = load_reference(code)
        warnings.extend(reference_warnings)
        if reference_source == "rules" and isinstance(reference, dict):
            add_rules_blocking_points(project, reference, blocking)
        elif isinstance(reference, dict):
            conditions = reference.get("eligibility_conditions")
            if isinstance(conditions, list):
                reference_conditions_count = len(conditions)

    chronology = None
    if has_chronology_inputs(project):
        chronology = validate_chronology(project)
        blocking.extend(item["text"] for item in chronology["blocking_points"])
        warnings.extend(chronology["warnings"])

    result = {
        "case_id": project.get("case_id"),
        "code": code or project.get("code"),
        "reference_source": reference_source,
        "reference_path": reference_path.relative_to(REPO_ROOT).as_posix() if reference_path else None,
        "reference_conditions_count": reference_conditions_count,
        "chronology": chronology,
        "valid": not blocking,
        "blocking_points": sorted(set(blocking)),
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
