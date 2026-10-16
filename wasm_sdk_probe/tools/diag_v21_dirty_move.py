#!/usr/bin/env python3
"""Diagnostic for the v21 shakedown: typing and arrows around a document move.  RECORDED, NEVER JUDGED.

Why (findings/evidence/link-batch-v21/shakedown/smoke/item1/README.md, "Observations" and "Product red"):
  1. In a dirty document the first Ctrl+End sends a checkpoint `save` first, and the move then completes
     `verified-move-readback` with the OLD caret; an engine ask later shows the caret at the end.  Spec
     SPEC-M3-link-batch-v21.md §9.1 names the consequence L-142-readback-overtaken (typing goes through
     a sync command that may run before Writer's GoToEndOfDoc).  Does it happen to typing?
  2. The move keys take the click-then-move path (`moveFromPoint`) while a delete is in flight, because
     the delete barrier's one-character range reads as the user's (web/e2-editor-app.js: the arrows'
     keydown path and `sendDocumentMove`; neither checks `deletesInFlight`).  Do arrows show it too?

Variants (`--variants`, comma-separated; every round is a fresh load and open):
  v1   plain3, dirty: real Z at the start (reply awaited), real Ctrl+End, real Q 30 ms after its keydown
  v2   as v1, but Q 50 ms after the move's reply arrives (polled from the observer's node)
  v3   as v1 without the Z: clean, no checkpoint (the control)
  v4   as v1 on long60 (create_long_document.build(60), as the item-1 runner builds it)
  v5   the Markdown dialog: paste `# a` with the clipboard instrument (D6's route), click 插入, then one
       real Z 0 ms (v5-0) or 300 ms (v5-300) after the dialog closes; added control v5-late (delayMs -1):
       Z once the page is quiet (ready, nothing pending, 0.5 s) plus 1 s.  Every v5 round then types Y
       (no click) and, after a real click at the engine's caret, X: does typing come back, and when?
       Added control v5-no-dialog (delayMs -2): the clipboard instrument's steps, no dialog, then Z, Y, X.
  v6   plain3, caret at «Bravo|» (k1024,k1027x5): Backspace @0, ArrowRight @20, Delete @40, on the v21
       page AND on the 0.2.24 page (dist/'s page, shell and v20 profile, as the item-1 runner's d8red)
  v6e  (added) as v6 with D8 (e)'s exact shape, ArrowRight in Ctrl+End's place: Backspace @0,
       Backspace @20, ArrowRight @40, Delete @60; both pages

Follow-up variants (2026-10-17, the coordinator's list; "(added)" = mine):
  v7   plain3, dirty: toolbar save, X ms after its reply Ctrl+End, Q 30 ms later; X in 0, 300, 1000, 3000
       (N=--rounds for 0 and 1000, 1 for the others)
  v8   plain3: Z at the start, «Bravo|», then ArrowDown and Q 30 ms later
  v8d  (added) «Bravo|» first, then Z there, so the ArrowDown is the first move after the change
  d11b the item-1 runner's arm_d11b, reused (with --fix fix1: no save request, unsaved stays true?)
  d8e  the item-1 runner's run_d8(..., ["e"]), reused
  range a real drag selecting `second`, then a real ArrowRight (the range path with no delete out)
  v11a-e (Chrome) after the Markdown dialog: (a) Input.insertText, (b) blur+focus then a key, (c) 取消 with no
       paste, (d) 插入 refused on a range then 取消, (e) Ctrl+V of plain text into the sink
  v11f the V5 step on the 0.2.24 page: recorded as not run (that page has no <dialog>)
  V11g (--headed, Chrome): v5 (with --v5-delays) and v11c in a headed Chrome on the owner's display; the shared
       launcher's flags minus `--headless=new` (HeadedChromeSession)

Candidate fixes (`--fix`), applied to the SERVED files in the mirror only, never the tree (FixPages):
  fix1   editor-shell-v2/narrow-editor-v2-session.js action(): Ctrl+Home/End take no checkpoint
  fix2   the page (web/e2-editor-app.js, repointed to v21): `deletesInFlight === 0 &&` in front of the arrow
         path's and sendDocumentMove's range decision (finding 131's rule A)
  fix12  both
  fix1p  (fix 1') no checkpoint before any of the eight moves (`if (false && BOUNDARY_CAPABLE_MOVES...`)
  fix3   closeMarkdownDialog: `el.sink.blur(); el.sink.focus(...)` in place of the focus alone
  fix3b  closeMarkdownDialog: `requestAnimationFrame(() => el.sink.focus(...))`
Third round (2026-10-17): v8d0224 (V8d on the 0.2.24 page), bup (fix1' boundary control: dirty, Home,
ArrowUp, Q 30 ms later).
The report states `candidateFix` with each patched file's sha256 and edits.

Reused, not copied: the item-1 runner's `Pages` (S-1 mirrors), `Ctx` (load/open/start/ask/quiet/save,
the observer log), `run_script` and `element_center`; v21_input (keys), v21_clipboard (the dialog's
paste), v21_shakedown_common (S-9 lock, pre-run checks, foreign-CPU sample), v21_item1_marker
(paragraphs via the S-7 adapter).  New here: timed key sequences (Firefox: ONE WebDriver chain with
pauses, so a 20/30 ms gap is not eaten by per-press HTTP round trips), a reply-triggered key (v2), and a
small in-page recorder for v5 (dialog close, sink disabled/readOnly, focus, keypress, beforeinput).

  diag_v21_dirty_move.py --browser chrome --variants v1,v2,v3,v4,v5,v6 --rounds 3 --out DIR --wait-lock 7200
  diag_v21_dirty_move.py --table DIR        markdown tables from every report in DIR (no browser)

Every report says `"recordedNotJudged": true, "counted": false`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r7_support  # noqa: E402
import run_browser_probe as rbp  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import judge_v21_shakedown_item1 as judge1  # noqa: E402
import run_merge_wasm_shakedown as mws  # noqa: E402
import run_v20_shakedown as v20  # noqa: E402
import run_v21_shakedown_item1 as item1  # noqa: E402
import v21_clipboard as clip  # noqa: E402
import v21_input as inp  # noqa: E402
import v21_item1_marker as marker  # noqa: E402
import v21_item1_observer as obs1  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402

VARIANTS = ("v1", "v2", "v3", "v4", "v5", "v6", "v6e",
            "v7", "v8", "v8d", "d11b", "d8e", "range", "v11a", "v11b", "v11c", "v11d", "v11e", "v11f",
            "v8d0224", "bup")
CHROME_ONLY = ("v11a", "v11b", "v11c", "v11d", "v11e", "v11f")
V7_WAITS = ((0, None), (300, 1), (1000, None), (3000, 1))   # (X ms, rounds; None = --rounds)
RANGE_SECOND = "k1024,k1027x6,ra,k1027x6,rb,sa:b"           # «Bravo |second|» in P2, dragged a -> b

# Candidate fixes, applied to the SERVED copy in the mirror only (never the tree).  Each edit must match
# exactly once in the file it patches.
SESSION_FILE = "editor-shell-v2/narrow-editor-v2-session.js"
SESSION_EDITS = [(
    "        if (BOUNDARY_CAPABLE_MOVES.has(action))\n          await this._checkpointBeforeBoundaryMove(document);",
    "        if (BOUNDARY_CAPABLE_MOVES.has(action) && action !== \"move-document-start\" && action !== \"move-document-end\")\n"
    "          await this._checkpointBeforeBoundaryMove(document);")]
PAGE_EDITS = [
    ("  if (pointMovesInFlight === 0 && shape !== \"collapsed\"",
     "  if (deletesInFlight === 0 && pointMovesInFlight === 0 && shape !== \"collapsed\""),
    ("  const fromPoint = pointMovesInFlight === 0 && shape !== \"collapsed\"",
     "  const fromPoint = deletesInFlight === 0 && pointMovesInFlight === 0 && shape !== \"collapsed\""),
]
# fix1': no checkpoint before any of the eight moves.
SESSION_EDITS_ALL = [(
    "        if (BOUNDARY_CAPABLE_MOVES.has(action))\n          await this._checkpointBeforeBoundaryMove(document);",
    "        if (false && BOUNDARY_CAPABLE_MOVES.has(action))\n          await this._checkpointBeforeBoundaryMove(document);")]
# fix3 / fix3b: closeMarkdownDialog's focus (the anchor carries the line before it: the same focus line also
# ends the toolbar's mousedown handler).
FOCUS_ANCHOR = "  el.markdownInsert.disabled = false;\n  if (session) el.sink.focus({ preventScroll: true });\n}"
FOCUS_EDITS = [(FOCUS_ANCHOR, "  el.markdownInsert.disabled = false;\n"
                              "  if (session) { el.sink.blur(); el.sink.focus({ preventScroll: true }); }\n}")]
FOCUS_RAF_EDITS = [(FOCUS_ANCHOR, "  el.markdownInsert.disabled = false;\n"
                                  "  if (session) requestAnimationFrame(() => el.sink.focus({ preventScroll: true }));\n}")]
EDITS_OF = {"session": ("session", SESSION_EDITS), "session_all": ("session", SESSION_EDITS_ALL),
            "page": ("page", PAGE_EDITS), "focus": ("page", FOCUS_EDITS), "focus_raf": ("page", FOCUS_RAF_EDITS)}
FIXES = {"none": (), "fix1": ("session",), "fix2": ("page",), "fix12": ("session", "page"),
         "fix1p": ("session_all",), "fix3": ("focus",), "fix3b": ("focus_raf",)}
FIX_WHAT = {"none": "no candidate fix",
            "fix1": "fix 1: Ctrl+Home/End take no checkpoint (session action())",
            "fix2": "fix 2: finding 131's rule A (deletesInFlight === 0) in the arrow path and sendDocumentMove (page)",
            "fix12": "fix 1 and fix 2 together",
            "fix1p": "fix 1': no checkpoint before any of the eight moves (session action(), `false &&`)",
            "fix3": "fix 3: closeMarkdownDialog blurs the sink, then focuses it (page)",
            "fix3b": "fix 3b: closeMarkdownDialog focuses the sink in requestAnimationFrame (page)"}
# The tree's page after 712f955a (fixes 1 and 2, item 2's entry off), as v21_shakedown_common.EXPECTED
# (re-pinned at f5f60ac1).  Was 3d5112161b23b060 (ARMS.md §1); §34.4 witness:
# findings/evidence/link-batch-v21/shakedown/evidence/witness/diag-v6e-stale-pin/.
V21_PAGE_PREFIX = "605cf24b3dff5a2d"
LOG_KINDS = ("kd", "kdp", "rq", "rs", "bi", "ask7post", "ask7", "askx")
PLACEMENT_BRAVO = "k1024,k1027x5"
V6_KEYS = [(0, "Backspace", ()), (20, "ArrowRight", ()), (40, "Delete", ())]
# Added: D8 (e)'s exact shape with ArrowRight in Ctrl+End's place (item-1 runner D8_SEQUENCES["e"]).
V6E_KEYS = [(0, "Backspace", ()), (20, "Backspace", ()), (40, "ArrowRight", ()), (60, "Delete", ())]
KEYS_OF = {"v6": V6_KEYS, "v6e": V6E_KEYS}
V5_TEXT = "# a"
StepError = item1.StepError


# ------------------------------------------------------------------ new instruments (small)

def timed_keys(ctx: item1.Ctx, steps: list[tuple[int, str, tuple]]) -> dict:
    """Real presses at offsets (ms).  Chrome: CDP presses on the monotonic clock (v21_input.schedule).
    Firefox: one WebDriver action chain with `pause` actions between the presses.  The page's own
    keydown times (the observer's `kd`) are what the report's gaps are computed from."""
    if ctx.browser == "chrome":
        sent = inp.schedule([(t, (lambda n=n, m=m: inp.key(ctx.session, "chrome", n, m))) for t, n, m in steps])
        return {"how": "cdp-schedule", "plannedMs": [t for t, _, _ in steps], "sentMs": sent}
    actions, previous = [], 0
    for t, name, mods in steps:
        if t > previous:
            actions.append({"type": "pause", "duration": t - previous})
        actions += inp._wd_press_actions(name, mods)  # noqa: SLF001  (the instrument's own press shape)
        previous = t
    t0 = time.monotonic()
    inp._wd_perform(ctx.session, actions)  # noqa: SLF001
    return {"how": "webdriver-chain-with-pauses", "plannedMs": [t for t, _, _ in steps],
            "chainMs": round((time.monotonic() - t0) * 1000, 1)}


PEEK_REPLY = (
    "(() => { const n = document.getElementById('v21-i1'); if (!n) return null; let log;"
    " try { log = JSON.parse(n.textContent || '[]'); } catch (e) { return null; }"
    " const hit = log.find((e) => e.k === 'rs' && e.op === ARG_OP && (ARG_ACTION === null || e.action === ARG_ACTION)"
    " && e.s > ARG_LAST); return hit ? { t: hit.t, now: Math.round(performance.now() * 10) / 10 } : null; })()")


def after_reply(ctx: item1.Ctx, last_seq: int, op: str, action: str | None, after_ms: float, then,
                limit: float = 30.0) -> dict:
    """Poll the observer's node for the first reply to `op` (and `action`) after `last_seq`; call `then()`
    `after_ms` after that reply (page clock).  The report's gaps are computed from the page's own times."""
    deadline = time.monotonic() + limit
    probe = (PEEK_REPLY.replace("ARG_LAST", str(last_seq)).replace("ARG_OP", json.dumps(op))
             .replace("ARG_ACTION", json.dumps(action)))
    while time.monotonic() < deadline:
        hit = pp.evaluate(ctx.session, probe)
        if hit:
            lag = hit["now"] - hit["t"]
            usable = 0 <= lag < 1000
            wait = max(0.0, after_ms - lag) if usable else after_ms
            time.sleep(wait / 1000)
            done = then()
            return {"replyT": hit["t"], "seenLagMs": round(lag, 1), "lagUsable": usable, "sleptMs": round(wait, 1),
                    **({"then": done} if isinstance(done, dict) else {})}
        time.sleep(0.002)
    raise StepError(f"no {op} {action or ''} reply within {limit} s")


def key_after_move_reply(ctx: item1.Ctx, last_seq: int, name: str, after_ms: float, limit: float = 30.0) -> dict:
    """V2: press `name` `after_ms` after the move-document-end reply (page clock)."""
    return after_reply(ctx, last_seq, "editorActionV2", "move-document-end", after_ms,
                       lambda: inp.key(ctx.session, ctx.browser, name), limit)


# ------------------------------------------------------------------ V11g: a headed Chrome

class HeadedChromeSession(rbp.ChromeSession):
    """V11g: the shared launcher's Chrome without `--headless=new`, on the display this process has
    (DISPLAY / WAYLAND_DISPLAY).  run_browser_probe.ChromeSession hardcodes that flag and is a shared file, so
    this drops that ONE argument while the shared __init__ runs; every other flag and step (profile dir,
    warm-up, CDP enables) is the shared one.  Refuses if the flag was not there to drop (it would be headless)."""

    def __init__(self, cache_mode: str):
        real = rbp.subprocess.Popen
        seen: dict = {}

        def popen(args, *rest, **kwargs):
            if isinstance(args, list) and "--headless=new" in args:
                args = [a for a in args if a != "--headless=new"]
                seen["argv"] = list(args)
            return real(args, *rest, **kwargs)

        rbp.subprocess.Popen = popen
        try:
            super().__init__(cache_mode)
        finally:
            rbp.subprocess.Popen = real
        if "argv" not in seen:
            self.close()
            raise SystemExit("headed launch: the shared launcher had no --headless=new to drop; refusing")
        self.argv = seen["argv"]
        self.display = {k: os.environ.get(k) for k in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_SESSION_TYPE")}


def open_headed(window: tuple[int, int]):
    """common.open_browser's Chrome branch, headed."""
    session = HeadedChromeSession("cold")
    session.call("Emulation.setDeviceMetricsOverride",
                 {"width": window[0], "height": window[1], "deviceScaleFactor": 1, "mobile": False})
    return session


def v5_jobs(spec: str, rounds: int) -> list[tuple[int, int]]:
    """`--v5-delays`: comma-separated delay[:rounds]; delay is ms, `late` or `no-dialog`."""
    jobs = []
    for token in [t for t in spec.split(",") if t]:
        name, _, count = token.partition(":")
        delay = {"late": LATE, "no-dialog": NO_DIALOG}.get(name)
        delay = int(name) if delay is None else delay
        jobs += [(delay, n) for n in range(1, int(count or rounds) + 1)]
    return jobs


# ------------------------------------------------------------------ candidate fixes (mirror only)

def apply_edits(text: str, edits: list[tuple[str, str]], name: str) -> str:
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"candidate fix: {name} holds the anchor {text.count(old)} times, not once: {old[:60]!r}")
        text = text.replace(old, new)
    return text


