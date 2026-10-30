#!/usr/bin/env python3
"""S3's and PL-1's document (SPEC-M3-v27-finding-176 7.3 S3, 7.2 PL-1): finding 176's native fixture
`two-plain.fodt` ("Plain first" / "E1-EMPTY-AFTER"), saved ONCE as ODT by the native core.

The native core is the one finding 176's native arm ran on (`native-lok-26-8/build/instdir`, its
`identity.json`); the save is `soffice --headless --convert-to odt` with a fresh user profile in a temporary
directory (storeToURL, the call LOK's saveAs makes).  The input is checked against the native arm's SHA256SUMS
before use.  The receipt records argv, exit code, seconds, the core's buildid, the input and output sha256.

  python3 -I make_two_plain_odt.py --out DIR      (DIR must not exist)
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
FIXTURES = ROOT / 'findings/evidence/176/native/fixtures'
SOURCE = FIXTURES / 'two-plain.fodt'
INSTALL = ROOT / 'native-lok-26-8/build/instdir/program'


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    out = ap.parse_args().out.resolve()
    if out.exists():
        ap.error('output must be fresh')
    sums = dict(line.split()[::-1] for line in (FIXTURES / 'SHA256SUMS').read_text().splitlines() if line.strip())
    if sha(SOURCE) != sums['two-plain.fodt']:
        ap.error('two-plain.fodt differs from the native arm SHA256SUMS')
    out.mkdir(parents=True)
    loadavg = open('/proc/loadavg').read().split()[:3]
    work = pathlib.Path(tempfile.mkdtemp(prefix='two-plain-'))
    try:
        shutil.copyfile(SOURCE, work / 'two-plain.fodt')
        argv = [str(INSTALL / 'soffice'), f'-env:UserInstallation={(work / "profile").as_uri()}', '--headless',
                '--norestore', '--convert-to', 'odt', '--outdir', str(work / 'out'), str(work / 'two-plain.fodt')]
        t0 = time.monotonic()
        result = subprocess.run(argv, capture_output=True, text=True, timeout=180)
        seconds = round(time.monotonic() - t0, 2)
        produced = work / 'out' / 'two-plain.odt'
        if produced.is_file():
            shutil.copyfile(produced, out / 'two-plain.odt')
    finally:
        shutil.rmtree(work, ignore_errors=True)
    versionrc = (INSTALL / 'versionrc').read_text()
    receipt = {'schema': 1, 'argv': argv, 'exitCode': result.returncode, 'seconds': seconds,
               'stdout': result.stdout, 'stderr': result.stderr,
               'buildid': next((l.split('=', 1)[1] for l in versionrc.splitlines() if l.startswith('buildid=')), None),
               'input': {'path': str(SOURCE.relative_to(ROOT)), 'sha256': sha(SOURCE)},
               'output': {'path': 'two-plain.odt', 'sha256': sha(out / 'two-plain.odt')}
               if (out / 'two-plain.odt').is_file() else None,
               'loadavgBefore': loadavg}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps({k: receipt[k] for k in ('exitCode', 'seconds', 'buildid', 'output')}, indent=1))
    return 0 if receipt['output'] and result.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
