#!/usr/bin/env python3
"""S3 (SPEC-M3-v27-finding-176 7.3): finding 046's cell on the user's path -- a bullet on an empty line that has a
paragraph after it is verified, not sent to review.

The procedure, every input real (tools/v21_input.py: Chrome CDP Input.*, Firefox WebDriver actions):
  open findings/evidence/v27-176/fixture-two-plain/build-01/two-plain.odt ("Plain first" / "E1-EMPTY-AFTER", the
  native core's one save of finding 176's two-plain.fodt; sha pinned below) through the page's file input; click past
  the end of the first line (LINE_END, PL-1's measured point: #paper includes LOK's 284-twip border); press Enter;
  click the toolbar bullet; type the marker; the product's save; read the saved ODT.  Then Ctrl+Z twice (the typing,
  then `Number On/Off`) and save again.  PL-1 (findings/evidence/v27-176/pl1/) ran the same recipe up to the press.

Products (tools/v81_f_products.py, identity checked file by file): before = generation 80 (profile v26), after =
the generation-81 candidate as dist/ serves it (profile v27).  Observer in the HTML: every Worker request and reply,
the save Blobs, and every console.warn (the page's `[review]` line).

An `after` run PASSes when every clause of AFTER_CLAUSES holds (spec 7.3 S3):
  after the press: pill ready; #toast empty; no `[review]` console line since the press; the strip is
  `• 項目符號 N ms`; the bullet's reply row is ok, completion `verified-format-readback`, formatBarrier.route
  `collapsed`, formatBarrier.readbackBlockCount 2 (formatBarrier.undo recorded, not judged); the saved ODT has the
  marker's paragraph in a bullet list, between `Plain first` and `E1-EMPTY-AFTER`, both plain paragraphs outside any
  list; after two Ctrl+Z (both replies ok) the second save is three paragraphs, the middle one empty and in no list,
  the neighbours unchanged.
A `before` run is red FOR 176 when the bullet's reply is 046's shape (error, failureShape multi-block-readback) and
every clause of BEFORE_RED holds: the toast says 「不只一個段落」, the strip is not `• 項目符號 N ms`, the saved
marker is in a list anyway.  Red for any other reason fails the verdict.

Mutations (spec 7.3, ruling 3 Q6.5; review item 4), each its own run, each must make every run FAIL:
  --mutation press-list-none     after, pressing 移除清單 instead of the bullet (the save has no list)
  --mutation hide-review-toast   the before page with the review toast hidden (ruling 3's B case)
  --mutation cosmetic-review     the before page with no toast, no [review] line and `N ms` in the strip:
                                 indistinguishable on the page; only the worker reply row can be red

  check_v81_blank_line_bullet.py --out DIR [--browsers chrome,firefox] [--repetitions 3] [--mutation NAME]
  check_v81_blank_line_bullet.py --self-test REPORT    (every clause's mutation, applied to a holding report, red)

Verdicts: S3_HOLDS (both identities, every after run PASS, every before run red for 176, full count);
S3_MUTATION_CAUGHT (a mutation report: every run FAIL, none PASS or fatal).  --out must not exist.  Nothing under
dist/ is written.  Not a timing measurement: no desk gate.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
sys.path.insert(0, str(PROJECT / "tools"))
import run_e2_c_product_path as pp  # noqa: E402
import v21_input as real  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v81_f_products as products  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

FIXTURE = REPO / "findings/evidence/v27-176/fixture-two-plain/build-01/two-plain.odt"
FIXTURE_SHA256 = "56bc01b03b094b8da784fa98419873009fb887c8bf62953d0574f71c18a497a9"
FIXTURE_RECEIPT = REPO / "findings/evidence/v27-176/fixture-two-plain/build-01/receipt.json"
LINE_END = (0.80, 0.0894)
MARKER = "mks3q"
FIRST, NEXT = "Plain first", "E1-EMPTY-AFTER"
STRIP = re.compile(r"• 項目符號 \d+ ms")
MULTI_SENTENCE = "不只一個段落"
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
MUTATIONS = {"press-list-none": ("after", "set-list-none"), "hide-review-toast": ("hide-review-toast", "set-list-unordered"),
             "cosmetic-review": ("cosmetic-review", "set-list-unordered")}
OBSERVER = """<script>
(() => {
  const rec = window.__s3 = {requests: [], responses: [], blobs: [], workers: 0, warns: []};
  const snap = v => { try { return JSON.parse(JSON.stringify(v, (k, x) =>
    (x instanceof ArrayBuffer || ArrayBuffer.isView(x)) ? {bytes: x.byteLength} : x)); }
    catch (e) { return {unserialisable: String(e)}; } };
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options); rec.workers += 1;
      this.addEventListener('message', ev => { if (ev.data?.kind === 'response') rec.responses.push(snap(ev.data)); }); }
    postMessage(m, ...rest) { if (m?.kind === 'request') rec.requests.push(snap(m)); return super.postMessage(m, ...rest); }
  };
  const warn = console.warn.bind(console);
  console.warn = (...args) => { try { rec.warns.push(args.map(a => String(a)).join(' ').slice(0, 300)); } catch (e) {} return warn(...args); };
  const create = URL.createObjectURL.bind(URL);
  URL.createObjectURL = blob => { if (blob instanceof Blob) rec.blobs.push(blob); return create(blob); };
  const click = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () { if (this.hasAttribute('download')) return; return click.call(this); };
})();
</script>"""
PAGE = """(() => ({pill: document.querySelector('#state-pill')?.dataset.state,
  latency: document.querySelector('#s-latency')?.textContent,
  toast: document.querySelector('#toast')?.textContent,
  toastBad: document.querySelector('#toast')?.classList.contains('bad') ?? null,
  revision: document.querySelector('#s-revision')?.textContent,
  notice: {show: document.querySelector('#notice')?.dataset.show ?? null,
           text: document.querySelector('#notice-text')?.textContent ?? null},
  requests: window.__s3.requests.length, responses: window.__s3.responses.length,
  workers: window.__s3.workers, blobs: window.__s3.blobs.length, warns: window.__s3.warns.length}))()"""
BLOB = """(async () => { const b = window.__s3.blobs.at(-1); const u = new Uint8Array(await b.arrayBuffer());
  let s = ''; for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode(...u.subarray(i, i + 8192)); return btoa(s); })()"""
CLEAR_LATENCY = "(() => { document.querySelector('#s-latency').textContent = ''; return true; })()"
BARRIER_KEYS = ("route", "readbackBlockCount", "itemCount", "failureShape", "dispatched", "undo")


def wait(session, predicate, limit):
    until, state = time.monotonic() + limit, None
    while time.monotonic() < until:
        state = evaluate(session, PAGE)
        if state and predicate(state):
            return state, True
        time.sleep(0.2)
    return state, False


def rows(session, start):
    record = evaluate(session, "window.__s3")
    replies = {r.get("requestId"): r for r in record["responses"]}
    out = []
    for q in record["requests"][start:]:
        payload = q.get("payload") or {}
        reply = replies.get(q.get("requestId")) or {}
        error, result = reply.get("error") or {}, reply.get("result") or {}
        barrier = result.get("formatBarrier") or error.get("formatBarrier") or (error.get("details") or {}).get("formatBarrier")
        out.append({"operation": q.get("operation"), "action": payload.get("action"), "replied": bool(reply),
                    "ok": reply.get("ok"), "code": error.get("code"), "recovery": error.get("recovery"),
                    "completion": result.get("completion"),
                    "formatBarrier": {k: barrier.get(k) for k in BARRIER_KEYS} if barrier else None,
                    "revision": [result.get("beforeRevision"), result.get("revision")]})
    return out


def odt_reading(raw: bytes) -> dict:
    """The body paragraphs in order: text, tag, in a list, and whether that list's level 1 is a bullet."""
    package = zipfile.ZipFile(io.BytesIO(raw))
    root = ET.fromstring(package.read("content.xml"))
    styles = ET.fromstring(package.read("styles.xml"))
    parent = {child: node for node in root.iter() for child in node}
    list_styles = {}
    for tree in (styles, root):
        for ls in tree.iter(f"{{{TEXT_NS}}}list-style"):
            level1 = next((c for c in ls if c.get(f"{{{TEXT_NS}}}level") == "1"), None)
            list_styles[ls.get(f"{{{STYLE_NS}}}name")] = None if level1 is None else level1.tag.split("}")[-1]
    body = next(root.iter("{urn:oasis:names:tc:opendocument:xmlns:office:1.0}text"))
    paragraphs = []
    for node in body.iter():
        if node.tag not in (f"{{{TEXT_NS}}}p", f"{{{TEXT_NS}}}h"):
            continue
        lists, up = [], parent.get(node)
        while up is not None and up is not body:
            if up.tag == f"{{{TEXT_NS}}}list":
                lists.append(up)
            up = parent.get(up)
        style = lists[-1].get(f"{{{TEXT_NS}}}style-name") if lists else None
        paragraphs.append({"text": "".join(node.itertext()), "tag": node.tag.split("}")[-1], "inList": bool(lists),
                           "listStyle": style, "listLevel1": list_styles.get(style) if style else None})
    return {"sha256": hashlib.sha256(raw).hexdigest(), "paragraphs": paragraphs}


