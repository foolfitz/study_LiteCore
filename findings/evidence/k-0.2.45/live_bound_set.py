#!/usr/bin/env python3
"""Spec K-0.2.44 4.2, on K 0.2.45 (a copy, so the receipt lands next to it): the live-bound set (v24 section 17 item 1) has not moved since v24's count.  Tool-closed over the
receipts: v23's counted cohort instrumentSources, v24's counted cohort instrumentSources and remaining orchestrationSources,
the settled reference reader-05's bindings under wasm_sdk_probe/, native run-03's identity sources; every path's live
sha256 against the LATEST receipt that records it (v24's count over v23's).  Writes live-bound-set.json next to itself.
Exit 0 iff no path moved.  A red case: --flip PATH reads that path as changed, and the verdict must go red.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
EV = ROOT / "findings/evidence"
SDK = ROOT / "wasm_sdk_probe"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    flip = sys.argv[sys.argv.index("--flip") + 1] if "--flip" in sys.argv else None
    records = [("v23-count", EV / "link-batch-v23/feature-protocol/counted-r1-s5-01/cohort.json", "instrumentSources"),
               ("v24-count", EV / "link-batch-v24/counted-selection-01/cohort.json", "instrumentSources"),
               ("v24-remaining", EV / "link-batch-v24/remaining-counted-01/cohort.json", "orchestrationSources")]
    frozen = {}
    for label, path, field in records:
        for name, value in json.loads(path.read_bytes())[field].items():
            digest = value if isinstance(value, str) else value.get("sha256")
            frozen["wasm_sdk_probe/" + name] = (digest, label)
    settled = json.loads((EV / "link-batch-v23/feature-protocol/s5-native/settled-reference-reader-05.json").read_bytes())
    for name, value in settled["bindings"].items():
        if name.startswith("wasm_sdk_probe/") and name not in frozen:
            digest = value if isinstance(value, str) else value.get("sha256")
            frozen[name] = (digest, "settled-reader-05")
    moved, rows = [], {}
    for name, (digest, label) in sorted(frozen.items()):
        path = ROOT / name
        live = sha(path) if path.is_file() else None
        if name == flip:
            live = "0" * 64
        rows[name] = {"receipt": label, "frozen": digest, "live": live, "moved": live != digest}
        if live != digest:
            moved.append(name)
    report = {"paths": len(rows), "moved": moved, "verdict": "LIVE_BOUND_SET_UNMOVED" if not moved and rows else "LIVE_BOUND_SET_MOVED", "rows": rows}
    if not flip:
        (Path(__file__).with_name("live-bound-set.json")).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("paths", "moved", "verdict")}, indent=1))
    return 0 if report["verdict"] == "LIVE_BOUND_SET_UNMOVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
