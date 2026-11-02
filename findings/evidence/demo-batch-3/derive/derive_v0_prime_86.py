#!/usr/bin/env python3
"""Derive V0' for generation 86 from ../v0-02/run_v0_prime.py (its evidence binds it; not edited): a closed list of replacements, each
with the count it must match.  python3 -I derive_v0_prime_86.py"""
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PARENT = REPO / "findings/evidence/demo-batch-3/v0-02/run_v0_prime.py"
CHILD = REPO / "findings/evidence/demo-batch-3/v0-86/run_v0_prime.py"
PAGE_85 = "0fa5662e11704dab6ba0f6579bbb400ea849ebe4f31c8898d850f9dc2bcd0bfa"
HTML_85 = "8016218347fc8e070bab3b288741035f5c18bd35d22c860eb49d789441f51f8f"
CLIENT_85 = "d07a58e0c674dd992e45df9a37ba26ade9a0d53555f284d1eb5cff2c343b5f3b"
NARROW_85 = "50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5"
SESSION_85 = "d037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0"
COMMIT = "ee55a7724"   # the last commit whose page sources are generation 85's: 36d215235 moved them ahead for the batch 3 controls
sha = lambda path: hashlib.sha256((REPO / "wasm_sdk_probe" / path).read_bytes()).hexdigest()

DOC = '''"""V0' for generation 86 (SPEC-P-demo-batch-3 section 3): the carried-over counts and every earlier generation's readings
still re-read.

Derived from ../v0-02/run_v0_prime.py (bound by its own committed result; not edited) by ../derive/derive_v0_prime_86.py.  The
differences are a closed list: this docstring; a ninth stage, v85 (page, HTML and the three shell modules of generation 85 from git
ee55a7724), which re-reads F4-85 with `judge_v85_product_four_arms.py` alongside the file readers; F4-85's reader recorded among the
live reds; the pre-check and the put-back target generation 86 and its bundle line.

Everything else as its parent's: the four-arm readers bind the live shell digest and are NOT_ESTABLISHED on the generation-86 tree
by construction, and are re-read in their stage, byte-identical with the argv of the committed result; put back in `finally` with
`git checkout HEAD --` and `make e2-c-assets`.  Writes only into this directory.  Must not run while anything serves dist/.

Verdict V0_PRIME_HOLDS iff every re-read is byte-identical with its expected exit (0 unless EXPECTED_EXIT says otherwise), every
four-arm live read is a red (nonzero exit), every restore and the put-back hold.
"""'''

V86 = (f"V86 = {{PAGE: '{sha('web/e2-editor-app.js')}',\n"
       f"       CLIENT: '{sha('editor-shell-v2/paragraph-editor-client.js')}',\n"
       f"       NCLIENT: '{sha('editor-shell-v2/narrow-editor-v2-client.js')}',\n"
       f"       NSESSION: '{sha('editor-shell-v2/narrow-editor-v2-session.js')}',\n"
       f"       HTML: '{sha('web/e2-editor.html')}'}}\n")
V85_DICT = (f"V85 = {{PAGE: '{PAGE_85}',\n       CLIENT: '{CLIENT_85}',\n       NCLIENT: '{NARROW_85}',\n"
            f"       NSESSION: '{SESSION_85}',\n       HTML: '{HTML_85}'}}\n")
REPLACEMENTS = [
    (V85_DICT, V86, 1),
    ("V80 = {PAGE:",
     f"STAGES['v85'] = {{PAGE: ('{COMMIT}', '{PAGE_85}'), CLIENT: ('{COMMIT}', '{CLIENT_85}'),\n"
     f"                 NCLIENT: ('{COMMIT}', '{NARROW_85}'), NSESSION: ('{COMMIT}', '{SESSION_85}'),\n"
     f"                 HTML: ('{COMMIT}', '{HTML_85}')}}\n"
     "V80 = {PAGE:", 1),
    ("F4_84 = EV / 'demo-batch-2/f4-84'\n", "F4_84 = EV / 'demo-batch-2/f4-84'\nF4_85 = EV / 'demo-batch-3/f4-85'\n", 1),
    ("    'v84-f4': (lambda out: four_arm_argv('tools/judge_v84_product_four_arms.py', F4_84, out), F4_84 / 'aggregate-judge.json'),\n",
     "    'v84-f4': (lambda out: four_arm_argv('tools/judge_v84_product_four_arms.py', F4_84, out), F4_84 / 'aggregate-judge.json'),\n"
     "    'v85-f4': (lambda out: four_arm_argv('tools/judge_v85_product_four_arms.py', F4_85, out), F4_85 / 'aggregate-judge.json'),\n", 1),
    ("HERE / 'restored-v84-f4.json']\n", "HERE / 'restored-v84-f4.json', HERE / 'restored-v85-f4.json']\n", 1),
    ("for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'",
     "for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'", 1),
    ("if served() != {p: {'source': V85[p], 'dist': V85[p]} for p in V85}:\n        raise SystemExit('the tree is not generation 85 before V0prime: '",
     "if served() != {p: {'source': V86[p], 'dist': V86[p]} for p in V86}:\n        raise SystemExit('the tree is not generation 86 before V0prime: '", 1),
    ("""                stage[name] = reread_stdout(name, HERE / f'restored-v84-{name}.json')
""", """                stage[name] = reread_stdout(name, HERE / f'restored-v84-{name}.json')
        stage = report['stages']['v85'] = {'restore': restore('v85')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v85-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v85-f4.json'), HERE / 'restored-v85-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v85-{name}.json')
""", 1),
    ("'--manifest', 'e2/editor-shell-v2-bundle-v85.json'])", "'--manifest', 'e2/editor-shell-v2-bundle-v86.json'])", 1),
    ("'bundleLineV85': bundle['exit']", "'bundleLineV86': bundle['exit']", 1),
    ("and all(hashes[p]['source'] == hashes[p]['dist'] == V85[p] for p in V85)}", "and all(hashes[p]['source'] == hashes[p]['dist'] == V86[p] for p in V86)}", 1),
    ("stages.get('v84', {}).get('f4')]\n", "stages.get('v84', {}).get('f4'), stages.get('v85', {}).get('f4')]\n", 1),
    ("rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84') for n in FILE_READERS]",
     "rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85') for n in FILE_READERS]", 1),
    ("and len(stages) == 8 and all(", "and len(stages) == 9 and all(", 1),
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
for stale in ("V85[", "V85 =", "bundle-v85"):
    if stale in code:
        raise SystemExit(f"stale {stale} left in the code")
CHILD.parent.mkdir(exist_ok=True)
CHILD.write_text(shebang + DOC + code, encoding="utf-8")
print("written", CHILD)
