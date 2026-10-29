#!/usr/bin/env python3
"""B1 (SPEC-M3-shell-v79-finding-173 5.3): a bullet in a NEW blank document keeps the queue open -- the owner's path.

Finding 173.  On host 0.2.40 the owner opened a new blank document (Files "+ New -> New document") and pressed
the toolbar bullet: 「引擎需要重新開啟。沒有檢查點…」.  The ordered engine reports finding 083's situation (a
`.uno:SelectText` on a blank paragraph that selects nothing) as `select-text-returned-none`; the page knew only
083's old name and asked for a rollback a new document cannot have.  Derived from
findings/evidence/173/blank_bullet.py (the diagnostic that reproduced it; not edited).

The owner's steps, not the product-path fixture (handoff 10-29h): the host's own blank template for a zh_TW
user, opened through the page's file input; two arms -- press the bullet right after the document opens
(`noclick`), or after clicking into the paragraph (`click`).  EVERY INPUT IS REAL (tools/v21_input.py: Chrome
CDP Input.dispatchMouseEvent / dispatchKeyEvent, Firefox WebDriver actions): the bullet is a mouse click on
the button's centre, then the marker is typed with real keys WITHOUT restoring focus first (a user presses
the button and types), then the product's own save button; the saved ODT is read from the Blob the page hands
over.  One Worker observer in the HTML records every request and reply, including the error's formatBarrier
-- the fields the disposition reads.

Products (tools/v79_f_products.py), each mirror identity-checked file by file before use; a product whose
identity fails is not run:
  before  page + paragraph-editor-client.js from git d14186167 (generation 78), profile v25
  after   dist/ as served: generation 78 except exactly the two declared files, which equal the tree

An `after` run PASSes when (spec 5.3):
  1. the bullet's reply is 173's shape: ok false, failureShape select-text-returned-none, dispatched true,
     route collapsed, selectionResultSeen true -- otherwise the run did not reach 173's path and is NE;
  2. after the press: pill `ready`, #notice not shown, the toast names the empty paragraph (「這一段是空的」)
     and neither 「不只一個段落」 nor 「回到檢查點」;
  3. the queue is open: at least one insertText after the bullet, every one answered ok, the revision
     advanced, the pill still `ready`;
  4. the save produced an ODT whose paragraph holding the marker has a text:list ancestor.
A `before` run is red FOR 173 when (1) holds and the pill is `recoverable-error` with #notice shown; red for
any other reason is the tool's own setup and fails the verdict.

  check_v79_blank_bullet.py --out DIR [--products before,after] [--browsers chrome,firefox]
                            [--arms noclick,click] [--repetitions 3]
  check_v79_blank_bullet.py --self-test REPORT      (mutations of a real report; each must turn the verdict)

Verdict B1_HOLDS iff both identities hold, every after run PASSes and every before run is red for 173, with
the full count.  --out must not exist.  Nothing under dist/ is written.  Not a timing measurement: no desk gate.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
import run_e2_c_product_path as pp  # noqa: E402
import v21_input as real  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v79_f_products as products  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

BLANK = Path("/home/jiajun/Projects/Nextcloud_Apps/litecore/blank/en-US_zh-TW_A4.odt")
BLANK_SHA256 = "7e6221b697d408fc011b820226b98e4ad908afbadce8aac3ded48140349b5475"
MARKER = "mkbulletq"
CLICK_AT = (0.30, 0.10)  # blank_bullet.py's click arm, as a fraction of #paper
SHAPE = {"failureShape": "select-text-returned-none", "dispatched": True, "route": "collapsed",
         "selectionResultSeen": True}
EMPTY_SENTENCE, MULTI_SENTENCE, ROLLBACK_SENTENCE = "這一段是空的", "不只一個段落", "回到檢查點"
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OBSERVER = """<script>
(() => {
  const rec = window.__b1 = {requests: [], responses: [], blobs: [], workers: 0};
  const snap = v => { try { return JSON.parse(JSON.stringify(v, (k, x) =>
    (x instanceof ArrayBuffer || ArrayBuffer.isView(x)) ? {bytes: x.byteLength} : x)); }
    catch (e) { return {unserialisable: String(e)}; } };
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options); rec.workers += 1;
      this.addEventListener('message', ev => { if (ev.data?.kind === 'response') rec.responses.push(snap(ev.data)); }); }
    postMessage(m, ...rest) { if (m?.kind === 'request') rec.requests.push(snap(m)); return super.postMessage(m, ...rest); }
  };
  const create = URL.createObjectURL.bind(URL);
  URL.createObjectURL = blob => { if (blob instanceof Blob) rec.blobs.push(blob); return create(blob); };
  const click = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () { if (this.hasAttribute('download')) return; return click.call(this); };
})();
</script>"""
PAGE = """(() => ({pill: document.querySelector('#state-pill')?.dataset.state,
  latency: document.querySelector('#s-latency')?.textContent,
  toast: document.querySelector('#toast')?.textContent,
  revision: document.querySelector('#s-revision')?.textContent,
  notice: {show: document.querySelector('#notice')?.dataset.show ?? null,
           text: document.querySelector('#notice-text')?.textContent ?? null},
  focus: document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null,
  requests: window.__b1.requests.length, responses: window.__b1.responses.length,
  workers: window.__b1.workers, blobs: window.__b1.blobs.length}))()"""
BLOB = """(async () => { const b = window.__b1.blobs.at(-1); const u = new Uint8Array(await b.arrayBuffer());
  let s = ''; for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode(...u.subarray(i, i + 8192)); return btoa(s); })()"""
BULLET_BOX = pp.BUTTON_BOX.replace("ARG_SELECTOR", '#toolbar button[data-action="set-list-unordered"]')


def wait(session, predicate, limit):
    until, state = time.monotonic() + limit, None
    while time.monotonic() < until:
        state = evaluate(session, PAGE)
        if state and predicate(state):
            return state, True
        time.sleep(0.2)
    return state, False


def rows(session, start):
    """Every request from index `start` with its reply; the barrier is the error's, as the page receives it."""
    record = evaluate(session, "window.__b1")
    replies = {r.get("requestId"): r for r in record["responses"]}
    out = []
    for q in record["requests"][start:]:
        payload = q.get("payload") or {}
        reply = replies.get(q.get("requestId")) or {}
        error, result = reply.get("error") or {}, reply.get("result") or {}
        barrier = error.get("formatBarrier") or (error.get("details") or {}).get("formatBarrier")
        out.append({"operation": q.get("operation"), "action": payload.get("action"), "route": payload.get("route"),
                    "replied": bool(reply), "ok": reply.get("ok"), "code": error.get("code"),
                    "message": error.get("message"),
                    "barrier": {k: barrier.get(k) for k in ("stage", "route", "dispatched", "failureShape",
                                                             "selectionResultSeen", "resultSeen")} if barrier else None,
                    "revision": [result.get("beforeRevision"), result.get("revision")]})
    return out


