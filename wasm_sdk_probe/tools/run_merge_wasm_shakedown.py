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
FIXTURES = {
    "boundaries": (HERE / "test-docs/merge/odt/boundaries.odt",
                   EVIDENCE / "r0c/round-20261006T144628Z", EVIDENCE / "r0c/eshape.json"),
    "text-frame": (HERE / "test-docs/merge/odt/text-frame.odt",
                   EVIDENCE / "r0c-frame/round-20261007T060036Z", None),
}
DEFAULT_CASES = "C01,C02,I02,C11,Y01,C29,C30,C17,C15,F01"
# What WASM must do where it differs from R0c's native decision.  Spec 18.1
# N1: inside a text frame Writer sends TEXT_SELECTION before START/END, so the
# fence refuses every merge there; "M2's WASM measurement includes a cell in a
# text frame, expected anchor-mismatch".  The runner compared F01 with the
# native merge instead, so the refusal it saw (both runs, 2026-10-07) was
# graded against the wrong expectation and no marker had been typed.
WASM_EXPECT = {"text-frame": ("refused", "anchor-mismatch", False)}
# Where refusal arms type the marker: a native caret IN THE FIXTURE UNDER TEST,
# and not the case's own.  It was C01's for every fixture, a boundaries.odt
# coordinate.  In the frame, F01 (the end of "F01 frame first") and F02 (the
# start of "F01 frame second") are on different lines, so each marks the
# other's.  Backward cases are placed with Home, so the marker goes in FRONT
# of the paragraph's text; forward ones with End, after it.
MARKER_AT = {"boundaries": ("C01",), "text-frame": ("F02", "F01")}
MARKER = "mk"
# Where the page's saved documents are kept (set in main()).
DOCS: dict = {"dir": None}
UNCHANGED = "沒有被改動"
DELETE_ACTIONS = ("delete-forward", "delete-backward")
# R0c's decision -> what v15/v16 must do (spec section 17).
EXPECT = {"merge": ("verified-key-undo", None, None),
          "typed-merge": ("verified-key-undo", None, None),
          "nothing-selected": ("refused", "nothing-selected", False),
          "refused-k1-anchor": ("refused", "anchor-mismatch", False),
          "refused-k1-fence": ("refused", "anchor-mismatch", False),
          "key-noop": ("refused", "key-deadline", True)}