def patch_served_file(mirror: Path, relative: str, edits: list[tuple[str, str]]) -> dict:
    """Replace one SERVED file in the mirror with its patched text.  Refuses when the file, or any directory
    between the mirror and it, is a symlink (the mirror symlinks into dist/; never write through one)."""
    path = mirror / relative
    for parent in Path(relative).parents:
        if parent != Path(".") and (mirror / parent).is_symlink():
            raise SystemExit(f"candidate fix: {mirror / parent} is a symlink; refusing to write under it")
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"candidate fix: {path} is not a materialised file in the mirror; refusing")
    original = path.read_bytes()
    patched = apply_edits(original.decode("utf-8"), edits, relative).encode("utf-8")
    path.unlink()
    path.write_bytes(patched)
    tree = common.PROJECT / relative
    return {"path": relative, "originalServedSha256": common.sha256_bytes(original),
            "treeSha256": common.sha256_file(tree) if tree.is_file() else None,
            "patchedSha256": common.sha256_bytes(patched), "servedSha256": common.sha256_file(path),
            "edits": edits}


class FixPages(item1.Pages):
    """The item-1 runner's Pages, plus a candidate fix applied to the v21 mirror only."""

    def __init__(self, scratch: Path, fixtures: dict[str, bytes], fix: str):
        super().__init__(scratch, fixtures, None)
        self.fix = fix
        self.candidate = {"name": fix, "what": FIX_WHAT[fix], "files": {}}

    def base(self, variant: str) -> str:
        if variant != "v21" or self.fix == "none" or variant in self.servers:
            return super().base(variant)
        parts = FIXES[self.fix]
        page_edits = [e for p in parts if EDITS_OF[p][0] == "page" for e in EDITS_OF[p][1]]
        session_edits = [e for p in parts if EDITS_OF[p][0] == "session" for e in EDITS_OF[p][1]]
        extra = {f"v21-fx-{name}.odt": raw for name, raw in self.fixtures.items()}
        extra.update(self.extra)
        source = common.PAGE_SOURCE.read_text(encoding="utf-8")
        manifest = common.DIST / "profiles" / common.DEFAULT_PROFILE / "sdk-manifest.json"
        kwargs = {}
        if page_edits:
            patched = apply_edits(source, page_edits, "web/e2-editor-app.js")
            unpatched_served = pp.repointed_page(source, common.DEFAULT_PROFILE, manifest)[0]
            patched_served = pp.repointed_page(patched, common.DEFAULT_PROFILE, manifest)[0]
            undone = patched_served
            for old, new in page_edits:
                undone = undone.replace(new, old)
            self.candidate["files"]["e2-editor-app.js"] = {
                "path": "e2-editor-app.js (served; source web/e2-editor-app.js repointed to e2-editor-v21)",
                "unpatchedServedSha256": common.sha256_bytes(unpatched_served.encode("utf-8")),
                "patchedServedSha256": common.sha256_bytes(patched_served.encode("utf-8")),
                "patchOnly": undone == unpatched_served, "edits": page_edits}
            kwargs["source_page"] = patched
        mirror = self.scratch / f"mirror-v21-{self.fix}"
        identity = common.build_mirror(mirror, snippets=[v20.OBSERVER, obs1.SNIPPET], extra_files=extra, **kwargs)
        if session_edits:
            self.candidate["files"][SESSION_FILE] = patch_served_file(mirror, SESSION_FILE, session_edits)
        if page_edits:
            served = identity["pageServedSha256"]
            if served != self.candidate["files"]["e2-editor-app.js"]["patchedServedSha256"]:
                raise SystemExit("candidate fix: the mirror serves a page other than the patched one")
        identity["shellDigestAfterFix"] = mws.shell_digest(mirror)
        identity["candidateFix"] = self.candidate
        ctx = common.served(mirror)
        url = ctx.__enter__()
        self._stack.append(ctx)
        self.servers[variant] = (url, identity)
        self.identity[variant] = identity
        return url


