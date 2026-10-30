#!/usr/bin/env python3
"""SPEC-M3-v27-finding-176 10 (PIN): the core source C rests on, pinned in both trees before the link.

The files of section 10 (fable ruling 3 section 2's line numbers), hashed in:
  link    the core the product links against: the Makefile's LOSRC, read from `make -pn` (not written by hand),
          resolved from wasm_sdk_probe/
  native  the core the native evidence ran on: native-lok-26-8/src (findings/evidence/176/native/README.md)
The two trees agree on these files, or the difference is recorded and goes to a ruling (section 10).  This pins
SOURCE, not the compiled core.

  source_pin.py --write OUT.json
  source_pin.py --check PIN.json [--link-root DIR] [--native-root DIR]   (exit 0 iff every hash equals the pin)

The red case is --check with --link-root pointing at a copy whose one file has one byte changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / 'wasm_sdk_probe'
NATIVE = ROOT / 'native-lok-26-8/src'
FILES = {
    'sw/sdi/swriter.sdi': '5649',
    'sw/source/uibase/shells/textsh1.cxx': '1975-1982',
    'sw/source/uibase/wrtsh/move.cxx': '76-90, 396-406',
    'sw/source/core/crsr/pam.cxx': '410-423, 1238-1263',
    'sw/source/core/crsr/paminit.cxx': '46-47',
    'sw/source/core/crsr/crsrsh.cxx': '1438-1454',
}


def losrc():
    out = subprocess.run(['make', '-pn'], cwd=PROJECT, capture_output=True, text=True).stdout
    values = [l.split('=', 1)[1].strip() for l in out.splitlines() if l.startswith(('LOSRC :=', 'LOSRC =', 'LOSRC ?='))]
    if len(set(values)) != 1:
        raise SystemExit(f'LOSRC is not one value in make -pn: {values}')
    return (PROJECT / values[0]).resolve(), values[0]


def head(tree):
    run = subprocess.run(['git', '-C', str(tree), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    return run.stdout.strip() if run.returncode == 0 else None


def hashes(tree):
    return {rel: hashlib.sha256((tree / rel).read_bytes()).hexdigest() if (tree / rel).is_file() else None
            for rel in FILES}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', type=Path)
    g.add_argument('--check', type=Path)
    ap.add_argument('--link-root', type=Path)
    ap.add_argument('--native-root', type=Path)
    args = ap.parse_args()
    link_tree, link_value = losrc()
    link_tree = args.link_root.resolve() if args.link_root else link_tree
    native_tree = args.native_root.resolve() if args.native_root else NATIVE
    now = {'link': hashes(link_tree), 'native': hashes(native_tree)}
    if args.write:
        if args.write.exists():
            raise SystemExit(f'refusing to overwrite {args.write}')
        agree = {rel: now['link'][rel] is not None and now['link'][rel] == now['native'][rel] for rel in FILES}
        pin = {'tool': 'source_pin', 'spec': 'SPEC-M3-v27-finding-176 10',
               'link': {'makefileLOSRC': link_value, 'path': str(link_tree), 'gitHead': head(link_tree)},
               'native': {'path': str(native_tree), 'gitHead': head(native_tree)},
               'lines': FILES, 'sha256': now, 'treesAgree': agree, 'allAgree': all(agree.values())}
        args.write.write_text(json.dumps(pin, indent=1) + '\n')
        print(json.dumps({'allAgree': pin['allAgree'], 'disagree': [r for r, ok in agree.items() if not ok]}))
        return 0 if pin['allAgree'] else 1
    pin = json.loads(args.check.read_text())
    differ = [f'{side}:{rel}' for side in ('link', 'native') for rel in FILES if now[side][rel] != pin['sha256'][side][rel]]
    print(json.dumps({'check': 'PIN_HOLDS' if not differ else 'PIN_RED', 'differ': differ,
                      'linkRoot': str(link_tree), 'nativeRoot': str(native_tree)}))
    return 0 if not differ else 1


if __name__ == '__main__':
    sys.exit(main())