def odt_reading(raw: bytes) -> dict:
    """Where the marker landed in the saved document, read from content.xml."""
    content = zipfile.ZipFile(io.BytesIO(raw)).read("content.xml")
    root = ET.fromstring(content)
    parent = {child: node for node in root.iter() for child in node}
    found = []
    for node in root.iter():
        if node.tag in (f"{{{TEXT_NS}}}p", f"{{{TEXT_NS}}}h") and MARKER in "".join(node.itertext()).lower():
            chain, up = [], parent.get(node)
            while up is not None:
                chain.append(up.tag.split("}")[-1])
                up = parent.get(up)
            found.append({"text": "".join(node.itertext()), "ancestors": chain, "inList": "list" in chain})
    return {"sha256": hashlib.sha256(raw).hexdigest(), "paragraphs": found,
            "markerInList": bool(found) and all(p["inList"] for p in found)}


def one(session, browser, base, arm, raw_blank, product):
    navigate(session, base)
    _, ok = wait(session, lambda s: s["pill"] == "ready", 240)
    if not ok:
        return {"fatal": "page not ready"}
    workers = evaluate(session, PAGE)["workers"]
    opened = evaluate(session, pp.OPEN_BYTES.replace("ARG_B64", base64.b64encode(raw_blank).decode())
                      .replace("ARG_NAME", BLANK.name))
    # Opening starts a new worker; `ready` before it would be the old document's.
    state, ok = wait(session, lambda s: s["workers"] > workers and s["pill"] == "ready", 120)
    if not ok:
        return {"fatal": f"document not opened ({opened})", "page": state}
    time.sleep(1.5)
    out = {"opened": evaluate(session, PAGE)}
    if arm == "click":
        evaluate(session, real.SCROLL_TO_FRACTION.replace("ARG_F", repr(CLICK_AT[1])))
        time.sleep(0.25)
        rect = evaluate(session, real.PAPER_RECT)
        real.click(session, browser, rect["left"] + rect["width"] * CLICK_AT[0], rect["top"] + rect["height"] * CLICK_AT[1])
        out["clicked"], out["caretPlaced"] = wait(session, lambda s: "定位游標" in (s["latency"] or ""), 30)
        time.sleep(0.8)
    evaluate(session, pp.CLEAR_TOAST)
    start = evaluate(session, PAGE)["requests"]
    box = evaluate(session, BULLET_BOX)
    if not box:
        out["fatal"] = "no bullet button"
        return out
    real.click(session, browser, box["x"], box["y"])
    _, out["pressSettled"] = wait(session, lambda s: s["pill"] in ("recoverable-error", "restart-required")
                                  or "項目符號" in (s["latency"] or ""), 60)
    time.sleep(1.5)
    out["press"] = evaluate(session, PAGE)
    out["pressRows"] = rows(session, start)
    if product == "before":
        return out
    typed_from = evaluate(session, PAGE)["requests"]
    for ch in MARKER:
        real.key(session, browser, ch)
        time.sleep(0.12)

    def typed(s):
        return (s["requests"] > typed_from and s["responses"] >= s["requests"] and s["pill"] == "ready"
                and s["revision"] != out["press"]["revision"])
    _, out["typedSettled"] = wait(session, typed, 30)
    time.sleep(1.5)
    out["typed"] = evaluate(session, PAGE)
    out["typedRows"] = rows(session, typed_from)
    blobs = out["typed"]["blobs"]
    evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
    _, out["saveSettled"] = wait(session, lambda s: s["blobs"] > blobs, 60)
    if out["saveSettled"]:
        out["saved"] = odt_reading(base64.b64decode(evaluate(session, BLOB)))
    return out