RECORDER = r"""(() => {
  if (document.getElementById('diag-dm')) return;
  const node = document.createElement('script'); node.type = 'application/json'; node.id = 'diag-dm';
  document.head.appendChild(node);
  const log = [];
  const now = () => Math.round(performance.now() * 10) / 10;
  const sink = document.querySelector('#sink'), dialog = document.querySelector('#markdown-dialog');
  const idOf = (el) => el ? (el.id || el.tagName) : null;
  const snap = () => ({ sinkDisabled: sink ? sink.disabled : null, sinkReadOnly: sink ? sink.readOnly : null,
                        active: idOf(document.activeElement), dialogOpen: dialog ? dialog.open : null,
                        hasFocus: document.hasFocus(), sinkInert: sink ? (sink.inert ?? null) : null,
                        closestInert: sink ? idOf(sink.closest('[inert]')) : null,
                        pointerEvents: sink ? getComputedStyle(sink).pointerEvents : null });
  const put = (e) => { log.push({ t: now(), ...e, ...snap() }); node.textContent = JSON.stringify(log); };
  if (dialog) new MutationObserver((rs) => { for (const r of rs) put({ k: 'mut', target: 'dialog', attr: r.attributeName }); })
    .observe(dialog, { attributes: true, attributeFilter: ['open'] });
  if (sink) new MutationObserver((rs) => { for (const r of rs) put({ k: 'mut', target: 'sink', attr: r.attributeName }); })
    .observe(sink, { attributes: true, attributeFilter: ['disabled', 'readonly'] });
  window.addEventListener('keydown', (e) => put({ k: 'kd', key: e.key, target: idOf(e.target) }), true);
  window.addEventListener('keypress', (e) => put({ k: 'kp', key: e.key, target: idOf(e.target) }), true);
  window.addEventListener('keypress', (e) => put({ k: 'kpp', key: e.key, prevented: e.defaultPrevented }));
  document.addEventListener('focusin', (e) => put({ k: 'focusin', target: idOf(e.target) }), true);
  window.addEventListener('beforeinput', (e) => put({ k: 'bi', type: e.inputType, data: e.data ?? null, target: idOf(e.target) }), true);
  window.addEventListener('input', (e) => put({ k: 'in', type: e.inputType, data: e.data ?? null, target: idOf(e.target) }), true);
  document.documentElement.addEventListener('diag-mark', (e) => put({ k: 'mark', what: e.detail ?? null }));
  put({ k: 'installed' });
})();"""
MARK = "document.documentElement.dispatchEvent(new CustomEvent('diag-mark', { detail: ARG }));"
READ_RECORDER = "(() => { const n = document.getElementById('diag-dm'); return n ? JSON.parse(n.textContent || '[]') : null; })()"
AFTER_Z = ("(() => { const s = document.querySelector('#sink'), m = document.querySelector('#markdown-text');"
           " const a = document.activeElement; return { sinkValue: s ? s.value : null, markdownValue: m ? m.value : null,"
           " active: a ? (a.id || a.tagName) : null }; })()")
LATE = -1        # v5's added control: Z once the page is quiet (ready, nothing pending) plus 1 s
NO_DIALOG = -2   # v5's added control: the clipboard instrument's steps, no dialog, then Z
DELAY_LABEL = {LATE: "late", NO_DIALOG: "no-dialog"}


# ------------------------------------------------------------------ reading what was recorded

def paragraphs(raw: bytes) -> list[str]:
    return [t for _, _, t in marker.paragraphs_of(raw)]


def hits(texts: list[str], ch: str) -> list[dict]:
    return [{"para": i, "offset": off, "text": t[:70]} for i, t in enumerate(texts) for off, c in enumerate(t) if c == ch]


def q_class(texts: list[str], dirty: bool) -> str:
    q = hits(texts, "Q")
    if len(q) != 1:
        return f"{len(q)} Q in the saved document"
    h = q[0]
    if h["para"] == len(texts) - 1 and h["offset"] == len(texts[-1]) - 1:
        return "document end"
    if h["para"] == 0 and texts[0][:h["offset"]] == ("Z" if dirty else ""):
        return "pre-move caret"
    return f"elsewhere: para {h['para']} offset {h['offset']}"


def first(log: list[dict], pred) -> dict | None:
    return next((e for e in log if pred(e)), None)


def timeline(log: list[dict], t0: float | None) -> list[str]:
    """Compact request/response order relative to `t0` (the first key's keydown, page clock)."""
    out = []
    for e in log:
        if e.get("k") not in ("kd", "rq", "rs", "bi"):
            continue
        dt = (e.get("t", 0) - t0) if t0 is not None else e.get("t", 0)
        if e["k"] == "kd":
            if e.get("key") in ("Control", "Shift"):
                continue
            what = f"KEY {'Ctrl+' if e.get('ctrl') else ''}{e.get('key')}"
        elif e["k"] == "bi":
            what = f"beforeinput {e.get('type')} {e.get('data')!r}"
        elif e["k"] == "rq":
            if e.get("ask"):
                continue
            what = f"rq {e.get('action') or e.get('op')}"
        else:
            if e.get("rq", 0) >= 0x7E000000:
                continue
            caret = e.get("caret") or {}
            what = (f"rs {e.get('action') or e.get('op')} {e.get('completion') or ('ok' if e.get('ok') else e.get('code'))}"
                    + (f" caret {caret.get('x')},{caret.get('y')}" if caret else ""))
        out.append(f"{dt:+8.1f} {what}")
    return out


def caret_str(c) -> str | None:
    return f"{c.get('x')},{c.get('y')}" if isinstance(c, dict) else None


def summarise_move(rec: dict, dirty: bool) -> dict:
    log = rec.get("log", [])
    end_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "End")
    q_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "Q")
    move = first(log, lambda e: e.get("k") == "rs" and e.get("action") == "move-document-end")
    ask7 = first(log, lambda e: e.get("k") == "ask7" and move is not None and e.get("forRq") == move.get("rq"))
    ins = first(log, lambda e: e.get("k") == "rs" and e.get("op") == "insertText")
    texts = rec.get("savedTexts") or []
    t0 = end_kd.get("t") if end_kd else None
    return {
        "qClass": q_class(texts, dirty) if texts else "no saved document",
        "qHits": hits(texts, "Q"), "zHits": hits(texts, "Z"),
        "gapEndKdToQKdMs": round(q_kd["t"] - end_kd["t"], 1) if end_kd and q_kd else None,
        "gapMoveReplyToQKdMs": round(q_kd["t"] - move["t"], 1) if move and q_kd else None,
        "moveCompletion": move and move.get("completion"), "moveRoundTripMs": move and round(move["t"] - move["tRq"], 1),
        "moveReplyCaret": caret_str(move and move.get("caret")),
        "ask7Caret": caret_str(ask7 and ask7.get("caret")), "ask7AfterReplyMs": ask7 and move and round(ask7["tPosted"] - move["t"], 1),
        "insertTextCompletion": ins and (ins.get("completion") or ("ok" if ins.get("ok") else ins.get("code"))),
        "insertTextCaret": caret_str(ins and ins.get("caret")),
        "qBeforeinput": [e.get("type") for e in log if e.get("k") == "bi"],
        "order": [e.get("action") or e.get("op") for e in log if e.get("k") == "rq" and not e.get("ask")],
        "timeline": timeline(log, t0),
    }


