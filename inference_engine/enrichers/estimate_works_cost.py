from __future__ import annotations

from .common import field


def price_item(pricebook: dict, item_id: str) -> dict:
    return pricebook.get("items", {}).get(item_id, {})


def line_from_item(item: dict, quantity: float) -> dict:
    return {
        "id": item.get("id"),
        "description": item.get("label", item.get("id", "ligne estimative")),
        "quantity": quantity,
        "unit": item.get("unit", "forfait"),
        "unit_price_ht_min": item.get("price_ht_min"),
        "unit_price_ht_typical": item.get("price_ht_typical"),
        "unit_price_ht_max": item.get("price_ht_max"),
        "total_ht_min": round(float(item.get("price_ht_min", 0)) * quantity, 2),
        "total_ht_typical": round(float(item.get("price_ht_typical", 0)) * quantity, 2),
        "total_ht_max": round(float(item.get("price_ht_max", 0)) * quantity, 2),
        "confidence": item.get("confidence", "low"),
        "notes": item.get("notes", ""),
    }


def estimate_works_cost(project: dict, pricebook: dict) -> dict:
    pac_power = (project["fields"].get("pac_nominal_power_kw") or {}).get("value")
    if pac_power is None:
        return {
            "estimated_works_cost_eur_ht": field(None, "missing", "high", "puissance PAC absente"),
            "estimated_works_cost_range_eur_ht": field(None, "missing", "high", "puissance PAC absente"),
            "quote_lines": field([], "missing", "high", "puissance PAC absente"),
        }

    pac_item = price_item(pricebook, "pac_air_water_collective_per_kw")
    hydraulics_item = price_item(pricebook, "boiler_room_hydraulics_flat")
    engineering_item = price_item(pricebook, "engineering_fees_flat")
    lines = [
        line_from_item(pac_item, float(pac_power)),
        line_from_item(hydraulics_item, 1),
        line_from_item(engineering_item, 1),
    ]
    totals = {
        "low": round(sum(line["total_ht_min"] for line in lines), 2),
        "typical": round(sum(line["total_ht_typical"] for line in lines), 2),
        "high": round(sum(line["total_ht_max"] for line in lines), 2),
    }
    return {
        "estimated_works_cost_eur_ht": field(totals["typical"], "estimated", "low", "pricebooks generiques de demonstration"),
        "estimated_works_cost_range_eur_ht": field(totals, "estimated", "low", "pricebooks generiques de demonstration"),
        "quote_lines": field(lines, "estimated", "low", "pricebooks generiques de demonstration"),
    }
