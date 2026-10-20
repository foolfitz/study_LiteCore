#!/usr/bin/env python3
"""Exhibit every assertion of the viewer draft's unit test going red.

AGENTS.md section 6: a green run only proves the checker can return green.  This
copies `wasm_sdk_probe/viewer-shell/` into a scratch directory, breaks the copy
in one named way, runs the node test against the copy (VIEWER_SHELL_DIR), and
records WHICH tests failed and with what message.  The real source is never
edited and nothing outside the scratch directory is written, except the two
report files next to this script.

Each mutation must (a) apply exactly once -- a replacement that silently missed
would be a green run labelled "red case" -- and (b) turn the test red in at least
one of the tests it names.  The unmutated copy is run through the same path first
and must be fully green, so the harness cannot be red for its own reasons.

Usage: red-cases.py            (writes red-cases.json and red-cases.txt here)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3] / "wasm_sdk_probe"
TEST = PROJECT / "tests" / "ods-viewer-session.test.mjs"

SESSION = "ods-viewer-session.js"
ADAPTER = "w7-adapter.js"
# Added 2026-10-20 with the package probe (specs/SPEC-M4-ods-in-nextcloud.md §5.2).
PROBE = "odf-package-probe.js"

# id, file, [(old, new), ...], what is broken, tests that must go red
MUTATIONS = [
    ("M01-one-tab-short", SESSION,
     [("    return view.partNames.map((label, index) => {",
       "    return view.partNames.slice(0, -1).map((label, index) => {")],
     "the tab strip has one tab fewer than parts",
     ["pre-W7 handle: one tab per part"]),
    ("M02-scheduler-always-part-0", SESSION,
     [("      part,\n      scale: 1,", "      part: 0,\n      scale: 1,")],
     "the scheduler is reconfigured with part 0 whatever part was switched to",
     ["showPart(k): the engine is switched"]),
    ("M03-readback-echoes-request", SESSION,
     [("    const readBack = this._view.readBackPart();\n    const shown",
       "    const readBack = k;\n    const shown")],
     "the session reports the requested part as the read-back",
     ["an engine that ignores set_part", "pre-W7: showPart(1) is refused"]),
    ("M04-adapter-readback-cached-request", ADAPTER,
     [("  const fallbacks = [];\n", "  const fallbacks = [];\n  let requestedPart = null;\n"),
      ("      const result = await handle.setPart(k, options);",
       "      const result = await handle.setPart(k, options);\n      requestedPart = k;"),
      ("      return Number.isInteger(handle.currentPart) ? handle.currentPart : null;",
       "      return requestedPart;")],
     "the adapter's read-back is the last part asked for, not the engine's current part",
     ["an engine that ignores set_part", "W7-shaped handle: tabs carry"]),
    ("M05-pre-w7-switch-not-refused", ADAPTER,
     [("        if (k !== 0) {", "        if (k < 0) {")],
     "without a part switch, part k > 0 is accepted and shown",
     ["pre-W7: showPart(1) is refused"]),
    ("M06-text-document-not-refused", SESSION,
     [("    if (this._view.documentTypeKnown && this._view.documentType !== SPREADSHEET) {",
       "    if (false) {")],
     "a document the engine says is text is shown as a spreadsheet",
     ["a known non-spreadsheet document is refused"]),
    ("M07-refusal-does-not-release", SESSION,
     [("      await this._release();\n      this._fail(\"refused\", refusal, \"DOCUMENT_TYPE_REFUSED\");",
       "      this._fail(\"refused\", refusal, \"DOCUMENT_TYPE_REFUSED\");")],
     "a refused document is left open in the engine",
     ["a known non-spreadsheet document is refused"]),
    ("M08-unknown-type-refused", SESSION,
     [("    if (this._view.documentTypeKnown && this._view.documentType !== SPREADSHEET) {",
       "    if (this._view.documentType !== SPREADSHEET) {")],
     "an UNKNOWN document type is refused too (refusal no longer needs a known wrong type)",
     ["refusal needs a KNOWN wrong type"]),
    ("M09-spoof-flag-always-true", ADAPTER,
     [("  return { openName: name, nameSpoofed: false };",
       "  return { openName: name, nameSpoofed: true };")],
     "the spoof flag is set even when the name was passed through unchanged",
     ["the spoof flag is set only when the adapter rewrote the name"]),
    ("M10-spoof-not-recorded", ADAPTER,
     [("nameSpoofed: true };\n  return { openName: name, nameSpoofed: false };",
       "nameSpoofed: false };\n  return { openName: name, nameSpoofed: false };")],
     "the name is rewritten to .odt but the flag says it was not",
     ["the spoof flag is set only when the adapter rewrote the name"]),
    ("M11-spoof-ignores-capability", ADAPTER,
     [("  if (/\\.ods$/i.test(name) && !engineAcceptsOds(manifest))",
       "  if (/\\.ods$/i.test(name))")],
     "an engine that lists the ods capability is spoofed anyway",
     ["the spoof flag is set only when the adapter rewrote the name"]),
    ("M12-stale-tile-guard-removed", SESSION,
     [("    if (this._state !== \"ready\" || entry.generation !== this._liveGeneration) {",
       "    if (this._state !== \"ready\") {")],
     "a late tile of the previous part is delivered under the new one",
     ["a tile of the previous part never reaches onTile"]),
    ("M13-live-generation-not-reset", SESSION,
     [("    this._liveGeneration = null;\n    this._scheduler.configureDocument({",
       "    this._scheduler.configureDocument({")],
     "a part switch does not invalidate the previous part's generation",
     ["a tile of the previous part never reaches onTile"]),
    ("M14-listener-attached-after-init", SESSION,
     [("      this._engine = await this._engineFactory({ onEvent: this._eventSink });",
       "      this._engine = await this._engineFactory({});\n      this._engine.onEvent(this._eventSink);")],
     "the event listener is added after the engine has initialised",
     ["the event listener is attached before initialisation"]),
    ("M15-render-also-clicks", ADAPTER,
     [("    render(region, options) {\n      return handle.render(region, options);",
       "    render(region, options) {\n      handle.click(0, 0);\n      return handle.render(region, options);")],
     "painting a tile also sends the engine a click",
     ["read-only: only render / setPart / close"]),
    ("M16-w7-vocabulary-in-session", SESSION,
     [("const DEFAULT_OPEN_TIMEOUT_MS = 180000;",
       "const DEFAULT_OPEN_TIMEOUT_MS = 180000; // pre-W7 timeout")],
     "the word pre-W7 appears outside the adapter",
     ["W7 vocabulary appears only in the adapter"]),
    ("M17-unknown-type-mislabelled", ADAPTER,
     [("const documentType = typeKnown ? handle.documentType : UNKNOWN_DOCUMENT_TYPE;",
       "const documentType = typeKnown ? handle.documentType : SPREADSHEET;")],
     "a handle without documentType is reported as a spreadsheet",
     ["pre-W7 handle: one tab per part"]),
    ("M18-synthesised-names-flagged-as-engine", ADAPTER,
     [("    namesFromEngine: namesUsable,", "    namesFromEngine: true,")],
     "invented sheet names are reported as the engine's",
     ["pre-W7 handle: one tab per part", "partNames that disagree with parts"]),
    ("M19-names-length-not-checked", ADAPTER,
     [("    && handle.partNames.length === parts\n", "")],
     "a partNames array of the wrong length is used as it is",
     ["partNames that disagree with parts"]),
    ("M20-switches-not-serialised", SESSION,
     [("    const run = this._chain.then(() => this._showPart(k));",
       "    const run = this._showPart(k);")],
     "two quick tab clicks run concurrently",
     ["switches are serialised"]),
    ("M21-crash-ignored", SESSION,
     [("    if (event?.event === \"worker-crashed\"",
       "    if (false && event?.event === \"worker-crashed\"")],
     "a worker-crashed event does not change the state",
     ["a worker crash takes the session"]),
    ("M22-range-not-checked", SESSION,
     [("    if (!Number.isInteger(k) || k < 0 || k >= this._view.parts) {",
       "    if (false) {")],
     "a part outside 0..parts-1 is passed to the engine",
     ["a part outside 0..parts-1 is refused"]),
    ("M23-open-failure-not-released", SESSION,
     [("      await this._release();\n      if (this._closeRequested)\n        throw error;",
       "      if (this._closeRequested)\n        throw error;")],
     "a failed open leaves the engine running",
     ["an open that fails is typed"]),
    ("M25-late-engine-adopted", SESSION,
     [("      this._engine = await this._engineFactory({ onEvent: this._eventSink });\n      this._assertNotClosedDuringOpen();",
       "      this._engine = await this._engineFactory({ onEvent: this._eventSink });")],
     "an engine that finishes starting after close() is used to open the document",
     ["a close() that arrives while the document is opening"]),
    ("M26-late-document-adopted", SESSION,
     [("      this._view = adaptHandle(handle);\n      this._assertNotClosedDuringOpen();",
       "      this._view = adaptHandle(handle);")],
     "a document that opens after close() is adopted and the session comes back to life",
     ["a close() that arrives while the document is opening"]),
    ("M27-close-does-not-record-itself", SESSION,
     [("    this._closeRequested = true;\n    await this._release();",
       "    await this._release();")],
     "close() does not tell an in-progress open that it was closed",
     ["a close() that arrives while the document is opening"]),
    ("M24-initial-part-not-read", SESSION,
     [("    const initial = this._view.readBackPart();", "    const initial = null;")],
     "the part the engine is on at open is not read; part 0 is assumed even when the engine says otherwise",
     ["W7-shaped handle: tabs carry"]),
    # ---- 2026-10-20: the package probe (SPEC-M4 §5.2, review C6) ----
    ("M28-encrypted-not-refused", SESSION,
     [("    if (this._packageProbe.encrypted === true) {", "    if (false) {")],
     "an encrypted package goes on to the engine",
     ["an encrypted package is refused before any engine is asked",
      "the probe reads a STORED manifest"]),
    ("M29-unreadable-refused", SESSION,
     [("    if (this._packageProbe.encrypted === true) {",
       "    if (this._packageProbe.encrypted !== false) {")],
     "a package the probe cannot read is refused as if it were encrypted",
     ["a package the probe cannot read goes to the engine"]),
    ("M30-engine-requested-from-the-start", SESSION,
     [("    this._engineRequested = false;\n", "    this._engineRequested = true;\n")],
     "the state says an engine was asked for before any was",
     ["an encrypted package is refused before any engine is asked",
      "a close() that arrives while the document is opening"]),
    ("M31-close-during-probe-ignored", SESSION,
     [("    this._packageProbe = await probeOdfPackage(bytes);\n    this._assertNotClosedDuringOpen();\n",
       "    this._packageProbe = await probeOdfPackage(bytes);\n")],
     "a close() during the package read does not stop the engine from being started",
     ["a close() that arrives while the document is opening"]),
    ("M32-deflate-not-read", PROBE,
     [("  else if (entry.method === 8)", "  else if (entry.method === 9)")],
     "a deflated manifest (every corpus file's) is not read",
     ["an encrypted package is refused before any engine is asked",
      "a plain package opens, and the state says what the probe saw"]),
    ("M33-stored-not-read", PROBE,
     [("  if (entry.method === 0)\n    raw = compressed;", "  if (entry.method === 0)\n    raw = new Uint8Array(0);")],
     "a stored manifest is read as empty",
     ["the probe reads a STORED manifest"]),
    ("M34-prefixed-element-missed", PROBE,
     [("const ENCRYPTION_DATA = /<(?:[A-Za-z_][\\w.-]*:)?encryption-data\\b/;",
       "const ENCRYPTION_DATA = /<encryption-data\\b/;")],
     "only an unprefixed encryption-data element counts; ODF's is manifest:encryption-data",
     ["an encrypted package is refused before any engine is asked",
      "the probe reads a STORED manifest"]),
    ("M35-unreadable-reason-dropped", PROBE,
     [("  return { readable: false, encrypted: null, reason };",
       "  return { readable: false, encrypted: null, reason: null };")],
     "the probe gives up without saying why",
     ["a package the probe cannot read goes to the engine"]),
    # ---- 2026-10-20: the refit (SPEC-M4 E4b, review B2) ----
    ("M36-refit-never", SESSION,
     [("    if (widthTwips === this._fitted.widthTwips && heightTwips === this._fitted.heightTwips)\n      return false;",
       "    if (true)\n      return false;")],
     "the page never refits, so the widened sheet's last columns stay unpainted",
     ["refit: a paint that widened the sheet"]),
    ("M37-refit-always", SESSION,
     [("    if (widthTwips === this._fitted.widthTwips && heightTwips === this._fitted.heightTwips)\n      return false;",
       "    if (false)\n      return false;")],
     "the page refits after every paint whether or not anything moved",
     ["refit: a paint that widened the sheet", "refit does nothing when no paint moved the size"]),
    ("M38-fitted-size-not-recorded", SESSION,
     [("    this._fitted = { widthTwips: dimensions.widthTwips, heightTwips: dimensions.heightTwips };\n", "")],
     "the size the scheduler was configured with is not remembered",
     ["refit: a paint that widened the sheet"]),
]


def run_node(shell_dir: Path) -> dict:
    env = dict(os.environ, VIEWER_SHELL_DIR=str(shell_dir))
    done = subprocess.run(
        ["node", "--test", "--test-reporter=tap", str(TEST)],
        capture_output=True, text=True, env=env, cwd=PROJECT, timeout=300)
    text = done.stdout
    failures = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^not ok \d+ - (.*)$", line)
        if not match:
            continue
        block = []
        for follow in lines[index + 1:index + 40]:
            if re.match(r"^(not )?ok \d+ - ", follow):
                break
            block.append(follow)
        message = ""
        for at, b in enumerate(block):
            if b.startswith("  error:"):
                inline = b[len("  error:"):].strip()
                if inline and inline != "|-":
                    message = inline.strip("'\"")
                else:
                    body = []
                    for nxt in block[at + 1:]:
                        if not nxt.startswith("    "):
                            break
                        if nxt.strip():
                            body.append(nxt.strip())
                    message = " / ".join(body[:2])
                break
        # The FIRST stack frame inside the test file is the failing assertion.
        where = ""
        for b in block:
            found = re.search(r"ods-viewer-session\.test\.mjs:(\d+):\d+\)?\s*$", b)
            if found and "location:" not in b:
                where = found.group(1)
                break
        source = ""
        if where:
            source = TEST.read_text(encoding="utf-8").splitlines()[int(where) - 1].strip()
        failures.append({"test": match.group(1), "message": message,
                         "assertionLine": where, "assertion": source})
    counts = {k: int(m.group(1)) for k in ("tests", "pass", "fail")
              for m in [re.search(rf"^# {k} (\d+)$", text, re.M)] if m}
    return {"exit": done.returncode, "counts": counts, "failures": failures,
            "stderr": done.stderr[-500:]}


def scratch_copy(root: Path, name: str) -> Path:
    target = root / name
    (target / "viewer-shell").parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PROJECT / "viewer-shell", target / "viewer-shell")
    # The session imports ../reader-shell/tile-scheduler.js (the real, unmodified one).
    os.symlink(PROJECT / "reader-shell", target / "reader-shell")
    return target / "viewer-shell"


def main() -> int:
    if not TEST.is_file():
        raise SystemExit(f"missing {TEST}")
    results = []
    problems = []
    with tempfile.TemporaryDirectory(prefix="viewer-red-") as tmp:
        root = Path(tmp)
        control = run_node(scratch_copy(root, "control"))
        control_ok = control["exit"] == 0 and control["counts"].get("fail") == 0 \
            and control["counts"].get("pass") == control["counts"].get("tests") \
            and control["counts"].get("tests", 0) > 0
        if not control_ok:
            problems.append("the UNMUTATED copy is not fully green through the harness")
        results.append({"id": "control-unmutated", "applied": True, **control})
        for mutation_id, file, edits, what, expect in MUTATIONS:
            shell = scratch_copy(root, mutation_id)
            path = shell / file
            source = path.read_text(encoding="utf-8")
            applied = True
            for old, new in edits:
                if source.count(old) != 1:
                    applied = False
                    problems.append(f"{mutation_id}: replacement occurs "
                                    f"{source.count(old)} times, want exactly 1: {old[:60]!r}")
                    break
                source = source.replace(old, new)
            if not applied:
                results.append({"id": mutation_id, "applied": False, "what": what})
                continue
            path.write_text(source, encoding="utf-8")
            outcome = run_node(shell)
            red = outcome["exit"] != 0 and outcome["counts"].get("fail", 0) > 0
            caught_by = [f for f in outcome["failures"]
                         if any(e in f["test"] for e in expect)]
            if not red:
                problems.append(f"{mutation_id}: the test stayed GREEN")
            elif not caught_by:
                problems.append(f"{mutation_id}: red, but not in a test it names "
                                f"{expect}; failed: {[f['test'] for f in outcome['failures']]}")
            results.append({"id": mutation_id, "applied": True, "what": what,
                            "expectedTests": expect, "red": red,
                            "caughtByExpected": bool(caught_by), **outcome})
    # NON-VACUITY: every test name in the control run must be named by at least
    # one mutation's expectation, otherwise some assertion was never exhibited red.
    control_names = []
    env = dict(os.environ, VIEWER_SHELL_DIR=str(PROJECT / "viewer-shell"))
    listing = subprocess.run(["node", "--test", "--test-reporter=tap", str(TEST)],
                             capture_output=True, text=True, env=env, cwd=PROJECT).stdout
    control_names = re.findall(r"^ok \d+ - (.*)$", listing, re.M)
    uncovered = [name for name in control_names
                 if not any(any(e in name for e in m[4]) for m in MUTATIONS)]
    if not control_names:
        problems.append("the listing run found no tests")
    if uncovered:
        problems.append(f"tests no mutation names: {uncovered}")
    report = {"tests": control_names, "mutations": len(MUTATIONS),
              "uncoveredTests": uncovered, "problems": problems, "results": results}
    (HERE / "red-cases.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out = [f"control (unmutated): {results[0]['counts']}"]
    for r in results[1:]:
        if not r.get("applied"):
            out.append(f"{r['id']}: NOT APPLIED")
            continue
        first = r["failures"][0] if r["failures"] else {}
        out.append(f"{r['id']}: red={r['red']} failed={r['counts'].get('fail')} "
                   f"named-test-caught={r['caughtByExpected']}")
        for f in r["failures"]:
            out.append(f"    - {f['test'][:60]}")
            out.append(f"        line {f['assertionLine']}: {f['assertion'][:110]}")
            out.append(f"        message: {f['message'][:120]}")
    out.append(f"problems: {problems or 'none'}")
    (HERE / "red-cases.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