def expected_in_order(text: str, caret: int, keys: list[str]) -> str:
    """The P2 text if each key were applied in order on a caret (no range)."""
    for key in keys:
        if key == "Backspace" and caret > 0:
            text, caret = text[:caret - 1] + text[caret:], caret - 1
        elif key == "Delete" and caret < len(text):
            text = text[:caret] + text[caret + 1:]
        elif key == "ArrowRight":
            caret = min(len(text), caret + 1)
        elif key == "ArrowLeft":
            caret = max(0, caret - 1)
    return text


def summarise_d11b(rec: dict) -> dict:
    """The item-1 runner's arm_d11b round (reused as V9's D11b-like check)."""
    presses = rec.get("presses") or []
    requests = rec.get("requests") or []
    return {
        "kind": rec.get("kind"), "requests": [r.get("action") or r.get("op") for r in requests],
        "saveRequests": sum(1 for r in requests if r.get("op") == "save"),
        "unsavedAtOpen": rec.get("unsavedAtOpen"), "unsavedAfterTyping": rec.get("unsavedAfterTyping"),
        "unsavedAfter": [p.get("unsavedAfter") for p in presses], "checkpoint": [p.get("checkpoint") for p in presses],
        "completions": [(p.get("response") or {}).get("completion") for p in presses],
        "replyCarets": [caret_str((p.get("response") or {}).get("caret")) for p in presses],
        "ask7Carets": [caret_str((p.get("ask7") or {}).get("caret")) for p in presses],
    }


def summarise_v6(rec: dict, keys: list, move_action: str = "move-character-right", expected: str | None = None) -> dict:
    log = rec.get("log", [])
    kds = [e for e in log if e.get("k") == "kd" and e.get("key") in ("Backspace", "ArrowRight", "Delete", "End")]
    t0 = kds[0]["t"] if kds else None
    reqs = [e for e in log if e.get("k") == "rq" and not e.get("ask")]
    labels = [e.get("action") or e.get("op") for e in reqs]
    first_delete = next((i for i, a in enumerate(labels) if str(a).startswith("delete")), None)
    move_i = next((i for i, a in enumerate(labels) if a == move_action), None)
    between = labels[first_delete + 1:move_i] if first_delete is not None and move_i is not None else []
    click_i = next((i for i, a in enumerate(between) if a in ("click", "editorPlaceCaretV2")), None)
    texts = rec.get("savedTexts") or []
    return {
        "p2": texts[1] if len(texts) > 1 else None,
        "expectedInOrder": expected or expected_in_order("Bravo second paragraph", 5, [k for _, k, _ in keys]),
        "keyGapsMs": [round(e["t"] - t0, 1) for e in kds] if t0 is not None else None,
        "order": labels,
        "betweenFirstDeleteAndMove": between,
        "placeCaretBeforeMove": click_i is not None,
        "deleteBetweenClickAndMove": click_i is not None and any(str(a).startswith("delete") for a in between[click_i:]),
        "timeline": timeline(log, t0),
    }


def summarise_v5(rec: dict) -> dict:
    log, recd = rec.get("log", []), rec.get("recorder") or []
    z_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "Z")
    closed = first(recd, lambda e: e.get("k") == "mut" and e.get("target") == "dialog" and e.get("dialogOpen") is False)
    # The first input's moment: Z's keydown, or (V11 a, e) the recorder's mark just before Input.insertText
    # or the Ctrl+V.  The observer and the recorder both stamp performance.now() on the same page.
    z_rec = (first(recd, lambda e: e.get("k") == "kd" and e.get("key") == "Z")
             or first(recd, lambda e: e.get("k") == "mark"))
    y_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "Y")
    y_rec = first(recd, lambda e: e.get("k") == "kd" and e.get("key") == "Y")
    z_t = z_rec["t"] if z_rec else (z_kd["t"] if z_kd else None)
    # Z's window: from that moment to Y's keydown (the added discriminator's first key), page clock.
    after_z = [e for e in log if z_t is not None and e.get("t", 0) >= z_t and (not y_kd or e.get("t", 0) < y_kd["t"])]
    rec_after_z = [e for e in recd if z_t is not None and e.get("t", 0) >= z_t and (not y_rec or e.get("t", 0) < y_rec["t"])]
    texts = rec.get("savedTexts") or []
    return {
        "startedBy": z_rec and (z_rec.get("what") or f"keydown {z_rec.get('key')}"),
        "atZ": z_rec and {k: z_rec.get(k) for k in ("active", "sinkDisabled", "sinkReadOnly", "sinkInert", "closestInert",
                                                     "pointerEvents", "dialogOpen", "hasFocus")},
        "wHits": hits(texts, "W"),
        "pasteBeforeinput": [f"{e.get('type')}@{e.get('target')}" for e in rec_after_z
                             if e.get("k") == "bi" and e.get("type") == "insertFromPaste"],
        "closeToZKdMs": round(z_rec["t"] - closed["t"], 1) if z_rec and closed else None,
        "zKeydownTarget": z_rec and z_rec.get("target"), "zKeydownActive": z_rec and z_rec.get("active"),
        "sinkDisabledAtZ": z_rec and z_rec.get("sinkDisabled"), "sinkReadOnlyAtZ": z_rec and z_rec.get("sinkReadOnly"),
        "documentHasFocusAtZ": z_rec and z_rec.get("hasFocus"),
        "zPrevented": (first(log, lambda e: e.get("k") == "kdp" and e.get("key") == "Z") or {}).get("prevented"),
        "zKeypress": any(e.get("k") == "kp" and e.get("key") == "Z" for e in recd),
        "zKeypressPrevented": (first(recd, lambda e: e.get("k") == "kpp" and e.get("key") == "Z") or {}).get("prevented"),
        "zBeforeinput": [e.get("type") for e in after_z if e.get("k") == "bi"],
        "anyBeforeinputAfterZ": [f"{e.get('type')}@{e.get('target')}" for e in rec_after_z if e.get("k") == "bi"],
        "anyInputAfterZ": [f"{e.get('type')}@{e.get('target')}" for e in rec_after_z if e.get("k") == "in"],
        "afterZ": rec.get("afterZ"),
        "insertTextAfterZ": any(e.get("k") == "rq" and e.get("op") == "insertText" for e in after_z),
        "sinkMutations": [(round(e["t"] - closed["t"], 1) if closed else e["t"], e.get("attr"), e.get("sinkDisabled"))
                          for e in recd if e.get("k") == "mut" and e.get("target") == "sink"],
        "focusins": [(round(e["t"] - closed["t"], 1) if closed else e["t"], e.get("target")) for e in recd if e.get("k") == "focusin"],
        "zHits": hits(texts, "Z"), "paragraphs": [t[:40] for t in texts[:4]],
        "yHits": hits(texts, "Y"), "xHits": hits(texts, "X"),
        "beforeinputData": [f"{e.get('data')}@{e.get('target')}" for e in recd if e.get("k") == "bi"],
        "clickOp": ((rec.get("click") or {}).get("response") or {}).get("op"),
        "order": [e.get("action") or e.get("op") for e in log if e.get("k") == "rq" and not e.get("ask")
                  and (not y_kd or e.get("t", 0) < y_kd["t"])],
        "orderAfterY": [e.get("action") or e.get("op") for e in log if e.get("k") == "rq" and not e.get("ask")
                        and y_kd and e.get("t", 0) >= y_kd["t"]],
    }


# ------------------------------------------------------------------ rounds

def settle_long(ctx: item1.Ctx) -> dict:
    """The item-1 D10 open: the first pageRectangles reply, then up to 40 s for all 60 parts."""
    _reply, entries = v20.settle_rects(ctx.session)
    ctx.trace.all += entries
    t0 = time.monotonic()
    while time.monotonic() - t0 < 40:
        latest = v20.latest_rects(ctx.trace.all)
        if latest and latest.get("parts") == 60:
            break
        time.sleep(1.0)
        ctx.drain()
    latest = v20.latest_rects(ctx.trace.all)
    return {"parts": latest and latest.get("parts")}


def settle_after(ctx: item1.Ctx) -> None:
    time.sleep(1.0)
    ctx.quiet(limit=60)
    time.sleep(0.5)
    ctx.quiet(limit=60)


def keep(ctx: item1.Ctx, rec: dict, mark: int, label: str) -> None:
    ctx.drain()
    rec["log"] = [e for e in ctx.log.all[mark:] if e.get("k") in LOG_KINDS]
    rec["save"] = ctx.save(label)
    if rec["save"].get("saved"):
        raw = (ctx.docs / f"{label}.odt").read_bytes()
        rec["savedTexts"] = paragraphs(raw)


