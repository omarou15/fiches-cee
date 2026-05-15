"""Normalize a CEE fiche record from extracted text and index metadata."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


SECTOR_MAP = {
    "Agriculture_AGRI": "agriculture",
    "Residentiel_BAR": "residentiel",
    "Tertiaire_BAT": "tertiaire",
    "Industrie_IND": "industrie",
    "Reseaux_RES": "reseaux",
    "Transport_TRA": "transport",
}

SYSTEM_KEYWORDS = {
    "heating": ["chauffage", "chaudiere", "chaudière", "pompe a chaleur", "pompe à chaleur", "pac"],
    "domestic_hot_water": ["eau chaude sanitaire", "ecs"],
    "heat_pump": ["pompe a chaleur", "pompe à chaleur", "pac"],
    "boiler": ["chaudiere", "chaudière"],
    "hybrid_system": ["hybride"],
    "district_heating": ["reseau de chaleur", "réseau de chaleur", "raccordement"],
    "ventilation": ["ventilation", "vmc"],
    "insulation": ["isolation", "isolant", "calorifugeage"],
    "regulation": ["regulation", "régulation", "programmateur"],
    "gtb": ["gestion technique du batiment", "gestion technique du bâtiment", "gtb"],
}


def fiche_family(code: str) -> str:
    parts = code.split("-")
    return parts[1] if len(parts) > 1 else "unknown"


def extract_version(text: str) -> str | None:
    match = re.search(r"\bvA\d+(?:[-.]\d+)?\b", text)
    return match.group(0) if match else None


def extract_effective_date(text: str) -> str | None:
    match = re.search(r"(?:a compter du|à compter du)\s+(\d{2})-(\d{2})-(\d{4})", text, re.I)
    if not match:
        return None
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def text_item(text: str, source_file: str | None = None, page: int | None = None, section_title: str | None = None, confidence: str = "medium") -> dict:
    return {
        "text": text.strip(),
        "source_file": source_file,
        "page": page,
        "section_title": section_title,
        "quote": text.strip()[:500] if text else None,
        "confidence": confidence,
    }


def find_lines(text: str, patterns: list[str], limit: int = 12) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    found: list[str] = []
    for line in lines:
        low = line.lower()
        if any(pattern in low for pattern in patterns):
            found.append(line)
        if len(found) >= limit:
            break
    return found


def infer_applicability(code: str, title: str, text: str) -> dict:
    blob = f"{code} {title} {text}".lower()
    return {
        "residential": code.startswith("BAR-") or "residentiel" in blob or "résidentiel" in blob,
        "tertiary": code.startswith("BAT-") or "tertiaire" in blob,
        "collective": "collectif" in blob or "collective" in blob,
        "individual": "individuel" in blob or "maison" in blob or "appartement" in blob,
        "new_building": True if "batiment neuf" in blob or "bâtiment neuf" in blob else None,
        "existing_building": True if "existant" in blob else None,
        "metropolitan_france": True if "france metropolitaine" in blob or "france métropolitaine" in blob else None,
        "overseas": True if "outre-mer" in blob else None,
    }


def infer_systems(title: str, text: str) -> dict:
    blob = f"{title} {text}".lower()
    return {key: any(keyword in blob for keyword in keywords) for key, keywords in SYSTEM_KEYWORDS.items()}


def infer_site_data_requirements(title: str, text: str, source_file: str | None) -> list[dict]:
    blob = f"{title} {text}".lower()
    requirements: list[dict] = []
    if "pompe a chaleur" in blob or "pompe à chaleur" in blob or "pac" in blob:
        requirements.extend([
            {"field": "puissance_pac", "unit": "kW", "required": True, "reason": "dimensionnement et controle de coherence", "source_file": source_file},
            {"field": "cop_etou_etasp", "unit": None, "required": True, "reason": "performance technique de la pompe a chaleur", "source_file": source_file},
            {"field": "surface_ou_nombre_logements", "unit": None, "required": True, "reason": "perimetre de l'operation et calcul", "source_file": source_file},
        ])
    if "calorifugeage" in blob:
        requirements.extend([
            {"field": "longueur_reseau_isole", "unit": "m", "required": True, "reason": "calcul du volume CEE", "source_file": source_file},
            {"field": "diametre_reseau", "unit": "mm", "required": True, "reason": "classement technique et calcul", "source_file": source_file},
        ])
    if "gtb" in blob or "gestion technique du batiment" in blob or "gestion technique du bâtiment" in blob:
        requirements.append({"field": "classe_gtb", "unit": None, "required": True, "reason": "eligibilite et niveau de performance", "source_file": source_file})
    return requirements


def infer_output_documents(text: str) -> dict:
    blob = text.lower()
    return {
        "note_dimensionnement_required": "dimensionnement" in blob,
        "dpt_required": None,
        "attestation_required": "attestation sur l'honneur" in blob or "attestation" in blob,
        "photos_required": "photo" in blob,
        "manufacturer_datasheet_required": "fiche technique" in blob or "document fabricant" in blob,
    }


def normalize_fiche(unique_row: dict, document_rows: list[dict], main_text: str, main_pages: list[dict]) -> dict:
    code = unique_row["Code"]
    title = unique_row.get("LibellePrincipal") or unique_row.get("Libelle") or code
    sector = SECTOR_MAP.get(unique_row.get("Secteur", ""), unique_row.get("Secteur", "unknown"))
    source_files = [row["CheminDepot"] for row in document_rows if row.get("CheminDepot")]
    main_file = unique_row.get("CheminDepot") or (source_files[0] if source_files else None)
    version = extract_version(title) or extract_version(main_text)
    effective_date = extract_effective_date(title) or extract_effective_date(main_text)

    eligibility = [text_item(line, main_file, None, "eligibility", "low") for line in find_lines(main_text, ["condition", "eligible", "éligible", "delivrance", "délivrance"])]
    technical = [text_item(line, main_file, None, "technical_requirements", "low") for line in find_lines(main_text, ["performance", "rendement", "classe", "norme", "cop", "etasp", "efficacite", "efficacité"])]
    required_docs = [text_item(line, main_file, None, "required_documents", "low") for line in find_lines(main_text, ["preuve", "document", "attestation", "facture", "devis", "controle", "contrôle"])]
    control_points = [text_item(line, main_file, None, "control_points", "low") for line in find_lines(main_text, ["controle", "contrôle", "inspection", "verifie", "vérifie"])]
    formulas = [text_item(line, main_file, None, "formula", "low") for line in find_lines(main_text, ["cumac", "kwh", "coefficient", "montant", "forfait"])]
    zones = [text_item(line, main_file, None, "zones", "low") for line in find_lines(main_text, ["zone", "h1", "h2", "h3"])]

    needs_review = not formulas or not eligibility
    notes = []
    if not formulas:
        notes.append("Formule non detectee automatiquement.")
    if not eligibility:
        notes.append("Conditions d'eligibilite non detectees automatiquement.")

    return {
        "code": code,
        "sector": sector,
        "family": fiche_family(code),
        "title": title,
        "version": version,
        "document_version": version,
        "effective_date": effective_date,
        "dates": {
            "arrete_date": None,
            "effective_date": effective_date,
            "partie_a_effective_date": None,
            "end_date": None,
            "date_source": "filename" if effective_date else "unknown",
        },
        "scope": {
            "building_types": [],
            "operation_types": [],
            "energy_systems": [],
        },
        "applicability": infer_applicability(code, title, main_text),
        "systems": infer_systems(title, main_text),
        "eligibility_conditions": eligibility,
        "technical_requirements": technical,
        "required_documents": required_docs,
        "attestation_fields": [],
        "control_points": control_points,
        "calculation": {
            "formula_text": formulas[0]["text"] if formulas else None,
            "variables": [],
            "tables": [],
        },
        "formulas": formulas,
        "zones": zones,
        "bonifications": [],
        "site_data_requirements": infer_site_data_requirements(title, main_text, main_file),
        "output_documents": infer_output_documents(main_text),
        "risks": [
            {
                "risk": "Extraction automatique heuristique : verifier les champs metier avant usage operationnel.",
                "severity": "medium" if needs_review else "low",
                "source_file": main_file,
            }
        ],
        "related_documents": [
            {
                "document_id": Path(row["CheminDepot"]).stem,
                "code": code,
                "document_type": row.get("DocumentType", "other"),
                "title": row.get("Libelle"),
                "path": row["CheminDepot"],
                "source_url": row.get("Url"),
                "format": Path(row["CheminDepot"]).suffix.lower().lstrip(".") or None,
                "effective_date": extract_effective_date(row.get("Libelle", "")),
                "metadata": {},
            }
            for row in document_rows
            if row.get("CheminDepot")
        ],
        "source_files": source_files,
        "extraction": {
            "status": "needs_review" if needs_review else "extracted",
            "tool": "scripts/build_indexes.py",
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "needs_human_review": needs_review,
            "notes": " ".join(notes) if notes else None,
        },
    }
