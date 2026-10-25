#!/usr/bin/env python3
"""Run the existing finite autosave population against the built v2 engine."""
import hashlib
import json
from pathlib import Path
import sys

import probe_calc_autosave as autosave
from probe_calc_range_format import mirror

PROFILE=autosave.PROJECT/'build/ods/editor-v2/profile'

def main():
    if not (PROFILE/'sdk-manifest.json').exists():raise SystemExit('owner v2 build required')
    autosave.mirror=lambda out,_profile:mirror(out,PROFILE)
    result=autosave.main()
    out=Path(sys.argv[sys.argv.index('--out')+1])
    (out/'v2-runner.json').write_text(json.dumps({'profile':str(PROFILE.resolve()),
        'wrapperSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runnerSha256':hashlib.sha256(Path(autosave.__file__).read_bytes()).hexdigest()},indent=2)+'\n')
    return result

if __name__=='__main__':raise SystemExit(main())