def round_move(ctx: item1.Ctx, variant: str, label: str) -> dict:
    fixture = "long60" if variant == "v4" else "plain3"
    dirty = variant != "v3"
    rec = {"fixture": fixture, "dirty": dirty, "foreign": ctx.foreign()}
    rec["load"] = ctx.load("v21")
    rec["open"] = ctx.open(fixture)
    if fixture == "long60":
        rec["rects"] = settle_long(ctx)
    rec["start"] = ctx.start_state()
    if dirty:
        rec["typedZ"] = ctx.type_marker()
    ctx.ev_quiet()
    mark, last_seq = len(ctx.log.all), ctx.log.last
    if variant == "v2":
        inp.key(ctx.session, ctx.browser, "End", ("ctrl",))
        rec["sent"] = {"how": "after-move-reply", **key_after_move_reply(ctx, last_seq, "Q", 50)}
    else:
        rec["sent"] = timed_keys(ctx, [(0, "End", ("ctrl",)), (30, "Q", ())])
    return move_tail(ctx, rec, mark, label, dirty)


def move_tail(ctx: item1.Ctx, rec: dict, mark: int, label: str, dirty: bool) -> dict:
    """After Ctrl+End and Q: the move's reply, the insert, the +500 ms ask, quiet, a final ask, save."""
    move = ctx.wait_rs(mark, lambda e: e.get("op") == "editorActionV2" and e.get("action") == "move-document-end", 30)
    rec["insert"] = ctx.wait_rs(mark, lambda e: e.get("op") == "insertText", 30)
    if move is not None and move.get("ok"):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            ctx.log.drain()
            if any(e.get("k") == "ask7" and e.get("forRq") == move.get("rq") for e in ctx.log.all[mark:]):
                break
            time.sleep(0.05)
    settle_after(ctx)
    rec["finalAsk"] = (ctx.ask().get("full") or {})
    keep(ctx, rec, mark, label)
    rec["summary"] = summarise_move(rec, dirty)
    return rec


def round_v7(ctx: item1.Ctx, wait_ms: int, label: str) -> dict:
    """V7: dirty, toolbar save, X ms after its reply Ctrl+End, Q 30 ms after that keydown."""
    rec = {"waitMs": wait_ms, "fixture": "plain3", "dirty": True, "foreign": ctx.foreign()}
    rec["load"] = ctx.load("v21")
    rec["open"] = ctx.open("plain3")
    rec["start"] = ctx.start_state()
    rec["typedZ"] = ctx.type_marker()
    ctx.ev_quiet()
    mark, last_seq = len(ctx.log.all), ctx.log.last
    index = pp.evaluate(ctx.session, pp.SAVE_COUNT) or 0
    pp.evaluate(ctx.session, pp.PRESS.replace("ARG_ACTION", "save"))
    rec["sent"] = {"how": "after-toolbar-save-reply", **after_reply(
        ctx, last_seq, "save", None, wait_ms, lambda: timed_keys(ctx, [(0, "End", ("ctrl",)), (30, "Q", ())]))}
    rec["toolbarSaveDelivered"] = pp.wait_saves(ctx.session, index + 1, 60)
    move_tail(ctx, rec, mark, label, True)
    log = rec.get("log", [])
    save_rs = first(log, lambda e: e.get("k") == "rs" and e.get("op") == "save")
    end_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "End")
    move_rq = first(log, lambda e: e.get("k") == "rq" and e.get("action") == "move-document-end")
    rec["summary"]["waitActualMs"] = round(end_kd["t"] - save_rs["t"], 1) if save_rs and end_kd else None
    rec["summary"]["savesBeforeMove"] = len([e for e in log if e.get("k") == "rq" and e.get("op") == "save"
                                             and move_rq and e.get("t", 0) < move_rq["t"]])
    rec["summary"]["checkpointSaveAfterKey"] = any(e.get("k") == "rq" and e.get("op") == "save" and end_kd and move_rq
                                                   and end_kd["t"] <= e.get("t", 0) < move_rq["t"] for e in log)
    return rec


def round_v8(ctx: item1.Ctx, variant: str, label: str) -> dict:
    """V8 (as asked): Z at the start, then «Bravo|», then ArrowDown and Q 30 ms later.  V8d (added): «Bravo|»
    first, then Z there, so the ArrowDown is the first move after the change (it takes the checkpoint)."""
    page = "dist0224" if variant == "v8d0224" else "v21"
    rec = {"fixture": "plain3", "page": page, "foreign": ctx.foreign()}
    rec["load"] = ctx.load(page)
    rec["open"] = ctx.open("plain3")
    rec["start"] = ctx.start_state()
    if variant == "v8":
        rec["typedZ"] = ctx.type_marker()
        rec["placement"] = item1.run_script(ctx, PLACEMENT_BRAVO, "placement", None)["steps"]
    else:
        rec["placement"] = item1.run_script(ctx, PLACEMENT_BRAVO, "placement", None)["steps"]
        rec["typedZ"] = ctx.type_marker()
    return arrow_then_q(ctx, rec, label, "ArrowDown", "move-line-down",
                        {1: "P2 (the line before the move)", 2: "P3 (the line moved to)"})


def round_bup(ctx: item1.Ctx, label: str) -> dict:
    """fix1' boundary control: dirty plain3 (Z at the start), Home back to the document start, then a real
    ArrowUp (a boundary: there is no line above) and a real Q 30 ms later."""
    rec = {"fixture": "plain3", "page": "v21", "foreign": ctx.foreign()}
    rec["load"] = ctx.load("v21")
    rec["open"] = ctx.open("plain3")
    rec["start"] = ctx.start_state()
    rec["typedZ"] = ctx.type_marker()
    rec["home"] = ctx.move_key("Home")
    ctx.quiet()
    return arrow_then_q(ctx, rec, label, "ArrowUp", "move-line-up", {0: "P1"})


def arrow_then_q(ctx: item1.Ctx, rec: dict, label: str, key: str, action: str, lines: dict) -> dict:
    """A real arrow, a real Q 30 ms after its keydown; the arrow's reply, Q's landing, a final ask, save."""
    rec["beforeCaret"] = (ctx.ask().get("full") or {}).get("caret")
    ctx.ev_quiet()
    mark = len(ctx.log.all)
    rec["sent"] = timed_keys(ctx, [(0, key, ()), (30, "Q", ())])
    rec["move"] = ctx.wait_rs(mark, lambda e: e.get("op") == "editorActionV2" and e.get("action") == action, 30)
    rec["insert"] = ctx.wait_rs(mark, lambda e: e.get("op") == "insertText", 30)
    settle_after(ctx)
    rec["finalAsk"] = (ctx.ask().get("full") or {})
    keep(ctx, rec, mark, label)
    log = rec["log"]
    down = first(log, lambda e: e.get("k") == "kd" and e.get("key") == key)
    q_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "Q")
    move = first(log, lambda e: e.get("k") == "rs" and e.get("action") == action)
    texts = rec.get("savedTexts") or []
    q = hits(texts, "Q")
    rec["summary"] = {
        "qHits": q, "zHits": hits(texts, "Z"),
        "qLine": (lines.get(q[0]["para"], f"para {q[0]['para']}") if len(q) == 1 else f"{len(q)} Q"),
        "gapDownKdToQKdMs": round(q_kd["t"] - down["t"], 1) if down and q_kd else None,
        "moveCompletion": move and move.get("completion"), "moveRoundTripMs": move and round(move["t"] - move["tRq"], 1),
        "moveWaitedMs": move and move.get("waitedMs"), "moveChanged": move and move.get("changed"),
        "moveReplyCaret": caret_str(move and move.get("caret")), "finalCaret": caret_str(rec["finalAsk"].get("caret")),
        "beforeCaret": caret_str(rec.get("beforeCaret")),
        "order": [e.get("action") or e.get("op") for e in log if e.get("k") == "rq" and not e.get("ask")],
        "timeline": timeline(log, down and down.get("t")),
    }
    return rec


def round_range(ctx: item1.Ctx, label: str) -> dict:
    """V10's range control: a real drag selecting `second` in P2, then a real ArrowRight, no delete out."""
    rec = {"fixture": "plain3", "foreign": ctx.foreign()}
    rec["load"] = ctx.load("v21")
    rec["open"] = ctx.open("plain3")
    rec["start"] = ctx.start_state()
    script = item1.run_script(ctx, RANGE_SECOND, "range", None)
    rec["selectionText"] = script.get("rangeSelectionText")
    if rec["selectionText"] != "second":
        raise StepError(f"placement-mismatch: the drag selected {rec['selectionText']!r}, not 'second'")
    ctx.ev_quiet()
    mark = len(ctx.log.all)
    inp.key(ctx.session, ctx.browser, "ArrowRight")
    rec["move"] = ctx.wait_rs(mark, lambda e: e.get("op") == "editorActionV2" and e.get("action") == "move-character-right", 30)
    settle_after(ctx)
    rec["finalAsk"] = (ctx.ask().get("full") or {})
    keep(ctx, rec, mark, label)
    log = rec["log"]
    labels = [e.get("action") or e.get("op") for e in log if e.get("k") == "rq" and not e.get("ask")]
    move_i = labels.index("move-character-right") if "move-character-right" in labels else None
    texts = rec.get("savedTexts") or []
    rec["summary"] = {
        "selectionText": rec["selectionText"], "p2": texts[1] if len(texts) > 1 else None,
        "placeCaretBeforeMove": move_i is not None and any(a in ("click", "editorPlaceCaretV2") for a in labels[:move_i]),
        "moveCompletion": (rec["move"] or {}).get("completion"), "finalCaret": caret_str(rec["finalAsk"].get("caret")),
        "order": labels, "timeline": timeline(log, None),
    }
    return rec


