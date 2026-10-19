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
  run_v21_d2.py --browser chrome --mode host --page 0224       the 0.2.24 red case ON THE HOST (before 0.2.25)
  run_v21_d2.py --browser chrome --mode host --page v21        criterion D2 as pinned: host 0.2.25, after v74
  run_v21_d2.py --mode host --page v21 --identity-only         the host identity check alone (reads files, no ddev)
  run_v21_d2.py --self-test                                    D2's verdict red cases and the host identity's

The host arm (added 2026-10-17, after the v74 freeze; ARMS-item1.md D2 "Steps" and "Identity"): the probe's own
host route (login, Files -> open; `probe_10_14n.py` `run_arm`'s host branch, re-composed here because that function
closes the browser before a save), the same arm, then a REAL Ctrl+S (the page binds accel+S,
`web/e2-editor-app.js` "FINDING 106") settled through the host's `data-litecore` save log (`outcome == "saved"`),
then a WebDAV GET of the file and the paragraph-text comparison; the positive control types `Z` and saves again.
Each round opens its own copy (`d2-long60-r<N>.odt`) in a folder this tool creates and deletes, so no round meets
another's lock or ETag.  A host save that did not land leaves the server's bytes as uploaded; that case is caught
by `serverChanged` and never reads as "text unchanged".

Before any browser starts, the host's identity is read from the host checkout's files (`engine/MANIFEST.json`,
`appinfo/info.xml`; no ddev command) and checked against `HOST_EXPECT[page]`: the host version, the page and the
engine the host packages, and the shell digest over the frozen bundle's paths as the host packages them (the same
digest S-1 binds, `run_merge_wasm_shakedown.shell_digest`, computed from the package manifest's hashes).  A
mismatch refuses the run.
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
import run_merge_wasm_shakedown as mws  # noqa: E402
import v21_engine_read as er  # noqa: E402
import v21_input as inp  # noqa: E402
import v21_item1_marker as marker  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402

P14N_PATH = common.REPO / "findings/evidence/host-0.2.20-hand-test/probe_10_14n.py"
PASS, FAIL, NE = "PASS", "FAIL", "NOT_ESTABLISHED"
NAME = "probe-10-14n-long60.odt"

# What the host must package for each host run (full hashes; the v21 values are the evidence runs' identity,
# README §5.2; the 0.2.24 values are the installed host's, the same as the dist0224 reports').
HOST_EXPECT = {
    "v21": {"hostVersion": "0.2.26",
            "servedPage": "605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f",
            "hostShellDigest": common.EXPECTED_SHELL_DIGEST,
            "hostWasm": "db3408f55316bf67345258ce9f7cb58a1cb3777c9aabb9f7790bee69e1599f30"},
    # v22 (SPEC-M3-link-batch-v22 §11.4 D2-v22; §13.1 step 8): host 0.2.27, engine v22 with shell generation v75.
    "v22": {"hostVersion": "0.2.27",
            "servedPage": "3b96cb1661aba6de6add989c98c80ab393cd394307763bc6dc28c9440fba82e2",
            "hostShellDigest": common.EXPECTED_SHELL_DIGEST,
            "hostWasm": "f7a40bcce073d913e562245b96f32a1051766dda23da0da3911741f03934d49e"},
    "0224": {"hostVersion": "0.2.24",
             "servedPage": "901dd6a6dbff6ad6f5252814fb4dc09230446a11d75387fb447e8a6a398a68c2",
             "hostShellDigest": "e7c4eefea59803599ce074dac97783f2c334a4a2a8d4571088a27bea9820f152",
             "hostWasm": "313b08d5cb08589783a3e4d4d03eaee02d26f705ff5da96396ce9010680c5264"},
}
SAVE_LIMIT_S = 90


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
    # The probe summarises only from the Backspace on (probe_10_14n.py:397, :400), so Ctrl+Home's move is
    # read from the probe's whole instrument log (§34.4 witness: smoke/witness-item1/).
    full = record.get("fullLog") or []
    move = next((e for e in full if e.get("k") == "rs" and str(e.get("action") or "").startswith("move-document-")), None)
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
                record["fullLog"] = [e for e in probe.log_from(session, 0) if e.get("k") in ("rq", "rs", "kd")]
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


