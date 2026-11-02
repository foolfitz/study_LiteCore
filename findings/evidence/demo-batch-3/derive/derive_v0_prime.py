#!/usr/bin/env python3
"""Derive V0' for generation 85 from ../../demo-batch-2/v0/run_v0_prime.py (its evidence binds it; not edited): a closed list of
replacements, each with the count it must match.  python3 -I derive_v0_prime.py [dir]"""
import hashlib
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[4]
PARENT = REPO / "findings/evidence/demo-batch-2/v0/run_v0_prime.py"
CHILD = REPO / "findings/evidence/demo-batch-3" / (sys.argv[1] if len(sys.argv) > 1 else "v0") / "run_v0_prime.py"
PAGE_84 = "c377b9f2a41b1d6223ec67ac8d53fdd2d1920086af2e0f5759aa4118d084edaf"
HTML_84 = "8016218347fc8e070bab3b288741035f5c18bd35d22c860eb49d789441f51f8f"
PAGE_85 = hashlib.sha256((REPO / "wasm_sdk_probe/web/e2-editor-app.js").read_bytes()).hexdigest()
COMMIT = "10b05fd36"   # the last commit on generation 84
CLIENT = "d07a58e0c674dd992e45df9a37ba26ade9a0d53555f284d1eb5cff2c343b5f3b"
NARROW = "50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5"
SESSION = "d037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0"

DOC = '''"""V0' for generation 85 (SPEC-P-demo-batch-3 section 2): the carried-over counts and every earlier generation's readings
still re-read.

Derived from ../../demo-batch-2/v0/run_v0_prime.py (bound by its own committed result; not edited) by
../derive/derive_v0_prime.py.  The differences are a closed list: this docstring; an eighth stage, v84 (page and HTML of
generation 84 from git 10b05fd36), which re-reads F4-84 (batch 2) with `judge_v84_product_four_arms.py` alongside the file readers;
F4-84's reader recorded among the live reds; the pre-check and the put-back target generation 85 and its bundle line.

Everything else as its parent's: the four-arm readers bind the live shell digest and are NOT_ESTABLISHED on the generation-85
tree by construction, and are re-read in their stage, byte-identical with the argv of the committed result; put back in `finally`
with `git checkout HEAD --` and `make e2-c-assets`.  Writes only into this directory.  Must not run while anything serves dist/.

Verdict V0_PRIME_HOLDS iff every re-read is byte-identical with its expected exit (0 unless EXPECTED_EXIT says
otherwise), every four-arm live read is a red (nonzero exit), every restore and the put-back hold.
"""'''

REPLACEMENTS = [
    (f"V84 = {{PAGE: '{PAGE_84}',", f"V85 = {{PAGE: '{PAGE_85}',", 1),
    ("V84 = {", "V85 = {", 0),
    ("V80 = {PAGE:",
     f"STAGES['v84'] = {{PAGE: ('{COMMIT}', '{PAGE_84}'), CLIENT: ('{COMMIT}', '{CLIENT}'),\n"
     f"                 NCLIENT: ('{COMMIT}', '{NARROW}'), NSESSION: ('{COMMIT}', '{SESSION}'),\n"
     f"                 HTML: ('{COMMIT}', '{HTML_84}')}}\n"
     "V80 = {PAGE:", 1),
    ("F4_83 = EV / 'v29-177/f4-83/final-page'\n", "F4_83 = EV / 'v29-177/f4-83/final-page'\nF4_84 = EV / 'demo-batch-2/f4-84'\n", 1),
    ("    'v83-f4': (lambda out: four_arm_argv('tools/judge_v83_product_four_arms.py', F4_83, out), F4_83 / 'aggregate-judge.json'),\n",
     "    'v83-f4': (lambda out: four_arm_argv('tools/judge_v83_product_four_arms.py', F4_83, out), F4_83 / 'aggregate-judge.json'),\n"
     "    'v84-f4': (lambda out: four_arm_argv('tools/judge_v84_product_four_arms.py', F4_84, out), F4_84 / 'aggregate-judge.json'),\n", 1),
    ("HERE / 'restored-v83-f4.json']\n", "HERE / 'restored-v83-f4.json', HERE / 'restored-v84-f4.json']\n", 1),
    ("for s in ('v79', 'v80', 'v81', 'v82', 'v83') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'",
     "for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'", 1),
    ("if served() != {p: {'source': V84[p], 'dist': V84[p]} for p in V84}:\n        raise SystemExit('the tree is not generation 84 before V0prime: '",
     "if served() != {p: {'source': V85[p], 'dist': V85[p]} for p in V85}:\n        raise SystemExit('the tree is not generation 85 before V0prime: '", 1),
    ("""                stage[name] = reread_stdout(name, HERE / f'restored-v83-{name}.json')
""", """                stage[name] = reread_stdout(name, HERE / f'restored-v83-{name}.json')
        stage = report['stages']['v84'] = {'restore': restore('v84')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v84-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v84-f4.json'), HERE / 'restored-v84-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v84-{name}.json')
""", 1),
    ("'--manifest', 'e2/editor-shell-v2-bundle-v84.json'])", "'--manifest', 'e2/editor-shell-v2-bundle-v85.json'])", 1),
    ("'bundleLineV84': bundle['exit']", "'bundleLineV85': bundle['exit']", 1),
    ("and all(hashes[p]['source'] == hashes[p]['dist'] == V84[p] for p in V84)}", "and all(hashes[p]['source'] == hashes[p]['dist'] == V85[p] for p in V85)}", 1),
    ("stages.get('v83', {}).get('f4')]\n", "stages.get('v83', {}).get('f4'), stages.get('v84', {}).get('f4')]\n", 1),
    ("rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83') for n in FILE_READERS]",
     "rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83', 'v84') for n in FILE_READERS]", 1),
    ("and len(stages) == 7 and all(", "and len(stages) == 8 and all(", 1),
]

text = PARENT.read_text(encoding="utf-8")
shebang = "#!/usr/bin/env python3\n"
assert text.startswith(shebang + '"""')
end = text.index('"""', len(shebang) + 3) + 3
code = text[end:]
for old, new, count in REPLACEMENTS:
    if count == 0:
        continue
    got = code.count(old)
    if got != count:
        raise SystemExit(f"{old[:70]!r} occurs {got} times, expected {count}")
    code = code.replace(old, new)
# The HTML line of the V84 dict.
line = f"       HTML: '{HTML_84}'}}\n"
assert code.count(line) == 1
code = code.replace(line, f"       HTML: '{HTML_84}'}}\n")
for stale in ("V84[", "V84 =", "bundle-v84"):
    if stale in code:
        raise SystemExit(f"stale {stale} left in the code")
CHILD.parent.mkdir(exist_ok=True)
CHILD.write_text(shebang + DOC + code, encoding="utf-8")
print("written", CHILD)
