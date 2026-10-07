#!/usr/bin/env python3
"""Paragraph merge (option B) on WASM: the uncounted shakedown (runbook v15 section
4 step 1; SPEC-M3-paragraph-merge 4.3 as amended in 10.2, 14.4, 17, 18, 20).

Written 2026-10-07.  NOT a counted M2 run: the design has not been through its
adversarial review, and the page is INSTRUMENTED (below), so every report says
`"counted": false` and `"instrumented": true`.

What it drives, per case, on the standalone product page pointed at a candidate
profile (the page `build_cutover_page.py` would produce, by the runner's own
`repointed_page`), Chrome or Firefox:

  1. open the fixture through the product's file input;
  2. refusal cases only: type a marker at a native caret OF THE SAME FIXTURE
     (`MARKER_AT`: boundaries.odt the end of "M01 plain alpha", text-frame.odt
     the start of "F01 frame second"; spec M2-3: it must survive the refusal's
     reopen, 109's guarantee).  A marker that cannot be placed ends the case as
     `marker-placement-mismatch`: its reopen check would say nothing;
  3. PLACE: click at the native caret of that case (R0c's `placed.cursor`, in
     twips, turned into canvas fractions -- the canvas is the whole document),
     then a real End (forward) or Home (backward); the engine's caret must then
     EQUAL the native one, or the key is not pressed and the case is recorded
     as `placement-mismatch` (a wrong boundary would also show as a different
     document; this makes it say so before the key instead of after);
  4. wait until the input adapter is empty (finding 111 is not this round's
     subject), then the REAL key (Chrome: CDP Input.dispatchKeyEvent; Firefox:
     WebDriver actions).  Y01: a real `x` and the key at once (M2-1b's shape);
  5. outcome from the instrument: `verified-key-undo` + `keyUndo`, or a refusal
     with `mergeKey.{stage, keyPosted}`; the worker generation (`#s-generation`,
     the page's own) says whether the session was reopened;
  6. merges: save (the product's button), then a real `Z` and save again; the two
     `content.xml` are compared with the native key arm `r1-<case>-key.odt` and
     `r1-<case>-key-follow.odt` (bytes, and paragraph text; Y01 by paragraph
     text only).  Refusals: after the reopen, save; the paragraph text must be
     the original's plus the marker, and the toast for `keyPosted:true` must not
     say 「沒有被改動」.

M2-0 runs first per fixture: load and save with no edit, `content.xml` against
native `original.odt`.  Every document the page saves is KEPT, under
`<report stem>.docs/`, so the M2-0 diff (and any later reduction) is read from
the bytes rather than from a hash of them.  When they differ, the merge comparisons report the
byte result anyway and the paragraph-text result beside it; no reduction is
invented here (spec 4.3: a reduction is derived from that diff, in the spec).

THE INSTRUMENT.  The product page publishes no handle, and nothing it shows
says `verified-key-undo`.  So the served HTML gets one classic script before
the page's module: it wraps the `Worker` constructor, adds a `message` listener
to the document worker (behaviour unchanged: a second listener), and writes
into a hidden DOM node what it saw -- responses carrying `keyUndo`,
`mergeKey` or `completion`, the last `editor-state` caret, the document size.
DOM, not a page global: Firefox evaluates in a Marionette sandbox.

  run_merge_wasm_shakedown.py --browser chrome --out REPORT.json
      [--candidate-profile e2-editor-v16] [--cases C01,C02,...] [--rounds 1]
"""
from __future__ import annotations

import argparse
import base64
import functools
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import odt_paragraphs  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

