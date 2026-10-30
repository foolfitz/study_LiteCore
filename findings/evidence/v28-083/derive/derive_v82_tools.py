#!/usr/bin/env python3
"""Derive the generation-82 F4/F3 tools from the generation-81 ones (SPEC-M3-v28-last-line-fallback 7.3 F3-82,
F4-82): a closed list of replacements per file, each with the count it must match; a derivation paragraph is put
in front of each parent's docstring.  The parents are not edited.  Re-running rewrites the four derived files.

  python3 -I derive_v82_tools.py BUNDLE_FILE_SHA256
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[4] / "wasm_sdk_probe/tools"
bundle_file = sys.argv[1]
assert len(bundle_file) == 64

V81_PINS = """    'probe.wasm': 'c089dfd699d646e373113fa8437d05e01e150987302e9851543a31debc7ffb3c',
    'probe.js': '0a73eb5ae83e42d6ce799b7ba32d6a4f821b184c66eff2053be7a83c1a4e6526',
    'sdk-worker.js': '8152448ab83bc323edfa6982a1db08c4367b15b4c99978eeb1b39b3ef41a669d',
    'sdk-manifest.json': 'd5d076399b921d2749fcb4ded45aa1a7613759a330c42e307a82dce6fbd4e9fe'}"""
V82_PINS = """    'probe.wasm': '13f674e498a56c8af68e1caaba36e861f9cb4ec83dd7ab865a9e4106cbd0b3bb',
    'probe.js': 'c5336b96c3a73deb803e5704324f44ed4ed2bdbfee685e84b3cef3ca79db01df',
    'sdk-worker.js': 'a5df83dbd0bd4df6b67b81d000da141910b76252fbf2bb8636d9a312edfffcba',
    'sdk-manifest.json': '7b4eb4743764a30bb38f9cdaa4be6bd1d7f6054d8fe43f609f45220fa6770db8'}"""

PLAN = {
    ("v81_four_arms_identity.py", "v82_four_arms_identity.py"): (
        '"""SPEC-M3-v28-last-line-fallback 7.3 F4-82: what names the build under test for the generation-82 four-arm run.\n\n'
        "Derived from tools/v81_four_arms_identity.py (bound by F4-81's evidence; not edited).  The differences are a\n"
        "closed list (spec 7.3): this paragraph and the line above it; PROFILE e2-editor-v27 -> e2-editor-v28; ARTIFACT_PINS\n"
        "-> the v28 link's four (probe.wasm 13f674e4, probe.js c5336b96, sdk-worker.js a5df83db, sdk-manifest.json\n"
        "7b4eb474); ARCHIVED_PROFILE -> the v28 archive; the page (3b0a2ebb, generation 82), the shell digest and the\n"
        "bundle file (generation 82, v28-083/freeze-82/); 81 -> 82 and v27 -> v28 in the messages, in the record and in\n"
        "shell()'s docstring.  Generation 82 also differs from 81 in the client; it is bound by the shell digest, as every\n"
        "included module is.  Everything below is that file's text from its own derivation note on.\n\n",
        [("PROFILE = 'e2-editor-v27'", "PROFILE = 'e2-editor-v28'", 1),
         ("PAGE_SHA256 = 'b63d8ee53659c8b6216ecfc6ddaf4e3ef909f99f96b5975204ff31039816b1c7'",
          "PAGE_SHA256 = '3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a'", 1),
         ("CANDIDATE_SHELL_DIGEST = '6eb7ca108ea77c4ad735f97344ee9befa76a2c3c76fb7a6bce2f6da1bdc5c094'",
          "CANDIDATE_SHELL_DIGEST = 'a02673fa0dd34b6b0c9852d0428970368e6322342d83bc08d3d6967ea568ee52'", 1),
         ("BUNDLE = 'e2/editor-shell-v2-bundle-v81.json'", "BUNDLE = 'e2/editor-shell-v2-bundle-v82.json'", 1),
         ("BUNDLE_FILE_SHA256 = '91f180232b33f2addb410cae25834561780c3b5344d021fed53e0e5b31fffbb1'",
          f"BUNDLE_FILE_SHA256 = '{bundle_file}'", 1),
         (V81_PINS, V82_PINS, 1),
         ("build/archive/e2-editor-v27-c089dfd6-worker-8152448a", "build/archive/e2-editor-v28-13f674e4-worker-a5df83db", 1),
         ("equal to frozen generation 81.", "equal to frozen generation 82.", 1),
         ("'shell digest is not generation 81: '", "'shell digest is not generation 82: '", 1),
         ("'generation 81 manifest differs: '", "'generation 82 manifest differs: '", 1),
         ("'live shell is not frozen generation 81'", "'live shell is not frozen generation 82'", 1),
         ("'page is not the generation-81 page'", "'page is not the generation-82 page'", 1),
         ("'v27 profile/archive identity differs: '", "'v28 profile/archive identity differs: '", 1),
         ("'v27 ABI/profile/typedInsert differs'", "'v28 ABI/profile/typedInsert differs'", 1),
         ("'shell': {'generation': 81,", "'shell': {'generation': 82,", 1)]),
    ("run_v81_four_arms.py", "run_v82_four_arms.py"): (
        '"""SPEC-M3-v28-last-line-fallback 7.3 F4-82: the unchanged product-path suite with frozen-82 identity, then its four arms.\n\n'
        "Derived from tools/run_v81_four_arms.py (bound by F4-81's evidence; not edited).  The differences are a closed\n"
        "list: this paragraph and the line above it; generation 81 -> 82 (default manifest, twice); the identity and\n"
        "reader modules v81 -> v82 (tools/v82_four_arms_identity.py, tools/judge_v82_product_four_arms.py); the lock\n"
        "name.  Everything below is run_v81_four_arms.py's text from its own derivation note on.\n\n",
        [("'e2/editor-shell-v2-bundle-v81.json'", "'e2/editor-shell-v2-bundle-v82.json'", 2),
         ("import judge_v81_product_four_arms as reader", "import judge_v82_product_four_arms as reader", 2),
         ("from v81_four_arms_identity import PROFILE", "from v82_four_arms_identity import PROFILE", 1),
         ("common.browser_lock('v81-four-arms')", "common.browser_lock('v82-four-arms')", 1)]),
    ("judge_v81_product_four_arms.py", "judge_v82_product_four_arms.py"): (
        '"""Four-arm reader on v28/frozen 82 (SPEC-M3-v28-last-line-fallback 7.3 F4-82).\n\n'
        "Derived from tools/judge_v81_product_four_arms.py (bound by F4-81's evidence; not edited).  The differences\n"
        "are a closed list: this paragraph and the line above it; the identity module v81 -> v82; the four identity\n"
        "messages (frozen 82, v28 ABI6, frozen v28, the generation-82 page).  Everything below is that file's text\n"
        "from its own derivation note on.\n\n",
        [("from v81_four_arms_identity import", "from v82_four_arms_identity import", 1),
         ("'shell generation is not frozen 81'", "'shell generation is not frozen 82'", 1),
         ("'profile is not v27 ABI6'", "'profile is not v28 ABI6'", 1),
         ("'profile artifacts are not frozen v27'", "'profile artifacts are not frozen v28'", 1),
         ("'product page is not the generation-81 page'", "'product page is not the generation-82 page'", 1)]),
    ("run_v81_f3_clipboard.py", "run_v82_f3_clipboard.py"): (
        '"""F3-82 (SPEC-M3-v28-last-line-fallback 7.3): the bound product-path runner on frozen generation 82, with the\n'
        "engine's copied text read from the clipboard.\n\n"
        "Derived from tools/run_v81_f3_clipboard.py (bound by F3-81's evidence, findings/evidence/v27-176/f3-81/; not\n"
        "edited).  The differences are a closed list: this paragraph and the two lines above it; the shell manifest\n"
        "rebound to generation 82 instead of 81 (the `used` value and its refusal message); the module name.\n"
        "BOUND_SHA256, REPLACEMENTS and `_clipboard_text` are unchanged.  Everything below is that file's text.\n\n",
        [("NAME = 'run_v81_f3_clipboard'", "NAME = 'run_v82_f3_clipboard'", 1),
         ("'used': 'e2/editor-shell-v2-bundle-v81.json'", "'used': 'e2/editor-shell-v2-bundle-v82.json'", 1),
         ("the generation-81 override", "the generation-82 override", 1)]),
}

for (parent, child), (header, replacements) in PLAN.items():
    text = (TOOLS / parent).read_text(encoding="utf-8")
    for old, new, count in replacements:
        got = text.count(old)
        if got != count:
            raise SystemExit(f"{parent}: {old[:60]!r} occurs {got} times, expected {count}")
        text = text.replace(old, new)
    # put the derivation paragraph in front of the parent's docstring
    shebang = "#!/usr/bin/env python3\n" if text.startswith("#!/usr/bin/env python3\n") else ""
    body = text[len(shebang):]
    if not body.startswith('"""'):
        raise SystemExit(f"{parent}: no docstring at the top")
    text = shebang + header + body[3:]
    (TOOLS / child).write_text(text, encoding="utf-8")
    print(child, "written")
