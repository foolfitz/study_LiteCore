#!/usr/bin/env python3
"""Finding 154's diagnostic: on host 0.2.25, is the closed Markdown dialog displayed, and is it what the click hits?

Opens one long60 copy through the host's own route (login, Files -> open; the D2 host arm's route), then reads, in
this order:
  1. the dialog: `open`, computed `display`/`position`, its box, and the stylesheet rules that set `display` on it;
  2. the paste-markdown button (item 2's entry, which the shell hides): `hidden` and computed `display`;
  3. what `elementFromPoint` returns at the D2 arm's first-line point;
  4. a real click there: does the page ask the engine to place the caret (the latency label 「定位游標」)?
Then the counterfactual, on the same page: one style rule `#markdown-dialog:not([open]) { display: none }`, and 1-4
again.  A screenshot before and after (Chrome).  Diagnostic, not evidence for any criterion.

  python3 findings/evidence/154/diag_markdown_dialog_on_host.py --browser chrome --out findings/evidence/154

H-154c and H-154o (SPEC-M3-link-batch-v22 §11.5; fable ruling 5 items 18-19), added 2026-10-19 -- an addition:
the diagnostic path above is unchanged.

  --h154 --rounds N --expect-version 0.2.27 --expect-build-id ID   N rounds, each in a fresh browser on a fresh copy:
      closedBefore  at page ready, before any dialog use: the read above, the element at the D2 first-line point,
                    a real click there and the place-caret request it sends;
      open          a real click on the entry button, then: open, display, box inside the viewport, the focused
                    element, the elements at the centres of 插入 and 取消, and (recorded) margin and centre offset;
      closedAfter   a real click on 取消, then the closedBefore reading again.
      Every read after a click waits for state == "ready" and pending == "0" (L-154-diag-second-click), and the
      place-caret read also waits for the request itself.  Writes h154-<browser>-<stamp>.json with its verdict.
  --judge REPORT [--expect-version V --expect-build-id ID]   the H-154c / H-154o verdicts of a report: an --h154
      report, or the closed reading (`asShipped`) of a diagnostic report, read as closedBefore only.
  --self-test   the red cases: 0.2.25's and 0.2.26's committed readings, and synthetic reports.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "wasm_sdk_probe" / "tools"))
import run_e2_c_product_path as pp  # noqa: E402
import run_v21_d2 as d2  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402

READ = r"""(() => {
  const d = document.getElementById('markdown-dialog');
  const b = document.querySelector('button[data-action="paste-markdown"]');
  const box = (e) => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height].map((v) => Math.round(v)); };
  const rules = [];
  for (const sheet of document.styleSheets) {
    let list; try { list = sheet.cssRules; } catch (e) { continue; }
    const walk = (items, where) => { for (const r of items) {
      if (r.cssRules) walk(r.cssRules, where + ' > ' + (r.cssText.split('{')[0].trim().slice(0, 60)));
      if (r.selectorText && r.style && r.style.display && d && (() => { try { return d.matches(r.selectorText); } catch (e) { return false; } })())
        rules.push({ sheet: (sheet.href || 'inline').split('/').slice(-2).join('/'), where, selector: r.selectorText.slice(0, 160), display: r.style.display });
    } };
    walk(list, '');
  }
  const cs = d && getComputedStyle(d);
  return {
    dialog: d && { open: d.open, display: cs.display, position: cs.position, visibility: cs.visibility, zIndex: cs.zIndex,
                   box: box(d), parent: d.parentElement && (d.parentElement.id || d.parentElement.tagName) },
    rulesSettingDisplay: rules,
    button: b && { hidden: b.hidden, display: getComputedStyle(b).display, box: box(b) },
    viewport: [innerWidth, innerHeight],
  };
})()"""

AT = r"""((x, y) => { const e = document.elementFromPoint(x, y); const d = document.getElementById('markdown-dialog');
  return e && { tag: e.tagName, id: e.id, cls: String(e.className).slice(0, 80), insideDialog: !!(d && d.contains(e)) }; })"""

FIX = r"""(() => { const s = document.createElement('style'); s.id = 'diag-154';
  s.textContent = '#markdown-dialog:not([open]) { display: none; }'; document.head.append(s); return true; })()"""


def shot(session, out: Path, name: str) -> str | None:
    try:
        png = session.screenshot()
    except Exception as error:  # noqa: BLE001
        return f"no screenshot: {type(error).__name__}"
    (out / name).write_bytes(png)
    return name


def measure(session, browser: str, probe, out: Path, label: str) -> dict:
    record = {"read": pp.evaluate(session, READ)}
    rects = probe.ask_rectangles(session)
    point = probe.first_line_point(session, rects)
    record["point"] = point.get("point")
    if record["point"]:
        x, y = record["point"]
        record["elementAtPoint"] = pp.evaluate(session, f"{AT}({x}, {y})")
        start = pp.evaluate(session, probe.LOG_LENGTH)
        probe.real_click(session, browser, x, y)
        record["clickState"] = probe.ui.until(session, lambda s: "定位游標" in (s.get("latency") or ""), 10)
        record["placeCaretRequests"] = [e.get("op") for e in probe.log_from(session, start)
                                        if e.get("k") == "rq" and "PlaceCaret" in str(e.get("op"))]
    record["screenshot"] = shot(session, out, f"{label}-{browser}.png")
    return record


# ------------------------------------------------------------------ H-154c / H-154o (v22 §11.5)

PAGE_RULE = "#markdown-dialog:not([open])"
HOST_RULE = "#litecore-editor-root dialog:not([open])"

OPEN_READ = r"""(() => {
  const d = document.getElementById('markdown-dialog');
  const box = (e) => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height].map((v) => Math.round(v)); };
  const at = (sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect();
    const x = r.x + r.width / 2, y = r.y + r.height / 2; const hit = document.elementFromPoint(x, y);
    return { center: [Math.round(x), Math.round(y)], hitId: hit && hit.id, hitTag: hit && hit.tagName,
             isTarget: !!(hit && (hit === e || e.contains(hit))) }; };
  const cs = d && getComputedStyle(d);
  return { open: d && d.open, display: cs && cs.display, box: d && box(d), margin: cs && cs.margin,
           activeElement: document.activeElement && document.activeElement.id,
           insert: at('#markdown-insert'), cancel: at('#markdown-cancel'), viewport: [innerWidth, innerHeight] };
})()"""

DIALOG_OPEN = "(() => !!document.getElementById('markdown-dialog')?.open)()"
CENTER = r"""((sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect();
  return r.width > 0 && r.height > 0 ? [r.x + r.width / 2, r.y + r.height / 2] : null; })"""


def ready(probe, session, limit: float = 15) -> dict | None:
    return probe.ui.until(session, lambda s: s.get("state") == "ready" and str(s.get("pending")) == "0", limit)


def closed_reading(session, browser: str, probe) -> dict:
    record = {"read": pp.evaluate(session, READ)}
    point = probe.first_line_point(session, probe.ask_rectangles(session))
    record["point"] = point.get("point")
    if record["point"]:
        x, y = record["point"]
        record["elementAtPoint"] = pp.evaluate(session, f"{AT}({x}, {y})")
        start = pp.evaluate(session, probe.LOG_LENGTH)
        probe.real_click(session, browser, x, y)
        deadline, sent = time.monotonic() + 10, []
        while time.monotonic() < deadline and not sent:
            sent = [e.get("op") for e in probe.log_from(session, start)
                    if e.get("k") == "rq" and "PlaceCaret" in str(e.get("op"))]
            time.sleep(0.15)
        record["placeCaretRequests"] = sent
        record["readyAfterClick"] = ready(probe, session)
    return record


def open_reading(session, browser: str, probe) -> dict:
    record = {}
    center = pp.evaluate(session, f"{CENTER}('#toolbar [data-action=\"paste-markdown\"]')")
    record["entryCenter"] = center
    if not center:
        record["error"] = "no visible entry button to click"
        return record
    probe.real_click(session, browser, *center)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not pp.evaluate(session, DIALOG_OPEN):
        time.sleep(0.15)
    time.sleep(0.3)
    record["read"] = pp.evaluate(session, OPEN_READ)
    return record


def cancel(session, browser: str, probe) -> dict:
    record = {"cancelCenter": pp.evaluate(session, f"{CENTER}('#markdown-cancel')")}
    if record["cancelCenter"]:
        probe.real_click(session, browser, *record["cancelCenter"])
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and pp.evaluate(session, DIALOG_OPEN):
            time.sleep(0.15)
    record["closed"] = not pp.evaluate(session, DIALOG_OPEN)
    record["ready"] = ready(probe, session)
    return record


def judge_closed(rec: dict | None) -> list[str]:
    """H-154c on one closed reading; the failing clauses (empty = pass)."""
    if not rec:
        return ["no closed reading"]
    read = rec.get("read") or {}
    d, b = read.get("dialog") or {}, read.get("button") or {}
    selectors = [r.get("selector") for r in read.get("rulesSettingDisplay") or [] if r.get("display") == "none"]
    out = []
    if d.get("open") is not False or d.get("display") != "none" or d.get("box") != [0, 0, 0, 0]:
        out.append(f"dialog shown: open {d.get('open')} display {d.get('display')} box {d.get('box')}")
    if PAGE_RULE not in selectors:
        out.append("page rule absent")
    if HOST_RULE not in selectors:
        out.append("host rule absent")
    at = rec.get("elementAtPoint") or {}
    if at.get("tag") != "CANVAS" or at.get("id") != "canvas" or at.get("insideDialog") is not False:
        out.append(f"the first-line point is {at.get('tag')}#{at.get('id')} (inside dialog {at.get('insideDialog')})")
    if not rec.get("placeCaretRequests"):
        out.append("the click sent no place-caret request")
    box = b.get("box") or [0, 0, 0, 0]
    if b.get("hidden") is not False or b.get("display") == "none" or not (box[2] > 0 and box[3] > 0):
        out.append(f"entry button not visible: hidden {b.get('hidden')} display {b.get('display')} box {box}")
    return out


def judge_open(rec: dict | None) -> list[str]:
    """H-154o on one open reading; the failing clauses (empty = pass)."""
    if not rec or rec.get("error"):
        return [f"no open reading: {(rec or {}).get('error')}"]
    r = rec.get("read") or {}
    out = []
    box, (vw, vh) = r.get("box") or [0, 0, 0, 0], r.get("viewport") or [0, 0]
    if r.get("open") is not True or r.get("display") == "none":
        out.append(f"not open: open {r.get('open')} display {r.get('display')}")
    if not (box[2] > 0 and box[3] > 0 and box[0] >= 0 and box[1] >= 0 and box[0] + box[2] <= vw and box[1] + box[3] <= vh):
        out.append(f"box {box} not inside the viewport {[vw, vh]}")
    if r.get("activeElement") != "markdown-text":
        out.append(f"focus on {r.get('activeElement')!r}, not the text box")
    for name in ("insert", "cancel"):
        if not (r.get(name) or {}).get("isTarget"):
            out.append(f"the centre of {name} hits {(r.get(name) or {}).get('hitTag')}#{(r.get(name) or {}).get('hitId')}")
    return out


def judge_h154(report: dict, version: str | None, build_id: str | None) -> dict:
    ident = report.get("hostIdentity") or {}
    pinned = []
    if version and ident.get("hostVersion") != version:
        pinned.append(f"host version {ident.get('hostVersion')} != {version}")
    if build_id and ident.get("buildId") != build_id:
        pinned.append(f"buildId {ident.get('buildId')} != {build_id}")
    rounds = report.get("rounds")
    if rounds is None:                     # a diagnostic report: its closed reading as shipped, closedBefore only
        rounds = [{"round": 1, "closedBefore": report.get("asShipped")}]
    c, o = [], []
    for rnd in rounds:
        for which in ("closedBefore", "closedAfter"):
            if which in rnd or which == "closedBefore":
                c += [f"r{rnd.get('round')} {which}: {why}" for why in judge_closed(rnd.get(which))]
        if "open" in rnd:
            o += [f"r{rnd.get('round')} open: {why}" for why in judge_open(rnd.get("open"))]
    has_open = any("open" in rnd for rnd in rounds)
    return {"H-154c": "FAIL" if (c or pinned) else ("PASS" if rounds else "NOT_ESTABLISHED"),
            "H-154o": ("FAIL" if (o or pinned) else "PASS") if has_open else "NOT_ESTABLISHED",
            "pinned": pinned, "closedFails": c, "openFails": o, "rounds": len(rounds)}


def self_test() -> int:
    here = Path(__file__).resolve().parent
    load = lambda name: json.loads((here / name).read_text(encoding="utf-8"))  # noqa: E731
    good_closed = {"read": {"dialog": {"open": False, "display": "none", "box": [0, 0, 0, 0]},
                            "rulesSettingDisplay": [{"selector": PAGE_RULE, "display": "none"},
                                                    {"selector": HOST_RULE, "display": "none"}],
                            "button": {"hidden": False, "display": "inline-flex", "box": [400, 8, 120, 28]}},
                   "elementAtPoint": {"tag": "CANVAS", "id": "canvas", "insideDialog": False},
                   "placeCaretRequests": ["editorPlaceCaretV2"]}
    good_open = {"read": {"open": True, "display": "block", "box": [605, 200, 640, 335], "viewport": [1850, 980],
                          "activeElement": "markdown-text", "margin": "auto",
                          "insert": {"isTarget": True}, "cancel": {"isTarget": True}}}
    good = {"hostIdentity": {"hostVersion": "0.2.27", "buildId": "B"},
            "rounds": [{"round": k, "closedBefore": json.loads(json.dumps(good_closed)), "open": json.loads(json.dumps(good_open)),
                        "closedAfter": json.loads(json.dumps(good_closed))} for k in (1, 2, 3)]}

    def mutated(fn):
        rep = json.loads(json.dumps(good)); fn(rep); return rep
    cases = [
        ("control: a synthetic passing report", good, "0.2.27", "B", {"H-154c": "PASS", "H-154o": "PASS"}, None),
        ("0.2.25 Chrome (displayed dialog)", load("diag-154-chrome-20261017T170402.json"), None, None, {"H-154c": "FAIL"},
         ["dialog shown", "page rule absent", "host rule absent", "the first-line point is TEXTAREA", "no place-caret",
          "entry button not visible"]),
        ("0.2.25 Firefox", load("diag-154-firefox-20261017T170449.json"), None, None, {"H-154c": "FAIL"},
         ["dialog shown", "page rule absent"]),
        ("0.2.26 Chrome: 154's own acceptance holds, the new clauses fail", load("0226/diag-154-chrome-20261017T181633.json"),
         None, None, {"H-154c": "FAIL"}, ["page rule absent", "entry button not visible"]),
        ("0.2.26 Firefox, as above", load("0226/diag-154-firefox-20261017T181647.json"), None, None, {"H-154c": "FAIL"},
         ["page rule absent", "entry button not visible"]),
        ("a synthetic report with the button hidden", mutated(lambda r: r["rounds"][1]["closedAfter"]["read"]["button"].update(hidden=True, display="none", box=[0, 0, 0, 0])),
         "0.2.27", "B", {"H-154c": "FAIL"}, ["entry button not visible"]),
        ("focus not in the text box", mutated(lambda r: r["rounds"][0]["open"]["read"].update(activeElement="sink")),
         "0.2.27", "B", {"H-154o": "FAIL"}, ["focus on 'sink'"]),
        ("the box partly outside the viewport", mutated(lambda r: r["rounds"][2]["open"]["read"].update(box=[1500, 200, 640, 335])),
         "0.2.27", "B", {"H-154o": "FAIL"}, ["not inside the viewport"]),
        ("the wrong host version", good, "0.2.28", "B", {"H-154c": "FAIL", "H-154o": "FAIL"}, ["host version"]),
        ("no open arm: H-154o is not established", mutated(lambda r: [x.pop("open") for x in r["rounds"]]), "0.2.27", "B",
         {"H-154o": "NOT_ESTABLISHED"}, None),
    ]
    # 154's own acceptance (v21 §12.5 (c)) on 0.2.26: none of these may fail there.
    acceptance = ["dialog shown", "host rule absent", "the first-line point", "no place-caret"]
    bad = 0
    for label, report, version, build, expect, clauses in cases:
        got = judge_h154(report, version, build)
        fails = " | ".join(got["closedFails"] + got["openFails"] + got["pinned"])
        ok = all(got[k] == v for k, v in expect.items()) and all(c in fails for c in (clauses or []))
        if label.startswith("0.2.26"):
            ok = ok and not any(a in fails for a in acceptance)
        bad += not ok
        print(f"{'ok  ' if ok else 'BAD '} {label}: {', '.join(f'{k} {got[k]}' for k in expect)}"
              + (f"; clauses {clauses}" if clauses else ""))
    print(f"self-test: {len(cases) - bad}/{len(cases)} as required")
    return 0 if bad == 0 else 1


def run_h154(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    probe = d2.load_probe()
    identity = d2.host_identity(probe.DEFAULT_DDEV)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    report = {"tool": "diag_markdown_dialog_on_host.py --h154", "browser": args.browser, "hostIdentity": identity,
              "toolSha256": common.sha256_file(Path(__file__)), "startedAt": common.now_iso(), "rounds": []}
    path = out / f"h154-{args.browser}-{stamp}.json"
    instance = probe.Instance(probe.DEFAULT_DDEV)
    doc = build_long_document(60)
    report["doc"] = hashlib.sha256(doc).hexdigest()
    with common.browser_lock(f"h154 {args.browser}", wait_s=args.wait_lock) as holder:
        report["lock"] = holder
        for k in range(1, args.rounds + 1):
            rnd = {"round": k}
            report["rounds"].append(rnd)
            folder, name = f"h154-{args.browser}-{stamp}-r{k}", "h154.odt"
            session = None
            try:
                rnd["mkcol"] = instance.dav("MKCOL", folder)[0]
                instance.dav("PUT", f"{folder}/{name}", doc, {"Content-Type": "application/vnd.oasis.opendocument.text"})
                session = probe.ui.new_session(args.browser)
                rnd["version"] = getattr(session, "version", None)
                rnd["login"] = probe.login(session, instance.base, "admin", instance.password)
                probe.open_from_files(session, instance.base, folder, name, rnd)
                rnd["opened"] = probe.ui.quiet(session, 180)
                pp.evaluate(session, probe.INSTRUMENT)
                rnd["closedBefore"] = closed_reading(session, args.browser, probe)
                rnd["open"] = open_reading(session, args.browser, probe)
                rnd["cancel"] = cancel(session, args.browser, probe)
                rnd["closedAfter"] = closed_reading(session, args.browser, probe)
                rnd["screenshot"] = shot(session, out, f"h154-{args.browser}-{stamp}-r{k}.png")
            except Exception as error:  # noqa: BLE001 -- recorded; the judge reads a missing reading as a failure
                rnd["error"] = f"{type(error).__name__}: {error}"[:600]
            finally:
                if session is not None:
                    rnd["close"] = common.close_browser(session)
                rnd["deletedFolder"] = instance.dav("DELETE", folder)[0]
                path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    report["completedAt"] = common.now_iso()
    report["verdict"] = judge_h154(report, args.expect_version, args.expect_build_id)
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    print(json.dumps(report["verdict"], ensure_ascii=False, indent=1))
    print(path)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    ap.add_argument("--out")
    ap.add_argument("--h154", action="store_true")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--wait-lock", type=float, default=0.0)
    ap.add_argument("--expect-version")
    ap.add_argument("--expect-build-id")
    ap.add_argument("--judge", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.judge:
        verdict = judge_h154(json.loads(args.judge.read_text(encoding="utf-8")), args.expect_version, args.expect_build_id)
        print(json.dumps(verdict, ensure_ascii=False, indent=1))
        return 0 if verdict["H-154c"] == "PASS" and verdict["H-154o"] == "PASS" else 1
    if not args.out:
        raise SystemExit("--out is required")
    if args.h154:
        if not (args.expect_version and args.expect_build_id):
            raise SystemExit("--h154 needs --expect-version and --expect-build-id")
        return run_h154(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    probe = d2.load_probe()
    identity = d2.host_identity(probe.DEFAULT_DDEV)
    doc = build_long_document(60)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    folder, name = f"diag-154-{args.browser}-{stamp}", "diag-154.odt"
    report = {"tool": "diag_markdown_dialog_on_host.py", "browser": args.browser, "hostIdentity": identity,
              "toolSha256": common.sha256_file(Path(__file__)), "doc": hashlib.sha256(doc).hexdigest(),
              "startedAt": common.now_iso()}
    instance = probe.Instance(probe.DEFAULT_DDEV)
    session = None
    with common.browser_lock(f"diag-154 {args.browser}", wait_s=0) as holder:
        report["lock"] = holder
        report["mkcol"] = instance.dav("MKCOL", folder)[0]
        try:
            instance.dav("PUT", f"{folder}/{name}", doc, {"Content-Type": "application/vnd.oasis.opendocument.text"})
            session = probe.ui.new_session(args.browser)
            report["version"] = getattr(session, "version", None)
            report["login"] = probe.login(session, instance.base, "admin", instance.password)
            probe.open_from_files(session, instance.base, folder, name, report)
            report["opened"] = probe.ui.quiet(session, 180)
            pp.evaluate(session, probe.INSTRUMENT)
            report["asShipped"] = measure(session, args.browser, probe, out, "as-shipped")
            report["fixApplied"] = pp.evaluate(session, FIX)
            time.sleep(0.5)
            report["withRule"] = measure(session, args.browser, probe, out, "with-rule")
        finally:
            if session is not None:
                report["close"] = common.close_browser(session)
            report["deletedFolder"] = instance.dav("DELETE", folder)[0]
            report["completedAt"] = common.now_iso()
            path = out / f"diag-154-{args.browser}-{stamp}.json"
            path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    for key in ("asShipped", "withRule"):
        r = report.get(key) or {}
        print(key, json.dumps({"dialog": (r.get("read") or {}).get("dialog"), "at": r.get("elementAtPoint"),
                               "placeCaret": r.get("placeCaretRequests"),
                               "rules": (r.get("read") or {}).get("rulesSettingDisplay")}, ensure_ascii=False))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
