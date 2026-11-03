#!/usr/bin/env python3
"""Derive the generation-89 tools from the generation-88 ones (SPEC-P-ms-formats step 4): a closed list of replacements per file, each with
the count it must match.  The parents are not edited.  Generation 89 moves the profile to e2-editor-v33, a real link: all four pins and the
archive change (demo-batch-4/derive/derive_v87_tools.py is the form, the last profile move).  The F3 reader is not derived:
read_v83_f3_equal.py takes --baseline.

  python3 -I derive_v89_tools.py        (after e2-editor-v33 is frozen, the page cut over and generation 89 frozen)
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "wasm_sdk_probe/tools"
MANIFEST = REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v89.json"
OLD = json.loads((REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v88.json").read_text(encoding="utf-8"))
PAGE_88 = "3d122cb731c6af2ad2a7456eed359981a65ade6b19064dce83037c759670647c"
PAGE_89 = hashlib.sha256((REPO / "wasm_sdk_probe/web/e2-editor-app.js").read_bytes()).hexdigest()
BUNDLE_88 = hashlib.sha256((REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v88.json").read_bytes()).hexdigest()
BUNDLE_89 = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
DIGEST_88 = OLD["bundleSha256"]
DIGEST_89 = json.loads(MANIFEST.read_text(encoding="utf-8"))["bundleSha256"]
PINS = {"probe.wasm": ("54e500931de0ee28fe5e6c9916adfef48ec7f81ae71cd432ddb1c6bc02db46fa", "444519df2a779a44352ff5c6faf07825bab6abcc9d086a1cc2ddab14ac0d5952"),
        "probe.js": ("a261f4c1fc72a251ca2c611e39232de87e6a6cb40eed53e729ea503bc3604c36", "e94122223cf0c154bccd7cbb0b9cd6657c63500cb4d7dfbddabdd24bd3e5cf01"),
        "sdk-worker.js": ("c394302c589baff3b40ff67a7579e07cf53fc7447dd3f04b26ff9c827280ff36", "b35359ce4c7fcd6b55f0ee3b8e1a733ed6ffa223284b49e2c71ecc0ec9f8d0b8"),
        "sdk-manifest.json": ("7616e19207e53fd773ec9debd6f75fd3fa10f889746855d6934fd7e9ccd916cd", "1a189dd294d4971c6d4e8569941eaa6644ea663e5c9639d5e4d44b2238c470ba")}

PLAN = {
    ("v88_four_arms_identity.py", "v89_four_arms_identity.py"): (
        '"""SPEC-P-ms-formats step 4: what names the build under test for the generation-89 four-arm run.\n\n'
        "Derived from tools/v88_four_arms_identity.py (bound by F4-88's evidence; not edited) by\n"
        "findings/evidence/ms-formats/derive/derive_v89_tools.py.  The differences are a closed list: this paragraph and the\n"
        "line above it; PROFILE e2-editor-v32 -> e2-editor-v33; the four ARTIFACT_PINS (a real link: probe.wasm 444519df,\n"
        "probe.js e9412222, sdk-worker.js b35359ce, sdk-manifest.json 1a189dd2); ARCHIVED_PROFILE -> the v33 archive; the page,\n"
        "the shell digest and the bundle file (generation 89); 88 -> 89 and v32 -> v33 in the messages and in the record.\n"
        "Everything below is that file's text.\n\n",
        [(f"PAGE_SHA256 = '{PAGE_88}'", f"PAGE_SHA256 = '{PAGE_89}'", 1),
         (f"CANDIDATE_SHELL_DIGEST = '{DIGEST_88}'", f"CANDIDATE_SHELL_DIGEST = '{DIGEST_89}'", 1),
         ("BUNDLE = 'e2/editor-shell-v2-bundle-v88.json'", "BUNDLE = 'e2/editor-shell-v2-bundle-v89.json'", 1),
         (f"BUNDLE_FILE_SHA256 = '{BUNDLE_88}'", f"BUNDLE_FILE_SHA256 = '{BUNDLE_89}'", 1),
         ("PROFILE = 'e2-editor-v32'", "PROFILE = 'e2-editor-v33'", 1)]
        + [(f"'{name}': '{old}'", f"'{name}': '{new}'", 1) for name, (old, new) in PINS.items()]
        + [("ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v32-54e50093-worker-c394302c'",
            "ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v33-444519df-worker-b35359ce'", 1),
           ("equal to frozen generation 88.", "equal to frozen generation 89.", 1),
           ("'shell digest is not generation 88: '", "'shell digest is not generation 89: '", 1),
           ("'generation 88 manifest differs: '", "'generation 89 manifest differs: '", 1),
           ("'live shell is not frozen generation 88'", "'live shell is not frozen generation 89'", 1),
           ("'page is not the generation-88 page'", "'page is not the generation-89 page'", 1),
           ("'shell': {'generation': 88,", "'shell': {'generation': 89,", 1),
           ("'v32 profile/archive identity differs: '", "'v33 profile/archive identity differs: '", 1),
           ("'v32 ABI/profile/typedInsert differs'", "'v33 ABI/profile/typedInsert differs'", 1)]),
    ("run_v88_four_arms.py", "run_v89_four_arms.py"): (
        '"""SPEC-P-ms-formats step 4: the unchanged product-path suite with frozen-89 identity, then its four arms.\n\n'
        "Derived from tools/run_v88_four_arms.py (bound by F4-88's evidence; not edited).  The differences are a closed list:\n"
        "this paragraph and the line above it; generation 88 -> 89 (default manifest, twice); the identity and reader modules\n"
        "v88 -> v89; the lock name.  Everything below is that file's text.\n\n",
        [("'e2/editor-shell-v2-bundle-v88.json'", "'e2/editor-shell-v2-bundle-v89.json'", 2),
         ("import judge_v88_product_four_arms as reader", "import judge_v89_product_four_arms as reader", 2),
         ("from v88_four_arms_identity import PROFILE", "from v89_four_arms_identity import PROFILE", 1),
         ("common.browser_lock('v88-four-arms')", "common.browser_lock('v89-four-arms')", 1)]),
    ("judge_v88_product_four_arms.py", "judge_v89_product_four_arms.py"): (
        '"""Four-arm reader on v33/frozen 89 (SPEC-P-ms-formats step 4).\n\n'
        "Derived from tools/judge_v88_product_four_arms.py (bound by F4-88's evidence; not edited).  The differences are a\n"
        "closed list: this paragraph and the line above it; the identity module v88 -> v89; the identity messages.\n"
        "Everything below is that file's text.\n\n",
        [("from v88_four_arms_identity import", "from v89_four_arms_identity import", 1),
         ("'shell generation is not frozen 88'", "'shell generation is not frozen 89'", 1),
         ("'product page is not the generation-88 page'", "'product page is not the generation-89 page'", 1),
         ("'profile is not v32 ABI6'", "'profile is not v33 ABI6'", 1)]),
    ("run_v88_f3_clipboard.py", "run_v89_f3_clipboard.py"): (
        '"""F3-89 (SPEC-P-ms-formats step 4): the bound product-path runner on frozen generation 89, with the engine\'s copied text read\n'
        "from the clipboard, one press per format arm, and the clear's toast waited for (finding 178).\n\n"
        "Derived from tools/run_v88_f3_clipboard.py (bound by F3-88's evidence; not edited).  The differences are a closed\n"
        "list: this paragraph and the two lines above it; the shell manifest rebound to generation 89 (the `used` value and\n"
        "its refusal message); the module name.  Everything below is that file's text.\n\n",
        [("NAME = 'run_v88_f3_clipboard'", "NAME = 'run_v89_f3_clipboard'", 1),
         ("'used': 'e2/editor-shell-v2-bundle-v88.json'", "'used': 'e2/editor-shell-v2-bundle-v89.json'", 1),
         ("the generation-88 override", "the generation-89 override", 1)]),
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
