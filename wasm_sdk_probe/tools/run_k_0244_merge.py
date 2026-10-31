#!/usr/bin/env python3
"""K ruling item 4 for host 0.2.44 (SPEC-M3-K-0.2.44 section 2): the unchanged merge runner, bound in-process.

`run_merge_wasm_shakedown.py` is byte-identical to the runner of the 0.2.26 count (aaee0cda...), and its BINDING at
line 176 is never edited.  Before `main()`, this wrapper rebinds build_e2_c_shell_bundle.MANIFEST to generation 82
(before anything imports the runner, as tools/run_v24_four_arms.py does) and sets the module's BINDING to the proposed
binding of findings/evidence/k-0.2.44/k-binding-inventory.json.  The record {default, used, applied} goes next to
the report as <out>.binding-override.json.  The arguments are the runner's.  Since spec append 2 the wrapper also keys the
merge table in-process (k_0244_merge_keying.py) and records what it read as `keying` in the same file.
"""
import hashlib
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
INVENTORY = PROJECT.parent / "findings/evidence/k-0.2.44/k-binding-inventory.json"
MANIFEST = "e2/editor-shell-v2-bundle-v82.json"
MANIFEST_SHA256 = "da4e595d859c8659145b80721007be124ad17d4b6517145630a1f7edfed3a7f3"
RUNNER_SHA256_16 = "aaee0cda5be5ad84"
PROFILE = "e2-editor-v28"
sys.path.insert(0, str(TOOLS))


def main() -> int:
    import build_e2_c_shell_bundle as bundle
    import k_0244_merge_keying as keying
    if "run_merge_wasm_shakedown" in sys.modules or "run_e2_c_product_path" in sys.modules:
        raise SystemExit("a runner was imported before the overrides")
    if hashlib.sha256((PROJECT / MANIFEST).read_bytes()).hexdigest() != MANIFEST_SHA256:
        raise SystemExit("generation 82 manifest differs")
    default_manifest = bundle.MANIFEST.as_posix()
    bundle.MANIFEST = Path(MANIFEST)
    import run_merge_wasm_shakedown as m
    runner = hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()[:16]
    if runner != RUNNER_SHA256_16:
        raise SystemExit(f"merge runner {runner}, not {RUNNER_SHA256_16}: K ruling item 1's default, merge red NOT ESTABLISHED")
    proposed = json.loads(INVENTORY.read_bytes())["proposedMergeBinding"]
    if set(proposed) != set(m.BOUND_KEYS):
        raise SystemExit("the proposed binding does not have exactly the runner's bound keys")
    record = {"manifest": {"default": default_manifest, "used": MANIFEST, "applied": True, "fileSha256": MANIFEST_SHA256},
              "binding": {"default": m.BINDING, "used": proposed, "applied": True, "inventory": str(INVENTORY.name)}}
    m.BINDING = proposed
    # Spec append 2: the ordered engine's table, keyed on the bound wasm and its manifest.  Before any browser: a run that
    # is not on v28 (the historical v8 reds are read, never run here) or whose manifest does not name the wasm stops.
    profile = sys.argv[sys.argv.index("--candidate-profile") + 1] if "--candidate-profile" in sys.argv else None
    if "--pair" not in sys.argv and profile != PROFILE:
        raise SystemExit(f"--candidate-profile {profile}: this wrapper runs the count's profile, {PROFILE}")
    key = keying.read_key(PROJECT / "dist/profiles" / PROFILE / "probe.wasm", m.BOUNDARY_NOOP_FRAGMENT, proposed["wasmSha256"])
    keying.require_ordered(key)
    keying.install(m, m, key)
    record["keying"] = key
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.with_name(out.name + ".binding-override.json").write_text(json.dumps(record, indent=1) + "\n")
    return m.main()


if __name__ == "__main__":
    raise SystemExit(main())
