#!/usr/bin/env python3
"""SPEC-M3-v28-last-line-fallback append 2: does v28's fallback (a selection and an html read on a path that never read
before) wedge or misjudge when a frame sits on or next to the empty last paragraph?  Findings 037/038 are that family.

check_v82_last_line_bullet.py (S4) is IMPORTED, not edited (S4's evidence binds it): five cells are added to its CELLS
and FIXTURES at run time, and its `one()` runs them.  Product: the generation-82 candidate as dist/ serves it (v28);
identity by tools/v82_f_products.py.

A run HOLDS when every clause of CLAUSES holds (spec append 2 item 3).  Either shape is fine, verified or
fallback-readback-refused: the question is "does it wedge or lie", not "can it verify".  A_FRAMES_HOLD: every cell,
both browsers, full count.  The cell in PRIMARY_COMPLEX never reaches the fallback (item 3a, found by the first
smoke): the primary read is already COMPLEX, finding 037's guard refuses with a typed reply, and COMPLEX_CLAUSES
apply; `--product before` runs it on generation 81 to show the path predates v28.

  check_v82_frame_last_line.py --out DIR [--cells a,b] [--browsers chrome,firefox] [--repetitions 3]
  check_v82_frame_last_line.py --product before --cells frame-char-last --out DIR     (the same shape on generation 81)
  check_v82_frame_last_line.py --mutation swallow-press --out DIR    (the positive control: every run must wedge)
  check_v82_frame_last_line.py --self-test REPORT                    (each clause mutated on a holding report is red)

--out must not exist.  Nothing under dist/ is written.  Not a timing measurement.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import traceback
import zipfile
import io

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_v82_last_line_bullet as s4  # noqa: E402

s3, pp, common, products, evaluate = s4.s3, s4.pp, s4.common, s4.products, s4.evaluate
BUILD = s4.REPO / "findings/evidence/v28-083/a-frames/build-01"
DOCS = {
    "frame-para-last": "bba5401ad8df9e07e1ac3bac69ad33a390044c92081e3e5c64a53b8c834bf939",
    "frame-char-last": "abbfaa8711161096000cd613e46c212d2309aeb3435d72b0e30329fc7ab1768f",
    "textbox-para-last": "de533cc3dd209b036ab20a049364152694c65e8b61a938b1d4079b0e77cd2f46",
    "prev-aschar-image": "3cccebb3a808244948bee6cd76120eead2f08abd00ca6b354dfb7b0cad7bc63a",
    "prev-note-frame": "2140fb16b604603c1180022596fce466e0ab74942aac30b3dde758e70ae7e3fe",
}
PRIMARY_COMPLEX = ("frame-char-last",)
BULLET_ACTION = "set-list-unordered"
FRAME = b"<draw:frame"
# The bullet request stopped in front of the worker: from the page this is an engine that never answers.
SWALLOW = """<script>
(() => { const post = window.Worker.prototype.postMessage;
  window.Worker.prototype.postMessage = function (m, ...rest) {
    if (m?.kind === 'request' && m?.payload?.action === 'set-list-unordered') { window.__s3.requests.push({operation: m.operation, requestId: m.requestId, payload: {action: m.payload.action}}); return; }
    return post.call(this, m, ...rest); };
})();
</script>"""


def frames(raw: bytes) -> int:
    return zipfile.ZipFile(io.BytesIO(raw)).read("content.xml").count(FRAME)


def fixture(cell: str) -> tuple[bytes, dict]:
    raw = (BUILD / f"{cell}.odt").read_bytes()
    if hashlib.sha256(raw).hexdigest() != DOCS[cell]:
        raise SystemExit(f"fixture {cell} changed")
    return raw, {"frames": frames(raw), **s4.odt_reading(raw)}


def run_one(session, browser, base, cell, raw):
    out = s4.one(session, browser, base, cell, raw, BULLET_ACTION)
    try:
        if out.get("savedSettled"):
            out["savedFrames"] = frames(base64.b64decode(evaluate(session, s3.BLOB)))
    except Exception as error:  # noqa: BLE001 -- recorded, the clause reads it as not holding
        out["savedFramesError"] = repr(error)
    return out


def rest_of_document(run, want):
    """Everything but the marker: paragraph for paragraph, text without the marker, tag, table; a list only on the marker
    paragraph (and on a text box inside it, which the reader counts as in that list)."""
    got, base = s4.ps(run, "saved"), want["paragraphs"]
    if len(got) != len(base):
        return False
    marked = [i for i, p in enumerate(got) if s4.MARKER in p["text"]]
    if len(marked) != 1:
        return False
    for i, (a, b) in enumerate(zip(got, base)):
        if a["text"].replace(s4.MARKER, "") != b["text"] or a["tag"] != b["tag"] or a.get("inTable") != b.get("inTable"):
            return False
        if a["inList"] != b["inList"] and i != marked[0] and "In frame" not in a["text"]:
            return False
    return True


def marker_paragraph(run):
    found = [p for p in s4.ps(run, "saved") if s4.MARKER in p["text"]]
    return found[0] if len(found) == 1 else None


def truthful(run):
    row = s4.press_row(run) or {}
    if row.get("completion") != "verified-format-readback":
        return True
    p = marker_paragraph(run)
    return bool(p) and p["inList"] and p["listLevel1"] == s4.BULLET


def _press(run):
    return run.get("press") or {}


CLAUSES = [
    ("a.replied", lambda r, w: bool(r.get("pressSettled")) and (s4.press_row(r) or {}).get("replied") is True,
     lambda r: s4.press_row(r).__setitem__("replied", False)),
    ("b.ready", lambda r, w: _press(r).get("pill") == "ready", lambda r: _press(r).__setitem__("pill", "restart-required")),
    ("c.typed", lambda r, w: s4.typed_ok(r), lambda r: r["typedRows"].clear()),
    ("d.saved", lambda r, w: bool(r.get("savedSettled")) and rest_of_document(r, w),
     lambda r: s4.ps(r, "saved")[0].__setitem__("text", "changed")),
    ("e.frames", lambda r, w: r.get("savedFrames") == w["frames"], lambda r: r.__setitem__("savedFrames", 0)),
    ("f.fallback", lambda r, w: s4.fallback(r).get("ran") is True and s4.fallback(r).get("restoreConfirmed") is True,
     lambda r: s4.fallback(r).__setitem__("restoreConfirmed", False)),
    ("g.truthful", lambda r, w: truthful(r), lambda r: (s4.press_row(r).__setitem__("completion", "verified-format-readback"),
                                                        marker_paragraph(r).__setitem__("inList", False))),
]
WEDGE_CLAUSES = ("a.replied", "b.ready", "c.typed")
COMPLEX_CLAUSES = [
    ("a.replied", CLAUSES[0][1], CLAUSES[0][2]),
    ("h.typed-refusal", lambda r, w: (s4.press_row(r) or {}).get("ok") is False
     and (s4.press_row(r) or {}).get("code") == "MUTATION_OUTCOME_UNKNOWN"
     and s4.barrier(r).get("failureShape") == "selection-type-not-readable",
     lambda r: s4.barrier(r).__setitem__("failureShape", "postcondition-not-met")),
    ("h.no-fallback", lambda r, w: s4.fallback(r).get("ran") is not True, lambda r: s4.barrier(r).__setitem__("fallback", {"ran": True})),
    ("h.not-wedged", lambda r, w: _press(r).get("pill") in ("ready", "recoverable-error"),
     lambda r: _press(r).__setitem__("pill", "restart-required")),
]


def clauses_for(cell):
    return COMPLEX_CLAUSES if cell in PRIMARY_COMPLEX else CLAUSES


def judge(run, want):
    if run.get("fatal"):
        return "NE", {"fatal": run["fatal"].strip().splitlines()[-1]}
    results = {}
    for cid, holds, _ in clauses_for(run["cell"]):
        try:
            results[cid] = bool(holds(run, want))
        except Exception as error:  # noqa: BLE001 -- unreadable is not holding
            results[cid] = False
            results[cid + ":error"] = f"{type(error).__name__}: {error}"
    return ("HOLDS" if all(v for k, v in results.items() if ":" not in k) else "RED"), results


def verdict(report):
    config = report["config"]
    per = len(config["browsers"]) * config["repetitions"]
    problems = [] if report["products"].get(config["product"], {}).get("ok") else ["identity failed"]
    for r in report["runs"]:
        r["outcome"], r["clauses"] = judge(r, report["fixtures"][r["cell"]])
        r["failedClauses"] = sorted(k for k, v in r["clauses"].items() if v is False)
    if config.get("mutation"):
        wedged = [r for r in report["runs"] if any(c in r["failedClauses"] for c in WEDGE_CLAUSES)]
        if not (len(report["runs"]) == per and len(wedged) == per):
            problems.append(f"positive control: {len(wedged)}/{per} runs read as a wedge")
        return ("A_FRAMES_CONTROL_RED_AS_WANTED" if not problems else "A_FRAMES_CONTROL_BLIND"), problems
    for cell in config["cells"]:
        runs = [r for r in report["runs"] if r["cell"] == cell]
        held = sum(r["outcome"] == "HOLDS" for r in runs)
        if not (len(runs) == per and held == per):
            problems.append(f"{cell}: {held}/{per} hold; red clauses {sorted({c for r in runs for c in r['failedClauses']})}")
    complete = sorted(config["cells"]) == sorted(DOCS) and config["product"] == "after"
    if problems:
        return "A_FRAMES_RED", problems
    return ("A_FRAMES_HOLD" if complete else "A_FRAMES_SUBSET_HOLDS"), problems


def self_test(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    base, _ = verdict(copy.deepcopy(report))
    if base not in ("A_FRAMES_HOLD", "A_FRAMES_SUBSET_HOLDS"):
        print(f"self-test needs a holding report; this one is {base}", file=sys.stderr)
        return 2
    results = {}
    for cell in report["config"]["cells"]:
        index = next(i for i, r in enumerate(report["runs"]) if r["cell"] == cell)
        for cid, _, mutate in clauses_for(cell):
            mutated = copy.deepcopy(report)
            mutate(mutated["runs"][index])
            results[f"{cell}/{cid}"] = verdict(mutated)[0]
    for name, mutate in {"one-run-missing": lambda r: r["runs"].pop(0),
                         "identity-failed": lambda r: r["products"][r["config"]["product"]].__setitem__("ok", False),
                         "one-run-fatal": lambda r: r["runs"][-1].__setitem__("fatal", "Traceback\nRuntimeError: x")}.items():
        mutated = copy.deepcopy(report)
        mutate(mutated)
        results[name] = verdict(mutated)[0]
    red = all(v == "A_FRAMES_RED" for v in results.values())
    print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "mutations": len(results), "results": results}, indent=1))
    return 0 if red else 1


def summary(run):
    row = s4.press_row(run) or {}
    barrier, fb = row.get("formatBarrier") or {}, s4.fallback(run)
    return [_press(run).get("pill"), _press(run).get("latency"), row.get("ok"), row.get("completion"), barrier.get("failureShape"),
            {k: fb.get(k) for k in ("selectionType", "blockCount", "lastListTag", "lastBlockTag", "refusal", "restoreConfirmed")},
            run.get("savedFrames"), (_press(run).get("toast") or "")[:24]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", type=Path, metavar="REPORT")
    parser.add_argument("--cells", default=",".join(DOCS))
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--mutation", choices=["swallow-press"])
    parser.add_argument("--product", choices=["after", "before"], default="after")
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test)
    if not args.out:
        parser.error("--out is required")
    cells = ["frame-para-last"] if args.mutation else [c for c in args.cells.split(",") if c]
    repetitions = 1 if args.mutation else args.repetitions
    raw, wanted = {}, {}
    for cell in cells:
        raw[cell], wanted[cell] = fixture(cell)
        s4.FIXTURES[cell] = (BUILD / f"{cell}.odt", DOCS[cell])
        s4.CELLS[cell] = (cell, 0, BULLET_ACTION, True, None)
    args.out.mkdir(parents=True, exist_ok=False)
    config = {"cells": cells, "browsers": [x for x in args.browsers.split(",") if x], "repetitions": repetitions,
              "mutation": args.mutation, "product": args.product}
    report = {"argv": sys.argv, "tool": "check_v82_frame_last_line", "config": config, "marker": s4.MARKER, "click": s4.CLICK,
              "fixtures": wanted, "products": {}, "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="a-frames-", dir=s4.PROJECT / "build"))
    try:
        with common.browser_lock("check_v82_frame_last_line"):
            report["preRun"] = common.pre_run_checks()
            if report["preRun"]["refuse"]:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            mirror = scratch / args.product
            snippets = [s3.OBSERVER] + ([SWALLOW] if args.mutation else [])
            pp.build_mirror(common.DIST, mirror, products.overrides(args.product, snippets))
            report["products"][args.product] = products.identity(args.product, mirror)
            if report["products"][args.product]["ok"]:
                with common.served(mirror) as base:
                    for cell in cells:
                        for browser in config["browsers"]:
                            for n in range(1, repetitions + 1):
                                run, session = {"cell": cell, "product": args.product, "browser": browser, "repetition": n}, None
                                try:
                                    session = common.open_browser(browser)
                                    run["browserVersion"] = getattr(session, "version", None)
                                    run.update(run_one(session, browser, base, cell, raw[cell]))
                                except Exception:  # noqa: BLE001 -- recorded
                                    run["fatal"] = traceback.format_exc()
                                finally:
                                    if session is not None:
                                        run["cleanup"] = common.close_browser(session)
                                report["runs"].append(run)
                                print(cell, browser, n, *summary(run), (run.get("fatal") or "").strip().splitlines()[-1:] or "",
                                      file=sys.stderr, flush=True)
            else:
                print("identity FAILED, not run:", report["products"][args.product]["checks"], file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report["verdict"], report["problems"] = verdict(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], report["problems"], file=sys.stderr)
    return 0 if report["verdict"] in ("A_FRAMES_HOLD", "A_FRAMES_SUBSET_HOLDS", "A_FRAMES_CONTROL_RED_AS_WANTED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
