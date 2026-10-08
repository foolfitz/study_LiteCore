#!/usr/bin/env python3
"""Finding 111, measured in a browser: does a key typed right after some text
overtake the text still waiting in the input adapter?

Finding 111 (2026-10-06) was read from the source and reproduced only in a unit
test: typed text goes through the input adapter's own queue, one commitText at a
time, while Delete/Backspace and Enter go straight into the session's queue, so a
key pressed while a typed character is still in the adapter can be dispatched
before it.  Its own next step: "measure the frequency in a browser with real keys
(sweep the gap between keys) before choosing a fix".  This is that measurement.
It changes no product byte: the standalone page from `dist/` (the shipped page,
v19 since the cutover), served from a symlink mirror with one fixture added.

One trial: open `boundaries.odt` fresh, click at the end of its first paragraph
("M01 plain alpha", the merge rounds' C01 click on v19) and press End, wait until
the page is idle; then REAL keys, `X`, gap, `Y`, gap, KEY; wait until idle; save
with the product's own button (captured) and read the saved paragraph text.

  KEY        correct first paragraphs                 overtaken
  Backspace  "M01 plain alphaX"                       "M01 plain alphaY" (X went, Y came after),
                                                      "M01 plain alphXY" (both came after)
  Enter      "M01 plain alphaXY", ""                  "M01 plain alphaX", "Y"; "M01 plain alpha", "XY"

Anything else is `other` and is reported with its text (the fixture is synthetic).
The gap is nominal: Chrome sends each key over CDP and sleeps the gap in Python;
Firefox sends the whole burst as one WebDriver action chain with pauses.  The
page's own keydown times (a capture-phase listener, performance.now()) are kept,
so the report says what the gaps really were.

  probe_111_overtake.py --browser chrome --out REPORT.json [--gaps 0,10,20,40,80,160]
                        [--keys Backspace,Enter] [--repeats 10]
"""
from __future__ import annotations

import argparse
import base64
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

HERE = Path(__file__).resolve().parent.parent
DIST = HERE / "dist"
FIXTURE = HERE / "test-docs" / "merge" / "odt" / "boundaries.odt"
FIRST = "M01 plain alpha"
# v19's click at the end of the first paragraph: the merge runner's C01 click on
# boundaries.odt (12474 x 34528 twips; X7 counted reports, caret 2991, 1418).
END_OF_FIRST = ("0.236572", "0.045065")
EXPECTED = {
    "Backspace": {"ok": [FIRST + "X"], "overtaken-1": [FIRST + "Y"], "overtaken-2": ["M01 plain alphXY"]},
    "Enter": {"ok": [FIRST + "XY", ""], "overtaken-1": [FIRST + "X", "Y"], "overtaken-2": [FIRST, "XY"]},
}
CDP_KEYS = {"Backspace": ("Backspace", "Backspace", 8), "Enter": ("Enter", "Enter", 13),
            "End": ("End", "End", 35)}
WD = {"Backspace": "", "Enter": "", "End": ""}
# Capture-phase, on the document, so it sees every key before the page does.
# DOM, not a page global: Firefox evaluates in a Marionette sandbox.
KEYLOG = """(() => { const root = document.documentElement;
  if (root.dataset.k111 === undefined) {
    document.addEventListener('keydown', (e) => {
      const log = JSON.parse(root.dataset.k111 || '[]');
      log.push([e.key, Math.round(performance.now() * 10) / 10]);
      root.dataset.k111 = JSON.stringify(log); }, true);
  }
  root.dataset.k111 = '[]'; return true; })()"""
READ_KEYLOG = "(() => JSON.parse(document.documentElement.dataset.k111 || '[]'))()"


def key_events(name: str) -> list[dict]:
    if name in CDP_KEYS:
        key, code, vk = CDP_KEYS[name]
        return [{"type": t, "key": key, "code": code, "windowsVirtualKeyCode": vk,
                 "nativeVirtualKeyCode": vk} for t in ("rawKeyDown", "keyUp")]
    vk = ord(name.upper())
    events = []
    for t in ("rawKeyDown", "char", "keyUp"):
        e = {"type": t, "key": name, "code": f"Key{name.upper()}", "windowsVirtualKeyCode": vk,
             "nativeVirtualKeyCode": vk, "modifiers": 8 if name.isupper() else 0}
        if t == "char":
            e["text"] = name
        events.append(e)
    return events


