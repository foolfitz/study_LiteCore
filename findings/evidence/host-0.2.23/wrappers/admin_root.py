#!/usr/bin/env python3
"""One-off: list the admin root (PROPFIND depth 1) via the probes' Instance helper; with names after '--delete', DELETE exactly those."""
import re, sys, urllib.parse
sys.path.insert(0, "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
from check_m3_skeleton_open import DEFAULT_DDEV, Instance
inst = Instance(DEFAULT_DDEV)
def listing():
    body = b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:getlastmodified/></d:prop></d:propfind>'
    status, ans = inst.dav("PROPFIND", "", body, {"Depth": "1", "Content-Type": "application/xml"})
    print(f"PROPFIND depth 1 status {status}")
    for m in re.finditer(rb"<d:href>([^<]+)</d:href>.*?<d:getlastmodified>([^<]+)</d:getlastmodified>", ans, re.S):
        href = urllib.parse.unquote(m.group(1).decode())
        print("   ", href.split("/files/admin/", 1)[-1] or "(root)", "|", m.group(2).decode())
args = sys.argv[1:]
if "--delete" in args:
    i = args.index("--delete")
    print("LIST before"); listing()
    for n in args[i + 1:]:
        st, _ = inst.dav("DELETE", n); print(f"DELETE {n} -> {st}")
    print("LIST after"); listing()
else:
    listing()