def bullet_row(run):
    return next((r for r in run.get("pressRows") or [] if r.get("action") == "set-list-unordered"), None)


def on_173_path(run):
    row = bullet_row(run)
    return bool(row) and row.get("ok") is False and all((row.get("barrier") or {}).get(k) == v for k, v in SHAPE.items())


def judge_after(run):
    """('PASS' | 'FAIL' | 'NE', why) for one after run, from the recorded run only."""
    if run.get("fatal"):
        return "NE", ["fatal: " + run["fatal"].strip().splitlines()[-1]]
    if not on_173_path(run):
        return "NE", [f"bullet reply is not 173's shape: {bullet_row(run)}"]
    why = []
    press = run.get("press") or {}
    toast = press.get("toast") or ""
    if press.get("pill") != "ready":
        why.append(f"after the press pill {press.get('pill')!r}")
    if (press.get("notice") or {}).get("show") == "1":
        why.append(f"notice shown: {(press.get('notice') or {}).get('text')!r}")
    if EMPTY_SENTENCE not in toast or MULTI_SENTENCE in toast or ROLLBACK_SENTENCE in toast:
        why.append(f"toast {toast!r}")
    inserts = [r for r in run.get("typedRows") or [] if r.get("operation") == "insertText"]
    if not inserts:
        why.append("no insertText after the bullet")
    for r in inserts:
        if r.get("ok") is not True:
            why.append(f"insertText ok={r.get('ok')} code={r.get('code')}")
    typed = run.get("typed") or {}
    if not run.get("typedSettled") or typed.get("pill") != "ready" or typed.get("revision") == press.get("revision"):
        why.append(f"typing: settled={run.get('typedSettled')} pill={typed.get('pill')!r} "
                   f"revision {press.get('revision')}->{typed.get('revision')}")
    saved = run.get("saved") or {}
    if not saved.get("markerInList"):
        why.append(f"saved ODT: marker paragraphs {saved.get('paragraphs')}")
    return ("PASS" if not why else "FAIL"), why


def red_for_173(run):
    press = run.get("press") or {}
    return (not run.get("fatal") and on_173_path(run) and press.get("pill") == "recoverable-error"
            and (press.get("notice") or {}).get("show") == "1")


def verdict(report):
    names, browsers, arms, n = (report["config"][k] for k in ("products", "browsers", "arms", "repetitions"))
    expected = len(browsers) * len(arms) * n
    problems = []
    for name in names:
        if not report["products"].get(name, {}).get("ok"):
            problems.append(f"{name}: identity failed")
    after = [r for r in report["runs"] if r["product"] == "after"]
    before = [r for r in report["runs"] if r["product"] == "before"]
    for r in after:
        r["outcome"], r["why"] = judge_after(r)
    for r in before:
        r["redFor173"] = red_for_173(r)
    if set(names) != {"before", "after"}:
        problems.append("a verdict needs both products: after to pass and before as the counterexample")
    if "after" in names and not (len(after) == expected and all(r["outcome"] == "PASS" for r in after)):
        problems.append(f"after: {sum(r['outcome'] == 'PASS' for r in after)}/{expected} PASS")
    if "before" in names and not (len(before) == expected and all(r["redFor173"] for r in before)):
        problems.append(f"before: {sum(r['redFor173'] for r in before)}/{expected} red for 173")
    return ("B1_HOLDS" if not problems else "B1_RED"), problems