def save(session, out, key):
    blobs = evaluate(session, PAGE)["blobs"]
    evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
    _, out[key + "Settled"] = wait(session, lambda s: s["blobs"] > blobs, 60)
    if out[key + "Settled"]:
        out[key] = odt_reading(base64.b64decode(evaluate(session, BLOB)))


def one(session, browser, base, raw_doc, action):
    navigate(session, base)
    _, ok = wait(session, lambda s: s["pill"] == "ready", 240)
    if not ok:
        return {"fatal": "page not ready"}
    workers = evaluate(session, PAGE)["workers"]
    opened = evaluate(session, pp.OPEN_BYTES.replace("ARG_B64", base64.b64encode(raw_doc).decode())
                      .replace("ARG_NAME", FIXTURE.name))
    state, ok = wait(session, lambda s: s["workers"] > workers and s["pill"] == "ready", 120)
    if not ok:
        return {"fatal": f"document not opened ({opened})", "page": state}
    time.sleep(1.5)
    out = {"action": action, "opened": evaluate(session, PAGE)}
    evaluate(session, real.SCROLL_TO_FRACTION.replace("ARG_F", repr(LINE_END[1])))
    time.sleep(0.25)
    rect = evaluate(session, real.PAPER_RECT)
    point = (rect["left"] + rect["width"] * LINE_END[0], rect["top"] + rect["height"] * LINE_END[1])
    out["clickAt"] = {"fraction": LINE_END, "viewport": point}
    real.click(session, browser, *point)
    _, out["caretPlaced"] = wait(session, lambda s: "定位游標" in (s["latency"] or ""), 30)
    time.sleep(0.8)
    before = evaluate(session, PAGE)
    real.key(session, browser, "Enter")
    _, out["enterSettled"] = wait(session, lambda s: s["requests"] > before["requests"]
                                  and s["responses"] >= s["requests"] and s["revision"] != before["revision"], 30)
    time.sleep(0.8)
    evaluate(session, pp.CLEAR_TOAST)
    start = evaluate(session, PAGE)
    label = evaluate(session, pp.BUTTON_LABEL.replace("ARG_ACTION", action))
    box = evaluate(session, pp.BUTTON_BOX.replace("ARG_SELECTOR", f'#toolbar button[data-action="{action}"]'))
    if not box or not label:
        out["fatal"] = f"no {action} button"
        return out
    real.click(session, browser, box["x"], box["y"])
    _, out["pressSettled"] = wait(session, lambda s: s["pill"] in ("recoverable-error", "restart-required")
                                  or label in (s["latency"] or ""), 60)
    time.sleep(1.5)
    out["press"] = evaluate(session, PAGE)
    out["pressRows"] = rows(session, start["requests"])
    out["pressWarns"] = evaluate(session, "window.__s3.warns")[start["warns"]:]
    typed_from = evaluate(session, PAGE)
    for ch in MARKER:
        real.key(session, browser, ch)
        time.sleep(0.12)
    _, out["typedSettled"] = wait(session, lambda s: s["requests"] > typed_from["requests"]
                                  and s["responses"] >= s["requests"] and s["pill"] == "ready"
                                  and s["revision"] != typed_from["revision"], 30)
    time.sleep(1.5)
    out["typed"] = evaluate(session, PAGE)
    out["typedRows"] = rows(session, typed_from["requests"])
    save(session, out, "saved")
    out["undo"] = []
    for _ in range(2):
        evaluate(session, CLEAR_LATENCY)
        mark = evaluate(session, PAGE)
        real.key(session, browser, "z", ("ctrl",))
        state, settled = wait(session, lambda s: s["requests"] > mark["requests"] and s["responses"] >= s["requests"]
                              and "復原" in (s["latency"] or ""), 30)
        time.sleep(1.0)
        out["undo"].append({"settled": settled, "page": evaluate(session, PAGE), "rows": rows(session, mark["requests"])})
    save(session, out, "savedAfterUndo")
    return out


