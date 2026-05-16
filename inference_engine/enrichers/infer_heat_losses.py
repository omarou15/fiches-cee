from __future__ import annotations

from .common import field


def infer_heat_losses(project: dict) -> dict:
    surface = (project["fields"].get("heated_surface_m2") or {}).get("value")
    apartments = (project["fields"].get("apartment_count_heated_by_pac") or {}).get("value")
    if surface is None and apartments:
        surface = apartments * 65
        project["fields"]["heated_surface_m2"] = field(surface, "estimated", "low", "65 m2/logement")
    if surface is None:
        return {
            "heat_losses_kw": field(None, "missing", "high", "surface chauffee absente"),
            "tbase_c": field(None, "missing", "medium", "adresse/surface insuffisantes"),
            "indoor_setpoint_temperature_c": field(19, "assumption", "low", "hypothese standard a valider"),
            "flow_temperature_c": field(None, "missing", "medium", "emetteurs ou regime reseau absents"),
        }
    heat_losses = round(float(surface) * 0.055, 1)
    return {
        "heat_losses_kw": field(heat_losses, "estimated", "low", "ratio brouillon 55 W/m2"),
        "tbase_c": field(-10, "estimated", "low", "valeur de brouillon a remplacer par etude thermique"),
        "indoor_setpoint_temperature_c": field(19, "assumption", "low", "hypothese standard"),
        "flow_temperature_c": field(45, "assumption", "low", "hypothese radiateurs basse/moyenne temperature a valider"),
    }
