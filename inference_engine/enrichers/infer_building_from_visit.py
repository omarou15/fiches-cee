from __future__ import annotations

from .common import field, first_number, int_or_none, normalize


def infer_building_from_visit(case: dict) -> dict:
    notes = normalize(case.get("visit", {}).get("notes"))
    apartments = first_number(r"(\d+)\s*(?:logements|appartements|lots)", notes)
    surface = first_number(r"(\d+(?:[ ,.]\d+)?)\s*m(?:2|²)", notes)
    collective = any(term in notes for term in ["copro", "collectif", "immeuble", "logements", "appartements"])
    existing = not any(term in notes for term in ["neuf", "construction neuve"])
    return {
        "building_type": field("residentiel_collectif" if collective else None, "deduced" if collective else "missing", "medium", "notes de visite"),
        "residential_collective": field(collective if collective else None, "deduced" if collective else "missing", "medium", "notes de visite"),
        "existing_building": field(existing, "deduced", "low", "absence d'indice batiment neuf dans les notes"),
        "apartment_count_heated_by_pac": field(int_or_none(apartments), "deduced" if apartments else "missing", "medium" if apartments else "high", "notes de visite"),
        "heated_surface_m2": field(surface, "deduced" if surface else "missing", "medium" if surface else "high", "notes de visite" if surface else "surface absente des notes"),
    }
