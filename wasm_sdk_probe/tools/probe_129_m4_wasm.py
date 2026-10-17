#!/usr/bin/env python3
"""M4 (finding 129) on WASM: the page's "click at the point, then the key" fix, measured in both
browsers with real keys, against the native reference of findings/evidence/129/native/.

Brief: handoff/tasks/TASK-2026-10-12d-m4-129-on-wasm.md.  Nothing under web/, dist/, editor-shell*/,
sdk/, src/, input/ is written.  The page under test is a MIRROR of dist/ (pp.build_mirror) whose
e2-editor-app.js is build/m4-mirror/e2-editor-app.js (= dist/e2-editor-app.js + the 129 patch, checked
at the start of every run; web/ is not read) plus ONE appended line,

    globalThis.__m4 = { get session() { return session; } };

and the red control uses the shipped dist/e2-editor-app.js plus the same one line.

Per arm (one fresh open of the document each):
  1. click inside the target paragraph (pp.POINT_AT at a calibrated first line), Home;
  2. real plain Right x k  -> read editorState.caret (twips) = the anchor; n more Rights -> the far end;
  3. DRAG through the page's own pointer handler (pp.DRAG, fractions = twips / document twips,
     y = caret.y + caret.height / 2) from the anchor to the far end (FORWARD) or back (BACKWARD);
  4. the selection is read with session.document.getSelection() (the engine read that copySelection()
     writes to the clipboard) and compared with what the native arm selected; a mismatch is
     `selection-mismatch`: reported, not counted;
  5. ONE real unshifted key; wait for quiet; ONE real '#'; wait for quiet;
  6. session.save() -> bytes -> content.xml -> paragraph texts; '#' is located (flattened index,
     paragraph, offset).
Every latency-line change, pill change, toast change and keydown is logged with performance.now().

  probe_129_m4_wasm.py --browser chrome --out DIR [--arms REGEX] [--phases calibrate,arms,shift,red]
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import odt_paragraphs  # noqa: E402
import probe_111_overtake as p111  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
from r7_support import run_in_page  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
TREE = HERE.parent
DIST = HERE / "dist"
MIRROR_PAGE = HERE / "build" / "m4-mirror" / "e2-editor-app.js"
PATCH = TREE / "findings" / "evidence" / "129" / "m4" / "page-129.patch"
FIXTURES = HERE / "test-docs" / "f129"
EXPECTED_DIST_SHA256 = "8909564eb2316afa6de7868a08b61d27219fabdf49f37326fee0dda2977bd401"
# --final (129-B on the bytes that ship, SPEC-M3-autosave §9.4): the page under test is dist/ itself once
# 0.2.13's page is copied there (it carries the 129 fix, with review 2's changes), and the red control is
# 0.2.12's page from the archived engine package (the same dist/ otherwise: only e2-editor-app.js differs).
# Re-pinned 2026-10-12 to the page with finding 131's rule A (SPEC-M3-autosave §9.12; it re-opens 129-B).
# The two earlier rounds in findings/evidence/129/final/ ran on c7f904fa1d807c63afc0e82522dcb0d8abab71175a9ee5de3c2af276dd24b5ab.
# Re-pinned 2026-10-13 to the final page of finding 132 (SPEC-M3-held-key §5.3, the "must not break" set; the page after N10).
# Round 3 in findings/evidence/129/final/ (round-20261012T092119Z) ran on d761f1cee9d26c50c0b152348d74c3d05f540e9228927815d93ad6ec161e7dcd.
# Re-pinned 2026-10-13 to the page of finding 134 (SPEC-M3-held-key §14, the "must not break" set; B + D on top of the 132 final page).
# The previous pin, the 132 final page, was abe93f4575c7797db97462f1f0e3a71cf5fc4063205cd6d5877093ca1c248fcf (findings/evidence/129/final/round-20261012T183200Z ran on it).
# Re-pinned 2026-10-13 to the page of finding 136 (SPEC-M3-held-key §16, the "must not break" set; caret note + restore-flash fix on top of the 134 page).
# The previous pin, the 134 page, was 6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b (findings/evidence/129/final/round-20261012T235136Z ran on it).
# Re-pinned 2026-10-14 to the v67 candidate page (task 2026-10-14c: v20 part 1/2 page+shell bytes and ruling 6 conditions 45, 47, 48, before the shell freeze; the shipped engine is still v19).
# The previous pin, the 136 page, was b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678 (findings/evidence/129/final/round-20261013T063013Z ran on it).
# Re-pinned 2026-10-15 (task 10-15c P4, before binding v20) to host 0.2.23's page (shell v72, engine v20).  129-B is NOT retired on v20:
# SPEC-M3-link-batch §10.9 S-2 retires it in favour of R1, and R1 is deferred to the ordered-commands batch (§13.3; handoff 10-13f), so
# L-129 stands and this instrument stays live -- it last ran as finding 140's C2 witness (task 10-14k, round-20261014T085633Z).
# The previous pin, the v67/v68 candidate page, was 7815e16c2cdfdebe90fbe8bf91d07a8315654bf76cf603fe8392acebb5be0799 (that round ran on it).
# Re-pinned 2026-10-15 to host 0.2.24's page (finding 145; shell v73).  The previous pin, host 0.2.23's page, was
# ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e (no round of this probe ran on it; the last, round-20261014T085633Z, ran on 7815e16c…).
# Re-pinned 2026-10-17 to host 0.2.26 (engine v21, shell v74, finding 154's host rule), 2026-10-17.  The previous pin, host 0.2.24's page, was
# 901dd6a6dbff6ad6f5252814fb4dc09230446a11d75387fb447e8a6a398a68c2 (no round of this probe ran on it).
FINAL_PAGE_SHA256 = "605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f"
OLD_PAGE_GZ = HERE / "build" / "archive" / "host-0.2.12-engine-45cdcedfc0fe7e61" / "files" / "e2-editor-app.js.gz"
INSTRUMENT_LINE = "\nglobalThis.__m4 = { get session() { return session; } };\n"
NATIVE_ROUND = TREE / "findings" / "evidence" / "129" / "native" / "point-click-round-20261012T031459Z"
NATIVE_ARMS = [NATIVE_ROUND / f"arms-r{r}.jsonl" for r in (1, 2, 3)]
NATIVE_DRAG = TREE / "findings" / "evidence" / "129" / "native" / "point-click-extras-drag-round-20261012T034525Z"

KEYS = ["Left", "Right", "Up", "Down", "Home", "End"]
ARROW = {"Left": ("ArrowLeft", 37, ""), "Up": ("ArrowUp", 38, ""),
         "Right": ("ArrowRight", 39, ""), "Down": ("ArrowDown", 40, ""),
         "Home": ("Home", 36, ""), "End": ("End", 35, "")}
SHIFT_WD = ""

# --------------------------------------------------------------------------- page-realm helpers
# Firefox's WebDriver runs injected scripts in a sandbox that cannot see page-defined expandos or call
# page functions, so everything that needs the page's `session` is a <script> element (run_in_page)
# that leaves its answer in a DOM attribute; the driver reads the attribute.
TIMELINE_JS = """
(() => {
  if (globalThis.__m4log) return;
  const log = globalThis.__m4log = [];
  const t0 = performance.now();
  const pill = document.querySelector('#state-pill'), lat = document.querySelector('#s-latency'),
        sink = document.querySelector('#sink'), toastEl = document.querySelector('#toast');
  const rec = (what, extra) => log.push({ t: Math.round((performance.now() - t0) * 10) / 10, what,
    state: pill.dataset.state, latency: lat.textContent,
    toast: toastEl.classList.contains('show') ? toastEl.textContent : null, ...extra });
  new MutationObserver(() => rec('pill')).observe(pill, { attributes: true, attributeFilter: ['data-state'] });
  new MutationObserver(() => rec('latency')).observe(lat, { childList: true, characterData: true, subtree: true });
  new MutationObserver((records) => {
    const added = records.flatMap((r) => [...r.addedNodes].map((n) => n.textContent)).filter(Boolean);
    rec('toast', { added, cls: toastEl.className });
  }).observe(toastEl, { attributes: true, childList: true, characterData: true, subtree: true });
  document.addEventListener('keydown', (e) => rec('keydown', { key: e.key, shift: e.shiftKey, repeat: e.repeat,
    now: Math.round(performance.now() * 10) / 10 }), true);
  rec('installed');
})();
"""


def page_eval(session, expression: str, *, wait: bool = False, timeout: float = 30):
    """Evaluate `expression` in the PAGE realm; return its JSON-able value.  `wait`: it is a promise."""
    marker = f"m4r{int(time.monotonic() * 1000) % 10**9}"
    script = (
        f"(() => {{ const d = document.documentElement.dataset; d.m4r = ''; d.m4k = {json.dumps(marker)};"
        f" const put = (v) => {{ d.m4r = JSON.stringify({{ k: {json.dumps(marker)}, v: v === undefined ? null : v }}); }};"
        f" const fail = (e) => {{ d.m4r = JSON.stringify({{ k: {json.dumps(marker)}, error: String(e && e.stack || e) }}); }};"
        f" try {{ Promise.resolve({expression}).then(put, fail); }} catch (e) {{ fail(e); }} }})();"
    )
    run_in_page(session, script)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        raw = pp.evaluate(session, "(() => document.documentElement.dataset.m4r || '')()")
        if raw:
            out = json.loads(raw)
            if out.get("k") == marker:
                if "error" in out:
                    raise RuntimeError(f"page_eval failed: {out['error']}")
                return out["v"]
        time.sleep(0.02 if not wait else 0.05)
    raise TimeoutError(f"page_eval timed out: {expression[:80]}")


EDITOR_STATE_JS = """(() => {
  const s = globalThis.__m4.session, snap = s.state.snapshot, e = snap.editorState || {};
  const pick = (r) => r ? { x: r.x, y: r.y, width: r.width, height: r.height } : null;
  return { state: snap.state, revision: snap.revision ?? null, dirty: snap.dirty ?? null,
    caret: pick(e.caret), selectionStart: pick(e.selectionStart), selectionEnd: pick(e.selectionEnd),
    selectionRectangles: (e.selectionRectangles || []).map(pick),
    sourceSequence: e.sourceSequence ?? null, keys: Object.keys(e), selection: e.selection ?? null,
    selectionType: e.selectionType ?? null, selectionTextMissing: e.selectionTextMissing ?? null,
    selectionText: e.selectionText ?? null,
    shape: (typeof snap.selectionShape === 'string') ? snap.selectionShape : null,
    docW: s.document.widthTwips, docH: s.document.heightTwips };
})()"""
READ_LOG = "globalThis.__m4log.slice(%d)"


def editor_state(session) -> dict:
    return page_eval(session, EDITOR_STATE_JS)


def log_mark(session) -> int:
    return page_eval(session, "globalThis.__m4log.length")


def log_since(session, mark: int) -> list:
    return page_eval(session, READ_LOG % mark)


def selection_text(session) -> dict:
    return page_eval(session, "globalThis.__m4.session.document.getSelection({ timeoutMs: 30000 })"
                              ".then((s) => ({ mimeType: s.mimeType, text: s.text, revision: s.revision }))",
                     wait=True, timeout=60)


def save_paragraphs(session) -> dict:
    """session.save() -> bytes -> paragraph texts (decoded here, in Python)."""
    out = page_eval(session, "globalThis.__m4.session.save().then((r) => { let s = ''; const u = new Uint8Array(r.bytes);"
                             " for (let i = 0; i < u.length; i += 1) s += String.fromCharCode(u[i]);"
                             " return { bytes: u.length, b64: btoa(s) }; })", wait=True, timeout=120)
    raw = base64.b64decode(out["b64"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        content = archive.read("content.xml")
    paragraphs = odt_paragraphs.paragraph_texts_from_xml(content)
    return {"bytes": out["bytes"], "sha256": hashlib.sha256(raw).hexdigest(), "paragraphs": paragraphs}


# --------------------------------------------------------------------------- real keys
def key_chrome(session, name: str, shift: bool = False) -> None:
    key, vk, _ = ARROW[name]
    mods = 8 if shift else 0
    for t in ("rawKeyDown", "keyUp"):
        session.call("Input.dispatchKeyEvent", {"type": t, "key": key, "code": key, "windowsVirtualKeyCode": vk,
                                                "nativeVirtualKeyCode": vk, "modifiers": mods})


def keys(session, browser: str, names: list[str], shift: bool = False, gap_ms: int = 0) -> None:
    """Real unshifted (or shifted) arrow / Home / End presses, in order."""
    if browser == "chrome":
        for i, name in enumerate(names):
            if i and gap_ms:
                time.sleep(gap_ms / 1000)
            key_chrome(session, name, shift)
        return
    actions = []
    for i, name in enumerate(names):
        if i and gap_ms:
            actions.append({"type": "pause", "duration": gap_ms})
        if shift:
            actions.append({"type": "keyDown", "value": SHIFT_WD})
        actions += [{"type": "keyDown", "value": ARROW[name][2]}, {"type": "keyUp", "value": ARROW[name][2]}]
        if shift:
            actions.append({"type": "keyUp", "value": SHIFT_WD})
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
    session.command("DELETE", "/actions")


def type_hash(session, browser: str) -> None:
    if browser == "chrome":
        for t in ("rawKeyDown", "char", "keyUp"):
            e = {"type": t, "key": "#", "code": "Digit3", "windowsVirtualKeyCode": 51, "nativeVirtualKeyCode": 51,
                 "modifiers": 8}
            if t == "char":
                e["text"] = "#"
            session.call("Input.dispatchKeyEvent", e)
        return
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": [
        {"type": "keyDown", "value": "#"}, {"type": "keyUp", "value": "#"}]}]})
    session.command("DELETE", "/actions")


def quiet(session, limit: float = 60) -> dict:
    return p111.quiet(session, limit)


# --------------------------------------------------------------------------- pointer
def fractions(state: dict, x_twips: float, y_twips: float) -> tuple[str, str]:
    return repr(x_twips / state["docW"]), repr(y_twips / state["docH"])


def click_at(session, state: dict, x: float, y: float) -> None:
    before = (pp.evaluate(session, pp.READ_STATE) or {}).get("latency")
    fx, fy = fractions(state, x, y)
    pp.evaluate(session, pp.POINT_AT.replace("ARG_X", fx).replace("ARG_Y", fy))
    pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or "") and s.get("latency") != before, 30)
    quiet(session)


def drag(session, state: dict, a: tuple[float, float], b: tuple[float, float]) -> None:
    f1 = fractions(state, *a)
    f2 = fractions(state, *b)
    pp.evaluate(session, pp.DRAG.replace("ARG_X1", f1[0]).replace("ARG_Y1", f1[1])
                .replace("ARG_X2", f2[0]).replace("ARG_Y2", f2[1]))


def mid(caret: dict) -> float:
    return caret["y"] + caret["height"] / 2


# --------------------------------------------------------------------------- reading the DOM
READ_TOOLBAR_SHAPE = "(() => { const t = document.querySelector('#toolbar'); return t ? { shape: t.dataset.selectionShape ?? null, evidence: t.dataset.selectionEvidence ?? null } : null; })()"


def toolbar_shape(session) -> dict:
    return pp.evaluate(session, READ_TOOLBAR_SHAPE) or {}


def loadavg() -> list[float]:
    return [float(x) for x in Path("/proc/loadavg").read_text().split()[:3]]


def memory_mb() -> dict:
    info = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, v = line.split(":", 1)
        if k in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
            info[k] = int(v.split()[0]) // 1024
    return info


def swap_counters() -> dict:
    out = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        k, v = line.split()
        if k in ("pswpin", "pswpout", "pgmajfault"):
            out[k] = int(v)
    return out


def swap_delta(before: dict) -> dict:
    now = swap_counters()
    return {k: now[k] - before.get(k, 0) for k in now}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------- environment
class Env:
    def __init__(self, browser: str, out: Path):
        self.browser = browser
        self.out = out
        self.session = None
        self.servers: list[subprocess.Popen] = []
        self.bases: dict[str, str] = {}
        self.roots: dict[str, Path] = {}
        self.current: str | None = None
        self.opens = 0

    def serve(self, name: str, page_bytes: bytes, docs: dict[str, bytes]) -> None:
        root = Path(tempfile.mkdtemp(prefix=f"m4-{name}-")) / "root"
        pp.build_mirror(DIST, root, {"e2-editor-app.js": page_bytes})
        for fname, data in docs.items():
            (root / fname).write_bytes(data)
        port = pp.free_port()
        self.servers.append(subprocess.Popen(
            [sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port), "--root", str(root)],
            cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        self.bases[name] = f"http://127.0.0.1:{port}/e2-editor.html"
        self.roots[name] = root
        pp.wait_page(self.bases[name])

    def start(self) -> None:
        self.session = (pp.ChromeSession if self.browser == "chrome" else pp.FirefoxSession)("cold")

    def goto(self, name: str) -> dict:
        """Load the page `name` ('patched' | 'unpatched') cold and wait for ready; install the shims."""
        pp.navigate(self.session, self.bases[name])
        boot = pp.wait_for(self.session, lambda s: s.get("state") == "ready", 300)
        pp.evaluate(self.session, pp.INSTALL)
        run_in_page(self.session, TIMELINE_JS)
        self.current = name
        self.opens = 0
        return boot

    def open_doc(self, doc: str) -> dict:
        self.opens += 1
        name = f"{doc}-{self.current}-{self.opens}.odt"
        pp.evaluate(self.session, pp.OPEN_FILE.replace("ARG_URL", f"./{doc}.odt").replace("ARG_NAME", name))
        state = pp.wait_for(self.session, lambda s: (s.get("doc") or "") == name and s.get("state") == "ready", 180)
        settled = quiet(self.session)
        es = editor_state(self.session)
        return {"name": name, "readyState": {k: state.get(k) for k in ("state", "revision", "pending", "doc")},
                "settled": {k: settled.get(k) for k in ("state", "revision", "pending", "timedOut")},
                "caret": es["caret"], "revision": es["revision"], "dirty": es["dirty"], "docW": es["docW"],
                "docH": es["docH"], "selectionCollapsed": (es.get("selection") or {}).get("collapsed")}

    def close(self) -> None:
        if self.session is not None:
            try:
                self.session.close()
            except Exception:  # noqa: BLE001
                pass
        for s in self.servers:
            s.terminate()
        for s in self.servers:
            try:
                s.wait(timeout=10)
            except subprocess.TimeoutExpired:
                s.kill()


# --------------------------------------------------------------------------- calibration
def wait_caret_change(session, previous: dict, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        st = editor_state(session)
        if st["caret"] != previous:
            return st
        time.sleep(0.03)
    return None


def right_walk(env: Env, doc: str, until_wraps: int) -> dict:
    """Fresh open of `doc`, click in its first paragraph, Home, then Right ONE press at a time (waiting for
    the caret to change after each) until the caret's y has changed `until_wraps` times.  The same method as
    the native discover step, extended to the next wraps."""
    info = env.open_doc(doc)
    st0 = editor_state(env.session)
    cal = cal_stops_first(env, st0)
    carets = [dict(cal["start"])]
    wraps: list[int] = []
    y = cal["start"]["y"]
    prev = cal["start"]
    for i in range(1, 700):
        keys(env.session, env.browser, ["Right"])
        st = wait_caret_change(env.session, prev)
        if st is None:
            carets.append(None)
            break
        prev = st["caret"]
        carets.append(dict(prev))
        if prev["y"] != y:
            wraps.append(i)
            y = prev["y"]
            if len(wraps) >= until_wraps:
                break
    return {"open": info, "start": cal, "carets": carets, "wrapOffsets": wraps}


def cal_stops_first(env: Env, st0: dict) -> dict:
    """Click inside the first line (a little right of the document's first caret) and press Home."""
    c0 = st0["caret"]
    click_at(env.session, st0, c0["x"] + 250, mid(c0))
    keys(env.session, env.browser, ["Home"])
    quiet(env.session)
    st = editor_state(env.session)
    return {"start": st["caret"], "clickedAt": [c0["x"] + 250, mid(c0)]}


def down_walk(env: Env, doc: str, max_stops: int = 40) -> dict:
    """Fresh open, click in the first line, Home, then Down one press at a time.  At every stop: the caret
    as Down (or the first Home) left it is the line's START; End reads the line's END; then a click inside
    the line and Home bring the column back to the line start.  (Home straight after End is NOT used: on a
    line that breaks mid-word End puts the caret at the end of line n, whose layout position is the start of
    line n+1, and Home then goes to line n+1 -- the very effect finding 129's extras are about; the first
    version of this walk did that and recorded wrong starts for the wrap fixture.)  Ends when Down no longer
    changes y."""
    info = env.open_doc(doc)
    st0 = editor_state(env.session)
    first = cal_stops_first(env, st0)
    stops = []
    start = first["start"]
    for i in range(max_stops):
        keys(env.session, env.browser, ["End"]); quiet(env.session)
        end = editor_state(env.session)["caret"]
        stops.append({"index": i, "start": start, "end": end})
        click_at(env.session, editor_state(env.session), start["x"] + 250, mid(start))
        keys(env.session, env.browser, ["Home"]); quiet(env.session)
        keys(env.session, env.browser, ["Down"]); quiet(env.session)
        nxt = editor_state(env.session)["caret"]
        if nxt["y"] == start["y"]:
            break
        start = nxt
    return {"open": info, "stops": stops, "docW": st0["docW"], "docH": st0["docH"]}


def calibrate(env: Env, texts: dict) -> dict:
    cal: dict = {"browser": env.browser}
    cal["old"] = down_walk(env, "arrow-selection", 6)
    cal["shapes"] = down_walk(env, "arrow-selection-shapes", 40)
    cal["wrap"] = down_walk(env, "arrow-selection-wrap", 12)
    cal["s1Walk"] = right_walk(env, "arrow-selection-shapes", 3)
    cal["m1Walk"] = right_walk(env, "arrow-selection-wrap", 3)
    cal["firstCaret"] = {"arrow-selection": cal["old"]["open"]["caret"],
                         "arrow-selection-shapes": cal["shapes"]["open"]["caret"],
                         "arrow-selection-wrap": cal["wrap"]["open"]["caret"]}
    n = len(cal["shapes"]["stops"])
    cal["shapesStops"] = n
    cal["s1Lines"] = n - 8
    return cal


# --------------------------------------------------------------------------- native references
def flat_index(text: str) -> int | None:
    i = text.find("#")
    return i if i >= 0 and text.count("#") == 1 else None


def load_native() -> dict:
    """(shape, key, kind) -> sorted set of '#' indices in the native text, over all native rounds."""
    out: dict = {}
    files = list(NATIVE_ARMS) + [NATIVE_DRAG / f"arms-r{r}.jsonl" for r in (1, 2, 3)]
    for f in files:
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") in ("ref", "emu") and "text" in r:
                out.setdefault((r["shape"], r["key"], r["kind"]), set()).add(flat_index(r["text"]))
    return {k: sorted(v) for k, v in out.items()}


def locate(paragraphs: list[str], flat: int) -> tuple[int, int]:
    """Flat index (paragraphs joined by ONE separator char each) -> (paragraph index, offset in paragraph)."""
    pos = 0
    for i, p in enumerate(paragraphs):
        if flat <= pos + len(p):
            return i, flat - pos
        pos += len(p) + 1
    return len(paragraphs) - 1, len(paragraphs[-1])


def norm_newlines(s: str) -> str:
    return s.replace("\r\n", "\n")


# --------------------------------------------------------------------------- arms
def shape_defs(cal: dict, texts: dict) -> dict:
    s1 = texts["shapes"][0]
    token = texts["wrap"][0]
    k = cal["s1Lines"]
    W = cal["s1Walk"]["wrapOffsets"][0]
    B = cal["m1Walk"]["wrapOffsets"][0]
    return {
        "p2-forward": dict(doc="arrow-selection", stops="old", stop=1, rights=(9, 10), direction="forward",
                           expected="BETA GAMMA"),
        "p2-backward": dict(doc="arrow-selection", stops="old", stop=1, rights=(9, 10), direction="backward",
                            expected="BETA GAMMA"),
        "s1": dict(doc="arrow-selection-shapes", stops="shapes", stop=0, rights=(W - 10, 10), direction="forward",
                   expected=s1[W - 10:W]),
        "s2": dict(doc="arrow-selection-shapes", stops="shapes", stop=k, rights=(9, 11), direction="forward",
                   expected="visual line"),
        "s3": dict(doc="arrow-selection-shapes", stops="shapes", stop=k + 2, rights=(25, 10), direction="forward",
                   expected="paragraph\n"),
        "s4": dict(doc="arrow-selection-shapes", stops="shapes", stop=k + 5, rights=(3, 7), direction="forward",
                   expected="cell A1"),
        "s5": dict(doc="arrow-selection-shapes", stops="shapes", stop=k + 5, rights=(11, 5), direction="forward",
                   expected=None),
        "s1d": dict(doc="arrow-selection-shapes", stops="shapes", stop=0, rights=(W - 10, None), direction="forward",
                    drag_far="right-of-line-1", expected=s1[W - 10:W]),
        "m1d": dict(doc="arrow-selection-wrap", stops="wrap", stop=0, rights=(B - 10, None), direction="forward",
                    drag_far="right-of-line-1", expected=token[B - 10:B]),
    }


def wait_key_done(session, mark: int, timeout: float = 8.0) -> list:
    """Until the timeline holds a keydown and a latency record that is not the click's (定位游標)."""
    deadline = time.monotonic() + timeout
    log: list = []
    while time.monotonic() < deadline:
        log = log_since(session, mark)
        saw_key = any(r["what"] == "keydown" for r in log)
        done = any(r["what"] == "latency" and not (r["latency"] or "").startswith("定位游標") for r in log)
        if saw_key and done:
            return log
        time.sleep(0.05)
    return log


def timing_of(log: list) -> dict:
    key = next((r for r in log if r["what"] == "keydown"), None)
    out = {"keydownT": key["t"] if key else None}
    if not key:
        return out
    after = [r for r in log if r["what"] == "latency" and r["t"] >= key["t"]]
    click = next((r for r in after if (r["latency"] or "").startswith("定位游標")), None)
    move = next((r for r in after if not (r["latency"] or "").startswith("定位游標")), None)
    out["clickDoneMs"] = round(click["t"] - key["t"], 1) if click else None
    out["moveDoneMs"] = round(move["t"] - key["t"], 1) if move else None
    out["moveLatencyText"] = move["latency"] if move else None
    out["clickLatencyText"] = click["latency"] if click else None
    out["latencyRecords"] = [(round(r["t"] - key["t"], 1), r["latency"]) for r in after]
    return out


def toasts_in(log: list) -> list:
    return [(r["t"], a) for r in log if r["what"] == "toast" for a in (r.get("added") or [])]


def make_selection(env: Env, cal: dict, d: dict, rec: dict) -> bool:
    """Click, Home, Rights, DRAG; returns False (and says why in rec) when the arm cannot be counted."""
    session, browser = env.session, env.browser
    stop = cal[d["stops"]]["stops"][d["stop"]]
    st = editor_state(session)
    c = stop["start"]
    rec["clickAt"] = [c["x"] + 250, mid(c)]
    click_at(session, st, c["x"] + 250, mid(c))
    keys(session, browser, ["Home"])
    quiet(session)
    home = editor_state(session)["caret"]
    rec["home"] = home
    k, n = d["rights"]
    if k:
        keys(session, browser, ["Right"] * k)
        quiet(session)
    a = editor_state(session)
    rec["anchor"] = a["caret"]
    if d.get("drag_far") == "right-of-line-1":
        far = {"x": min(stop["end"]["x"] + 400, st["docW"] - 200), "y": stop["end"]["y"], "height": stop["end"]["height"]}
    else:
        keys(session, browser, ["Right"] * n)
        quiet(session)
        far = editor_state(session)["caret"]
    rec["far"] = far
    if d["direction"] == "forward":
        start, end = a["caret"], far
    else:
        start, end = far, a["caret"]
    drag(session, st, (start["x"], mid(start)), (end["x"], mid(end)))
    time.sleep(0.2)
    quiet(session)
    return True


def run_arm(env: Env, cal: dict, defs: dict, texts: dict, native: dict, shape: str, key: str, round_no: int) -> dict:
    d = defs[shape]
    session, browser = env.session, env.browser
    rec: dict = {"arm": f"m4-{shape}-{key}", "kind": "m4", "shape": shape, "key": key, "browser": browser,
                 "round": round_no, "loadavgStart": loadavg(), "startedAtEpoch": time.time(),
                 "page": env.current}
    swap0 = swap_counters()
    try:
        rec["open"] = env.open_doc(d["doc"])
        o = rec["open"]
        rec["fresh"] = bool(o["revision"] == 0 and o["dirty"] is False and o["caret"] == cal["firstCaret"][d["doc"]]
                            and o["selectionCollapsed"] in (True, None))
        armMark = log_mark(session)
        pp_toasts0 = len(pp.evaluate(session, pp.READ_TOASTS) or [])
        make_selection(env, cal, d, rec)
        sel = selection_text(session)
        rec["selection"] = {"text": sel["text"], "expected": d["expected"],
                            "matches": (d["expected"] is None) or norm_newlines(sel["text"]) == d["expected"]}
        pre = editor_state(session)
        rec["beforeKey"] = {"caret": pre["caret"], "selection": pre["selection"], "toolbar": toolbar_shape(session),
                            "selectionType": pre["selectionType"], "revision": pre["revision"]}
        if not rec["selection"]["matches"]:
            rec["status"] = "selection-mismatch"
        else:
            mark = log_mark(session)
            keys(session, browser, [key])
            log = wait_key_done(session, mark)
            quiet(session)
            time.sleep(0.3)
            quiet(session)
            rec["timing"] = timing_of(log)
            after = editor_state(session)
            rec["afterKey"] = {"caret": after["caret"], "selection": after["selection"],
                               "toolbar": toolbar_shape(session), "revision": after["revision"]}
            before_rev = after["revision"]
            type_hash(session, browser)
            time.sleep(0.3)
            settled = quiet(session)
            rec["afterHash"] = {"revision": editor_state(session)["revision"], "settled": settled.get("timedOut") is None}
            saved = save_paragraphs(session)
            rec["save"] = {"bytes": saved["bytes"], "sha256": saved["sha256"]}
            paras = saved["paragraphs"]
            rec["paragraphsAfter"] = paras
            flat = "\u0001".join(paras)
            idx = flat_index(flat)
            rec["hash"] = {"count": flat.count("#"), "flatIndex": idx}
            if idx is not None:
                pi, off = locate(paras, idx)
                rec["hash"].update({"paragraph": pi, "offset": off,
                                    "excerpt": flat[max(0, idx - 14):idx] .replace("\u0001", "|") + "<#>"
                                               + flat[idx + 1:idx + 15].replace("\u0001", "|")})
            ref = native.get((shape, key, "ref"))
            emu = native.get((shape, key, "emu"))
            rec["native"] = {"ref": ref, "emu": emu}
            rec["equalsNativeRef"] = bool(ref) and len(ref) == 1 and idx == ref[0]
            rec["equalsNativeEmu"] = bool(emu) and len(emu) == 1 and idx == emu[0]
            rec["status"] = "counted" if rec["fresh"] and idx is not None else "instrument-fault"
            if not rec["fresh"]:
                rec["faultWhy"] = "the document was not fresh at open"
        full = log_since(session, armMark)
        rec["toasts"] = toasts_in(full)
        rec["ppToasts"] = (pp.evaluate(session, pp.READ_TOASTS) or [])[pp_toasts0:]
        rec["pillStates"] = sorted({r["state"] for r in full if r["what"] == "pill"})
    except Exception as error:  # noqa: BLE001 -- recorded, the run goes on
        import traceback
        rec["status"] = "runner-error"
        rec["error"] = f"{type(error).__name__}: {error}"
        rec["trace"] = traceback.format_exc()[-1500:]
    rec["loadavgEnd"] = loadavg()
    rec["swapDuringArm"] = swap_delta(swap0)
    rec["elapsedS"] = round(time.time() - rec["startedAtEpoch"], 1)
    return rec


def run_shift_arms(env: Env, cal: dict, defs: dict, round_no: int) -> list[dict]:
    session, browser = env.session, env.browser
    out = []
    # --- shift-collapsed: caret at offset 9 of P2, Shift+Right x3 -> nothing moves, '#' lands at 9
    rec: dict = {"arm": "m4-shift-collapsed", "kind": "shift", "browser": browser, "round": round_no,
                 "loadavgStart": loadavg(), "page": env.current}
    try:
        d = defs["p2-forward"]
        rec["open"] = env.open_doc(d["doc"])
        armMark = log_mark(session)
        stop = cal["old"]["stops"][1]
        st = editor_state(session)
        click_at(session, st, stop["start"]["x"] + 250, mid(stop["start"]))
        keys(session, browser, ["Home"]); quiet(session)
        keys(session, browser, ["Right"] * 9); quiet(session)
        c0 = editor_state(session)
        rec["caretBefore"] = c0["caret"]
        mark = log_mark(session)
        for _ in range(3):
            keys(session, browser, ["Right"], shift=True)
            time.sleep(0.4)
        time.sleep(0.6)
        quiet(session)
        c1 = editor_state(session)
        rec["caretAfter"] = c1["caret"]
        rec["revisionBefore"], rec["revisionAfter"] = c0["revision"], c1["revision"]
        rec["selectionCollapsedAfter"] = (c1["selection"] or {}).get("collapsed")
        rec["toolbar"] = toolbar_shape(session)
        log = log_since(session, mark)
        rec["keydowns"] = [(r["key"], r["shift"]) for r in log if r["what"] == "keydown"]
        rec["latencyRecords"] = [r["latency"] for r in log if r["what"] == "latency"]
        type_hash(session, browser); time.sleep(0.3); quiet(session)
        saved = save_paragraphs(session)
        flat = "\u0001".join(saved["paragraphs"])
        idx = flat_index(flat)
        rec["hash"] = {"flatIndex": idx, "paragraph": locate(saved["paragraphs"], idx)[0] if idx is not None else None,
                       "offset": locate(saved["paragraphs"], idx)[1] if idx is not None else None}
        rec["paragraphsAfter"] = saved["paragraphs"]
        full = log_since(session, armMark)
        rec["toasts"] = toasts_in(full)
        rec["status"] = "counted"
    except Exception as error:  # noqa: BLE001
        import traceback
        rec["status"], rec["error"], rec["trace"] = "runner-error", f"{type(error).__name__}: {error}", traceback.format_exc()[-1500:]
    out.append(rec)
    # --- shift-range: a forward selection, Shift+Right x1 -> the selection is still there
    rec = {"arm": "m4-shift-range", "kind": "shift", "browser": browser, "round": round_no,
           "loadavgStart": loadavg(), "page": env.current}
    try:
        d = defs["p2-forward"]
        rec["open"] = env.open_doc(d["doc"])
        armMark = log_mark(session)
        make_selection(env, cal, d, rec)
        s0 = selection_text(session)
        e0 = editor_state(session)
        rec["before"] = {"text": s0["text"], "caret": e0["caret"], "selection": e0["selection"],
                         "toolbar": toolbar_shape(session), "revision": e0["revision"]}
        mark = log_mark(session)
        keys(session, browser, ["Right"], shift=True)
        time.sleep(1.0)
        quiet(session)
        s1 = selection_text(session)
        e1 = editor_state(session)
        rec["after"] = {"text": s1["text"], "caret": e1["caret"], "selection": e1["selection"],
                        "toolbar": toolbar_shape(session), "revision": e1["revision"]}
        log = log_since(session, mark)
        rec["keydowns"] = [(r["key"], r["shift"]) for r in log if r["what"] == "keydown"]
        rec["latencyRecords"] = [r["latency"] for r in log if r["what"] == "latency"]
        rec["toasts"] = toasts_in(log_since(session, armMark))
        rec["status"] = "counted"
    except Exception as error:  # noqa: BLE001
        import traceback
        rec["status"], rec["error"], rec["trace"] = "runner-error", f"{type(error).__name__}: {error}", traceback.format_exc()[-1500:]
    out.append(rec)
    return out


CONTROL_REPEATS = 3


def run_control_arms(env: Env, cal: dict, defs: dict, round_no: int) -> list[dict]:
    """EXTRA (added after the first counted round, which showed 280 ms key-to-move in arms whose move does
    not move).  Plain COLLAPSED carets on the patched page -- no selection, so the page takes its ordinary
    `editorAction` path, no click -- with a key that does move the caret and with the same key when the caret
    is already there (a no-op move).  Times key -> the move's latency record."""
    session, browser = env.session, env.browser
    out = []
    plan = [("move-Home", "Home", None), ("noop-Home", "Home", "Home"), ("move-End", "End", None), ("noop-End", "End", "End"),
            ("move-Right", "Right", None), ("noop-Up-at-top", "Up", "Up")]
    for rep in range(1, CONTROL_REPEATS + 1):
        for name, key, prime in plan:
            rec: dict = {"arm": f"ctl-{name}", "kind": "control", "key": key, "repeat": rep, "browser": browser,
                         "round": round_no, "page": env.current, "loadavgStart": loadavg()}
            try:
                rec["open"] = env.open_doc("arrow-selection")
                stop = cal["old"]["stops"][1] if name != "noop-Up-at-top" else cal["old"]["stops"][0]
                st = editor_state(session)
                c = stop["start"]
                click_at(session, st, c["x"] + 250, mid(c))
                if prime:     # bring the caret to where `key` will leave it, so the timed press changes nothing
                    keys(session, browser, [prime if prime != "Up" else "Home"]); quiet(session)
                    if prime == "Up":
                        keys(session, browser, ["Up"]); quiet(session)
                before = editor_state(session)["caret"]
                mark = log_mark(session)
                keys(session, browser, [key])
                log = wait_key_done(session, mark)
                quiet(session)
                rec["caretBefore"], rec["caretAfter"] = before, editor_state(session)["caret"]
                rec["moved"] = before != rec["caretAfter"]
                rec["timing"] = timing_of(log)
                rec["toasts"] = toasts_in(log)
                rec["status"] = "counted"
            except Exception as error:  # noqa: BLE001
                import traceback
                rec["status"], rec["error"], rec["trace"] = "runner-error", f"{type(error).__name__}: {error}", traceback.format_exc()[-1500:]
            out.append(rec)
    return out


REACH_DELTAS = [0, 100, 400, 900]


def run_reach_arms(env: Env, cal: dict, defs: dict, round_no: int) -> list[dict]:
    """EXTRA (not in the brief).  Does the page's own drag ever leave the visible caret at the END of line 1
    (the native shapes s1d / m1d did)?  For s1d and m1d: the drag's far end `delta` twips to the right of the
    end of line 1, for several deltas; no key is pressed.  Reads what the page reads before a key: the caret,
    the selection start / end rectangles, the selection text."""
    session, browser = env.session, env.browser
    out = []
    for shape in ("s1d", "m1d"):
        for delta in REACH_DELTAS:
            rec: dict = {"arm": f"reach-{shape}-{delta}", "kind": "reach", "shape": shape, "delta": delta,
                         "browser": browser, "round": round_no, "page": env.current, "loadavgStart": loadavg()}
            try:
                d = dict(defs[shape])
                stop = cal[d["stops"]]["stops"][d["stop"]]
                rec["open"] = env.open_doc(d["doc"])
                st = editor_state(session)
                c = stop["start"]
                click_at(session, st, c["x"] + 250, mid(c))
                keys(session, browser, ["Home"]); quiet(session)
                k = d["rights"][0]
                keys(session, browser, ["Right"] * k); quiet(session)
                a = editor_state(session)["caret"]
                far = {"x": min(stop["end"]["x"] + delta, st["docW"] - 200), "y": stop["end"]["y"], "height": stop["end"]["height"]}
                rec["anchor"], rec["far"], rec["lineEnd"] = a, far, stop["end"]
                drag(session, st, (a["x"], mid(a)), (far["x"], mid(far)))
                time.sleep(0.2); quiet(session)
                es = editor_state(session)
                sel = selection_text(session)
                rec["after"] = {"caret": es["caret"], "selectionStart": (es["selection"] or {}).get("start"),
                                "selectionEnd": (es["selection"] or {}).get("end"),
                                "rectangles": (es["selection"] or {}).get("rectangles"),
                                "text": sel["text"], "toolbar": toolbar_shape(session)}
                rec["status"] = "counted"
            except Exception as error:  # noqa: BLE001
                import traceback
                rec["status"], rec["error"], rec["trace"] = "runner-error", f"{type(error).__name__}: {error}", traceback.format_exc()[-1500:]
            out.append(rec)
    return out


RED_ARMS = [("p2-forward", "Left"), ("p2-forward", "End"), ("p2-backward", "Down")]


def run_red_arms(env: Env, cal: dict, defs: dict, round_no: int) -> list[dict]:
    session, browser = env.session, env.browser
    out = []
    for shape, key in RED_ARMS:
        rec: dict = {"arm": f"red-{shape}-{key}", "kind": "red", "shape": shape, "key": key, "browser": browser,
                     "round": round_no, "loadavgStart": loadavg(), "page": env.current}
        try:
            d = defs[shape]
            rec["open"] = env.open_doc(d["doc"])
            armMark = log_mark(session)
            make_selection(env, cal, d, rec)
            sel = selection_text(session)
            rec["selection"] = {"text": sel["text"], "expected": d["expected"], "matches": sel["text"] == d["expected"]}
            rec["beforeKey"] = {"toolbar": toolbar_shape(session), "caret": editor_state(session)["caret"]}
            mark = log_mark(session)
            keys(session, browser, [key])
            log = wait_key_done(session, mark)
            time.sleep(0.5)
            quiet(session)
            log = log_since(session, mark)
            rec["timing"] = timing_of(log)
            rec["toasts"] = toasts_in(log)
            rec["ppToasts"] = pp.evaluate(session, pp.READ_TOASTS)
            rec["afterKey"] = {"toolbar": toolbar_shape(session), "caret": editor_state(session)["caret"],
                               "latency": (pp.evaluate(session, pp.READ_STATE) or {}).get("latency")}
            rec["refusedWithDeveloperSentence"] = any("EDITOR_FORMAT_GESTURE_UNSUPPORTED" in t for _, t in rec["toasts"])
            rec["status"] = "counted" if rec["selection"]["matches"] else "selection-mismatch"
        except Exception as error:  # noqa: BLE001
            import traceback
            rec["status"], rec["error"], rec["trace"] = "runner-error", f"{type(error).__name__}: {error}", traceback.format_exc()[-1500:]
        out.append(rec)
    return out


# --------------------------------------------------------------------------- main
def pages(final: bool) -> tuple[bytes, bytes]:
    """(page under test, red-control page) without the instrument line."""
    if final:
        return (DIST / "e2-editor-app.js").read_bytes(), gzip.decompress(OLD_PAGE_GZ.read_bytes())
    return MIRROR_PAGE.read_bytes(), (DIST / "e2-editor-app.js").read_bytes()


def preflight(docs_dir: Path, out: Path, final: bool = False) -> dict:
    """The mirror page = the shipped dist/ page + the 129 patch (web/ is NOT read: the main session has since
    edited it for 0.2.13); documents = the fixtures; hashes of everything.  (The first counted Chrome round
    checked the mirror against web/ + patch, which held then; web/ was equal to dist/ at that time.)"""
    pre: dict = {}
    dist = (DIST / "e2-editor-app.js").read_bytes()
    mirror = MIRROR_PAGE.read_bytes()
    pre["distPlusPatchSha256"] = None   # --final: dist/ already carries the fix, the patch does not apply
    if not final:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "dist-page.js"
            base.write_bytes(dist)
            patched = Path(tmp) / "patched.js"
            subprocess.run(["patch", "-s", "-o", str(patched), str(base), str(PATCH)], check=True)
            pre["distPlusPatchSha256"] = sha256_bytes(patched.read_bytes())
    pre.update({"distPageSha256": sha256_bytes(dist), "mirrorPageSha256": sha256_bytes(mirror),
                "patchSha256": sha256_bytes(PATCH.read_bytes()),
                "distIsTheExpectedShippedPage": sha256_bytes(dist) == EXPECTED_DIST_SHA256,
                "mirrorEqualsDistPlusPatch": sha256_bytes(mirror) == pre["distPlusPatchSha256"],
                "mirrorCheckedAgainst": "dist/e2-editor-app.js + page-129.patch (web/ not read)",
                "instrumentLine": INSTRUMENT_LINE,
                "patchedServedSha256": sha256_bytes(mirror + INSTRUMENT_LINE.encode()),
                "unpatchedServedSha256": sha256_bytes(dist + INSTRUMENT_LINE.encode())})
    texts = {}
    docs = {}
    for name, key in (("arrow-selection", "old"), ("arrow-selection-shapes", "shapes"), ("arrow-selection-wrap", "wrap")):
        odt = (docs_dir / f"{name}.odt").read_bytes()
        fodt = (FIXTURES / f"{name}.fodt").read_bytes()
        docs[name] = odt
        with zipfile.ZipFile(io.BytesIO(odt)) as z:
            t_odt = odt_paragraphs.paragraph_texts_from_xml(z.read("content.xml"))
        t_fodt = odt_paragraphs.paragraph_texts_from_xml(fodt)
        texts[key] = t_odt
        pre.setdefault("documents", {})[name] = {"odtSha256": sha256_bytes(odt), "fodtSha256": sha256_bytes(fodt),
                                                 "paragraphsEqualFodt": t_odt == t_fodt, "paragraphs": len(t_odt)}
    pre["runnerSha256"] = sha256_bytes(Path(__file__).read_bytes())
    if final:
        under, red = pages(True)
        pre["final"] = {"pageUnderTestSha256": sha256_bytes(under), "redControlSha256": sha256_bytes(red),
                        "pageUnderTestIsFinal": sha256_bytes(under) == FINAL_PAGE_SHA256,
                        "redControlIs0212": sha256_bytes(red) == EXPECTED_DIST_SHA256,
                        "patchedServedSha256": sha256_bytes(under + INSTRUMENT_LINE.encode()),
                        "unpatchedServedSha256": sha256_bytes(red + INSTRUMENT_LINE.encode())}
    return pre, texts, docs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--docs", type=Path, required=True, help="directory with the three converted .odt files")
    ap.add_argument("--phases", default="calibrate,arms,shift,reach,red")
    ap.add_argument("--arms", default=None, help="regex on the arm id m4-<shape>-<key>")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--round-label", type=int, default=1)
    ap.add_argument("--final", action="store_true", help="page under test = dist/ (0.2.13), red control = 0.2.12's page")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    phases = a.phases.split(",")
    pre, texts, docs = preflight(a.docs, a.out, a.final)
    report: dict = {"probe": "probe_129_m4_wasm.py", "browser": a.browser, "preflight": pre,
                    "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "startedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "loadavgStart": loadavg(), "memoryStartMb": memory_mb(), "phases": phases}
    if a.final and not (pre["final"]["pageUnderTestIsFinal"] and pre["final"]["redControlIs0212"]):
        report["fatal"] = "--final: dist/ is not the 0.2.13 page, or the archived red control is not 0.2.12's page"
        (a.out / f"report-{a.browser}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
        print(report["fatal"])
        return 2
    if not a.final and (not pre["mirrorEqualsDistPlusPatch"] or not pre["distIsTheExpectedShippedPage"]):
        report["fatal"] = "the mirror page is not dist + patch, or dist is not the expected shipped page"
        (a.out / f"report-{a.browser}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
        print(report["fatal"])
        return 2
    native = load_native()
    arms_path = a.out / f"arms-{a.browser}.jsonl"
    env = Env(a.browser, a.out)
    cal = None
    try:
        under, red = pages(a.final)
        env.serve("patched", under + INSTRUMENT_LINE.encode(), docs_to_files(docs))
        env.serve("unpatched", red + INSTRUMENT_LINE.encode(), docs_to_files(docs))
        env.start()
        report["version"] = getattr(env.session, "version", None)
        report["boot"] = env.goto("patched")
        cal_path = a.out / f"calibration-{a.browser}.json"
        if "calibrate" in phases:
            cal = calibrate(env, texts)
            cal_path.write_text(json.dumps(cal, indent=1, ensure_ascii=False))
        elif cal_path.exists():
            cal = json.loads(cal_path.read_text())
        defs = shape_defs(cal, texts) if cal else None
        if cal:
            report["wrapOffsets"] = {"s1": cal["s1Walk"]["wrapOffsets"], "token": cal["m1Walk"]["wrapOffsets"],
                                     "s1Lines": cal["s1Lines"], "shapesStops": cal["shapesStops"]}
        with arms_path.open("a") as sink:
            def emit(r: dict) -> None:
                sink.write(json.dumps(r, ensure_ascii=False).replace("\u2028", "\\u2028") + "\n")
                sink.flush()
                print(f"{r['arm']:28s} r{r.get('round')} {r.get('status')}"
                      f" ref={r.get('equalsNativeRef')} emu={r.get('equalsNativeEmu')}"
                      f" move={((r.get('timing') or {}).get('moveDoneMs'))}", flush=True)
            if "arms" in phases:
                for rnd in range(a.round_label, a.round_label + a.rounds):
                    for shape in defs:
                        for key in KEYS:
                            arm_id = f"m4-{shape}-{key}"
                            if a.arms and not re.search(a.arms, arm_id):
                                continue
                            emit(run_arm(env, cal, defs, texts, native, shape, key, rnd))
            if "shift" in phases:
                for r in run_shift_arms(env, cal, defs, a.round_label):
                    emit(r)
            if "control" in phases:
                for r in run_control_arms(env, cal, defs, a.round_label):
                    emit(r)
            if "reach" in phases:
                for r in run_reach_arms(env, cal, defs, a.round_label):
                    emit(r)
            if "red" in phases:
                report["bootUnpatched"] = env.goto("unpatched")
                for r in run_red_arms(env, cal, defs, a.round_label):
                    emit(r)
    except Exception:  # noqa: BLE001
        import traceback
        report["fatal"] = traceback.format_exc()
        print(report["fatal"])
    finally:
        report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        report["completedAtUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        report["loadavgEnd"] = loadavg()
        report["memoryEndMb"] = memory_mb()
        env.close()
        (a.out / f"report-{a.browser}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


def docs_to_files(docs: dict) -> dict:
    return {f"{name}.odt": data for name, data in docs.items()}


if __name__ == "__main__":
    sys.exit(main())
