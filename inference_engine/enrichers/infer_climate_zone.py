from __future__ import annotations

import re

from .common import field


H1_PREFIXES = {
    "01", "02", "03", "05", "08", "10", "14", "15", "19", "21", "23", "25", "27", "28",
    "38", "39", "42", "43", "45", "51", "52", "54", "55", "57", "58", "59", "60", "61",
    "62", "63", "67", "68", "69", "70", "71", "73", "74", "75", "76", "77", "78", "80",
    "88", "89", "90", "91", "92", "93", "94", "95",
}
H2_PREFIXES = {
    "04", "07", "09", "12", "16", "17", "18", "22", "24", "26", "29", "31", "32", "33",
    "35", "36", "37", "40", "41", "44", "46", "47", "48", "49", "50", "53", "56", "64",
    "65", "72", "79", "81", "82", "84", "85", "86", "87",
}
H3_PREFIXES = {"06", "11", "13", "20", "30", "34", "66", "83"}


def infer_climate_zone(case: dict) -> dict:
    address = case.get("site", {}).get("address") or case.get("client", {}).get("address") or ""
    postal = case.get("site", {}).get("postal_code")
    if not postal:
        match = re.search(r"\b(\d{5})\b", address)
        postal = match.group(1) if match else None
    if not postal:
        return field(None, "blocking", "high", "adresse/postal_code absent")
    prefix = str(postal)[:2]
    if prefix in H1_PREFIXES:
        zone = "H1"
    elif prefix in H2_PREFIXES:
        zone = "H2"
    elif prefix in H3_PREFIXES:
        zone = "H3"
    else:
        return field(None, "blocking", "medium", f"departement {prefix} non mappe")
    return field(zone, "deduced", "medium", f"code postal {postal}")
