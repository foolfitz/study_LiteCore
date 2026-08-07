#!/usr/bin/env python3
"""Capture immutable core, R5, R8-B, and R8-C release-set baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from r8_bundle import validate_bundle
from r8_release import load_json, sha256_file, write_json
from validate_r8_preflight import capture


def validate_release_set(project: Path) -> dict[str, object]:
    root = project / "dist" / "r8c"
    index = load_json(root / "release-set.json")
    releases = index.get("releases", [])
    errors: list[str] = []
    if [item.get("slot") for item in releases] != ["A", "B", "C"]:
        errors.append("release slots differ from A/B/C")
    ids = [item.get("releaseId") for item in releases]
    if len(set(ids)) != 3:
        errors.append("release IDs are not distinct")
    r8b = load_json(project / "dist" / "releases" / "index.json")
    standard = next(item for item in r8b["releases"] if item["policy"] == "standard")
    if not releases or releases[0].get("releaseId") != standard["releaseId"]:
        errors.append("slot A differs from the canonical R8-B standard release")
    validations = []
    for item in releases:
        validation = validate_bundle(root / "releases" / str(item.get("releaseId")), "standard")
        validations.append({"slot": item.get("slot"), **validation})
        if not validation["pass"]:
            errors.extend(f"{item.get('slot')}: {error}" for error in validation["errors"])
        manifest_path = root / "releases" / str(item.get("releaseId")) / "release-manifest.json"
        if manifest_path.is_file() and item.get("manifestSha256") != sha256_file(manifest_path):
            errors.append(f"{item.get('slot')}: manifest hash differs")
        if item.get("requiredArtifactCount") != 15:
            errors.append(f"{item.get('slot')}: required artifact count differs from 15")
    return {
        "schemaVersion": 1,
        "index": index,
        "validations": validations,
        "errors": errors,
        "pass": index.get("pass") is True and not errors,
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument("--core", type=Path, default=workspace / "libreoffice-26-8")
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r8" / "service-worker",
    )
    args = parser.parse_args()
    project = args.project.resolve()
    report = capture(project, args.core.resolve(), args.phase)
    report["release"] = "R8-C-service-worker"
    release_set = validate_release_set(project)
    tracked = {
        "serviceWorkerContract": project / "r8" / "service-worker-contract-v1.json",
        "releaseSet": project / "dist" / "r8c" / "release-set.json",
        "releaseState": project / "delivery" / "release-state.js",
        "verifiedLoader": project / "delivery" / "verified-loader.js",
        "serviceWorker": project / "web" / "r8-service-worker.js",
        "updateApp": project / "web" / "r8-update-app.js",
    }
    report["serviceWorker"] = {
        "releaseSet": release_set,
        "files": {
            name: {
                "path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path),
            }
            for name, path in tracked.items()
        },
    }
    report["checks"]["releaseSet"] = release_set["pass"]
    report["pass"] = all(report["checks"].values())
    output = args.evidence_root.resolve() / "baseline" / f"preflight-{args.phase}.json"
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        if existing.get("pass") is not True:
            digest = hashlib.sha256(output.read_bytes()).hexdigest()[:12]
            output.replace(output.with_name(f"preflight-{args.phase}-failed-{digest}.json"))
    write_json(output, report)
    print(json.dumps({
        "output": str(output), "phase": args.phase,
        "checks": report["checks"], "pass": report["pass"],
    }, ensure_ascii=False, indent=2))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
