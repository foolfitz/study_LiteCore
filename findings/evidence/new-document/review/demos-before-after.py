#!/usr/bin/env python3
"""The review's red demos (DISPOSITION.md): each mutation of the counted 0.2.19 report scored by the tool
BEFORE the review (`git show 3b818514:wasm_sdk_probe/tools/check_m3_new_document.py`, copied to a temporary
file, the sibling modules on PYTHONPATH) and by the tool in the tree.  Then every committed report scored by
both, to show no verdict moved.  Offline: no ddev, no browser.  Output: demos-before-after.txt.

    python3 findings/evidence/new-document/review/demos-before-after.py
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TOOLS = REPO / "wasm_sdk_probe" / "tools"
TOOL = TOOLS / "check_m3_new_document.py"
EVIDENCE = HERE.parent
BEFORE = "3b818514"
MARK = "zqx"


def run(r, arm, browser="chrome"):
    return next(x for x in r["runs"] if x["arm"] == arm and x["browser"] == browser)


def demos(base: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    r = copy.deepcopy(base); r["settingsRestored"]["locale"] = {"key": "locale", "value": None, "exit": 1, "readback": None}
    out["f1b-locale-restore-failed (codex Q6: delete and readback failed)"] = r
    r = copy.deepcopy(base)
    for x in r["runs"]:
        x["reopen"]["a11y"] = {"offers": None, "text": None, "reason": None, "deferred": None}
    out["f2-offers-not-read"] = r
    r = copy.deepcopy(base)
    for x in r["runs"]:
        del x["reopen"]["a11y"]
    out["f2b-a11y-block-missing"] = r
    r = copy.deepcopy(base)
    for x in r["runs"]:
        for k in x["keys"]:
            k["genBefore"] = None; k["genAfter"] = None
    out["f3-generation-unread"] = r
    r = copy.deepcopy(base); run(r, "TW")["savedFile"]["paragraphs"] = ["zqxOLD"]
    out["f4-cached-old-document (codex N3)"] = r
    r = copy.deepcopy(base); run(r, "EN", "firefox")["savedFile"]["paragraphs"] = [MARK, "UNEXPECTED TEXT"]
    out["f4b-extra-paragraph (codex N4)"] = r
    r = copy.deepcopy(base)
    for x in r["runs"]:
        new = str(int(x["createdFile"]["fileid"]) + 50000)
        x["savedFile"]["fileid"] = new
        x["reopen"]["landed"] = x["reopen"]["landed"].split("fileId=")[0] + "fileId=" + new
        x["reopen"]["host"]["file"]["id"] = int(new)
    out["f5-fileid-replaced (opus N4+N5)"] = r
    r = copy.deepcopy(base); r["readOnly"]["sharePermissions"] = 31; r["readOnly"]["otherSees"] = "SRGDNVCK"
    out["f6-share-allows-create (codex N8a)"] = r
    r = copy.deepcopy(base); r["label"] = "shakedown"; r["runs"] = []; r["stopped"] = "kwallet locked"
    out["f7-stopped-no-runs-shakedown"] = r
    r = copy.deepcopy(base); r["label"] = "shakedown"; r["runs"] = []
    out["f7b-no-runs-shakedown"] = r
    r = copy.deepcopy(base)
    r["hostStatic"].update(hostCommit="1234567", hostVersion="0.2.20", buildId="a" * 16, servedPage="9" * 64,
                           changedOutsideAllowed=["js/litecore-editor.js"])
    out["q3-next-host (0.2.20-shaped, bindings not moved)"] = r
    return out


def score(tool: Path, report: Path) -> str:
    env = {**os.environ, "PYTHONPATH": str(TOOLS)}
    done = subprocess.run([sys.executable, str(tool), "--score", str(report)], capture_output=True, text=True, env=env)
    return (done.stdout.strip().splitlines() or [done.stderr.strip().splitlines()[-1] if done.stderr.strip() else ""])[-1]


def main() -> int:
    base_path = EVIDENCE / "runs" / "2026-10-14T035226Z.json"
    base = json.loads(base_path.read_text())
    lines = [f"# Red demos: the tool at {BEFORE} (OLD) against this tree's tool (NEW), on mutations of {base_path.relative_to(REPO)}", ""]
    with tempfile.TemporaryDirectory() as tmp:
        old = Path(tmp) / "check_m3_new_document_before.py"
        old.write_text(subprocess.run(["git", "show", f"{BEFORE}:wasm_sdk_probe/tools/check_m3_new_document.py"],
                                      cwd=REPO, capture_output=True, text=True, check=True).stdout)
        for name, report in demos(base).items():
            path = Path(tmp) / (name.split(" ")[0] + ".json")
            path.write_text(json.dumps(report, ensure_ascii=False))
            lines += [f"## {name}", f"OLD: {score(old, path)}", f"NEW: {score(TOOL, path)}", ""]
        lines += ["# Committed reports: OLD against NEW (a verdict that moved would be a finding)", ""]
        for report in sorted(list((EVIDENCE / "runs").glob("*.json")) + list((EVIDENCE / "shakedown").glob("*.json"))):
            a, b = score(old, report), score(TOOL, report)
            lines += [f"{'SAME ' if a == b else 'MOVED'} {report.relative_to(EVIDENCE)}", f"  OLD: {a}", f"  NEW: {b}", ""]
    (HERE / "demos-before-after.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
