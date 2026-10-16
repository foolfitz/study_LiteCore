#!/usr/bin/env python3
"""D2 (`press-after-ctrl-home`) for the v21 shakedown: the no-host predictor, the host run's code path,
the 0.2.24 red case, and D2's verdict with its red cases.

Arms: ARMS-item1.md D2 and §8 D-1 (B: no-host predictor before the freeze; the host run after the freeze
is the criterion), D-16 (A: `long60`, sha256 per run).  The probe is
`findings/evidence/host-0.2.20-hand-test/probe_10_14n.py`, imported by path and NOT edited: its arm
`arm_backspace(..., "ctrl-home")` (real click on the first line, six wheel scrolls of 1,500, real
Ctrl+Home, settle, one real Backspace, settle).  Added here, around it: the save and the comparison of the
saved paragraph texts with the opened document's, and the positive control (type `Z`, save again: the
comparison must then say "differs").

  run_v21_d2.py --browser chrome --mode nohost --page v21      the predictor (page 3d511216, profile v21)
  run_v21_d2.py --browser chrome --mode nohost --page dist0224 the 0.2.24 red case without the host
  run_v21_d2.py --browser chrome --mode host ...               NOT RUN in phase B: needs ddev, host 0.2.25
                                                               (or 0.2.24 for the red case), and the owner's yes
  run_v21_d2.py --self-test                                    D2's verdict red cases
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_e2_c_product_path as pp  # noqa: E402
import v21_engine_read as er  # noqa: E402
import v21_input as inp  # noqa: E402
import v21_item1_marker as marker  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402

P14N_PATH = common.REPO / "findings/evidence/host-0.2.20-hand-test/probe_10_14n.py"
PASS, FAIL, NE = "PASS", "FAIL", "NOT_ESTABLISHED"
NAME = "probe-10-14n-long60.odt"


def load_probe():
    spec = importlib.util.spec_from_file_location("probe_10_14n", P14N_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DOC_KIND["value"] = "long60"
    return module


def texts_of(raw: bytes) -> list[str]:
    return [t for _, _, t in marker.paragraphs_of(raw)]


def responses(record: dict) -> list[dict]:
    return ((record.get("summary") or {}).get("editorResponses") or [])


def judge_d2(record: dict, red: bool = False) -> tuple[str, str]:
    """One round.  `red`: the 0.2.24 run, which must show the old shape."""
    if record.get("fatal") or not record.get("summary"):
        return NE, f"no arm record: {str(record.get('fatal'))[:120]}"
    resp = responses(record)
    backspace = next((r for r in resp if str(r.get("action") or "").startswith("delete")), None)
    move = next((r for r in resp if str(r.get("action") or "").startswith("move-document-")), None)
    if backspace is None:
        return NE, "no Backspace response"
    if red:
        if move is not None:
            return NE, "a move-document request on the 0.2.24 page"
        ok = (backspace.get("completion") == "verified-selection-delete" and backspace.get("changed") is True
              and backspace.get("rev") == (backspace.get("beforeRev") or 0) + 1)
        return (FAIL, "0.2.24 still red: verified-selection-delete, revision +1") if ok else \
            (NE, f"the 0.2.24 red case is not red: {backspace}")
    if move is None:
        return FAIL, "no move-document-start request: the key did not reach the action"
    compare = record.get("compare") or {}
    if compare.get("controlDiffers") is not True:
        return NE, "the positive control's second save was not different: the comparison is blind"
    clauses = {
        "boundaryNoop": backspace.get("completion") == "verified-boundary-noop" and backspace.get("changed") is False,
        "revisionUnchanged": isinstance(backspace.get("rev"), int) and isinstance(backspace.get("beforeRev"), int)
        and backspace["rev"] == backspace["beforeRev"],
        "savedTextUnchanged": compare.get("savedEqualsOpened") is True,
    }
    bad = [k for k, v in clauses.items() if not v]
    return (FAIL, f"clauses not met: {bad}; {backspace}") if bad else (PASS, "")


def run_nohost(args, probe) -> dict:
    doc = build_long_document(60)
    report = {"tool": "run_v21_d2.py", "mode": "nohost", "page": args.page, "browser": args.browser, "counted": False,
              "smoke": args.smoke, "doc": {"name": NAME, "sha256": hashlib.sha256(doc).hexdigest(), "bytes": len(doc)},
              "probeSha256": common.sha256_file(P14N_PATH), "toolSha256": common.sha256_file(Path(__file__)),
              "preRun": common.pre_run_checks(), "startedAt": common.now_iso(), "rounds": []}
    if report["preRun"]["refuse"]:
        raise SystemExit(f"pre-run checks refuse: {report['preRun']['refuse']}")
    scratch = Path(tempfile.mkdtemp(prefix="v21-d2-"))
    kwargs = {}
    if args.page == "dist0224":
        kwargs.update(page_profile="e2-editor-v20", shell_from_tree=False,
                      source_page=(common.DIST / "e2-editor-app.js").read_text(encoding="utf-8"))
    identity = common.build_mirror(scratch / "mirror", extra_files={"fixture.odt": doc}, **kwargs)
    report["identity"] = identity
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"d2-{args.mode}-{args.page}-{args.browser}-{time.strftime('%Y%m%dT%H%M%S')}.json"

    def flush():
        path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))

    with common.browser_lock(f"run_v21_d2 {args.browser} {args.page}", wait_s=args.wait_lock) as holder, \
            common.served(Path(identity["mirror"])) as base:
        report["lock"] = holder
        for index in range(args.rounds):
            record = {"round": index + 1, "arm": "press-after-ctrl-home", "startedAt": common.now_iso()}
            report["rounds"].append(record)
            session = None
            try:
                session = common.open_browser(args.browser, (1850, 980))
                record["version"] = getattr(session, "version", None)
                pp.navigate(session, base)
                pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
                er.install(session)
                pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./fixture.odt").replace("ARG_NAME", NAME))
                record["landed"] = pp.wait_for(session, lambda s: (s.get("doc") or "") == NAME and s.get("state") == "ready", 300)
                record["opened"] = probe.ui.quiet(session, 180)
                opened_bytes = doc
                record["instrument"] = pp.evaluate(session, probe.INSTRUMENT)
                g = pp.evaluate(session, probe.GEOMETRY)
                cx, cy = g["inner"][0] // 2, (g["desk"]["top"] + g["desk"]["bottom"]) // 2
                for _ in range(3):
                    probe.wheel(session, args.browser, cx, cy, 1200)
                    time.sleep(0.25)
                time.sleep(0.6)
                probe.wheel(session, args.browser, cx, cy, -40000)
                time.sleep(0.6)
                record["nudgeSettled"] = probe.settle(session, 1.0, 30)
                probe.arm_backspace(session, args.browser, record, "ctrl-home")
                saved = er.save(session)
                record["compare"] = {"saved": saved is not None}
                if saved is not None:
                    record["compare"]["savedEqualsOpened"] = texts_of(saved) == texts_of(opened_bytes)
                    record["compare"]["savedSha256"] = hashlib.sha256(saved).hexdigest()
                    first = texts_of(saved)[:2]
                    record["compare"]["firstParagraphs"] = first
                inp.key(session, args.browser, "Z")
                time.sleep(1.0)
                probe.ui.quiet(session, 30)
                again = er.save(session)
                record["compare"]["controlDiffers"] = (again is not None and texts_of(again) != texts_of(opened_bytes))
                record["verdict"] = judge_d2(record, red=args.page == "dist0224")
            except Exception:  # noqa: BLE001
                record["fatal"] = traceback.format_exc()[-2000:]
            finally:
                if session is not None:
                    record["close"] = common.close_browser(session)
                record["completedAt"] = common.now_iso()
                flush()
    report["completedAt"] = common.now_iso()
    flush()
    print(json.dumps({"report": str(path), "verdicts": [r.get("verdict") for r in report["rounds"]]}, ensure_ascii=False))
    return report


def run_host(args, probe) -> dict:
    """The host arm (criterion D2 as pinned).  NOT RUN in phase B (ARMS.md §2: host 0.2.25 after the v74
    freeze; the 0.2.24 red case before 0.2.25 is installed; each asked of the owner before ddev is touched).
    The same probe arm; the save is the host's Ctrl+S and the comparison reads the file back over WebDAV."""
    raise SystemExit("the host arm is not run in phase B (ARMS.md §2); it needs ddev and the owner's yes")