def self_test(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    base, _ = verdict(copy.deepcopy(report))
    if base != "B1_HOLDS":
        print(f"self-test needs a holding report; this one is {base}", file=sys.stderr)
        return 2

    def first(r, product):
        return next(x for x in r["runs"] if x["product"] == product)

    def toast_multi(r):
        first(r, "after")["press"]["toast"] = "（動作已送出，但這一格的檢查涵蓋了不只一個段落…這是檢查的極限，不是文件壞了）"

    def notice_shown(r):
        first(r, "after")["press"]["notice"]["show"] = "1"

    def marker_out_of_list(r):
        first(r, "after")["saved"]["markerInList"] = False

    def insert_refused(r):
        next(x for x in first(r, "after")["typedRows"] if x["operation"] == "insertText")["ok"] = False

    def other_shape(r):
        bullet_row(first(r, "after"))["barrier"]["failureShape"] = "multi-block-readback"

    def before_ready(r):
        first(r, "before")["press"]["pill"] = "ready"

    def one_run_missing(r):
        r["runs"].remove(first(r, "after"))

    def identity_failed(r):
        r["products"]["after"]["ok"] = False

    results = {}
    for name, mutate in [("toast-multi", toast_multi), ("notice-shown", notice_shown),
                         ("marker-out-of-list", marker_out_of_list), ("insert-refused", insert_refused),
                         ("other-shape", other_shape), ("before-ready", before_ready),
                         ("one-run-missing", one_run_missing), ("identity-failed", identity_failed)]:
        mutated = copy.deepcopy(report)
        mutate(mutated)
        got, problems = verdict(mutated)
        results[name] = {"verdict": got, "problems": problems}
        if name == "other-shape":
            ne = [r for r in mutated["runs"] if r["product"] == "after" and r.get("outcome") == "NE"]
            results[name]["afterNE"] = len(ne)
    red = all(v["verdict"] != "B1_HOLDS" for v in results.values()) and results["other-shape"].get("afterNE") == 1
    print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "mutations": results},
                     indent=1, ensure_ascii=False))
    return 0 if red else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", type=Path, metavar="REPORT")
    parser.add_argument("--products", default="before,after")
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--arms", default="noclick,click")
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test)
    if not args.out:
        parser.error("--out is required")
    args.out.mkdir(parents=True, exist_ok=False)
    raw_blank = BLANK.read_bytes()
    config = {"products": [x for x in args.products.split(",") if x], "browsers": [x for x in args.browsers.split(",") if x],
              "arms": [x for x in args.arms.split(",") if x], "repetitions": args.repetitions}
    report = {"argv": sys.argv, "tool": "check_v79_blank_bullet", "config": config, "marker": MARKER,
              "blank": {"path": str(BLANK), "sha256": hashlib.sha256(raw_blank).hexdigest()},
              "products": {}, "runs": []}
    if report["blank"]["sha256"] != BLANK_SHA256:
        raise SystemExit(f"blank template changed: {report['blank']['sha256']}")
    scratch = Path(tempfile.mkdtemp(prefix="b1-blank-bullet-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("check_v79_blank_bullet"):
            report["preRun"] = common.pre_run_checks()
            if report["preRun"]["refuse"]:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            for name in config["products"]:
                mirror = scratch / name
                pp.build_mirror(common.DIST, mirror, products.overrides(name, [OBSERVER]))
                report["products"][name] = products.identity(name, mirror)
                if not report["products"][name]["ok"]:
                    print(name, "identity FAILED, not run:", report["products"][name]["checks"], file=sys.stderr, flush=True)
                    continue
                with common.served(mirror) as base:
                    for browser in config["browsers"]:
                        for arm in config["arms"]:
                            for n in range(1, args.repetitions + 1):
                                run, session = {"product": name, "browser": browser, "arm": arm, "repetition": n}, None
                                try:
                                    session = common.open_browser(browser)
                                    run["browserVersion"] = getattr(session, "version", None)
                                    run.update(one(session, browser, base, arm, raw_blank, name))
                                except Exception:  # noqa: BLE001 -- recorded
                                    run["fatal"] = traceback.format_exc()
                                finally:
                                    if session is not None:
                                        run["cleanup"] = common.close_browser(session)
                                report["runs"].append(run)
                                press = run.get("press") or {}
                                print(name, browser, arm, n, press.get("pill"), (press.get("toast") or "")[-60:],
                                      "saved-in-list" if (run.get("saved") or {}).get("markerInList") else "",
                                      (run.get("fatal") or "").strip().splitlines()[-1:] or "",
                                      file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report["verdict"], report["problems"] = verdict(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], report["problems"], file=sys.stderr)
    return 0 if report["verdict"] == "B1_HOLDS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