def round_v5(ctx: item1.Ctx, delay_ms: int, label: str) -> dict:
    rec = {"delayMs": delay_ms, "foreign": ctx.foreign()}
    rec["load"] = ctx.load("v21")
    rec["open"] = ctx.open("plain3")
    rec["start"] = ctx.start_state()
    origin = pp.evaluate(ctx.session, "(() => location.origin)()")
    rec["grant"] = clip.grant(ctx.session, ctx.browser, origin)
    rec["clipboard"] = clip.write_text(ctx.session, V5_TEXT)
    r7_support.run_in_page(ctx.session, RECORDER)
    if delay_ms == NO_DIALOG:
        # Added control: the clipboard instrument's steps exactly as above, no dialog, then the same keys.
        r7_support.run_in_page(ctx.session, "document.querySelector('#sink').focus({ preventScroll: true });")
        time.sleep(0.3)
        ctx.drain()
        mark = len(ctx.log.all)
        inp.key(ctx.session, ctx.browser, "Z")
        time.sleep(0.3)
        rec["afterZ"] = pp.evaluate(ctx.session, AFTER_Z)
        settle_after(ctx)
        return finish_v5(ctx, rec, mark, label)
    mark = dialog_paste_insert(ctx, rec)
    if delay_ms == LATE:
        rec["lateQuiet"] = ctx.quiet(limit=30)
        time.sleep(1.0)
    elif delay_ms:
        time.sleep(delay_ms / 1000)
    inp.key(ctx.session, ctx.browser, "Z")
    time.sleep(0.3)
    rec["afterZ"] = pp.evaluate(ctx.session, AFTER_Z)
    settle_after(ctx)
    return finish_v5(ctx, rec, mark, label)


DIALOG_OPEN = "(() => document.querySelector('#markdown-dialog').open)()"


def open_dialog(ctx: item1.Ctx, rec: dict) -> None:
    entry = item1.element_center(ctx, '#toolbar [data-action="paste-markdown"]')
    if entry is None:
        raise StepError("no-entry: the paste-markdown button is hidden or missing")
    inp.click(ctx.session, ctx.browser, *entry)
    time.sleep(0.5)
    rec["dialogOpen"] = pp.evaluate(ctx.session, DIALOG_OPEN)


def paste_into_dialog(ctx: item1.Ctx, rec: dict) -> None:
    clip.press_ctrl_v(ctx.session, ctx.browser)
    time.sleep(0.8)
    rec["readback"] = clip.readback(ctx.session, "#markdown-text")
    if rec["readback"].get("sha256") != (rec["clipboard"] or {}).get("sha256"):
        raise StepError(f"input-mismatch: the textarea holds {rec['readback']}")


def click_and_wait_closed(ctx: item1.Ctx, rec: dict, selector: str, limit: float = 60.0) -> None:
    target = item1.element_center(ctx, selector)
    if target is None:
        raise StepError(f"no {selector}")
    inp.click(ctx.session, ctx.browser, *target)
    t0 = time.monotonic()
    closed_after = None
    while time.monotonic() - t0 < limit:
        if not pp.evaluate(ctx.session, DIALOG_OPEN):
            closed_after = round((time.monotonic() - t0) * 1000)
            break
    rec["dialogClosedAfterMs"] = closed_after
    if closed_after is None:
        raise StepError(f"the dialog did not close within {limit} s after {selector}")


def dialog_paste_insert(ctx: item1.Ctx, rec: dict) -> int:
    """D6's route: open the dialog, Ctrl+V the clipboard, check the textarea, click 插入, wait for the close.
    Returns the log mark taken just before 插入."""
    open_dialog(ctx, rec)
    paste_into_dialog(ctx, rec)
    ctx.drain()
    mark = len(ctx.log.all)
    click_and_wait_closed(ctx, rec, "#markdown-insert")
    return mark


def v11_start(ctx: item1.Ctx, rec: dict) -> None:
    rec["load"] = ctx.load("v21")
    rec["open"] = ctx.open("plain3")
    rec["start"] = ctx.start_state()
    origin = pp.evaluate(ctx.session, "(() => location.origin)()")
    rec["grant"] = clip.grant(ctx.session, ctx.browser, origin)
    rec["clipboard"] = clip.write_text(ctx.session, V5_TEXT)
    r7_support.run_in_page(ctx.session, RECORDER)


def round_v11(ctx: item1.Ctx, sub: str, label: str) -> dict:
    """V11 (Chrome): what the sink does after the Markdown dialog, (a)-(e)."""
    rec = {"sub": sub, "foreign": ctx.foreign()}
    v11_start(ctx, rec)
    if sub == "d":
        # A range first (`second` in P2), so 插入 is refused and the dialog stays open.
        script = item1.run_script(ctx, RANGE_SECOND, "range", None)
        rec["selectionText"] = script.get("rangeSelectionText")
        if rec["selectionText"] != "second":
            raise StepError(f"placement-mismatch: the drag selected {rec['selectionText']!r}, not 'second'")
    if sub == "c":
        open_dialog(ctx, rec)
        ctx.drain()
        mark = len(ctx.log.all)
        click_and_wait_closed(ctx, rec, "#markdown-cancel")
    elif sub == "d":
        open_dialog(ctx, rec)
        paste_into_dialog(ctx, rec)
        ctx.drain()
        mark = len(ctx.log.all)
        insert = item1.element_center(ctx, "#markdown-insert")
        if insert is None:
            raise StepError("no 插入 button")
        inp.click(ctx.session, ctx.browser, *insert)
        time.sleep(1.0)
        rec["refused"] = pp.evaluate(ctx.session, "(() => { const m = document.querySelector('#markdown-message');"
                                     " return { dialogOpen: document.querySelector('#markdown-dialog').open,"
                                     " message: m && !m.hidden ? m.textContent : null }; })()")
        if not (rec["refused"] or {}).get("dialogOpen"):
            raise StepError(f"the page did not refuse 插入 on a range: {rec['refused']}")
        click_and_wait_closed(ctx, rec, "#markdown-cancel")
    else:
        mark = dialog_paste_insert(ctx, rec)
    if sub == "a":
        r7_support.run_in_page(ctx.session, MARK.replace("ARG", json.dumps("insertText Z")))
        ctx.session.call("Input.insertText", {"text": "Z"})
    elif sub == "b":
        r7_support.run_in_page(ctx.session, "const s = document.querySelector('#sink'); s.blur(); s.focus();")
        time.sleep(0.1)
        inp.key(ctx.session, ctx.browser, "Z")
    elif sub == "e":
        rec["clipboardW"] = clip.write_text(ctx.session, "W")
        r7_support.run_in_page(ctx.session, MARK.replace("ARG", json.dumps("Ctrl+V W")))
        clip.press_ctrl_v(ctx.session, ctx.browser)
    else:
        inp.key(ctx.session, ctx.browser, "Z")
    time.sleep(0.3)
    rec["afterZ"] = pp.evaluate(ctx.session, AFTER_Z)
    settle_after(ctx)
    return finish_v5(ctx, rec, mark, label)


def finish_v5(ctx: item1.Ctx, rec: dict, mark: int, label: str) -> dict:
    # Added discriminator: a second key with no click (Y), then a real click at the engine's caret and X.
    inp.key(ctx.session, ctx.browser, "Y")
    settle_after(ctx)
    caret = (ctx.ask().get("full") or {}).get("caret")
    if caret:
        rec["click"] = ctx.click_caret(caret)
        inp.key(ctx.session, ctx.browser, "X")
        settle_after(ctx)
    rec["recorder"] = pp.evaluate(ctx.session, READ_RECORDER)
    keep(ctx, rec, mark, label)
    rec["summary"] = summarise_v5(rec)
    return rec


def round_v6(ctx: item1.Ctx, page: str, label: str, keys: list) -> dict:
    rec = {"page": page, "keys": keys, "foreign": ctx.foreign()}
    rec["load"] = ctx.load(page)
    rec["open"] = ctx.open("plain3")
    rec["start"] = ctx.start_state()
    rec["placement"] = item1.run_script(ctx, PLACEMENT_BRAVO, "placement", None)["steps"]
    rec["placementCaret"] = ((ctx.ask().get("full") or {}).get("caret"))
    ctx.ev_quiet()
    mark = len(ctx.log.all)
    rec["sent"] = timed_keys(ctx, keys)
    settle_after(ctx)
    keep(ctx, rec, mark, label)
    rec["summary"] = summarise_v6(rec, keys)
    return rec


def guarded(fn, *args) -> dict:
    try:
        rec = fn(*args)
        rec["outcome"] = "done"
    except StepError as error:
        rec = {"outcome": "step-error", "error": str(error)}
    except Exception as error:  # noqa: BLE001
        rec = {"outcome": "runner-error", "error": f"{type(error).__name__}: {error}",
               "trace": traceback.format_exc()[-1500:]}
    return rec


