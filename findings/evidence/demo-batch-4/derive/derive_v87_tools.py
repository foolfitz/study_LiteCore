#!/usr/bin/env python3
"""Derive the generation-87 tools from the generation-86 ones (SPEC-P-demo-batch-4 section 5): a closed list of replacements per file, each with
the count it must match.  The parents are not edited.  Generation 87 moves the profile to e2-editor-v32, a real link: all four pins and the
archive change.  The F3 runner also takes the wait on the clear's toast as a replacement, which finding 178's append of 2026-11-03 asks of the
next generation.  The F3 reader is not derived: read_v83_f3_equal.py takes --baseline.

  python3 -I derive_v87_tools.py        (after generation 87 is frozen)
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "wasm_sdk_probe/tools"
MANIFEST = REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v87.json"
OLD = json.loads((REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v86.json").read_text(encoding="utf-8"))
PAGE_86 = "50127676e87df9c8ef33a3f8bf7780d0692f1f65b253df50dfa95ba4568fbe4b"
PAGE_87 = hashlib.sha256((REPO / "wasm_sdk_probe/web/e2-editor-app.js").read_bytes()).hexdigest()
BUNDLE_86 = hashlib.sha256((REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v86.json").read_bytes()).hexdigest()
BUNDLE_87 = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
DIGEST_86 = OLD["bundleSha256"]
DIGEST_87 = json.loads(MANIFEST.read_text(encoding="utf-8"))["bundleSha256"]
PINS = {"probe.wasm": ("809893a97c9d2d19e60f9aaee14bf49c201c6d4f0c6210abc46ea9e797ab13bf", "54e500931de0ee28fe5e6c9916adfef48ec7f81ae71cd432ddb1c6bc02db46fa"),
        "probe.js": ("f557d76c30b3ecf8fc658a83d48a5a95a4a4632ca6f68d59581c2729280f3abc", "a261f4c1fc72a251ca2c611e39232de87e6a6cb40eed53e729ea503bc3604c36"),
        "sdk-worker.js": ("54352fad3f5434162512d20e64e655a9cce789629495a74cbbe4c8a34e41637e", "c394302c589baff3b40ff67a7579e07cf53fc7447dd3f04b26ff9c827280ff36"),
        "sdk-manifest.json": ("faa7bdb97c212c5039efbaffa21fc6d532033d60f12ce6960ed9450fe00adb7d", "7616e19207e53fd773ec9debd6f75fd3fa10f889746855d6934fd7e9ccd916cd")}
SINGLE = 'REPLACEMENTS = REPLACEMENTS + (("single-press", _TAIL + _PRESS + _NEXT, _TAIL + _NEXT),)\n'
CLEAR_WAIT = SINGLE + r'''
# Finding 178's append: the wait on the 清除格式 label is met by the first of the clear's four steps, so the runner can press into the page's own
# loop.  The toast 「已清除…」 is written once, after the fourth.  The same edit as findings/evidence/demo-batch-3/f3-86/diag_clear_wait.py.
_LABEL = 'lambda st: "清除格式" in (st.get("latency") or ""), 30)'
_DONE = 'lambda st: "已清除" in (evaluate(session, READ_TOAST) or ""), 30)'
REPLACEMENTS = REPLACEMENTS + (
    ("clear-wait-normalise",
     '                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + _LABEL,
     '                evaluate(session, CLEAR_TOAST)\n                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + _DONE),
    ("clear-wait-accumulate",
     '        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + _LABEL,
     '        evaluate(session, CLEAR_TOAST)\n        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + _DONE),
)
'''

PLAN = {
    ("v86_four_arms_identity.py", "v87_four_arms_identity.py"): (
        '"""SPEC-P-demo-batch-4 section 5: what names the build under test for the generation-87 four-arm run.\n\n'
        "Derived from tools/v86_four_arms_identity.py (bound by F4-86's evidence; not edited) by\n"
        "findings/evidence/demo-batch-4/derive/derive_v87_tools.py.  The differences are a closed list: this paragraph and the\n"
        "line above it; PROFILE e2-editor-v31 -> e2-editor-v32; the four ARTIFACT_PINS (a real link: probe.wasm 54e50093,\n"
        "probe.js a261f4c1, sdk-worker.js c394302c, sdk-manifest.json 7616e192); ARCHIVED_PROFILE -> the v32 archive; the page,\n"
        "the shell digest and the bundle file (generation 87); 86 -> 87 and v31 -> v32 in the messages and in the record.\n"
        "Everything below is that file's text.\n\n",
        [(f"PAGE_SHA256 = '{PAGE_86}'", f"PAGE_SHA256 = '{PAGE_87}'", 1),
         (f"CANDIDATE_SHELL_DIGEST = '{DIGEST_86}'", f"CANDIDATE_SHELL_DIGEST = '{DIGEST_87}'", 1),
         ("BUNDLE = 'e2/editor-shell-v2-bundle-v86.json'", "BUNDLE = 'e2/editor-shell-v2-bundle-v87.json'", 1),
         (f"BUNDLE_FILE_SHA256 = '{BUNDLE_86}'", f"BUNDLE_FILE_SHA256 = '{BUNDLE_87}'", 1),
         ("PROFILE = 'e2-editor-v31'", "PROFILE = 'e2-editor-v32'", 1)]
        + [(f"'{name}': '{old}'", f"'{name}': '{new}'", 1) for name, (old, new) in PINS.items()]
        + [("ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v31-809893a9-worker-54352fad'",
            "ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v32-54e50093-worker-c394302c'", 1),
           ("equal to frozen generation 86.", "equal to frozen generation 87.", 1),
           ("'shell digest is not generation 86: '", "'shell digest is not generation 87: '", 1),
           ("'generation 86 manifest differs: '", "'generation 87 manifest differs: '", 1),
           ("'live shell is not frozen generation 86'", "'live shell is not frozen generation 87'", 1),
           ("'page is not the generation-86 page'", "'page is not the generation-87 page'", 1),
           ("'shell': {'generation': 86,", "'shell': {'generation': 87,", 1),
           ("'v31 profile/archive identity differs: '", "'v32 profile/archive identity differs: '", 1),
           ("'v31 ABI/profile/typedInsert differs'", "'v32 ABI/profile/typedInsert differs'", 1)]),
    ("run_v86_four_arms.py", "run_v87_four_arms.py"): (
        '"""SPEC-P-demo-batch-4 section 5: the unchanged product-path suite with frozen-87 identity, then its four arms.\n\n'
        "Derived from tools/run_v86_four_arms.py (bound by F4-86's evidence; not edited).  The differences are a closed list:\n"
        "this paragraph and the line above it; generation 86 -> 87 (default manifest, twice); the identity and reader modules\n"
        "v86 -> v87; the lock name.  Everything below is that file's text.\n\n",
        [("'e2/editor-shell-v2-bundle-v86.json'", "'e2/editor-shell-v2-bundle-v87.json'", 2),
         ("import judge_v86_product_four_arms as reader", "import judge_v87_product_four_arms as reader", 2),
         ("from v86_four_arms_identity import PROFILE", "from v87_four_arms_identity import PROFILE", 1),
         ("common.browser_lock('v86-four-arms')", "common.browser_lock('v87-four-arms')", 1)]),
    ("judge_v86_product_four_arms.py", "judge_v87_product_four_arms.py"): (
        '"""Four-arm reader on v32/frozen 87 (SPEC-P-demo-batch-4 section 5).\n\n'
        "Derived from tools/judge_v86_product_four_arms.py (bound by F4-86's evidence; not edited).  The differences are a\n"
        "closed list: this paragraph and the line above it; the identity module v86 -> v87; the identity messages.\n"
        "Everything below is that file's text.\n\n",
        [("from v86_four_arms_identity import", "from v87_four_arms_identity import", 1),
         ("'shell generation is not frozen 86'", "'shell generation is not frozen 87'", 1),
         ("'product page is not the generation-86 page'", "'product page is not the generation-87 page'", 1),
         ("'profile is not v31 ABI6'", "'profile is not v32 ABI6'", 1)]),
    ("run_v86_f3_clipboard.py", "run_v87_f3_clipboard.py"): (
        '"""F3-87 (SPEC-P-demo-batch-4 section 5): the bound product-path runner on frozen generation 87, with the engine\'s\n'
        "copied text read from the clipboard, one press per format arm, and the clear's toast waited for (finding 178).\n\n"
        "Derived from tools/run_v86_f3_clipboard.py (bound by F3-86's evidence; not edited).  The differences are a closed\n"
        "list: this paragraph and the two lines above it; the shell manifest rebound to generation 87 (the `used` value and\n"
        "its refusal message); the module name; REPLACEMENTS gains finding 178's wait on the toast, the same edit as\n"
        "findings/evidence/demo-batch-3/f3-86/diag_clear_wait.py.  Everything below is that file's text.\n\n",
        [("NAME = 'run_v86_f3_clipboard'", "NAME = 'run_v87_f3_clipboard'", 1),
         ("'used': 'e2/editor-shell-v2-bundle-v86.json'", "'used': 'e2/editor-shell-v2-bundle-v87.json'", 1),
         ("the generation-86 override", "the generation-87 override", 1),
         (SINGLE, CLEAR_WAIT, 1)]),
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
