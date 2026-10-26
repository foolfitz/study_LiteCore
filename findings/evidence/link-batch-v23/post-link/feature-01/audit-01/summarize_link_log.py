#!/usr/bin/env python3
"""Summarize the fresh feature compile and link records from the preserved log."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex

p = argparse.ArgumentParser()
p.add_argument("--log", required=True, type=Path)
a = p.parse_args()
raw = a.log.read_bytes()
text = raw.decode("utf-8")
records = []
for line in text.replace("\\\n", " ").splitlines():
    if " -c " in line and "-o build/e2/editor-v23/" in line:
        args = shlex.split(line)
        records.append({"kind": "compile", "source": args[args.index("-c") + 1],
                        "output": args[args.index("-o") + 1],
                        "abi6": "-DOXSDK_E2_V23_FEATURE_ABI6" in args,
                        "diagnosticFlag": any("OXSDK_FINDING_016_SCHEDULER_PROBE" in x for x in args)})
    if "build/e2/editor-v23/probe.js" in line and ("em++" in line or "wasm-ld" in line):
        args = shlex.split(line)
        records.append({"kind": "link", "output": next((args[i + 1] for i, x in enumerate(args[:-1]) if x == "-o"), None),
                        "objectInputs": [x for x in args if x.startswith("build/e2/editor-v23/") and x.endswith(".o")]})
result = {"logPath": a.log.as_posix(), "logBytes": len(raw), "logSha256": hashlib.sha256(raw).hexdigest(),
          "compileCount": sum(r["kind"] == "compile" for r in records),
          "linkCount": sum(r["kind"] == "link" for r in records), "records": records}
print(json.dumps(result, indent=2))
