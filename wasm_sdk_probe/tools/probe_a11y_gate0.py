#!/usr/bin/env python3
"""A11y gate 0: does LOK emit a focused paragraph on WASM?

Roadmap section 3.3 puts ONE question at this gate.  This probe asks it and
nothing else.  Criteria are fixed in `handoff/a11y-gate-0/PREDICTION.md`, written
2026-08-21 BEFORE the patch and before any rebuild -- read that first.

PREPARED, NOT RUN.  It cannot pass on today's core: `SwEditWin::CreateAccessible`
returns {} whenever ENABLE_WASM_STRIP_ACCESSIBILITY is set
(`sw/source/uibase/docvw/edtwin.cxx:6532-6542`), and on 26.8's Emscripten no flag
combination clears it (finding 057).  So the probe REFUSES to run against a build
whose `config_wasm_strip.h` still sets the macro -- see G0-1.  That refusal is the
point: a run against an unpatched build measures nothing, and a number from it
would be worse than no number.

Nothing new is added to the engine.  It already reports every field this needs
(`probe_engine.cpp:1090-1100`) and already probes `getA11yFocusedParagraph`
(`:1835`); what has never existed is a build where the call sites are compiled in.

Usage:
  probe_a11y_gate0.py --browser chrome [--profile e2-editor-v4] [--out FILE]
  probe_a11y_gate0.py --check-build-only
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from run_e2_c_product_path import (  # noqa: E402
    LINE_INK, OPEN_FILE, POINT_AT, build_mirror, caret_click_fractions,
    place_caret_and_settle, stable_bands,
)

PROJECT = Path(__file__).resolve().parent.parent

# RESOLVED 2026-08-22: the page does NOT surface it, and it never will.
#
# The first version of this constant looked for `#s-a11y` and fell back to
# saying "read it from the editor state instead".  There is no such element and
# adding one would be a permanent product change bought for one diagnostic run.
# The block is already in the editor state -- `sdk-worker.js:318` projects the
# engine's `a11y` into `caretParagraph` -- so the mirror below appends a reader
# that closes over the page's own `session`, and this asks that.
#
# It also answers the PREDICTION's own trap in passing: reading through
# `caretParagraph` proves the WORKER FORWARDED the field. An engine field
# nobody forwards does not exist, and a probe that read the engine some other
# way could not tell those apart.
READ_A11Y = """(() => {
if (typeof globalThis.__a11yGate0 !== 'function')
  return { unavailableToProbe:
    'the served page carries no __a11yGate0 reader, so this run was NOT '
    + 'against the gate mirror and measures nothing -- see PREDICTION.md G0-2' };
return globalThis.__a11yGate0();
})()"""

# The three edits the mirror makes to the product page, each with a reason.
#
#   1. the worker URL, because the product page hard-codes the SHIPPED profile
#      and the gate needs the one linked against the a11y core;
#   2. the pinned wasm hash, because the page refuses to open a document whose
#      wasm does not start with it (PAGE_BUILD_MISMATCH) -- that guard is
#      doing its job, and a gate artifact is exactly what it is built to
#      reject;
#   3. the reader above.
#
# dist/ is never written: `build_mirror` symlinks everything and materialises
# only what is overridden, which is the same machinery the product path's
# diagnostic arms use.
GATE_READER = """
// APPENDED BY probe_a11y_gate0.py -- not part of the product page.
//
// The KEYS as well as the value, because run 1 came back
// `caretParagraph: null` and null has two readings that matter differently:
// the worker projected the block and the engine's `a11y` was falsy, or this
// snapshot never went through that projection at all. `keys` tells them
// apart, and `hasKey` says whether the field is present-and-null or absent.
globalThis.__a11yGate0 = () => {
  const snapshot = session?.state?.snapshot?.editorState;
  if (!snapshot) return { unavailableToProbe: 'no editor state on the page' };
  // BOTH, and which one carried it is part of the record.
  //
  // Run 2 measured that this page's snapshot is the RAW engine state -- its
  // keys include `a11y` and `schedulerProbe`, which the product projection
  // drops -- so `caretParagraph` is absent here rather than null-because-empty.
  // Reading only the projected name would have reported "nothing came back"
  // about a block that was sitting right there under its engine name.
  return {
    a11y: snapshot.a11y ?? null,
    caretParagraph: snapshot.caretParagraph ?? null,
    projected: Object.prototype.hasOwnProperty.call(snapshot, 'caretParagraph'),
    keys: Object.keys(snapshot).sort(),
    sourceSequence: snapshot.sourceSequence ?? null,
  };
};
"""


def build_provides_accessibility(core_build: str | None) -> dict:
    """G0-1, and it runs BEFORE a browser starts.

    Delegated to the standing guard rather than reimplemented:
    `check_core_build_provides.py` already reads
    `config_host/config_wasm_strip.h` for the macro AND `sw/source/core/access`
    for the objects, and it requires both -- one alone agrees with a build that
    cannot work.

    `--core-build` is passed through rather than defaulted away.  With no
    argument the guard judges the PRODUCT's core, which is red and SHOULD stay
    red: the shipped profile does not provide accessibility and nothing about
    this gate changes that.  The gate build is a different core, and naming it
    here is what keeps the two claims apart.
    """
    guard = PROJECT / "tools" / "check_core_build_provides.py"
    command = [sys.executable, str(guard)]
    if core_build:
        command += ["--build", core_build]
    completed = subprocess.run(command, capture_output=True, text=True)
    return {
        "guard": "tools/check_core_build_provides.py",
        "coreBuild": core_build or "(the product's)",
        "exitCode": completed.returncode,
        "provides": completed.returncode == 0,
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-800:],
    }


def gate_mirror(scratch: Path, profile: str) -> dict:
    """Serve the product page against the gate profile, without changing it."""
    page_relative = "e2-editor-app.js"
    source = (PROJECT / "dist" / page_relative).read_text(encoding="utf-8")

    # WHICHEVER profile the page currently loads, not a hardcoded one.
    #
    # This named `e2-editor-v4` until the v5 cutover, which would have made the
    # count-1 assertion below fire -- loudly, which is the good failure. The
    # generic match keeps the assertion (still exactly one) while surviving a
    # product that moves, because the thing this probe cares about is that
    # there is ONE worker URL to rewrite, not which one it is.
    matches = re.findall(r'"\./profiles/[A-Za-z0-9._-]+/sdk-worker\.js"', source)
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one profile worker URL in dist/{page_relative}, "
            f"found {len(matches)}; the page moved under this probe and the "
            f"mirror would be silent about it")
    worker_before = matches[0]
    worker_after = f'"./profiles/{profile}/sdk-worker.js"'
    page = source.replace(worker_before, worker_after, 1)

    manifest = json.loads(
        (PROJECT / "dist" / "profiles" / profile / "sdk-manifest.json")
        .read_text(encoding="utf-8"))
    wasm_sha = manifest["editorContract"]["wasmSha256"]
    pin_match = re.search(r'const PINNED_WASM_SHA256 = "([0-9a-f]+)";', page)
    if not pin_match:
        raise SystemExit("the page no longer pins a wasm hash the way this "
                         "mirror expects")
    page = page.replace(pin_match.group(0),
                        f'const PINNED_WASM_SHA256 = "{wasm_sha[:16]}";', 1)
    page += GATE_READER

    root = scratch / "a11y-gate0-root"
    build_mirror(PROJECT / "dist", root,
                 {page_relative: page.encode("utf-8")})
    return {
        "root": str(root),
        "profile": profile,
        "wasmSha256": wasm_sha,
        "pinBefore": pin_match.group(1),
        "pinAfter": wasm_sha[:16],
        "workerUrl": worker_after,
        "note": "The product page is MIRRORED, not modified: dist/ is never "
                "written and the shipped page still pins the shipped wasm. "
                "This run is diagnostic on both counts -- a core that is not "
                "the product's, and a page that was edited to reach it.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"),
                        default="chrome")
    parser.add_argument("--profile", default="a11y-gate0",
                        help="the profile the mirrored page is pointed at. "
                             "NOT the product's: the gate needs the artifact "
                             "linked against the core whose accessibility call "
                             "sites are compiled in")
    parser.add_argument("--open-url", default=None,
                        help="before measuring, open this URL through the "
                             "page's own file input instead of the fixture it "
                             "boots with. Off by default, so the gate path is "
                             "unchanged. Used to ask the tree-shape question "
                             "of a document that does not fit on one screen")
    parser.add_argument("--core-build",
                        default="../wasm-lite/build-a11y-gate0",
                        help="the core build G0-1 is judged against")
    parser.add_argument("--fixture", default="list-contexts.odt")
    parser.add_argument("--out", default=None)
    parser.add_argument("--check-build-only", action="store_true")
    parser.add_argument("--i-know-the-macro-is-set", action="store_true",
                        help="run anyway; the result is stamped UNMEASURABLE "
                             "and may not be quoted as a gate outcome")
    args = parser.parse_args()

    record: dict = {
        "schemaVersion": 1,
        "release": "a11y-gate-0",
        "question": "does LOK emit a focused paragraph on WASM?",
        "criteria": "handoff/a11y-gate-0/PREDICTION.md (written 2026-08-21, "
                    "before the patch and before any rebuild)",
        "patch": "handoff/a11y-gate-0/PATCH.md",
        "browser": args.browser,
        "profile": args.profile,
        "placements": [],
    }

    record["G0_1_buildProvidesAccessibility"] = build_provides_accessibility(
        args.core_build)
    if args.check_build_only:
        return finish(record, args)

    if not record["G0_1_buildProvidesAccessibility"]["provides"]:
        record["outcome"] = "REFUSED"
        record["why"] = (
            "G0-1 fails: this core build still sets "
            "ENABLE_WASM_STRIP_ACCESSIBILITY, so SwEditWin::CreateAccessible "
            "returns {} and there is nothing for the gate to measure. Apply "
            "handoff/a11y-gate-0/PATCH.md and rebuild core first. A run here "
            "would produce a number about the patch not having been applied.")
        if not args.i_know_the_macro_is_set:
            return finish(record, args)
        record["outcome"] = "UNMEASURABLE"

    scratch = Path(tempfile.mkdtemp(prefix="a11y-gate0-"))
    record["mirror"] = gate_mirror(scratch, args.profile)
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", record["mirror"]["root"]],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
    session = session_class("cold")
    try:
        navigate(session, base)
        state = wait_until(session, lambda s: s.get("state") == "ready", 180)
        record["booted"] = state.get("state")
        if state.get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = "the page never reached ready"
            return finish(record, args)

        if args.open_url:
            # MANAGES_DESCENDANTS is set on the document root, and an
            # implementation carrying that state is entitled to materialise
            # only the children it is currently rendering. Nine paragraphs on
            # one screen proves nothing about a document that scrolls, so this
            # opens a longer one through the product's own file input.
            record["openedUrl"] = args.open_url
            record["openDispatched"] = evaluate(
                session, OPEN_FILE.replace("ARG_URL", args.open_url)
                                  .replace("ARG_NAME", "a11y-long.odt"))
            state = wait_until(session, lambda s: s.get("state") == "ready", 180)
            record["stateAfterOpen"] = state.get("state")
            if state.get("state") != "ready":
                record["outcome"] = "NOT_ESTABLISHED"
                record["why"] = "the page never returned to ready after opening"
                return finish(record, args)
            time.sleep(2.0)

        # THREE paragraphs, and three is the point (PREDICTION G0-2).  One
        # reading cannot tell "a focused paragraph" from "an event that fires":
        # a callback reporting the same thing everywhere would pass a
        # single-placement check.  This is the positive control, and it is here
        # because three checks on 2026-08-21 passed or abstained for want of one.
        scan, bands = stable_bands(session)
        targets = [b for b in bands if (b["last"] - b["first"]) > 40][:3]
        record["bandsFound"] = len(bands)
        record["targetsUsed"] = len(targets)
        if len(targets) < 3:
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = ("fewer than three text bands to aim at, so the "
                             "readings cannot be shown to differ BY PARAGRAPH")
            return finish(record, args)

        for index, band in enumerate(targets):
            ink = evaluate(session, LINE_INK.replace(
                "ARG_Y", f"{band['centreFraction']:.5f}")) or {}
            clicks = caret_click_fractions(ink)
            place_caret_and_settle(session, POINT_AT, clicks["near"],
                                   f"{band['centreFraction']:.5f}")
            time.sleep(1.0)
            record["placements"].append({
                "index": index,
                "yFraction": round(band["centreFraction"], 5),
                "state": (wait_until(session, lambda s: True, 5) or {}).get("state"),
                "a11y": evaluate(session, READ_A11Y),
            })

        record["outcome"] = record.get("outcome") or "SEE_PLACEMENTS"
        record["howToJudge"] = (
            "PASS requires >= 2 DISTINCT paragraph identities across the three "
            "placements, each matching the paragraph actually targeted. A "
            "callback that fires with the same reading every time is an event, "
            "not a focused paragraph. FAIL = no callback, nothing "
            "paragraph-shaped, or one reading for all three. On FAIL: STOP "
            "(roadmap 3.3) -- do not start the shell half, and report the "
            "result to M3's positioning.")
        record["doNotConclude"] = (
            "If nothing comes back, 'core does not support it' is ONE "
            "hypothesis. Check first that the engine enabled it "
            "(`enabled`/`unavailable`) and that the worker FORWARDS the field "
            "-- an engine field nobody forwards does not exist, and that has "
            "bitten this tree twice in one afternoon. Do not name a layer "
            "without measuring it (040, 048, 062).")
    finally:
        try:
            if session is not None:
                session.close()
        finally:
            server.terminate()
    return finish(record, args)


def wait_until(session, predicate, timeout, poll=0.5):
    deadline = time.monotonic() + timeout
    state = evaluate(session, READ_STATE) or {}
    while time.monotonic() < deadline:
        if predicate(state):
            return state
        time.sleep(poll)
        state = evaluate(session, READ_STATE) or {}
    return state


def finish(record: dict, args) -> int:
    text = json.dumps(record, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
