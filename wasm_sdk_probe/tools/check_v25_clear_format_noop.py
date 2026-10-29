#!/usr/bin/env python3
"""F2 (SPEC-M3-link-batch-v25 6.3, R3): clear-format on plain text is four ok answers on v25 -- and red on v24.

Finding 172.  On v23/v24 the ordered engine judged a request for the inline format the text already has (a
no-op) LOK_COMMAND_FAILED, so the page's clear-format (four `set-*` presses with enabled:false,
e2-editor-app.js clearInlineFormatting) stopped at its first press on plain text.  v25 answers a verified no-op
like a change and names the proof in `witness`.

Products (tools/v25_f_products.py): v24 from its own bytes (page b15a6d8e from git, the v24 archive's profile),
v25 as dist/ serves it since the cutover; each mirror is identity-checked file by file before it is used, and a
product whose identity fails is not run.  One Worker observer in the HTML records requests and replies.

Per run (fresh browser): wait for `ready`, click into plain text (the product-path POINT_AT at 0.35/0.28, as
diag_format.py's format scenario), press clear-format TWICE, waiting for each toast; the SECOND press is judged.

WHY TWICE (measured 2026-10-29, f2-shake-01, before any evidence run): on the FIRST clear-format after the caret
is placed, LOK broadcasts all four state items inside the flush, so even v24 answers four ok (v25's witnesses
were all "on-time-item").  172 needs a no-op request whose state item does NOT arrive in the flush, and LOK only
re-broadcasts a state that changed.  The first press is the warm-up that makes the second press's four requests
no-ops with nothing broadcast -- finding 172's path, still on plain text.  The first press is recorded and must
end in 已清除 and `ready` (else the run is the check's own setup, not a measurement); it is not judged.

The judged press PASSes when: exactly the four requests set-bold, set-italic, set-underline, set-strikethrough,
each with enabled:false; each answered ok with changed:true, completion "uno-command-result" and a witness from
{"uno-success","on-time-item","state-noop"}; the toast starts with 已清除; the pill is `ready`; and set-bold's
witness is "state-noop" (the press exercised the no-op proof 172 broke, rather than meeting a broadcast).
The witness clauses are the first measurement of the engine's JSON field (spec v25 13 item 4): the v25 worker
forwards only those three values and turns a missing or unknown engine witness into null.

A v24 run counts as the counterexample only when it is red FOR 172: the warm-up held and the judged press's
first reply is LOK_COMMAND_FAILED.  A v24 run red for any other reason is the check's own setup and fails the
verdict.  Exit 0 iff every v25 run PASSes and every v24 run is red for 172.

--out must not exist.  Nothing under dist/ is written.  Not a timing measurement: no desk gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
import run_e2_c_product_path as pp  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v25_f_products as products  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

FORMAT_ACTIONS = ["set-bold", "set-italic", "set-underline", "set-strikethrough"]
WITNESSES = {"uno-success", "on-time-item", "state-noop"}
OBSERVER = """<script>
(() => {
  const rec = window.__f2 = {requests: [], responses: []};
  const snap = v => { try { return JSON.parse(JSON.stringify(v, (k, x) =>
    (x instanceof ArrayBuffer || ArrayBuffer.isView(x)) ? {bytes: x.byteLength} : x)); }
    catch (e) { return {unserialisable: String(e)}; } };
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options);
      this.addEventListener('message', ev => { if (ev.data?.kind === 'response') rec.responses.push(snap(ev.data)); }); }
    postMessage(m, ...rest) { if (m?.kind === 'request') rec.requests.push(snap(m)); return super.postMessage(m, ...rest); }
  };
})();
</script>"""
PAGE = """(() => ({pill: document.querySelector('#state-pill')?.dataset.state,
  latency: document.querySelector('#s-latency')?.textContent,
  toast: document.querySelector('#toast')?.textContent,
  revision: document.querySelector('#s-revision')?.textContent,
  requests: window.__f2.requests.length}))()"""


def wait(session, predicate, limit):
    until, state = time.monotonic() + limit, None
    while time.monotonic() < until:
        state = evaluate(session, PAGE)
        if state and predicate(state):
            return state, True
        time.sleep(0.2)
    return state, False


def rows(session, start):
    record = evaluate(session, "window.__f2")
    replies = {r.get("requestId"): r for r in record["responses"]}
    out = []
    for q in record["requests"][start:]:
        if q.get("operation") != "editorActionV2":
            continue
        payload = q.get("payload") or {}
        reply = replies.get(q.get("requestId")) or {}
        result, error = reply.get("result") or {}, reply.get("error") or {}
        out.append({"action": payload.get("action"), "enabled": payload.get("enabled"),
                    "ok": reply.get("ok"), "code": error.get("code"), "message": error.get("message"),
                    "changed": result.get("changed"), "completion": result.get("completion"),
                    "witness": result.get("witness"), "hasWitness": "witness" in result,
                    "revision": [result.get("beforeRevision"), result.get("revision")]})
    return out


def judge(run):
    """(pass, why) for one run, from the recorded rows and page only."""
    why = []
    got = [r["action"] for r in run.get("rows", [])]
    if got != FORMAT_ACTIONS:
        why.append(f"requests {got}")
    for r in run.get("rows", []):
        if r["enabled"] is not False:
            why.append(f"{r['action']} enabled={r['enabled']!r}")
        if not (r["ok"] is True and r["changed"] is True and r["completion"] == "uno-command-result"):
            why.append(f"{r['action']} ok={r['ok']} code={r['code']} changed={r['changed']} completion={r['completion']}")
        elif r["witness"] not in WITNESSES:
            why.append(f"{r['action']} witness={r['witness']!r}")
    if run.get("rows") and run["rows"][0]["action"] == "set-bold" and run["rows"][0]["witness"] != "state-noop":
        why.append(f"set-bold witness {run['rows'][0]['witness']!r}, not state-noop: the no-op path was not exercised")
    if not run.get("warmupHeld"):
        why.append("warm-up press did not end in 已清除 and ready")
    after = run.get("after") or {}
    if not (after.get("toast") or "").startswith("已清除"):
        why.append(f"toast {after.get('toast')!r}")
    if after.get("pill") != "ready":
        why.append(f"pill {after.get('pill')!r}")
    return not why, why


def red_for_172(run):
    first = (run.get("rows") or [{}])[0]
    return (not run.get("fatal") and run.get("warmupHeld") is True
            and first.get("action") == "set-bold" and first.get("ok") is False
            and first.get("code") == "LOK_COMMAND_FAILED")


def one(session, base):
    navigate(session, base)
    _, ok = wait(session, lambda s: s["pill"] == "ready", 240)
    if not ok:
        return {"fatal": "not ready"}
    evaluate(session, pp.POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
    _, placed = wait(session, lambda s: "定位游標" in (s["latency"] or ""), 60)
    presses = []
    for _ in range(2):
        before = evaluate(session, PAGE)
        evaluate(session, pp.CLEAR_TOAST)
        evaluate(session, pp.CLEAR_LATENCY)
        evaluate(session, pp.CLEAR_FORMAT)
        _, settled = wait(session, lambda s: (s["toast"] or "").startswith("已清除") or "清除格式：" in (s["toast"] or "")
                          or s["pill"] in ("recoverable-error", "restart-required"), 60)
        time.sleep(1.0)
        presses.append({"settled": settled, "before": before, "after": evaluate(session, PAGE),
                        "rows": rows(session, before["requests"])})
    warmup, judged = presses
    held = (warmup["after"]["pill"] == "ready" and (warmup["after"]["toast"] or "").startswith("已清除")
            and [r["action"] for r in warmup["rows"]] == FORMAT_ACTIONS and all(r["ok"] for r in warmup["rows"]))
    return {"caretPlaced": placed, "warmup": warmup, "warmupHeld": held, **judged}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--products", default="v24,v25")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    browsers = [b for b in args.browsers.split(",") if b]
    names = [n for n in args.products.split(",") if n]
    report = {"argv": sys.argv, "tool": "check_v25_clear_format_noop", "products": {}, "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="f2-clear-format-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("check_v25_clear_format_noop"):
            report["preRun"] = common.pre_run_checks()
            if report["preRun"]["refuse"]:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            for name in names:
                mirror = scratch / name
                pp.build_mirror(common.DIST, mirror, products.overrides(name, [OBSERVER]))
                report["products"][name] = products.identity(name, mirror)
                if not report["products"][name]["ok"]:
                    print(name, "identity FAILED, not run", file=sys.stderr, flush=True)
                    continue
                with common.served(mirror) as base:
                    for browser in browsers:
                        for n in range(1, args.repetitions + 1):
                            run, session = {"product": name, "browser": browser, "repetition": n}, None
                            try:
                                session = common.open_browser(browser)
                                run["browserVersion"] = getattr(session, "version", None)
                                run.update(one(session, base))
                            except Exception:  # noqa: BLE001 -- recorded
                                run["fatal"] = traceback.format_exc()
                            finally:
                                if session is not None:
                                    run["cleanup"] = common.close_browser(session)
                            run["pass"], run["why"] = judge(run)
                            run["redFor172"] = red_for_172(run)
                            report["runs"].append(run)
                            print(name, browser, n, "PASS" if run["pass"] else "red", "/".join(run["why"])[:160],
                                  file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    v25 = [r for r in report["runs"] if r["product"] == "v25"]
    v24 = [r for r in report["runs"] if r["product"] == "v24"]
    expected = len(browsers) * args.repetitions
    problems = []
    for name in names:
        if not report["products"].get(name, {}).get("ok"):
            problems.append(f"{name}: identity failed")
    if "v25" in names and not (len(v25) == expected and all(r["pass"] for r in v25)):
        problems.append(f"v25: {sum(r['pass'] for r in v25)}/{expected} PASS")
    if "v24" in names and not (len(v24) == expected and all(r["redFor172"] and not r["pass"] for r in v24)):
        problems.append(f"v24: {sum(r['redFor172'] for r in v24)}/{expected} red for 172")
    if set(names) != {"v24", "v25"}:
        problems.append("a verdict needs both products: v25 to pass and v24 as the counterexample")
    report["problems"] = problems
    report["verdict"] = "F2_HOLDS" if not problems else "F2_RED"
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], problems, file=sys.stderr)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
