#!/usr/bin/env python3
"""Derive V0' for generation 89 from ../../demo-batch-5/v0-88/run_v0_prime.py (its evidence binds it; not edited): a closed list of replacements,
each with the count it must match.  python3 -I derive_v0_prime_89.py"""
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PARENT = REPO / "findings/evidence/demo-batch-5/v0-88/run_v0_prime.py"
CHILD = REPO / "findings/evidence/ms-formats/v0-89/run_v0_prime.py"
COMMIT = "54b0ac826"   # the last commit whose page sources are generation 88's: 4c866daf2 moved them for the Microsoft formats
V88_FILES = {"PAGE": "3d122cb731c6af2ad2a7456eed359981a65ade6b19064dce83037c759670647c",
             "CLIENT": "60c3043233bbab4726947eb4e1850bfc20938f24d026bb2e8d8984c9f5b33ca8",
             "NCLIENT": "7548e8f6170d0fa3afab090c3950e1c57645fded16f3db7ce98050cbe62ca65f",
             "NSESSION": "a07747602d47dcb9dd5a8f271def6373471e52c9bfd7ec671cf7a20580cbaeab",
             "HTML": "3a2b9ac2c4a62ff1b9b182db4c6664c4132101fca3f640f102ba88ab2eb7aa6f"}
# sdk/document-sdk.js is in the shell bundle and generation 89 is the first to change it since v24: every earlier stage has these bytes
# (git show at each stage's commit, v24 b241c83a4 through v88 54b0ac826), so every restore puts them back.
DSDK_BEFORE = "afdff2d4c6fc86a3fbca9f40ab7c0122021c61a0d23a7969b4f80b7770f3632e"
sha = lambda path: hashlib.sha256((REPO / "wasm_sdk_probe" / path).read_bytes()).hexdigest()

DOC = '''"""V0' for generation 89 (SPEC-P-ms-formats step 4): the carried-over counts and every earlier generation's readings still re-read.

Derived from ../../demo-batch-5/v0-88/run_v0_prime.py (bound by its own committed result; not edited) by ../derive/derive_v0_prime_89.py.
The differences are a closed list: this docstring; a twelfth stage, v88 (page, HTML and the three shell modules of generation 88 from git
54b0ac826), which re-reads F4-88 with `judge_v88_product_four_arms.py` alongside the file readers; F4-88's reader recorded among the
live reds; sdk/document-sdk.js added to the files restored, compared and put back (DSDK), with every stage's bytes afdff2d4 (generation 89
is the first since v24 to change it, and it is in the shell digest every four-arm reader binds); the pre-check and the put-back target
generation 89 and its bundle line.

Everything else as its parent's: the four-arm readers bind the live shell digest and are NOT_ESTABLISHED on the generation-89 tree
by construction, and are re-read in their stage, byte-identical with the argv of the committed result; put back in `finally` with
`git checkout HEAD --` and `make e2-c-assets`.  Writes only into this directory.  Must not run while anything serves dist/ or copies the
source tree into a mirror (it swaps sdk/document-sdk.js, which the Calc pages import too).

Verdict V0_PRIME_HOLDS iff every re-read is byte-identical with its expected exit (0 unless EXPECTED_EXIT says otherwise), every
four-arm live read is a red (nonzero exit), every restore and the put-back hold.
"""'''

V89 = (f"V89 = {{PAGE: '{sha('web/e2-editor-app.js')}',\n"
       f"       CLIENT: '{sha('editor-shell-v2/paragraph-editor-client.js')}',\n"
       f"       NCLIENT: '{sha('editor-shell-v2/narrow-editor-v2-client.js')}',\n"
       f"       NSESSION: '{sha('editor-shell-v2/narrow-editor-v2-session.js')}',\n"
       f"       HTML: '{sha('web/e2-editor.html')}',\n"
       f"       DSDK: '{sha('sdk/document-sdk.js')}'}}\n")
V88_DICT = (f"V88 = {{PAGE: '{V88_FILES['PAGE']}',\n       CLIENT: '{V88_FILES['CLIENT']}',\n       NCLIENT: '{V88_FILES['NCLIENT']}',\n"
            f"       NSESSION: '{V88_FILES['NSESSION']}',\n       HTML: '{V88_FILES['HTML']}'}}\n")
