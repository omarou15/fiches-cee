from __future__ import annotations

import os
from pathlib import Path


def find_repo_root() -> Path:
    env_root = os.environ.get("CEE_REPO_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "data" / "indexes" / "fiches_cee_index.json").exists():
            return parent
    return Path(__file__).resolve().parents[2]


REPO_ROOT = find_repo_root()
DATA_DIR = REPO_ROOT / "data"
INDEXES_DIR = DATA_DIR / "indexes"
JSON_DIR = DATA_DIR / "json"
TEXT_DIR = DATA_DIR / "text"
CURATED_DIR = DATA_DIR / "curated"
RULES_DIR = REPO_ROOT / "rules"


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


def relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()

