#!/usr/bin/env python3
"""The v21 WASM shakedown, item 1 (Ctrl+Home/End): the runner.

Arms: findings/evidence/link-batch-v21/shakedown/ARMS-item1.md (draft + rulings §8), ARMS.md (shared
rules S-1..S-11), spec §11.1, §12.2 and §12.3.  Written after the arms were committed (8f1dbf0a).  Never a
count: every report says `"counted": false`.  Every browser run holds the S-9 lock.

Spec §12.3 (fable ruling 1, 2026-10-17), before any evidence run (README "Runner and judge changes for
spec §12.3"): the new arm d14; every arm's start state also records the item-2 entry read (E0); d6 is
not runnable (item 2 is not shipped, so the Markdown dialog has no entry).

Arms (`--arms`, comma-separated):
  d1      D1's 38 arms + its 2 controls; each Ctrl press also feeds D7 (the +500 ms ask) and the
          range arms feed D4                                                  (page v21)
  d2p     D2' back-to-back Ctrl+Home, Backspace on numbered-second, with the placement witness and the
          Backspace-alone control                                             (page v21)
  d8      D8 (a)-(e)                                                          (page v21)
  d8red   D8 (d) on 0.2.24 (dist/'s page, shell and v20 profile as they are)  (page dist0224)
  d9      D9: Ctrl+Home / Ctrl+End held 1 s, flagged and unflagged             (page v21)
  d10     D10: Ctrl+End in the 60-page document                               (page v21)
  d11a    D11a: view-only through the host shim                               (page v21 + shim)
  d11b    D11b: clean and dirty                                               (page v21)
  d11c    D11c: stale expectedRevision through the page's own SDK (S-3)       (page v21 + S-3)
  d12     D12: the page's own client on a range (S-3)                         (page v21 + S-3)
  d5w     D5-w: real chords on the final page repointed to v20, and on v21     (pages v20, v21)
  xlc     R-xlc (record)                                                      (page v21)
  table   R-table (record)                                                    (page v21)
  d14     D14: dirty plain3 and long60 (Z at the start), real Ctrl+End, real Q <= 30 ms after its
          keydown, quiet, save; diag-dirty-move V1/V4's procedure, imported (page v21)
  d6      D6 (record): NOT RUNNABLE in v21 -- recorded as notRun, never driven (spec §12.3 (e))

  run_v21_shakedown_item1.py --browser chrome --arms d1,d2p --rounds 1 --out DIR [--smoke] [--only a1-home-mid,...]

What a report holds: the identity of every page served (S-1), the pre-run checks and foreign-CPU samples
(S-9), per arm and round the raw logs the judge reads, and the saved documents as files beside the
report (`docs/`).  The judge (`judge_v21_shakedown_item1.py`) decides; this runner records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r7_support  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import run_merge_wasm_shakedown as mws  # noqa: E402
import run_v20_shakedown as v20  # noqa: E402
import v21_engine_read as er  # noqa: E402
import v21_input as inp  # noqa: E402
import v21_item1_marker as marker  # noqa: E402
import v21_item1_observer as obs1  # noqa: E402
import v21_item1_population as population  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402

PROJECT = common.PROJECT
REPO = common.REPO
FIXTURE_DIR = REPO / "findings/evidence/link-batch-v21/shakedown/fixtures"
ARMS = ("d1", "d2p", "d8", "d8red", "d9", "d10", "d11a", "d11b", "d11c", "d12", "d5w", "xlc", "table", "d14", "d6")
# Arms that are kept selectable (so a report says why they are absent) but are never driven.
NOT_RUNNABLE = {"d6": "not runnable: item 2 not shipped (spec §12.3 (e))"}
PAGE_OF = {"d8red": "dist0224", "d11a": "v21host"}
KEY_ACTION = {"ArrowDown": "move-line-down", "ArrowUp": "move-line-up", "ArrowRight": "move-character-right",
              "ArrowLeft": "move-character-left", "Home": "move-line-home", "End": "move-line-end"}
K_CODE = {1024: "ArrowDown", 1025: "ArrowUp", 1027: "ArrowRight", 1028: "Home", 1029: "End"}
CTRL_CODE = {9220: "Home", 9221: "End"}
MOVE_OF = {9220: "move-document-start", 9221: "move-document-end"}
PRE_PRESS_QUIET_S = 1.5


def navigate(session, browser: str, url: str, timeout: float = 180) -> bool:
    """Navigate; answer the page's own leave prompt if it comes (§34.4 witness: smoke/witness-item1/).

    Leaving a page with unsaved work raises the page's beforeunload prompt (finding 107's guard), and a
    headless Chrome waits on it forever.  The measurement on that page is over, so the prompt is
    accepted, and the load records that it was.  Firefox: WebDriver navigation accepts it itself.
    Returns True when a dialog was accepted."""
    import json as _json
    if browser != "chrome":
        pp.navigate(session, url)
        return False
    session.next_id += 1
    nav_id = session.next_id
    session.websocket.send(_json.dumps({"id": nav_id, "method": "Page.navigate", "params": {"url": url}}))
    accepted = False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = _json.loads(session.websocket.recv(timeout=timeout))
        if message.get("method") == "Page.javascriptDialogOpening":
            session.next_id += 1
            session.websocket.send(_json.dumps({"id": session.next_id, "method": "Page.handleJavaScriptDialog",
                                                "params": {"accept": True}}))
            accepted = True
            continue
        if message.get("id") == nav_id:
            if "error" in message:
                raise RuntimeError(f"CDP Page.navigate: {message['error']}")
            break
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            if pp.evaluate(session, "(() => document.readyState === 'complete')()"):
                return accepted
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.2)
    raise RuntimeError("the page did not finish loading")
OBSERVE_CAP_S = 10.0
FLUSH = {"fn": lambda: None}

# Spec §12.3 (e), the judge's clause E0: is item 2's entry on the page?  Read at every arm's start state.
#  - `exists`/`hidden`: `#toolbar [data-action="paste-markdown"]` (the button `updatePasteMarkdownAffordance`
#    shows or hides) and whether it renders;
#  - `visibleOpeners`: every rendered control outside the dialog that names the dialog or Markdown: the
#    page's own route (`data-action="paste-markdown"`, the toolbar click handler's only way to
#    `openMarkdownDialog`) anywhere in the document, the HTML ways to target a dialog (`aria-controls`,
#    `commandfor`, `popovertarget`), and any button, link or menu item whose text says "Markdown";
#  - `controlVisible`: the same visibility read on `#toolbar [data-action="undo"]`, which is always rendered
#    (disabled, not hidden, on a view-only page): false means the read is blind.
# A static read: nothing is clicked, so the arm's start state is not changed.
ENTRY_READ = r"""(() => {
  const shown = (e) => {
    if (!e || !e.isConnected) return false;
    if (typeof e.checkVisibility === "function") {
      if (!e.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return false;
    } else {
      for (let n = e; n && n.nodeType === 1; n = n.parentElement) {
        const s = getComputedStyle(n);
        if (s.display === "none" || s.visibility === "hidden" || s.opacity === "0") return false;
      }
    }
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const describe = (e) => ({ tag: e.tagName.toLowerCase(), id: e.id || null, action: e.getAttribute("data-action"),
    text: (e.textContent || e.value || "").trim().slice(0, 40) });
  const dialog = document.querySelector("#markdown-dialog");
  const button = document.querySelector('#toolbar [data-action="paste-markdown"]');
  const found = Array.from(document.querySelectorAll('[data-action="paste-markdown"], [aria-controls="markdown-dialog"],'
    + ' [commandfor="markdown-dialog"], [popovertarget="markdown-dialog"]'));
  for (const e of Array.from(document.querySelectorAll('button, a[href], [role="button"], [role="menuitem"], summary,'
      + ' input[type="button"], input[type="submit"]'))) {
    if (!found.includes(e) && /markdown/i.test(e.textContent || e.value || "")) found.push(e);
  }
  const outside = found.filter((e) => !(dialog && dialog.contains(e)));
  return { exists: !!button, hidden: button ? !shown(button) : null, hiddenAttr: button ? button.hidden : null,
           candidates: outside.length, visibleOpeners: outside.filter(shown).map(describe),
           controlVisible: shown(document.querySelector('#toolbar [data-action="undo"]')),
           dialogExists: !!dialog, dialogOpen: dialog ? !!dialog.open : null };
})()"""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class StepError(RuntimeError):
    """A step could not be done as the arm says; the round is recorded with the reason, not judged."""


# ------------------------------------------------------------------ pages and the browser

# SPEC-M3-link-batch-v22 §11.4 (fable ruling 5, item 14): the 0.2.24 red case (`dist0224`, D8's d8red) is
# the 0.2.24 host package, decompressed.  It used to be dist/'s page and shell, which WAS 0.2.24's when
# item 1 ran (10-17 morning); dist/ became v74 that evening and becomes v75 at the v22 freeze.  A binding,
# §34.4 0 / 0; its witness is the served page 901dd6a6... and shell digest e7c4eefe...
# (run_v21_d2.HOST_EXPECT["0224"]).
HOST_0224_ARCHIVE = common.PROJECT / "build/archive/host-0.2.24-engine-d3cd39bbc71ec311"


def host_0224_root(target: Path) -> Path:
    """The archived 0.2.24 package (zst and gz on disk), decompressed and checked against its MANIFEST.json."""
    source = HOST_0224_ARCHIVE / "files"
    manifest = json.loads((HOST_0224_ARCHIVE / "MANIFEST.json").read_text(encoding="utf-8"))["files"]
    for compressed in sorted(source.rglob("*.zst")):
        out = target / compressed.relative_to(source).with_suffix("")
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["zstd", "-d", "-q", "-f", str(compressed), "-o", str(out)], check=True)
    files = {str(path.relative_to(target)): sha256_bytes(path.read_bytes()) for path in target.rglob("*") if path.is_file()}
    wrong = sorted(name for name, entry in manifest.items() if files.get(name) != entry["sha256"])
    if wrong or set(files) != set(manifest):
        raise SystemExit(f"the 0.2.24 archive does not decompress to its MANIFEST.json: {wrong[:5]} "
                         f"{sorted(set(files) ^ set(manifest))[:5]}")
    return target


class Pages:
    """One mirror and one server per page variant, built on first use (S-1)."""

    def __init__(self, scratch: Path, fixtures: dict[str, bytes], page_hook: str | None, extra: dict | None = None):
        self.scratch = scratch
        self.fixtures = fixtures
        self.extra = extra or {}
        self.page_hook = page_hook
        self.servers: dict[str, tuple] = {}
        self.identity: dict[str, dict] = {}
        self._stack = []

    def base(self, variant: str) -> str:
        if variant in self.servers:
            return self.servers[variant][0]
        extra = {f"v21-fx-{name}.odt": raw for name, raw in self.fixtures.items()}
        extra.update(self.extra)
        snippets = [v20.OBSERVER, obs1.SNIPPET]
        kwargs = {}
        if variant == "v21host":
            snippets.append(obs1.host_shim("./v21-fx-plain3.odt", "plain3.odt"))
        if variant == "v21hook":
            if not self.page_hook:
                raise StepError("S-3's SNIPPET is not available")
            snippets.append(self.page_hook)
        if variant == "v20":
            kwargs["page_profile"] = "e2-editor-v20"
        if variant == "dist0224":
            root = host_0224_root(self.scratch / "host-0.2.24")
            kwargs.update(page_profile="e2-editor-v20", shell_from_tree=False, root=root,
                          source_page=(root / "e2-editor-app.js").read_text(encoding="utf-8"))
        identity = common.build_mirror(self.scratch / f"mirror-{variant}", snippets=snippets, extra_files=extra,
                                       **kwargs)
        ctx = common.served(Path(identity["mirror"]))
        url = ctx.__enter__()
        self._stack.append(ctx)
        self.servers[variant] = (url, identity)
        self.identity[variant] = identity
        return url

    def close(self) -> None:
        while self._stack:
            ctx = self._stack.pop()
            try:
                ctx.__exit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass


class Ctx:
    def __init__(self, session, browser: str, pages: Pages, report: dict, docs: Path):
        self.session, self.browser, self.pages, self.report, self.docs = session, browser, pages, report, docs
        self.trace = er.Trace(session)
        self.log = obs1.Log(session)
        self.variant = None

    def ev(self, expr: str):
        return pp.evaluate(self.session, expr)

    def drain(self) -> None:
        self.trace.drain()
        self.log.drain()

    # -- load and open
    def load(self, variant: str = "v21") -> dict:
        base = self.pages.base(variant)
        t0 = time.monotonic()
        accepted = navigate(self.session, self.browser, base)
        boot = pp.wait_for(self.session, lambda s: s.get("state") in ("ready", "expired", "stopped"), 300)
        er.install(self.session)
        self.trace.reset()
        self.log.reset()
        self.variant = variant
        self.drain()
        return {"variant": variant, "state": (boot or {}).get("state"), "seconds": round(time.monotonic() - t0, 1),
                "leaveDialogAccepted": accepted}

    def open(self, name: str) -> dict:
        opened = mws.open_fixture(self.session, f"./v21-fx-{name}.odt", f"{name}.odt")
        self.drain()
        if not opened.get("opened"):
            raise StepError(f"{name}.odt did not open: {opened}")
        return opened

    def worker(self) -> int | None:
        return er.current_worker(self.session)

    def handle(self):
        return er.document_handle(self.session)

    def ask(self) -> dict:
        """editorGetStateV2 through v20's channel; the selection text from the item-1 snippet's askx."""
        mark = len(self.log.all)
        asked = er.ask_state(self.trace, self.handle())
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            self.log.drain()
            hit = next((e for e in self.log.all[mark:] if e.get("k") == "askx" and e.get("rq") == asked.get("asked")), None)
            if hit:
                asked["full"] = hit
                break
            time.sleep(0.1)
        return asked

    def start_state(self) -> dict:
        """ARMS-item1.md §2.4 (rulings D-5 A, D-6 A): selection observed, then the sink focused."""
        t0 = time.monotonic()
        observed, asked = False, None
        while time.monotonic() - t0 < OBSERVE_CAP_S:
            asked = self.ask()
            sel = ((asked.get("full") or {}).get("sel") or {})
            if asked.get("answered") and sel.get("observed") is True:
                observed = True
                break
            time.sleep(0.4)
        r7_support.run_in_page(self.session, "document.querySelector('#sink').focus({ preventScroll: true });")
        time.sleep(0.1)
        focused = self.ev("(() => document.activeElement && document.activeElement.id)()")
        out = {"observed": observed, "observedAfterMs": round((time.monotonic() - t0) * 1000), "focus": "sink.focus()",
               "activeElement": focused, "caret": (asked or {}).get("full", {}).get("caret") if asked else None,
               "entry": self.entry()}
        if not observed:
            raise StepError(f"not-observed: no selection reported within {OBSERVE_CAP_S} s")
        return out

    def entry(self) -> dict:
        """The item-2 entry read (ENTRY_READ; the judge's E0), tagged with the page variant."""
        try:
            read = self.ev(ENTRY_READ)
        except Exception as error:  # noqa: BLE001 -- a failed read is recorded; the judge reads it as blind
            read = {"error": f"{type(error).__name__}: {error}"}
        if not isinstance(read, dict):
            read = {"error": f"unexpected read: {read!r}"[:200]}
        read["variant"] = self.variant
        return read

    def quiet(self, limit: float = 30) -> dict:
        state = mws.quiet(self.session, limit)
        self.drain()
        return state

    def ev_quiet(self, seconds: float = PRE_PRESS_QUIET_S, cap: float = 8.0) -> float:
        """No editor-state push for `seconds` (the native probe's pre-press quiet)."""
        t0 = time.monotonic()
        last = time.monotonic()
        while time.monotonic() - t0 < cap:
            if any(e.get("k") == "ev" and not e.get("event") for e in self.trace.drain()):
                last = time.monotonic()
            self.log.drain()
            if time.monotonic() - last >= seconds:
                break
            time.sleep(0.15)
        return round(time.monotonic() - t0, 2)

    def wait_rs(self, mark: int, predicate, limit: float = 15.0) -> dict | None:
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            self.log.drain()
            hit = next((e for e in self.log.all[mark:] if e.get("k") == "rs" and predicate(e)), None)
            if hit:
                return hit
            time.sleep(0.05)
        return None

    def size(self) -> dict:
        seen = mws.obs(self.session) or {}
        size = seen.get("size") or {}
        if size.get("generation") != seen.get("workers") or not size.get("w"):
            raise StepError(f"no document size from the current worker: {size}")
        return size

    # -- steps
    def move_key(self, name: str) -> dict:
        mark = len(self.log.all)
        inp.key(self.session, self.browser, name)
        action = KEY_ACTION[name]
        hit = self.wait_rs(mark, lambda e: e.get("op") == "editorActionV2" and e.get("action") == action)
        if hit is None or not hit.get("ok"):
            raise StepError(f"{name}: no successful {action} response: {hit}")
        return hit

    def ctrl(self, which: str) -> dict:
        """One real Ctrl+Home/End and everything D7 reads about it."""
        self.ev_quiet()
        mark = len(self.log.all)
        action = "move-document-start" if which == "Home" else "move-document-end"
        inp.key(self.session, self.browser, which, ("ctrl",))
        place = None
        hit = self.wait_rs(mark, lambda e: e.get("op") == "editorActionV2" and e.get("action") == action)
        record = {"key": f"Ctrl+{which}", "action": action, "response": hit}
        if hit is None:
            record["error"] = "no response"
            return record
        # The page's moveFromPoint click: editorPlaceCaretV2 on a caret, `click` (v67's path) on an open
        # range (narrow-editor-v2-session.js placeCaret, `rangeOpen`).  Recorded with its op; the judge decides.
        place = [e for e in self.log.all[mark:] if e.get("k") == "rs" and e.get("op") in ("editorPlaceCaretV2", "click")
                 and e.get("s", 0) < hit.get("s", 0)]
        record["placeCaretBefore"] = place
        record["requestsBetween"] = [{"op": e.get("op"), "action": e.get("action"), "s": e.get("s")}
                                     for e in self.log.all[mark:] if e.get("k") == "rq" and e.get("s", 0) <= hit.get("s", 0)]
        keys = [e for e in self.log.all[mark:] if e.get("k") in ("kd", "kdp")]
        record["keys"] = keys[:6]
        if hit.get("ok"):
            deadline = time.monotonic() + 3
            ask = None
            while time.monotonic() < deadline and ask is None:
                self.log.drain()
                ask = next((e for e in self.log.all[mark:] if e.get("k") == "ask7" and e.get("forRq") == hit.get("rq")), None)
                time.sleep(0.05)
            record["ask7"] = ask
        self.quiet()
        return record

    def type_marker(self) -> dict:
        self.ev_quiet()
        mark = len(self.log.all)
        inp.key(self.session, self.browser, "Z")
        hit = self.wait_rs(mark, lambda e: e.get("op") == "insertText")
        self.quiet()
        ops = [e.get("op") for e in self.log.all[mark:] if e.get("k") == "rq"]
        return {"response": hit, "requestOps": ops,
                "beforeinput": [e for e in self.log.all[mark:] if e.get("k") == "bi"][:3]}

    def save(self, label: str) -> dict:
        raw = er.save(self.session)
        if raw is None:
            return {"saved": False}
        path = self.docs / f"{label}.odt"
        if path.exists():
            raise SystemExit(f"refusing to overwrite a kept document: {path}")
        path.write_bytes(raw)
        return {"saved": True, "file": str(path.relative_to(self.docs.parent.parent)), "sha256": sha256_bytes(raw),
                "bytes": len(raw)}

    def point_of(self, caret: dict) -> tuple[float, float]:
        return inp.paper_point(self.session, pp.evaluate, caret["x"], caret["y"], caret["height"], self.size())

    def click_caret(self, caret: dict) -> dict:
        mark = len(self.log.all)
        x, y = self.point_of(caret)
        inp.click(self.session, self.browser, x, y)
        hit = self.wait_rs(mark, lambda e: e.get("op") in ("editorPlaceCaretV2", "click"))
        self.quiet()
        return {"point": [round(x, 1), round(y, 1)], "response": hit}

    def drag(self, a: dict, b: dict) -> dict:
        mark = len(self.log.all)
        pa, pb = self.point_of(a), self.point_of(b)
        inp.drag(self.session, self.browser, pa, pb)
        hit = self.wait_rs(mark, lambda e: e.get("op") == "editorSelectRangeV2", 15)
        time.sleep(0.4)
        self.quiet()
        return {"from": [round(v, 1) for v in pa], "to": [round(v, 1) for v in pb], "response": hit}

    def foreign(self) -> dict:
        return common.foreign_cpu()


# ------------------------------------------------------------------ the D1 script on the page

def run_script(ctx: Ctx, script: str, arm_name: str, native_sel: str | None) -> dict:
    """ARMS-item1.md §2.6: every step of a D1 script as the product path takes it."""
    out = {"steps": [], "presses": [], "points": {}}
    for step in [s for s in script.split(",") if s]:
        t0 = time.monotonic()
        rec = {"step": step}
        if step[0] == "k":
            code, _, times = step[1:].partition("x")
            name = K_CODE.get(int(code))
            if name is None:
                raise StepError(f"k code {code} has no page key")
            for _ in range(int(times or 1)):
                hit = ctx.move_key(name)
            rec["completion"] = hit.get("completion")
            ctx.quiet()
        elif step[0] == "r":
            ctx.quiet()
            asked = ctx.ask()
            caret = (asked.get("full") or {}).get("caret")
            if not caret:
                raise StepError(f"{step}: no caret in the engine read")
            out["points"][step[1:]] = caret
            rec["caret"] = caret
        elif step[0] == "s":
            a, b = step[1:].split(":")
            rec["drag"] = ctx.drag(out["points"][a], out["points"][b])
            asked = ctx.ask()
            full = asked.get("full") or {}
            rec["selection"] = {"selectionType": full.get("selectionType"), "selectionText": full.get("selectionText"),
                                "sel": full.get("sel")}
            out["rangeSelectionText"] = full.get("selectionText")
            if native_sel is not None and full.get("selectionText") != native_sel:
                raise StepError(f"placement-mismatch: the drag selected {full.get('selectionText')!r}, native {native_sel!r}")
        elif step[0] == "c":
            rec["click"] = ctx.click_caret(out["points"][step[1:]])
        elif step[0] == "M":
            label, _, code = step[1:].partition("=")
            which = CTRL_CODE.get(int(code))
            if which is None:
                raise StepError(f"{step}: not a Ctrl press")
            press = ctx.ctrl(which)
            press["label"] = label
            out["presses"].append(press)
        elif step == "T":
            rec["typed"] = ctx.type_marker()
        elif step == "S":
            rec["save"] = ctx.save(arm_name)
            out["save"] = rec["save"]
        elif step == "L":
            rec["skipped"] = "the native locator is an instrument; the saved document is the reader's input"
        else:
            raise StepError(f"unknown step {step!r}")
        rec["ms"] = round((time.monotonic() - t0) * 1000)
        out["steps"].append(rec)
    return out


def native_selection(arm: str) -> str | None:
    for record in population.press_records(arm, 1):
        if record.get("codes", [0])[0] in (9220, 9221):
            text = (record.get("before") or {}).get("selText")
            return text if text else None
    return None


def arm_d1(ctx: Ctx, rounds: int, only: set | None) -> dict:
    pops = population.populations()
    arms = [a for a in pops["d1"] if not only or a["name"] in only]
    controls = [c for c in pops["controls"] if not only or c["pairedWith"] in only or c["name"] in only]
    out = {"arm": "d1", "population": {"in": [a["name"] for a in pops["d1"]], "controls": [c["name"] for c in pops["controls"]],
                                       "d4": pops["d4"], "counts": pops["counts"]},
           "selected": [a["name"] for a in arms] + [c["name"] for c in controls], "rounds": []}
    jobs = [("D1", a["name"], a["fixture"], a["d1Script"]) for a in arms]
    jobs += [("control", c["name"], c["fixture"], c["script"]) for c in controls]
    for round_no in range(1, rounds + 1):
        for role, name, fixture, script in jobs:
            rec = {"round": round_no, "role": role, "arm": name, "fixture": fixture, "script": script}
            out["rounds"].append(rec)
            try:
                rec["foreign"] = ctx.foreign()
                rec["load"] = ctx.load("v21")
                rec["open"] = ctx.open(fixture)
                rec["start"] = ctx.start_state()
                native_sel = native_selection(name) if role == "D1" else None
                rec.update(run_script(ctx, script, f"d1-{name}-r{round_no}", native_sel))
                rec["outcome"] = "done"
            except StepError as error:
                rec["outcome"] = str(error).split(":", 1)[0] if str(error).startswith(("placement-mismatch", "not-observed")) else "step-error"
                rec["error"] = str(error)
            except Exception as error:  # noqa: BLE001 -- recorded with the round; the run goes on
                rec["outcome"] = "runner-error"
                rec["error"] = f"{type(error).__name__}: {error}"
                rec["trace"] = traceback.format_exc()[-1500:]
            rec["toasts"] = (pp.evaluate(ctx.session, pp.READ_TOASTS) or [])[-4:]
            FLUSH["fn"]()
    return out


# ------------------------------------------------------------------ the other arms

def placed(ctx: Ctx, fixture: str, script: str) -> dict:
    """Load, open, start state, then a placement script of k steps (no Ctrl press)."""
    rec = {"load": ctx.load("v21"), "open": ctx.open(fixture), "start": ctx.start_state()}
    rec["placement"] = run_script(ctx, script, "placement", None)["steps"] if script else []
    return rec


def arm_d2p(ctx: Ctx, rounds: int) -> dict:
    out = {"arm": "d2p", "fixture": "numbered-second", "rounds": []}
    for round_no in range(1, rounds + 1):
        for kind in ("witness", "control", "back-to-back"):
            rec = {"round": round_no, "kind": kind}
            out["rounds"].append(rec)
            try:
                rec.update(placed(ctx, "numbered-second", "k1024"))
                ctx.ev_quiet()
                mark = len(ctx.log.all)
                if kind == "witness":
                    rec["typed"] = ctx.type_marker()
                elif kind == "control":
                    inp.key(ctx.session, ctx.browser, "Backspace")
                    rec["delete"] = ctx.wait_rs(mark, lambda e: e.get("op") == "editorActionV2"
                                                and str(e.get("action", "")).startswith("delete"), 20)
                else:
                    inp.chain(ctx.session, ctx.browser, [("Home", ("ctrl",)), ("Backspace", ())])
                    rec["move"] = ctx.wait_rs(mark, lambda e: e.get("op") == "editorActionV2" and e.get("action") == "move-document-start", 15)
                    rec["delete"] = ctx.wait_rs(mark, lambda e: e.get("op") == "editorActionV2"
                                                and str(e.get("action", "")).startswith("delete"), 20)
                ctx.quiet()
                rec["log"] = [e for e in ctx.log.all[mark:] if e.get("k") in ("kd", "kdp", "rq", "rs", "bi")]
                rec["save"] = ctx.save(f"d2p-{kind}-r{round_no}")
                rec["outcome"] = "done"
            except StepError as error:
                rec["outcome"], rec["error"] = "step-error", str(error)
            except Exception as error:  # noqa: BLE001
                rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
                rec["trace"] = traceback.format_exc()[-1500:]
            FLUSH["fn"]()
    return out


D8_SEQUENCES = {
    # name: (placement script, [(t_ms, key, mods) | (t_ms, "click", None)])
    "a": ("", [(0, "Backspace", ()), (100, "End", ("ctrl",)), (200, "Backspace", ())]),
    "b": ("", [(0, "Backspace", ()), (100, "Home", ("ctrl",))] + [(150 + 55 * i, "Backspace", ()) for i in range(18)]),
    "c": ("", [(0, "Backspace", ()), (100, "End", ("ctrl",)), (200, "Backspace", ()), (300, "Backspace", ())]),
    "d": ("", [(0, "Backspace", ()), (100, "click", None), (200, "Backspace", ())]),
    "e": ("k1024,k1027x5", [(0, "Backspace", ()), (20, "Backspace", ()), (40, "End", ("ctrl",)), (60, "Delete", ())]),
}


def d8_point(ctx: Ctx, variant: str) -> dict:
    """(d)'s click target: the WASM caret at «Bravo|», measured in a separate open."""
    ctx.load(variant)
    ctx.open("plain3")
    ctx.start_state()
    run_script(ctx, "k1024,k1027x5", "d8-point", None)
    asked = ctx.ask()
    caret = (asked.get("full") or {}).get("caret")
    if not caret:
        raise StepError("no caret for (d)'s point")
    return caret


def run_d8(ctx: Ctx, rounds: int, variant: str, names) -> dict:
    out = {"arm": "d8" if variant == "v21" else "d8red", "variant": variant, "rounds": []}
    for round_no in range(1, rounds + 1):
        for name in names:
            rec = {"round": round_no, "sequence": name}
            out["rounds"].append(rec)
            try:
                point = d8_point(ctx, variant) if name == "d" else None
                rec["clickTarget"] = point
                rec["load"] = ctx.load(variant)
                rec["open"] = ctx.open("plain3")
                rec["start"] = ctx.start_state()
                placement, steps = D8_SEQUENCES[name]
                if placement:
                    rec["placement"] = run_script(ctx, placement, "placement", None)["steps"]
                viewport = ctx.point_of(point) if point else None
                ctx.ev_quiet()
                mark = len(ctx.log.all)
                actions = []
                for t, key, mods in steps:
                    if key == "click":
                        actions.append((t, lambda: inp.click(ctx.session, ctx.browser, *viewport)))
                    else:
                        actions.append((t, (lambda k=key, m=mods: inp.key(ctx.session, ctx.browser, k, m))))
                rec["sentMs"] = inp.schedule(actions)
                time.sleep(1.0)
                ctx.quiet(limit=20)
                time.sleep(0.5)
                ctx.quiet(limit=20)
                rec["log"] = [e for e in ctx.log.all[mark:] if e.get("k") in ("kd", "kdp", "rq", "rs", "bi")]
                rec["save"] = ctx.save(f"{out['arm']}-{name}-r{round_no}")
                rec["outcome"] = "done"
            except StepError as error:
                rec["outcome"], rec["error"] = "step-error", str(error)
            except Exception as error:  # noqa: BLE001
                rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
                rec["trace"] = traceback.format_exc()[-1500:]
            FLUSH["fn"]()
    return out


def arm_d9(ctx: Ctx, rounds: int) -> dict:
    out = {"arm": "d9", "rounds": []}
    for round_no in range(1, rounds + 1):
        for which in ("Home", "End"):
            for flagged in (True, False):
                rec = {"round": round_no, "key": f"Ctrl+{which}", "flagged": flagged}
                out["rounds"].append(rec)
                try:
                    rec["foreign"] = ctx.foreign()
                    rec.update(placed(ctx, "plain3", "k1024,k1027x5"))
                    ctx.ev_quiet()
                    mark = len(ctx.log.all)
                    rec["hold"] = inp.hold(ctx.session, ctx.browser, which, ("ctrl",), 1000, flagged)
                    time.sleep(2.0)
                    ctx.drain()
                    rec["log"] = [e for e in ctx.log.all[mark:] if e.get("k") in ("kd", "kdp", "ku", "rq", "rs", "st")]
                    rec["outcome"] = "done"
                except StepError as error:
                    rec["outcome"], rec["error"] = "step-error", str(error)
                except Exception as error:  # noqa: BLE001
                    rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
                    rec["trace"] = traceback.format_exc()[-1500:]
                FLUSH["fn"]()
    return out


def arm_d10(ctx: Ctx, rounds: int) -> dict:
    out = {"arm": "d10", "rounds": []}
    for round_no in range(1, rounds + 1):
        rec = {"round": round_no}
        out["rounds"].append(rec)
        try:
            rec["foreign"] = ctx.foreign()
            rec["load"] = ctx.load("v21")
            rec["open"] = ctx.open("long60")
            reply, entries = v20.settle_rects(ctx.session)
            ctx.trace.all += entries
            t0 = time.monotonic()
            while time.monotonic() - t0 < 40:
                latest = v20.latest_rects(ctx.trace.all)
                if latest and latest.get("parts") == 60:
                    break
                time.sleep(1.0)
                ctx.drain()
            latest = v20.latest_rects(ctx.trace.all)
            rec["rects"] = latest and {"parts": latest.get("parts"), "raw": latest.get("rects"), "docH": latest.get("docH"),
                                       "docW": latest.get("docW")}
            rec["start"] = ctx.start_state()
            mark = len(ctx.log.all)
            press = ctx.ctrl("End")
            rec["press"] = press
            frame = None
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and frame is None:
                ctx.log.drain()
                frame = next((e for e in ctx.log.all[mark:] if e.get("k") == "frame"), None)
                time.sleep(0.05)
            rec["read1"] = frame
            # Read 2: quiet 1 s (no state change, no editor-state push), then an ask and the geometry.
            t0 = time.monotonic()
            while time.monotonic() - t0 < 10:
                before = len(ctx.log.all) + len(ctx.trace.all)
                time.sleep(1.0)
                ctx.drain()
                if len(ctx.log.all) + len(ctx.trace.all) == before:
                    break
            asked = ctx.ask()
            rec["read2"] = {"ask": asked.get("full"), "geometry": pp.evaluate(ctx.session, v20.GEOMETRY)}
            rec["outcome"] = "done"
        except StepError as error:
            rec["outcome"], rec["error"] = "step-error", str(error)
        except Exception as error:  # noqa: BLE001
            rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
            rec["trace"] = traceback.format_exc()[-1500:]
        FLUSH["fn"]()
    return out


def unsaved_noh(ctx: Ctx):
    r7_support.run_in_page(ctx.session, obs1.BEFOREUNLOAD)
    return pp.evaluate(ctx.session, obs1.READ_BEFOREUNLOAD)


def arm_d11a(ctx: Ctx, rounds: int) -> dict:
    out = {"arm": "d11a", "rounds": []}
    for round_no in range(1, rounds + 1):
        rec = {"round": round_no}
        out["rounds"].append(rec)
        try:
            rec["load"] = ctx.load("v21host")
            opened = pp.wait_for(ctx.session, lambda s: (s.get("doc") or "").startswith("plain3.odt") and s.get("state") == "ready", 120)
            rec["opened"] = opened
            ctx.quiet()
            rec["start"] = ctx.start_state()
            r7_support.run_in_page(ctx.session, obs1.ASK_UNSAVED)
            rec["hostBefore"] = pp.evaluate(ctx.session, obs1.READ_HOST)
            mark = len(ctx.log.all)
            rec["press"] = ctx.ctrl("End")
            rec["after"] = ctx.ask().get("full")
            r7_support.run_in_page(ctx.session, obs1.ASK_UNSAVED)
            mark2 = len(ctx.log.all)
            inp.key(ctx.session, ctx.browser, "Z")
            time.sleep(1.5)
            ctx.drain()
            rec["typedRequests"] = [e.get("op") for e in ctx.log.all[mark2:] if e.get("k") == "rq"]
            rec["hostAfter"] = pp.evaluate(ctx.session, obs1.READ_HOST)
            rec["requests"] = [e.get("op") for e in ctx.log.all[mark:] if e.get("k") == "rq"]
            rec["doc"] = pp.evaluate(ctx.session, "(() => document.querySelector('#s-doc').textContent)()")
            rec["outcome"] = "done"
        except StepError as error:
            rec["outcome"], rec["error"] = "step-error", str(error)
        except Exception as error:  # noqa: BLE001
            rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
            rec["trace"] = traceback.format_exc()[-1500:]
        FLUSH["fn"]()
    return out


def arm_d11b(ctx: Ctx, rounds: int) -> dict:
    out = {"arm": "d11b", "rounds": []}
    for round_no in range(1, rounds + 1):
        for kind in ("clean", "dirty"):
            rec = {"round": round_no, "kind": kind}
            out["rounds"].append(rec)
            try:
                rec["load"] = ctx.load("v21")
                rec["open"] = ctx.open("plain3")
                rec["start"] = ctx.start_state()
                rec["unsavedAtOpen"] = unsaved_noh(ctx)
                mark = len(ctx.log.all)
                if kind == "dirty":
                    rec["typed"] = ctx.type_marker()
                    rec["unsavedAfterTyping"] = unsaved_noh(ctx)
                rec["presses"] = []
                for which in ("End", "Home"):
                    press = ctx.ctrl(which)
                    press["unsavedAfter"] = unsaved_noh(ctx)
                    press["checkpoint"] = pp.evaluate(ctx.session, "(() => document.querySelector('#s-checkpoint').textContent)()")
                    rec["presses"].append(press)
                ctx.drain()
                rec["requests"] = [{"op": e.get("op"), "action": e.get("action"), "s": e.get("s")}
                                   for e in ctx.log.all[mark:] if e.get("k") == "rq"]
                rec["engineCaretAfterEnd"] = (rec["presses"][0].get("ask7") or {}).get("caret")
                rec["outcome"] = "done"
            except StepError as error:
                rec["outcome"], rec["error"] = "step-error", str(error)
            except Exception as error:  # noqa: BLE001
                rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
                rec["trace"] = traceback.format_exc()[-1500:]
            FLUSH["fn"]()
    return out


def arm_record(ctx: Ctx, rounds: int, name: str) -> dict:
    """R-xlc and R-table: placement, Ctrl+Home, then one Backspace; recorded."""
    if name == "xlc":
        arms = json.loads((population.N142 / "out/arms.json").read_text())
        jobs = []
        for arm in arms:
            if arm["name"] in population.populations()["xlc"]:
                steps = arm["script"].split(",")
                placement = ",".join(s for s in steps[:steps.index(next(s for s in steps if s.startswith("Mch")))])
                jobs.append((arm["name"], arm["fixture"], placement))
    else:
        jobs = [("table-B2-home-bksp", "table-mid", "k1024x2,k1029,k1027x3")]
    out = {"arm": name, "rounds": []}
    for round_no in range(1, rounds + 1):
        for arm_name, fixture, placement in jobs:
            rec = {"round": round_no, "arm": arm_name, "fixture": fixture, "placement": placement}
            out["rounds"].append(rec)
            try:
                rec.update(placed(ctx, fixture, placement))
                rec["press"] = ctx.ctrl("Home")
                ctx.ev_quiet()
                gen_before = pp.evaluate(ctx.session, mws.GEN)
                mark = len(ctx.log.all)
                inp.key(ctx.session, ctx.browser, "Backspace")
                rec["delete"] = ctx.wait_rs(mark, lambda e: e.get("op") == "editorActionV2"
                                            and str(e.get("action", "")).startswith("delete"), 20)
                if rec["delete"] and not rec["delete"].get("ok"):
                    rec["reopen"] = mws.toast_window(ctx.session, gen_before, 60)
                    time.sleep(3.0)
                ctx.quiet(limit=60)
                rec["generationAfter"] = pp.evaluate(ctx.session, mws.GEN)
                rec["after"] = ctx.ask().get("full")
                rec["log"] = [e for e in ctx.log.all[mark:] if e.get("k") in ("rq", "rs")]
                rec["toasts"] = (pp.evaluate(ctx.session, pp.READ_TOASTS) or [])[-4:]
                rec["save"] = ctx.save(f"{name}-{arm_name}-r{round_no}")
                rec["outcome"] = "done"
            except StepError as error:
                rec["outcome"], rec["error"] = "step-error", str(error)
            except Exception as error:  # noqa: BLE001
                rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
                rec["trace"] = traceback.format_exc()[-1500:]
            FLUSH["fn"]()
    return out


def arm_d5w(ctx: Ctx, rounds: int) -> dict:
    chords = [("Home", ("ctrl",)), ("End", ("ctrl",)), ("Home", ("meta",)), ("End", ("meta",)), ("Home", ("ctrl", "shift"))]
    out = {"arm": "d5w", "rounds": []}
    for round_no in range(1, rounds + 1):
        for variant in ("v20", "v21"):
            rec = {"round": round_no, "page": variant, "chords": []}
            out["rounds"].append(rec)
            try:
                rec["load"] = ctx.load(variant)
                rec["open"] = ctx.open("plain3")
                rec["start"] = ctx.start_state()
                run_script(ctx, "k1024,k1027x5", "placement", None)
                for name, mods in chords:
                    ctx.ev_quiet(0.5, 3)
                    mark = len(ctx.log.all)
                    inp.key(ctx.session, ctx.browser, name, mods)
                    time.sleep(1.0)
                    ctx.quiet()
                    rec["chords"].append({"chord": "+".join(list(mods) + [name]),
                                          "log": [e for e in ctx.log.all[mark:] if e.get("k") in ("kd", "kdp", "rq", "rs")]})
                    if variant == "v21" and "shift" not in mods:
                        # back to mid-text so the next chord is a real move
                        run_script(ctx, "k1024,k1027x2" if name == "Home" else "k1025,k1028,k1027x2", "replace", None)
                rec["outcome"] = "done"
            except StepError as error:
                rec["outcome"], rec["error"] = "step-error", str(error)
            except Exception as error:  # noqa: BLE001
                rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
                rec["trace"] = traceback.format_exc()[-1500:]
            FLUSH["fn"]()
    return out


def element_center(ctx: Ctx, selector: str) -> tuple[float, float] | None:
    box = pp.evaluate(ctx.session, "(() => { const e = document.querySelector(%s); if (!e) return null;"
                      " const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2,"
                      " hidden: e.hidden || r.width === 0 }; })()" % json.dumps(selector))
    if not box or box.get("hidden"):
        return None
    return box["x"], box["y"]


D14_FIXTURES = ("plain3", "long60")
D14_PLAN_MS = 20


def arm_d14(ctx: Ctx, rounds: int) -> dict:
    """D14 (spec §12.3 (c), forced by finding 151): per round and fixture, a fresh load and open, real `Z` at
    the document start (reply awaited: the document is dirty), real Ctrl+End, real `Q` planned D14_PLAN_MS
    after it, then the move's reply, the insert, quiet, an ask, and the save.

    The procedure is diag-dirty-move V1 (plain3) / V4 (long60), imported from `diag_v21_dirty_move`, not
    copied: its long60 settle, its timed keys (Chrome: CDP presses on the monotonic clock; Firefox: one
    WebDriver chain with a pause) and its `move_tail` (reply, insert, +500 ms ask, quiet, final ask, log,
    save, saved texts, summary).  Two differences, both recorded in the README section for §12.3:
      * the plan is 20 ms, not V1/V4's 30 ms: planned 30 ms reached the page as 30.0-31.0 ms (Chrome) and
        32.7-34.6 ms (Firefox) between the keydowns, past the criterion's 30 ms on most rounds;
      * the dirty read (the page's `beforeunload` guard, D11b's instrument) after typing, before the keys.
    The judge reads the gap on the page's own keydown times and the landing in the saved document."""
    import diag_v21_dirty_move as diag   # it imports this module back; main() has aliased it by then
    out = {"arm": "d14", "planMs": D14_PLAN_MS, "dirtyChar": "Z", "marker": "Q",
           "procedure": "diag_v21_dirty_move V1/V4 (settle_long, timed_keys, move_tail)",
           "diagSha256": common.sha256_file(Path(diag.__file__)), "rounds": []}
    for round_no in range(1, rounds + 1):
        for fixture in D14_FIXTURES:
            rec = {"round": round_no, "fixture": fixture}
            out["rounds"].append(rec)
            try:
                rec["foreign"] = ctx.foreign()
                rec["load"] = ctx.load("v21")
                rec["open"] = ctx.open(fixture)
                if fixture == "long60":
                    rec["rects"] = diag.settle_long(ctx)
                rec["start"] = ctx.start_state()
                rec["typed"] = ctx.type_marker()                 # Z at the start, reply awaited
                rec["unsavedAfterTyping"] = unsaved_noh(ctx)
                ctx.ev_quiet()
                mark = len(ctx.log.all)
                rec["sent"] = diag.timed_keys(ctx, [(0, "End", ("ctrl",)), (D14_PLAN_MS, "Q", ())])
                diag.move_tail(ctx, rec, mark, f"d14-{fixture}-r{round_no}", True)
                rec["outcome"] = "done"
            except StepError as error:
                rec["outcome"], rec["error"] = "step-error", str(error)
            except Exception as error:  # noqa: BLE001
                rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
                rec["trace"] = traceback.format_exc()[-1500:]
            FLUSH["fn"]()
    return out


def not_available(name: str, why: str) -> dict:
    return {"arm": name, "rounds": [], "notRun": why}


# ------------------------------------------------------------------ main

def run_arm(ctx: Ctx | None, arm: str, args, page_hook: str | None) -> dict:
    """One arm's result.  A NOT_RUNNABLE arm is recorded with its reason and never touches the browser."""
    if arm in NOT_RUNNABLE:
        return not_available(arm, NOT_RUNNABLE[arm])
    if arm == "d1":
        return arm_d1(ctx, args.rounds, set(filter(None, args.only.split(","))) or None)
    if arm == "d2p":
        return arm_d2p(ctx, args.rounds)
    if arm == "d8":
        return run_d8(ctx, args.rounds, "v21", args.d8.split(","))
    if arm == "d8red":
        return run_d8(ctx, args.rounds, "dist0224", ["d"])
    if arm == "d9":
        return arm_d9(ctx, args.rounds)
    if arm == "d10":
        return arm_d10(ctx, args.rounds)
    if arm == "d11a":
        return arm_d11a(ctx, args.rounds)
    if arm == "d11b":
        return arm_d11b(ctx, args.rounds)
    if arm in ("d11c", "d12"):
        if page_hook is None:
            return not_available(arm, "S-3 (tools/v21_page_hook.py, Agent M) is not there yet")
        import v21_item1_sdk_arms as sdk_arms
        return sdk_arms.run(ctx, arm, args.rounds)
    if arm == "d5w":
        return arm_d5w(ctx, args.rounds)
    if arm in ("xlc", "table"):
        return arm_record(ctx, args.rounds, arm)
    if arm == "d14":
        return arm_d14(ctx, args.rounds)
    raise SystemExit(f"no dispatch for arm {arm!r}")


def main() -> int:
    # One module object whether run as a script or imported (v21_item1_sdk_arms imports this file).
    sys.modules.setdefault("run_v21_shakedown_item1", sys.modules[__name__])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--arms", default="d1")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--only", default="", help="D1 arm names (development)")
    ap.add_argument("--d8", default="a,b,c,d,e")
    ap.add_argument("--window", default="1400x1000")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true", help="label the report a smoke (a development run, never judged)")
    ap.add_argument("--wait-lock", type=float, default=0.0, help="seconds to wait for the S-9 lock (default: refuse)")
    args = ap.parse_args()
    arms = [a for a in args.arms.split(",") if a]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise SystemExit(f"unknown arms {unknown}; known {ARMS}")
    window = tuple(int(v) for v in args.window.split("x"))
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    report_path = args.out / f"report-{args.browser}-{'-'.join(arms)}-{stamp}.json"
    docs = args.out / "docs" / f"{args.browser}-{stamp}"
    docs.mkdir(parents=True, exist_ok=True)
    pre = common.pre_run_checks()
    if pre["refuse"]:
        raise SystemExit(f"pre-run checks refuse: {pre['refuse']}")
    page_hook = None
    if any(a in ("d11c", "d12") for a in arms):
        try:
            import v21_page_hook  # noqa: F401  (S-3, Agent M)
            page_hook = getattr(v21_page_hook, "SNIPPET", None)
        except ImportError:
            page_hook = None
    fixtures = {p.stem: p.read_bytes() for p in sorted(FIXTURE_DIR.glob("*.odt"))}
    long60 = build_long_document(60)
    fixtures["long60"] = long60
    report = {"runner": "run_v21_shakedown_item1.py", "runnerSha256": sha256_bytes(Path(__file__).read_bytes()),
              "counted": False, "smoke": args.smoke, "browser": args.browser, "arms": arms, "window": window,
              "startedAt": common.now_iso(), "preRun": pre,
              "inputs": {name: sha256_bytes(raw) for name, raw in fixtures.items()},
              "reference": {"arms.json": common.sha256_file(population.N142 / "out/arms.json"),
                            "population.json": common.sha256_file(marker.D1M / "out/population.json"),
                            "d1-marker/SHA256SUMS": common.sha256_file(marker.D1M / "SHA256SUMS"),
                            "read_marker.py": common.sha256_file(marker.READ_MARKER),
                            "d1_population.py": common.sha256_file(marker.D1_POPULATION)},
              "results": {}}

    def flush() -> None:
        report["pages"] = pages.identity
        report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))

    FLUSH["fn"] = flush
    scratch = Path(tempfile.mkdtemp(prefix="v21-item1-"))
    pages = Pages(scratch, fixtures, page_hook)
    session = None
    with common.browser_lock(f"run_v21_shakedown_item1 {args.browser} {','.join(arms)}", wait_s=args.wait_lock) as holder:
        report["lock"] = holder
        try:
            session = common.open_browser(args.browser, window)
            report["browserVersion"] = getattr(session, "version", None)
            ctx = Ctx(session, args.browser, pages, report, docs)
            for arm in arms:
                t0 = time.monotonic()
                try:
                    result = run_arm(ctx, arm, args, page_hook)
                except Exception as error:  # noqa: BLE001
                    result = {"arm": arm, "runnerError": f"{type(error).__name__}: {error}",
                              "trace": traceback.format_exc()[-2000:]}
                result["seconds"] = round(time.monotonic() - t0, 1)
                report["results"][arm] = result
                flush()
        finally:
            report["completedAt"] = common.now_iso()
            if session is not None:
                report["close"] = common.close_browser(session)
            pages.close()
            flush()
    summary = {arm: {"rounds": len(r.get("rounds", [])),
                     "outcomes": sorted({x.get("outcome") for x in r.get("rounds", [])} - {None}),
                     "error": r.get("runnerError") or r.get("notRun")} for arm, r in report["results"].items()}
    print(json.dumps({"report": str(report_path), **summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