f = V88_FILES
REPLACEMENTS = [
    ("HTML = 'web/e2-editor.html'\nFILES = (PAGE, CLIENT, NCLIENT, NSESSION, HTML)\n",
     "HTML = 'web/e2-editor.html'\nDSDK = 'sdk/document-sdk.js'\nFILES = (PAGE, CLIENT, NCLIENT, NSESSION, HTML, DSDK)\n", 1),
    ("NSESSION: 'dist/editor-shell-v2/narrow-editor-v2-session.js', HTML: 'dist/e2-editor.html'}\n",
     "NSESSION: 'dist/editor-shell-v2/narrow-editor-v2-session.js', HTML: 'dist/e2-editor.html',\n        DSDK: 'dist/sdk/document-sdk.js'}\n", 1),
    (V88_DICT, V89, 1),
    ("V80 = {PAGE:",
     f"STAGES['v88'] = {{PAGE: ('{COMMIT}', '{f['PAGE']}'), CLIENT: ('{COMMIT}', '{f['CLIENT']}'),\n"
     f"                 NCLIENT: ('{COMMIT}', '{f['NCLIENT']}'), NSESSION: ('{COMMIT}', '{f['NSESSION']}'),\n"
     f"                 HTML: ('{COMMIT}', '{f['HTML']}')}}\n"
     "# Generation 89 changed sdk/document-sdk.js, the first change since v24: every stage restores the bytes it was frozen with.\n"
     "for _files in STAGES.values():\n"
     f"    _files[DSDK] = ('{COMMIT}', '{DSDK_BEFORE}')\n"
     "V80 = {PAGE:", 1),
    ("F4_87 = EV / 'demo-batch-4/f4-87'\n", "F4_87 = EV / 'demo-batch-4/f4-87'\nF4_88 = EV / 'demo-batch-5/f4-88'\n", 1),
    ("    'v87-f4': (lambda out: four_arm_argv('tools/judge_v87_product_four_arms.py', F4_87, out), F4_87 / 'aggregate-judge.json'),\n",
     "    'v87-f4': (lambda out: four_arm_argv('tools/judge_v87_product_four_arms.py', F4_87, out), F4_87 / 'aggregate-judge.json'),\n"
     "    'v88-f4': (lambda out: four_arm_argv('tools/judge_v88_product_four_arms.py', F4_88, out), F4_88 / 'aggregate-judge.json'),\n", 1),
    ("HERE / 'restored-v87-f4.json']\n", "HERE / 'restored-v87-f4.json', HERE / 'restored-v88-f4.json']\n", 1),
    ("for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86', 'v87') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'",
     "for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86', 'v87', 'v88') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'", 1),
    ("if served() != {p: {'source': V88[p], 'dist': V88[p]} for p in V88}:\n        raise SystemExit('the tree is not generation 88 before V0prime: '",
     "if served() != {p: {'source': V89[p], 'dist': V89[p]} for p in V89}:\n        raise SystemExit('the tree is not generation 89 before V0prime: '", 1),
    ("""                stage[name] = reread_stdout(name, HERE / f'restored-v87-{name}.json')
""", """                stage[name] = reread_stdout(name, HERE / f'restored-v87-{name}.json')
        stage = report['stages']['v88'] = {'restore': restore('v88')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v88-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v88-f4.json'), HERE / 'restored-v88-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v88-{name}.json')
""", 1),
    ("'--manifest', 'e2/editor-shell-v2-bundle-v88.json'])", "'--manifest', 'e2/editor-shell-v2-bundle-v89.json'])", 1),
    ("'bundleLineV88': bundle['exit']", "'bundleLineV89': bundle['exit']", 1),
    ("and all(hashes[p]['source'] == hashes[p]['dist'] == V88[p] for p in V88)}", "and all(hashes[p]['source'] == hashes[p]['dist'] == V89[p] for p in V89)}", 1),
    ("stages.get('v87', {}).get('f4')]\n", "stages.get('v87', {}).get('f4'), stages.get('v88', {}).get('f4')]\n", 1),
    ("rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86', 'v87') for n in FILE_READERS]",
     "rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84', 'v85', 'v86', 'v87', 'v88') for n in FILE_READERS]", 1),
    ("and len(stages) == 11 and all(", "and len(stages) == 12 and all(", 1),
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
for stale in ("V88[", "V88 =", "bundle-v88"):
    if stale in code:
        raise SystemExit(f"stale {stale} left in the code")
CHILD.parent.mkdir(exist_ok=True)
CHILD.write_text(shebang + DOC + code, encoding="utf-8")
print("written", CHILD)
