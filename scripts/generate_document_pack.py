"""Generate a generic local CEE document pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from document_engine.generators.generate_document_pack import generate_pack, generate_pack_from_operation  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--code")
    parser.add_argument("--company", required=True)
    parser.add_argument("--operation")
    parser.add_argument("--inferred")
    parser.add_argument("--mode", choices=["draft", "strict"], default="draft")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not args.operation and not args.inferred:
        parser.error("Provide --operation for the document engine flow, or --inferred for the inference flow.")
    if args.operation and args.inferred:
        parser.error("Use either --operation or --inferred, not both.")
    try:
        company = load_json(Path(args.company))
        if args.operation:
            operation = load_json(Path(args.operation))
            code = args.code or operation.get("operation", {}).get("cee_code")
            if not code:
                parser.error("Provide --code or operation.operation.cee_code.")
            manifest = generate_pack_from_operation(company, operation, code, Path(args.output), args.mode)
        else:
            manifest = generate_pack(load_json(Path(args.inferred)), company, args.mode, Path(args.output))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
