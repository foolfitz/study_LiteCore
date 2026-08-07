#!/usr/bin/env python3
"""Build deterministic canonical-A and content-distinct candidate-B releases for R8-C."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from r8_bundle import CREATED_AT, build_policy_bundle, validate_bundle
from r8_release import load_json, write_json


CANDIDATE_VARIANT = "r8c-candidate-v1"
RETENTION_VARIANT = "r8c-candidate-v2"


def build_release_set(project: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    releases_root = output / "releases"
    old_ids: set[str] = set()
    index_path = output / "release-set.json"
    if index_path.is_file():
        try:
            old_ids = {
                str(item["releaseId"])
                for item in load_json(index_path).get("releases", [])
                if isinstance(item, dict)
            }
        except Exception:
            old_ids = set()

    canonical = build_policy_bundle(project, releases_root, "standard")
    candidate = build_policy_bundle(
        project, releases_root, "standard", variant_marker=CANDIDATE_VARIANT,
    )
    retention = build_policy_bundle(
        project, releases_root, "standard", variant_marker=RETENTION_VARIANT,
    )
    if len({canonical["releaseId"], candidate["releaseId"], retention["releaseId"]}) != 3:
        raise RuntimeError("R8-C release variants did not produce three distinct identities")

    releases = [
        {"slot": "A", "variant": "canonical-r8b-standard", **canonical},
        {"slot": "B", "variant": CANDIDATE_VARIANT, **candidate},
        {"slot": "C", "variant": RETENTION_VARIANT, **retention},
    ]
    for item in releases:
        manifest = load_json(releases_root / item["releaseId"] / "release-manifest.json")
        item["requiredArtifactCount"] = sum(
            artifact.get("required") is True for artifact in manifest["artifacts"]
        )
    validation = []
    for item in releases:
        result = validate_bundle(releases_root / item["releaseId"], "standard")
        validation.append({"slot": item["slot"], **result})
    index = {
        "schemaVersion": 1,
        "release": "R8-C-service-worker",
        "createdAt": CREATED_AT,
        "activeSlot": "A",
        "candidateSlot": "B",
        "releases": releases,
        "validation": validation,
        "pass": all(item["pass"] for item in validation),
    }
    write_json(index_path, index)

    current_ids = {item["releaseId"] for item in releases}
    for release_id in sorted(old_ids - current_ids):
        target = releases_root / release_id
        if (target.parent == releases_root and target.is_dir()
                and release_id.startswith("writer-review-") and len(release_id) == 30):
            shutil.rmtree(target)
    return index


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument("--output", type=Path, default=project / "dist" / "r8c")
    args = parser.parse_args()
    result = build_release_set(args.project.resolve(), args.output.resolve())
    print(json.dumps({
        "output": str(args.output.resolve() / "release-set.json"),
        "releaseIds": {item["slot"]: item["releaseId"] for item in result["releases"]},
        "pass": result["pass"],
    }, ensure_ascii=False, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
