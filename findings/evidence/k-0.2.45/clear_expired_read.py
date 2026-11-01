#!/usr/bin/env python3
"""Read the lock property of the folders that hold an expired lock row: files_lock then drops the row itself.  No write, no lock-table edit."""
import importlib
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
s = importlib.import_module('check_m3_' + 'skeleton_open')
i = s.Instance(s.DEFAULT_DDEV)
rows = i._run(['ddev', 'mysql', '-B', '-N', '-e', "SELECT f.path FROM oc_files_lock l JOIN oc_filecache f ON f.fileid=l.file_id WHERE UNIX_TIMESTAMP() > l.creation + l.ttl;"]).splitlines()
body = b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns"><d:prop><nc:lock/></d:prop></d:propfind>'
for path in rows:
    name = re.sub(r'^files/', '', path)
    print(name, i.dav('PROPFIND', name, body, {'Depth': '0', 'Content-Type': 'application/xml'})[0])
