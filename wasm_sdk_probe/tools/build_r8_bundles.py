#!/usr/bin/env python3
"""Build R8-B standard and full-fidelity release bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from r8_bundle import build_bundles, validate_bundle_index


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument("--output", type=Path, default=project / "dist" / "releases")
    args = parser.parse_args()
    index = build_bundles(args.project.resolve(), args.output.resolve())
    validation = validate_bundle_index(args.output.resolve())
    result = {"output": str(args.output.resolve()), "index": index, "validation": validation,
              "pass": index["pass"] and validation["pass"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
