#!/usr/bin/env python3
"""Per run of repeat.sh: on-screen and commit median / max, keys over 100 ms (README.md here)."""
import json
import statistics
import sys
from pathlib import Path

here = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent)
paths = sorted(here.glob("run-*.json"))
if not paths:
    sys.exit(f"no run-*.json under {here}")
for path in paths:
    r = json.loads(path.read_text())
    rows = r.get("rows") or []
    screens = [x.get("onScreenMs") for x in rows if x.get("onScreenMs") is not None]
    commits = [x.get("revisionMs") for x in rows if x.get("revisionMs") is not None]
    slow = [(i + 1, x.get("onScreenMs")) for i, x in enumerate(rows) if (x.get("onScreenMs") or 0) >= 100]
    print(f"{path.name} page {str(r.get('page'))[:8]} rows {len(rows)} "
          f"screen median {statistics.median(screens) if screens else None} max {max(screens) if screens else None} "
          f"commit median {statistics.median(commits) if commits else None} max {max(commits) if commits else None} "
          f"slow>=100 {slow}")