# ------------------------------------------------------------------ judging

def press_row(run):
    return next((r for r in run.get("pressRows") or [] if r.get("action") == run.get("action")), None)


def barrier(run):
    return (press_row(run) or {}).get("formatBarrier") or {}


def paragraphs(run, key):
    return (run.get(key) or {}).get("paragraphs") or []


def plain(p, text):
    return bool(p) and p["text"] == text and p["tag"] == "p" and not p["inList"]


def marker_index(run):
    found = [i for i, p in enumerate(paragraphs(run, "saved")) if MARKER in p["text"]]
    return found[0] if len(found) == 1 else None


def saved_marker_in_bullet_list(run):
    i = marker_index(run)
    return i is not None and paragraphs(run, "saved")[i]["inList"] and \
        paragraphs(run, "saved")[i]["listLevel1"] == "list-level-style-bullet"


def saved_neighbours(run):
    ps, i = paragraphs(run, "saved"), marker_index(run)
    return i is not None and len(ps) == 3 and i == 1 and plain(ps[0], FIRST) and plain(ps[2], NEXT)


def undo_three_paragraphs(run):
    ps = paragraphs(run, "savedAfterUndo")
    return len(ps) == 3 and plain(ps[0], FIRST) and plain(ps[2], NEXT) and ps[1]["text"] == "" and not ps[1]["inList"]


