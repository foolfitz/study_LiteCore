#!/usr/bin/env python3
"""Derive V0' for generation 83 from findings/evidence/v28-083/v0/run_v0_prime.py (its evidence binds it; not edited): a closed
list of replacements, each with the count it must match.  python3 -I derive_v0_prime.py"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PARENT = REPO / "findings/evidence/v28-083/v0/run_v0_prime.py"
CHILD = REPO / "findings/evidence/v29-177/v0/run_v0_prime.py"
PAGE_82 = "3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a"
PAGE_83 = "022d0cd0b5152f1ee9cabc74b10f5af2eb55935299228119a419ab717957759b"
CLIENT = "d07a58e0c674dd992e45df9a37ba26ade9a0d53555f284d1eb5cff2c343b5f3b"
NARROW = "50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5"
SESSION = "d037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0"
COMMIT = "69c5583a9"   # the last commit before the cutover to v29

DOC = '''"""V0' for generation 83 (SPEC-M3-v29-tick-pacing section 6 T3): the carried-over counts and the generation-79, -80, -81 and
-82 readings still re-read.

Derived from findings/evidence/v28-083/v0/run_v0_prime.py (bound by its own committed result; not edited) by
../derive/derive_v0_prime.py.  The differences are a closed list: this docstring; a sixth stage, v82 (the four files of
generation 82, all from git 69c5583a9), which re-reads F4-82 with `judge_v82_product_four_arms.py` alongside the file
readers; the generation-82 F3 readings (`read_v25_f3.py` and `read_v82_f3_equal.py` on f3-82/run-01, with the argv their
committed results were made with) added to the file readers, read on the live tree and in every stage, `read_v25_f3.py`'s
on F3-82 with its recorded exit 1 -- EXPECTED_EXIT; F4-82's reader recorded among the live reds; the pre-check and the
put-back target generation 83 (only the page differs from 82) and its bundle line.

  stage v82  page 3b0a2ebb, paragraph client d07a58e0, narrow client 50f5a2ac, narrow session d037eaa4 (git 69c5583a9)

Everything else as v82's, whose docstring is the parent's: the four-arm readers bind the live shell digest and are
NOT_ESTABLISHED on the generation-83 tree by construction, and are re-read in their stage, byte-identical with the argv of
the committed result; put back in `finally` with `git checkout HEAD --` and `make e2-c-assets`.  Writes only into this
directory.  Must not run while anything serves dist/.

Verdict V0_PRIME_HOLDS iff every re-read is byte-identical with its expected exit (0 unless EXPECTED_EXIT says
otherwise), every four-arm live read is a red (nonzero exit), every restore and the put-back hold.
"""'''

REPLACEMENTS = [
    ("""            NSESSION: ('a9a04dc64', 'd037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0')},
}
V82 = {PAGE: '%s',""" % PAGE_82,
     """            NSESSION: ('a9a04dc64', 'd037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0')},
    'v82': {PAGE: ('%s', '%s'),
            CLIENT: ('%s', '%s'),
            NCLIENT: ('%s', '%s'),
            NSESSION: ('%s', '%s')},
}
V83 = {PAGE: '%s',""" % (COMMIT, PAGE_82, COMMIT, CLIENT, COMMIT, NARROW, COMMIT, SESSION, PAGE_83), 1),
    ("F3_81 = EV / 'v27-176/f3-81'\n",
     "F3_81 = EV / 'v27-176/f3-81'\nF4_82 = EV / 'v28-083/f4-82'\nF3_82 = EV / 'v28-083/f3-82'\n", 1),
    ("""               F4_81 / 'aggregate-judge.json'),
}""", """               F4_81 / 'aggregate-judge.json'),
    'v82-f4': (lambda out: four_arm_argv('tools/judge_v82_product_four_arms.py', F4_82, out), F4_82 / 'aggregate-judge.json'),
}""", 1),
    ("""                       F3_81 / 'equal-01.json'),
}
EXPECTED_EXIT = {'f3-81-read-01': 1}""", """                       F3_81 / 'equal-01.json'),
    'f3-82-read-01': (['python3', 'tools/read_v25_f3.py', '--v25', '../findings/evidence/v28-083/f3-82/run-01'],
                      F3_82 / 'read-01.json'),
    'f3-82-equal-01': (['python3', 'tools/read_v82_f3_equal.py', '--v82', '../findings/evidence/v28-083/f3-82/run-01'],
                       F3_82 / 'equal-01.json'),
}
EXPECTED_EXIT = {'f3-81-read-01': 1, 'f3-82-read-01': 1}""", 1),
    ("HERE / 'restored-v80-f4.json', HERE / 'restored-v81-f4.json']",
     "HERE / 'restored-v80-f4.json', HERE / 'restored-v81-f4.json', HERE / 'restored-v82-f4.json']", 1),
    ("for s in ('v79', 'v80', 'v81') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'",
     "for s in ('v79', 'v80', 'v81', 'v82') for n in FILE_READERS]\n           + [HERE / 'v0-prime.json'", 1),
    ("if served() != {p: {'source': V82[p], 'dist': V82[p]} for p in V82}:\n        raise SystemExit('the tree is not generation 82 before V0prime: '",
     "if served() != {p: {'source': V83[p], 'dist': V83[p]} for p in V83}:\n        raise SystemExit('the tree is not generation 83 before V0prime: '", 1),
    ("""                stage[name] = reread_stdout(name, HERE / f'restored-v81-{name}.json')
""", """                stage[name] = reread_stdout(name, HERE / f'restored-v81-{name}.json')
        stage = report['stages']['v82'] = {'restore': restore('v82')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v82-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v82-f4.json'), HERE / 'restored-v82-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v82-{name}.json')
""", 1),
    ("'--manifest', 'e2/editor-shell-v2-bundle-v82.json'])", "'--manifest', 'e2/editor-shell-v2-bundle-v83.json'])", 1),
    ("'bundleLineV82': bundle['exit']", "'bundleLineV83': bundle['exit']", 1),
    ("and all(hashes[p]['source'] == hashes[p]['dist'] == V82[p] for p in V82)}", "and all(hashes[p]['source'] == hashes[p]['dist'] == V83[p] for p in V83)}", 1),
    ("stages.get('v81', {}).get('f4')]\n", "stages.get('v81', {}).get('f4'), stages.get('v82', {}).get('f4')]\n", 1),
    ("rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81') for n in FILE_READERS]",
     "rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82') for n in FILE_READERS]", 1),
    ("and len(stages) == 5 and all(", "and len(stages) == 6 and all(", 1),
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
for stale in ("V82", "bundle-v82"):
    if stale in code:
        raise SystemExit(f"stale {stale} left in the code")
CHILD.write_text(shebang + DOC + code, encoding="utf-8")
print("written", CHILD)
