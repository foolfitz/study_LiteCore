#!/usr/bin/env python3
"""One-off: every report's static (and staticAfter where present) must read host 0.2.23, buildId c3c22d9294de068a, page ccb67a52...  Exit 1 on mismatch."""
import json, sys
HOST, BUILD, PAGE = "0.2.23", "c3c22d9294de068a", "ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e"
bad = 0
for p in sys.argv[1:]:
    r = json.load(open(p))
    for key in ("static", "staticAfter"):
        s = r.get(key)
        if s is None:
            print(f"{p}: {key} absent (not recorded by this probe)")
            continue
        sb = s.get("shellBundle") or {}
        ok = s.get("hostVersion") == HOST and s.get("buildId") == BUILD and s.get("servedPage") == PAGE and s.get("distPage") == PAGE
        print(f"{p}: {key} hostVersion={s.get('hostVersion')} hostCommit={s.get('hostCommit')} hostDirty={s.get('hostDirty')} buildId={s.get('buildId')} "
              f"servedPage={str(s.get('servedPage'))[:12]} distPage={str(s.get('distPage'))[:12]} servedSession={str(s.get('servedSession'))[:12]} "
              f"shellBundle.exit={sb.get('exit')} manifest={sb.get('manifest')} sha={str(sb.get('sha256'))[:12]} problems={sb.get('problems')} -> {'OK' if ok else 'MISMATCH'}")
        bad += not ok
sys.exit(1 if bad else 0)