HERE = pp.PROJECT
EVIDENCE = HERE.parent / "findings/evidence/merge-native"
ESHAPE = EVIDENCE / "r0c/eshape.json"
PMPC_ROUND = HERE / "build/merge-native-pmpc/r0c/round-20261006T150756Z"
# name -> (fixture, R0c round directory with arms.jsonl and docs/, the round's
# key in eshape.json or None, private).  The three eshape.json rounds are the
# M2-1/M2-3 population (spec 22.1); text-frame is the registered one-time cell
# (22.2) and is read through the native reader instead.  PRIVATE: the owner's
# document -- read from build/ only, kept documents go to build/, and the
# report carries hashes and paragraph indices, never paragraph text.
FIXTURES = {
    "boundaries": (HERE / "test-docs/merge/odt/boundaries.odt",
                   EVIDENCE / "r0c/round-20261006T144628Z", "round-20261006T144628Z", False),
    "boundaries-indent": (HERE / "test-docs/merge/odt/boundaries-indent.odt",
                          EVIDENCE / "r0c/round-20261006T150437Z", "round-20261006T150437Z", False),
    "pmpc": (PMPC_ROUND / "fixture.odt", PMPC_ROUND, "round-20261006T150756Z", True),
    "text-frame": (HERE / "test-docs/merge/odt/text-frame.odt",
                   EVIDENCE / "r0c-frame/round-20261007T060036Z", None, False),
}
FRAME_CELL = ("F01", "F02")
# The one STOP the native reader prints for the frame round, and why it is
# expected: that round has only merge cases, so every other decision class is
# empty.  Any other STOP, or a KILL, stops this runner.
FRAME_STOPS = ["vacuous: a decision class never occurred {'merge': 6}"]
# Spec 22.2: inside a text frame the fence refuses every merge (18.1 N1).  A
# registered one-time cell, outside the M2-1/M2-3 lists, valid only while the
# native decision there is still `merge`.
FRAME_EXPECT = ("refused", "anchor-mismatch", False)
# Where refusal arms type the marker: a native caret IN THE FIXTURE UNDER TEST,
# and not the case's own.  It was C01's for every fixture, a boundaries.odt
# coordinate.  In the frame, F01 (the end of "F01 frame first") and F02 (the
# start of "F01 frame second") are on different lines, so each marks the
# other's.  Backward cases are placed with Home, so the marker goes in FRONT
# of the paragraph's text; forward ones with End, after it.  Hand-picked
# (review N7): a fixture with a refusal case and no entry here stops the run.
MARKER_AT = {"boundaries": ("C01",), "text-frame": ("F02", "F01")}
MARKER = "mk"
# Where the page's saved documents are kept (set in main()); `private` for the
# owner's document, under build/.
DOCS: dict = {"dir": None, "private": None}
UNCHANGED = "沒有被改動"
DELETE_ACTIONS = ("delete-forward", "delete-backward")
# R0c's decision -> what v16 must do and which criterion counts it (spec 17,
# 22.1).  Anything else STOPS the runner: before the review a decision with no
# entry (G01's `barrier`, any `refused-k2-*`) got no expectation and passed
# silently.
def expectation(decision: str | None) -> tuple[str, tuple]:
    if decision in ("merge", "typed-merge"):
        return "M2-1", ("verified-key-undo", None, None)
    if decision == "barrier":
        return "barrier", ("verified-selection-delete", None, None)
    if decision == "nothing-selected":
        return "M2-3", ("refused", "nothing-selected", False)
    if decision and decision.startswith("refused-k1-"):
        return "M2-3", ("refused", "anchor-mismatch", False)
    if decision and decision.startswith("refused-k2-"):
        return "M2-3", ("refused", "return-mismatch", False)
    if decision == "key-noop":
        return "M2-3", ("refused", "key-deadline", True)
    raise SystemExit(f"no expectation for the R0c decision {decision!r}; spec 22.1 says stop")


# The instrument (spec 22.2 on its cost and on what only it can see).  Since the
# review of 5555e554: a bounded record written OUTSIDE the message handler
# (setTimeout, so the SDK's own listener for the same message is not delayed by
# a JSON.stringify of everything seen so far), and EVERY failed editor action is
# recorded -- before, an error was kept only if it carried keyUndo/mergeKey/
# completion, so v8's refusal (no mergeKey) read as `no-response`.  Responses
# carry only a requestId, so outgoing requests are mapped to their operation
# (and an editor action to its action name) on the way out; a failed paint
# (BUSY during a barrier) is therefore never taken for the delete's answer.
OBSERVER = r"""<script>
(() => {
  const Native = window.Worker;
  const KEEP = 64;
  const obs = { workers: 0, responses: [], responsesSeen: 0, caret: null, carets: 0,
                size: null };
  const node = document.createElement("script");
  node.type = "application/json"; node.id = "merge-observer";
  let queued = false;
  const flush = () => { queued = false; node.textContent = JSON.stringify(obs); };
  const later = () => { if (!queued) { queued = true; setTimeout(flush, 0); } };
  document.addEventListener("DOMContentLoaded", () => { document.head.appendChild(node); flush(); });
  function seen(data, generation, requests) {
    if (!data || typeof data !== "object") return;
    if (data.kind === "event" && data.event === "editor-state" && data.caret) {
      obs.caret = { generation, t: performance.now(), caret: data.caret,
                    sourceSequence: data.sourceSequence ?? null };
      obs.carets += 1; later(); return;
    }
    if (data.kind !== "response") return;
    const request = requests.get(data.requestId) || {};
    requests.delete(data.requestId);
    const value = data.ok ? data.result : data.error;
    if (value && typeof value === "object") {
      let size = null;
      if (typeof value.width === "number" && typeof value.height === "number"
          && value.documentHandle !== undefined)
        size = { w: value.width, h: value.height, from: "open" };
      if (typeof value.documentWidthTwips === "number")
        size = { w: value.documentWidthTwips, h: value.documentHeightTwips, from: "paint" };
      if (size && (!obs.size || obs.size.w !== size.w || obs.size.h !== size.h
                   || obs.size.generation !== generation)) {
        obs.size = { ...size, generation }; later();
      }
    }
    const editor = /^editorAction/.test(request.operation || "");
    const marked = value && typeof value === "object"
      && (value.keyUndo || value.mergeKey || value.completion);
    if (!(marked || (editor && !data.ok))) return;
    obs.responses.push({ n: obs.responsesSeen, t: performance.now(), generation, ok: data.ok,
      operation: request.operation ?? null,
      action: request.action ?? value?.action ?? null,
      completion: value?.completion ?? null, keyUndo: value?.keyUndo ?? null,
      code: value?.code ?? null, message: value?.message ?? null,
      mergeKey: value?.mergeKey ?? value?.details?.mergeKey ?? null });
    obs.responsesSeen += 1;
    if (obs.responses.length > KEEP) obs.responses.shift();
    later();
  }
  function Wrapped(url, options) {
    const worker = new Native(url, options);
    if (options && options.name === "oxoffice-document-engine") {
      obs.workers += 1;
      const generation = obs.workers;
      const requests = new Map();
      const post = worker.postMessage.bind(worker);
      worker.postMessage = (message, transfer) => {
        if (message && message.kind === "request")
          requests.set(message.requestId, { operation: message.operation,
                                            action: message.payload?.action });
        return post(message, transfer);
      };
      worker.addEventListener("message", (event) => {
        try { seen(event.data, generation, requests); }
        catch (error) { obs.error = String(error); later(); }
      });
      later();
    }
    return worker;
  }
  Wrapped.prototype = Native.prototype;
  window.Worker = Wrapped;
})();
</script>
"""
READ_OBS = "(() => { const n = document.getElementById('merge-observer'); return n ? n.textContent : null; })()"
NOW = "(() => performance.now())()"
GEN = "(() => document.querySelector('#s-generation').textContent)()"

