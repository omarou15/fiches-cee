"""Normalize a CEE fiche record from extracted text and index metadata."""

from __future__ import annotations

import re
import os
import unicodedata
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
    "heating": ["chauffage", "chaudiere", "chaudière", "pompe a chaleur", "pompe à chaleur", r"\bPAC\b"],
    "domestic_hot_water": ["eau chaude sanitaire", "ecs"],
    "heat_pump": ["pompe a chaleur", "pompe à chaleur", r"\bPAC\b"],
    "boiler": ["chaudiere", "chaudière"],
    "hybrid_system": ["hybride"],
    "district_heating": ["reseau de chaleur", "réseau de chaleur", "raccordement"],
    "ventilation": ["ventilation", "vmc"],
    "insulation": ["isolation", "isolant", "calorifugeage"],
    "regulation": ["regulation", "régulation", "programmateur"],
    "gtb": ["gestion technique du batiment", "gestion technique du bâtiment", "gtb"],
}

SECTION_RE = re.compile(r"(?m)^([1-5])(?:\.\s+|\s*-\s*)(.+?)\s*$")
ETAS_RANGE_RE = re.compile(r"(?P<min>\d+)\s*%\s*(?:≤|<=)\s*Etas(?:\s*<\s*(?P<max>\d+)\s*%)?")
DEFAULT_BUILD_TIMESTAMP = "2026-05-15T00:00:00+00:00"
VARIABLE_DEFINITION_RE = re.compile(
    r"(?ims)(?:^|\n)\s*[«\"']?\s*(?P<name>[A-Z][A-Za-z0-9_]{0,5})\s*[»\"']?\s+"
    r"(?P<verb>est|correspond|désigne|designe|représente|represente)\b\s*:?\s*"
    r"(?P<label>.+?)(?=(?:\n\s*[«\"']?\s*[A-Z][A-Za-z0-9_]{0,5}\s*[»\"']?\s+"
    r"(?:est|correspond|désigne|designe|représente|represente)\b)|\Z)"
)
DIRECT_EXPRESSION_RE = re.compile(
    r"(?i)(?:\d+(?:[ ,.]\d+)?|\b[A-Z]\b)\s*(?:x|×|\*)\s*(?:\d+(?:[ ,.]\d+)?|\b[A-Z]\b)"
)
NUMERIC_VALUE_RE = re.compile(r"(?<![A-Za-z])\d+(?:[\s\u00a0\u202f]\d{3})*(?:[,.]\d+)?\s*%?")


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


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def contains_term(blob: str, term: str) -> bool:
    if term.startswith(r"\b"):
        return re.search(term, blob, re.I) is not None
    return strip_accents(term).lower() in strip_accents(blob).lower()


def parse_sections(pages: list[dict]) -> list[dict]:
    """Parse official numbered sections and keep page spans."""
    text_parts: list[str] = []
    offsets: list[tuple[int, int, int]] = []
    cursor = 0
    for page in pages:
        page_text = page.get("text") or ""
        start = cursor
        text_parts.append(page_text)
        cursor += len(page_text)
        offsets.append((start, cursor, int(page.get("page") or 1)))
        text_parts.append("\n\n")
        cursor += 2
    full_text = "".join(text_parts)
    matches = [match for match in SECTION_RE.finditer(full_text) if is_official_section(match.group(1), match.group(2))]
    sections: list[dict] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(full_text)
        section_text = full_text[match.end():end].strip()
        sections.append({
            "number": match.group(1),
            "title": match.group(2).strip(),
            "text": section_text,
            "page_start": page_for_offset(offsets, start),
            "page_end": page_for_offset(offsets, max(start, end - 1)),
        })
    return sections


def is_official_section(number: str, title: str) -> bool:
    normalized = strip_accents(title).lower()
    expected = {
        "1": ["secteur"],
        "2": ["denomination"],
        "3": ["conditions"],
        "4": ["duree", "vie conventionnelle"],
        "5": ["montant", "certificats", "kwh"],
    }
    return any(keyword in normalized for keyword in expected.get(number, []))


