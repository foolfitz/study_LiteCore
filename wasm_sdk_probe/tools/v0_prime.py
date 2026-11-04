#!/usr/bin/env python3
"""V0' for a new shell generation: the previous generation and the last counted K still re-read (CLAUDE.md, the section on
cadence, item 3).  One tool for every generation from 90 on, in place of the per-generation run_v0_prime.py copies that
re-read twelve stages (findings/evidence/ms-formats/v0-89/ was the last).

  v0_prime.py --generation N --k-reader PY --k-log DIR --k-verdict JSON --out NEW_DIR      (run from anywhere)

Stages, with the tree at generation N (e2/generations/generation-N.json) before and after:
  live      judge_product_four_arms.py --generation N-1 on N-1's committed F4 runs, on the generation-N tree: must be red
            (nonzero exit, no arm PASS) -- the reader binds the live shell, so the re-read below is not vacuous.
  previous  every module of N-1's bundle manifest, and web/e2-editor.html, whose bytes differ from N-1's is written back
            from N-1's frozenCommit; `make e2-c-assets` (copies only); source == dist == N-1's bytes; then the same reader
            re-reads N-1's F4 and must give the committed aggregate byte for byte, exit 0.  This is also the witness that
            the parametrised tools read a generation as the per-generation copies did (cadence item 2).
  k         the last counted K's reader on its chain log: exit 0, and its committed verdict file unchanged in git.
  put back  `git checkout HEAD --` the restored files, `make e2-c-assets`, every file back at generation N's bytes in
            source and dist, generation N's shell() holds, E1-C intact (tools/check_e1_c_bundle_intact.py).

Must not run while anything serves dist/ or copies the source tree into a mirror.  Writes only into NEW_DIR (and,
transiently, the restored files and their dist/ copies, put back in `finally`).  Every record carries this tool's sha256
and argv.  Verdict V0_PRIME_HOLDS iff every stage and the put-back hold.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

SDK = Path(__file__).resolve().parents[1]
REPO = SDK.parent
sys.path.insert(0, str(SDK / 'tools'))
from four_arms_identity import Generation  # noqa: E402

HTML = 'web/e2-editor.html'
PAGE = 'web/e2-editor-app.js'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dist_name(path):
    return {PAGE: 'dist/e2-editor-app.js', HTML: 'dist/e2-editor.html'}.get(path, 'dist/' + path)


def run(argv, cwd=SDK):
    started = time.monotonic()
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    return {'argv': argv, 'cwd': str(cwd), 'exit': p.returncode, 'seconds': round(time.monotonic() - started, 3),
            'stdoutTail': p.stdout[-2000:], 'stderrTail': p.stderr[-2000:]}


def wanted(gen):
    """{path: sha256} of generation `gen`: its bundle manifest's modules and the page HTML."""
    manifest = json.loads((SDK / gen.bundle).read_text())
    files = {r['path']: r['sha256'] for r in manifest['included']}
    files[HTML] = json.loads(gen.path.read_text())['htmlSha256']
    return files


def served(files):
    return {p: {'source': sha(SDK / p), 'dist': sha(SDK / dist_name(p))} for p in files}


def at(files, hashes):
    return all(hashes[p]['source'] == hashes[p]['dist'] == want for p, want in files.items())