OBSERVER = r"""<script>
(() => {
  const Native = window.Worker;
  const obs = { workers: 0, responses: [], caret: null, carets: 0, size: null };
  const node = document.createElement("script");
  node.type = "application/json"; node.id = "merge-observer";
  const flush = () => { node.textContent = JSON.stringify(obs); };
  document.addEventListener("DOMContentLoaded", () => { document.head.appendChild(node); flush(); });
  function seen(data, generation) {
    if (!data || typeof data !== "object") return;
    if (data.kind === "event" && data.event === "editor-state" && data.caret) {
      obs.caret = { generation, t: performance.now(), caret: data.caret,
                    sourceSequence: data.sourceSequence ?? null };
      obs.carets += 1; flush(); return;
    }
    if (data.kind !== "response") return;
    const value = data.ok ? data.result : data.error;
    if (!value || typeof value !== "object") return;
    if (typeof value.width === "number" && typeof value.height === "number"
        && value.documentHandle !== undefined)
      obs.size = { w: value.width, h: value.height, from: "open" };
    if (typeof value.documentWidthTwips === "number")
      obs.size = { w: value.documentWidthTwips, h: value.documentHeightTwips, from: "paint" };
    if (value.keyUndo || value.mergeKey || value.completion) {
      obs.responses.push({ t: performance.now(), generation, ok: data.ok,
        action: value.action ?? null,
        completion: value.completion ?? null, keyUndo: value.keyUndo ?? null,
        code: value.code ?? null, message: value.message ?? null,
        mergeKey: value.mergeKey ?? null, operation: value.operation ?? null });
    }
    flush();
  }
  function Wrapped(url, options) {
    const worker = new Native(url, options);
    if (options && options.name === "oxoffice-document-engine") {
      obs.workers += 1;
      const generation = obs.workers;
      worker.addEventListener("message", (event) => {
        try { seen(event.data, generation); } catch (error) { obs.error = String(error); flush(); }
      });
      flush();
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


@functools.lru_cache(maxsize=None)
def native_cases(fixture: str) -> dict:
    """Per case: native placed cursor, direction, R0c decision, reference documents."""
    _, round_dir, decisions = FIXTURES[fixture]
    rows = [json.loads(line) for line in (round_dir / "arms.jsonl").read_text().splitlines() if line.strip()]
    if decisions is not None:
        table = json.loads(decisions.read_text())["cases"]
        decided = {key.split(" ", 1)[1]: value for key, value in table.items()
                   if key.startswith(round_dir.name + " ")}
    else:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "eshape.json"
            subprocess.run([sys.executable, str(HERE / "tools/check_merge_eshape.py"), "--json",
                            str(target), str(round_dir)], capture_output=True, text=True)
            verdict = json.loads(target.read_text())
        if verdict["kills"]:
            raise SystemExit(f"{round_dir.name}: the native reader has KILL lines {verdict['kills']}")
        decided = {key.split(" ", 1)[1]: value for key, value in verdict["cases"].items()}
    cases = {}
    for row in rows:
        if row.get("round") != 1 or row.get("arm") != "select":
            continue
        cursor = [int(v) for v in ((row.get("placed") or {}).get("cursor") or "").split(",")]
        cases[row["case"]] = {"fixture": fixture, "backward": bool(row.get("backward")),
                              "nativeCaret": cursor, "search": row.get("search"),
                              "decision": decided.get(row["case"]),
                              "key": round_dir / "docs" / f"r1-{row['case']}-key.odt",
                              "follow": round_dir / "docs" / f"r1-{row['case']}-key-follow.odt"}
    return cases


def odt_parts(raw: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        content = archive.read("content.xml")
    paragraphs = odt_paragraphs.paragraph_texts_from_xml(content)
    return {"content": content, "sha": hashlib.sha256(content).hexdigest()[:16],
            "paragraphs": paragraphs}


def compare(raw: bytes | None, reference: Path) -> dict:
    if raw is None:
        return {"saved": False}
    mine, theirs = odt_parts(raw), odt_parts(reference.read_bytes())
    return {"saved": True, "reference": reference.name, "bytesEqual": mine["content"] == theirs["content"],
            "textEqual": mine["paragraphs"] == theirs["paragraphs"],
            "mine": mine["sha"], "theirs": theirs["sha"],
            "firstTextDifference": next(([i, a, b] for i, (a, b) in enumerate(
                zip(mine["paragraphs"], theirs["paragraphs"])) if a != b),
                None if len(mine["paragraphs"]) == len(theirs["paragraphs"])
                else ["count", len(mine["paragraphs"]), len(theirs["paragraphs"])])}


def save(session, name: str) -> bytes | None:
    """The product's save; the bytes are kept as `<DOCS>/<name>.odt`."""
    index = pp.evaluate(session, pp.SAVE_COUNT) or 0
    pp.evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
    if not pp.wait_saves(session, index + 1, 60):
        return None
    saved = pp.evaluate(session, pp.READ_SAVE.replace("ARG_INDEX", str(index)))
    raw = base64.b64decode(saved["b64"]) if saved else None
    if raw is not None and DOCS["dir"] is not None:
        target = DOCS["dir"] / f"{name}.odt"
        if target.exists():
            raise SystemExit(f"refusing to overwrite a kept document: {target}")
        target.write_bytes(raw)
    return raw


def open_fixture(session, url: str, name: str) -> dict:
    pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", url).replace("ARG_NAME", name))
    opened = pp.wait_for(session, lambda s: (s.get("doc") or "") == name and s.get("state") == "ready", 120)
    return {"opened": bool(opened), "settled": quiet(session)}