def page_for_offset(offsets: list[tuple[int, int, int]], offset: int) -> int | None:
    for start, end, page in offsets:
        if start <= offset <= end:
            return page
    return offsets[-1][2] if offsets else None


def parse_lifetime_years(sections: list[dict]) -> int | None:
    section = next((item for item in sections if item["number"] == "4"), None)
    if not section:
        return None
    match = re.search(r"(\d+)\s+ans", section["text"], re.I)
    return int(match.group(1)) if match else None


def parse_engagement_deadline(text: str) -> str | None:
    match = re.search(r"engagées jusqu’au\s+(\d{1,2})\s+([a-zéû]+)\s+(\d{4})", text, re.I)
    if not match:
        return None
    months = {
        "janvier": "01", "février": "02", "fevrier": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08", "aout": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12", "decembre": "12",
    }
    day, month_name, year = match.groups()
    month = months.get(strip_accents(month_name).lower())
    if not month:
        return None
    return f"{year}-{month}-{int(day):02d}"


def parse_amount_table(text: str) -> list[dict]:
    """Parse the common CEE amount table shape found in BAR-TH-179-like fiches."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    range_indexes = [(index, line, ETAS_RANGE_RE.search(line)) for index, line in enumerate(lines) if ETAS_RANGE_RE.search(line)]
    rows: list[dict] = []
    for pos, (start, label, match) in enumerate(range_indexes):
        if not match:
            continue
        end = range_indexes[pos + 1][0] if pos + 1 < len(range_indexes) else len(lines)
        segment = lines[start + 1:end]
        zone_values: list[tuple[str, int]] = []
        for idx, line in enumerate(segment[:-1]):
            if line in {"H1", "H2", "H3"}:
                value = parse_int(segment[idx + 1])
                if value is not None:
                    zone_values.append((line, value))
        if len(zone_values) < 3:
            continue
        etas_min = int(match.group("min"))
        etas_max = int(match.group("max")) if match.group("max") else None
        for index, (zone, amount) in enumerate(zone_values[:6]):
            rows.append({
                "etas_min": etas_min,
                "etas_max": etas_max,
                "usage": "chauffage" if index < 3 else "chauffage_et_ecs",
                "zone": zone,
                "kwh_cumac_per_apartment": amount,
            })
    return rows


def parse_zone_fixed_amount_table(text: str) -> list[dict]:
    """Parse simple fixed amount tables: H1 amount, H2 amount, H3 amount."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows: list[dict] = []
    for index, line in enumerate(lines[:-1]):
        if line in {"H1", "H2", "H3"}:
            value = parse_int(lines[index + 1])
            if value is not None:
                rows.append({
                    "table_type": "zone_fixed_amount",
                    "zone": line,
                    "kwh_cumac": value,
                })
    zones = [row["zone"] for row in rows]
    if zones == ["H1", "H2", "H3"] and not any(line in {"X", "x", "×"} for line in lines):
        return rows
    return []


def section_by_number(sections: list[dict], number: str) -> dict | None:
    return next((section for section in sections if section.get("number") == number), None)


def compact_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = compact_line(value)
        key = strip_accents(normalized).lower()
        if normalized and key not in seen:
            unique.append(normalized)
            seen.add(key)
    return unique


