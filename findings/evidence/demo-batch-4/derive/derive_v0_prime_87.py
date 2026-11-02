#!/usr/bin/env python3
"""Derive V0' for generation 87 from ../../demo-batch-3/v0-86/run_v0_prime.py (its evidence binds it; not edited): a closed list of replacements,
each with the count it must match.  python3 -I derive_v0_prime_87.py"""
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PARENT = REPO / "findings/evidence/demo-batch-3/v0-86/run_v0_prime.py"
CHILD = REPO / "findings/evidence/demo-batch-4/v0-87/run_v0_prime.py"
PAGE_86 = "50127676e87df9c8ef33a3f8bf7780d0692f1f65b253df50dfa95ba4568fbe4b"
HTML_86 = "40bcd4716991d71e783b19c52a5d97a4e4c74f1c57e54b98b74d21fcbb66c43f"
CLIENT_86 = "1c961f3bc706257ebfe57287cf810256c5a430d1fb87850df14480c557883aad"
NARROW_86 = "ab33027541448229e96f1c0f787da15ce8f9e0d1d811736616fc408cd687df0e"
SESSION_86 = "5fce8eec0c9516bcf8855ab8b8176f1090c617189326b9cdd399409223dcf388"
COMMIT = "f3204745e"   # the last commit whose page sources are generation 86's: 3daa0c30f moved them ahead for the batch 4 controls
sha = lambda path: hashlib.sha256((REPO / "wasm_sdk_probe" / path).read_bytes()).hexdigest()

DOC = '''"""V0' for generation 87 (SPEC-P-demo-batch-4 section 5): the carried-over counts and every earlier generation's readings
still re-read.

Derived from ../../demo-batch-3/v0-86/run_v0_prime.py (bound by its own committed result; not edited) by ../derive/derive_v0_prime_87.py.
The differences are a closed list: this docstring; a tenth stage, v86 (page, HTML and the three shell modules of generation 86 from git
f3204745e), which re-reads F4-86 with `judge_v86_product_four_arms.py` alongside the file readers; F4-86's reader recorded among the
live reds; the pre-check and the put-back target generation 87 and its bundle line.

Everything else as its parent's: the four-arm readers bind the live shell digest and are NOT_ESTABLISHED on the generation-87 tree
by construction, and are re-read in their stage, byte-identical with the argv of the committed result; put back in `finally` with
`git checkout HEAD --` and `make e2-c-assets`.  Writes only into this directory.  Must not run while anything serves dist/.

Verdict V0_PRIME_HOLDS iff every re-read is byte-identical with its expected exit (0 unless EXPECTED_EXIT says otherwise), every
four-arm live read is a red (nonzero exit), every restore and the put-back hold.
"""'''

V87 = (f"V87 = {{PAGE: '{sha('web/e2-editor-app.js')}',\n"
       f"       CLIENT: '{sha('editor-shell-v2/paragraph-editor-client.js')}',\n"
       f"       NCLIENT: '{sha('editor-shell-v2/narrow-editor-v2-client.js')}',\n"
       f"       NSESSION: '{sha('editor-shell-v2/narrow-editor-v2-session.js')}',\n"
       f"       HTML: '{sha('web/e2-editor.html')}'}}\n")
V86_DICT = (f"V86 = {{PAGE: '{PAGE_86}',\n       CLIENT: '{CLIENT_86}',\n       NCLIENT: '{NARROW_86}',\n"
            f"       NSESSION: '{SESSION_86}',\n       HTML: '{HTML_86}'}}\n")
REPLACEMENTS = [
    (V86_DICT, V87, 1),
    ("V80 = {PAGE:",
     f"STAGES['v86'] = {{PAGE: ('{COMMIT}', '{PAGE_86}'), CLIENT: ('{COMMIT}', '{CLIENT_86}'),\n"
     f"                 NCLIENT: ('{COMMIT}', '{NARROW_86}'), NSESSION: ('{COMMIT}', '{SESSION_86}'),\n"
     f"                 HTML: ('{COMMIT}', '{HTML_86}')}}\n"
     "V80 = {PAGE:", 1),
    ("F4_85 = EV / 'demo-batch-3/f4-85'\n", "F4_85 = EV / 'demo-batch-3/f4-85'\nF4_86 = EV / 'demo-batch-3/f4-86'\n", 1),
    ("    'v85-f4': (lambda out: four_arm_argv('tools/judge_v85_product_four_arms.py', F4_85, out), F4_85 / 'aggregate-judge.json'),\n",
     "    'v85-f4': (lambda out: four_arm_argv('tools/judge_v85_product_four_arms.py', F4_85, out), F4_85 / 'aggregate-judge.json'),\n"
     "    'v86-f4': (lambda out: four_arm_argv('tools/judge_v86_product_four_arms.py', F4_86, out), F4_86 / 'aggregate-judge.json'),\n", 1),
    ("HERE / 'restored-v85-f4.json']\n", "HERE / 'restored-v85-f4.json', HERE / 'restored-v86-f4.json']\n", 1),
    ("for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'",
     "for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'", 1),
    ("if served() != {p: {'source': V86[p], 'dist': V86[p]} for p in V86}:\n        raise SystemExit('the tree is not generation 86 before V0prime: '",
     "if served() != {p: {'source': V87[p], 'dist': V87[p]} for p in V87}:\n        raise SystemExit('the tree is not generation 87 before V0prime: '", 1),
    ("""                stage[name] = reread_stdout(name, HERE / f'restored-v85-{name}.json')
""", """                stage[name] = reread_stdout(name, HERE / f'restored-v85-{name}.json')
        stage = report['stages']['v86'] = {'restore': restore('v86')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v86-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v86-f4.json'), HERE / 'restored-v86-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v86-{name}.json')
""", 1),
    ("'--manifest', 'e2/editor-shell-v2-bundle-v86.json'])", "'--manifest', 'e2/editor-shell-v2-bundle-v87.json'])", 1),
    ("'bundleLineV86': bundle['exit']", "'bundleLineV87': bundle['exit']", 1),
    ("and all(hashes[p]['source'] == hashes[p]['dist'] == V86[p] for p in V86)}", "and all(hashes[p]['source'] == hashes[p]['dist'] == V87[p] for p in V87)}", 1),
    ("stages.get('v85', {}).get('f4')]\n", "stages.get('v85', {}).get('f4'), stages.get('v86', {}).get('f4')]\n", 1),
    ("rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85') for n in FILE_READERS]",
     "rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86') for n in FILE_READERS]", 1),
    ("and len(stages) == 9 and all(", "and len(stages) == 10 and all(", 1),
]

text = PARENT.read_text(encoding="utf-8")
shebang = "#!/usr/bin/env python3\n"
assert text.startswith(shebang + '"""')
end = text.index('"""', len(shebang) + 3) + 3
code = text[end:]
for old, new, count in REPLACEMENTS:
    got = code.count(old)
    if got != count:
        raise SystemExit(f"{old[:70]!r} occurs {got} times, expected {count}")
    code = code.replace(old, new)
for stale in ("V86[", "V86 =", "bundle-v86"):
    if stale in code:
        raise SystemExit(f"stale {stale} left in the code")
CHILD.parent.mkdir(exist_ok=True)
CHILD.write_text(shebang + DOC + code, encoding="utf-8")
print("written", CHILD)
