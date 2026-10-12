#!/usr/bin/env python3
"""Criterion 131-B (specs/SPEC-M3-autosave.md §9.12), read from a probe_hand_test_0212.py report.

Per browser: the rapid20 arm has exactly ROUNDS bursts, and every burst has refusedDeleteSelection == 0,
deleted == 20 and other == []; the high and low arms each have persistent.differing == 0.  Both browsers
must be present.  Prints every number it reads.  Exit 0 = PASS, 1 = FAIL.

  judge_131b.py REPORT.json [--rounds 6] [--page SHA256]
"""
import argparse
import json
import sys

p = argparse.ArgumentParser()
p.add_argument("report")
p.add_argument("--rounds", type=int, default=6)
p.add_argument("--page", default=None, help="the page the report must say was served")
a = p.parse_args()
r = json.load(open(a.report))
bad = []
served = (r.get("static") or {}).get("servedPage")
print("servedPage", served)
if a.page and served != a.page:
    bad.append(f"served page {served} is not {a.page}")
seen = set()
for run in r.get("runs") or []:
    b = run.get("browser")
    seen.add(b)
    if run.get("fatal"):
        bad.append(f"{b}: fatal {run['fatal'][-200:]}")
    rounds = (run.get("rapid20") or {}).get("rounds") or []
    for i, x in enumerate(rounds):
        print(f"{b} burst {i + 1}: deleted {x.get('deleted')} refused {x.get('refusedDeleteSelection')} other {x.get('other')}")
        if x.get("deleted") != 20 or x.get("refusedDeleteSelection") != 0 or x.get("other") != []:
            bad.append(f"{b} burst {i + 1}")
    if len(rounds) != a.rounds:
        bad.append(f"{b}: {len(rounds)} bursts, wanted {a.rounds}")
    for arm in ("high", "low"):
        d = ((run.get(arm) or {}).get("persistent") or {}).get("differing")
        print(f"{b} {arm} persistent.differing {d}")
        if d != 0:
            bad.append(f"{b} {arm} persistent {d}")
for b in ("chrome", "firefox"):
    if b not in seen:
        bad.append(f"{b}: no run")
print("131-B", "PASS" if not bad else "FAIL", bad)
sys.exit(1 if bad else 0)
