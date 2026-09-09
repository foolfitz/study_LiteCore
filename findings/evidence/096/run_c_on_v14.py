#!/usr/bin/env python3
"""Run finding 096's half-C probe against a profile OTHER than the one the
product page pins.

WHY THIS EXISTS, and why it is a driver rather than an edit to the probe.
`probe_096_checkpoint_before_the_gesture.py` has no `--profile`: it mirrors
`dist/` as it stands and the page there pins `e2-editor-v8`
(`PINNED_WASM_SHA256 = "4a2710bba1ef07d9"`, `profiles/e2-editor-v8/sdk-worker.js`).
Re-running it unchanged after the link therefore measures the SHIPPING engine,
not the new one -- so the handoff's step 3 ("a RECOVERED there after the link
means the deadline is not in the artifact") cannot be evaluated by the literal
re-run.  The probe is left byte-identical; every judgement, arm, mutation
assertion and verdict below is the probe's own.

WHAT THIS CHANGES: exactly one file in each served mirror -- `e2-editor-app.js`,
replaced by `repointed_page()`, the SAME function the boundary-arrow probe and
`build_cutover_page.py` use, so the worker URL and the pinned wasm hash move
together.  Nothing is written into the tree; the mirrors are temporary.

The report's own `profile` string is corrected afterwards (the probe hard-codes
it), and the page sha256, the pin before and the pin after are added, so the
JSON cannot be read as a measurement of v8.
"""
import json
import sys
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
EVIDENCE = Path("/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/096")
sys.path.insert(0, str(PROJECT / "tools"))
sys.path.insert(0, str(EVIDENCE))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "probe_c", EVIDENCE / "probe_096_checkpoint_before_the_gesture.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

from run_e2_c_product_path import repointed_page   # noqa: E402

PROFILE = sys.argv[1]
OUT = Path(sys.argv[2])
ATTEMPTS = sys.argv[3] if len(sys.argv) > 3 else "3"

manifest = PROJECT / "dist" / "profiles" / PROFILE / "sdk-manifest.json"
source = (PROJECT / "dist" / "e2-editor-app.js").read_text(encoding="utf-8")
page, pin_before, wasm = repointed_page(source, PROFILE, manifest)
import hashlib
page_sha = hashlib.sha256(page.encode("utf-8")).hexdigest()
assert f'profiles/{PROFILE}/sdk-worker.js' in page
assert f'PINNED_WASM_SHA256 = "{wasm[:16]}"' in page

original_build_mirror = probe.build_mirror


def build_mirror(root, mirror, overrides):
    merged = dict(overrides)
    merged["e2-editor-app.js"] = page.encode("utf-8")
    return original_build_mirror(root, mirror, merged)


probe.build_mirror = build_mirror

sys.argv = [str(EVIDENCE / "probe_096_checkpoint_before_the_gesture.py"),
            "--attempts", ATTEMPTS, "--out", str(OUT)]
rc = probe.main()

report = json.loads(OUT.read_text(encoding="utf-8"))
report["profile"] = PROFILE
report["pageRepointedBy"] = (
    "scratch driver run_c_on_v14.py -- the probe itself is unmodified; the "
    "served mirror's e2-editor-app.js was replaced by repointed_page()")
report["pageSha256"] = page_sha
report["pagePinBefore"] = pin_before
report["pagePinAfter"] = wasm[:16]
report["wasmSha256"] = wasm
report["engineHalfIsUnmeasurable"] = (
    "SUPERSEDED for this run: the page serves " + PROFILE + ", whose engine "
    "carries the move-path deadline. The probe's docstring statement that no "
    "artifact in this tree answers the press was true when it was written.")
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
               encoding="utf-8")
print("profile", PROFILE, "page", page_sha[:16], "pin", pin_before, "->",
      wasm[:16], file=sys.stderr)
sys.exit(rc)