def place(session, browser: str, target: list[int], backward: bool) -> dict:
    """Click at the native caret, then End/Home; the engine's caret must equal it."""
    size = obs(session).get("size") or {}
    if not size.get("w") or not size.get("h"):
        return {"ok": False, "why": "no document size from the instrument"}
    x, y, _, height = target
    fx = (x + (-40 if not backward else 40)) / size["w"]
    fy = (y + height / 2) / size["h"]
    before = (obs(session).get("carets") or 0)
    pp.evaluate(session, pp.POINT_AT.replace("ARG_X", f"{fx:.6f}").replace("ARG_Y", f"{fy:.6f}"))
    pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 30)
    quiet(session)
    time.sleep(0.3)
    clicked = caret_tuple(obs(session).get("caret"))
    # A click that already lands on the native caret needs no key: Home at the
    # start of a numbered or bulleted paragraph moves IN FRONT OF the label
    # (measured on C11: x 1778 against the native 2138), which is not where
    # the native round placed it.
    keyed = not (clicked and clicked[:2] == target[:2] and clicked[3] == target[3])
    if keyed:
        press(session, browser, "Home" if backward else "End")
        time.sleep(0.4)
        quiet(session)
    deadline = time.monotonic() + 5
    caret = None
    while time.monotonic() < deadline:
        seen = obs(session)
        caret = caret_tuple(seen.get("caret"))
        if (seen.get("carets") or 0) > before and caret and caret[:2] == target[:2] and caret[3] == target[3]:
            break
        time.sleep(0.2)
    ok = bool(caret) and caret[:2] == target[:2] and caret[3] == target[3]
    return {"ok": ok, "click": [round(fx, 6), round(fy, 6)], "size": size, "keyed": keyed,
            "afterClick": clicked,
            "engineCaret": caret, "nativeCaret": target}