def burst(session, browser: str, keys: list[str], gap_ms: int) -> None:
    """The keys in order, `gap_ms` between one key's release and the next press."""
    if browser == "chrome":
        for index, name in enumerate(keys):
            if index and gap_ms:
                time.sleep(gap_ms / 1000)
            for event in key_events(name):
                session.call("Input.dispatchKeyEvent", event)
        return
    actions = []
    for index, name in enumerate(keys):
        if index and gap_ms:
            actions.append({"type": "pause", "duration": gap_ms})
        value = WD.get(name, name)
        actions += [{"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}]
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
    session.command("DELETE", "/actions")


def quiet(session, limit: float = 30) -> dict:
    deadline, since, seen = time.monotonic() + limit, None, {}
    while time.monotonic() < deadline:
        seen = pp.evaluate(session, pp.READ_STATE) or {}
        if seen.get("state") == "ready" and str(seen.get("pending")) == "0":
            since = since or time.monotonic()
            if time.monotonic() - since >= 0.5:
                return seen
        else:
            since = None
        time.sleep(0.1)
    return {**seen, "timedOut": True}


def save_texts(session) -> list[str] | None:
    index = pp.evaluate(session, pp.SAVE_COUNT) or 0
    pp.evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
    if not pp.wait_saves(session, index + 1, 60):
        return None
    saved = pp.evaluate(session, pp.READ_SAVE.replace("ARG_INDEX", str(index)))
    raw = base64.b64decode(saved["b64"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return odt_paragraphs.paragraph_texts_from_xml(archive.read("content.xml"))


def classify(key: str, texts: list[str] | None) -> str:
    if texts is None:
        return "no-save"
    for verdict, head in EXPECTED[key].items():
        if texts[:len(head)] == head:
            return verdict
    return "other"


def trial(session, browser: str, key: str, gap: int, number: int, url: str) -> dict:
    out: dict = {"key": key, "gapMs": gap, "n": number}
    name = f"probe-111-{key}-{gap}-{number}.odt"
    pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", url).replace("ARG_NAME", name))
    opened = pp.wait_for(session, lambda s: (s.get("doc") or "") == name and s.get("state") == "ready", 120)
    out["opened"] = bool(opened)
    quiet(session)
    before = (pp.evaluate(session, pp.READ_STATE) or {}).get("latency")
    pp.evaluate(session, pp.POINT_AT.replace("ARG_X", END_OF_FIRST[0]).replace("ARG_Y", END_OF_FIRST[1]))
    pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or "") and s.get("latency") != before, 30)
    quiet(session)
    burst(session, browser, ["End"], 0)
    quiet(session)
    revision = (pp.evaluate(session, pp.READ_STATE) or {}).get("revision")
    pp.evaluate(session, KEYLOG)
    started = time.monotonic()
    burst(session, browser, ["X", "Y", key], gap)
    out["sendSeconds"] = round(time.monotonic() - started, 3)
    settled = quiet(session)
    out["keydowns"] = pp.evaluate(session, READ_KEYLOG)
    out["revision"] = [revision, settled.get("revision")]
    out["latency"] = settled.get("latency")
    out["toast"] = settled.get("toast")
    texts = save_texts(session)
    out["verdict"] = classify(key, texts)
    out["head"] = texts[:3] if texts is not None else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--gaps", default="0,10,20,40,80,160")
    ap.add_argument("--keys", default="Backspace,Enter")
    ap.add_argument("--repeats", type=int, default=10)
    args = ap.parse_args()
    gaps = [int(g) for g in args.gaps.split(",")]
    keys = args.keys.split(",")
    mirror = Path(tempfile.mkdtemp(prefix="probe-111-")) / "root"
    pp.build_mirror(DIST, mirror, {})
    target = mirror / "probe-111.odt"
    if target.exists():
        raise SystemExit(f"refusing to write {target}")
    target.write_bytes(FIXTURE.read_bytes())
    report = {"probe": "probe_111_overtake.py", "browser": args.browser,
              "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "page": hashlib.sha256((DIST / "e2-editor-app.js").read_bytes()).hexdigest(),
              "fixture": FIXTURE.name, "gaps": gaps, "keys": keys, "repeats": args.repeats,
              "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "trials": []}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port),
                               "--root", str(mirror)], cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = (pp.ChromeSession if args.browser == "chrome" else pp.FirefoxSession)("cold")
        report["version"] = getattr(session, "version", None)
        pp.navigate(session, base)
        report["boot"] = pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        report["shims"] = pp.evaluate(session, pp.INSTALL)
        # Interleaved: every key and gap once per pass, so drift over the run
        # (a warming JIT, a growing heap) spreads over all cells alike.
        for number in range(1, args.repeats + 1):
            for key in keys:
                for gap in gaps:
                    try:
                        result = trial(session, args.browser, key, gap, number, "./probe-111.odt")
                    except Exception as error:  # noqa: BLE001 -- recorded, the run goes on
                        result = {"key": key, "gapMs": gap, "n": number, "verdict": "runner-error",
                                  "error": f"{type(error).__name__}: {error}"}
                    report["trials"].append(result)
                    print(f"{number:2d} {key:9s} {gap:4d} ms {result['verdict']}", flush=True)
                    args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    finally:
        report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if session is not None:
            try:
                session.close()
            except Exception as error:  # noqa: BLE001
                report["closeError"] = str(error)
        server.terminate()
        server.wait(timeout=10)
        table: dict = {}
        for t in report["trials"]:
            cell = table.setdefault(f"{t['key']}/{t['gapMs']}", {})
            cell[t["verdict"]] = cell.get(t["verdict"], 0) + 1
        report["table"] = table
        args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps(report["table"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
