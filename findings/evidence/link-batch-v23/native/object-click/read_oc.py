#!/usr/bin/env python3
"""Read the object-click arms (SPEC-M3-ordered-commands §15.3, L-object-click-shell-switch; fable ruling 2 §2.3).

Usage:
  python3 -I read_oc.py OUT_DIR [--rounds N]          the reading; see Exit below
  python3 -I read_oc.py --self-test SMOKE_DIR           the red cases, built from a real one-round run

Cells come from ../ordered-commands/tool/run_arms.py --arms-set o --modes seq,uni1f: click an as-char image
(the cursor rect at its left edge + 1 cm), then one command (Bold, Delete, Backspace, Left), at once
(uni1f: the next op at the next poll) or after a 150 ms idle (`-i` arms); seq is the settled Writer.

A landing is the saved document's paragraphs (text, run weights: ../ordered-commands/tool/read_results.py's
shape) plus each paragraph's draw:frame count, plus the locator's caret.

  reference  every seq round of an arm lands the same; otherwise that arm is NE (no reference)
  control    (non-vacuity) seq ob-del and seq ob-bksp delete the image (0 frames) in every round: the click
             selected the object; otherwise the whole reading is NOT-ESTABLISHED
  per arm    uni1f: "as seq N/N", or "differs" with the landings printed. This is a measurement for a named
             limit, not a gate: where uni1f differs, the engine's response is decided then (ruling 2 §2.3)
Every cell must be clean (one run-log entry with exit 0, `done`, no fatal, env mode as asked, a measured
record, a saved file, a locate record); an unclean cell makes its arm NE.

VERDICT O-RECORDED when the control holds and every arm has a reference and clean cells; otherwise
NOT-ESTABLISHED. Exit: 0 for O-RECORDED on N >= 5 rounds; 2 when --rounds < 5; 1 otherwise.
"""
import argparse
import gzip
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('read_results', HERE.parent / 'ordered-commands' / 'tool' / 'read_results.py')
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)

TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
DRAW = '{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}'
MODES = ('seq', 'uni1f')
CONTROL = ('ob-del', 'ob-bksp')
COUNTED_ROUNDS = 5


def frames(fodt_gz):
    root = ET.fromstring(gzip.decompress(fodt_gz.read_bytes()))
    return [len(list(p.iter(DRAW + 'frame'))) for p in root.iter() if p.tag in (TEXT + 'p', TEXT + 'h')]


def read_cell(out, arm, mode, r, log):
    cell = rr.read_cell(out / arm, mode, r, log)
    # read_results' cell checks the unipoll env for 'unipoll' only; uni1f needs SAL_LOK_OPTIONS=unipoll too
    jl = out / arm / f'{mode}-r{r}.jsonl'
    if jl.exists() and mode == 'uni1f':
        recs = [json.loads(x) for x in jl.read_text().splitlines() if x.strip()]
        env = next((x for x in recs if x.get('rec') == 'env'), {})
        init = next((x for x in recs if x.get('rec') == 'init'), {})
        # read_results flags any SAL_LOK_OPTIONS outside its 'unipoll' mode; uni1f is unipoll too
        cell['problems'] = [p for p in cell['problems'] if not p.startswith('env SAL_LOK_OPTIONS')]
        if env.get('SAL_LOK_OPTIONS') != 'unipoll':
            cell['problems'].append(f"env SAL_LOK_OPTIONS {env.get('SAL_LOK_OPTIONS')!r}, not 'unipoll'")
        if not init.get('sofficeMainSkipped') or not init.get('execute'):
            cell['problems'].append('no unipoll init record')
    gz = out / arm / f'{mode}-r{r}.fodt.gz'
    if gz.exists() and 'shape' in cell:
        cell['frames'] = frames(gz)
    return cell


def landing(cell):
    return json.dumps({'shape': cell.get('shape'), 'frames': cell.get('frames'), 'caret': cell.get('caret')},
                      ensure_ascii=False, sort_keys=True)


