#!/usr/bin/env python3
"""ABI6 feature wrapper; inherited builders and their defaults stay unchanged."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import os
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_e2_editor_v5_profile as v5
import check_v23_feature_contract as contract
BASE_ACTION_MAP=v5.action_map

def action_map():
    actions=BASE_ACTION_MAP()
    for name in contract.MOVES:
        actions[name]['gestures']=['collapsed','range-single','range-cross']
        if name.startswith('move-line-'):
            actions[name]['limits']=[x for x in actions[name]['limits'] if x!='no-extend-selection']
    return actions

def main(argv=None):
    argv=list(sys.argv if argv is None else argv)
    parser=argparse.ArgumentParser(add_help=False,allow_abbrev=False)
    parser.add_argument('--profile',required=True)
    for field in ('loader','worker','wasm','exports','output'):parser.add_argument('--'+field,type=Path,required=True)
    args,_=parser.parse_known_args(argv[1:])
    if args.profile!=contract.PROFILE:raise SystemExit('feature builder requires exactly '+contract.PROFILE)
    if args.output.exists() and any(args.output.iterdir()):raise SystemExit('existing feature profile/partial files must be preserved')
    problems=contract.input_problems(args.worker,args.exports,args.wasm)+contract.actual_export_problems(args.loader,args.wasm)
    if problems:raise SystemExit('; '.join(problems))
    manifest=args.output/'sdk-manifest.json';printed=io.StringIO();validated=False
    original=(v5.ABI_VERSION,v5.action_map)
    try:
        reference=json.loads((contract.ARCHIVE/'sdk-manifest.json').read_text())
        v5.ABI_VERSION=6;v5.action_map=action_map
        with contextlib.redirect_stdout(printed):code=v5.main(argv)
        if code:return code
        candidate=json.loads(manifest.read_text())
        problems=contract.contract_problems(candidate,reference)+contract.binding_problems(candidate,args.output)
        if problems:raise SystemExit('; '.join(problems))
        summary=json.loads(printed.getvalue());summary.update(profile=contract.PROFILE,abiVersion=6,manifestSha256=contract.sha(manifest))
        print(json.dumps(summary,indent=2));validated=True;return 0
    finally:
        v5.ABI_VERSION,v5.action_map=original
        if not validated:
            try:
                if manifest.exists():
                    fd,failed=tempfile.mkstemp(prefix='sdk-manifest.failed-',suffix='.json',dir=args.output)
                    os.close(fd);os.replace(manifest,failed)
            finally:sys.stderr.write(printed.getvalue())
if __name__=='__main__':raise SystemExit(main())
