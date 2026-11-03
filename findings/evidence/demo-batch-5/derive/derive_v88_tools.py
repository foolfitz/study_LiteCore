#!/usr/bin/env python3
"""Derive the generation-88 tools from the generation-87 ones (SPEC-P-demo-batch-5): a closed list of replacements per file, each with the count it
must match.  The parents are not edited.  Generation 88 keeps e2-editor-v32 and its four pins and archive; only the page, the shell digest and the
bundle file move.
  python3 -I derive_v88_tools.py        (after generation 88 is frozen)
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "wasm_sdk_probe/tools"
MANIFEST = REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v88.json"
PAGE_87 = "f6fd0b75dbf26a09d1ea0dcc97543cab8ef703a7e9c6eef4841953cff92caa26"
DIGEST_87 = "97c3da2935d64dfa442292d98bc54b3562ade298718dfb0d16752e5ea03aecda"
BUNDLE_87 = "ad5525f32f6ac2a38025c6a6934f51c57e1e843ecc409e396008da4568f736a8"
PAGE_88 = hashlib.sha256((REPO / "wasm_sdk_probe/web/e2-editor-app.js").read_bytes()).hexdigest()
BUNDLE_88 = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
DIGEST_88 = json.loads(MANIFEST.read_text(encoding="utf-8"))["bundleSha256"]

PLAN = {
    ("v87_four_arms_identity.py", "v88_four_arms_identity.py"): (
        '"""SPEC-P-demo-batch-5: what names the build under test for the generation-88 four-arm run.\n\n'
        "Derived from tools/v87_four_arms_identity.py (bound by F4-87's evidence; not edited) by\n"
        "findings/evidence/demo-batch-5/derive/derive_v88_tools.py.  The differences are a closed list: this paragraph and the\n"
        "line above it; the page, the shell digest and the bundle file (generation 88); 87 -> 88 in the messages and in the\n"
        "record.  The profile, its four pins and its archive stay e2-editor-v32's.  Everything below is that file's text.\n\n",
        [(f"PAGE_SHA256 = '{PAGE_87}'", f"PAGE_SHA256 = '{PAGE_88}'", 1),
         (f"CANDIDATE_SHELL_DIGEST = '{DIGEST_87}'", f"CANDIDATE_SHELL_DIGEST = '{DIGEST_88}'", 1),
         ("BUNDLE = 'e2/editor-shell-v2-bundle-v87.json'", "BUNDLE = 'e2/editor-shell-v2-bundle-v88.json'", 1),
         (f"BUNDLE_FILE_SHA256 = '{BUNDLE_87}'", f"BUNDLE_FILE_SHA256 = '{BUNDLE_88}'", 1),
         ("equal to frozen generation 87.", "equal to frozen generation 88.", 1),
         ("'shell digest is not generation 87: '", "'shell digest is not generation 88: '", 1),
         ("'generation 87 manifest differs: '", "'generation 88 manifest differs: '", 1),
         ("'live shell is not frozen generation 87'", "'live shell is not frozen generation 88'", 1),
         ("'page is not the generation-87 page'", "'page is not the generation-88 page'", 1),
         ("'shell': {'generation': 87,", "'shell': {'generation': 88,", 1)]),
    ("run_v87_four_arms.py", "run_v88_four_arms.py"): (
        '"""SPEC-P-demo-batch-5: the unchanged product-path suite with frozen-88 identity, then its four arms.\n\n'
        "Derived from tools/run_v87_four_arms.py (bound by F4-87's evidence; not edited).  The differences are a closed list:\n"
        "this paragraph and the line above it; generation 87 -> 88 (default manifest, twice); the identity and reader modules\n"
        "v87 -> v88; the lock name.  Everything below is that file's text.\n\n",
        [("'e2/editor-shell-v2-bundle-v87.json'", "'e2/editor-shell-v2-bundle-v88.json'", 2),
         ("import judge_v87_product_four_arms as reader", "import judge_v88_product_four_arms as reader", 2),
         ("from v87_four_arms_identity import PROFILE", "from v88_four_arms_identity import PROFILE", 1),
         ("common.browser_lock('v87-four-arms')", "common.browser_lock('v88-four-arms')", 1)]),
    ("judge_v87_product_four_arms.py", "judge_v88_product_four_arms.py"): (
        '"""Four-arm reader on v32/frozen 88 (SPEC-P-demo-batch-5).\n\n'
        "Derived from tools/judge_v87_product_four_arms.py (bound by F4-87's evidence; not edited).  The differences are a\n"
        "closed list: this paragraph and the line above it; the identity module v87 -> v88; the identity messages.\n"
        "Everything below is that file's text.\n\n",
        [("from v87_four_arms_identity import", "from v88_four_arms_identity import", 1),
         ("'shell generation is not frozen 87'", "'shell generation is not frozen 88'", 1),
         ("'product page is not the generation-87 page'", "'product page is not the generation-88 page'", 1)]),
    ("run_v87_f3_clipboard.py", "run_v88_f3_clipboard.py"): (
        '"""F3-88 (SPEC-P-demo-batch-5): the bound product-path runner on frozen generation 88, with the engine\'s copied text read\n'
        "from the clipboard, one press per format arm, and the clear's toast waited for (finding 178).\n\n"
        "Derived from tools/run_v87_f3_clipboard.py (bound by F3-87's evidence; not edited).  The differences are a closed\n"
        "list: this paragraph and the two lines above it; the shell manifest rebound to generation 88 (the `used` value and\n"
        "its refusal message); the module name.  Everything below is that file's text.\n\n",
        [("NAME = 'run_v87_f3_clipboard'", "NAME = 'run_v88_f3_clipboard'", 1),
         ("'used': 'e2/editor-shell-v2-bundle-v87.json'", "'used': 'e2/editor-shell-v2-bundle-v88.json'", 1),
         ("the generation-87 override", "the generation-88 override", 1)]),
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
