#!/usr/bin/env python3
"""Re-judge the merge runner's committed reports under the re-expectation of task 2026-10-14i.

No browser.  Every record's clauses are recomputed from the recorded fields and the kept documents with the
runner's own clause functions (`tools/run_merge_wasm_shakedown.py`: `merge_clauses`, `refusal_clauses`,
`noop_clauses`, `limit_clauses`), twice: under the expectation the report was recorded with (the refusal for
`nothing-selected`), which must REPRODUCE the recorded `clauses` and `pass` of every record -- that is what makes
the second judgement comparable -- and under the expectation the profile's own bytes declare (`expectation(...,
boundary_noop)`), which is what the edited runner would record.

The keying is read as the runner reads it: `dist/profiles/<profile>/probe.wasm` of the profile the report names,
and that file's sha256 must equal the report's `bound.wasmSha256`, or this script STOPS -- the declaration must
come from the bytes that ran, not from a file of the same name.

What the old refusal path recorded for a no-op is mapped onto what the no-op path records, explicitly:
  - `toasts`      <- `toastWindow.toasts` (both are `READ_TOASTS` after `CLEAR_TOASTS` at the key; the window
                     polled it for 90 s, the no-op path reads it once after the session is quiet -- a longer
                     observation of the same thing, so a `[]` there is a `[]` here);
  - the document  <- `<stem>.docs/<case>-r<n>-reopened.odt` (saved after the key; under the no-op path the same
                     save is kept as `-after-key.odt`), its content hash checked against `reopenedDocument.sha`;
  - `caretAfterKey` is absent: the clause `caretUnchanged` reads None (not established), as `noop_clauses` says.

Red cases (AGENTS.md 6), each printed and written beside the main output:
  R1  the v19 counted reports under the keying: v19's wasm does not declare C, every record reproduces;
  R2  the v19 C29/C30 records judged under C's expectation anyway: all red;
  R3  the v20 C29/C30 records judged under the refusal anyway (what runner 73b2e9ff did): all red, as recorded;
  R4  `--self-red`: the v20 shakedown report keyed on v19's wasm -> STOP (sha256 mismatch), nothing judged.

  rejudge.py [--merge-dir DIR] [--v19-dir DIR] [--profiles DIR] [--out-dir DIR] [--self-red]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]        # findings/evidence/link-batch/v20-shakedown/merge/re-expectation/
sys.path.insert(0, str(ROOT / "wasm_sdk_probe" / "tools"))
import run_merge_wasm_shakedown as m  # noqa: E402

MERGE_DIR = ROOT / "findings/evidence/link-batch/v20-shakedown/merge"
V19_DIR = ROOT / "findings/evidence/v19/x7-counted-m2"
PROFILES = ROOT / "wasm_sdk_probe/dist/profiles"
V20_REPORTS = ("shakedown-chrome", "shakedown-firefox", "control-chrome", "control-firefox",
               "m2-1b-chrome", "m2-1b-firefox", "m2-4-chrome", "m2-4-firefox")
V19_REPORTS = ("counted-chrome", "counted-firefox", "counted-control-chrome", "counted-control-firefox")
EXPECTED_RECORDS = {"shakedown": 56, "control": 56, "m2-1b": 20, "m2-4": 1, "counted": 78, "counted-control": 78}
NOOP_CASES = ("C29", "C30")


def keying(report: dict, profiles: Path, profile: str | None = None) -> dict:
    profile = profile or report["candidate"]["profile"]
    wasm = profiles / profile / "probe.wasm"
    if not wasm.is_file():
        raise SystemExit(f"STOP: {wasm} is not served; the declaration cannot be read")
    sha = hashlib.sha256(wasm.read_bytes()).hexdigest()
    if sha != report["bound"]["wasmSha256"]:
        raise SystemExit(f"STOP: {wasm} is {sha[:16]}, the report ran {report['bound']['wasmSha256'][:16]}; "
                         "the declaration must be read from the bytes that ran")
    return {"profile": profile, "wasm": wasm.relative_to(ROOT).as_posix(), "wasmSha256": sha,
            "declared": m.boundary_noop_declared(wasm),
            "nothingSelectedExpects": m.expectation("nothing-selected", m.boundary_noop_declared(wasm))[1][0]}


def kept(report_path: Path, record: dict, kind: str) -> list | None:
    path = report_path.parent / f"{report_path.stem}.docs" / f"{record['case']}-r{record['round']}-{kind}.odt"
    if not path.is_file():
        return None
    parts = m.odt_parts(path.read_bytes())
    recorded = (record.get("reopenedDocument") or record.get("afterKeyDocument") or {}).get("sha")
    if recorded is not None and recorded != parts["sha"]:
        raise SystemExit(f"STOP: {path} is {parts['sha']}, the record says {recorded}")
    return parts["paragraphs"]


def judge_record(record: dict, cases: dict, report_path: Path, control: bool) -> tuple[dict, bool, str]:
    """The runner's judgement of one record from its recorded fields; returns (clauses, pass, path taken)."""
    if record.get("criterion") == "M2-4":
        clauses, path = m.limit_clauses(record), "limit"
    else:
        spec = cases[record["case"]]
        expected = spec["expected"]
        marker_at = m.native_cases(spec["fixture"])[record["markerAt"]] if record.get("markerAt") else None
        expected_text = m.original_plus_marker(spec, marker_at)
        if expected[0] == m.BOUNDARY_NOOP:
            adapted = dict(record)
            if "toasts" not in adapted and "toastWindow" in adapted:
                adapted["toasts"] = adapted["toastWindow"].get("toasts")
            mine = kept(report_path, record, "reopened" if "reopenedDocument" in record else "after-key")
            clauses, path = m.noop_clauses(adapted, spec, expected_text, mine), "noop"
        elif expected[0] == "refused" or "toastWindow" in record:
            mine = kept(report_path, record, "reopened")
            clauses = m.refusal_clauses(record, spec, expected_text if marker_at else None, mine)
            if expected[0] != "refused":
                clauses["outcome"] = False
            path = "refusal"
        else:
            clauses, path = m.merge_clauses(record, spec), "merge"
    if control:
        clauses.update({k: None for k in m.INSTRUMENT_ONLY if k in clauses})
    return clauses, all(v for v in clauses.values() if v is not None), path