def undo_replies_ok(run):
    undo = run.get("undo") or []
    return len(undo) == 2 and all(u["settled"] and any(r["operation"] == "undo" and r["ok"] is True for r in u["rows"])
                                  for u in undo)


def _press(run):
    return run.get("press") or {}


def _set(path_fn, key, value):
    def mutate(run):
        path_fn(run)[key] = value
    return mutate


def _drop_marker_from_list(run):
    i = marker_index(run)
    paragraphs(run, "saved")[i]["inList"] = False


def _swap_neighbour(run):
    paragraphs(run, "saved")[0]["text"] = "Plain first changed"


def _undo_left_list(run):
    paragraphs(run, "savedAfterUndo")[1]["inList"] = True


def _undo_refused(run):
    for r in run["undo"][1]["rows"]:
        if r["operation"] == "undo":
            r["ok"] = False


# (id, predicate over one after run, mutation of a run that holds it)
AFTER_CLAUSES = [
    ("A.ready", lambda r: _press(r).get("pill") == "ready", _set(_press, "pill", "recoverable-error")),
    ("A.no-toast", lambda r: (_press(r).get("toast") or "").strip() == "",
     _set(_press, "toast", "• 項目符號：動作已送出，但這一格的檢查涵蓋了不只一個段落")),
    ("A.no-review-line", lambda r: not any(w.startswith("[review]") for w in r.get("pressWarns") or []),
     lambda r: r["pressWarns"].append("[review] • 項目符號: MUTATION_OUTCOME_UNKNOWN")),
    ("A.strip", lambda r: STRIP.fullmatch(_press(r).get("latency") or "") is not None,
     _set(_press, "latency", "• 項目符號 失敗")),
    ("A.reply-ok", lambda r: (press_row(r) or {}).get("ok") is True, lambda r: press_row(r).__setitem__("ok", False)),
    ("A.completion", lambda r: (press_row(r) or {}).get("completion") == "verified-format-readback",
     lambda r: press_row(r).__setitem__("completion", None)),
    ("A.route", lambda r: barrier(r).get("route") == "collapsed", lambda r: barrier(r).__setitem__("route", "range-single")),
    ("A.two-blocks", lambda r: barrier(r).get("readbackBlockCount") == 2,
     lambda r: barrier(r).__setitem__("readbackBlockCount", 1)),
    ("A.saved-marker-in-bullet-list", saved_marker_in_bullet_list, _drop_marker_from_list),
    ("A.saved-neighbours", saved_neighbours, _swap_neighbour),
    ("A.undo-replies-ok", undo_replies_ok, _undo_refused),
    ("A.undo-three-paragraphs", undo_three_paragraphs, _undo_left_list),
]
BEFORE_RED = [
    ("B.046-shape", lambda r: (press_row(r) or {}).get("ok") is False and barrier(r).get("failureShape") == "multi-block-readback",
     lambda r: barrier(r).__setitem__("failureShape", "postcondition-not-met")),
    ("B.multi-sentence", lambda r: MULTI_SENTENCE in (_press(r).get("toast") or ""), _set(_press, "toast", "")),
    ("B.strip-not-verified", lambda r: STRIP.fullmatch(_press(r).get("latency") or "") is None,
     _set(_press, "latency", "• 項目符號 51 ms")),
    ("B.saved-in-list-anyway", saved_marker_in_bullet_list, _drop_marker_from_list),
]


