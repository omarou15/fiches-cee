"""Best-effort extraction for Office files without heavyweight dependencies."""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


XML_TEXT_RE = re.compile(r"\s+")


def _xml_text(xml_bytes: bytes) -> str:
    root = ET.fromstring(xml_bytes)
    texts: list[str] = []
    for node in root.iter():
        if node.text and node.tag.endswith("}t"):
            texts.append(node.text)
    return XML_TEXT_RE.sub(" ", " ".join(texts)).strip()


def extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.startswith("word/") and name.endswith(".xml")]
        parts = []
        for name in names:
            try:
                text = _xml_text(archive.read(name))
            except Exception:
                text = ""
            if text:
                parts.append(text)
        return "\n\n".join(parts).strip()


def extract_xlsx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            try:
                shared_text = _xml_text(archive.read("xl/sharedStrings.xml"))
                shared = shared_text.split()
            except Exception:
                shared = []
        sheet_names = [name for name in archive.namelist() if name.startswith("xl/worksheets/") and name.endswith(".xml")]
        parts: list[str] = []
        for name in sheet_names:
            try:
                root = ET.fromstring(archive.read(name))
            except Exception:
                continue
            values: list[str] = []
            for node in root.iter():
                if node.tag.endswith("}v") and node.text:
                    values.append(node.text)
            if values:
                parts.append(f"{name}\n" + " ".join(values))
        if shared:
            parts.insert(0, "sharedStrings\n" + " ".join(shared))
        return "\n\n".join(parts).strip()


def extract_office(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return extract_docx(path)
    if suffix == ".xlsx":
        return extract_xlsx(path)
    return ""


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/extract_office.py <docx|xlsx>", file=sys.stderr)
        return 2
    print(extract_office(Path(argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
