#!/usr/bin/env python3
"""SPEC-M3-autosave §4 M1: does typing during a save lose characters?

Not a counted runner; no product byte is touched (host 0.2.12, page 8909564e).
The owner's document (the production-UI runner's gitignored copy) is uploaded as
PROBE_NAME.  One browser session per round; in it, three arms in this order,
each starting with its own marker so the server's text says which arm's letters
arrived:

  C  control: no save; 20 letters by real keys, 50 ms apart
  A  press the toolbar's save, wait 50 ms, then the same 20 letters 50 ms apart
  H  press save, wait 50 ms, then one letter "held": 40 repeats 33 ms apart
     (Chrome: CDP keyDown with autoRepeat; Firefox: 40 presses, the WebDriver
     call's own latency recorded)

Then quiet, one manual save to settle, and the server's file is read.  The count
is the arm's letters found after its marker (lowercase ASCII up to the next
marker) against the letters sent.  The report carries none of the owner's text:
only the received run of our own letters.

Prediction (spec §4, written before the shakedown): A loses nothing; H loses
characters.  The shakedown missed both (A50 lost 4, H lost 0 -- H's save took
173 ms against A's 609 ms).  Prediction for the widened arms, written before
they ran: a loss happens when more than 9 keys (8 queued + 1 in flight) arrive
while the engine is busy, i.e. roughly saveMs / gap > 9 -- A100 and A150 lose
nothing on a ~0.6 s save; A50 and H lose characters whenever their save takes
more than about 450 / 300 ms.

  probe_autosave_m1.py --out DIR [--browsers chrome,firefox] [--rounds 3]
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_m3_production_ui as ui  # noqa: E402
from check_m3_locks import Server, login, open_from_files  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
from odt_paragraphs import paragraph_texts_from_xml  # noqa: E402
from probe_m3_gate0_coep import utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import PRESS  # noqa: E402

PROBE_NAME = "probe-autosave-m1.odt"
LETTERS = "abcdefghijklmnoprstu"   # 20
HELD = "k"
# (arm, marker, save first?, held?, gap s).  After the shakedown (2026-10-12,
# Chrome: A at 50 ms lost 4 of 20 during a 609 ms save; H lost 0 during a 173 ms
# save -- both predictions missed) the rates were widened: 50 ms is 20 keys/s,
# faster than people type; 100 and 150 ms are about 10 and 7 keys/s.
ARMS = (("C", "zqxzc", False, False, 0.05), ("A50", "zqxza", True, False, 0.05),
        ("A100", "zqxzb", True, False, 0.10), ("A150", "zqxzd", True, False, 0.15),
        ("H", "zqxzh", True, True, 0.033))

# Every change of the pill's state and of the latency line, and every keydown
# the sink sees, with performance.now().
TIMELINE = """(() => { const t0 = performance.now(); const log = window.__m1 = [];
  const pill = document.querySelector('#state-pill'), lat = document.querySelector('#s-latency'),
        sink = document.querySelector('#sink'), toastEl = document.querySelector('#toast');
  const rec = (what) => log.push({ t: Math.round(performance.now() - t0), what, state: pill.dataset.state,
    latency: lat.textContent, toast: toastEl.classList.contains('show') ? toastEl.textContent : null });
  new MutationObserver(() => rec('pill')).observe(pill, { attributes: true, attributeFilter: ['data-state'] });
  new MutationObserver(() => rec('latency')).observe(lat, { childList: true, characterData: true, subtree: true });
  new MutationObserver(() => rec('toast')).observe(toastEl, { attributes: true, childList: true, subtree: true });
  sink.addEventListener('keydown', (e) => rec('keydown:' + e.key + (e.repeat ? ':repeat' : '')), true);
  rec('installed'); return true; })()"""
MARK = "(() => window.__m1.length)()"
READ = "(() => window.__m1.slice(ARG_FROM))()"


def type_letters(session, kind: str, text: str, gap: float) -> list[float]:
    stamps = []
    for ch in text:
        stamps.append(time.monotonic())
        ui.press(session, kind, ch)
        time.sleep(gap)
    return stamps


def hold(session, kind: str, ch: str, repeats: int, gap: float) -> list[float]:
    stamps = []
    if kind == "chrome":
        code, vk = f"Key{ch.upper()}", ord(ch.upper())
        for i in range(repeats):
            stamps.append(time.monotonic())
            for phase in ("rawKeyDown", "char"):
                params = {"type": phase, "key": ch, "code": code, "windowsVirtualKeyCode": vk,
                          "nativeVirtualKeyCode": vk, "autoRepeat": i > 0}
                if phase == "char":
                    params["text"] = ch
                session.call("Input.dispatchKeyEvent", params)
            time.sleep(gap)
        session.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": ch, "code": code,
                                                "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk})
        return stamps
    for _ in range(repeats):
        stamps.append(time.monotonic())
        ui.press(session, kind, ch)
        time.sleep(gap)
    return stamps


def received(server: Server) -> dict[str, Any]:
    status, raw = server.instance.dav("GET", PROBE_NAME)
    out: dict[str, Any] = {"status": status, "bytes": len(raw)}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        texts = paragraph_texts_from_xml(archive.read("content.xml"))
    para = next((p for p in texts if ARMS[0][1] in p), None)
    if para is None:
        out["error"] = "no paragraph carries the first marker"
        return out
    for arm, marker, *_ in ARMS:
        at = para.find(marker)
        if at < 0:
            out[arm] = None
            continue
        rest = para[at + len(marker):]
        cut = rest.find("zqxz")
        if cut >= 0:
            rest = rest[:cut]
        out[arm] = re.match(r"[a-z]*", rest).group(0)
    return out


def run_round(kind: str, server: Server, doc: bytes) -> dict[str, Any]:
    base = server.instance.base
    record: dict[str, Any] = {"browser": kind, "startedAt": utc_now()}
    record["clearedLocks"] = server.clear_locks()
    record["upload"] = server.upload(server.admin, PROBE_NAME, doc)
    session = ui.new_session(kind)
    record["version"] = getattr(session, "version", None)
    try:
        record["login"] = login(session, base, "admin", server.instance.password)
        open_from_files(session, base, "", PROBE_NAME, record)
        record["opened"] = ui.quiet(session, 90)
        evaluate(session, TIMELINE)
        record["click"] = ui.click(session, ui.IN_TEXT)
        record["arms"] = {}
        for arm, marker, saves, held, gap in ARMS:
            rec: dict[str, Any] = {"gapMs": round(gap * 1000), "save": saves, "held": held}
            rec["marker"] = [ui.keyed(session, kind, ch) for ch in marker]
            time.sleep(0.5)
            ui.quiet(session)
            start = evaluate(session, MARK)
            t0 = time.monotonic()
            if saves:
                evaluate(session, PRESS.replace("ARG_ACTION", "save"))
                time.sleep(0.05)
            stamps = (hold(session, kind, HELD, 40, gap) if held
                      else type_letters(session, kind, LETTERS, gap))
            rec["sendMs"] = [round((s - t0) * 1000) for s in stamps]
            time.sleep(1.0)
            rec["settled"] = ui.quiet(session, 60)
            # The arm's own save must have landed before the next arm's marker.
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                saves = (evaluate(session, ui.HOST) or {}).get("saves") or []
                if not saves or saves[-1].get("settled") is True:
                    break
                time.sleep(0.3)
            rec["log"] = evaluate(session, READ.replace("ARG_FROM", str(start)))
            record["arms"][arm] = rec
        record["finalSave"] = ui.save_and_settle(session, 60)
        record["host"] = evaluate(session, ui.HOST)
        record["server"] = received(server)
        sent = {arm: (HELD * 40 if held else LETTERS) for arm, _, _, held, _ in ARMS}
        record["lost"] = {arm: (None if record["server"].get(arm) is None
                                else len(sent[arm]) - len(record["server"][arm])) for arm in sent}
        record["exact"] = {arm: record["server"].get(arm) == sent[arm] for arm in sent}
        # The engine's save time per arm, from the latency line ("儲存 N ms").
        record["saveMs"] = {arm: next((int(m.group(1)) for e in record["arms"][arm]["log"]
                                       if (m := re.match(r"儲存 (\d+) ms", e.get("latency") or ""))), None)
                            for arm in sent}
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            record.setdefault("closeError", traceback.format_exc())
        record["completedAt"] = utc_now()
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    doc = ui.DOC.read_bytes()
    server = Server(Instance(DEFAULT_DDEV), [])
    report: dict[str, Any] = {"probe": "probe_autosave_m1.py", "startedAt": utc_now(),
                              "static": ui.static_facts(DEFAULT_DDEV), "runs": []}
    try:
        for _ in range(args.rounds):
            for kind in args.browsers.split(","):
                run = run_round(kind, server, doc)
                report["runs"].append(run)
                (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
                print(kind, "fatal" if run.get("fatal") else run.get("lost"), run.get("exact"), flush=True)
    finally:
        server.clear_locks()
        report["completedAt"] = utc_now()
        (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
