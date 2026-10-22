#!/usr/bin/env python3
"""DIAGNOSTIC: read what the viewer's engine says the text of every sheet of the given .ods files
is, through the Phase E harness (the product's OdsViewerSession and OdsViewerEngine on
`ods-viewer-v1`, on a mirror), with the text itself recorded.  No judge, no criterion: the
report is for reading, e.g. finding 159's one-formula-per-cause probe file.

  probe_ods_viewer_sheet_text.py --out DIR FILE.ods [FILE.ods ...]

Preconditions as run_ods_viewer_phase_e.py (recorded, not refused).  The files are staged into
the mirror under ods-e-cases/, so they need not live in the corpus and E1 is not involved.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))
from run_ods_viewer_draft_smoke import PAGE_FILES, preconditions             # noqa: E402
from run_ods_viewer_phase_e import HARNESS, NS, PROFILE, sha256_bytes, utc_now  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    gate = preconditions()
    profile_manifest = PROJECT / "dist" / "profiles" / PROFILE / "sdk-manifest.json"
    if not profile_manifest.is_file():
        raise SystemExit(f"{profile_manifest} does not exist: the viewer is not linked")

    from r7_support import evaluate, wait_page                      # noqa: E402
    from run_browser_probe import ChromeSession, free_port          # noqa: E402
    from run_e2_c_page_smoke import navigate                        # noqa: E402
    from run_e2_c_product_path import build_mirror                  # noqa: E402

    overrides = {path: source.read_bytes() for path, source in PAGE_FILES.items() if path.startswith("viewer-shell/")}
    overrides.update({path: source.read_bytes() for path, source in HARNESS.items()})
    specs, staged = [], []
    for index, file in enumerate(args.files):
        payload = file.read_bytes()
        rel = f"ods-e-cases/{index:03d}/{file.name}"
        overrides[rel] = payload
        specs.append({"name": file.name, "file": "./" + rel, "kind": "corpus"})
        staged.append({"path": str(file), "sha256": sha256_bytes(payload), "bytes": len(payload)})
    overrides["ods-e-cases.json"] = json.dumps(specs, ensure_ascii=False).encode("utf-8")

    scratch = Path(tempfile.mkdtemp(prefix="ods-text-probe-"))
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root, overrides)
    for relative, payload in overrides.items():
        target = root / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    report = {"schemaVersion": 1, "release": "m4-ods-sheet-text-probe", "evidenceClass": "diagnostic",
              "startedAt": utc_now(), "profile": PROFILE, "preconditions": gate,
              "probeWasmSha256": sha256_bytes((profile_manifest.parent / "probe.wasm").read_bytes()),
              "workerSha256": sha256_bytes((profile_manifest.parent / "sdk-worker.js").read_bytes()),
              "pageFiles": {p: sha256_bytes(b) for p, b in overrides.items() if not p.startswith("ods-e-cases")},
              "staged": staged, "cases": []}
    session = server = None
    try:
        port = free_port()
        server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
                                   "--root", str(root)], cwd=PROJECT,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_page(f"http://127.0.0.1:{port}/ods-viewer-e-harness.html")
        session = ChromeSession("cold")
        report["chrome"] = session.version
        navigate(session, f"http://127.0.0.1:{port}/ods-viewer-e-harness.html?openTimeoutMs=180000&recordText=1")
        deadline = time.monotonic() + args.timeout
        head = {}
        while time.monotonic() < deadline:
            head = evaluate(session, f"(() => {{ const r = window.{NS}; return r ? "
                                     f"{{ done: r.done, seen: r.cases.length, fatal: r.fatal }} : null; }})()") or {}
            if head.get("done"):
                break
            time.sleep(1)
        report["timedOut"] = not head.get("done")
        report["pageFatal"] = head.get("fatal")
        for index in range(int(head.get("seen") or 0)):
            text = evaluate(session, f"JSON.stringify(window.{NS}.cases[{index}])")
            report["cases"].append(json.loads(text) if text else {"fatal": "not retrieved"})
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                pass
        if server is not None:
            server.terminate()
        shutil.rmtree(scratch, ignore_errors=True)
    report["completedAt"] = utc_now()
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f"report-{report['startedAt']}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)
    for case in report["cases"]:
        print(f"== {case.get('name')}: opened {bool(case.get('opened'))}, refused {case.get('refused')}, "
              f"error {case.get('error')}")
        for sheet in case.get("sheets") or []:
            t = sheet.get("text") or {}
            print(f"-- part {sheet['part']} ({(case.get('state') or {}).get('partNames', [None] * 99)[sheet['part']]}): "
                  f"{t.get('length')} chars, selectAllConfirmed {t.get('selectAllConfirmed')}, error {sheet.get('error')}")
            if t.get("sample") is not None:
                print(t["sample"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
