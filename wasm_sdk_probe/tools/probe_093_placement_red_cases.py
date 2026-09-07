#!/usr/bin/env python3
"""Finding 093, option B, step 3: prove `the-projection-is-placed-where-the-
document-is` can go red before it is trusted for going green.

AGENTS.md §6.  A check its own author declares green has only demonstrated that
it returns green.  This runs the check's predicate against a page that has the
defect it is written for, and against a page that has the OTHER defect it is
written for, and requires both to fail -- and it runs it against the page as
landed and requires that to pass.

IT DOES NOT REIMPLEMENT THE PREDICATE.  `projection_placement_verdict` and
`READ_A11Y_GEOMETRY` are imported from `tools/run_e2_c_product_path.py`, and
the two mutations are read out of that file's `MUTATIONS` table rather than
written out again here.  Two implementations of one rule drift, and they
disagree on the day nobody is checking.

WHY THIS EXISTS SEPARATELY FROM `--mutate`.  `run_e2_c_product_path.py
--mutate <name>` is the normal home for this and it stays the normal home: it
drives the whole net and requires the owning check to be the one that reddens.
It also takes eight minutes per arm and drives forty checks to exercise one.
This probe answers only "can this predicate fail, on a real page, for each of
its two failure modes", which is the question that has to be answered before
the check is landed rather than after.

WHAT IT CANNOT ANSWER, and it is the point of option B rather than a footnote:
clause C3 -- the node for the paragraph the caret is in sits where that
paragraph is drawn -- needs an engine that emits per-paragraph geometry, and no
linked artifact does.  Every arm below reports `clausesExercised`, so a green
arm cannot be read as evidence about a clause that never ran.  The acceptance
for C3 is `findings/evidence/093/ORACLE-fix-shape.md` measured by
`tools/probe_093_fix_shape_oracle.py`, and it cannot be met until the relink.

Nothing under `dist/` or `web/` is written: every arm is a symlink mirror of
`dist/` with one file materialised, the same mechanism the product path and the
phase-3 probe use.

Usage:
  probe_093_placement_red_cases.py [--profile e2-editor-v12] [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))

from r7_support import evaluate, wait_page                       # noqa: E402
from run_browser_probe import ChromeSession, free_port           # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate             # noqa: E402
from run_e2_c_product_path import (                              # noqa: E402
    MUTATIONS, READ_A11Y_GEOMETRY, build_mirror,
    projection_placement_verdict, repointed_page)

# The two mutations this probe drives, and what each one is a red case FOR.
# Named here rather than "every mutation whose check is ours", because a table
# that grows silently would let a new mutation join without anyone deciding it
# belongs.
ARMS = {
    "a11y-projection-at-its-static-position":
        "C2 -- finding 093 itself: the container returns to the static "
        "position after the canvas, at the bottom of the paper",
    "geometry-declared-but-not-delivered":
        "C1 -- the contract promises each paragraph's rectangle and the "
        "payload carries none, which is an engine that stopped emitting or a "
        "worker allowlist that dropped the fields",
}


def wait_ready(session, timeout=180.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = evaluate(session, READ_STATE) or {}
        if last.get("state") in ("ready", "stopped", "expired"):
            return last
        time.sleep(0.25)
    return last


def measure(root: Path, overrides: dict, label: str, note: str,
            settle: float) -> dict:
    scratch = Path(tempfile.mkdtemp(prefix=f"f093rc-{label}-"))
    mirror = scratch / "root"
    build_mirror(root, mirror, overrides)
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(mirror)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    record: dict = {"arm": label, "note": note,
                    "filesMaterialised": sorted(overrides)}
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session = ChromeSession("cold")
        navigate(session, base)
        state = wait_ready(session)
        record["pageState"] = state
        if (state or {}).get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = f"page state {(state or {}).get('state')!r}"
            return record
        # A FIXED settle with no early exit, for the reason phase 2 recorded:
        # the projection needs 1.0-1.5 s, and a loop that stops at the first
        # `projected` gives one arm as long as it needs and another the whole
        # wait -- and the difference between the arms is what is being measured.
        time.sleep(settle)
        reading = evaluate(session, READ_A11Y_GEOMETRY) or {}
        record["reading"] = reading
        record["verdict"] = projection_placement_verdict(reading)
        record["outcome"] = "MEASURED"
        return record
    finally:
        if session is not None:
            session.close()
        server.terminate()
        server.wait(timeout=10)
        shutil.rmtree(scratch, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-editor-v12",
                        help="the profile the mirrored page is pointed at. "
                             "The default is the candidate, because the "
                             "shipped profile carries no outline at all and "
                             "the second mutation would be DEAD on it -- a "
                             "run reporting 'the product survived it' having "
                             "never executed the line")
    parser.add_argument("--settle", type=float, default=6.0)
    parser.add_argument("--out")
    args = parser.parse_args()

    root = PROJECT / "dist"
    page_source = (root / "e2-editor-app.js").read_text(encoding="utf-8")
    html_source = (root / "e2-editor.html").read_text(encoding="utf-8")
    manifest = root / "profiles" / args.profile / "sdk-manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"no manifest at {manifest}")
    page, pin_before, wasm = repointed_page(page_source, args.profile,
                                            manifest)

    report = {
        "schemaVersion": 1,
        "finding": "093",
        "step": "option-B-step-3-red-cases",
        "evidenceClass": "diagnostic",
        "check": "the-projection-is-placed-where-the-document-is",
        "predicateFrom": "tools/run_e2_c_product_path.py "
                         "(projection_placement_verdict), imported not copied",
        "profile": args.profile,
        "pagePinBefore": pin_before,
        "wasmSha256": wasm[:16],
        "mutation": "symlink mirrors of dist/ only; nothing under dist/ or "
                    "web/ is written by this probe",
        "limitation": "clause C3 needs an engine that emits per-paragraph "
                      "geometry and none exists yet, so no arm below "
                      "exercises it. Every arm reports clausesExercised.",
        "arms": [],
    }

    # THE SHIPPED PROFILE, first, and it is not a formality: the check has to
    # pass on a page that projects nothing at all, or landing it turns the
    # incumbent red for a capability the incumbent never claimed.
    report["arms"].append(measure(
        root, {}, "control-shipped",
        "the page exactly as it ships, pointing at the profile it ships "
        "pointing at. Expect PASS with geometry 'noProjection'.",
        args.settle))

    report["arms"].append(measure(
        root, {"e2-editor-app.js": page.encode("utf-8")}, "control-candidate",
        f"the page repointed at {args.profile}, otherwise as landed. Expect "
        f"PASS with geometry 'absent' -- the honest degradation of a profile "
        f"linked before the geometry existed.",
        args.settle))

    for name, why in ARMS.items():
        spec = MUTATIONS[name]
        source = page if spec["path"] == "e2-editor-app.js" else html_source
        hits = source.count(spec["find"])
        if hits != 1:
            report["arms"].append({
                "arm": name, "outcome": "NOT_ESTABLISHED",
                "why": f"the mutation's pattern matched {hits} times in "
                       f"{spec['path']}; the tree moved under it"})
            continue
        overrides = {"e2-editor-app.js": page.encode("utf-8")}
        overrides[spec["path"]] = source.replace(
            spec["find"], spec["replace"], 1).encode("utf-8")
        report["arms"].append(measure(
            root, overrides, name,
            f"{why}. Reintroduces: {spec['reintroduces']}. Expect FAIL.",
            args.settle))

    measured = [a for a in report["arms"] if a.get("outcome") == "MEASURED"]
    greens = [a for a in measured if a["arm"].startswith("control")]
    reds = [a for a in measured if not a["arm"].startswith("control")]
    report["controlsGreen"] = all(a["verdict"]["ok"] for a in greens)
    report["redCasesRed"] = (len(reds) == len(ARMS)
                             and all(not a["verdict"]["ok"] for a in reds))
    report["allArmsMeasured"] = len(measured) == len(report["arms"])
    report["ok"] = bool(report["controlsGreen"] and report["redCasesRed"]
                        and report["allArmsMeasured"] and greens)
    report["verdict"] = (
        "the predicate passes on the page as landed and fails on both of the "
        "defects it is written for" if report["ok"] else
        "NOT DEMONSTRATED -- see the arms")

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    for arm in report["arms"]:
        print(f"{arm['arm']}: {arm.get('outcome')} "
              f"ok={arm.get('verdict', {}).get('ok')} "
              f"geometry={arm.get('verdict', {}).get('geometry')}",
              file=sys.stderr)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
