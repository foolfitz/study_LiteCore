#!/usr/bin/env python3
"""S4's three other documents (SPEC-M3-v28-last-line-fallback 7.3 S4-b, S4-d): native-q52's fixtures, each saved
ONCE as ODT by the native core.  Derived from findings/evidence/v27-176/fixture-two-plain/make_two_plain_odt.py
(S3's maker, not edited); the differences are the list of inputs and their SHA256SUMS.

  bulleted-last.fodt          fixtures-v6        "Plain first" + an empty bullet item, last  (S4-b none)
  realheading-last.fodt       fixtures-headings  "Plain first" + an empty real Heading 1, last (S4-b body)
  table-then-empty-last.fodt  fixtures           "Plain first" + a one-cell table ("Cell text") + an empty
                                                 paragraph, last (S4-d)

Each input is checked against its directory's SHA256SUMS; `soffice --headless --convert-to odt` from
`native-lok-26-8/build/instdir` (the core the native arms ran on), a fresh user profile per input.

  python3 -I make_s4_odts.py --out DIR      (DIR must not exist)
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
Q52 = ROOT / 'findings/evidence/176/native-q52'
INPUTS = [Q52 / 'fixtures-v6/bulleted-last.fodt', Q52 / 'fixtures-headings/realheading-last.fodt',
          Q52 / 'fixtures/table-then-empty-last.fodt']
INSTALL = ROOT / 'native-lok-26-8/build/instdir/program'


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    out = ap.parse_args().out.resolve()
    if out.exists():
        ap.error('output must be fresh')
    for source in INPUTS:
        sums = dict(l.split()[::-1] for l in (source.parent / 'SHA256SUMS').read_text().splitlines() if l.strip())
        if sha(source) != sums[source.name]:
            ap.error(f'{source} differs from its SHA256SUMS')
    out.mkdir(parents=True)
    versionrc = (INSTALL / 'versionrc').read_text()
    buildid = next((l.split('=', 1)[1] for l in versionrc.splitlines() if l.startswith('buildid=')), None)
    receipts, ok = [], True
    for source in INPUTS:
        loadavg = open('/proc/loadavg').read().split()[:3]
        work = pathlib.Path(tempfile.mkdtemp(prefix='s4-odt-'))
        try:
            shutil.copyfile(source, work / source.name)
            argv = [str(INSTALL / 'soffice'), f'-env:UserInstallation={(work / "profile").as_uri()}', '--headless',
                    '--norestore', '--convert-to', 'odt', '--outdir', str(work / 'out'), str(work / source.name)]
            t0 = time.monotonic()
            result = subprocess.run(argv, capture_output=True, text=True, timeout=180)
            seconds = round(time.monotonic() - t0, 2)
            name = source.stem + '.odt'
            produced = work / 'out' / name
            if produced.is_file():
                shutil.copyfile(produced, out / name)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        done = (out / name).is_file() and result.returncode == 0
        ok = ok and done
        receipts.append({'argv': argv, 'exitCode': result.returncode, 'seconds': seconds, 'stdout': result.stdout,
                         'stderr': result.stderr, 'buildid': buildid, 'loadavgBefore': loadavg,
                         'input': {'path': str(source.relative_to(ROOT)), 'sha256': sha(source)},
                         'output': {'path': name, 'sha256': sha(out / name)} if (out / name).is_file() else None})
    (out / 'receipt.json').write_text(json.dumps({'schema': 1, 'documents': receipts}, indent=1) + '\n')
    print(json.dumps([{k: r[k] for k in ('exitCode', 'seconds', 'output')} for r in receipts], indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
