#!/usr/bin/env python3
"""Derive the generation-86 tools from the generation-85 ones (SPEC-P-demo-batch-3 section 3): a closed list of replacements per
file, each with the count it must match.  The parents are not edited.  Generation 86 moves the profile to e2-editor-v31, a real link:
all four pins and the archive change, unlike generation 85, which kept the wasm and the loader.  The F3 reader is not derived:
read_v83_f3_equal.py takes --baseline.

  python3 -I derive_v86_tools.py        (after generation 86 is frozen)
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "wasm_sdk_probe/tools"
MANIFEST = REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v86.json"
OLD = json.loads((REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v85.json").read_text(encoding="utf-8"))
PAGE_85 = "0fa5662e11704dab6ba0f6579bbb400ea849ebe4f31c8898d850f9dc2bcd0bfa"
PAGE_86 = hashlib.sha256((REPO / "wasm_sdk_probe/web/e2-editor-app.js").read_bytes()).hexdigest()
BUNDLE_85 = hashlib.sha256((REPO / "wasm_sdk_probe/e2/editor-shell-v2-bundle-v85.json").read_bytes()).hexdigest()
BUNDLE_86 = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
DIGEST_85 = OLD["bundleSha256"]
DIGEST_86 = json.loads(MANIFEST.read_text(encoding="utf-8"))["bundleSha256"]
PINS = {"probe.wasm": ("e61e5890bac5c1d24144beec6e5907c225b1637e5dc306510deaf5c5e3726b12", "809893a97c9d2d19e60f9aaee14bf49c201c6d4f0c6210abc46ea9e797ab13bf"),
        "probe.js": ("0ca2665cba3b444cdebb5dd152600cba2991d9979f82833a81241a5f8ec0ce83", "f557d76c30b3ecf8fc658a83d48a5a95a4a4632ca6f68d59581c2729280f3abc"),
        "sdk-worker.js": ("464d129c044231c516c666487db32e78f33d3f6393d2afdcc089d36bb0f0fe93", "54352fad3f5434162512d20e64e655a9cce789629495a74cbbe4c8a34e41637e"),
        "sdk-manifest.json": ("9616efbaab4200bfb2de3c3570b2ba7e726c32c2c5667ac9ed0c822c403b00ac", "faa7bdb97c212c5039efbaffa21fc6d532033d60f12ce6960ed9450fe00adb7d")}

PLAN = {
    ("v85_four_arms_identity.py", "v86_four_arms_identity.py"): (
        '"""SPEC-P-demo-batch-3 section 3: what names the build under test for the generation-86 four-arm run.\n\n'
        "Derived from tools/v85_four_arms_identity.py (bound by F4-85's evidence; not edited) by\n"
        "findings/evidence/demo-batch-3/derive/derive_v86_tools.py.  The differences are a closed list: this paragraph and the\n"
        "line above it; PROFILE e2-editor-v30 -> e2-editor-v31; the four ARTIFACT_PINS (a real link: probe.wasm 809893a9,\n"
        "probe.js f557d76c, sdk-worker.js 54352fad, sdk-manifest.json faa7bdb9); ARCHIVED_PROFILE -> the v31 archive; the page,\n"
        "the shell digest and the bundle file (generation 86); 85 -> 86 and v30 -> v31 in the messages and in the record.\n"
        "Everything below is that file's text.\n\n",
        [(f"PAGE_SHA256 = '{PAGE_85}'", f"PAGE_SHA256 = '{PAGE_86}'", 1),
         (f"CANDIDATE_SHELL_DIGEST = '{DIGEST_85}'", f"CANDIDATE_SHELL_DIGEST = '{DIGEST_86}'", 1),
         ("BUNDLE = 'e2/editor-shell-v2-bundle-v85.json'", "BUNDLE = 'e2/editor-shell-v2-bundle-v86.json'", 1),
         (f"BUNDLE_FILE_SHA256 = '{BUNDLE_85}'", f"BUNDLE_FILE_SHA256 = '{BUNDLE_86}'", 1),
         ("PROFILE = 'e2-editor-v30'", "PROFILE = 'e2-editor-v31'", 1)]
        + [(f"'{name}': '{old}'", f"'{name}': '{new}'", 1) for name, (old, new) in PINS.items()]
        + [("ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v30-e61e5890-worker-464d129c'",
            "ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v31-809893a9-worker-54352fad'", 1),
           ("equal to frozen generation 85.", "equal to frozen generation 86.", 1),
           ("'shell digest is not generation 85: '", "'shell digest is not generation 86: '", 1),
           ("'generation 85 manifest differs: '", "'generation 86 manifest differs: '", 1),
           ("'live shell is not frozen generation 85'", "'live shell is not frozen generation 86'", 1),
           ("'page is not the generation-85 page'", "'page is not the generation-86 page'", 1),
           ("'shell': {'generation': 85,", "'shell': {'generation': 86,", 1),
           ("'v30 profile/archive identity differs: '", "'v31 profile/archive identity differs: '", 1),
           ("'v30 ABI/profile/typedInsert differs'", "'v31 ABI/profile/typedInsert differs'", 1)]),
    ("run_v85_four_arms.py", "run_v86_four_arms.py"): (
        '"""SPEC-P-demo-batch-3 section 3: the unchanged product-path suite with frozen-86 identity, then its four arms.\n\n'
        "Derived from tools/run_v85_four_arms.py (bound by F4-85's evidence; not edited).  The differences are a closed list:\n"
        "this paragraph and the line above it; generation 85 -> 86 (default manifest, twice); the identity and reader modules\n"
        "v85 -> v86; the lock name.  Everything below is that file's text.\n\n",
        [("'e2/editor-shell-v2-bundle-v85.json'", "'e2/editor-shell-v2-bundle-v86.json'", 2),
         ("import judge_v85_product_four_arms as reader", "import judge_v86_product_four_arms as reader", 2),
         ("from v85_four_arms_identity import PROFILE", "from v86_four_arms_identity import PROFILE", 1),
         ("common.browser_lock('v85-four-arms')", "common.browser_lock('v86-four-arms')", 1)]),
    ("judge_v85_product_four_arms.py", "judge_v86_product_four_arms.py"): (
        '"""Four-arm reader on v31/frozen 86 (SPEC-P-demo-batch-3 section 3).\n\n'
        "Derived from tools/judge_v85_product_four_arms.py (bound by F4-85's evidence; not edited).  The differences are a\n"
        "closed list: this paragraph and the line above it; the identity module v85 -> v86; the identity messages.\n"
        "Everything below is that file's text.\n\n",
        [("from v85_four_arms_identity import", "from v86_four_arms_identity import", 1),
         ("'shell generation is not frozen 85'", "'shell generation is not frozen 86'", 1),
         ("'product page is not the generation-85 page'", "'product page is not the generation-86 page'", 1),
         ("'profile is not v30 ABI6'", "'profile is not v31 ABI6'", 1)]),
    ("run_v85_f3_clipboard.py", "run_v86_f3_clipboard.py"): (
        '"""F3-86 (SPEC-P-demo-batch-3 section 3): the bound product-path runner on frozen generation 86, with the engine\'s\n'
        "copied text read from the clipboard, and one press per format arm (finding 178).\n\n"
        "Derived from tools/run_v85_f3_clipboard.py (bound by F3-85's evidence; not edited).  The differences are a closed\n"
        "list: this paragraph and the two lines above it; the shell manifest rebound to generation 86 (the `used` value and\n"
        "its refusal message); the module name.  Everything below is that file's text.\n\n",
        [("NAME = 'run_v85_f3_clipboard'", "NAME = 'run_v86_f3_clipboard'", 1),
         ("'used': 'e2/editor-shell-v2-bundle-v85.json'", "'used': 'e2/editor-shell-v2-bundle-v86.json'", 1),
         ("the generation-85 override", "the generation-86 override", 1)]),
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