def judge(run, clauses):
    if run.get("fatal"):
        return "NE", {"fatal": run["fatal"].strip().splitlines()[-1]}
    results = {}
    for cid, holds, _ in clauses:
        try:
            results[cid] = bool(holds(run))
        except Exception as error:  # noqa: BLE001 -- unreadable is not holding
            results[cid] = False
            results[cid + ":error"] = f"{type(error).__name__}: {error}"
    return ("PASS" if all(v for k, v in results.items() if ":" not in k) else "FAIL"), results


def verdict(report):
    config = report["config"]
    expected = len(config["browsers"]) * config["repetitions"]
    problems = [f"{name}: identity failed" for name in config["products"] if not report["products"].get(name, {}).get("ok")]
    for r in report["runs"]:
        clauses = BEFORE_RED if r["product"] == "before" and not config.get("mutation") else AFTER_CLAUSES
        r["outcome"], r["clauses"] = judge(r, clauses)
        r["failedClauses"] = sorted(k for k, v in r["clauses"].items() if v is False)
    if config.get("mutation"):
        runs = report["runs"]
        if not (len(runs) == expected and all(r["outcome"] == "FAIL" for r in runs)):
            problems.append(f"mutation {config['mutation']}: {sum(r['outcome'] == 'FAIL' for r in runs)}/{expected} "
                            f"runs FAIL (outcomes {[r['outcome'] for r in runs]})")
        return ("S3_MUTATION_CAUGHT" if not problems else "S3_MUTATION_MISSED"), problems
    after = [r for r in report["runs"] if r["product"] == "after"]
    before = [r for r in report["runs"] if r["product"] == "before"]
    if not (len(after) == expected and all(r["outcome"] == "PASS" for r in after)):
        problems.append(f"after: {sum(r['outcome'] == 'PASS' for r in after)}/{expected} PASS")
    if not (len(before) == expected and all(r["outcome"] == "PASS" for r in before)):
        problems.append(f"before: {sum(r['outcome'] == 'PASS' for r in before)}/{expected} red for 176")
    return ("S3_HOLDS" if not problems else "S3_RED"), problems


