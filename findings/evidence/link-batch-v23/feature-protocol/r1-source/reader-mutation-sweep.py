#!/usr/bin/env python3
"""R1 reader mutation sweep: disable one check at a time; every mutation must turn an R1 test red.

Census, not a sample: every need()/contradict()/check() call inside the R1 reader functions of
wasm_sdk_probe/tools/judge_v23_feature_selection.py is found with ast, and its condition (the
first argument) is replaced by True.  A new check added to one of those functions is swept
without editing this file.  A few further defining expressions (the control rectangle rule, the
oracle branch, the caret rule, the premise branch, FAIL-vs-NE for the candidate, the aggregate's
wrong-old-click list) are mutated by exact text that must occur exactly once.

Each mutant is written to a temporary directory and imported ahead of the real reader in a fresh
`python3 -I` process, which then runs the R1 reader tests of wasm_sdk_probe/tests/
test_v23_feature_r1.py.  The unmutated reader must pass that suite first, the census must find
the declared R1 functions and at least one check in each, and the result is red if any mutant
survives.  No browser, build or runner is involved.

Usage, from the repository root:
  python3 -I findings/evidence/link-batch-v23/feature-protocol/r1-source/reader-mutation-sweep.py [--out FILE]
Prints the JSON result; with --out also writes it to FILE, refusing an existing file.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
TOOLS = ROOT / 'wasm_sdk_probe/tools'
TESTS = ROOT / 'wasm_sdk_probe/tests'
READER = TOOLS / 'judge_v23_feature_selection.py'
R1_FUNCTIONS = ('r1_walk', 'r1_drag_end', 'r1_marker_witness', 'r1_arm', 'r1_literal_premise', 'inspect_r1')
CHECKS = ('need', 'contradict', 'check')
READER_SUITE = ['R1ReaderRedCases', 'R1ReaderEvidenceBinding', 'R1ReaderBaseline.test_all_72_cells_pass_on_the_model']
AGGREGATE_SUITE = ['R1ReaderBaseline.test_aggregate_is_per_cell_and_lists_the_three_controls']
TEXT_MUTATIONS = (
    ('control rectangle always the visible cursor (emuend ignored)',
     "rect=state['caret'] if row['control']['rule']=='emu' else selection.get('end')", "rect=state['caret']", READER_SUITE),
    ('every cell judged against the native literal landing',
     "if row['oracle']=='literal':", "if True:", READER_SUITE),
    ('caret rule: equality dropped for keyboard and Shift+End shapes',
     "if s['caret']['kind']=='equals':", "if False:", READER_SUITE),
    ('literal Home/End premise skipped',
     "if row['literalPremise']:record['premise']", "if False:record['premise']", READER_SUITE),
    ('candidate outcome contradictions read as NE instead of FAIL',
     "measured=name=='r1cand';check=contradict if measured else need", "measured=name=='r1cand';check=need", READER_SUITE),
    ('aggregate drops the three wrong-old-click controls',
     "and population[r['cell'][1]]['wrongOldClickControl']]", "and False]", AGGREGATE_SUITE),
)
HARNESS = r'''
import json,os,sys,unittest
mutant,tools,tests=sys.argv[1:4];names=json.loads(sys.argv[4])
sys.path[:0]=[mutant,tools,tests]
import judge_v23_feature_selection as reader
assert os.path.dirname(os.path.abspath(reader.__file__))==os.path.abspath(mutant),reader.__file__
import test_v23_feature_r1 as t
suite=unittest.TestSuite();loader=unittest.TestLoader()
for name in names:suite.addTests(loader.loadTestsFromName(name,t))
with open(os.devnull,'w') as sink:result=unittest.TextTestRunner(stream=sink,verbosity=0).run(suite)
print(json.dumps({'ran':result.testsRun,'red':sorted({str(x[0]) for x in result.failures+result.errors})}))
'''


def census(source):
    """Every check call in the R1 functions: (function, line, kind, message, (start, end) byte span of its condition)."""
    raw = source.encode()
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    tree = ast.parse(source)
    found = {name: [] for name in R1_FUNCTIONS}
    for function in tree.body:
        if not (isinstance(function, ast.FunctionDef) and function.name in R1_FUNCTIONS):
            continue
        for node in ast.walk(function):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in CHECKS and len(node.args) == 2:
                cond = node.args[0]
                span = (offsets[cond.lineno - 1] + cond.col_offset, offsets[cond.end_lineno - 1] + cond.end_col_offset)
                found[function.name].append({'function': function.name, 'line': node.lineno, 'kind': node.func.id,
                                             'message': ast.get_source_segment(source, node.args[1]), 'span': span})
    missing = [name for name, rows in found.items() if not rows]
    if missing:
        raise SystemExit('census found no check in: ' + ', '.join(missing))
    return sorted((row for rows in found.values() for row in rows), key=lambda r: r['span'])


def run(mutant_source, names):
    with tempfile.TemporaryDirectory(prefix='r1-reader-mutant-') as directory:
        (Path(directory) / 'judge_v23_feature_selection.py').write_text(mutant_source)
        done = subprocess.run([sys.executable, '-I', '-c', HARNESS, directory, str(TOOLS), str(TESTS), json.dumps(names)],
                              capture_output=True, text=True, cwd=ROOT)
    if done.returncode != 0 or not done.stdout.strip():
        return {'ran': 0, 'red': ['harness failure: ' + done.stderr[-800:]]}
    return json.loads(done.stdout.strip().splitlines()[-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    source = READER.read_text()
    raw = source.encode()
    report = {'schema': 1, 'reader': str(READER.relative_to(ROOT)), 'readerSha256': hashlib.sha256(raw).hexdigest(),
              'tests': str((TESTS / 'test_v23_feature_r1.py').relative_to(ROOT)),
              'testsSha256': hashlib.sha256((TESTS / 'test_v23_feature_r1.py').read_bytes()).hexdigest(),
              'functions': list(R1_FUNCTIONS), 'mutations': []}
    baseline = {'reader': run(source, READER_SUITE), 'aggregate': run(source, AGGREGATE_SUITE)}
    report['baseline'] = baseline
    if any(b['red'] or not b['ran'] for b in baseline.values()):
        report['verdict'] = 'RED_BASELINE'
    else:
        mutants = []
        for row in census(source):
            start, end = row['span']
            mutants.append(({'id': f"{row['function']}:{row['line']}:{row['kind']}", 'kind': 'condition-disabled',
                             'message': row['message'], 'original': raw[start:end].decode()[:160]},
                            (raw[:start] + b'True' + raw[end:]).decode(), READER_SUITE))
        for description, old, new, suite in TEXT_MUTATIONS:
            if source.count(old) != 1:
                raise SystemExit('text mutation target not unique: ' + old)
            mutants.append(({'id': 'text:' + description, 'kind': 'text', 'original': old, 'replacement': new},
                            source.replace(old, new), suite))
        for record, mutant, suite in mutants:
            if mutant == source:
                raise SystemExit('mutation changed nothing: ' + record['id'])
            outcome = run(mutant, suite)
            record.update(suite=suite, ran=outcome['ran'], red=outcome['red'], killed=bool(outcome['red']) and outcome['ran'] > 0)
            report['mutations'].append(record)
            print(('KILLED   ' if record['killed'] else 'SURVIVED ') + record['id'], file=sys.stderr, flush=True)
        survivors = [m['id'] for m in report['mutations'] if not m['killed']]
        report['survivors'] = survivors
        report['counts'] = {'mutations': len(report['mutations']), 'killed': len(report['mutations']) - len(survivors),
                            'conditionChecks': sum(m['kind'] == 'condition-disabled' for m in report['mutations'])}
        report['verdict'] = 'ALL_KILLED' if not survivors else 'SURVIVORS'
    encoded = json.dumps(report, indent=2) + '\n'
    if args.out:
        with args.out.open('x') as handle:
            handle.write(encoded)
    print(encoded, end='')
    return 0 if report['verdict'] == 'ALL_KILLED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
