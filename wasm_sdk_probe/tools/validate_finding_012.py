#!/usr/bin/env python3
"""Select and validate cross-browser finding 012 feature boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from r7_support import load_json, write_json


def one_outcome(summary: dict[str, Any], identifier: str) -> str:
    values = summary.get("outcomes", {}).get(identifier, [])
    return values[0] if len(values) == 1 else "missing"


def select_boundaries(manifest: dict[str, Any], outcomes: dict[str, str]) -> list[dict[str, Any]]:
    variants = {item["id"]: item for item in manifest["variants"]}
    passing = [item for item in manifest["variants"] if outcomes.get(item["id"]) == "close-pass"]
    timing_out = [item for item in manifest["variants"] if outcomes.get(item["id"]) == "timeout"]
    selected: dict[str, dict[str, Any]] = {}
    boundaries = []
    for lower in passing:
        lower_features = set(lower["retainedFeatures"])
        for upper in timing_out:
            upper_features = set(upper["retainedFeatures"])
            if lower_features < upper_features and len(upper_features) == len(lower_features) + 1:
                boundaries.append((lower, upper, sorted(upper_features - lower_features)[0]))
    if boundaries:
        maximum = max(len(lower["retainedFeatures"]) for lower, _, _ in boundaries)
        for lower, upper, feature in boundaries:
            if len(lower["retainedFeatures"]) != maximum:
                continue
            selected[lower["id"]] = {
                "id": lower["id"], "expectedOutcome": "close-pass", "runs": 3,
                "reason": f"maximal passing side of one-feature boundary; adding {feature} timed out",
            }
            selected[upper["id"]] = {
                "id": upper["id"], "expectedOutcome": "timeout", "runs": 1,
                "reason": f"failing side of one-feature boundary; added {feature}",
            }
    elif passing:
        maximum = max(len(item["retainedFeatures"]) for item in passing)
        for item in passing:
            if len(item["retainedFeatures"]) == maximum:
                selected[item["id"]] = {
                    "id": item["id"], "expectedOutcome": "close-pass", "runs": 3,
                    "reason": "maximal passing combination; no immediate failing superset",
                }
        if "t2-original" in variants and outcomes.get("t2-original") == "timeout":
            selected["t2-original"] = {
                "id": "t2-original", "expectedOutcome": "timeout", "runs": 1,
                "reason": "original failing control",
            }
    else:
        identifier = "t2-keep-none"
        selected[identifier] = {
            "id": identifier, "expectedOutcome": outcomes.get(identifier, "timeout"), "runs": 1,
            "reason": "no passing feature combination; confirm the empty retained-feature case",
        }
    return sorted(selected.values(), key=lambda item: item["id"])


def select_image_axis_boundaries(
    manifest: dict[str, Any], outcomes: dict[str, str]
) -> list[dict[str, Any]]:
    if outcomes.get("t2-original") != "timeout":
        return []
    passing = [
        item for item in manifest["variants"]
        if item.get("changedAxes") and outcomes.get(item["id"]) == "close-pass"
    ]
    if not passing:
        return []
    smallest = min(len(item["changedAxes"]) for item in passing)
    selected = []
    for item in sorted(passing, key=lambda value: value["id"]):
        if len(item["changedAxes"]) != smallest:
            continue
        axes = ", ".join(item["changedAxes"])
        reason = (
            f"smallest passing image-object change: {axes}"
            if smallest == 1
            else f"smallest passing image-object interaction ({smallest} axes): {axes}"
        )
        selected.append({
            "id": item["id"],
            "expectedOutcome": "close-pass",
            "runs": 3,
            "reason": reason,
        })
    selected.append({
        "id": "t2-original",
        "expectedOutcome": "timeout",
        "runs": 1,
        "reason": "byte-identical failing control",
    })
    return selected


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--select-boundaries", action="store_true")
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "012" / "r7-minimization",
    )
    args = parser.parse_args()
    manifest = load_json(project / "test-docs" / "r7-finding-012" / "manifest.json")
    release = manifest.get("release", "finding-012-r7-minimization")
    image_axis = release == "finding-012-r7-image-axis"
    phase = "classify" if args.select_boundaries else "confirm"
    summaries = {}
    for browser in ("chrome", "firefox"):
        path = args.evidence_root / phase / browser / "summary.json"
        summaries[browser] = load_json(path) if path.is_file() else {"path": str(path), "pass": False}
    if args.select_boundaries:
        cross = {}
        for item in manifest["variants"]:
            observed = [one_outcome(summaries[browser], item["id"]) for browser in ("chrome", "firefox")]
            cross[item["id"]] = observed[0] if len(set(observed)) == 1 else "divergent"
        selected = (
            select_image_axis_boundaries(manifest, cross)
            if image_axis
            else select_boundaries(manifest, cross)
        )
        result = {
            "schemaVersion": 1,
            "release": release,
            "crossBrowserClassification": cross,
            "selected": selected,
            "pass": all(summary.get("pass") is True for summary in summaries.values())
            and bool(selected) and "divergent" not in cross.values(),
        }
        output = args.evidence_root / "selection.json"
        write_json(output, result)
        print(json.dumps({"output": str(output), "selected": selected, "pass": result["pass"]}, ensure_ascii=False, indent=2))
        if not result["pass"]:
            raise SystemExit(1)
        return

    selection = load_json(args.evidence_root / "selection.json")
    confirmation = []
    for selected in selection["selected"]:
        values = {}
        for browser, summary in summaries.items():
            observed = summary.get("outcomes", {}).get(selected["id"], [])
            values[browser] = {
                "outcomes": observed,
                "expected": selected["expectedOutcome"],
                "pass": len(observed) == selected["runs"]
                and all(value == selected["expectedOutcome"] for value in observed),
            }
        confirmation.append({**selected, "browsers": values, "pass": all(item["pass"] for item in values.values())})
    manifest_by_id = {item["id"]: item for item in manifest["variants"]}
    confirmed_passes = [item for item in confirmation if item["expectedOutcome"] == "close-pass" and item["pass"]]
    confirmed_failures = [item for item in confirmation if item["expectedOutcome"] == "timeout" and item["pass"]]
    candidate_features = set()
    candidate_axes = set()
    if image_axis:
        for item in confirmed_passes:
            candidate_axes.update(manifest_by_id[item["id"]].get("changedAxes", []))
    else:
        for passed_item in confirmed_passes:
            lower = set(manifest_by_id[passed_item["id"]]["retainedFeatures"])
            for failed in confirmed_failures:
                upper = set(manifest_by_id[failed["id"]]["retainedFeatures"])
                if lower < upper and len(upper) == len(lower) + 1:
                    candidate_features.update(upper - lower)
    passed = all(summary.get("pass") is True for summary in summaries.values())
    passed = passed and bool(confirmation) and all(item["pass"] for item in confirmation)
    if image_axis and passed and candidate_axes:
        decision = "MINIMIZED" if all(
            len(manifest_by_id[item["id"]].get("changedAxes", [])) == 1
            for item in confirmed_passes
        ) else "INTERACTION_BOUNDARY"
    else:
        decision = "MINIMIZED" if passed and candidate_features else "INCONCLUSIVE"
    result = {
        "schemaVersion": 1,
        "release": release,
        "decision": decision,
        "confirmation": confirmation,
        "candidateTriggerFeatures": sorted(candidate_features),
        "candidateTriggerAxes": sorted(candidate_axes),
        "observed": "public open-close outcomes only",
        "inference": (
            "removing the confirmed image-object axis or axis interaction changes timeout to close-pass; causality below ODF attributes is not yet proven"
            if image_axis
            else "candidate features are necessary at the confirmed one-feature boundary, not yet proven sufficient"
        ),
        "notValidated": ["LibreOffice core versus SDK Worker root cause", "native LOK reproduction"],
        "pass": passed,
    }
    output = args.evidence_root / "summary.json"
    write_json(output, result)
    print(json.dumps({
        "output": str(output),
        "decision": result["decision"],
        "candidateTriggerFeatures": result["candidateTriggerFeatures"],
        "candidateTriggerAxes": result["candidateTriggerAxes"],
        "pass": passed,
    }, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