def self_test() -> int:
    good = {"summary": {"editorResponses": [
        {"action": "move-document-start", "completion": "documented-callback-visible-cursor"},
        {"action": "delete-backward", "completion": "verified-boundary-noop", "changed": False, "rev": 0, "beforeRev": 0}]},
        "compare": {"savedEqualsOpened": True, "controlDiffers": True}}
    red_good = {"summary": {"editorResponses": [
        {"action": "delete-backward", "completion": "verified-selection-delete", "changed": True, "rev": 1, "beforeRev": 0}]}}
    cases = []

    def mutate(base, path, value):
        import copy
        record = copy.deepcopy(base)
        target = record
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        return record
    cases.append(("green", judge_d2(good)[0] == PASS))
    cases.append(("Backspace answered verified-selection-delete -> FAIL",
                  judge_d2(mutate(good, ["summary", "editorResponses", 1, "completion"], "verified-selection-delete"))[0] == FAIL))
    cases.append(("revision advanced -> FAIL", judge_d2(mutate(good, ["summary", "editorResponses", 1, "rev"], 1))[0] == FAIL))
    cases.append(("saved text differs -> FAIL", judge_d2(mutate(good, ["compare", "savedEqualsOpened"], False))[0] == FAIL))
    cases.append(("no Backspace response -> NE",
                  judge_d2(mutate(good, ["summary", "editorResponses"], good["summary"]["editorResponses"][:1]))[0] == NE))
    cases.append(("no move-document-start on v21 -> FAIL",
                  judge_d2(mutate(good, ["summary", "editorResponses"], good["summary"]["editorResponses"][1:]))[0] == FAIL))
    cases.append(("positive control not different -> NE", judge_d2(mutate(good, ["compare", "controlDiffers"], False))[0] == NE))
    cases.append(("0.2.24 red present -> red", judge_d2(red_good, red=True)[0] == FAIL))
    cases.append(("0.2.24 not red -> NE", judge_d2(good, red=True)[0] == NE))
    cases.append(("zero rounds (no record) -> NE", judge_d2({})[0] == NE))
    for name, ok in cases:
        print(f"{'ok ' if ok else 'NOT'}  {name}")
    bad = [n for n, ok in cases if not ok]
    print(f"self-test: {len(cases) - len(bad)}/{len(cases)}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"))
    ap.add_argument("--mode", choices=("nohost", "host"), default="nohost")
    ap.add_argument("--page", choices=("v21", "dist0224"), default="v21")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--out", default="")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--wait-lock", type=float, default=0.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.browser or not args.out:
        ap.error("--browser and --out are required")
    probe = load_probe()
    if args.mode == "host":
        run_host(args, probe)
        return 1
    run_nohost(args, probe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
