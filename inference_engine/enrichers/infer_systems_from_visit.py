from __future__ import annotations

from .common import field, first_number, normalize


def infer_systems_from_visit(case: dict) -> dict:
    notes = normalize(case.get("visit", {}).get("notes"))
    pac_power = first_number(r"pac[^0-9]{0,20}(\d+(?:[ ,.]\d+)?)\s*kw", notes)
    boiler_power = first_number(r"(?:chaufferie|chaudiere|chaudière)[^0-9]{0,30}(\d+(?:[ ,.]\d+)?)\s*kw", notes)
    etas = first_number(r"etas[^0-9]{0,15}(\d+(?:[ ,.]\d+)?)\s*%?", notes)
    heating_and_dhw = "ecs" in notes or "eau chaude sanitaire" in notes
    heating_only = "chauffage seul" in notes
    usage = "chauffage" if heating_only else "chauffage_et_ecs" if heating_and_dhw else "chauffage_et_ecs"
    return {
        "pac_type": field("air_eau" if ("air/eau" in notes or "air eau" in notes or "pac" in notes) else None, "deduced" if "pac" in notes else "missing", "medium", "notes de visite"),
        "usage": field(usage, "deduced" if heating_and_dhw or heating_only else "assumption", "medium" if heating_and_dhw or heating_only else "low", "notes de visite"),
        "heating_system_collective": field(True if "collectif" in notes or "chaufferie" in notes else None, "deduced" if "collectif" in notes or "chaufferie" in notes else "missing", "medium", "notes de visite"),
        "pac_nominal_power_kw": field(pac_power, "confirmed" if pac_power else "missing", "high" if pac_power else "high", "notes de visite"),
        "chaufferie_useful_power_after_works_kw": field(boiler_power, "confirmed" if boiler_power else "missing", "high" if boiler_power else "high", "notes de visite"),
        "etas_percent": field(etas, "confirmed" if etas else "assumption", "high" if etas else "low", "notes de visite" if etas else "valeur de brouillon a valider"),
        "application_temperature": field("moyenne_haute_temperature", "deduced", "medium", "chauffage collectif avec ECS ou radiateurs"),
        "backup_equipment_excluded": field(True, "assumption", "low", "hypothese de brouillon : a confirmer sur schema chaufferie"),
    }
