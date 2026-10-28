#!/usr/bin/env python3
"""V0'' (fable ruling 1, v24 pre-count, 3.4): v23's counted record is still re-readable with exactly the
declared edits undone.  V0' (spec 14.2) extended from the two shell files to the declared tool edits of
findings/evidence/link-batch-v24/pre-count/bound-tool-edits.json.

  1  live tree: counted-r1-s5-01/read-completion.py exits 1 on the shell (v23's identity() raises
     `final shell source/dist differs` inside config(), before any later assertion -- as V0' recorded)
  2  drift census, tool-closed over the cohort's 30 instrumentSources with the path as payload: the
     paths whose live sha256 differs from the frozen one are EXACTLY the declared ones.  Then the
     reader with only the shell restored, recorded.  (The ruling expected this read to fail naming a
     declared path; it cannot: v23's config() hashes its whole import closure into configSha256, so
     any moved closure tool fails the earlier `live frozen plan differs` assertion.  The census is the
     path-by-path proof the ruling asked that read for; see the run README.)
  3  shell AND every declared tool restored (tools from frozen-sources.tar.gz instrument/<path>, each
     checked against the cohort): the reader exits 0 with stage verdicts and counts equal to
     completion-read-01.json
  4  native run-03 re-read on the live tree equals the committed s5-native/reader-03.json
  5  E1-C: check_e1_c_bundle_intact.py exits 0, intact true
  6  put back (always, in `finally`): every restored file returns to its live bytes; each declared tool
     equals its liveSha256 and differs from its frozen sha256; the shell equals the cutover's; git
     status shows no tracked change under wasm_sdk_probe/
  7  report: product-four-arms-counted-01's instruments that differ from the live tree are a subset of
     the declared paths and the two pre-v24 moves

  python3 -I tools/run_v24_v0_double_prime.py --out <new dir> [--edits <list>]

--edits points at another list for red cases V-1..V-3; the verdict is V0PP_HOLDS only if every step holds.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT.parent
EVIDENCE = ROOT / 'findings/evidence/link-batch-v24/pre-count'
COHORT_DIR = ROOT / 'findings/evidence/link-batch-v23/feature-protocol/counted-r1-s5-01'
FOUR_ARMS = ROOT / 'findings/evidence/link-batch-v23/feature-protocol/product-four-arms-counted-01/cohort.json'
NATIVE = ROOT / 'findings/evidence/link-batch-v23/feature-protocol/s5-native'
PRE_V24_MOVES = {'tools/judge_v23_feature_selection.py', 'tools/v23_feature_selection_cases.py'}
SHELL = {  # live path -> (git source, generation-76 sha256, cutover sha256)
    'web/e2-editor-app.js': ('008efd722:wasm_sdk_probe/web/e2-editor-app.js', 'c25b11c463a24fc183a046a5c26ebe6ad71d04d22dcc7830ba77997d231e4490',
                             'b15a6d8e07b6a4f3e551f27971b7cfe8bec2cb743e5f6809013ca7f2082de669'),
    'dist/e2-editor-app.js': ('008efd722:wasm_sdk_probe/web/e2-editor-app.js', 'c25b11c463a24fc183a046a5c26ebe6ad71d04d22dcc7830ba77997d231e4490',
                              'b15a6d8e07b6a4f3e551f27971b7cfe8bec2cb743e5f6809013ca7f2082de669'),
    'sdk/document-sdk.js': ('ceaa2770:wasm_sdk_probe/sdk/document-sdk.js', '9dcb83120c144cad5cf04cabcc14452255d0a640200b8e08f5eed4d4c2d63539',
                            'afdff2d4c6fc86a3fbca9f40ab7c0122021c61a0d23a7969b4f80b7770f3632e'),
    'dist/sdk/document-sdk.js': ('ceaa2770:wasm_sdk_probe/sdk/document-sdk.js', '9dcb83120c144cad5cf04cabcc14452255d0a640200b8e08f5eed4d4c2d63539',
                                 'afdff2d4c6fc86a3fbca9f40ab7c0122021c61a0d23a7969b4f80b7770f3632e'),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(out, name, argv, cwd=ROOT):
    started = time.time()
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    (out / f'{name}.stdout.txt').write_text(done.stdout)
    (out / f'{name}.stderr.txt').write_text(done.stderr)
    return {'name': name, 'argv': argv, 'exit': done.returncode, 'seconds': round(time.time() - started, 1),
            'stderrTail': done.stderr.strip().splitlines()[-1] if done.stderr.strip() else ''}


def completion(out, name):
    target = out / f'{name}.json'
    record = run(out, name, [sys.executable, '-I', str(COHORT_DIR / 'read-completion.py'), '--output', str(target)])
    record['stages'] = None
    if target.is_file():
        record['stages'] = [{k: s.get(k) for k in ('population', 'conclusion', 'required', 'observed', 'counts')}
                            for s in json.loads(target.read_text())['stages']]
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--edits', type=Path, default=EVIDENCE / 'bound-tool-edits.json')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    edits = json.loads(args.edits.read_text())['edits']
    declared = {e['path']: e for e in edits}
    cohort = json.loads((COHORT_DIR / 'cohort.json').read_text())['instrumentSources']
    report = {'schema': 1, 'argv': sys.argv, 'edits': str(args.edits), 'editsSha256': sha(args.edits.read_bytes()),
              'declared': sorted(declared), 'steps': {}, 'red': []}
    write = lambda: (args.out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    def red(step, why):
        report['red'].append({'step': step, 'why': why}); write()

    status = subprocess.run(['git', 'status', '--porcelain', '--', 'wasm_sdk_probe'], cwd=ROOT, capture_output=True, text=True).stdout
    report['gitStatusBefore'] = status
    if status.strip():
        red(0, 'tracked changes under wasm_sdk_probe/ before the run'); return finish(report, write)

    # 1 -- live tree
    step1 = completion(args.out, 'step1-live')
    report['steps']['1'] = step1
    if not (step1['exit'] != 0 and 'final shell source/dist differs' in step1['stderrTail']):
        red(1, 'the live read did not fail on the shell')

    # 2 -- drift census over the cohort's instruments
    live = {p: sha((PROJECT / p).read_bytes()) for p in cohort}
    differing = sorted(p for p in cohort if live[p] != cohort[p])
    report['steps']['2'] = {'instruments': len(cohort), 'differing': differing, 'declared': sorted(declared)}
    if len(cohort) != 30:
        red(2, f'cohort has {len(cohort)} instruments, not 30')
    if set(differing) != set(declared):
        red(2, f'undeclared drift {sorted(set(differing) - set(declared))}; declared but unmoved {sorted(set(declared) - set(differing))}')
    if report['red']:
        return finish(report, write)

    originals = {p: (PROJECT / p).read_bytes() for p in list(SHELL) + sorted(declared)}
    (args.out / 'backup').mkdir()
    for p, raw in originals.items():
        target = args.out / 'backup' / p; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    try:
        for p, (source, frozen, _) in SHELL.items():
            raw = subprocess.run(['git', 'show', source], cwd=ROOT, capture_output=True, check=True).stdout
            if sha(raw) != frozen:
                raise SystemExit('generation-76 bytes differ: ' + p)
            (PROJECT / p).write_bytes(raw)
        report['steps']['2']['shellRestoredRead'] = completion(args.out, 'step2-shell-restored')
        write()

        # 3 -- shell and every declared tool restored
        with tarfile.open(COHORT_DIR / 'frozen-sources.tar.gz') as archive:
            members = {m.name: m for m in archive.getmembers()}
            for p in sorted(declared):
                member = members.get('instrument/' + p) or members.get('./instrument/' + p)
                if member is None:
                    raise SystemExit('frozen archive has no ' + p)
                raw = archive.extractfile(member).read()
                if sha(raw) != cohort[p]:
                    raise SystemExit('frozen archive bytes differ from the cohort: ' + p)
                (PROJECT / p).write_bytes(raw)
        step3 = completion(args.out, 'step3-all-restored')
        recorded = [{k: s.get(k) for k in ('population', 'conclusion', 'required', 'observed', 'counts')}
                    for s in json.loads((COHORT_DIR / 'completion-read-01.json').read_text())['stages']]
        step3['equalsCompletionRead01'] = step3['stages'] == recorded
        report['steps']['3'] = step3; write()
        if step3['exit'] != 0 or not step3['equalsCompletionRead01']:
            red(3, 'the read with everything restored did not exit 0 with the recorded stages')
    finally:
        # 6 -- put back, always
        for p, raw in originals.items():
            (PROJECT / p).write_bytes(raw)
        back = {p: sha((PROJECT / p).read_bytes()) for p in originals}
        problems = []
        for p, (_, _, cutover) in SHELL.items():
            if back[p] != cutover: problems.append(f'{p} is not the cutover bytes')
        for p, e in declared.items():
            if back[p] != e.get('liveSha256'): problems.append(f'{p}: live {back[p]} is not the declared liveSha256')
            if back[p] == cohort[p]: problems.append(f'{p}: declared but unmoved')
        status = subprocess.run(['git', 'status', '--porcelain', '--', 'wasm_sdk_probe'], cwd=ROOT, capture_output=True, text=True).stdout
        report['steps']['6'] = {'liveAfter': back, 'gitStatusAfter': status, 'problems': problems}
        if status.strip(): problems.append('tracked change left under wasm_sdk_probe/')
        if problems: red(6, '; '.join(problems))
        write()

    # 4 -- native run-03 re-read
    target = args.out / 'step4-native-run-03.json'
    step4 = run(args.out, 'step4-native-run-03', [sys.executable, '-I', str(PROJECT / 'tools/read_v23_native_s5_type.py'),
                                                str(NATIVE / 'run-03'), '--output', str(target)], cwd=PROJECT)
    step4['equalsReader03'] = target.is_file() and json.loads(target.read_text()) == json.loads((NATIVE / 'reader-03.json').read_text())
    report['steps']['4'] = step4
    if step4['exit'] != 0 or not step4['equalsReader03']:
        red(4, 'native run-03 re-read differs')

    # 5 -- E1-C
    step5 = run(args.out, 'step5-e1-c', [sys.executable, '-I', str(PROJECT / 'tools/check_e1_c_bundle_intact.py')], cwd=PROJECT)
    out5 = (args.out / 'step5-e1-c.stdout.txt').read_text()
    step5['intact'] = '"intact": true' in out5
    report['steps']['5'] = step5
    if step5['exit'] != 0 or not step5['intact']:
        red(5, 'E1-C not intact')

    # 7 -- report: the four-arm cohort
    four = json.loads(FOUR_ARMS.read_text())['instrumentSources']
    moved = sorted(p for p, want in four.items() if sha((PROJECT / p).read_bytes()) != want)
    report['steps']['7'] = {'instruments': len(four), 'differing': moved, 'allowed': sorted(set(declared) | PRE_V24_MOVES)}
    if not set(moved) <= set(declared) | PRE_V24_MOVES:
        red(7, f'undeclared drift against the four-arm cohort: {sorted(set(moved) - set(declared) - PRE_V24_MOVES)}')
    return finish(report, write)


def finish(report, write):
    report['verdict'] = 'V0PP_HOLDS' if not report['red'] else 'V0PP_RED'
    write()
    print(json.dumps({'verdict': report['verdict'], 'red': report['red']}, ensure_ascii=False))
    return 0 if not report['red'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
