#!/usr/bin/env python3
"""Spec SPEC-M3-v29-tick-pacing section 6 T3: before a derived tool's first run, scan it for the old values.

Derived from findings/evidence/v28-083/stale-scan/scan.py (its evidence binds it; not edited); the only
difference is the closed list of old values, generation 82's and v28's: e2-editor-v28, c5336b96 (probe.js),
7b4eb474 (manifest), 13f674e4 (wasm), 3b0a2ebb (page), a02673fa (digest), da4e595d (bundle file), bundle-v82; the worker a5df83db is v29's too.  A hit inside
the module docstring is derivation history (every derived tool quotes its parent's note) and is listed but
not counted; a hit anywhere else is a stale pin and turns the scan red.  --self-test copies each file with
one stale value appended as code and requires the scan to turn red on it (and stay green on the original).

    python3 -I scan.py <file>...            # exit 0 = no hit outside docstrings
    python3 -I scan.py --self-test <file>...
"""
import ast
import json
import sys

OLD = ('e2-editor-v28', '13f674e4', 'c5336b96', '7b4eb474', '3b0a2ebb', 'a02673fa', 'da4e595d', 'bundle-v82')


def scan_text(text):
    tree = ast.parse(text)
    doc_lines = set()
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(getattr(tree.body[0], 'value', None), ast.Constant) \
            and isinstance(tree.body[0].value.value, str):
        doc_lines = set(range(tree.body[0].lineno, tree.body[0].end_lineno + 1))
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for old in OLD:
            if old in line:
                hits.append({'line': n, 'value': old, 'inDocstring': n in doc_lines, 'text': line.strip()[:160]})
    return hits


def main(argv):
    self_test = argv[:1] == ['--self-test']
    files = argv[1:] if self_test else argv
    if not files:
        raise SystemExit('no files')
    report = {'old': OLD, 'files': {}}
    red = False
    for path in files:
        text = open(path, encoding='utf-8').read()
        hits = scan_text(text)
        stale = [h for h in hits if not h['inDocstring']]
        entry = {'stale': stale, 'docstringHits': len(hits) - len(stale)}
        if self_test:
            mutant = text + f"\n_STALE = '{OLD[0]}'\n"
            entry['selfTest'] = {'originalRed': bool(stale), 'mutantRed': bool([h for h in scan_text(mutant) if not h['inDocstring']])}
            red |= entry['selfTest']['originalRed'] or not entry['selfTest']['mutantRed']
        else:
            red |= bool(stale)
        report['files'][path] = entry
    report['verdict'] = ('SELF_TEST_' if self_test else '') + ('RED' if red else 'GREEN')
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 1 if red else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