def host_identity(root: Path) -> dict:
    """What the host packages, read from its checkout's files only (no ddev command)."""
    manifest = json.loads((root / "engine" / "MANIFEST.json").read_text(encoding="utf-8"))
    files = manifest.get("files") or {}
    info = (root / "appinfo" / "info.xml").read_text(encoding="utf-8")
    version = info.split("<version>", 1)[1].split("</version>", 1)[0] if "<version>" in info else None
    bundle = json.loads(pp.SHELL_BUNDLE_V2.read_text(encoding="utf-8"))
    paths = [e["path"] for e in bundle["included"] if e["path"] != bundle.get("entrypoint")]
    missing = [p for p in paths if pp.served_in_dist(p) not in files]
    wasms = {k: (v or {}).get("sha256") for k, v in files.items() if k.endswith("/probe.wasm")}
    return {"root": str(root), "hostVersion": version, "buildId": manifest.get("buildId"),
            "profile": (manifest.get("source") or {}).get("profile"),
            "servedPage": (files.get("e2-editor-app.js") or {}).get("sha256"),
            "hostShellDigest": None if missing else mws.digest(
                [f"{p}={files[pp.served_in_dist(p)]['sha256']}" for p in paths]),
            "hostShellPaths": len(paths), "hostShellMissing": missing, "bundleManifest": pp.SHELL_BUNDLE_V2.name,
            "hostWasms": wasms, "hostWasm": next(iter(wasms.values())) if len(wasms) == 1 else None}


def identity_problems(identity: dict, expect: dict) -> list[str]:
    out = [f"{key}: the host packages {str(identity.get(key))[:16]}, the run needs {str(want)[:16]}"
           for key, want in expect.items() if identity.get(key) != want]
    if identity.get("hostShellMissing"):
        out.append(f"shell files missing from the package: {identity['hostShellMissing']}")
    if not identity.get("hostShellPaths"):
        out.append("no shell paths: the frozen bundle manifest names none, so the digest would bind nothing")
    if len(identity.get("hostWasms") or {}) != 1:
        out.append(f"{len(identity.get('hostWasms') or {})} probe.wasm entries in the package")
    return out


def host_save(session, browser: str, probe) -> dict:
    """A real Ctrl+S, settled through the host's own save log (`data-litecore`, `saves[-1].settled`)."""
    before = len((pp.evaluate(session, probe.ui.HOST) or {}).get("saves") or [])
    inp.key(session, browser, "s", ("ctrl",))
    deadline = time.monotonic() + SAVE_LIMIT_S
    while time.monotonic() < deadline:
        saves = (pp.evaluate(session, probe.ui.HOST) or {}).get("saves") or []
        if len(saves) > before and saves[-1].get("settled") is True:
            time.sleep(0.5)
            return {"saves": len(saves), "outcome": saves[-1].get("outcome"), "last": saves[-1]}
        time.sleep(0.3)
    return {"saves": before, "timedOut": True}


