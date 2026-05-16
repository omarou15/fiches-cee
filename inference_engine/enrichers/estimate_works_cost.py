from __future__ import annotations

from .common import field


def estimate_works_cost(project: dict, pricebook: dict) -> dict:
    pac_power = (project["fields"].get("pac_nominal_power_kw") or {}).get("value")
    if pac_power is None:
        return {"estimated_works_cost_eur_ht": field(None, "blocking", "high", "puissance PAC absente")}
    unit_price = pricebook.get("items", {}).get("pac_air_water_collective_per_kw", {}).get("unit_price_eur_ht", 1250)
    hydraulics = pricebook.get("items", {}).get("boiler_room_hydraulics_flat", {}).get("unit_price_eur_ht", 18000)
    engineering = pricebook.get("items", {}).get("engineering_fees_flat", {}).get("unit_price_eur_ht", 6500)
    cost = round(float(pac_power) * float(unit_price) + float(hydraulics) + float(engineering), 2)
    return {"estimated_works_cost_eur_ht": field(cost, "estimated", "low", "pricebook generique de demonstration")}
