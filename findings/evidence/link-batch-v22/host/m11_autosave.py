#!/usr/bin/env python3
"""M11-autosave on the host (SPEC-M3-link-batch-v22 §11.5; fable ruling 5 item 20; ARMS-item2.md M11-autosave, DM-18 A).

v21 §11.2 M11: 「記帳：貼上之後 `dirty` 為 true、自動儲存會觸發」.  The autosave half cannot fire on the no-host page
(the page's autosave returns when there is no `liteCoreHost`), so it is a host arm.  A new small runner, an
addition (§34.4 0 / 0); it reuses the host route and instruments the counted runners already drive.

  m11_autosave.py --browser chrome|firefox --rounds 3 --out DIR --expect-version 0.2.27 --expect-build-id ID
  m11_autosave.py --judge REPORT [--expect-version V --expect-build-id ID]
  m11_autosave.py --self-test

One round, in a fresh browser on a fresh copy of item 2's empty template (`empty-template.odt`):
  1. log in, open the copy from Files (check_m3_locks.open_from_files), wait until quiet;
  2. revision r0 and the host's save list (`data-litecore`'s `saves`) before;
  3. the clipboard instrument writes round-1/M2.md (v21_clipboard), a real click on 「貼上為 Markdown…」, a trusted
     Ctrl+V into the text box, the read-back must equal what was written, a real click on 「插入」;
  4. the paste completed = the dialog closed, the session ready with nothing pending, revision r0 + 1;
  5. then NO input: wait up to 45 s (the page's 30 s idle and 15 s) for a new host save with trigger "auto";
  6. the file read back over WebDAV: its paragraphs must hold M2's text.

Reading (written before any run, v22 §12 (d)): ARMS-item2 says "the file's structure contains the pasted heading", but
round-1/M2.md has no heading -- it is one line, `Plain **bold** and *italic* and `inline code` end.` -- so the check is
that line's text, `Plain bold and italic and inline code end.`, as one paragraph of the saved file.

Per round: an error or a paste that did not complete -> NOT_ESTABLISHED; no auto save in the window -> FAIL; the saved
file without M2's text -> FAIL; else PASS.  Verdict: FAIL beats NOT_ESTABLISHED beats PASS; fewer rounds than asked,
or none, is NOT_ESTABLISHED; a host version or buildId other than the expected one is FAIL.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "wasm_sdk_probe" / "tools"
NATIVE = REPO / "findings/evidence/link-batch-v21/native/markdown-paste"
M2_PATH = NATIVE / "tool/corpus/M2.md"
TEMPLATE = NATIVE / "tool/inputs/empty-template.odt"
M2_SAVED = "Plain bold and italic and inline code end."
WINDOW_S = 45.0
PASS, FAIL, NE = "PASS", "FAIL", "NOT_ESTABLISHED"
TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"

DIALOG_OPEN = "(() => !!document.getElementById('markdown-dialog')?.open)()"
CENTER = r"""((sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect();
  return r.width > 0 && r.height > 0 ? [r.x + r.width / 2, r.y + r.height / 2] : null; })"""


def paragraphs(odt: bytes) -> list[str]:
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(odt)).read("content.xml"))
    return ["".join(e.itertext()) for e in root.iter() if e.tag in (TEXT + "p", TEXT + "h")]


def judge_round(rnd: dict) -> tuple[str, str]:
    if rnd.get("error"):
        return NE, f"error: {rnd['error'][:160]}"
    paste = rnd.get("paste") or {}
    if not paste.get("completed"):
        return NE, f"the paste did not complete: {paste}"
    auto = rnd.get("autoSave") or {}
    if not auto.get("found"):
        return FAIL, f"no auto save within {WINDOW_S:.0f} s after the paste (saves {auto.get('savesAfter')})"
    if M2_SAVED not in (rnd.get("savedParagraphs") or []):
        return FAIL, f"the saved file does not hold M2's text: {(rnd.get('savedParagraphs') or [])[:3]}"
    return PASS, f"auto save {auto.get('afterMs')} ms after the paste"


def judge(report: dict, version: str | None, build_id: str | None, rounds: int = 3) -> dict:
    ident = report.get("hostIdentity") or {}
    pinned = [f"host version {ident.get('hostVersion')} != {version}" for _ in [0] if version and ident.get("hostVersion") != version]
    pinned += [f"buildId {ident.get('buildId')} != {build_id}" for _ in [0] if build_id and ident.get("buildId") != build_id]
    lines, verdicts = [], []
    for rnd in report.get("rounds") or []:
        verdict, why = judge_round(rnd)
        verdicts.append(verdict)
        lines.append(f"r{rnd.get('round')} {verdict}: {why}")
    if pinned or FAIL in verdicts:
        verdict = FAIL
    elif NE in verdicts or len(verdicts) < rounds:
        verdict = NE
    else:
        verdict = PASS
    return {"M11-autosave": verdict, "pinned": pinned, "rounds": lines}


def self_test() -> int:
    good_round = {"paste": {"completed": True}, "autoSave": {"found": True, "afterMs": 31000},
                  "savedParagraphs": [M2_SAVED, ""]}
    good = {"hostIdentity": {"hostVersion": "0.2.27", "buildId": "B"},
            "rounds": [dict(copy.deepcopy(good_round), round=k) for k in (1, 2, 3)]}

    def mutated(fn):
        rep = copy.deepcopy(good)
        fn(rep)
        return rep
    cases = [
        ("control", good, PASS),
        ("no auto save in one round", mutated(lambda r: r["rounds"][1]["autoSave"].update(found=False)), FAIL),
        ("the saved file without M2's text", mutated(lambda r: r["rounds"][0].update(savedParagraphs=["", ""])), FAIL),
        ("a paste that did not complete", mutated(lambda r: r["rounds"][2]["paste"].update(completed=False)), NE),
        ("a round with an error", mutated(lambda r: r["rounds"][2].update(error="TimeoutError: x")), NE),
        ("zero rounds", mutated(lambda r: r.update(rounds=[])), NE),
        ("two rounds of three", mutated(lambda r: r["rounds"].pop()), NE),
        ("the wrong host version", mutated(lambda r: r["hostIdentity"].update(hostVersion="0.2.26")), FAIL),
    ]
    bad = 0
    for label, report, expect in cases:
        got = judge(report, "0.2.27", "B")["M11-autosave"]
        bad += got != expect
        print(f"{'ok  ' if got == expect else 'BAD '} {label}: expected {expect}, got {got}")
    print(f"self-test: {len(cases) - bad}/{len(cases)} as required")
    return 0 if bad == 0 else 1


def run(args) -> int:
    sys.path.insert(0, str(TOOLS))
    import check_m3_locks as locks  # noqa: E402
    import check_m3_production_ui as ui  # noqa: E402
    import probe_paste_latency as ppl  # noqa: E402
    import run_e2_c_product_path as pp  # noqa: E402
    import run_v21_d2 as d2  # noqa: E402
    import v21_clipboard as clip  # noqa: E402
    import v21_shakedown_common as common  # noqa: E402
    from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
    probe = d2.load_probe()                     # probe_10_14n: real_click

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    m2 = M2_PATH.read_text(encoding="utf-8")
    template = TEMPLATE.read_bytes()
    report = {"tool": "m11_autosave.py", "toolSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "browser": args.browser, "hostIdentity": d2.host_identity(DEFAULT_DDEV), "startedAt": common.now_iso(),
              "m2Sha256": hashlib.sha256(m2.encode("utf-8")).hexdigest(),
              "templateSha256": hashlib.sha256(template).hexdigest(), "rounds": []}
    path = out / f"m11-autosave-{args.browser}-{stamp}.json"
    instance = Instance(DEFAULT_DDEV)

    def ev(session, script):
        return pp.evaluate(session, script)

    def click(session, selector):
        center = ev(session, f"{CENTER}({json.dumps(selector)})")
        if not center:
            raise RuntimeError(f"nothing visible to click at {selector}")
        probe.real_click(session, args.browser, *center)

    with common.browser_lock(f"m11-autosave {args.browser}", wait_s=args.wait_lock) as holder:
        report["lock"] = holder
        for k in range(1, args.rounds + 1):
            rnd = {"round": k}
            report["rounds"].append(rnd)
            folder, name = f"m11-autosave-{args.browser}-{stamp}-r{k}", "m11.odt"
            session = None
            try:
                rnd["mkcol"] = instance.dav("MKCOL", folder)[0]
                instance.dav("PUT", f"{folder}/{name}", template, {"Content-Type": "application/vnd.oasis.opendocument.text"})
                session = ppl.new_session(args.browser, out / f".scratch-{args.browser}-{stamp}")
                rnd["version"] = getattr(session, "version", None)
                rnd["login"] = locks.login(session, instance.base, "admin", instance.password)
                locks.open_from_files(session, instance.base, folder, name, rnd)
                rnd["opened"] = ui.quiet(session, 180)
                r0 = int(str(ui.state(session).get("revision") or 0))
                saves0 = len((ev(session, ui.HOST) or {}).get("saves") or [])
                origin = ev(session, "(() => location.origin)()")
                rnd["grant"] = clip.grant(session, args.browser, origin)
                rnd["clipboard"] = clip.write_text(session, m2)
                click(session, '#toolbar [data-action="paste-markdown"]')
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and not ev(session, DIALOG_OPEN):
                    time.sleep(0.15)
                rnd["dialogOpened"] = ev(session, DIALOG_OPEN)
                clip.press_ctrl_v(session, args.browser)
                time.sleep(0.8)
                rnd["readback"] = clip.readback(session, "#markdown-text")
                if rnd["readback"].get("sha256") != (rnd["clipboard"] or {}).get("sha256"):
                    raise RuntimeError(f"input-mismatch: the text box holds {rnd['readback']}")
                click(session, "#markdown-insert")
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline and ev(session, DIALOG_OPEN):
                    time.sleep(0.15)
                settled = ui.until(session, lambda s: s.get("state") == "ready" and str(s.get("pending")) == "0"
                                   and int(str(s.get("revision") or 0)) == r0 + 1, 30)
                t_paste = time.monotonic()
                rnd["paste"] = {"completed": bool(settled) and not ev(session, DIALOG_OPEN),
                                "r0": r0, "state": settled or ui.state(session)}
                found = None
                while rnd["paste"]["completed"] and time.monotonic() - t_paste < WINDOW_S and found is None:
                    saves = (ev(session, ui.HOST) or {}).get("saves") or []
                    new = [s for s in saves[saves0:] if s.get("trigger") == "auto"
                           and s.get("outcome", "saved") == "saved" and s.get("settled", True) is not False]
                    if new:
                        found = {"found": True, "afterMs": round((time.monotonic() - t_paste) * 1000), "save": new[0]}
                    time.sleep(0.5)
                saves = (ev(session, ui.HOST) or {}).get("saves") or []
                rnd["autoSave"] = found or {"found": False, "savesAfter": saves[saves0:]}
                if found:
                    status, body = instance.dav("GET", f"{folder}/{name}")
                    rnd["savedStatus"] = status
                    rnd["savedSha256"] = hashlib.sha256(body).hexdigest()
                    rnd["savedParagraphs"] = paragraphs(body)
            except Exception as error:  # noqa: BLE001 -- recorded; the judge reads it as NOT_ESTABLISHED
                rnd["error"] = f"{type(error).__name__}: {error}"[:600]
            finally:
                if session is not None:
                    rnd["close"] = common.close_browser(session)
                try:
                    rnd["deletedFolder"] = instance.dav("DELETE", folder)[0]
                except Exception as error:  # noqa: BLE001
                    rnd["deletedFolder"] = f"{type(error).__name__}: {error}"[:200]
                path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    report["completedAt"] = common.now_iso()
    report["verdict"] = judge(report, args.expect_version, args.expect_build_id, args.rounds)
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    print(json.dumps(report["verdict"], ensure_ascii=False, indent=1))
    print(path)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", choices=("chrome", "firefox"))
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--out")
    ap.add_argument("--wait-lock", type=float, default=0.0)
    ap.add_argument("--expect-version")
    ap.add_argument("--expect-build-id")
    ap.add_argument("--judge", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.judge:
        verdict = judge(json.loads(args.judge.read_text(encoding="utf-8")), args.expect_version, args.expect_build_id)
        print(json.dumps(verdict, ensure_ascii=False, indent=1))
        return 0 if verdict["M11-autosave"] == PASS else 1
    if not (args.browser and args.out and args.expect_version and args.expect_build_id):
        raise SystemExit("a run needs --browser, --out, --expect-version and --expect-build-id")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
