#!/usr/bin/env python3
"""Derive V0' for generation 84 from findings/evidence/v29-177/v0/run_v0_prime.py (its evidence binds it; not edited): a closed
list of replacements, each with the count it must match.  python3 -I derive_v0_prime.py"""
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PARENT = REPO / "findings/evidence/v29-177/v0/run_v0_prime.py"
CHILD = REPO / "findings/evidence/demo-batch-1/v0/run_v0_prime.py"
PAGE_83 = "022d0cd0b5152f1ee9cabc74b10f5af2eb55935299228119a419ab717957759b"
HTML_83 = "ca58f40f30b7ad115dab51b65ff82ce297724f2185c1cd199c0c16f7a32f601a"
PAGE_84 = hashlib.sha256((REPO / "wasm_sdk_probe/web/e2-editor-app.js").read_bytes()).hexdigest()
HTML_84 = hashlib.sha256((REPO / "wasm_sdk_probe/web/e2-editor.html").read_bytes()).hexdigest()
COMMIT = "3830a72a9"   # the last commit before the zoom: generation 83's page and HTML
CLIENT = "d07a58e0c674dd992e45df9a37ba26ade9a0d53555f284d1eb5cff2c343b5f3b"
NARROW = "50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5"
SESSION = "d037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0"

DOC = '''"""V0' for generation 84 (SPEC-P-demo-batch-1 section 3): the carried-over counts and every earlier generation's readings
still re-read.

Derived from findings/evidence/v29-177/v0/run_v0_prime.py (bound by its own committed result; not edited) by
../derive/derive_v0_prime.py.  The differences are a closed list: this docstring; a seventh stage, v83 (page and HTML of
generation 83 from git 3830a72a9), which re-reads F4-83's final page with `judge_v83_product_four_arms.py` alongside the file
readers; F4-83's reader recorded among the live reds; the pre-check and the put-back target generation 84 and its bundle line.

Everything else as v83's, whose docstring is the parent's: the four-arm readers bind the live shell digest and are
NOT_ESTABLISHED on the generation-84 tree by construction, and are re-read in their stage, byte-identical with the argv of
the committed result; put back in `finally` with `git checkout HEAD --` and `make e2-c-assets`.  Writes only into this
directory.  Must not run while anything serves dist/.

Verdict V0_PRIME_HOLDS iff every re-read is byte-identical with its expected exit (0 unless EXPECTED_EXIT says
otherwise), every four-arm live read is a red (nonzero exit), every restore and the put-back hold.
"""'''

REPLACEMENTS = [
    (f"V83 = {{PAGE: '{PAGE_83}',", f"V84 = {{PAGE: '{PAGE_84}',", 1),
    (f"       HTML: '{HTML_83}'}}\n", f"       HTML: '{HTML_84}'}}\n", 1),
    ("    _files[HTML] = ('69c5583a9', 'b9c2b9751f57962585bb9788255e2aa42a228c0a8b9983755191d2004bab545a')\n",
     "    _files[HTML] = ('69c5583a9', 'b9c2b9751f57962585bb9788255e2aa42a228c0a8b9983755191d2004bab545a')\n"
     f"STAGES['v83'] = {{PAGE: ('{COMMIT}', '{PAGE_83}'), CLIENT: ('{COMMIT}', '{CLIENT}'),\n"
     f"                 NCLIENT: ('{COMMIT}', '{NARROW}'), NSESSION: ('{COMMIT}', '{SESSION}'),\n"
     f"                 HTML: ('{COMMIT}', '{HTML_83}')}}\n", 1),
    ("F3_82 = EV / 'v28-083/f3-82'\n", "F3_82 = EV / 'v28-083/f3-82'\nF4_83 = EV / 'v29-177/f4-83/final-page'\n", 1),
    ("    'v82-f4': (lambda out: four_arm_argv('tools/judge_v82_product_four_arms.py', F4_82, out), F4_82 / 'aggregate-judge.json'),\n",
     "    'v82-f4': (lambda out: four_arm_argv('tools/judge_v82_product_four_arms.py', F4_82, out), F4_82 / 'aggregate-judge.json'),\n"
     "    'v83-f4': (lambda out: four_arm_argv('tools/judge_v83_product_four_arms.py', F4_83, out), F4_83 / 'aggregate-judge.json'),\n", 1),
    ("HERE / 'restored-v82-f4.json']\n", "HERE / 'restored-v82-f4.json', HERE / 'restored-v83-f4.json']\n", 1),
    ("for s in ('v79', 'v80', 'v81', 'v82') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'",
     "for s in ('v79', 'v80', 'v81', 'v82', 'v83') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'", 1),
    ("if served() != {p: {'source': V83[p], 'dist': V83[p]} for p in V83}:\n        raise SystemExit('the tree is not generation 83 before V0prime: '",
     "if served() != {p: {'source': V84[p], 'dist': V84[p]} for p in V84}:\n        raise SystemExit('the tree is not generation 84 before V0prime: '", 1),
    ("""                stage[name] = reread_stdout(name, HERE / f'restored-v82-{name}.json')
""", """                stage[name] = reread_stdout(name, HERE / f'restored-v82-{name}.json')
        stage = report['stages']['v83'] = {'restore': restore('v83')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v83-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v83-f4.json'), HERE / 'restored-v83-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v83-{name}.json')
""", 1),
    ("'--manifest', 'e2/editor-shell-v2-bundle-v83.json'])", "'--manifest', 'e2/editor-shell-v2-bundle-v84.json'])", 1),
    ("'bundleLineV83': bundle['exit']", "'bundleLineV84': bundle['exit']", 1),
    ("and all(hashes[p]['source'] == hashes[p]['dist'] == V83[p] for p in V83)}", "and all(hashes[p]['source'] == hashes[p]['dist'] == V84[p] for p in V84)}", 1),
    ("stages.get('v82', {}).get('f4')]\n", "stages.get('v82', {}).get('f4'), stages.get('v83', {}).get('f4')]\n", 1),
    ("rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82') for n in FILE_READERS]",
     "rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82', 'v83') for n in FILE_READERS]", 1),
    ("and len(stages) == 6 and all(", "and len(stages) == 7 and all(", 1),
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
for stale in ("V83[", "V83 =", "bundle-v83"):
    if stale in code:
        raise SystemExit(f"stale {stale} left in the code")
CHILD.parent.mkdir(exist_ok=True)
CHILD.write_text(shebang + DOC + code, encoding="utf-8")
print("written", CHILD)
