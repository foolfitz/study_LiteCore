#!/usr/bin/env python3
"""SPEC E2-B 7.2: derive the decision from the evidence.

Nothing here decides anything new.  The thresholds are 7.1's, written before
any of this ran; this reads what was saved and reports whether they were met.
Separating the two is the whole point -- a decision written by hand in prose is
a decision that can drift from its evidence without anyone noticing, which is
the failure finding 044 records.

Every input is re-derived rather than trusted:

  * the artifact hashes are recomputed from the files on disk and compared with
    what each evidence file recorded (finding 027: a result that names an
    artifact it did not run on is not evidence of anything);
  * the per-arm verdicts are recomputed by the analyzers, not read from their
    summaries;
  * the four-way action inventory and the E1-C bundle are re-checked, because a
    freeze that silently unbound a shipped verdict would still look green here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
EVIDENCE = PROJECT.parent / "findings" / "evidence" / "sdk-e2" / "discovery"
BROWSERS = ("chrome", "firefox")


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_tool(*argv: str) -> tuple[int, dict | None]:
    result = subprocess.run([sys.executable, *argv], cwd=PROJECT,
                            capture_output=True, text=True)
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.returncode, None


def check_matrix(root: Path, wasm: str) -> dict:
    out = {"browsers": {}, "problems": []}
    for browser in BROWSERS:
        directory = root / browser
        if not (directory / "result.json").is_file():
            out["problems"].append(f"matrix: no {browser} result")
            continue
        code, summary = run_tool("tools/analyze_e2b_matrix.py", str(directory))
        if summary is None:
            out["problems"].append(f"matrix: {browser} analyzer produced no summary")
            continue
        recorded = (summary.get("artifact") or {}).get("wasmSha256")
        if recorded != wasm:
            out["problems"].append(
                f"matrix {browser}: evidence records {str(recorded)[:16]}, "
                f"the profile on disk is {wasm[:16]}")
        self_red = set(summary.get("selfRedArms") or [])
        ordinary = {k: v for k, v in summary["byArm"].items() if k not in self_red}
        bad = [k for k, v in ordinary.items()
               if v["failed"] or v["void"] or v["rounds"] < 3]
        if bad:
            out["problems"].append(f"matrix {browser}: arms not passing 3/3: {bad}")
        if summary.get("selfRedBehavedAsRequired") is not True:
            out["problems"].append(
                f"matrix {browser}: the self-red arm did not fail as required")
        out["browsers"][browser] = {
            "arms": len(summary["byArm"]),
            "selfRedArms": sorted(self_red),
            "selfRedBehavedAsRequired": summary.get("selfRedBehavedAsRequired"),
        }
    return out


def check_negative(root: Path, wasm: str) -> dict:
    out = {"browsers": {}, "problems": []}
    for browser in BROWSERS:
        directory = root / browser
        if not (directory / "result.json").is_file():
            out["problems"].append(f"negative: no {browser} result")
            continue
        code, summary = run_tool("tools/analyze_e2b_negative.py", str(directory))
        if summary is None:
            out["problems"].append(f"negative: {browser} analyzer produced no summary")
            continue
        recorded = (summary.get("artifact") or {}).get("wasmSha256")
        if recorded != wasm:
            out["problems"].append(
                f"negative {browser}: evidence records {str(recorded)[:16]}")
        if (summary.get("attribution") or {}).get("consistent") is not True:
            out["problems"].append(f"negative {browser}: attribution inconsistent")
        bad = [k for k, v in summary["byRow"].items()
               if v["failed"] or v["void"] or v["rounds"] < 1]
        if bad:
            out["problems"].append(f"negative {browser}: rows not passing: {bad}")
        out["browsers"][browser] = {"rows": len(summary["byRow"])}
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path,
                        default=PROJECT / "dist" / "profiles" / "e2-editor-v2")
    parser.add_argument("--output", type=Path,
                        default=EVIDENCE.parent / "e2-b-summary.json")
    args = parser.parse_args()

    wasm = sha256(args.profile / "probe.wasm")
    loader = sha256(args.profile / "probe.js")
    worker = sha256(args.profile / "sdk-worker.js")
    manifest = json.loads((args.profile / "sdk-manifest.json").read_text(encoding="utf-8"))
    contract = manifest.get("editorContract", {})

    problems: list[str] = []

    # The manifest must describe the artifact it sits beside.
    for label, actual, recorded in (("wasm", wasm, contract.get("wasmSha256")),
                                    ("loader", loader, contract.get("loaderSha256")),
                                    ("worker", worker, contract.get("workerSha256"))):
        if actual != recorded:
            problems.append(f"{label}: on disk {str(actual)[:16]}, "
                            f"manifest says {str(recorded)[:16]}")

    matrix = check_matrix(EVIDENCE / "e2b-matrix" / f"e2-editor-v2-{wasm[:8]}", wasm)
    negative = check_negative(EVIDENCE / "e2b-negative" / f"e2-editor-v2-{wasm[:8]}", wasm)
    problems += matrix["problems"] + negative["problems"]

    inventory_code, inventory = run_tool("tools/check_e2_b_inventory.py",
                                         "--profile", str(args.profile))
    if inventory_code != 0:
        problems.append(f"action inventory disagrees: "
                        f"{(inventory or {}).get('problems')}")

    bundle_code, bundle = run_tool("tools/check_e1_c_bundle_intact.py")
    if bundle_code != 0:
        problems.append(f"E1-C shell bundle no longer intact: "
                        f"{(bundle or {}).get('problems')}")

    self_test_code, _ = run_tool("tools/analyze_e2b_matrix.py", "--self-test")
    if self_test_code != 0:
        problems.append("the matrix analyzer's own self-test does not pass")

    decision = "GO_TO_E2_C" if not problems else "NOT_YET"
    summary = {
        "schemaVersion": 1,
        "release": "E2-B-paragraph-format-contract",
        "decision": decision,
        "artifact": {"profile": manifest.get("profile"), "wasmSha256": wasm,
                     "loaderSha256": loader, "workerSha256": worker},
        "contract": {"version": contract.get("version"),
                     "abiVersion": contract.get("abiVersion"),
                     "actions": len(contract.get("actions") or {}),
                     "crossParagraphDisposition":
                         contract.get("crossParagraphDisposition")},
        "matrix": matrix["browsers"],
        "negative": negative["browsers"],
        "actionInventory": inventory,
        "e1cBundle": bundle,
        "matrixSelfTest": "passed" if self_test_code == 0 else "FAILED",
        "problems": problems,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if decision == "GO_TO_E2_C" else 1


if __name__ == "__main__":
    sys.exit(main())
