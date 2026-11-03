#!/usr/bin/env bash
# Functional engine rollback to exact 0.2.53 bytes, preserving host label 0.2.54 (derived from host-0.2.47/rollback-package.sh, not edited).
# 0.2.54 ships 0.2.53's engine package byte for byte, so this restores the same bytes: batch 6 is host source (the New spreadsheet creator,
# blank-ods/, img/), which this script does not touch.  Taking batch 6 back is a host commit on a new version, not this script.
# Closed list of differences: these comment lines; EVIDENCE host-0.2.47 -> host-0.2.48; the installer it loads (install-0.2.48.py,
# module name host048_install); the oldArchive assert names the exact 0.2.47 archive (host-0.2.47-engine-268e3009dbf33a5a);
# the message 0.2.44/0.2.45 -> 0.2.45/0.2.46.
# Prepared only. Run with host-stack/bin first on PATH (the installer's slot() checks it).
set -euo pipefail
APP=/home/jiajun/Projects/Nextcloud_Apps/litecore
EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.54
python3 - "$EVIDENCE" "$APP" <<'PY'
import importlib.util,json,subprocess,sys
from pathlib import Path
out,app=map(Path,sys.argv[1:]);spec=importlib.util.spec_from_file_location('host054_install',out/'install-0.2.54.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.slot();release=json.loads((out/'release.json').read_bytes())
assert release['oldArchive']==str(m.SDK/'build/archive/host-0.2.53-engine-89860962782b3a21')
assert m.command(['git','rev-parse','HEAD'])==release['hostCommit'] and not m.command(['git','status','--porcelain'])
assert m.tree(app/'engine')==m.tree(Path(release['archive']))
subprocess.run(['rsync','-a','--delete','--exclude','ATTRIBUTION.md',release['oldArchive']+'/',str(app/'engine')+'/'],check=True)
assert m.tree(app/'engine')==m.tree(Path(release['oldArchive']))
print('Exact 0.2.53 engine restored; host label stays 0.2.54; full K remains unestablished.')
PY
