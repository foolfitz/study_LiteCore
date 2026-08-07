#!/usr/bin/env python3
"""Build the deterministic R8-A writer-review release manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from r8_release import build_release_manifest, validate_release_manifest, write_json


DEFAULT_CREATED_AT = "2026-08-04T00:00:00+08:00"


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument("--created-at", default=DEFAULT_CREATED_AT)
    parser.add_argument(
        "--output",
        type=Path,
        default=project / "dist" / "r8" / "release-manifest.json",
    )
    parser.add_argument("--validation-output", type=Path)
    args = parser.parse_args()

    resolved_project = args.project.resolve()
    manifest = build_release_manifest(resolved_project, args.created_at)
    report = validate_release_manifest(manifest, resolved_project / "dist")
    if not report["pass"]:
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))
    write_json(args.output.resolve(), manifest)
    if args.validation_output:
        write_json(args.validation_output.resolve(), report)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "releaseId": manifest["releaseId"],
        "manifestSha256": report["manifestSha256"],
        "artifacts": len(manifest["artifacts"]),
        "requiredArtifacts": sum(item["required"] for item in manifest["artifacts"]),
        "rawBytes": sum(item["rawBytes"] for item in manifest["artifacts"]),
        "pass": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
