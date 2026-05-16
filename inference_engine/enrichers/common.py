from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize(text: str | None) -> str:
    text = text or ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def field(value: Any, status: str, confidence: str, source: str, needs_human_validation: bool | None = None) -> dict:
    if needs_human_validation is None:
        needs_human_validation = status != "confirmed"
    return {
        "value": value,
        "status": status,
        "confidence": confidence,
        "source": source,
        "needs_human_validation": needs_human_validation,
    }


def first_number(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, re.I)
    if not match:
        return None
    raw = match.group(1).replace(",", ".").replace(" ", "")
    try:
        return float(raw)
    except ValueError:
        return None


def int_or_none(value: float | None) -> int | None:
    return int(value) if value is not None else None
