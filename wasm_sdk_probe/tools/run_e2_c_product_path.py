#!/usr/bin/env python3
"""Drive the E2-C product page down the paths a USER takes, not the ones a
harness takes.

Why this exists
---------------
On 2026-08-16 three product defects were found in one day, by a person, in the
D5 operator round -- and not one of them was reachable by any automated round
this tree had:

  * finding 049: the product's own save button wrote 15 bytes of
    "[object Object]".  Every harness calls `session.save()` itself and
    destructures `{bytes}`, so every harness measured the SHELL's save and none
    of them ever pressed the button.
  * finding 050: every IME commit after the first in a session was rejected as a
    buffer mismatch.  Every harness calls `session.commitText()` directly, so
    none of them ever went through the adapter's composition path, and none of
    them ever typed a SECOND time.
  * Ctrl+C never asked the engine for the selection.  Nothing called
    `copySelection()`; the shell had it all along.

The shape they share is one sentence: **where the harness's path and the user's
path differ, only the user's path is unmeasured.**  This runner closes that gap
for the three known shapes and leaves a place to add the next one.

What this is NOT
----------------
The events here are synthesised, so `isTrusted` is false throughout.  **This is
not D5 and no cell may cite it.**  D5's entire subject is trusted input and
needs a human; this is a regression net underneath it.  What the two have in
common is only the path -- the product's own handlers.

Declared shims (SPEC E2-C 6: a harness that patches the page it observes says so
where the evidence can see it):

  * `URL.createObjectURL` -- the product saves by handing a Blob to a download
    link, and nothing outside the page can read a download.
  * `HTMLAnchorElement.prototype.click` for anchors carrying `download` -- so a
    headless browser is never asked to open a save dialog, which would block
    every subsequent command.  What this leaves unmeasured is the download
    plumbing itself (href/download/click); an operator established that by hand
    on 2026-08-16 (findings/evidence/049/verified-by-operator/).
  * `#toast.textContent` is cleared before a step, so that "the product said
    nothing" is distinguishable from "the product said something earlier".

Being able to fail
------------------
`--mutate` reintroduces one of the three defects into a symlink mirror of dist/
(dist itself is never written) and requires the matching check to go RED while
the others stay green.  A check that cannot be shown to fail is not a check --
this tree has recorded that lesson often enough to build it into the tool.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

# The three texts committed through the composition path.  Distinct, and absent
# from every fixture, so finding them in the saved ODT is a statement about this
# run.
IME_TEXTS = ["甲一", "乙二", "丙三"]

# --------------------------------------------------------------------- shims

INSTALL = """(() => {
if (globalThis.__pp) return "already";
const pp = { saves: [], anchorClicks: 0, error: null };
globalThis.__pp = pp;
const nativeCreate = URL.createObjectURL.bind(URL);
URL.createObjectURL = (blob) => {
  const url = nativeCreate(blob);
  void (async () => {
    try {
      const bytes = new Uint8Array(await blob.arrayBuffer());
      let binary = "";
      for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
      pp.saves.push({ bytes: bytes.length, type: blob.type, b64: btoa(binary) });
    } catch (error) { pp.error = String(error); }
  })();
  return url;
};
const nativeClick = HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click = function () {
  if (this.hasAttribute("download")) { pp.anchorClicks += 1; return; }
  return nativeClick.call(this);
};
return "installed";
})()"""

CLEAR_TOAST = """(() => {
document.querySelector('#toast').textContent = '';
return true;
})()"""

READ_TOAST = "(() => document.querySelector('#toast').textContent)()"

SAVE_COUNT = "(() => globalThis.__pp.saves.length)()"

READ_SAVE = "(() => globalThis.__pp.saves[ARG_INDEX] || null)()"

PRESS = """(() => {
const button = document.querySelector('#toolbar button[data-action="ARG_ACTION"]');
if (!button) return false;
button.click();
return true;
})()"""

POINT_AT = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const x = box.left + box.width * ARG_X;
const y = box.top + box.height * ARG_Y;
canvas.dispatchEvent(new PointerEvent('pointerdown', {
  clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, bubbles: true }));
canvas.dispatchEvent(new PointerEvent('pointerup', {
  clientX: x, clientY: y, button: 0, buttons: 0, pointerId: 1, bubbles: true }));
return true;
})()"""