# ------------------------------------------------------------------ tables (no browser)

def _cell(v) -> str:
    return "" if v is None else str(v).replace("|", "\\|")


def _order(ops) -> str:
    """Request order with runs of one op collapsed (`editorGetStateV2 ×27`): rendering only."""
    out = []
    for op in map(str, ops or []):
        if out and out[-1][0] == op:
            out[-1][1] += 1
        else:
            out.append([op, 1])
    return " → ".join(op if n == 1 else f"{op} ×{n}" for op, n in out)


def _hit(h: list) -> str:
    return "; ".join(f"para {x['para']} off {x['offset']} {x['text'][:28]!r}" for x in h) or "absent"


def tables(directory: Path, pattern: str = "report-*.json") -> str:
    lines = []
    for path in sorted(directory.glob(pattern)):
        report = json.loads(path.read_text())
        browser = report["browser"]
        fix = (report.get("candidateFix") or {}).get("name", "none")
        files = (report.get("candidateFix") or {}).get("files") or {}
        shas = ", ".join(f"`{name}` {(v.get('patchedServedSha256') or v.get('servedSha256') or '')[:16]}…"
                         for name, v in files.items())
        lines.append(f"\n### {browser} ({report.get('browserVersion')}), candidateFix: {fix}"
                     f"{' (' + shas + ')' if shas else ''}, `{path.name}`\n")
        for variant, block in report["results"].items():
            rounds = block.get("rounds", [])
            lines.append(f"\n**{variant.upper()}** ({block.get('what')})\n")
            if block.get("notRun"):
                lines.append(f"Not run: {block['notRun']}.")
                continue
            if variant == "v7":
                lines.append("| X planned (ms) | round | X actual: Ctrl+End kd − toolbar save reply (ms) | checkpoint save after the key "
                             "| Q lands | move completion (round trip ms) | reply caret | +500 ms ask caret | final caret | request order |")
                lines.append("|---|---|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('waitMs')} | {r.get('round')} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} |||||||| ")
                        continue
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("waitMs"), r.get("round"), s.get("waitActualMs"), s.get("checkpointSaveAfterKey"), s.get("qClass"),
                        f"{s.get('moveCompletion')} ({s.get('moveRoundTripMs')})", s.get("moveReplyCaret"), s.get("ask7Caret"),
                        caret_str((r.get("finalAsk") or {}).get("caret")), _order(s.get("order")))) + " |")
            elif variant in ("v8", "v8d", "v8d0224", "bup"):
                lines.append("| round | caret before | Q lands | Q kd − arrow kd (ms) | arrow completion (round trip ms) "
                             "| reply caret | final caret | request order |")
                lines.append("|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('round')} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} ||||||| ")
                        continue
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("round"), s.get("beforeCaret"), f"{s.get('qLine')}: {_hit(s.get('qHits') or [])}",
                        s.get("gapDownKdToQKdMs"), f"{s.get('moveCompletion')} ({s.get('moveRoundTripMs')})",
                        s.get("moveReplyCaret"), s.get("finalCaret"), _order(s.get("order")))) + " |")
            elif variant == "d11b":
                lines.append("| round | kind | save requests | requests | completions (End, Home) | reply carets | +500 ms carets "
                             "| unsaved: open / after typing / after End / after Home | checkpoint shown |")
                lines.append("|---|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('round')} | {r.get('kind')} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} ||||||| ")
                        continue
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("round"), s.get("kind"), s.get("saveRequests"), _order(s.get("requests")), s.get("completions"),
                        s.get("replyCarets"), s.get("ask7Carets"),
                        " / ".join(map(str, [s.get("unsavedAtOpen"), s.get("unsavedAfterTyping"), *(s.get("unsavedAfter") or [])])),
                        s.get("checkpoint"))) + " |")
            elif variant == "range":
                lines.append("| round | dragged | place-caret before the move | move completion | final caret | saved P2 | request order |")
                lines.append("|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('round')} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} |||||| ")
                        continue
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("round"), repr(s.get("selectionText")), s.get("placeCaretBeforeMove"), s.get("moveCompletion"),
                        s.get("finalCaret"), repr(s.get("p2")), _order(s.get("order")))) + " |")
            elif variant in CHROME_ONLY:
                lines.append("| round | first input | at that moment: active / disabled / readOnly / inert / closest [inert] / pointer-events "
                             "/ dialog open / hasFocus | beforeinput / input anywhere | insertText | Z | W (pasted) "
                             "| then Y (no click), X (after click) | request order |")
                lines.append("|---|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('round')} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} |||||||| ")
                        continue
                    a = s.get("atZ") or {}
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("round"), s.get("startedBy"),
                        " / ".join(str(a.get(k)) for k in ("active", "sinkDisabled", "sinkReadOnly", "sinkInert", "closestInert",
                                                         "pointerEvents", "dialogOpen", "hasFocus")),
                        f"{s.get('anyBeforeinputAfterZ')} / {s.get('anyInputAfterZ')}", s.get("insertTextAfterZ"),
                        _hit(s.get("zHits") or []), _hit(s.get("wHits") or []),
                        f"Y {'in' if s.get('yHits') else 'absent'}, X after click {'in' if s.get('xHits') else 'absent'}",
                        _order(s.get("order")))) + " |")
            elif variant in ("v1", "v2", "v3", "v4"):
                lines.append("| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) "
                             "| reply caret | +500 ms ask caret | final ask caret (after quiet) | request order |")
                lines.append("|---|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('round')} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} |||||||| ")
                        continue
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("round"), s.get("qClass"), s.get("gapEndKdToQKdMs"), s.get("gapMoveReplyToQKdMs"),
                        f"{s.get('moveCompletion')} ({s.get('moveRoundTripMs')})", s.get("moveReplyCaret"), s.get("ask7Caret"),
                        caret_str((r.get("finalAsk") or {}).get("caret")), _order(s.get("order")))) + " |")
            elif variant == "v5":
                lines.append("| round | delay | dialog close → Z kd (ms) | Z kd target / active | sink disabled at Z | keypress (prevented) "
                             "| beforeinput / input anywhere after Z | insertText | Z in saved doc | then Y (no click), X (after click) "
                             "| request order |")
                lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    delay = DELAY_LABEL.get(r.get("delayMs"), r.get("delayMs"))
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('round')} | {delay} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} ||||||| ")
                        continue
                    z = s.get("zHits") or []
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("round"), delay, s.get("closeToZKdMs"), f"{s.get('zKeydownTarget')} / {s.get('zKeydownActive')}",
                        s.get("sinkDisabledAtZ"), f"{s.get('zKeypress')} ({s.get('zKeypressPrevented')})",
                        f"{s.get('anyBeforeinputAfterZ')} / {s.get('anyInputAfterZ')}", s.get("insertTextAfterZ"),
                        "; ".join(f"para {h['para']} off {h['offset']} {h['text'][:28]!r}" for h in z) or "absent",
                        f"Y {'in' if s.get('yHits') else 'absent'}, X after click {'in' if s.get('xHits') else 'absent'}",
                        _order(s.get("order")))) + " |")
            else:
                lines.append("| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move "
                             "| a delete between that click and the move | request order |")
                lines.append("|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('page')} | {r.get('round')} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} ||||| ")
                        continue
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("page"), r.get("round"), s.get("keyGapsMs"), repr(s.get("p2")), repr(s.get("expectedInOrder")),
                        s.get("placeCaretBeforeMove"), s.get("deleteBetweenClickAndMove"), _order(s.get("order")))) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------------ main

WHAT = {"v1": "plain3, dirty, Q 30 ms after Ctrl+End's keydown", "v2": "plain3, dirty, Q 50 ms after the move's reply",
        "v3": "plain3, clean control, Q 30 ms after Ctrl+End's keydown", "v4": "long60, dirty, Q 30 ms after Ctrl+End's keydown",
        "v5": "Markdown dialog `# a`, Z 0 / 300 ms after it closes (+ added controls late, no-dialog)",
        "v6": "«Bravo|»: Backspace @0, ArrowRight @20, Delete @40",
        "v6e": "(added) «Bravo|»: Backspace @0, Backspace @20, ArrowRight @40, Delete @60 (D8 (e) with ArrowRight)",
        "v7": "plain3, dirty, toolbar save, X ms after its reply Ctrl+End, Q 30 ms after that keydown",
        "v8": "plain3: Z at the start, then «Bravo|», then ArrowDown and Q 30 ms later",
        "v8d": "(added) plain3: «Bravo|», then Z there, then ArrowDown and Q 30 ms later (the arrow is the first move after the change)",
        "d11b": "the item-1 D11b arm reused: clean and dirty, Ctrl+End then Ctrl+Home, requests and unsaved state",
        "d8e": "the item-1 D8 (e) sequence reused: «Bravo|», Backspace @0, Backspace @20, Ctrl+End @40, Delete @60",
        "range": "a real drag selecting `second` in P2, then a real ArrowRight (no delete out)",
        "v11a": "after 「插入」 closes the dialog: Z through CDP Input.insertText",
        "v11b": "after 「插入」 closes the dialog: sink.blur(); sink.focus(), then a real Z",
        "v11c": "open the dialog, 取消 (no paste), then a real Z",
        "v11d": "a range (`second`), open the dialog, paste, 「插入」 refused (dialog stays open), 取消, then a real Z",
        "v11e": "after 「插入」 closes the dialog: a real Ctrl+V of plain text `W` into the sink",
        "v11f": "the V5 step on the 0.2.24 page with another <dialog>",
        "v8d0224": "V8d on the 0.2.24 page and v20 profile: «Bravo|», Z there, then ArrowDown and Q 30 ms later",
        "bup": "boundary control: dirty plain3 (Z at the start), Home, then ArrowUp and Q 30 ms later"}