def judge(out, rounds):
    arms = json.loads((out / 'arms.json').read_text())
    log = rr.run_log(out)
    lines, problems, control_fail, no_ref = [], [], [], []
    for a in arms:
        name = a['name']
        cells = {(m, r): read_cell(out, name, m, r, log) for m in MODES for r in range(1, rounds + 1)}
        bad = [f'{m} r{r}: {p}' for (m, r), c in cells.items() for p in c['problems']]
        if bad:
            problems += [f'{name} {b}' for b in bad]
            lines.append(f'{name:10} NE   unclean: {bad[:2]}')
            continue
        land = {m: [landing(cells[(m, r)]) for r in range(1, rounds + 1)] for m in MODES}
        if len(set(land['seq'])) != 1:
            no_ref.append(name)
            lines.append(f'{name:10} NE   seq rounds disagree (no reference)')
            continue
        if name in CONTROL and any(sum(cells[('seq', r)]['frames']) != 0 for r in range(1, rounds + 1)):
            control_fail.append(name)
        same = sum(1 for x in land['uni1f'] if x == land['seq'][0])
        verdict = f'as seq {same}/{rounds}' if same == rounds else f'DIFFERS ({same}/{rounds} as seq)'
        lines.append(f'{name:10} {verdict}')
        lines.append(f'           seq:   {land["seq"][0][:260]}')
        for x in sorted(set(land['uni1f']) - {land['seq'][0]}):
            lines.append(f'           uni1f: {x[:260]}  ({land["uni1f"].count(x)}/{rounds})')
    if control_fail:
        lines.append(f'CONTROL FAILS: seq did not delete the image in {control_fail}: the click did not select it')
    if problems:
        lines.append(f'unclean cells: {len(problems)}: ' + '; '.join(problems[:6]))
    verdict = 'O-RECORDED' if not (control_fail or problems or no_ref) else 'NOT-ESTABLISHED'
    lines.append(f'VERDICT {verdict}')
    return verdict, lines


def self_test(smoke):
    results = []

    def case(label, mutate, expect, needle=None):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'out'
            shutil.copytree(smoke, out)
            mutate(out)
            verdict, lines = judge(out, 1)
            text = '\n'.join(lines)
            ok = verdict == expect and (needle is None or needle in text)
            results.append(ok)
            print(f"{'ok  ' if ok else 'BAD '} {label}: VERDICT {verdict} (expected {expect}"
                  + (f', with {needle!r}' if needle else '') + ')')

    def control_missed(out):   # seq ob-del kept the image: as if the click selected nothing
        shutil.copy(out / 'ob-left' / 'seq-r1.fodt.gz', out / 'ob-del' / 'seq-r1.fodt.gz')

    def uni1f_differs(out):    # uni1f ob-del kept the image
        shutil.copy(out / 'ob-left' / 'seq-r1.fodt.gz', out / 'ob-del' / 'uni1f-r1.fodt.gz')

    def runlog_dup(out):
        with open(out / 'run-log.jsonl', 'a') as f:
            f.write(json.dumps({'arm': 'ob-bold', 'mode': 'seq', 'round': 1, 'exit': 0}) + '\n')

    case('control: the smoke run as recorded', lambda out: None, 'O-RECORDED')
    case('the seq control kept the image', control_missed, 'NOT-ESTABLISHED', 'CONTROL FAILS')
    case('uni1f lands differently: recorded, not a failure', uni1f_differs, 'O-RECORDED', 'ob-del     DIFFERS')
    case('a cell with two run-log entries', runlog_dup, 'NOT-ESTABLISHED', '2 run-log entries')
    print(f'self-test: {sum(results)}/{len(results)} as required')
    return 0 if all(results) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?')
    ap.add_argument('--rounds', type=int, default=5)
    ap.add_argument('--self-test', metavar='SMOKE_DIR')
    a = ap.parse_args()
    if a.self_test:
        return self_test(pathlib.Path(a.self_test))
    verdict, lines = judge(pathlib.Path(a.out), a.rounds)
    print('\n'.join(lines))
    print(f'N = {a.rounds} rounds' + ('' if a.rounds >= COUNTED_ROUNDS else f' < {COUNTED_ROUNDS}: NOT a counted reading'))
    if a.rounds < COUNTED_ROUNDS:
        return 2
    return 0 if verdict == 'O-RECORDED' else 1


if __name__ == '__main__':
    sys.exit(main())