DRAG = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const at = (fx, fy) => ({ x: box.left + box.width * fx, y: box.top + box.height * fy });
const a = at(ARG_X1, ARG_Y1);
const b = at(ARG_X2, ARG_Y2);
const send = (type, point, buttons) => canvas.dispatchEvent(new PointerEvent(type, {
  clientX: point.x, clientY: point.y, button: 0, buttons, pointerId: 1, bubbles: true }));
send('pointerdown', a, 1);
send('pointermove', { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, 1);
send('pointermove', b, 1);
send('pointerup', b, 0);
return true;
})()"""

# One composition, through the product page's own input sink.
#
# The line that matters is `sink.value += TEXT`.  A real IME does not write that
# line -- the browser does, as the default action of `beforeinput` with
# inputType `insertCompositionText`, which is NOT cancelable during composition.
# Synthetic events run no default action, so without this the textarea would
# stay empty, the adapter's buffer comparison would short-circuit on an empty
# string, and finding 050 would be invisible to this harness exactly as it was
# invisible to every other one.  Appending (not assigning) is what the browser
# does, and it is what makes the fix's absence observable: nothing in this tree
# clears that buffer except the fix.
COMPOSE = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
sink.dispatchEvent(new CompositionEvent('compositionstart', { data: '', bubbles: true }));
sink.dispatchEvent(new CompositionEvent('compositionupdate', { data: 'ARG_TEXT', bubbles: true }));
sink.dispatchEvent(new InputEvent('beforeinput', {
  inputType: 'insertCompositionText', data: 'ARG_TEXT', bubbles: true, cancelable: false }));
sink.value += 'ARG_TEXT';
sink.dispatchEvent(new CompositionEvent('compositionend', { data: 'ARG_TEXT', bubbles: true }));
return sink.value;
})()"""

COPY = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
const notPrevented = sink.dispatchEvent(
  new ClipboardEvent('copy', { bubbles: true, cancelable: true }));