def run_host(args, probe) -> dict:
    """Criterion D2 as pinned (`--page v21`, host 0.2.25) or its 0.2.24 red case (`--page 0224`)."""
    if args.page not in HOST_EXPECT:
        raise SystemExit(f"--mode host takes --page {' or '.join(HOST_EXPECT)}")
    identity = host_identity(probe.DEFAULT_DDEV)
    problems = identity_problems(identity, HOST_EXPECT[args.page])
    if args.identity_only:
        print(json.dumps({"page": args.page, "identity": identity, "problems": problems}, indent=1))
        return {"problems": problems}
    if problems:
        raise SystemExit(f"the host is not the one this run needs ({args.page}): {problems}")
    doc = build_long_document(60)
    report = {"tool": "run_v21_d2.py", "mode": "host", "page": args.page, "browser": args.browser, "counted": False,
              "smoke": args.smoke, "doc": {"kind": "long60", "sha256": hashlib.sha256(doc).hexdigest(), "bytes": len(doc)},
              "probeSha256": common.sha256_file(P14N_PATH), "toolSha256": common.sha256_file(Path(__file__)),
              "preRun": common.pre_run_checks(), "hostIdentity": identity, "identityProblems": problems,
              "static": probe.ui.static_facts(probe.DEFAULT_DDEV), "startedAt": common.now_iso(), "rounds": []}
    if report["preRun"]["refuse"]:
        raise SystemExit(f"pre-run checks refuse: {report['preRun']['refuse']}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    path = out / f"d2-host-{args.page}-{args.browser}-{stamp}.json"
    instance = probe.Instance(probe.DEFAULT_DDEV)
    folder = f"v21-d2-host-{args.page}-{args.browser}-{stamp}"
    report["folder"] = folder

    def flush():
        path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))

    with common.browser_lock(f"run_v21_d2 host {args.browser} {args.page}", wait_s=args.wait_lock) as holder:
        report["lock"] = holder
        report["mkcol"] = instance.dav("MKCOL", folder)[0]
        try:
            for index in range(args.rounds):
                name = f"d2-long60-r{index + 1}.odt"
                record = {"round": index + 1, "arm": "press-after-ctrl-home", "name": name, "startedAt": common.now_iso()}
                report["rounds"].append(record)
                session = None
                try:
                    record["upload"] = instance.dav("PUT", f"{folder}/{name}", doc,
                                                    {"Content-Type": "application/vnd.oasis.opendocument.text"})[0]
                    session = probe.ui.new_session(args.browser)
                    record["version"] = getattr(session, "version", None)
                    record["login"] = probe.login(session, instance.base, "admin", instance.password)
                    probe.open_from_files(session, instance.base, folder, name, record)
                    record["opened"] = probe.ui.quiet(session, 180)
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
                    record["fullLog"] = [e for e in probe.log_from(session, 0) if e.get("k") in ("rq", "rs", "kd")]
                    record["save1"] = host_save(session, args.browser, probe)
                    status, raw = instance.dav("GET", f"{folder}/{name}")
                    landed = record["save1"].get("outcome") == "saved" and raw != doc
                    record["compare"] = {"saved": landed, "getStatus": status, "serverChanged": raw != doc,
                                         "savedSha256": hashlib.sha256(raw).hexdigest()}
                    if landed:
                        record["compare"]["savedEqualsOpened"] = texts_of(raw) == texts_of(doc)
                        record["compare"]["firstParagraphs"] = texts_of(raw)[:2]
                    # The positive control.  More than a second after the first write (findings 103/104: two writes in
                    # one second keep the ETag).
                    inp.key(session, args.browser, "Z")
                    time.sleep(1.2)
                    probe.ui.quiet(session, 30)
                    record["save2"] = host_save(session, args.browser, probe)
                    status2, raw2 = instance.dav("GET", f"{folder}/{name}")
                    record["compare"]["controlGetStatus"] = status2
                    record["compare"]["controlDiffers"] = (record["save2"].get("outcome") == "saved"
                                                           and texts_of(raw2) != texts_of(doc))
                    record["verdict"] = judge_d2(record, red=args.page == "0224")
                except Exception:  # noqa: BLE001
                    record["fatal"] = traceback.format_exc()[-2000:]
                finally:
                    if session is not None:
                        record["close"] = common.close_browser(session)
                    record["completedAt"] = common.now_iso()
                    flush()
        finally:
            if not args.keep_folder:
                report["deletedFolder"] = instance.dav("DELETE", folder)[0]
            report["completedAt"] = common.now_iso()
            flush()
    print(json.dumps({"report": str(path), "verdicts": [r.get("verdict") for r in report["rounds"]]}, ensure_ascii=False))
    return report


