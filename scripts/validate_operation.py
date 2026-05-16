"""Validate inferred CEE project readiness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    project = json.loads(Path(args.input).read_text(encoding="utf-8"))
    blocking = list(project.get("blocking_points") or [])
    if args.strict:
        blocking.extend(
            name
            for name, item in project.get("fields", {}).items()
            if item.get("status") in {"estimated", "assumption", "missing", "blocking"}
        )
    result = {
        "case_id": project.get("case_id"),
        "code": project.get("code"),
        "valid": not blocking,
        "blocking_points": sorted(set(blocking)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
