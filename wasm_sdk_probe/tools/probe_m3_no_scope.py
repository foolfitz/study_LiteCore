#!/usr/bin/env python3
"""Review 2026-10-06 item 8: the editor on a browser without CSS @scope.

Host 0.2.6 wraps the product's stylesheet in `@scope (#litecore-editor-root)`
(finding 110).  A browser without @scope drops that whole block, so the
product page renders unstyled.  Firefox 157 with `layout.css.at-scope.enabled`
off stands in for such a browser (Firefox ESR 140 is not installed here).

One Firefox, one open of the usual test file, then: does the page see
CSSScopeRule, what the host decided (`data-litecore` .scope, host 0.2.7+), the
A3-1 inventory (every visible control and text outside the kept set), and
whether the parts the product sheet hides are visible.

  probe_m3_no_scope.py --out REPORT [--scope on|off]

A one-time measurement, not a criterion (spec §9.6).  Never run it beside
another M3 runner: it clears the whole oc_files_lock table.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_production_ui import (  # noqa: E402
    DOC, HOST, INVENTORY, KEEP_ACTIONS, KEEP_IDS, NAME, SCRATCH, TEXT_PLACES, Server, quiet, static_facts,
)
from check_m3_locks import login, open_from_files  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
from probe_m3_gate0_coep import firefox_profile, sha256_file, utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402

HIDDEN_BY_SHEET = ["#notice", "#expired", "#a11y-structure", "#sink"]
LOOK = """(() => { const out = { scopeRule: typeof CSSScopeRule };
  const vis = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return { w: Math.round(r.width), h: Math.round(r.height), display: s.display, visibility: s.visibility,
             opacity: s.opacity, visible: r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && parseFloat(s.opacity) > 0 }; };
  out.parts = Object.fromEntries(ARG_SELECTORS.map(q => [q, vis(document.querySelector(q))]));
  const u = document.getElementById('litecore-unscoped'); out.unscopedSheet = u ? u.media : null;
  return out; })()"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scope", choices=("on", "off"), default="off")
    args = parser.parse_args()
    instance = Instance(DEFAULT_DDEV)
    server = Server(instance, [])
    doc = DOC.read_bytes()
    record: dict[str, Any] = {"probe": "probe_m3_no_scope.py", "probeSha256": sha256_file(Path(__file__)),
                              "startedAt": utc_now(), "static": static_facts(DEFAULT_DDEV),
                              "pref": {"layout.css.at-scope.enabled": args.scope == "on"}}
    record["clearedLocks"] = server.clear_locks()
    record["upload"] = server.upload(server.admin, NAME, doc)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    session = FirefoxSession("cold", profile_dir=firefox_profile(SCRATCH / f"ff-noscope-{time.monotonic_ns()}"),
                             extra_prefs={"layout.css.at-scope.enabled": args.scope == "on"})
    record["version"] = getattr(session, "version", None)
    try:
        session.command("POST", "/window/rect", {"width": 1850, "height": 1080})
        record["login"] = login(session, instance.base, "admin", instance.password)
        open_from_files(session, instance.base, "", NAME, record)
        record["opened"] = quiet(session, 90)
        record["look"] = evaluate(session, LOOK.replace("ARG_SELECTORS", json.dumps(HIDDEN_BY_SHEET)))
        record["inventory"] = evaluate(session, INVENTORY.replace("ARG_ACTIONS", json.dumps(KEEP_ACTIONS))
                                       .replace("ARG_IDS", json.dumps(KEEP_IDS)).replace("ARG_PLACES", json.dumps(TEXT_PLACES)))
        record["hostScope"] = (evaluate(session, HOST) or {}).get("scope")
        shot = args.out.with_suffix(".png")
        try:
            import base64
            shot.write_bytes(base64.b64decode(session.command("GET", "/screenshot")))
            record["screenshot"] = shot.name
        except Exception:  # noqa: BLE001 -- the picture is a convenience, the record is the evidence
            record["screenshotError"] = traceback.format_exc().strip().splitlines()[-1]
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        finally:
            server.clear_locks()
            record["completedAt"] = utc_now()
            args.out.write_text(json.dumps(record, ensure_ascii=False, indent=1))
    look, inventory = record.get("look") or {}, record.get("inventory") or {}
    print(json.dumps({"scopeRule": look.get("scopeRule"), "hostScope": record.get("hostScope"),
                      "shown": [q for q, v in (look.get("parts") or {}).items() if (v or {}).get("visible")],
                      "badControls": len(inventory.get("badControls") or []),
                      "badText": len(inventory.get("badText") or []), "fatal": bool(record.get("fatal"))},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