def main() -> int:
    sys.modules.setdefault("diag_v21_dirty_move", sys.modules[__name__])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"))
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--window", default="1400x1000")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--smoke", action="store_true", help="label the report a development run")
    ap.add_argument("--wait-lock", type=float, default=0.0)
    ap.add_argument("--table", type=Path, help="print markdown tables from the reports in this directory")
    ap.add_argument("--table-glob", default="report-*.json", help="which reports --table reads")
    ap.add_argument("--fix", choices=tuple(FIXES), default="none",
                    help="candidate fix applied to the v21 mirror only (never the tree)")
    ap.add_argument("--tag", default="", help="a word in the report's file name (default: the fix, or none)")
    ap.add_argument("--headed", action="store_true",
                    help="V11g: Chrome without --headless=new, on this process's DISPLAY / WAYLAND_DISPLAY")
    ap.add_argument("--v5-delays", default="0,300,late,no-dialog",
                    help="v5's sub-rounds: comma-separated delay[:rounds]; delay is ms, late or no-dialog")
    args = ap.parse_args()
    if args.headed and args.browser != "chrome":
        raise SystemExit("--headed is Chrome-only")
    if args.table:
        print(tables(args.table, args.table_glob))
        return 0
    if not args.browser or not args.out:
        raise SystemExit("--browser and --out are required")
    variants = [v for v in args.variants.split(",") if v]
    if [v for v in variants if v not in VARIANTS]:
        raise SystemExit(f"unknown variants; known {VARIANTS}")
    if args.browser != "chrome" and [v for v in variants if v in CHROME_ONLY]:
        raise SystemExit(f"{CHROME_ONLY} are Chrome-only")
    window = tuple(int(v) for v in args.window.split("x"))
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    tag = args.tag or (args.fix if args.fix != "none" else "")
    name = f"{args.browser}-{tag}-{stamp}" if tag else f"{args.browser}-{stamp}"
    report_path = args.out / f"report-{name}.json"
    docs = args.out / "docs" / name
    docs.mkdir(parents=True, exist_ok=True)
    pre = common.pre_run_checks()
    if pre["refuse"]:
        raise SystemExit(f"pre-run checks refuse: {pre['refuse']}")
    fixtures = {p.stem: p.read_bytes() for p in sorted(item1.FIXTURE_DIR.glob("*.odt"))}
    fixtures["long60"] = build_long_document(60)
    report = {"tool": "diag_v21_dirty_move.py", "toolSha256": common.sha256_file(Path(__file__)),
              "recordedNotJudged": True, "counted": False, "smoke": args.smoke, "browser": args.browser,
              "fix": args.fix,
              "variants": variants, "rounds": args.rounds, "window": window, "startedAt": common.now_iso(),
              "preRun": pre, "inputs": {name: common.sha256_bytes(raw) for name, raw in fixtures.items()
                                        if name in ("plain3", "long60")}, "results": {}}
    scratch = Path(tempfile.mkdtemp(prefix="diag-dirty-move-"))
    pages = FixPages(scratch, fixtures, args.fix)
    v6_pages = ("v21", "dist0224") if args.fix == "none" else ("v21",)

    def flush() -> None:
        report["pages"] = pages.identity
        report["candidateFix"] = pages.candidate
        report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))

    item1.FLUSH["fn"] = flush
    session = None
    with common.browser_lock(f"diag_v21_dirty_move {args.browser} {args.fix} {','.join(variants)}",
                             wait_s=args.wait_lock) as holder:
        report["lock"] = {**holder, "acquiredAt": common.now_iso()}
        try:
            pages.base("v21")
            page_fix = pages.candidate["files"].get("e2-editor-app.js")
            served = (page_fix["unpatchedServedSha256"] if page_fix else pages.identity["v21"]["pageServedSha256"])
            report["v21PageCheck"] = {"served": pages.identity["v21"]["pageServedSha256"],
                                      "unpatchedServed": served, "expectedPrefix": V21_PAGE_PREFIX,
                                      "matches": served.startswith(V21_PAGE_PREFIX) and (not page_fix or page_fix["patchOnly"]),
                                      "identityOk": pages.identity["v21"].get("identityOk")}
            if not report["v21PageCheck"]["matches"]:
                flush()
                raise SystemExit(f"the v21 page (before any fix) is {served[:16]}, not {V21_PAGE_PREFIX}, or the patch is not alone")
            if ("v6" in variants or "v6e" in variants) and "dist0224" in v6_pages:
                pages.base("dist0224")
            if args.headed:
                session = open_headed(window)
                report["headed"] = {"argv": session.argv, "display": session.display}
            else:
                session = common.open_browser(args.browser, window,
                                              firefox_prefs=clip.FIREFOX_PREFS if "v5" in variants else None)
            report["browserVersion"] = getattr(session, "version", None)
            ctx = item1.Ctx(session, args.browser, pages, report, docs)
            for variant in variants:
                t0 = time.monotonic()
                block = {"what": WHAT[variant], "rounds": []}
                report["results"][variant] = block
                if variant == "v7":
                    for wait_ms, n_rounds in V7_WAITS:
                        for n in range(1, (n_rounds or args.rounds) + 1):
                            rec = guarded(round_v7, ctx, wait_ms, f"v7-{wait_ms}-r{n}")
                            block["rounds"].append({"round": n, "waitMs": wait_ms, **rec})
                            flush()
                elif variant in ("v8", "v8d", "v8d0224"):
                    for n in range(1, args.rounds + 1):
                        rec = guarded(round_v8, ctx, variant, f"{variant}-r{n}")
                        block["rounds"].append({"round": n, **rec})
                        flush()
                elif variant == "bup":
                    for n in range(1, args.rounds + 1):
                        rec = guarded(round_bup, ctx, f"bup-r{n}")
                        block["rounds"].append({"round": n, **rec})
                        flush()
                elif variant == "range":
                    for n in range(1, args.rounds + 1):
                        rec = guarded(round_range, ctx, f"range-r{n}")
                        block["rounds"].append({"round": n, **rec})
                        flush()
                elif variant == "d11b":
                    result = item1.arm_d11b(ctx, args.rounds)
                    for rec in result["rounds"]:
                        rec["summary"] = summarise_d11b(rec)
                    block.update({"reused": "run_v21_shakedown_item1.arm_d11b", **result})
                elif variant == "d8e":
                    result = item1.run_d8(ctx, args.rounds, "v21", ["e"])
                    keys = item1.D8_SEQUENCES["e"][1]
                    for rec in result["rounds"]:
                        if (rec.get("save") or {}).get("saved"):
                            rec["savedTexts"] = paragraphs((args.out / rec["save"]["file"]).read_bytes())
                        rec["page"] = "v21"
                        rec["summary"] = summarise_v6(rec, keys, "move-document-end", judge1.D8_EXPECT["e"][0][1])
                    block.update({"reused": "run_v21_shakedown_item1.run_d8(..., ['e'])", **result})
                elif variant == "v11f":
                    block["notRun"] = ("the 0.2.24 page (dist/e2-editor.html, dist/e2-editor-app.js) has no <dialog> "
                                       "element and no showModal call, so there is no dialog to open and close")
                elif variant in CHROME_ONLY:
                    for n in range(1, args.rounds + 1):
                        rec = guarded(round_v11, ctx, variant[-1], f"{variant}-r{n}")
                        block["rounds"].append({"round": n, **rec})
                        flush()
                elif variant == "v5":
                    for delay, n in v5_jobs(args.v5_delays, args.rounds):
                        rec = guarded(round_v5, ctx, delay, f"v5-{DELAY_LABEL.get(delay, delay)}-r{n}")
                        block["rounds"].append({"round": n, "delayMs": delay, **rec})
                        flush()
                elif variant in ("v6", "v6e"):
                    for page in v6_pages:
                        for n in range(1, args.rounds + 1):
                            rec = guarded(round_v6, ctx, page, f"{variant}-{page}-r{n}", KEYS_OF[variant])
                            block["rounds"].append({"round": n, "page": page, **rec})
                            flush()
                else:
                    for n in range(1, args.rounds + 1):
                        rec = guarded(round_move, ctx, variant, f"{variant}-r{n}")
                        block["rounds"].append({"round": n, **rec})
                        flush()
                block["seconds"] = round(time.monotonic() - t0, 1)
                flush()
        finally:
            report["completedAt"] = common.now_iso()
            if session is not None:
                report["close"] = common.close_browser(session)
            pages.close()
            flush()
    out = {v: [r.get("outcome") for r in b["rounds"]] for v, b in report["results"].items()}
    print(json.dumps({"report": str(report_path), "outcomes": out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
