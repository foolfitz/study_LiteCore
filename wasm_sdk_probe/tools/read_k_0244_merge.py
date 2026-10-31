#!/usr/bin/env python3
"""K ruling item 3 for host 0.2.44 (SPEC-M3-K-0.2.44 section 2): are the merge reports the counted ones?

  non-red reports: counted true, binding == proposedMergeBinding, bound == binding on all nine keys, runner aaee0cda...,
                   stderr empty, candidate profile e2-editor-v28, a binding-override record that says applied
  red reports:     binding == originalMergeBinding, the non-profile bound keys equal to it, wasm 4a2710bb..., runner
                   aaee0cda..., profile e2-editor-v8, boot ready, three cases (they are the 0.2.26 count's, read, not run)
  every report of a browser present, and the historical reds byte-equal to release-0.2.26/merge-m2/ (K ruling item 1)

  read_k_0244_merge.py --dir DIR            exit 0 iff K_MERGE_COUNTED
  read_k_0244_merge.py --dir DIR --self-test   each clause's mutation of a holding input must be red

The verdict on the behaviour stays judge_counted_m2.py's (--uncounted, exit 4, red PASS, oneRunner); this reader only
says what those reports are.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
INVENTORY = REPO / "findings/evidence/k-0.2.44/k-binding-inventory.json"
HISTORICAL = REPO / "findings/evidence/release-0.2.26/merge-m2"
RUNNER = "aaee0cda5be5ad84"
V8_WASM = "4a2710bba1ef07d9364f02bd07905f0e95e92f805d97eab37dfb26"  # a prefix, compared with startswith
BROWSERS = ("chrome", "firefox")
KINDS = {"counted": "counted-{}", "control": "counted-control-{}", "m2-1b": "m2-1b-{}", "m2-4": "m2-4-{}"}
PROFILE_BOUND = ("wasmSha256", "workerSha256", "pageSha256")


def load(directory: Path):
    reports = {}
    for browser in BROWSERS:
        for kind, stem in {**KINDS, "red": "red-{}"}.items():
            path = directory / (stem.format(browser) + ".json")
            if path.is_file():
                stderr = path.with_name(path.stem + ".stderr.txt")
                override = path.with_name(path.name + ".binding-override.json")
                reports[(browser, kind)] = {"report": json.loads(path.read_text()),
                                            "stderrBytes": stderr.stat().st_size if stderr.is_file() else None,
                                            "override": json.loads(override.read_text()) if override.is_file() else None,
                                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return reports


def read(reports, proposed, original, historical):
    problems = []
    for browser in BROWSERS:
        for kind in (*KINDS, "red"):
            item = reports.get((browser, kind))
            where = f"{browser} {kind}"
            if item is None:
                problems.append(f"{where}: report missing")
                continue
            r = item["report"]
            if r.get("runner") != RUNNER:
                problems.append(f"{where}: runner {r.get('runner')}")
            bound, binding = r.get("bound") or {}, r.get("binding")
            if kind == "red":
                if binding != original:
                    problems.append(f"{where}: binding is not the original merge binding")
                if any(bound.get(k) != original.get(k) for k in original if k not in PROFILE_BOUND):
                    problems.append(f"{where}: a non-profile bound key differs")
                if not str(bound.get("wasmSha256") or "").startswith(V8_WASM):
                    problems.append(f"{where}: wasm {bound.get('wasmSha256')}")
                if (r.get("candidate") or {}).get("profile") != "e2-editor-v8" or (r.get("boot") or {}).get("state") != "ready":
                    problems.append(f"{where}: not v8 booted ready")
                if len(r.get("cases") or []) != 3:
                    problems.append(f"{where}: {len(r.get('cases') or [])} cases")
                if item["sha256"] != historical.get(browser):
                    problems.append(f"{where}: not byte-equal to release-0.2.26/merge-m2/")
            else:
                if r.get("counted") is not True:
                    problems.append(f"{where}: counted {r.get('counted')}")
                if binding != proposed:
                    problems.append(f"{where}: binding is not the proposed one")
                if set(bound) != set(proposed) or any(bound.get(k) != v for k, v in proposed.items()):
                    problems.append(f"{where}: bound differs from the binding")
                if (r.get("candidate") or {}).get("profile") != "e2-editor-v28":
                    problems.append(f"{where}: profile {(r.get('candidate') or {}).get('profile')}")
                if item["stderrBytes"] != 0:
                    problems.append(f"{where}: stderr bytes {item['stderrBytes']}")
                if not ((item["override"] or {}).get("binding") or {}).get("applied"):
                    problems.append(f"{where}: no applied binding override")
    return ("K_MERGE_COUNTED" if not problems else "K_MERGE_NOT_COUNTED"), problems


def inputs():
    inventory = json.loads(INVENTORY.read_bytes())
    historical = {b: hashlib.sha256((HISTORICAL / f"red-{b}.json").read_bytes()).hexdigest() for b in BROWSERS}
    return inventory["proposedMergeBinding"], inventory["originalMergeBinding"], historical


def mutations():
    def report(key):
        return lambda r: r[key]["report"]

    def flip_bound(r):
        bound = r[("chrome", "counted")]["report"]["bound"]
        bound["wasmSha256"] = bound["wasmSha256"][::-1]

    yield "run-without-override-is-uncounted", lambda r: r[("firefox", "counted")]["report"].__setitem__("counted", False)
    yield "one-flipped-bound-hash", flip_bound
    yield "another-runner", lambda r: r[("chrome", "m2-4")]["report"].__setitem__("runner", "0" * 16)
    yield "stderr-not-empty", lambda r: r[("firefox", "control")].__setitem__("stderrBytes", 3)
    yield "no-override-record", lambda r: r[("chrome", "m2-1b")].__setitem__("override", None)
    yield "wrong-profile", lambda r: r[("chrome", "counted")]["report"]["candidate"].__setitem__("profile", "e2-editor-v27")
    yield "missing-report", lambda r: r.pop(("firefox", "m2-4"))
    yield "red-rebound", lambda r: r[("chrome", "red")]["report"].__setitem__("binding", dict(r[("chrome", "counted")]["report"]["binding"]))
    yield "red-not-historical", lambda r: r[("firefox", "red")].__setitem__("sha256", "0" * 64)
    yield "red-two-cases", lambda r: r[("chrome", "red")]["report"]["cases"].pop()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    proposed, original, historical = inputs()
    reports = load(args.dir)
    verdict, problems = read(reports, proposed, original, historical)
    if args.self_test:
        if verdict != "K_MERGE_COUNTED":
            print(f"self-test needs a holding input; this one is {verdict}: {problems[:4]}", file=sys.stderr)
            return 2
        results = {}
        for name, mutate in mutations():
            mutated = copy.deepcopy(reports)
            mutate(mutated)
            results[name] = read(mutated, proposed, original, historical)[0]
        red = all(v != "K_MERGE_COUNTED" for v in results.values())
        print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "results": results}, indent=1))
        return 0 if red else 1
    print(json.dumps({"verdict": verdict, "problems": problems}, indent=1))
    return 0 if verdict == "K_MERGE_COUNTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
