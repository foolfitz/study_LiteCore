#!/usr/bin/env python3
"""Derive the generation-85 tools from the generation-84 ones (SPEC-P-demo-batch-3 section 2): a closed list of replacements per
file, each with the count it must match.  The parents are not edited.  Generation 85 moves the profile to e2-editor-v30: its worker
and manifest pins and its archive change, the wasm and the loader do not.  The F3 reader is not derived: read_v83_f3_equal.py takes
--baseline.

  python3 -I derive_v85_tools.py        (after generation 85 is frozen)
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "wasm_sdk_probe/tools"
MANIFEST = REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v85.json"
OLD = json.loads((REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v84.json").read_text(encoding="utf-8"))
PAGE_84 = "c377b9f2a41b1d6223ec67ac8d53fdd2d1920086af2e0f5759aa4118d084edaf"
PAGE_85 = hashlib.sha256((REPO / "wasm_sdk_probe/web/e2-editor-app.js").read_bytes()).hexdigest()
BUNDLE_84 = hashlib.sha256((REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v84.json").read_bytes()).hexdigest()
BUNDLE_85 = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
DIGEST_84 = OLD["bundleSha256"]
DIGEST_85 = json.loads(MANIFEST.read_text(encoding="utf-8"))["bundleSha256"]
WORKER_29 = "a5df83dbd0bd4df6b67b81d000da141910b76252fbf2bb8636d9a312edfffcba"
WORKER_30 = "464d129c044231c516c666487db32e78f33d3f6393d2afdcc089d36bb0f0fe93"
MANIFEST_29 = "a0352c83b312b4f3988886936228985bea83aafa6cd0a49ce6af56f519d3432b"
MANIFEST_30 = "9616efbaab4200bfb2de3c3570b2ba7e726c32c2c5667ac9ed0c822c403b00ac"

PLAN = {
    ("v84_four_arms_identity.py", "v85_four_arms_identity.py"): (
        '"""SPEC-P-demo-batch-3 section 2: what names the build under test for the generation-85 four-arm run.\n\n'
        "Derived from tools/v84_four_arms_identity.py (bound by F4-84's evidence; not edited) by\n"
        "findings/evidence/demo-batch-3/derive/derive_v85_tools.py.  The differences are a closed list: this paragraph and the\n"
        "line above it; PROFILE e2-editor-v29 -> e2-editor-v30; the pins of sdk-worker.js and sdk-manifest.json (probe.wasm and\n"
        "probe.js are v29's bytes, unchanged); ARCHIVED_PROFILE -> the v30 archive; the page, the shell digest and the bundle\n"
        "file (generation 85); 84 -> 85 and v29 -> v30 in the messages and in the record.  Everything below is that file's text.\n\n",
        [(f"PAGE_SHA256 = '{PAGE_84}'", f"PAGE_SHA256 = '{PAGE_85}'", 1),
         (f"CANDIDATE_SHELL_DIGEST = '{DIGEST_84}'", f"CANDIDATE_SHELL_DIGEST = '{DIGEST_85}'", 1),
         ("BUNDLE = 'e2/editor-shell-v2-bundle-v84.json'", "BUNDLE = 'e2/editor-shell-v2-bundle-v85.json'", 1),
         (f"BUNDLE_FILE_SHA256 = '{BUNDLE_84}'", f"BUNDLE_FILE_SHA256 = '{BUNDLE_85}'", 1),
         ("PROFILE = 'e2-editor-v29'", "PROFILE = 'e2-editor-v30'", 1),
         (f"'sdk-worker.js': '{WORKER_29}'", f"'sdk-worker.js': '{WORKER_30}'", 1),
         (f"'sdk-manifest.json': '{MANIFEST_29}'", f"'sdk-manifest.json': '{MANIFEST_30}'", 1),
         ("ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v29-e61e5890-worker-a5df83db'",
          "ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v30-e61e5890-worker-464d129c'", 1),
         ("equal to frozen generation 84.", "equal to frozen generation 85.", 1),
         ("'shell digest is not generation 84: '", "'shell digest is not generation 85: '", 1),
         ("'generation 84 manifest differs: '", "'generation 85 manifest differs: '", 1),
         ("'live shell is not frozen generation 84'", "'live shell is not frozen generation 85'", 1),
         ("'page is not the generation-84 page'", "'page is not the generation-85 page'", 1),
         ("'shell': {'generation': 84,", "'shell': {'generation': 85,", 1),
         ("'v29 profile/archive identity differs: '", "'v30 profile/archive identity differs: '", 1),
         ("'v29 ABI/profile/typedInsert differs'", "'v30 ABI/profile/typedInsert differs'", 1)]),
    ("run_v84_four_arms.py", "run_v85_four_arms.py"): (
        '"""SPEC-P-demo-batch-3 section 2: the unchanged product-path suite with frozen-85 identity, then its four arms.\n\n'
        "Derived from tools/run_v84_four_arms.py (bound by F4-84's evidence; not edited).  The differences are a closed list:\n"
        "this paragraph and the line above it; generation 84 -> 85 (default manifest, twice); the identity and reader modules\n"
        "v84 -> v85; the lock name.  Everything below is that file's text.\n\n",
        [("'e2/editor-shell-v2-bundle-v84.json'", "'e2/editor-shell-v2-bundle-v85.json'", 2),
         ("import judge_v84_product_four_arms as reader", "import judge_v85_product_four_arms as reader", 2),
         ("from v84_four_arms_identity import PROFILE", "from v85_four_arms_identity import PROFILE", 1),
         ("common.browser_lock('v84-four-arms')", "common.browser_lock('v85-four-arms')", 1)]),
    ("judge_v84_product_four_arms.py", "judge_v85_product_four_arms.py"): (
        '"""Four-arm reader on v30/frozen 85 (SPEC-P-demo-batch-3 section 2).\n\n'
        "Derived from tools/judge_v84_product_four_arms.py (bound by F4-84's evidence; not edited).  The differences are a\n"
        "closed list: this paragraph and the line above it; the identity module v84 -> v85; the identity messages.\n"
        "Everything below is that file's text.\n\n",
        [("from v84_four_arms_identity import", "from v85_four_arms_identity import", 1),
         ("'shell generation is not frozen 84'", "'shell generation is not frozen 85'", 1),
         ("'product page is not the generation-84 page'", "'product page is not the generation-85 page'", 1),
         ("'profile is not v29 ABI6'", "'profile is not v30 ABI6'", 1)]),
    ("run_v84_f3_clipboard.py", "run_v85_f3_clipboard.py"): (
        '"""F3-85 (SPEC-P-demo-batch-3 section 2): the bound product-path runner on frozen generation 85, with the engine\'s\n'
        "copied text read from the clipboard, and one press per format arm (finding 178).\n\n"
        "Derived from tools/run_v84_f3_clipboard.py (bound by F3-84's evidence; not edited).  The differences are a closed\n"
        "list: this paragraph and the two lines above it; the shell manifest rebound to generation 85 (the `used` value and\n"
        "its refusal message); the module name.  Everything below is that file's text.\n\n",
        [("NAME = 'run_v84_f3_clipboard'", "NAME = 'run_v85_f3_clipboard'", 1),
         ("'used': 'e2/editor-shell-v2-bundle-v84.json'", "'used': 'e2/editor-shell-v2-bundle-v85.json'", 1),
         ("the generation-84 override", "the generation-85 override", 1)]),
}

for (parent, child), (header, replacements) in PLAN.items():
    text = (TOOLS / parent).read_text(encoding="utf-8")
    shebang = "#!/usr/bin/env python3\n" if text.startswith("#!/usr/bin/env python3\n") else ""
    body = text[len(shebang):]
    if not body.startswith('"""'):
        raise SystemExit(f"{parent}: no docstring at the top")
    end = body.index('"""', 3) + 3
    doc, code = body[3:end], body[end:]
    for old, new, count in replacements:
        got = code.count(old)
        if got != count:
            raise SystemExit(f"{parent}: {old[:60]!r} occurs {got} times in the code, expected {count}")
        code = code.replace(old, new)
    (TOOLS / child).write_text(shebang + header + doc + code, encoding="utf-8")
    print(child, "written")
