#!/usr/bin/env python3
"""Spec SPEC-M3-v28-last-line-fallback 7.3 (F3-82, F4-82): before a derived tool's first run, scan it for the old values.

Derived from findings/evidence/v27-176/stale-scan/scan.py (its evidence binds it; not edited); the only
difference is the closed list of old values, generation 81's and v27's: e2-editor-v27, 8152448a (worker),
d5d07639 (manifest), c089dfd6 (wasm), b63d8ee5 (page), 6eb7ca10 (digest), bundle-v81.  A hit inside
the module docstring is derivation history (every derived tool quotes its parent's note) and is listed but
not counted; a hit anywhere else is a stale pin and turns the scan red.  --self-test copies each file with
one stale value appended as code and requires the scan to turn red on it (and stay green on the original).

    python3 -I scan.py <file>...            # exit 0 = no hit outside docstrings
    python3 -I scan.py --self-test <file>...
"""
import ast
import json
import sys

OLD = ('e2-editor-v27', '8152448a', 'd5d07639', 'c089dfd6', 'b63d8ee5', '6eb7ca10', 'bundle-v81')


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
