#!/usr/bin/env python3
"""Round 3 of the native Markdown-paste measurements: the two native pre-runs the v21 shakedown
arms require before their WASM runs (findings/evidence/link-batch-v21/shakedown/ARMS-item2.md §9).

  DM-5   the five M0-PASS items with no native reference -- C1, X09, X10, X11, X12 -- pasted as
         text/markdown;charset=utf-8 at round 1's P1 (the empty template, document start), 3 runs each,
         with round 2's probe binary (md_paste_probe2.cpp, rebuilt byte-identical: sha256 425a8b01...),
         so the instrument is the one that produced every other M1 reference (round 2's T3-P1 arms).
  DM-17 C  clicks on the image and the frame of the M10 fixture (wasm_sdk_probe/tools/v21_item2_fixtures.py
         m10_selectables()), recording what Writer sends while the click is placed (TEXT_SELECTION with or
         without rectangles, GRAPHIC_SELECTION, the cursor), getSelectionType() and
         getSelectionTypeAndText() -- the call the WASM engine's readSelection() makes -- then the paste
         of M2 and its undo walk, as round 2 did. Probe: md_paste_probe3.cpp (round 2's plus those
         records). Controls: a click inside the frame's text and a caret placed by keys in body text.

Usage: run_arms3.py PROBE2_BINARY PROBE3_BINARY SCRATCH_DIR OUT_DIR [--runs=N] [ARM_ID_PREFIX ...]

Everything about a process is round 2's (`run_arms2.run_one`, imported, not copied): its own profile
and document copy, `env -i` with LANG=zh_TW.UTF-8 and SAL_USE_VCLPLUGIN=svp, nice, timeout, the
probe's 20 s watchdog, waiting for any other LOK probe, the listener on 18765 and the closer on 18768.
This runner only declares the arms, points corpus_path() at round 3's corpus, and adds the probe-3
records to each summary.json under "round3".
"""

import hashlib
import importlib.util
import json
import os
import sys
import threading
import time
import http.server

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROUND2_TOOL = os.path.abspath(os.path.join(HERE, "..", "..", "round-2", "tool"))
ROUND1_TOOL = os.path.abspath(os.path.join(HERE, "..", "..", "tool"))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 7))
sys.path.insert(0, ROUND2_TOOL)
import run_arms2 as r2  # noqa: E402  (round 2's runner; read-only use)

MD = r2.MD
CH, DOWN, END = r2.CH, r2.DOWN, r2.END

CORPUS = os.path.join(HERE, "corpus")
INPUTS = os.path.join(HERE, "inputs")
EXPECTED = os.path.join(REPO, "wasm_sdk_probe/tests/markdown_paste_expected.json")
FIXTURES_TOOL = os.path.join(REPO, "wasm_sdk_probe/tools/v21_item2_fixtures.py")

# DM-5: the five PASS items without a native reference, by their fixture path.
DM5_ITEMS = ["round-1/C1.md", "m0/X09-angle-generic-inline-code.md", "m0/X10-angle-generic-fenced.md",
             "m0/X11-task-list.md", "m0/X12-entities.md"]

# DM-17 C click points, twips, from the fixture's declared geometry (v21_item2_fixtures.M10_GEOMETRY):
# page 1 at (284, 284), 2 cm margins -> body text from (1418, 1418); the 2 cm image (1134 twips) alone on
# line 1; the frame at (3 cm, 10 cm) = (1985, 5953), 6 cm x 3 cm, border 0.06 cm (34), padding 0.5 cm (283).
# Declared, not measured: what the runs record is what Writer did with a click at these points.
CLICKS = {
    "image-centre": "a1985:1985",
    "frame-border": "a2002:6803",       # the left border's middle line
    "frame-padding": "a2161:6803",      # 0.25 cm inside the border, in the padding
    "frame-text": "a2600:6408",         # inside "M10-FRAME text"
}


def m10_path():
    return os.path.join(INPUTS, "m10-selectables.odt")


POSITIONS = {
    # Round 1's P1, as round 2 declared it for T3.
    "P1": r2.POS["P1"],
    "SELIMG": (m10_path(), "-", CLICKS["image-centre"], "sel", None, "-", None),
    "SELFRB": (m10_path(), "-", CLICKS["frame-border"], "sel", None, "-", None),
    "SELFRP": (m10_path(), "-", CLICKS["frame-padding"], "sel", None, "-", None),
    "SELFRT": (m10_path(), "-", CLICKS["frame-text"], "sel", None, "-", None),
    # Control: a caret placed by keys at the end of the body paragraph (no click): collapsed.
    "SELKEY": (m10_path(), "-", "k%d,k%d,k%d" % (CH, DOWN, END), "sel", "", "-", None),
}