CDP_KEYS = {"Delete": ("Delete", "Delete", 46), "Backspace": ("Backspace", "Backspace", 8),
            "End": ("End", "End", 35), "Home": ("Home", "Home", 36)}
WD_KEYS = {"Delete": "", "Backspace": "", "End": "", "Home": ""}


def press(session, browser: str, key: str) -> None:
    """One real key: a name in CDP_KEYS, or one lowercase/uppercase letter."""
    if browser == "chrome":
        if key in CDP_KEYS:
            name, code, vk = CDP_KEYS[key]
            phases, text = ("rawKeyDown", "keyUp"), None
        else:
            name, code, vk, text = key, f"Key{key.upper()}", ord(key.upper()), key
            phases = ("rawKeyDown", "char", "keyUp")
        for phase in phases:
            params = {"type": phase, "key": name, "code": code,
                      "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk,
                      "modifiers": 8 if (text and text.isupper()) else 0}
            if phase == "char":
                params["text"] = text
            session.call("Input.dispatchKeyEvent", params)
        return
    value = WD_KEYS.get(key, key)
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": [
        {"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}]}]})
    session.command("DELETE", "/actions")


def obs(session) -> dict:
    raw = pp.evaluate(session, READ_OBS)
    return json.loads(raw) if raw else {}


def state(session) -> dict:
    return pp.evaluate(session, pp.READ_STATE) or {}


def quiet(session, limit: float = 30) -> dict:
    """Ready with an empty queue for half a second (the input adapter is empty)."""
    deadline, since, seen = time.monotonic() + limit, None, {}
    while time.monotonic() < deadline:
        seen = state(session)
        if seen.get("state") == "ready" and str(seen.get("pending")) == "0":
            since = since or time.monotonic()
            if time.monotonic() - since >= 0.5:
                return seen
        else:
            since = None
        time.sleep(0.15)
    return {**seen, "timedOut": True}


def caret_tuple(record) -> list | None:
    caret = (record or {}).get("caret")
    if not isinstance(caret, dict):
        return None
    keys = ("x", "y", "width", "height")
    return [caret.get(k) for k in keys] if all(k in caret for k in keys) else None


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def top_undo_comment(row: dict) -> str | None:
    """The newest undo action's comment in a native arm (index 0 is the newest)."""
    after = row.get("undoAfter")
    after = json.loads(after) if isinstance(after, str) else (after or {})
    actions = json.loads(after.get("actions") or "{}").get("actions") or []
    newest = [a for a in actions if str(a.get("index")) == "0"]
    return newest[0].get("comment") if newest else None


@functools.lru_cache(maxsize=None)
def native_cases(fixture: str) -> dict:
    """Per case: native placed cursor, direction, R0c decision, reference documents.

    Bound, not assumed: the fixture served must be the round's own fixture.odt,
    and the decisions come from eshape.json (its KILL/STOP lists must be empty)
    or, for the frame round, from the native reader with only its one expected
    STOP.
    """
    path, round_dir, round_key, private = FIXTURES[fixture]
    arms = round_dir / "arms.jsonl"
    if not path.is_file() or not arms.is_file():
        raise SystemExit(f"{fixture}: {path} or {arms} is missing")
    if (round_dir / "fixture.odt").is_file() and sha256_of(round_dir / "fixture.odt") != sha256_of(path):
        raise SystemExit(f"{fixture}: {path} is not the fixture R0c ran ({round_dir}/fixture.odt)")
    rows = [json.loads(line) for line in arms.read_text().splitlines() if line.strip()]
    if round_key is not None:
        table = json.loads(ESHAPE.read_text())
        if table["kills"] or table["stops"]:
            raise SystemExit(f"{ESHAPE}: KILL {table['kills']} STOP {table['stops']}")
        decided = {key.split(" ", 1)[1]: value for key, value in table["cases"].items()
                   if key.split(" ", 1)[0] == round_key}
    else:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "eshape.json"
            subprocess.run([sys.executable, str(HERE / "tools/check_merge_eshape.py"), "--json",
                            str(target), str(round_dir)], capture_output=True, text=True)
            verdict = json.loads(target.read_text())
        if verdict["kills"] or verdict["stops"] != FRAME_STOPS:
            raise SystemExit(f"{round_dir.name}: native reader KILL {verdict['kills']} "
                             f"STOP {verdict['stops']} (only {FRAME_STOPS} is expected)")
        decided = {key.split(" ", 1)[1]: value for key, value in verdict["cases"].items()}
    comments = {row["case"]: top_undo_comment(row) for row in rows
                if row.get("round") == 1 and row.get("arm") == "key"}
    cases = {}
    for row in rows:
        if row.get("round") != 1 or row.get("arm") != "select":
            continue
        placed = row.get("placed") or {}
        placed = json.loads(placed) if isinstance(placed, str) else placed
        cursor = [int(v) for v in (placed.get("cursor") or "").split(",")]
        cases[row["case"]] = {"fixture": fixture, "private": private,
                              "backward": bool(row.get("backward")),
                              "nativeCaret": cursor, "search": row.get("search"),
                              "decision": decided.get(row["case"]),
                              "nativeComment": comments.get(row["case"]),
                              "original": round_dir / "docs" / "original.odt",
                              "key": round_dir / "docs" / f"r1-{row['case']}-key.odt",
                              "follow": round_dir / "docs" / f"r1-{row['case']}-key-follow.odt"}
    if not cases or set(cases) != set(decided):
        raise SystemExit(f"{fixture}: R0c select arms {sorted(cases)} and decisions "
                         f"{sorted(decided)} do not match")
    return cases


def tool_cases(frame_cell: bool) -> dict:
    """The M2-1/M2-3 population (spec 22.1), plus the frame cell when asked."""
    out = {}
    for fixture, (_, _, round_key, _) in FIXTURES.items():
        if round_key is None and not frame_cell:
            continue
        for case, spec in native_cases(fixture).items():
            if round_key is None:
                if spec["decision"] != "merge":
                    raise SystemExit(f"{case}: the frame cell assumes the native decision "
                                     f"`merge`, R0c-frame says {spec['decision']!r} (spec 22.2)")
                out[case] = {**spec, "criterion": "frame", "expected": FRAME_EXPECT}
                continue
            criterion, expected = expectation(spec["decision"])
            if expected[0] == "refused" and fixture not in MARKER_AT:
                raise SystemExit(f"{case}: a refusal case in {fixture}, which has no marker place")
            out[case] = {**spec, "criterion": criterion, "expected": expected}
    return out


def odt_parts(raw: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        content = archive.read("content.xml")
    paragraphs = odt_paragraphs.paragraph_texts_from_xml(content)
    return {"content": content, "sha": hashlib.sha256(content).hexdigest()[:16],
            "paragraphs": paragraphs}


def compare(raw: bytes | None, reference: Path, private: bool) -> dict:
    """content.xml against a native document: bytes and paragraph text.

    `bytesEqual` is reported but is not a clause until M2-0's reduction is in
    the spec (4.3).  A private fixture reports indices and hashes, never text.
    """
    if raw is None:
        return {"saved": False}
    mine, theirs = odt_parts(raw), odt_parts(reference.read_bytes())
    first = next((i for i, (a, b) in enumerate(zip(mine["paragraphs"], theirs["paragraphs"]))
                  if a != b), None)
    out = {"saved": True, "reference": reference.name,
           "bytesEqual": mine["content"] == theirs["content"],
           "textEqual": mine["paragraphs"] == theirs["paragraphs"],
           "mine": mine["sha"], "theirs": theirs["sha"],
           "paragraphs": [len(mine["paragraphs"]), len(theirs["paragraphs"])],
           "firstTextDifference": first}
    if first is not None and not private:
        out["firstTextDifferenceText"] = [mine["paragraphs"][first], theirs["paragraphs"][first]]
    return out


def save(session, name: str, private: bool) -> bytes | None:
    """The product's save; the bytes are kept as `<DOCS>/<name>.odt`."""
    index = pp.evaluate(session, pp.SAVE_COUNT) or 0
    pp.evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
    if not pp.wait_saves(session, index + 1, 60):
        return None
    saved = pp.evaluate(session, pp.READ_SAVE.replace("ARG_INDEX", str(index)))
    raw = base64.b64decode(saved["b64"]) if saved else None
    folder = DOCS["private" if private else "dir"]
    if raw is not None and folder is not None:
        target = folder / f"{name}.odt"
        if target.exists():
            raise SystemExit(f"refusing to overwrite a kept document: {target}")
        target.write_bytes(raw)
    return raw


def open_fixture(session, url: str, name: str) -> dict:
    pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", url).replace("ARG_NAME", name))
    opened = pp.wait_for(session, lambda s: (s.get("doc") or "") == name and s.get("state") == "ready", 120)
    return {"opened": bool(opened), "settled": quiet(session)}


def place(session, browser: str, target: list[int], backward: bool) -> dict:
    """Click at the native caret, then End/Home; the engine's caret must equal it.

    The caret and the document size must come from the CURRENT worker (review
    S5): right after an open the last caret seen can be the previous worker's,
    and if it happened to equal the target the key would go out unplaced.
    """
    seen = obs(session)
    current, size = seen.get("workers"), seen.get("size") or {}
    if not size.get("w") or not size.get("h") or size.get("generation") != current:
        return {"ok": False, "why": "no document size from the current worker", "size": size,
                "workers": current}

    def at_target(record) -> bool:
        caret = caret_tuple(record)
        return (bool(caret) and (record or {}).get("generation") == current
                and caret[:2] == target[:2] and caret[3] == target[3])

    x, y, _, height = target
    fx = (x + (-40 if not backward else 40)) / size["w"]
    fy = (y + height / 2) / size["h"]
    before = seen.get("carets") or 0
    pp.evaluate(session, pp.POINT_AT.replace("ARG_X", f"{fx:.6f}").replace("ARG_Y", f"{fy:.6f}"))
    pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 30)
    quiet(session)
    time.sleep(0.3)
    clicked_record = obs(session).get("caret")
    # A click that already lands on the native caret needs no key: Home at the
    # start of a numbered or bulleted paragraph moves IN FRONT OF the label
    # (measured on C11: x 1778 against the native 2138), which is not where
    # the native round placed it.
    keyed = not at_target(clicked_record)
    if keyed:
        press(session, browser, "Home" if backward else "End")
        time.sleep(0.4)
        quiet(session)
    deadline, record = time.monotonic() + 5, None
    while time.monotonic() < deadline:
        seen = obs(session)
        record = seen.get("caret")
        if (seen.get("carets") or 0) > before and at_target(record):
            break
        time.sleep(0.2)
    return {"ok": at_target(record), "click": [round(fx, 6), round(fy, 6)], "size": size,
            "keyed": keyed, "afterClick": caret_tuple(clicked_record),
            "engineCaret": caret_tuple(record), "caretGeneration": (record or {}).get("generation"),
            "workers": current, "nativeCaret": target}


# The reopen's own last sentence (e2-editor-app.js reopenAfterBoundaryRefusal),
# or the generation ceiling's, which ends the flow without a restart.
REOPENED, AT_LIMIT = "已重新載入", "不能再重新載入"


def toast_window(session, gen_before: str, limit: float = 90) -> dict:
    """Spec 22.1 (B4): the window closes on the reopen's own end, not on a timer.

    Closed when the generation has moved AND the final sentence is shown, or
    when the ceiling's sentence is (that path does not restart).  Not closed
    within `limit` seconds: the case fails, it is not read early.
    """
    deadline = time.monotonic() + limit
    generation, toasts = gen_before, []
    while time.monotonic() < deadline:
        generation = pp.evaluate(session, GEN)
        toasts = pp.evaluate(session, pp.READ_TOASTS) or []
        if any(AT_LIMIT in (t or "") for t in toasts) or (
                generation != gen_before and any(REOPENED in (t or "") for t in toasts)):
            return {"closed": True, "generation": generation, "toasts": toasts}
        time.sleep(0.2)
    return {"closed": False, "generation": generation, "toasts": toasts}


def merge_clauses(out: dict, spec: dict) -> dict:
    """Spec 22.1, every clause on its own (None = not established yet)."""
    key_undo = out.get("keyUndo") or {}
    clauses = {"outcome": out.get("outcome") == spec["expected"][0],
               "generation": out["generation"][0] == out["generation"][1],
               "afterKeyText": (out.get("afterKeyDocument") or {}).get("textEqual") is True,
               # M2-0: WASM and native differ with no edit, so bytes wait for
               # the reduction appended to the spec (4.3).
               "afterKeyBytes": None,
               "followText": (out.get("followDocument") or {}).get("textEqual") is True,
               "noToast": out.get("toasts") == []}
    if spec["criterion"] == "M2-1":
        clauses["comment"] = (key_undo.get("comment") is not None
                              and key_undo.get("comment") == spec["nativeComment"])
        clauses["restorePresses"] = key_undo.get("restorePresses") == 0
    return clauses


def refusal_clauses(out: dict, spec: dict, expected_text: list | None, mine: list | None) -> dict:
    """Spec 22.1 and 22.2 (the narrowed M2-3), every clause on its own."""
    _, stage, posted = spec["expected"]
    window = out.get("toastWindow") or {}
    toasts = window.get("toasts") or []
    before = out.get("beforeKey") or {}
    after = out.get("afterKey") or {}
    try:
        reopened = str(int(out["generation"][0]) + 1)
    except (TypeError, ValueError):
        reopened = None
    clauses = {"outcome": out.get("outcome") == "refused",
               "stage": out.get("stage") == stage,
               "keyPosted": out.get("keyPosted") == posted,
               "generation": reopened is not None and window.get("generation") == reopened,
               "toastWindowClosed": window.get("closed") is True,
               "reopenedText": mine is not None and mine == expected_text,
               "markerSurvived": mine is not None and sum(MARKER in p for p in mine) == 1,
               "checkpointRevision": after.get("checkpoint") == f"有（r{before.get('revision')}）",
               "onlyTheReopenToasts": len(toasts) == 2 and all("重新載入" in (t or "") for t in toasts),
               "noUnchanged": (not any(UNCHANGED in (t or "") for t in toasts)) if posted else None}
    return clauses


def run_case(session, browser: str, case: str, spec: dict, round_no: int, url: str) -> dict:
    private = spec["private"]
    out = {"case": case, "round": round_no, "fixture": spec["fixture"],
           "criterion": spec["criterion"], "decision": spec["decision"],
           "backward": spec["backward"], "search": None if private else spec["search"],
           "expected": spec["expected"]}
    if spec["criterion"] == "frame":
        out["note"] = (f"native R0c decided {spec['decision']!r}; spec 22.2 registers the frame "
                       "cell as a one-time measurement expecting 18.1 N1's anchor-mismatch")
    out["open"] = open_fixture(session, url, f"{case}-r{round_no}.odt")
    refusal = spec["expected"][0] == "refused"
    marker_at = None
    if refusal:
        marker_case = next(c for c in MARKER_AT[spec["fixture"]] if c != case)
        marker_at = native_cases(spec["fixture"])[marker_case]
        out["markerAt"] = marker_case
        out["markerPlace"] = place(session, browser, marker_at["nativeCaret"], marker_at["backward"])
        if not out["markerPlace"]["ok"]:
            out["outcome"] = "marker-placement-mismatch"
            out["pass"] = False
            return out
        for letter in MARKER:
            press(session, browser, letter)
        out["markerSettled"] = quiet(session)
    out["place"] = place(session, browser, spec["nativeCaret"], spec["backward"])
    if not out["place"]["ok"]:
        out["outcome"] = "placement-mismatch"
        out["pass"] = False
        return out
    out["beforeKey"] = quiet(session)
    gen_before = pp.evaluate(session, GEN)
    responses_before = obs(session).get("responsesSeen") or 0
    pp.evaluate(session, pp.CLEAR_TOASTS)
    if case.startswith("Y"):
        press(session, browser, "x")
    # The clock starts at the DELETE (review N1; spec 22.1 M2-2): Y's typed `x`
    # is not the merge's latency.
    t0 = pp.evaluate(session, NOW)
    press(session, browser, "Backspace" if spec["backward"] else "Delete")
    # THE DELETE'S OWN ANSWER, not the next one.  Every editor action's reply
    # carries `completion` (moves, caret placement, typing), so "the first
    # response after the key" is the typed `x` on Y01.  Taken: the first
    # successful reply of a delete action, or the first FAILED EDITOR ACTION
    # (the observer records those since the review, mergeKey or not, and never
    # a failed paint); everything before it is kept as `intervening`.
    response, intervening, lost = None, [], False
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and response is None:
        record = obs(session).get("responses") or []
        lost = bool(record) and record[0].get("n", 0) > responses_before
        intervening = []
        for item in (r for r in record if r.get("n", -1) >= responses_before):
            if (item.get("ok") and item.get("action") in DELETE_ACTIONS) or not item.get("ok"):
                response = item
                break
            intervening.append({k: item.get(k) for k in ("action", "completion", "ok")})
        time.sleep(0.1)
    out["response"], out["intervening"], out["responsesLost"] = response, intervening, lost
    out["keyToResponseMs"] = round(response["t"] - t0, 1) if response else None
    if response and response.get("ok"):
        out["outcome"] = response.get("completion")
        out["keyUndo"] = response.get("keyUndo")
    elif response:
        mk = response.get("mergeKey") or {}
        out["outcome"] = "refused"
        out["code"] = response.get("code")
        out["stage"], out["keyPosted"] = mk.get("stage"), mk.get("keyPosted")
    else:
        out["outcome"] = "no-response"
    if refusal or out["outcome"] == "refused":
        out["toastWindow"] = toast_window(session, gen_before)
        out["afterKey"] = quiet(session, 90)
        out["generation"] = [gen_before, pp.evaluate(session, GEN)]
        raw = save(session, f"{case}-r{round_no}-reopened", private)
        original = odt_parts(spec["original"].read_bytes())["paragraphs"]
        mine = odt_parts(raw)["paragraphs"] if raw else None
        expected_text = list(original)
        if marker_at is not None:
            # Exactly once, checked before any browser ran (tool_cases); an
            # insertion that silently found nothing made "original + marker"
            # read as "original" and passed when the marker was lost (B3).
            i = expected_text.index(marker_at["search"])
            expected_text[i] = (MARKER + marker_at["search"] if marker_at["backward"]
                                else marker_at["search"] + MARKER)
        out["reopenedDocument"] = {"saved": raw is not None,
                                   "paragraphs": None if mine is None else len(mine)}
        out["clauses"] = refusal_clauses(out, spec, expected_text if marker_at else None, mine)
        if not refusal:
            out["clauses"]["outcome"] = False
    else:
        time.sleep(0.5)
        out["afterKey"] = quiet(session, 90)
        out["generation"] = [gen_before, pp.evaluate(session, GEN)]
        out["toasts"] = pp.evaluate(session, pp.READ_TOASTS)
        raw = save(session, f"{case}-r{round_no}-after-key", private)
        out["afterKeyDocument"] = compare(raw, spec["key"], private)
        press(session, browser, "Z")
        out["followSettled"] = quiet(session)
        out["followDocument"] = compare(save(session, f"{case}-r{round_no}-follow", private),
                                        spec["follow"], private)
        out["clauses"] = merge_clauses(out, spec)
    out["notEstablished"] = sorted(k for k, v in out["clauses"].items() if v is None)
    out["pass"] = all(v for v in out["clauses"].values() if v is not None)
    return out


def m2_0(session, fixture: str, url: str) -> dict:
    """Load and save with no edit; content.xml against native original.odt."""
    _, round_dir, _, private = FIXTURES[fixture]
    opened = open_fixture(session, url, f"m2-0-{fixture}.odt")
    return {"fixture": fixture, "open": opened,
            "document": compare(save(session, f"m2-0-{fixture}", private),
                                round_dir / "docs" / "original.odt", private)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    ap.add_argument("--candidate-profile", default="e2-editor-v16")
    ap.add_argument("--cases", default=None,
                    help="a SUBSET for a shakedown; the default is the tool-generated list "
                         "(spec 22.1), and a report from a subset says so")
    ap.add_argument("--frame-cell", action="store_true",
                    help="also run spec 22.2's registered text-frame cell (F01, F02)")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    root = HERE / "dist"
    # THE CUTOVER'S SOURCE, not dist's.  `tools/build_cutover_page.py` repoints
    # web/e2-editor-app.js; dist/ still serves the v8-era page until the shell
    # generation is frozen, and on 2026-10-07 the two differed by 63 lines --
    # B's refusal wording and the BUSY budget among them.  Measured: the first
    # run of this runner repointed dist's page and saw the old toasts.  The
    # constant is the one `build_cutover_page.py` and the product-path runner's
    # candidate mode read (3ab4f04a).
    source = pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8")
    manifest = root / "profiles" / args.candidate_profile / "sdk-manifest.json"
    page, pin_before, wasm = pp.repointed_page(source, args.candidate_profile, manifest)
    html = (root / "e2-editor.html").read_text(encoding="utf-8")
    anchor = '<script type="module" src="./e2-editor-app.js"></script>'
    if html.count(anchor) != 1:
        raise SystemExit("the page's module script is not where the instrument expects it")
    instrumented = html.replace(anchor, OBSERVER + anchor)
    mirror = Path(tempfile.mkdtemp(prefix="merge-wasm-")) / "root"
    pp.build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8"),
                                   "e2-editor.html": instrumented.encode("utf-8")})
    # Before any browser: the list, its fixtures, and every marker target
    # exactly once in its original (B3's offline half).
    cases = tool_cases(args.frame_cell)
    wanted = [c for c in (args.cases.split(",") if args.cases else cases) if c]
    missing = [c for c in wanted if c not in cases]
    if missing:
        raise SystemExit(f"not in the tool-generated list: {missing}")
    for fixture in {cases[c]["fixture"] for c in wanted if cases[c]["expected"][0] == "refused"}:
        original = odt_parts(next(iter(native_cases(fixture).values()))["original"]
                             .read_bytes())["paragraphs"]
        for marker_case in MARKER_AT[fixture]:
            target = native_cases(fixture)[marker_case]["search"]
            if original.count(target) != 1:
                raise SystemExit(f"marker target of {marker_case} occurs {original.count(target)} "
                                 f"times in {fixture}'s original, not once")
    needed = {cases[c]["fixture"] for c in wanted}
    fixture_urls = {}
    for name, (path, _, _, _) in FIXTURES.items():
        if name not in needed:
            continue
        target = mirror / f"merge-{name}.odt"     # mirror ROOT: a real directory
        if target.exists() or mirror.is_symlink():
            raise SystemExit(f"refusing to write {target}")
        target.write_bytes(path.read_bytes())
        fixture_urls[name] = f"./merge-{name}.odt"
    # Kept documents beside the report.  Never inside the native evidence tree:
    # spec 10.2 (M2-1) -- expected documents and candidate output must not
    # share a tree, so a comparison can never read its own output as the truth.
    docs = args.out.parent / f"{args.out.stem}.docs"
    if EVIDENCE.resolve() in [docs.resolve(), *docs.resolve().parents]:
        raise SystemExit(f"{docs} is inside the native evidence tree {EVIDENCE}")
    docs.mkdir(parents=True, exist_ok=False)
    DOCS["dir"] = docs
    if any(FIXTURES[f][3] for f in needed):
        # The owner's document: what the page saves from it stays in build/.
        DOCS["private"] = HERE / "build" / "merge-wasm-private" / f"{args.out.stem}.docs"
        DOCS["private"].mkdir(parents=True, exist_ok=False)
    report = {"counted": False, "instrumented": True, "browser": args.browser,
              "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "candidate": {"profile": args.candidate_profile, "pinBefore": pin_before,
                            "pageSource": pp.CUTOVER_PAGE_SOURCE.relative_to(HERE).as_posix(),
                            "pinAfter": wasm[:16],
                            "pageSha256": hashlib.sha256(page.encode()).hexdigest(),
                            "htmlSha256": hashlib.sha256(instrumented.encode()).hexdigest(),
                            "uninstrumentedHtmlSha256": hashlib.sha256(html.encode()).hexdigest(),
                            "workerSha256": sha256_of(root / "profiles" / args.candidate_profile
                                                      / "sdk-worker.js")},
              "caseList": "subset" if args.cases else "tool",
              "frameCell": args.frame_cell,
              "eshapeSha256": sha256_of(ESHAPE),
              "observedOnlyOnTheInstrumentedPage": ["completion", "keyUndo.comment",
                                                    "restorePresses", "stage", "keyPosted"],
              "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "fixtures": {n: sha256_of(FIXTURES[n][0])[:16] for n in sorted(needed)},
              "keptDocuments": docs.name,
              "m2_0": [], "cases": []}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port),
                               "--root", str(mirror)], cwd=HERE,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = (pp.ChromeSession if args.browser == "chrome" else pp.FirefoxSession)("cold")
        pp.navigate(session, base)
        report["boot"] = pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        report["shims"] = pp.evaluate(session, pp.INSTALL)
        report["observerAtBoot"] = obs(session)
        for fixture in sorted(needed):
            report["m2_0"].append(m2_0(session, fixture, fixture_urls[fixture]))
        for round_no in range(1, args.rounds + 1):
            for case in wanted:
                try:
                    report["cases"].append(run_case(session, args.browser, case, cases[case], round_no,
                                                    fixture_urls[cases[case]["fixture"]]))
                except Exception as error:  # noqa: BLE001 -- recorded with the case, the run goes on
                    report["cases"].append({"case": case, "round": round_no, "outcome": "runner-error",
                                            "error": f"{type(error).__name__}: {error}"})
                args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    finally:
        report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if session is not None:
            report["observerAtEnd"] = {k: v for k, v in obs(session).items() if k != "responses"}
            session.close()
        server.terminate()
        server.wait(timeout=10)
        args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    summary = [(c["case"], c.get("outcome"), c.get("stage"), c.get("pass"),
                [k for k, v in (c.get("clauses") or {}).items() if v is False])
               for c in report["cases"]]
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