def f4_argv(gen, out):
    f4 = json.loads(gen.path.read_text())['f4']
    return (['python3', 'tools/judge_product_four_arms.py', '--generation', str(gen.number)]
            + [str(REPO / r) for r in f4['runs']] + ['--out', str(out)]), REPO / f4['aggregate']


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--generation', type=int, required=True)
    parser.add_argument('--k-reader', type=Path, required=True)
    parser.add_argument('--k-log', type=Path, required=True)
    parser.add_argument('--k-verdict', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    now, prev = Generation(args.generation), Generation(args.generation - 1)
    now_files, prev_files = wanted(now), wanted(prev)
    report = {'tool': {'path': 'wasm_sdk_probe/tools/v0_prime.py', 'sha256': sha(__file__), 'argv': sys.argv[1:]},
              'generation': now.number, 'previous': prev.number, 'head': run(['git', 'rev-parse', 'HEAD'], REPO)['stdoutTail'].strip(),
              'generationFiles': {g.number: {'path': g.path.relative_to(REPO).as_posix(), 'sha256': g.file_sha256} for g in (now, prev)},
              'startedAt': time.time(), 'stages': {}}
    before = served(now_files)
    report['before'] = {'hashes': before, 'atGeneration': at(now_files, before)}
    if not report['before']['atGeneration']:
        (out / 'v0-prime.json').write_text(json.dumps(report, indent=1) + '\n')
        raise SystemExit(f'the tree is not generation {now.number} before V0prime; see {out}/v0-prime.json')
    restored = sorted(p for p, want in prev_files.items() if sha(SDK / p) != want)
    try:
        argv, committed = f4_argv(prev, out / f'live-red-f4-{prev.number}.json')
        live = run(argv)
        outcomes = None
        if (out / f'live-red-f4-{prev.number}.json').is_file():
            outcomes = {k: v['outcome'] for k, v in json.loads((out / f'live-red-f4-{prev.number}.json').read_text())['arms'].items()}
        live.update(armOutcomes=outcomes, ok=live['exit'] != 0 and outcomes is not None and all(v != 'PASS' for v in outcomes.values()))
        report['stages']['live'] = live

        stage = report['stages']['previous'] = {'restored': restored, 'from': json.loads(prev.path.read_text())['frozenCommit']}
        for path in restored:
            (SDK / path).write_bytes(subprocess.check_output(
                ['git', '-C', str(REPO), 'show', f"{stage['from']}:wasm_sdk_probe/{path}"]))
        stage['make'] = run(['make', 'e2-c-assets'])
        hashes = served(prev_files)
        stage['hashes'] = hashes
        stage['restoreOk'] = stage['make']['exit'] == 0 and at(prev_files, hashes)
        if stage['restoreOk']:
            argv, committed = f4_argv(prev, out / f'restored-f4-{prev.number}.json')
            reread = run(argv)
            target = out / f'restored-f4-{prev.number}.json'
            reread.update(committed=str(committed.relative_to(REPO)),
                          byteIdentical=target.is_file() and target.read_bytes() == committed.read_bytes())
            reread['ok'] = reread['exit'] == 0 and reread['byteIdentical']
            stage['f4'] = reread
        stage['ok'] = stage['restoreOk'] and stage.get('f4', {}).get('ok', False)

        k = run(['python3', str(args.k_reader.resolve()), str(args.k_log.resolve())], REPO)
        verdict = args.k_verdict.resolve().relative_to(REPO).as_posix()
        k['verdictFile'] = verdict
        k['verdictUnchanged'] = run(['git', 'diff', '--quiet', 'HEAD', '--', verdict], REPO)['exit'] == 0
        k['ok'] = k['exit'] == 0 and k['verdictUnchanged']
        report['stages']['k'] = k
    finally:
        back = {'checkout': run(['git', '-C', str(REPO), 'checkout', 'HEAD', '--'] + [f'wasm_sdk_probe/{p}' for p in restored]) if restored else None}
        back['make'] = run(['make', 'e2-c-assets'])
        back['hashes'] = served(now_files)
        try:
            now.shell()
            back['shell'] = 'GENERATION_HOLDS'
        except Exception as error:  # noqa: BLE001 -- recorded; the verdict is red
            back['shell'] = f'{type(error).__name__}: {error}'
        e1c = subprocess.run(['python3', 'tools/check_e1_c_bundle_intact.py'], cwd=SDK, capture_output=True, text=True)
        (out / 'e1-c-after-put-back.json').write_text(e1c.stdout if e1c.returncode == 0 else '{}\n')
        e1c = {'exit': e1c.returncode, 'stderrTail': e1c.stderr[-2000:]}
        back['e1c'] = e1c
        back['ok'] = ((back['checkout'] is None or back['checkout']['exit'] == 0) and back['make']['exit'] == 0
                      and at(now_files, back['hashes']) and back['shell'] == 'GENERATION_HOLDS' and e1c['exit'] == 0)
        report['putBack'] = back
        stages = report['stages']
        holds = (all(stages.get(s, {}).get('ok') for s in ('live', 'previous', 'k')) and back['ok'])
        report['verdict'] = 'V0_PRIME_HOLDS' if holds else 'V0_PRIME_RED'
        report['finishedAt'] = time.time()
        (out / 'v0-prime.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
        print(report['verdict'])
    return 0 if report['verdict'] == 'V0_PRIME_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
