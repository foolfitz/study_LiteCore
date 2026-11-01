#!/usr/bin/env python3
"""S4 on v29 (SPEC-M3-v29-tick-pacing section 6 T3): tools/check_v82_last_line_bullet.py, unedited, with `after` naming v29.

`tools/v82_f_products.py` writes `after` as "dist/ as served": every module of generation 81 except the page and the client,
which must equal the tree and differ from 81, so it describes generation 83 too.  The one value that moves is the profile
and its archive, set here in process before the check imports it.  `before` stays generation 81 / v27: S4 still requires
083 to be red there.  The arguments, the exit code and the verdicts are the check's.
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

AFTER = ("e2-editor-v29", "build/archive/e2-editor-v29-e61e5890-worker-a5df83db")


def main() -> int:
    if "check_v82_last_line_bullet" in sys.modules:
        raise SystemExit("the check was imported before the override")
    import v82_f_products as products
    products.PROFILES["after"] = AFTER
    import check_v82_last_line_bullet as s4
    return s4.main()


if __name__ == "__main__":
    raise SystemExit(main())
