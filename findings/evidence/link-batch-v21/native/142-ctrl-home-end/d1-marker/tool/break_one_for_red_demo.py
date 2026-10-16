#!/usr/bin/env python3
"""Make read_marker.py go red on deliberately broken copies of one saved file.

Usage: python3 -I break_one_for_red_demo.py OUT_DIR FIXTURES_DIR ARMS_JSON_142 OUT_142 SCRATCH_DIR

Three scratch copies of OUT_DIR, the reader run on each (nothing in OUT_DIR is touched):
  0. unbroken copy                                             -> must exit 0
  1. a1-home-mid/r2.fodt.gz: the marker moved one character
     right ('ZAlpha' -> 'AZlpha'), file otherwise intact       -> must exit 1
  2. t-home-B2-n1/r3.fodt.gz: the XML cut off 200 bytes early   -> must exit 1
Prints each exit status and the reader's RED lines. Exits 1 if any case does not
behave as stated.
"""
import gzip
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def main():
    out, fixtures, arms142, out142, scratch = (pathlib.Path(x) for x in sys.argv[1:6])
    ok = True

    def case(title, mutate, want):
        nonlocal ok
        d = scratch / f'case-{title.split(".")[0]}'
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(out, d)
        what = mutate(d)
        p = subprocess.run([sys.executable, '-I', str(HERE / 'read_marker.py'), str(d), str(fixtures),
                            str(arms142), str(out142)], capture_output=True, text=True)
        lines = p.stdout.strip().splitlines()
        tail = lines[lines.index('RED:'):] if 'RED:' in lines else lines[-1:]
        good = p.returncode == want
        ok = ok and good
        print(f'## {title}')
        print(f'change: {what}')
        print(f'reader exit {p.returncode} (want {want})')
        for ln in tail:
            print(f'  {ln}')
        print(f'-> {"as stated" if good else "NOT as stated"}')
        print()

    def nothing(d):
        return 'none'

    def move_marker(d):
        f = d / 'a1-home-mid' / 'r2.fodt.gz'
        raw = gzip.decompress(f.read_bytes())
        assert raw.count(b'ZAlpha') == 1, 'expected exactly one ZAlpha'
        f.write_bytes(gzip.compress(raw.replace(b'ZAlpha', b'AZlpha'), mtime=0))
        return "a1-home-mid/r2.fodt.gz: 'ZAlpha' -> 'AZlpha' (one byte pair swapped, XML still valid)"

    def truncate(d):
        f = d / 't-home-B2-n1' / 'r3.fodt.gz'
        raw = gzip.decompress(f.read_bytes())
        f.write_bytes(gzip.compress(raw[:-200], mtime=0))
        return f't-home-B2-n1/r3.fodt.gz: last 200 of {len(raw)} bytes removed'

    case('0. unbroken copy', nothing, 0)
    case('1. marker moved by one character', move_marker, 1)
    case('2. saved XML truncated', truncate, 1)
    print('ALL AS STATED' if ok else 'SOMETHING WAS NOT AS STATED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