def arms():
    out = []

    def add(arm_id, pos, corpus, probe, runs=3, note=""):
        out.append({"id": arm_id, "position": pos, "corpus": corpus, "mime": MD, "lang": r2.ZH,
                    "runs": runs, "note": note, "probe": probe})

    for item in DM5_ITEMS:
        name = os.path.basename(item)[:-3]
        add("R3-P1-" + name, "P1", name, "probe2", note="DM-5: the native reference for an M0-PASS item")
    add("R3-SEL-image-M2", "SELIMG", "M2", "probe3", note="DM-17 C: click on the image's centre")
    add("R3-SEL-frameborder-M2", "SELFRB", "M2", "probe3", note="DM-17 C: click on the frame's left border")
    add("R3-SEL-framepadding-M2", "SELFRP", "M2", "probe3", note="DM-17 C: click in the frame's padding")
    add("R3-SEL-frametext-M2", "SELFRT", "M2", "probe3", note="control: click in the frame's text")
    add("R3-SEL-keys-M2", "SELKEY", "M2", "probe3", note="control: caret by keys in body text")
    return out


def corpus_path(name):
    for base in (CORPUS, os.path.join(ROUND1_TOOL, "corpus")):
        path = os.path.join(base, name + ".md")
        if os.path.exists(path):
            return path
    raise SystemExit("no corpus item " + name)


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def verify_inputs():
    """The corpus copies equal the M0 fixture's bytes; the M10 fixture equals the generator's pin."""
    with open(EXPECTED) as handle:
        items = {it["path"]: it for it in json.load(handle)["items"]}
    problems = []
    for item in DM5_ITEMS:
        path = os.path.join(CORPUS, os.path.basename(item))
        if not os.path.exists(path) or sha(path) != items[item]["sha256"]:
            problems.append("corpus %s does not match markdown_paste_expected.json" % item)
    spec = importlib.util.spec_from_file_location("v21_item2_fixtures", FIXTURES_TOOL)
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    if not os.path.exists(m10_path()) or sha(m10_path()) != fixtures.PINNED["m10-selectables.odt"]:
        problems.append("inputs/m10-selectables.odt does not match v21_item2_fixtures.PINNED")
    if problems:
        raise SystemExit("; ".join(problems))


def augment(out_dir, arm, k):
    """Add probe 3's place records to summary.json (probe 2 runs have none)."""
    run_dir = os.path.join(out_dir, arm["id"], "run%d" % k)
    path = os.path.join(run_dir, "summary.json")
    with open(path) as handle:
        summary = json.load(handle)
    if "round3" in summary:
        return
    records = []
    with open(os.path.join(run_dir, "stdout.jsonl"), encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                records.append(json.loads(line))
            except ValueError:
                pass
    by = {}
    for r in records:
        by.setdefault(r.get("probe"), []).append(r)
    extra = {"probe": arm["probe"]}
    if "place-callbacks" in by:
        cbs = by["place-callbacks"][0]["list"]
        counts = {}
        for c in cbs:
            counts[c["name"]] = counts.get(c["name"], 0) + 1
        extra["placeCallbackCounts"] = counts
        extra["placeTextSelections"] = [c["payload"] for c in cbs if c["type"] == 2]
        extra["placeGraphicSelections"] = [c["payload"] for c in cbs if c["type"] == 6]
        extra["placeCursors"] = [c["payload"] for c in cbs if c["type"] == 1]
        extra["placeCallbackNamesInOrder"] = [c["name"] for c in cbs][:60]
    if "position" in by:
        p = by["position"][0]
        for key in ("selectionTypeAndTextAtPlace", "selectionTypeAndTextAtPaste", "lastTextSelection",
                    "lastGraphicSelection"):
            if key in p:
                extra[key] = p[key]
    summary["round3"] = extra
    with open(path, "w") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=1)


def main(argv):
    probe2, probe3, scratch, out_dir = argv[1:5]
    runs_override = [int(a.split("=", 1)[1]) for a in argv[5:] if a.startswith("--runs=")]
    prefixes = [a for a in argv[5:] if not a.startswith("--runs=")]
    verify_inputs()
    r2.POS.update(POSITIONS)
    r2.corpus_path = corpus_path
    probes = {"probe2": probe2, "probe3": probe3}
    os.makedirs(out_dir, exist_ok=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", r2.LISTENER_PORT), r2.Listener)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    r2.Closer(r2.CLOSER_PORT)
    with open(os.path.join(out_dir, "runner.log"), "a") as log:
        log.write("=== %s start, prefixes=%s, probe2 sha256 %s, probe3 sha256 %s\n" % (
            time.strftime("%Y-%m-%dT%H:%M:%S%z"), prefixes, sha(probe2), sha(probe3)))
        for arm in arms():
            if prefixes and not any(arm["id"].startswith(p) for p in prefixes):
                continue
            for k in range(1, (runs_override[0] if runs_override else arm["runs"]) + 1):
                r2.run_one(probes[arm["probe"]], scratch, out_dir, arm, k, log)
                augment(out_dir, arm, k)
        log.write("=== %s end\n" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
