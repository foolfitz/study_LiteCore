#!/usr/bin/env python3
"""Derive the generation-84 tools from the generation-83 ones (SPEC-P-demo-batch-1 section 3): a closed list of replacements
per file, each with the count it must match.  The parents are not edited; generation 84 keeps the profile, so only the page,
the shell digest and the bundle move.  The F3 reader is not derived: tools/read_v83_f3_equal.py takes --baseline.

  python3 -I derive_v84_tools.py        (after generation 84 is frozen)
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "wasm_sdk_probe/tools"
MANIFEST = REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v84.json"
PAGE_83 = "022d0cd0b5152f1ee9cabc74b10f5af2eb55935299228119a419ab717957759b"
DIGEST_83 = "607b280d8ce86b04b471ad21a84f8c96eadb405a50ef1eb14ad5b0d91324a704"
BUNDLE_83 = "98371d7f7479021dc2b859bf78db796571d7070b8509548edf7db977bc214174"

PAGE_84 = hashlib.sha256((REPO / "wasm_sdk_probe/web/e2-editor-app.js").read_bytes()).hexdigest()
BUNDLE_84 = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
DIGEST_84 = json.loads(MANIFEST.read_text(encoding="utf-8"))["bundleSha256"]

PLAN = {
    ("v83_four_arms_identity.py", "v84_four_arms_identity.py"): (
        '"""SPEC-P-demo-batch-1 section 3: what names the build under test for the generation-84 four-arm run.\n\n'
        "Derived from tools/v83_four_arms_identity.py (bound by F4-83's evidence; not edited) by\n"
        "findings/evidence/demo-batch-1/derive/derive_v84_tools.py.  The differences are a closed list: this paragraph and the\n"
        "line above it; the page, the shell digest and the bundle file (generation 84); 83 -> 84 in the messages, in the\n"
        "record and in shell()'s docstring.  The profile stays e2-editor-v29.  Everything below is that file's text.\n\n",
        [(f"PAGE_SHA256 = '{PAGE_83}'", f"PAGE_SHA256 = '{PAGE_84}'", 1),
         (f"CANDIDATE_SHELL_DIGEST = '{DIGEST_83}'", f"CANDIDATE_SHELL_DIGEST = '{DIGEST_84}'", 1),
         ("BUNDLE = 'e2/editor-shell-v2-bundle-v83.json'", "BUNDLE = 'e2/editor-shell-v2-bundle-v84.json'", 1),
         (f"BUNDLE_FILE_SHA256 = '{BUNDLE_83}'", f"BUNDLE_FILE_SHA256 = '{BUNDLE_84}'", 1),
         ("equal to frozen generation 83.", "equal to frozen generation 84.", 1),
         ("'shell digest is not generation 83: '", "'shell digest is not generation 84: '", 1),
         ("'generation 83 manifest differs: '", "'generation 84 manifest differs: '", 1),
         ("'live shell is not frozen generation 83'", "'live shell is not frozen generation 84'", 1),
         ("'page is not the generation-83 page'", "'page is not the generation-84 page'", 1),
         ("'shell': {'generation': 83,", "'shell': {'generation': 84,", 1)]),
    ("run_v83_four_arms.py", "run_v84_four_arms.py"): (
        '"""SPEC-P-demo-batch-1 section 3: the unchanged product-path suite with frozen-84 identity, then its four arms.\n\n'
        "Derived from tools/run_v83_four_arms.py (bound by F4-83's evidence; not edited).  The differences are a closed list:\n"
        "this paragraph and the line above it; generation 83 -> 84 (default manifest, twice); the identity and reader modules\n"
        "v83 -> v84; the lock name.  Everything below is that file's text.\n\n",
        [("'e2/editor-shell-v2-bundle-v83.json'", "'e2/editor-shell-v2-bundle-v84.json'", 2),
         ("import judge_v83_product_four_arms as reader", "import judge_v84_product_four_arms as reader", 2),
         ("from v83_four_arms_identity import PROFILE", "from v84_four_arms_identity import PROFILE", 1),
         ("common.browser_lock('v83-four-arms')", "common.browser_lock('v84-four-arms')", 1)]),
    ("judge_v83_product_four_arms.py", "judge_v84_product_four_arms.py"): (
        '"""Four-arm reader on v29/frozen 84 (SPEC-P-demo-batch-1 section 3).\n\n'
        "Derived from tools/judge_v83_product_four_arms.py (bound by F4-83's evidence; not edited).  The differences are a\n"
        "closed list: this paragraph and the line above it; the identity module v83 -> v84; two identity messages.\n"
        "Everything below is that file's text.\n\n",
        [("from v83_four_arms_identity import", "from v84_four_arms_identity import", 1),
         ("'shell generation is not frozen 83'", "'shell generation is not frozen 84'", 1),
         ("'product page is not the generation-83 page'", "'product page is not the generation-84 page'", 1)]),
    ("run_v83_f3_clipboard.py", "run_v84_f3_clipboard.py"): (
        '"""F3-84 (SPEC-P-demo-batch-1 section 3): the bound product-path runner on frozen generation 84, with the engine\'s\n'
        "copied text read from the clipboard, and one press per format arm (finding 178).\n\n"
        "Derived from tools/run_v83_f3_clipboard.py (bound by F3-83's evidence; not edited).  The differences are a closed\n"
        "list: this paragraph and the two lines above it; the shell manifest rebound to generation 84 (the `used` value and\n"
        "its refusal message); the module name; REPLACEMENTS gains finding 178's removal of the first press, the same edit as\n"
        "findings/evidence/v29-177/f3-83/diag_single_press.py.  Everything below is that file's text.\n\n",
        [("NAME = 'run_v83_f3_clipboard'", "NAME = 'run_v84_f3_clipboard'", 1),
         ("'used': 'e2/editor-shell-v2-bundle-v83.json'", "'used': 'e2/editor-shell-v2-bundle-v84.json'", 1),
         ("the generation-83 override", "the generation-84 override", 1)]),
}

SINGLE_PRESS = '''
# Finding 178: the bound `format_arm` presses each format button twice.  Removed here, as diag_single_press.py did for F3-83.
_TAIL = '                "return b ? !b.disabled : null; })()")\\n'
_PRESS = '            evaluate(session, PRESS.replace("ARG_ACTION", action))\\n'
_NEXT = '            # WAIT ON THE COMPLETION SIGNAL, AND RECORD THE STATE CACHE.\\n'
REPLACEMENTS = REPLACEMENTS + (("single-press", _TAIL + _PRESS + _NEXT, _TAIL + _NEXT),)
'''

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
    if child == "run_v84_f3_clipboard.py":
        anchor = code.index("REPLACEMENTS = (")
        close = code.index("\n)\n", anchor) + 3
        code = code[:close] + SINGLE_PRESS + code[close:]
    (TOOLS / child).write_text(shebang + header + doc + code, encoding="utf-8")
    print(child, "written")