def rejudge_report(report_path: Path, profiles: Path, force: bool | None = None) -> dict:
    report = json.loads(report_path.read_text())
    key = keying(report, profiles)
    declared = key["declared"] if force is None else force
    frame = bool(report.get("frameCell"))
    old_cases = m.tool_cases(frame_cell=frame, boundary_noop=False)
    new_cases = m.tool_cases(frame_cell=frame, boundary_noop=declared)
    control = bool(report.get("control"))
    records = report["cases"]
    mode = report["mode"] if not (report["mode"] == "counted" and control) else "counted-control"
    if len(records) != EXPECTED_RECORDS[mode]:
        raise SystemExit(f"STOP: {report_path.name} has {len(records)} records, expected {EXPECTED_RECORDS[mode]}")
    out = {"report": report_path.name, "mode": report["mode"], "control": control, "browser": report["browser"],
           "runner": report["runner"], "keying": key, "declaredUsed": declared, "records": len(records),
           "reproduced": 0, "notReproduced": [], "verdictChanged": [], "verdictUnchanged": 0,
           "clausesChanged": [], "noopRecords": []}
    for record in records:
        if "clauses" not in record:
            raise SystemExit(f"STOP: {report_path.name} {record['case']} r{record['round']} has no clauses")
        old, old_pass, _ = judge_record(record, old_cases, report_path, control)
        new, new_pass, path = judge_record(record, new_cases, report_path, control)
        tag = f"{record['case']} r{record['round']}"
        if old == record["clauses"] and old_pass == record["pass"]:
            out["reproduced"] += 1
        else:
            out["notReproduced"].append({"record": tag, "recorded": record["clauses"], "recomputed": old})
        if new_pass != record["pass"]:
            out["verdictChanged"].append(tag)
        else:
            out["verdictUnchanged"] += 1
        if new != old:
            out["clausesChanged"].append(tag)
        if record["case"] in NOOP_CASES and path == "noop":
            out["noopRecords"].append({"record": tag, "recordedPass": record["pass"], "recordedFalse":
                                       sorted(k for k, v in record["clauses"].items() if v is False),
                                       "newClauses": new, "newPass": new_pass,
                                       "notEstablished": sorted(k for k, v in new.items() if v is None)})
    return out