def extract_unit_from_formula_section(text: str) -> str | None:
    lines = [compact_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    for index, line in enumerate(lines):
        blob = strip_accents(line).lower()
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        next_next = lines[index + 2] if index + 2 < len(lines) else ""
        joined = compact_line(" ".join([line, next_line, next_next]))
        if "montant" in blob and has_kwh_cumac_unit(line) and not blob.endswith("par"):
            return line
        if "montant" in blob and has_kwh_cumac_unit(joined):
            return joined
        if has_kwh_cumac_unit(line):
            return joined
    return None


def has_kwh_cumac_unit(text: str) -> bool:
    normalized = strip_accents(text).lower()
    compact = normalized.replace(" ", "")
    return ("kwh" in normalized and "cumac" in normalized) or "kwhc" in compact


def extract_direct_expressions(text: str) -> list[str]:
    expressions: list[str] = []
    for line in text.splitlines():
        line = compact_line(line)
        if not line:
            continue
        if DIRECT_EXPRESSION_RE.search(line) or looks_like_direct_expression(line):
            expressions.append(line)
    return unique_strings(expressions)


def looks_like_direct_expression(line: str) -> bool:
    if len(line) > 180:
        return False
    return bool(re.search(r"\d", line) and re.search(r"(?:\s|^)(?:x|×|\*)(?:\s|$|\()", line, re.I))


def extract_formula_variables(text: str) -> list[dict]:
    variables: dict[str, dict] = {}
    for match in VARIABLE_DEFINITION_RE.finditer(text):
        name = match.group("name").strip()
        label = compact_line(match.group("label"))
        variables[name] = {
            "name": name,
            "label": label[:500] if label else None,
            "unit": infer_variable_unit(label),
            "value_type": "number",
            "description": label[:500] if label else None,
        }

    lines = [compact_line(line) for line in text.splitlines() if compact_line(line)]
    has_multiplier = any(line in {"X", "x", "×"} for line in lines)
    for index, line in enumerate(lines):
        if line in {"X", "x", "×"} and index + 1 < len(lines):
            candidate = lines[index + 1]
            if candidate not in {"X", "H1", "H2", "H3", "DN", "PAC", "ECS"} and re.fullmatch(r"[A-Z][A-Z0-9_]{0,5}", candidate):
                variables.setdefault(candidate, {
                    "name": candidate,
                    "label": None,
                    "unit": None,
                    "value_type": "unknown",
                    "description": "Variable detectee dans la table de calcul.",
                })
        if line not in {"X", "H1", "H2", "H3", "DN", "PAC", "ECS"} and re.fullmatch(r"[A-Z][A-Z0-9_]{0,5}", line) and index > 0 and lines[index - 1] in {"X", "x", "×"}:
            variables.setdefault(line, {
                "name": line,
                "label": None,
                "unit": None,
                "value_type": "unknown",
                "description": "Variable detectee dans la table de calcul.",
            })
        if has_multiplier and re.fullmatch(r"[A-Z][A-Z0-9_]{0,5}", line) and line not in {"X", "H1", "H2", "H3", "DN", "PAC", "ECS"}:
            variables.setdefault(line, {
                "name": line,
                "label": None,
                "unit": None,
                "value_type": "unknown",
                "description": "Variable detectee dans la section de calcul.",
            })
    return list(variables.values())


def normalize_numeric_token(token: str) -> str:
    token = token.strip()
    is_percent = token.endswith("%")
    token = token.rstrip("%").strip()
    token = token.replace("\u00a0", " ").replace("\u202f", " ")
    token = re.sub(r"\s+", "", token)
    token = token.replace(",", ".")
    return f"{token}%" if is_percent else token


def extract_formula_values(text: str) -> list[dict]:
    values: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    for line_no, line in enumerate(text.splitlines(), start=1):
        compact = compact_line(line)
        if not compact:
            continue
        for match in NUMERIC_VALUE_RE.finditer(line):
            raw = match.group(0).strip()
            normalized = normalize_numeric_token(raw)
            key = ("number", normalized, line_no)
            if key in seen:
                continue
            values.append({
                "type": "number",
                "raw": raw,
                "normalized": normalized,
                "line": line_no,
                "context": compact,
            })
            seen.add(key)
        for zone in re.findall(r"\bH[123]\b", line):
            key = ("zone", zone, line_no)
            if key in seen:
                continue
            values.append({
                "type": "zone",
                "raw": zone,
                "normalized": zone,
                "line": line_no,
                "context": compact,
            })
            seen.add(key)
    return values


def infer_variable_unit(label: str | None) -> str | None:
    if not label:
        return None
    low = strip_accents(label).lower()
    unit_map = [
        ("m2", "m2"),
        ("m²", "m2"),
        ("m3", "m3"),
        ("mètre", "m"),
        ("metre", "m"),
        ("kw", "kW"),
        ("kwh", "kWh"),
        ("vehicule", "vehicule"),
        ("véhicule", "vehicule"),
        ("logement", "logement"),
        ("appartement", "appartement"),
        ("heure", "h"),
        ("tonne", "t"),
    ]
    for needle, unit in unit_map:
        if needle in low:
            return unit
    return None


def infer_calculation_methods(text: str, expressions: list[str], variables: list[dict], amount_table: list[dict]) -> list[str]:
    methods: list[str] = []
    normalized = strip_accents(text).lower()
    if amount_table:
        methods.append("structured_amount_table")
    if any(row.get("table_type") == "zone_fixed_amount" for row in amount_table):
        methods.append("zone_fixed_amount_table")
    if expressions:
        methods.append("direct_expression")
    if "montant" in normalized and has_kwh_cumac_unit(text) and (" x " in f" {normalized} " or "\nx\n" in normalized or variables):
        methods.append("table_amount_times_variables")
    if "coefficient" in normalized:
        methods.append("coefficient_based")
    return unique_strings(methods)


def summarize_formula_text(unit: str | None, expressions: list[str], variables: list[dict], amount_table: list[dict]) -> str | None:
    if expressions:
        return " ; ".join(expressions[:12])
    if amount_table:
        if any(row.get("table_type") == "zone_fixed_amount" for row in amount_table):
            return "Montant CEE = forfait selon zone climatique"
        return "Montant CEE = montant_kWh_cumac_unitaire × variables de la fiche"
    if unit and variables:
        names = " × ".join(variable["name"] for variable in variables)
        return f"{unit} × {names}"
    return unit


def extract_calculation(sections: list[dict], source_file: str | None, amount_table: list[dict]) -> dict:
    section = section_by_number(sections, "5")
    if not section or not (section.get("text") or "").strip():
        return {
            "formula_text": None,
            "variables": [],
            "tables": [],
            "amount_table": amount_table,
            "formula_section_title": None,
            "formula_section_text": None,
            "formula_section_page_start": None,
            "formula_section_page_end": None,
            "unit": None,
            "expressions": [],
            "extracted_values": [],
            "calculation_methods": [],
            "formula_status": "missing_section",
            "source_file": source_file,
            "confidence": "low",
        }

    text = section["text"].strip()
    unit = extract_unit_from_formula_section(text)
    if not unit and has_kwh_cumac_unit(section.get("title") or ""):
        unit = section.get("title")
    expressions = extract_direct_expressions(text)
    variables = extract_formula_variables(text)
    extracted_values = extract_formula_values(text)
    amount_table = amount_table or parse_zone_fixed_amount_table(text)
    methods = infer_calculation_methods(text, expressions, variables, amount_table)
    formula_text = summarize_formula_text(unit, expressions, variables, amount_table)
    return {
        "formula_text": formula_text,
        "variables": variables,
        "tables": [],
        "amount_table": amount_table,
        "formula_section_title": section.get("title"),
        "formula_section_text": text,
        "formula_section_page_start": section.get("page_start"),
        "formula_section_page_end": section.get("page_end"),
        "unit": unit,
        "expressions": expressions,
        "extracted_values": extracted_values,
        "calculation_methods": methods,
        "formula_status": "extracted" if formula_text else "needs_review",
        "source_file": source_file,
        "confidence": "medium" if formula_text else "low",
    }


def formula_items_from_calculation(calculation: dict, source_file: str | None) -> list[dict]:
    section_title = calculation.get("formula_section_title") or "Montant de certificats en kWh cumac"
    page = calculation.get("formula_section_page_start")
    items: list[dict] = []
    for expression in calculation.get("expressions") or []:
        items.append(text_item(expression, source_file, page, section_title, "medium"))
    formula_text = calculation.get("formula_text")
    if formula_text and not items:
        items.append(text_item(formula_text, source_file, page, section_title, calculation.get("confidence") or "medium"))
    unit = calculation.get("unit")
    if unit and unit != formula_text:
        items.append(text_item(unit, source_file, page, section_title, "medium"))
    return items


def parse_int(text: str) -> int | None:
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else None


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
    return {key: any(contains_term(blob, keyword) for keyword in keywords) for key, keywords in SYSTEM_KEYWORDS.items()}


def infer_site_data_requirements(title: str, text: str, source_file: str | None) -> list[dict]:
    blob = f"{title} {text}".lower()
    requirements: list[dict] = []
    if contains_term(blob, "pompe a chaleur") or contains_term(blob, "pompe à chaleur") or contains_term(blob, r"\bPAC\b"):
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
    sections = parse_sections(main_pages)
    amount_table = parse_amount_table(main_text)
    calculation = extract_calculation(sections, main_file, amount_table)
    lifetime_years = parse_lifetime_years(sections)
    engagement_deadline = parse_engagement_deadline(main_text)

    eligibility = [text_item(line, main_file, None, "eligibility", "low") for line in find_lines(main_text, ["condition", "eligible", "éligible", "delivrance", "délivrance"])]
    technical = [text_item(line, main_file, None, "technical_requirements", "low") for line in find_lines(main_text, ["performance", "rendement", "classe", "norme", "cop", "etasp", "efficacite", "efficacité"])]
    required_docs = [text_item(line, main_file, None, "required_documents", "low") for line in find_lines(main_text, ["preuve", "document", "attestation", "facture", "devis", "controle", "contrôle"])]
    control_points = [text_item(line, main_file, None, "control_points", "low") for line in find_lines(main_text, ["controle", "contrôle", "inspection", "verifie", "vérifie"])]
    formulas = formula_items_from_calculation(calculation, main_file)
    zones = [text_item(line, main_file, None, "zones", "low") for line in find_lines(main_text, ["zone", "h1", "h2", "h3"])]

    critical_items = eligibility + technical + required_docs + formulas
    needs_review = (
        not eligibility
        or not technical
        or not required_docs
        or any(item.get("confidence") == "low" for item in critical_items)
    )
    notes = []
    if calculation["formula_status"] == "missing_section":
        needs_review = True
        notes.append("Section 5 de calcul non detectee dans le PDF principal.")
    elif not formulas or calculation["formula_status"] == "needs_review":
        needs_review = True
        notes.append("Formule detectee mais a revoir.")
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
        "sections": sections,
        "applicability": infer_applicability(code, title, main_text),
        "systems": infer_systems(title, main_text),
        "eligibility_conditions": eligibility,
        "technical_requirements": technical,
        "required_documents": required_docs,
        "attestation_fields": [],
        "control_points": control_points,
        "calculation": calculation,
        "formulas": formulas,
        "zones": zones,
        "bonifications": [],
        "site_data_requirements": infer_site_data_requirements(title, main_text, main_file),
        "output_documents": infer_output_documents(main_text),
        "validity": {
            "effective_date": effective_date,
            "engagement_deadline": engagement_deadline,
        },
        "lifetime_years": lifetime_years,
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
            "extracted_at": os.environ.get("CEE_BUILD_TIMESTAMP", DEFAULT_BUILD_TIMESTAMP),
            "needs_human_review": needs_review,
            "notes": " ".join(notes) if notes else None,
        },
    }