return { handlerRan: !notPrevented };
})()"""

# ----------------------------------------------------------------- mutations

MUTATIONS = {
    "save": {
        "check": "product-save-button-writes-a-real-odt",
        "path": "e2-editor-app.js",
        "find": 'const { bytes } = await run("儲存", () => session.save());',
        "replace": 'const bytes = await run("儲存", () => session.save());',
        "reintroduces": "finding 049",
    },
    "ime": {
        "check": "every-ime-commit-reaches-the-document",
        "path": "input/input-adapter.js",
        "find": '      this._target.value = "";',
        "replace": "      /* mutation: finding 050 reintroduced */;",
        "reintroduces": "finding 050",
    },
    "copy": {
        "check": "ctrl-c-asks-the-engine",
        "path": "e2-editor-app.js",
        "find": 'el.sink.addEventListener("copy", (event) => {',
        "replace": 'el.sink.addEventListener("copy-removed-by-mutation", (event) => {',
        "reintroduces": "the Ctrl+C gap found in the D5 operator round",
    },
}


def build_mirror(source: Path, target: Path, overrides: dict[str, bytes]) -> None:
    """Mirror `source` into `target` with symlinks, materialising `overrides`.

    dist/ is 7.5 GB and holds every frozen profile; copying it to break one file
    would be both slow and a way to accidentally write to a frozen artifact.
    Everything is a symlink except the directories leading to an override.
    """
    real_dirs: set[str] = set()
    for relative in overrides:
        parent = Path(relative).parent
        while parent != Path("."):
            real_dirs.add(parent.as_posix())
            parent = parent.parent

    def walk(relative: Path) -> None:
        source_dir = source / relative
        target_dir = target / relative
        target_dir.mkdir(parents=True, exist_ok=True)
        for entry in source_dir.iterdir():
            child = relative / entry.name if relative != Path(".") else Path(entry.name)
            key = child.as_posix()
            if key in overrides:
                (target / child).write_bytes(overrides[key])
            elif entry.is_dir() and key in real_dirs:
                walk(child)
            else:
                os.symlink(entry.resolve(), target / child)

    walk(Path("."))


def apply_mutation(name: str, scratch: Path) -> tuple[Path, dict]:
    spec = MUTATIONS[name]
    original = (PROJECT / "dist" / spec["path"]).read_text(encoding="utf-8")
    hits = original.count(spec["find"])
    if hits != 1:
        raise SystemExit(
            f"mutation '{name}' expects exactly one occurrence of its pattern in "
            f"dist/{spec['path']}, found {hits}.  The tree moved under the "
            f"mutation; fix the pattern rather than the count.")
    mutated = original.replace(spec["find"], spec["replace"])
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root,
                 {spec["path"]: mutated.encode("utf-8")})
    return root, {"mutation": name, "file": spec["path"],
                  "reintroduces": spec["reintroduces"],
                  "mustGoRed": spec["check"]}


# ------------------------------------------------------------------- helpers


def wait_for(session, predicate, timeout, poll=0.4):
    deadline = time.monotonic() + timeout
    state = None
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and predicate(state):
            return state
        time.sleep(poll)
    return state


def revision_of(state) -> int | None:
    text = (state or {}).get("revision") or ""
    return int(text) if text.isdigit() else None


def wait_saves(session, count, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if (evaluate(session, SAVE_COUNT) or 0) >= count:
            return True
        time.sleep(0.3)
    return False


def zip_report(raw: bytes) -> dict:
    out = {"bytes": len(raw), "magic": raw[:4].hex(), "isZip": raw[:4] == b"PK\x03\x04"}
    if not out["isZip"]:
        out["head"] = raw[:64].decode("utf-8", "replace")
        return out
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            out["entries"] = len(archive.namelist())
            out["badEntry"] = archive.testzip()
            out["content"] = archive.read("content.xml").decode("utf-8", "replace")
    except Exception as error:            # noqa: BLE001 -- reported, not raised
        out["zipError"] = str(error)
    return out


# ---------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--fixture", default="list-contexts")
    parser.add_argument("--mutate", choices=tuple(MUTATIONS) + ("none",), default="none")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--out", default=None, help="write the report here as JSON")
    args = parser.parse_args()

    report: dict = {
        "schemaVersion": 1,
        "release": "e2-c-product-path",
        "browser": args.browser,
        "fixture": args.fixture,
        "isTrusted": False,
        "notD5": "synthetic events; SPEC E2-C D5 requires trusted input and a human",
        "shims": ["URL.createObjectURL",
                  "HTMLAnchorElement.prototype.click (download anchors)",
                  "#toast.textContent cleared between steps"],
        "mutation": args.mutate if args.mutate != "none" else None,
        "checks": [],
        "steps": [],
    }

    scratch = Path(tempfile.mkdtemp(prefix="e2c-product-path-"))
    root = PROJECT / "dist"
    if args.mutate != "none":
        root, mutation_report = apply_mutation(args.mutate, scratch)
        report["mutationDetail"] = mutation_report

    def check(cid, ok, **fields):
        report["checks"].append({"id": cid, "ok": bool(ok), **fields})

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        navigate(session, base)

        booted = wait_for(session, lambda s: s.get("state") in ("ready", "stopped",
                                                               "expired"),
                          args.timeout)
        report["steps"].append({"step": "boot", "state": booted})
        if not booted or booted.get("state") != "ready":
            report["failedAt"] = "boot"
            return finish(report, args)

        report["steps"].append({"step": "install-shims",
                                "result": evaluate(session, INSTALL)})

        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        caret = wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        report["steps"].append({"step": "place-caret", "state": caret})
        if not caret or "失敗" in (caret.get("latency") or ""):
            report["failedAt"] = "place-caret"
            return finish(report, args)

        # ------------------------------------------------ 049: the save button
        evaluate(session, CLEAR_TOAST)
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        captured = wait_saves(session, 1)
        toast_after_save = evaluate(session, READ_TOAST) or ""
        saved = evaluate(session, READ_SAVE.replace("ARG_INDEX", "0")) if captured else None
        first = zip_report(base64.b64decode(saved["b64"])) if saved else {}
        check("product-save-button-writes-a-real-odt",
              bool(first.get("isZip")) and first.get("badEntry") is None
              and "NaN" not in toast_after_save,
              observed={"capturedBytes": first.get("bytes"),
                        "magic": first.get("magic"),
                        "head": first.get("head"),
                        "entries": first.get("entries"),
                        "toast": toast_after_save,
                        "anchorClicks": evaluate(session,
                                                 "(() => globalThis.__pp.anchorClicks)()")},
              oracle="the bytes the product hands to the download begin with the ZIP "
                     "magic and open as an ODT, and its own toast reports a size "
                     "rather than NaN")

        # -------------------------------------- 050: three commits, three edits
        before = revision_of(evaluate(session, READ_STATE))
        commits = []
        last = before if before is not None else 0
        for text in IME_TEXTS:
            evaluate(session, CLEAR_TOAST)
            sink = evaluate(session, COMPOSE.replace("ARG_TEXT", text))
            # A commit that is going to be dropped is dropped silently, so this
            # waits for the revision it expects and gives up rather than hanging.
            settled = wait_for(session,
                               lambda s, floor=last: revision_of(s) is not None
                               and revision_of(s) > floor,
                               8)
            observed = revision_of(settled)
            commits.append({"text": text, "sinkAfter": sink, "revision": observed,
                            "toast": evaluate(session, READ_TOAST)})
            if observed is not None:
                last = max(last, observed)
        after = revision_of(evaluate(session, READ_STATE))
        report["steps"].append({"step": "ime-commits", "commits": commits,
                                "revisionBefore": before, "revisionAfter": after})

        # The document, not only the counter: the counter is what round 5's
        # analyzer looked at, and it reported success while two thirds of a
        # user's typing was being dropped.
        evaluate(session, CLEAR_TOAST)
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        wait_saves(session, 2)
        second_raw = evaluate(session, READ_SAVE.replace("ARG_INDEX", "1"))
        second = zip_report(base64.b64decode(second_raw["b64"])) if second_raw else {}
        content = second.get("content") or ""
        present = [t for t in IME_TEXTS if t in content]
        advanced = (after - before) if (after is not None and before is not None) else None
        check("every-ime-commit-reaches-the-document",
              advanced == len(IME_TEXTS) and len(present) == len(IME_TEXTS),
              observed={"revisionBefore": before, "revisionAfter": after,
                        "advancedBy": advanced, "committed": IME_TEXTS,
                        "foundInSavedOdt": present,
                        "savedBytes": second.get("bytes")},
              oracle="three commits through the product's composition path advance "
                     "the revision three times AND all three strings are in the "
                     "saved ODT")

        # ------------------------------------------------------ Ctrl+C reaches
        evaluate(session, DRAG.replace("ARG_X1", "0.20").replace("ARG_Y1", "0.28")
                 .replace("ARG_X2", "0.75").replace("ARG_Y2", "0.28"))
        time.sleep(1.5)
        evaluate(session, CLEAR_TOAST)
        copy_result = evaluate(session, COPY)
        time.sleep(1.5)
        copy_toast = evaluate(session, READ_TOAST) or ""
        # Three outcomes, and only one of them is the defect: silence.  A typed
        # clipboard error still means the product asked the engine -- and the
        # real clipboard write cannot be established headless anyway (WebDriver
        # refuses it), which is why finding 050's note leaves that half to D5.
        copied = "已複製" in copy_toast
        spoke = bool(copy_toast.strip())
        check("ctrl-c-asks-the-engine",
              bool(copy_result and copy_result.get("handlerRan")) and spoke,
              observed={"handlerRan": (copy_result or {}).get("handlerRan"),
                        "toast": copy_toast, "reportedACount": copied},
              oracle="a copy event on the product page is handled by the product "
                     "(default prevented) and produces a clipboard outcome rather "
                     "than silence",
              notEstablished="whether the OS clipboard received the text; WebDriver "
                             "refuses clipboard access, so that half belongs to D5")
        return finish(report, args)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        shutil.rmtree(scratch, ignore_errors=True)


def finish(report: dict, args) -> int:
    checks = report["checks"]
    must_be_red = MUTATIONS[args.mutate]["check"] if args.mutate != "none" else None
    if must_be_red:
        red = next((c for c in checks if c["id"] == must_be_red), None)
        others_ok = all(c["ok"] for c in checks if c["id"] != must_be_red)
        report["ok"] = bool(red is not None and not red["ok"] and others_ok)
        report["verdict"] = (
            "the mutation was detected by the check that owns it"
            if report["ok"] else
            "THE MUTATION WAS NOT DETECTED -- the check cannot fail, or another "
            "check failed with it")
    else:
        report["ok"] = bool(checks) and all(c["ok"] for c in checks)
        report["verdict"] = ("every product path this covers behaves"
                             if report["ok"] else "a product path is broken")
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
