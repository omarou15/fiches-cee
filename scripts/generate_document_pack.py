"""Generate a generic local CEE document pack from an inferred project."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from document_engine.generators.generate_document_pack import generate_pack  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    parser.add_argument("--inferred", required=True)
    parser.add_argument("--mode", choices=["draft", "strict"], default="draft")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        manifest = generate_pack(load_json(Path(args.inferred)), load_json(Path(args.company)), args.mode, Path(args.output))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
