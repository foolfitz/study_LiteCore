#!/usr/bin/env python3
"""Derive V0' for generation 88 from ../../demo-batch-4/v0-87/run_v0_prime.py (its evidence binds it; not edited): a closed list of replacements,
each with the count it must match.  python3 -I derive_v0_prime_88.py"""
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PARENT = REPO / "findings/evidence/demo-batch-4/v0-87/run_v0_prime.py"
CHILD = REPO / "findings/evidence/demo-batch-5/v0-88/run_v0_prime.py"
V87_FILES = {"PAGE": "f6fd0b75dbf26a09d1ea0dcc97543cab8ef703a7e9c6eef4841953cff92caa26",
             "CLIENT": "60c3043233bbab4726947eb4e1850bfc20938f24d026bb2e8d8984c9f5b33ca8",
             "NCLIENT": "7548e8f6170d0fa3afab090c3950e1c57645fded16f3db7ce98050cbe62ca65f",
             "NSESSION": "a07747602d47dcb9dd5a8f271def6373471e52c9bfd7ec671cf7a20580cbaeab",
             "HTML": "3a2b9ac2c4a62ff1b9b182db4c6664c4132101fca3f640f102ba88ab2eb7aa6f"}
COMMIT = "1e4f2b3b7"   # the last commit whose page sources are generation 87's: d60dec651 moved the page ahead for batch 5
sha = lambda path: hashlib.sha256((REPO / "wasm_sdk_probe" / path).read_bytes()).hexdigest()

DOC = '''"""V0' for generation 88 (SPEC-P-demo-batch-5): the carried-over counts and every earlier generation's readings still re-read.

Derived from ../../demo-batch-4/v0-87/run_v0_prime.py (bound by its own committed result; not edited) by ../derive/derive_v0_prime_88.py.
The differences are a closed list: this docstring; an eleventh stage, v87 (page, HTML and the three shell modules of generation 87 from git
1e4f2b3b7), which re-reads F4-87 with `judge_v87_product_four_arms.py` alongside the file readers; F4-87's reader recorded among the
live reds; the pre-check and the put-back target generation 88 and its bundle line.

Everything else as its parent's: the four-arm readers bind the live shell digest and are NOT_ESTABLISHED on the generation-88 tree
by construction, and are re-read in their stage, byte-identical with the argv of the committed result; put back in `finally` with
`git checkout HEAD --` and `make e2-c-assets`.  Writes only into this directory.  Must not run while anything serves dist/.

Verdict V0_PRIME_HOLDS iff every re-read is byte-identical with its expected exit (0 unless EXPECTED_EXIT says otherwise), every
four-arm live read is a red (nonzero exit), every restore and the put-back hold.
"""'''

V88 = (f"V88 = {{PAGE: '{sha('web/e2-editor-app.js')}',\n"
       f"       CLIENT: '{sha('editor-shell-v2/paragraph-editor-client.js')}',\n"
       f"       NCLIENT: '{sha('editor-shell-v2/narrow-editor-v2-client.js')}',\n"
       f"       NSESSION: '{sha('editor-shell-v2/narrow-editor-v2-session.js')}',\n"
       f"       HTML: '{sha('web/e2-editor.html')}'}}\n")
V87_DICT = (f"V87 = {{PAGE: '{V87_FILES['PAGE']}',\n       CLIENT: '{V87_FILES['CLIENT']}',\n       NCLIENT: '{V87_FILES['NCLIENT']}',\n"
            f"       NSESSION: '{V87_FILES['NSESSION']}',\n       HTML: '{V87_FILES['HTML']}'}}\n")
f = V87_FILES
REPLACEMENTS = [
    (V87_DICT, V88, 1),
    ("V80 = {PAGE:",
     f"STAGES['v87'] = {{PAGE: ('{COMMIT}', '{f['PAGE']}'), CLIENT: ('{COMMIT}', '{f['CLIENT']}'),\n"
     f"                 NCLIENT: ('{COMMIT}', '{f['NCLIENT']}'), NSESSION: ('{COMMIT}', '{f['NSESSION']}'),\n"
     f"                 HTML: ('{COMMIT}', '{f['HTML']}')}}\n"
     "V80 = {PAGE:", 1),
    ("F4_86 = EV / 'demo-batch-3/f4-86'\n", "F4_86 = EV / 'demo-batch-3/f4-86'\nF4_87 = EV / 'demo-batch-4/f4-87'\n", 1),
    ("    'v86-f4': (lambda out: four_arm_argv('tools/judge_v86_product_four_arms.py', F4_86, out), F4_86 / 'aggregate-judge.json'),\n",
     "    'v86-f4': (lambda out: four_arm_argv('tools/judge_v86_product_four_arms.py', F4_86, out), F4_86 / 'aggregate-judge.json'),\n"
     "    'v87-f4': (lambda out: four_arm_argv('tools/judge_v87_product_four_arms.py', F4_87, out), F4_87 / 'aggregate-judge.json'),\n", 1),
    ("HERE / 'restored-v86-f4.json']\n", "HERE / 'restored-v86-f4.json', HERE / 'restored-v87-f4.json']\n", 1),
    ("for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'",
     "for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86', 'v87') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'", 1),
    ("if served() != {p: {'source': V87[p], 'dist': V87[p]} for p in V87}:\n        raise SystemExit('the tree is not generation 87 before V0prime: '",
     "if served() != {p: {'source': V88[p], 'dist': V88[p]} for p in V88}:\n        raise SystemExit('the tree is not generation 88 before V0prime: '", 1),
    ("""                stage[name] = reread_stdout(name, HERE / f'restored-v86-{name}.json')
""", """                stage[name] = reread_stdout(name, HERE / f'restored-v86-{name}.json')
        stage = report['stages']['v87'] = {'restore': restore('v87')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v87-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v87-f4.json'), HERE / 'restored-v87-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v87-{name}.json')
""", 1),
    ("'--manifest', 'e2/editor-shell-v2-bundle-v87.json'])", "'--manifest', 'e2/editor-shell-v2-bundle-v88.json'])", 1),
    ("'bundleLineV87': bundle['exit']", "'bundleLineV88': bundle['exit']", 1),
    ("and all(hashes[p]['source'] == hashes[p]['dist'] == V87[p] for p in V87)}", "and all(hashes[p]['source'] == hashes[p]['dist'] == V88[p] for p in V88)}", 1),
    ("stages.get('v86', {}).get('f4')]\n", "stages.get('v86', {}).get('f4'), stages.get('v87', {}).get('f4')]\n", 1),
    ("rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86') for n in FILE_READERS]",
     "rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86', 'v87') for n in FILE_READERS]", 1),
    ("and len(stages) == 10 and all(", "and len(stages) == 11 and all(", 1),
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
for stale in ("V87[", "V87 =", "bundle-v87"):
    if stale in code:
        raise SystemExit(f"stale {stale} left in the code")
CHILD.parent.mkdir(exist_ok=True)
CHILD.write_text(shebang + DOC + code, encoding="utf-8")
print("written", CHILD)