def lines_of(result: dict) -> list[str]:
    key = result["keying"]
    lines = [f"{result['report']}: runner {result['runner']}, profile {key['profile']}, wasm {key['wasmSha256'][:16]} "
             f"({key['wasm']}), declares C: {key['declared']}, nothing-selected expects {key['nothingSelectedExpects']}"
             + ("" if result["declaredUsed"] == key["declared"] else f"  [FORCED declared={result['declaredUsed']}]"),
             f"  records {result['records']}: reproduced under the recorded expectation {result['reproduced']}, "
             f"not reproduced {len(result['notReproduced'])}; verdict changed {len(result['verdictChanged'])} "
             f"{result['verdictChanged']}, unchanged {result['verdictUnchanged']}; clauses changed "
             f"{len(result['clausesChanged'])} {result['clausesChanged']}"]
    for item in result["notReproduced"]:
        lines.append(f"  NOT REPRODUCED {item['record']}: recorded {item['recorded']} recomputed {item['recomputed']}")
    for item in result["noopRecords"]:
        lines.append(f"  {item['record']}: recorded pass {item['recordedPass']} (false: {item['recordedFalse']}) -> "
                     f"pass {item['newPass']}, clauses {json.dumps(item['newClauses'])}, "
                     f"not established {item['notEstablished']}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge-dir", type=Path, default=MERGE_DIR)
    ap.add_argument("--v19-dir", type=Path, default=V19_DIR)
    ap.add_argument("--profiles", type=Path, default=PROFILES)
    ap.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--self-red", action="store_true", help="R4: key the v20 shakedown on v19's wasm; must STOP")
    args = ap.parse_args()
    if args.self_red:
        report = json.loads((args.merge_dir / "shakedown-chrome.json").read_text())
        try:
            keying(report, args.profiles, profile="e2-editor-v19")
        except SystemExit as stop:
            print(f"R4 self-red: {stop}")
            return 2
        print("R4 self-red: the keying accepted another profile's wasm -- the check is broken")
        return 1
    lines, results = [], {"v20": [], "r1_v19": [], "r2_v19_under_c": [], "r3_v20_under_refusal": []}
    lines.append("## v20 part-B reports under the keying (the declaration read from the served wasm)")
    for name in V20_REPORTS:
        result = rejudge_report(args.merge_dir / f"{name}.json", args.profiles)
        results["v20"].append(result)
        lines += lines_of(result)
    lines.append("")
    lines.append("## R1: v19 counted reports under the keying (v19's wasm does not declare C)")
    for name in V19_REPORTS:
        result = rejudge_report(args.v19_dir / f"{name}.json", args.profiles)
        results["r1_v19"].append(result)
        lines += lines_of(result)
    lines.append("")
    lines.append("## R2: v19 C29/C30 records judged under C's expectation anyway (must all be red)")
    for name in V19_REPORTS[:2]:
        result = rejudge_report(args.v19_dir / f"{name}.json", args.profiles, force=True)
        results["r2_v19_under_c"].append(result)
        lines += lines_of(result)
    lines.append("")
    lines.append("## R3: v20 C29/C30 records judged under the refusal anyway (what runner 73b2e9ff recorded; red)")
    for name in V20_REPORTS[:2]:
        result = rejudge_report(args.merge_dir / f"{name}.json", args.profiles, force=False)
        results["r3_v20_under_refusal"].append(result)
        lines += lines_of(result)
    # The claims, each checked here so the exit code carries them.
    failures = []
    for result in results["v20"] + results["r1_v19"] + results["r2_v19_under_c"] + results["r3_v20_under_refusal"]:
        if result["notReproduced"]:
            failures.append(f"{result['report']}: {len(result['notReproduced'])} records not reproduced")
    for result in results["v20"]:
        noop = result["noopRecords"]
        if result["mode"] in ("shakedown",) and result["keying"]["declared"]:
            if len(noop) != 4 or any(not r["newPass"] for r in noop) or sorted(result["verdictChanged"]) != sorted(
                    r["record"] for r in noop):
                failures.append(f"{result['report']}: expected exactly the 4 C29/C30 records to turn green")
        elif result["verdictChanged"]:
            failures.append(f"{result['report']}: verdicts changed in a report with no nothing-selected case")
        if not result["keying"]["declared"]:
            failures.append(f"{result['report']}: v20's wasm must declare C")
    for result in results["r1_v19"]:
        if result["keying"]["declared"] or result["verdictChanged"] or result["clausesChanged"]:
            failures.append(f"{result['report']}: v19 must not declare C and nothing may change")
    for result in results["r2_v19_under_c"]:
        if len(result["noopRecords"]) != 6 or any(r["newPass"] for r in result["noopRecords"]):
            failures.append(f"{result['report']}: v19's refusals must be red under C")
    for result in results["r3_v20_under_refusal"]:
        if result["verdictChanged"] or result["clausesChanged"]:
            failures.append(f"{result['report']}: under the refusal the recorded reds must come back unchanged")
    lines.append("")
    lines.append("RESULT " + ("PASS: every claim holds" if not failures else "FAIL: " + "; ".join(failures)))
    text = "\n".join(lines) + "\n"
    print(text, end="")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "rejudge-output.txt").write_text(text, encoding="utf-8")
    (args.out_dir / "rejudge.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
