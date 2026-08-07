#!/usr/bin/env python3
"""Capture immutable R8-B bundle/core baselines before and after delivery runs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from r8_bundle import validate_bundle_index
from r8_release import sha256_file, write_json
from validate_r8_preflight import capture


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument("--core", type=Path, default=workspace / "libreoffice-26-8")
    parser.add_argument("--evidence-root", type=Path,
                        default=workspace / "findings" / "evidence" / "sdk-r8" / "delivery")
    args = parser.parse_args()
    project = args.project.resolve()
    report = capture(project, args.core.resolve(), args.phase)
    report["release"] = "R8-B-versioned-artifact-delivery"
    bundle = validate_bundle_index(project / "dist" / "releases")
    tracked = {
        "deliveryContract": project / "r8" / "delivery-contract-v1.json",
        "releaseIndex": project / "dist" / "releases" / "index.json",
        "verifiedLoader": project / "delivery" / "verified-loader.js",
    }
    report["delivery"] = {
        "bundle": bundle,
        "files": {
            name: {"path": str(path), "bytes": path.stat().st_size,
                   "sha256": sha256_file(path)}
            for name, path in tracked.items()
        },
    }
    report["checks"]["bundle"] = bundle["pass"]
    report["pass"] = all(report["checks"].values())
    output = args.evidence_root.resolve() / "baseline" / f"preflight-{args.phase}.json"
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        if existing.get("pass") is not True:
            digest = hashlib.sha256(output.read_bytes()).hexdigest()[:12]
            output.replace(output.with_name(f"preflight-{args.phase}-failed-{digest}.json"))
    write_json(output, report)
    print(json.dumps({"output": str(output), "phase": args.phase,
                      "checks": report["checks"], "pass": report["pass"]},
                     ensure_ascii=False, indent=2))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