def run_case(session, browser: str, case: str, spec: dict, round_no: int, url: str) -> dict:
    out = {"case": case, "round": round_no, "decision": spec["decision"],
           "backward": spec["backward"], "search": spec["search"]}
    expected = WASM_EXPECT.get(spec["fixture"], EXPECT.get(spec["decision"]))
    if spec["fixture"] in WASM_EXPECT:
        out["note"] = (f"native R0c decided {spec['decision']!r}; on WASM the expectation is "
                       "spec 18.1 N1's (the fence refuses inside a text frame)")
    out["expected"] = expected
    out["open"] = open_fixture(session, url, f"{case}-r{round_no}.odt")
    refusal = expected is not None and expected[0] == "refused"
    marker_case = next(c for c in MARKER_AT[spec["fixture"]] if c != case)
    marker_at = native_cases(spec["fixture"])[marker_case]
    out["markerAt"] = marker_case
    if refusal:
        out["markerPlace"] = place(session, browser, marker_at["nativeCaret"], marker_at["backward"])
        if not out["markerPlace"]["ok"]:
            out["outcome"] = "marker-placement-mismatch"
            return out
        for letter in MARKER:
            press(session, browser, letter)
        out["markerSettled"] = quiet(session)
    out["place"] = place(session, browser, spec["nativeCaret"], spec["backward"])
    if not out["place"]["ok"]:
        out["outcome"] = "placement-mismatch"
        return out
    out["beforeKey"] = quiet(session)
    gen_before = pp.evaluate(session, GEN)
    responses_before = len(obs(session).get("responses") or [])
    pp.evaluate(session, pp.CLEAR_TOASTS)
    t0 = pp.evaluate(session, NOW)
    if case.startswith("Y"):
        press(session, browser, "x")
    press(session, browser, "Backspace" if spec["backward"] else "Delete")
    # THE DELETE'S OWN ANSWER, not the next one.  Every editor action's reply
    # carries `completion` (moves, caret placement, typing), so "the first
    # response after the key" is the typed `x` on Y01.  Taken: the first
    # successful reply of a delete action, or the first error; everything
    # before it is kept as `intervening`.
    response, intervening = None, []
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and response is None:
        seen = (obs(session).get("responses") or [])[responses_before:]
        intervening = []
        for item in seen:
            if (item.get("ok") and item.get("action") in DELETE_ACTIONS) or not item.get("ok"):
                response = item
                break
            intervening.append({k: item.get(k) for k in ("action", "completion", "ok")})
        time.sleep(0.1)
    out["response"], out["intervening"] = response, intervening
    out["keyToResponseMs"] = round(response["t"] - t0, 1) if response else None
    time.sleep(0.5)
    out["afterKey"] = quiet(session, 90)
    out["generation"] = [gen_before, pp.evaluate(session, GEN)]
    out["toasts"] = pp.evaluate(session, pp.READ_TOASTS)
    if response and response.get("ok") and response.get("completion") == "verified-key-undo":
        out["outcome"] = "verified-key-undo"
        out["keyUndo"] = response.get("keyUndo")
        raw = save(session, f"{case}-r{round_no}-after-key")
        out["afterKeyDocument"] = compare(raw, spec["key"])
        press(session, browser, "Z")
        out["followSettled"] = quiet(session)
        out["followDocument"] = compare(save(session, f"{case}-r{round_no}-follow"), spec["follow"])
    elif response and not response.get("ok"):
        mk = response.get("mergeKey") or {}
        out["outcome"] = "refused"
        out["stage"], out["keyPosted"] = mk.get("stage"), mk.get("keyPosted")
        raw = save(session, f"{case}-r{round_no}-reopened")
        original = odt_parts(spec["key"].with_name("original.odt").read_bytes())["paragraphs"]
        mine = odt_parts(raw)["paragraphs"] if raw else None
        expected_text = list(original)
        target = marker_at["search"]
        if target in expected_text:
            i = expected_text.index(target)
            expected_text[i] = MARKER + target if marker_at["backward"] else target + MARKER
        out["reopenedDocument"] = {"saved": raw is not None,
                                   "textIsOriginalPlusMarker": mine == expected_text,
                                   "markerSurvived": bool(mine) and any(MARKER in p for p in mine)}
        out["toastSaysUnchanged"] = any(UNCHANGED in (t or "") for t in (out["toasts"] or []))
    else:
        out["outcome"] = "no-response" if response is None else "other"
    if expected:
        want, stage, posted = expected
        out["asExpected"] = (out["outcome"] == want and
                             (want != "refused" or (out.get("stage") == stage and out.get("keyPosted") == posted)))
    return out


def m2_0(session, fixture: str, url: str) -> dict:
    """Load and save with no edit; content.xml against native original.odt."""
    _, round_dir, _ = FIXTURES[fixture]
    opened = open_fixture(session, url, f"m2-0-{fixture}.odt")
    return {"fixture": fixture, "open": opened,
            "document": compare(save(session, f"m2-0-{fixture}"), round_dir / "docs" / "original.odt")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    ap.add_argument("--candidate-profile", default="e2-editor-v16")
    ap.add_argument("--cases", default=DEFAULT_CASES)
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
    fixture_urls = {}
    for name, (path, _, _) in FIXTURES.items():
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
    cases = {**native_cases("boundaries"), **native_cases("text-frame")}
    wanted = [c for c in args.cases.split(",") if c]
    missing = [c for c in wanted if c not in cases]
    if missing:
        raise SystemExit(f"no native R0c row for {missing}")
    report = {"counted": False, "instrumented": True, "browser": args.browser,
              "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "candidate": {"profile": args.candidate_profile, "pinBefore": pin_before,
                            "pageSource": pp.CUTOVER_PAGE_SOURCE.relative_to(HERE).as_posix(),
                            "pinAfter": wasm[:16],
                            "pageSha256": hashlib.sha256(page.encode()).hexdigest(),
                            "htmlSha256": hashlib.sha256(instrumented.encode()).hexdigest()},
              "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "fixtures": {n: hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                           for n, (p, _, _) in FIXTURES.items()},
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
        for fixture in sorted({cases[c]["fixture"] for c in wanted}):
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
    summary = [(c["case"], c.get("outcome"), c.get("stage"), c.get("asExpected")) for c in report["cases"]]
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
