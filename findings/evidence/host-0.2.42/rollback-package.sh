#!/usr/bin/env bash
# Functional engine rollback to exact 0.2.41 bytes, preserving host label 0.2.42 (derived from host-0.2.41/rollback-package.sh, not edited).
# Closed list of differences: these comment lines; EVIDENCE host-0.2.41 -> host-0.2.42; the installer it loads (install-0.2.42.py,
# module name host042_install); one added assert that release.json's oldArchive is the exact 0.2.41 archive
# (host-0.2.41-engine-829a988e199ebc43); the message 0.2.40/0.2.41 -> 0.2.41/0.2.42.
# Prepared only. Requires the owner-confirmed shared slot used by the install.
set -euo pipefail
APP=/home/jiajun/Projects/Nextcloud_Apps/litecore
EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.42
python3 - "$EVIDENCE" "$APP" <<'PY'
import importlib.util,json,subprocess,sys
from pathlib import Path
out,app=map(Path,sys.argv[1:]);spec=importlib.util.spec_from_file_location('host042_install',out/'install-0.2.42.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.slot();release=json.loads((out/'release.json').read_bytes())
assert release['oldArchive']==str(m.SDK/'build/archive/host-0.2.41-engine-829a988e199ebc43')
assert m.command(['git','rev-parse','HEAD'])==release['hostCommit'] and not m.command(['git','status','--porcelain'])
assert m.tree(app/'engine')==m.tree(Path(release['archive']))
subprocess.run(['rsync','-a','--delete','--exclude','ATTRIBUTION.md',release['oldArchive']+'/',str(app/'engine')+'/'],check=True)
assert m.tree(app/'engine')==m.tree(Path(release['oldArchive']))
print('Exact 0.2.41 engine restored; host label stays 0.2.42; full K remains unestablished.')
PY
