from __future__ import annotations

from .common import field


def infer_pac_sizing(project: dict) -> dict:
    fields = project["fields"]
    heat_losses = (fields.get("heat_losses_kw") or {}).get("value")
    pac_power = (fields.get("pac_nominal_power_kw") or {}).get("value")
    chaufferie_power = (fields.get("chaufferie_useful_power_after_works_kw") or {}).get("value")
    updates = {}
    if pac_power is None and heat_losses is not None:
        pac_power = round(float(heat_losses) * 0.65, 1)
        updates["pac_nominal_power_kw"] = field(pac_power, "estimated", "low", "65% des deperditions estimees")
    if chaufferie_power is None and pac_power is not None:
        chaufferie_power = round(float(pac_power) / 0.45, 1)
        updates["chaufferie_useful_power_after_works_kw"] = field(chaufferie_power, "estimated", "low", "hypothese ratio PAC/chaufferie 45%")
    if pac_power is not None and chaufferie_power:
        ratio = float(pac_power) / float(chaufferie_power)
        r_value = ratio if ratio < 0.4 else 1
        updates["r_factor"] = field(round(r_value, 6), "deduced" if ratio >= 0.4 else "estimated", "medium", "regle BAR-TH-179 facteur R")
    return updates
