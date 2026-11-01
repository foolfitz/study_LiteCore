#!/usr/bin/env python3
"""Derive the generation-83 tools from the generation-82 ones (SPEC-M3-v29-tick-pacing section 6 T3, section 11): a closed
list of replacements per file, each with the count it must match; a derivation paragraph is put in front of each parent's
docstring.  The parents are not edited.  Re-running rewrites the derived files.

  python3 -I derive_v83_tools.py
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "wasm_sdk_probe/tools"
BUNDLE_FILE = "98371d7f7479021dc2b859bf78db796571d7070b8509548edf7db977bc214174"
BUNDLE_82 = "da4e595d859c8659145b80721007be124ad17d4b6517145630a1f7edfed3a7f3"
PAGE_82 = "3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a"
PAGE_83 = "022d0cd0b5152f1ee9cabc74b10f5af2eb55935299228119a419ab717957759b"
DIGEST_82 = "a02673fa0dd34b6b0c9852d0428970368e6322342d83bc08d3d6967ea568ee52"
DIGEST_83 = "607b280d8ce86b04b471ad21a84f8c96eadb405a50ef1eb14ad5b0d91324a704"

V82_PINS = """    'probe.wasm': '13f674e498a56c8af68e1caaba36e861f9cb4ec83dd7ab865a9e4106cbd0b3bb',
    'probe.js': 'c5336b96c3a73deb803e5704324f44ed4ed2bdbfee685e84b3cef3ca79db01df',
    'sdk-worker.js': 'a5df83dbd0bd4df6b67b81d000da141910b76252fbf2bb8636d9a312edfffcba',
    'sdk-manifest.json': '7b4eb4743764a30bb38f9cdaa4be6bd1d7f6054d8fe43f609f45220fa6770db8'}"""
V83_PINS = """    'probe.wasm': 'e61e5890bac5c1d24144beec6e5907c225b1637e5dc306510deaf5c5e3726b12',
    'probe.js': '0ca2665cba3b444cdebb5dd152600cba2991d9979f82833a81241a5f8ec0ce83',
    'sdk-worker.js': 'a5df83dbd0bd4df6b67b81d000da141910b76252fbf2bb8636d9a312edfffcba',
    'sdk-manifest.json': 'a0352c83b312b4f3988886936228985bea83aafa6cd0a49ce6af56f519d3432b'}"""

PLAN = {
    ("v82_four_arms_identity.py", "v83_four_arms_identity.py"): (
        '"""SPEC-M3-v29-tick-pacing section 6 T3: what names the build under test for the generation-83 four-arm run.\n\n'
        "Derived from tools/v82_four_arms_identity.py (bound by F4-82's evidence; not edited).  The differences are a\n"
        "closed list: this paragraph and the line above it; PROFILE e2-editor-v28 -> e2-editor-v29; ARTIFACT_PINS -> the\n"
        "v29 link's four (probe.wasm e61e5890, probe.js 0ca2665c, sdk-worker.js a5df83db, the same bytes as v28's,\n"
        "sdk-manifest.json a0352c83); ARCHIVED_PROFILE -> the v29 archive; the page (022d0cd0), the shell digest and the\n"
        "bundle file (generation 83, v29-177/freeze-83/); 82 -> 83 and v28 -> v29 in the messages, in the record and in\n"
        "shell()'s docstring.  Everything below is that file's text from its own derivation note on.\n\n",
        [("PROFILE = 'e2-editor-v28'", "PROFILE = 'e2-editor-v29'", 1),
         (f"PAGE_SHA256 = '{PAGE_82}'", f"PAGE_SHA256 = '{PAGE_83}'", 1),
         (f"CANDIDATE_SHELL_DIGEST = '{DIGEST_82}'", f"CANDIDATE_SHELL_DIGEST = '{DIGEST_83}'", 1),
         ("BUNDLE = 'e2/editor-shell-v2-bundle-v82.json'", "BUNDLE = 'e2/editor-shell-v2-bundle-v83.json'", 1),
         (f"BUNDLE_FILE_SHA256 = '{BUNDLE_82}'", f"BUNDLE_FILE_SHA256 = '{BUNDLE_FILE}'", 1),
         (V82_PINS, V83_PINS, 1),
         ("build/archive/e2-editor-v28-13f674e4-worker-a5df83db", "build/archive/e2-editor-v29-e61e5890-worker-a5df83db", 1),
         ("equal to frozen generation 82.", "equal to frozen generation 83.", 1),
         ("'shell digest is not generation 82: '", "'shell digest is not generation 83: '", 1),
         ("'generation 82 manifest differs: '", "'generation 83 manifest differs: '", 1),
         ("'live shell is not frozen generation 82'", "'live shell is not frozen generation 83'", 1),
         ("'page is not the generation-82 page'", "'page is not the generation-83 page'", 1),
         ("'v28 profile/archive identity differs: '", "'v29 profile/archive identity differs: '", 1),
         ("'v28 ABI/profile/typedInsert differs'", "'v29 ABI/profile/typedInsert differs'", 1),
         ("'shell': {'generation': 82,", "'shell': {'generation': 83,", 1)]),
    ("run_v82_four_arms.py", "run_v83_four_arms.py"): (
        '"""SPEC-M3-v29-tick-pacing section 6 T3: the unchanged product-path suite with frozen-83 identity, then its four arms.\n\n'
        "Derived from tools/run_v82_four_arms.py (bound by F4-82's evidence; not edited).  The differences are a closed\n"
        "list: this paragraph and the line above it; generation 82 -> 83 (default manifest, twice); the identity and\n"
        "reader modules v82 -> v83 (tools/v83_four_arms_identity.py, tools/judge_v83_product_four_arms.py); the lock\n"
        "name.  Everything below is run_v82_four_arms.py's text from its own derivation note on.\n\n",
        [("'e2/editor-shell-v2-bundle-v82.json'", "'e2/editor-shell-v2-bundle-v83.json'", 2),
         ("import judge_v82_product_four_arms as reader", "import judge_v83_product_four_arms as reader", 2),
         ("from v82_four_arms_identity import PROFILE", "from v83_four_arms_identity import PROFILE", 1),
         ("common.browser_lock('v82-four-arms')", "common.browser_lock('v83-four-arms')", 1)]),
    ("judge_v82_product_four_arms.py", "judge_v83_product_four_arms.py"): (
        '"""Four-arm reader on v29/frozen 83 (SPEC-M3-v29-tick-pacing section 6 T3).\n\n'
        "Derived from tools/judge_v82_product_four_arms.py (bound by F4-82's evidence; not edited).  The differences\n"
        "are a closed list: this paragraph and the line above it; the identity module v82 -> v83; the four identity\n"
        "messages (frozen 83, v29 ABI6, frozen v29, the generation-83 page).  Everything below is that file's text\n"
        "from its own derivation note on.\n\n",
        [("from v82_four_arms_identity import", "from v83_four_arms_identity import", 1),
         ("'shell generation is not frozen 82'", "'shell generation is not frozen 83'", 1),
         ("'profile is not v28 ABI6'", "'profile is not v29 ABI6'", 1),
         ("'profile artifacts are not frozen v28'", "'profile artifacts are not frozen v29'", 1),
         ("'product page is not the generation-82 page'", "'product page is not the generation-83 page'", 1)]),
    ("run_v82_f3_clipboard.py", "run_v83_f3_clipboard.py"): (
        '"""F3-83 (SPEC-M3-v29-tick-pacing section 6 T3): the bound product-path runner on frozen generation 83, with the\n'
        "engine's copied text read from the clipboard.\n\n"
        "Derived from tools/run_v82_f3_clipboard.py (bound by F3-82's evidence, findings/evidence/v28-083/f3-82/; not\n"
        "edited).  The differences are a closed list: this paragraph and the two lines above it; the shell manifest\n"
        "rebound to generation 83 instead of 82 (the `used` value and its refusal message); the module name.\n"
        "BOUND_SHA256, REPLACEMENTS and `_clipboard_text` are unchanged.  Everything below is that file's text.\n\n",
        [("NAME = 'run_v82_f3_clipboard'", "NAME = 'run_v83_f3_clipboard'", 1),
         ("'used': 'e2/editor-shell-v2-bundle-v82.json'", "'used': 'e2/editor-shell-v2-bundle-v83.json'", 1),
         ("the generation-82 override", "the generation-83 override", 1)]),
    ("read_v82_f3_equal.py", "read_v83_f3_equal.py"): (
        '"""SPEC-M3-v29-tick-pacing section 6 T3, F3-83 reading 2: every check\'s outcome equals F3-82\'s, with NO declared move\n'
        "(v29 moves timing, not behaviour; any moved cell, to PASS included, is a finding: stop and look) -- and reading 1\n"
        "(tools/read_v25_f3.py, unchanged, imported) is F3_RED with exactly F3-82's four problems.\n\n"
        "Derived from tools/read_v82_f3_equal.py (bound by F3-82's evidence; not edited).  The differences are a closed list:\n"
        "this paragraph and the two lines above it; BASELINE = F3-82 (findings/evidence/v28-083/f3-82/run-01); the names\n"
        "v82 -> v83, f381 -> f382, F3-81 -> F3-82, F3_82 -> F3_83 in the code, the argument and the verdict.  Everything\n"
        "below in this docstring is that file's text.\n\n",
        [('"findings/evidence/v27-176/f3-81/run-01"', '"findings/evidence/v28-083/f3-82/run-01"', 1),
         ("F3_82", "F3_83", 8), ("v82", "v83", 22), ("f381", "f382", 1), ("f3-81", "f3-82", 5), ("F3-81", "F3-82", 1),
         ("AsF381", "AsF382", 2)]),
    ("run_k_0244_merge.py", "run_v83_merge.py"): (
        '"""SPEC-M3-v29-tick-pacing section 6 T3: the K wrapper over the unchanged merge runner, on v29 and generation 83.\n\n'
        "Derived from tools/run_k_0244_merge.py (it belongs to SPEC-M3-K-0.2.44 and is not edited; a new K spec re-values it).\n"
        "The differences are a closed list: this paragraph and the line above it; INVENTORY -> the binding computed for v29\n"
        "(findings/evidence/v29-177/t3/merge/binding.json, same shape as the K inventory's `proposedMergeBinding` key);\n"
        "MANIFEST and MANIFEST_SHA256 -> generation 83; PROFILE -> e2-editor-v29; 82 -> 83 in one message.  The keying is the\n"
        "same module, unchanged.  Everything below is that file's text from its own docstring on.\n\n",
        [('INVENTORY = PROJECT.parent / "findings/evidence/k-0.2.44/k-binding-inventory.json"',
          'INVENTORY = PROJECT.parent / "findings/evidence/v29-177/t3/merge/binding.json"', 1),
         ('MANIFEST = "e2/editor-shell-v2-bundle-v82.json"', 'MANIFEST = "e2/editor-shell-v2-bundle-v83.json"', 1),
         (f'MANIFEST_SHA256 = "{BUNDLE_82}"', f'MANIFEST_SHA256 = "{BUNDLE_FILE}"', 1),
         ('PROFILE = "e2-editor-v28"', 'PROFILE = "e2-editor-v29"', 1),
         ('"generation 82 manifest differs"', '"generation 83 manifest differs"', 1)]),
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