def self_test(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    base, _ = verdict(copy.deepcopy(report))
    if base != "S3_HOLDS":
        print(f"self-test needs a holding report; this one is {base}", file=sys.stderr)
        return 2
    results = {}
    for product, clauses in (("after", AFTER_CLAUSES), ("before", BEFORE_RED)):
        index = next(i for i, r in enumerate(report["runs"]) if r["product"] == product)
        for cid, _, mutate in clauses:
            mutated = copy.deepcopy(report)
            mutate(mutated["runs"][index])
            results[cid] = verdict(mutated)[0]
    for name, mutate in {"one-run-missing": lambda r: r["runs"].pop(0),
                         "identity-failed": lambda r: r["products"]["after"].__setitem__("ok", False),
                         "one-run-fatal": lambda r: r["runs"][-1].__setitem__("fatal", "Traceback\nRuntimeError: x")}.items():
        mutated = copy.deepcopy(report)
        mutate(mutated)
        results[name] = verdict(mutated)[0]
    red = all(v != "S3_HOLDS" for v in results.values())
    print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "mutations": len(results),
                      "held": sorted(k for k, v in results.items() if v == "S3_HOLDS"), "results": results},
                     indent=1, ensure_ascii=False))
    return 0 if red else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", type=Path, metavar="REPORT")
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--mutation", choices=sorted(MUTATIONS))
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test)
    if not args.out:
        parser.error("--out is required")
    args.out.mkdir(parents=True, exist_ok=False)
    raw_doc = FIXTURE.read_bytes()
    if hashlib.sha256(raw_doc).hexdigest() != FIXTURE_SHA256:
        raise SystemExit("two-plain.odt changed")
    plan = ([MUTATIONS[args.mutation]] if args.mutation
            else [("before", "set-list-unordered"), ("after", "set-list-unordered")])
    config = {"products": [p for p, _ in plan], "browsers": [x for x in args.browsers.split(",") if x],
              "repetitions": args.repetitions, "mutation": args.mutation}
    report = {"argv": sys.argv, "tool": "check_v81_blank_line_bullet", "config": config, "marker": MARKER,
              "lineEnd": LINE_END, "fixture": {"path": str(FIXTURE.relative_to(REPO)), "sha256": FIXTURE_SHA256,
                                               "receipt": str(FIXTURE_RECEIPT.relative_to(REPO))},
              "products": {}, "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="s3-blank-line-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("check_v81_blank_line_bullet"):
            report["preRun"] = common.pre_run_checks()
            if report["preRun"]["refuse"]:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            for name, action in plan:
                mirror = scratch / name
                pp.build_mirror(common.DIST, mirror, products.overrides(name, [OBSERVER]))
                report["products"][name] = products.identity(name, mirror)
                if not report["products"][name]["ok"]:
                    print(name, "identity FAILED, not run:", report["products"][name]["checks"], file=sys.stderr, flush=True)
                    continue
                with common.served(mirror) as base:
                    for browser in config["browsers"]:
                        for n in range(1, args.repetitions + 1):
                            run, session = {"product": name, "browser": browser, "repetition": n}, None
                            try:
                                session = common.open_browser(browser)
                                run["browserVersion"] = getattr(session, "version", None)
                                run.update(one(session, browser, base, raw_doc, action))
                            except Exception:  # noqa: BLE001 -- recorded
                                run["fatal"] = traceback.format_exc()
                            finally:
                                if session is not None:
                                    run["cleanup"] = common.close_browser(session)
                            report["runs"].append(run)
                            row, press = press_row(run) or {}, run.get("press") or {}
                            print(name, browser, n, press.get("pill"), press.get("latency"), row.get("ok"),
                                  row.get("completion"), (row.get("formatBarrier") or {}).get("readbackBlockCount"),
                                  (press.get("toast") or "")[:40], (run.get("fatal") or "").strip().splitlines()[-1:] or "",
                                  file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report["verdict"], report["problems"] = verdict(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], report["problems"], file=sys.stderr)
    return 0 if report["verdict"] in ("S3_HOLDS", "S3_MUTATION_CAUGHT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
