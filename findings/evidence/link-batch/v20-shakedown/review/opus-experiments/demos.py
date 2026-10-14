#!/usr/bin/env python3
"""Opus seat, v20 judge review: each demo copies the committed reports, applies one mutation that an
honest run of the committed runner could produce (unless marked otherwise), runs the committed judge
(HEAD, extracted to ./head), and prints the verdict line(s)."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "head" / "wasm_sdk_probe" / "tools"))
sys.dont_write_bytecode = True
import judge_v20_shakedown as J  # noqa: E402
import run_v20_shakedown as R  # noqa: E402

PAGE = "53019168651b6b4686f1baaba9aa75e0b566d02a3e2cc8a8e8ed4339f360bfd7"
REPORTS = {p.name: json.loads(p.read_text()) for p in sorted((HERE / "reports").glob("report-*.json"))}


def run(name, mutate, extra=None, expect_page=PAGE):
    reps = copy.deepcopy(REPORTS)
    mutate(reps)
    if extra:
        reps.update(extra(reps))
    ordered = [reps[k] for k in sorted(reps)]   # load_reports' order: sorted file names
    code, lines = J.judge_reports(ordered, expect_page)
    cells = [l for l in lines if l.startswith("[") and not l.startswith("    ")]
    print(f"### {name}")
    for l in cells:
        if not l.endswith(": PASS") and "PASS (" not in l and "p2c" not in l:
            print("   ", l)
    print("   ", lines[-1], "exit", code)
    return code


# --- D1: a FAIL and a later PASS for the same (browser, arm): last file in sort order wins.
def d1(reps):
    bad = reps["report-chrome-main.json"]["results"]["p1-60"]
    bad["positions"][5]["text"] = "第 7 頁，共 60 頁"   # a real FAIL in the first run
def d1_extra(reps):
    rerun = copy.deepcopy(REPORTS["report-chrome-main.json"])   # an honest green re-run of the same arms
    rerun["results"] = {"p1-60": rerun["results"]["p1-60"]}
    rerun["arms"] = ["p1-60"]
    return {"report-chrome-p1rerun.json": rerun}


# --- D1b: the reverse order masks a PASS with... (control: FAIL last -> FAIL)
def d1b_extra(reps):
    rerun = copy.deepcopy(REPORTS["report-chrome-main.json"])
    rerun["results"] = {"p1-60": copy.deepcopy(rerun["results"]["p1-60"])}
    rerun["results"]["p1-60"]["positions"][5]["text"] = "第 7 頁，共 60 頁"
    return {"report-chrome-p1rerun.json": rerun}


# --- D2: the E2 hold raised (caught inside arm_e2: out["hold"] = {"error": ...}); 5 cases judged.
def d2(reps):
    reps["report-chrome-main.json"]["results"]["e2"]["hold"] = {"error": "TimeoutError: CDP Input.dispatchKeyEvent"}


# --- D3: runner killed during E2 (last FLUSH after case 2): no hold, 2 of 5 cases, no completedAt.
def d3(reps):
    r = reps["report-chrome-main.json"]
    e2 = r["results"]["e2"]
    r["results"]["e2"] = {"arm": "e2", "cases": e2["cases"][:2], "hold": None}
    for k in ("completedAt", "observerAtEnd"):
        r.pop(k, None)


# --- D4: 4 of 5 cases placement-mismatch (honest runner outcome) and the hold produced no refusal.
def d4(reps):
    e2 = reps["report-chrome-main.json"]["results"]["e2"]
    for c in e2["cases"][1:]:
        for k in ("judge", "pass", "answer", "e3Record", "reopen"):
            c.pop(k, None)
        c["outcome"] = "placement-mismatch"
    e2["hold"] = {k: v for k, v in e2["hold"].items() if k not in ("judge", "pass")}
    e2["hold"]["outcome"] = "hold-reached-no-refusal"


# --- D5: the hold's first press is the refusal (no merge crossed): §10.6's hold is vacuous, still judged.
def d5(reps):
    h = reps["report-chrome-main.json"]["results"]["e2"]["hold"]
    h["deleteAnswers"] = [d for d in h["deleteAnswers"] if not d["ok"]]
    h["merges"] = 0


# --- D6: C1, the engine's FRESH read says a selection exists (selectionType "text") while the callback
# cache (selection.collapsed/rectangles, appendEditorState) is still collapsed.  The clause is the
# runner's own expression (run_v20_shakedown.py:834), evaluated on that input.
def c1_clause(asked):
    result = (asked.get("result") or {})
    sel = result.get("sel") or {}
    return asked.get("ok") is True and sel.get("collapsed") is True and (sel.get("n") or 0) == 0
def d6(reps):
    rd = reps["report-chrome-main.json"]["results"]["c1"]["rounds"][0]
    rd["engineRead"]["result"]["selectionType"] = "text"
    rd["clauses"]["noSelectionAt500ms"] = c1_clause(rd["engineRead"])


# --- D7: C1, a non-reopen toast after the noop.  The clause is the runner's (run_v20_shakedown.py:835).
REOPENED, STARTING = "已重新載入", "，正在重新載入…"
def toast_clause(toasts):
    return not any(REOPENED in (t or "") or STARTING in (t or "") for t in toasts)
def d7(reps):
    rd = reps["report-chrome-main.json"]["results"]["c1"]["rounds"][0]
    rd["toastsAfterKey"] = rd["toastsAfterKey"][1:] + ["EDITOR_BOUNDARY_UNSUPPORTED：游標已在文件開頭"]
    rd["clauses"]["noReopenToast"] = toast_clause(rd["toastsAfterKey"])


# --- D8: P1-60 on a page that never re-reads after the lazy first reply (1 part, P2-c measured it):
# the runner builds its positions from the page's only reply, so expectation and text agree on M=1.
def d8(reps):
    p1 = reps["report-chrome-main.json"]["results"]["p1-60"]
    raw = p1["reply"]["raw"].split(";")[0]
    p1["reply"] = {"parts": 1, "count": 1, "docW": 12474, "docH": 17406, "raw": raw}
    p1["positions"] = [{"kind": "centre", "page": 1, "yTwips": 8703, "expected": "第 1 頁，共 1 頁",
                        "text": "第 1 頁，共 1 頁", "hidden": False, "pass": True}]
    p1["partsEqualsCount"] = True


# --- D9: no --expect-page: a report about another page (v19 repoint) is judged and passes.
def d9(reps):
    reps["report-firefox-main.json"]["identity"]["pageServedSha256"] = "0" * 64


# --- D10: the served worker is not the profile's (stale dist/ copy, edited worker) and not declared
# instrumented: no identity rule reads workerServedSha256 or profileHashes.
def d10(reps):
    # what the committed runner writes when dist/profiles/e2-editor-v20/sdk-worker.js is stale or edited
    # (34.2 "dist/ 過期"): both fields hash the same file, the page sha (profile name + the manifest's
    # declared wasm hash) is unchanged.
    ident = reps["report-chrome-main.json"]["identity"]
    ident["workerServedSha256"] = "f" * 64
    ident["profileHashes"]["sdk-worker.js"] = "f" * 64
    ident["profileHashes"]["probe.js"] = "e" * 64


# --- D11: C1 clause dict lost a key (a runner revision that stops writing one): the judge iterates
# whatever clauses exist.
def d11(reps):
    for rd in reps["report-chrome-main.json"]["results"]["c1"]["rounds"]:
        rd["engineRead"]["result"]["sel"] = {"collapsed": False, "n": 2, "observed": True}
        del rd["clauses"]["noSelectionAt500ms"]


# --- D12: report says counted: true (a counted run) -- prints a line, exit unaffected.
def d12(reps):
    reps["report-chrome-main.json"]["counted"] = True


if __name__ == "__main__":
    run("baseline (committed reports)", lambda r: None)
    run("D1 FAIL in report-chrome-main + green re-run report-chrome-p1rerun", d1, d1_extra)
    run("D1-control: same pair, the FAIL in the file that sorts last", lambda r: None, d1b_extra)
    run("D2 E2 hold raised (runner catches it), 5 cases judged", d2)
    run("D3 runner killed during E2 after case 2 (no hold, no completedAt)", d3)
    run("D4 E2: 4/5 placement-mismatch, hold without refusal", d4)
    run("D5 E2 hold: first press refused, merges 0", d5)
    print("    D6 clause value:", c1_clause({"ok": True, "result": {"sel": {"collapsed": True, "n": 0},
                                                                  "selectionType": "text"}}))
    run("D6 C1 engine fresh read selectionType 'text', cache collapsed", d6)
    print("    D7 clause value:", toast_clause(["已開啟 c1-C29-r1.odt", "EDITOR_BOUNDARY_UNSUPPORTED：游標已在文件開頭"]))
    run("D7 C1 an error toast after the noop (no reopen)", d7)
    run("D8 P1-60 built from the lazy 1-part reply", d8)
    run("D9 another page, judged WITHOUT --expect-page", d9, expect_page=None)
    run("D9-control: same, WITH --expect-page", d9)
    run("D10 stale dist/ worker+loader (profileHashes and workerServedSha256 not v20's), same page sha", d10)
    run("D11 (outside 34.2: a runner revision) C1 clause dropped, selection present", d11)
    run("D12 counted: true", d12)
