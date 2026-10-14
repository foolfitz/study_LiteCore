#!/usr/bin/env python3
"""A small reader for witness-c-0.2.23.json: the fields the prediction names, read from the raw report.

It does not call the runner's scorer and does not judge; the runner's own score lines are printed separately,
verbatim, from report["score"].  Run: python3 -I read_witness.py [report.json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parents[3] / "wasm_sdk_probe" / "tools" / "check_m3_production_ui.py"


def runner_constant(name: str) -> str:
    text = RUNNER.read_text()
    found = re.search(rf'^{name}\s*=\s*"([0-9a-f]{{64}})"', text, re.M)
    if not found:
        raise SystemExit(f"constant {name} not found in {RUNNER}")
    return found.group(1)


def busy_intervals(timeline: list[dict], at_least_ms: int = 1000) -> list[dict]:
    """Spans where state was busy until the next sample that was ready, longer than at_least_ms."""
    out = []
    for i, s in enumerate(timeline[:-1]):
        if s["state"] != "busy":
            continue
        nxt = next((x for x in timeline[i + 1:] if x["state"] != "busy"), None)
        if nxt and nxt["t"] - s["t"] >= at_least_ms:
            out.append({"from": s["t"], "to": nxt["t"], "ms": nxt["t"] - s["t"], "rev": f"{s['rev']}->{nxt['rev']}",
                        "gen": f"{s['gen']}->{nxt['gen']}", "endState": nxt["state"]})
    return out


def timeline_facts(timeline: list[dict]) -> dict:
    states = sorted({s["state"] for s in timeline})
    return {"samples": len(timeline), "states": states, "outsideReadyBusy": sum(1 for s in timeline if s["state"] not in ("ready", "busy")),
            "generations": sorted({s["gen"] for s in timeline}), "toastTexts": sorted({s["toast"] for s in timeline if s.get("toast")}),
            "revisions": f"{timeline[0]['rev']}..{timeline[-1]['rev']}" if timeline else None,
            "lastSampleAtMs": timeline[-1]["t"] if timeline else None, "busyOver1s": busy_intervals(timeline)}


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "witness-c-0.2.23.json"
    report = json.loads(path.read_text())
    original_seq = runner_constant("ORIGINAL_SEQ")
    print(f"report {path.name}: runner {report.get('runnerSha256', '')[:16]} counted {report.get('counted')} started {report.get('startedAt')} completed {report.get('completedAt')}")
    st = report["static"]
    print(f"static: host {st['hostVersion']} {st['hostCommit']} dirty {st['hostDirty']} buildId {st['buildId']} servedPage {st['servedPage'][:12]} distPage {st['distPage'][:12]} "
          f"servedSession {st['servedSession'][:12]} shell {st['shellBundle'].get('manifest')} exit {st['shellBundle'].get('exit')}")
    print(f"doc: {report['doc']['name']} {report['doc']['bytes']} B sha {report['doc']['sha256'][:16]} marks {report['doc']['marks']}")
    for run in report["runs"]:
        arm, browser = run["arm"], run["browser"]
        print(f"\n=== {arm} / {browser}  (browser version {run.get('version')}, clearedLocks {run.get('clearedLocks')}, fatal {'YES' if run.get('fatal') else 'no'})")
        if run.get("fatal"):
            print("  FATAL:", run["fatal"].strip().splitlines()[-1])
        tl = timeline_facts(run.get("timeline") or [])
        print(f"  generation {run.get('genOpened')} -> {run.get('genAfter')}"
              + (f", after reload {run.get('genReloaded')}" if arm == "B3x" else ""))
        print(f"  timeline: {tl['samples']} samples, states {tl['states']}, outside ready/busy {tl['outsideReadyBusy']}, generations {tl['generations']}, "
              f"revisions {tl['revisions']}, last sample at {tl['lastSampleAtMs']} ms")
        print(f"  toast texts in the timeline: {tl['toastTexts']}")
        print(f"  busy >= 1 s: {tl['busyOver1s']}")
        server = run.get("server") or {}
        if arm != "B3x":
            ak = run.get("afterKey") or {}
            print(f"  afterKey (the state when the reopen wait ended): state {ak.get('state')} pending {ak.get('pending')} revision {ak.get('revision')} latency {ak.get('latency')!r} toast {ak.get('toast')!r}")
            sv = run.get("save") or {}
            print(f"  save: saves {sv.get('saves')} outcome {sv.get('outcome')} timedOut {sv.get('timedOut')}")
            print(f"  server: status {server.get('status')} marks {server.get('marks')} paragraphs {server.get('paragraphs')} "
                  f"seqSha256 {str(server.get('seqSha256'))[:16]} == ORIGINAL_SEQ ({original_seq[:16]}): {server.get('seqSha256') == original_seq} "
                  f"firstDiffFromUploaded {server.get('firstDiffFromUploaded')}")
        else:
            for i, step in enumerate(run.get("refusals") or []):
                after = step.get("after") or {}
                limit = step.get("limit") or {}
                print(f"  press {i + 1} ({step.get('mark')}): generation {step.get('genBefore')} -> {step.get('genAfter')}; state after {after.get('state')!r}; "
                      f"latency {after.get('latency')!r}; data-limit {limit.get('limit')!r}; limitAfter {step.get('limitAfter')}; typed revs "
                      f"{[(t.get('revBefore'), t.get('revAfter')) for t in step.get('typed') or []]}")
            print(f"  unsavedHiddenAfter {run.get('unsavedHiddenAfter')}")
            hb = run.get("hostBefore") or {}
            print(f"  host saves before the reload step: {[(s.get('trigger'), s.get('at'), s.get('outcome'), s.get('sha256', '')[:12]) for s in hb.get('saves') or []]}")
            print(f"  server: status {server.get('status')} marks3 {server.get('marks3')} marks {server.get('marks')} seqSha256 {str(server.get('seqSha256'))[:16]} "
                  f"== ORIGINAL_SEQ: {server.get('seqSha256') == original_seq}; serverBefore marks3 {(run.get('serverBefore') or {}).get('marks3')}")
            reload = run.get("reload") or {}
            print(f"  notice button step: dialog {reload.get('dialog')} path {reload.get('path')} evaluateError {reload.get('evaluateError')} "
                  f"record {[e.get('what') for e in reload.get('record') or []]}")
            rl = run.get("reloaded") or {}
            print(f"  after that step: state {rl.get('state')} revision {rl.get('revision')} latency {rl.get('latency')!r} toast {rl.get('toast')!r}")
            fetched = ((run.get("hostAfter") or {}).get("fetched") or {}).get("sha256")
            print(f"  hostAfter: lock {((run.get('hostAfter') or {}).get('lock') or {}).get('state')} fetched sha {str(fetched)[:12]} == server sha {server.get('sha256', '')[:12]}: {fetched == server.get('sha256')}")
    print("\nRunner's own score lines, verbatim (report['score']['cells'][*]['failures']):")
    for cell, v in report["score"]["cells"].items():
        print(f"  {cell}: pass {v['pass']}/{v['runs']}")
        for failure in v["failures"]:
            for line in failure:
                print(f"      {line}")
    print(f"  docClean {report['score']['docClean']} allPass {report['score']['allPass']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