def self_test() -> int:
    good = {"summary": {"editorResponses": [
        {"action": "delete-backward", "completion": "verified-boundary-noop", "changed": False, "rev": 0, "beforeRev": 0}]},
        "fullLog": [{"k": "rs", "action": "move-document-start", "completion": "documented-callback-visible-cursor"}],
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
                  judge_d2(mutate(good, ["summary", "editorResponses", 0, "completion"], "verified-selection-delete"))[0] == FAIL))
    cases.append(("revision advanced -> FAIL", judge_d2(mutate(good, ["summary", "editorResponses", 0, "rev"], 1))[0] == FAIL))
    cases.append(("saved text differs -> FAIL", judge_d2(mutate(good, ["compare", "savedEqualsOpened"], False))[0] == FAIL))
    cases.append(("no Backspace response -> NE", judge_d2(mutate(good, ["summary", "editorResponses"], []))[0] == NE))
    cases.append(("no move-document-start on v21 -> FAIL", judge_d2(mutate(good, ["fullLog"], []))[0] == FAIL))
    cases.append(("the move only in the Backspace summary (the witness's shape) is not enough -> FAIL",
                  judge_d2(mutate(mutate(good, ["fullLog"], []), ["summary", "editorResponses"],
                                  [{"action": "move-document-start"}] + good["summary"]["editorResponses"]))[0] == FAIL))
    cases.append(("positive control not different -> NE", judge_d2(mutate(good, ["compare", "controlDiffers"], False))[0] == NE))
    cases.append(("0.2.24 red present -> red", judge_d2(red_good, red=True)[0] == FAIL))
    cases.append(("0.2.24 not red -> NE", judge_d2(good, red=True)[0] == NE))
    cases.append(("zero rounds (no record) -> NE", judge_d2({})[0] == NE))
    # The host identity (refuses the run when not empty).
    want = HOST_EXPECT["v21"]
    ident = {**want, "hostShellPaths": 12, "hostShellMissing": [], "hostWasms": {"profiles/x/probe.wasm": want["hostWasm"]}}
    cases.append(("host identity as expected -> no problem", identity_problems(ident, want) == []))
    cases.append(("host 0.2.24 where 0.2.25 is needed -> refused", bool(identity_problems({**ident, "hostVersion": "0.2.24"}, want))))
    cases.append(("another page packaged -> refused", bool(identity_problems({**ident, "servedPage": "901dd6a6"}, want))))
    cases.append(("another shell packaged -> refused", bool(identity_problems({**ident, "hostShellDigest": "e7c4eefe"}, want))))
    cases.append(("a shell file missing from the package -> refused",
                  bool(identity_problems({**ident, "hostShellDigest": None, "hostShellMissing": ["sdk/document-sdk.js"]}, want))))
    cases.append(("another engine packaged -> refused", bool(identity_problems({**ident, "hostWasm": "313b08d5"}, want))))
    cases.append(("two engines packaged -> refused",
                  bool(identity_problems({**ident, "hostWasms": {"a/probe.wasm": want["hostWasm"], "b/probe.wasm": "x"}}, want))))
    cases.append(("an empty bundle manifest -> refused", bool(identity_problems({**ident, "hostShellPaths": 0}, want))))
    for name, ok in cases:
        print(f"{'ok ' if ok else 'NOT'}  {name}")
    bad = [n for n, ok in cases if not ok]
    print(f"self-test: {len(cases) - len(bad)}/{len(cases)}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"))
    ap.add_argument("--mode", choices=("nohost", "host"), default="nohost")
    ap.add_argument("--page", choices=("v21", "v22", "dist0224", "0224"), default="v21",
                    help="nohost: v21 or dist0224; host: v21 (0.2.26), v22 (0.2.27) or 0224 (the red case on host 0.2.24)")
    ap.add_argument("--identity-only", action="store_true", help="host: check the host identity and stop")
    ap.add_argument("--keep-folder", action="store_true", help="host: keep the uploaded folder")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--out", default="")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--wait-lock", type=float, default=0.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    probe = load_probe()
    if args.mode == "host" and args.identity_only:
        return 1 if run_host(args, probe)["problems"] else 0
    if not args.browser or not args.out:
        ap.error("--browser and --out are required")
    if args.mode == "host":
        run_host(args, probe)
        return 0
    if args.page not in ("v21", "dist0224"):
        ap.error("--mode nohost takes --page v21 or dist0224")
    run_nohost(args, probe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
