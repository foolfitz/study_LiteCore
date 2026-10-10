#!/usr/bin/env python3
"""The counted typing-latency probe (`probe_typing_latency.py`, unchanged) at a given devicePixelRatio and CSS
window -- SPEC-M3-production-ui §17.4 C2 (ratio 2 wide).  NOT diagnostic: nothing in the page, the worker or
the probe is changed; only the browser is sized, the way the R2 wrapper sizes it
(`findings/evidence/typing-latency/r2-blit-bytes/blit_bytes_probe.py`): Chrome
`Emulation.setDeviceMetricsOverride` before the first navigation, Firefox `layout.css.devPixelsPerPx` and
`MOZ_HEADLESS_WIDTH/HEIGHT` in device pixels.  The report is the probe's, plus `dprRequested`,
`windowRequested`, and `runner` = "probe_typing_latency_view.py <its sha256[:16]> over probe <probe's [:16]>".

  probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser chrome --document owner --gap 80 --chars 20 --out R.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import probe_typing_latency as ptl  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

PROBE = hashlib.sha256((TOOLS / "probe_typing_latency.py").read_bytes()).hexdigest()


def take(flag: str) -> str:
    i = sys.argv.index(flag)
    value = sys.argv[i + 1]
    del sys.argv[i:i + 2]
    return value


dpr = float(take("--dpr"))
window = tuple(int(v) for v in take("--window").split("x"))
os.environ["MOZ_HEADLESS_WIDTH"] = str(round(window[0] * dpr))
os.environ["MOZ_HEADLESS_HEIGHT"] = str(round(window[1] * dpr))
native_navigate, NativeFirefox = pp.navigate, pp.FirefoxSession


def navigate_sized(session, *args, **kwargs):
    if isinstance(session, pp.ChromeSession) and not getattr(session, "_view_sized", False):
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": window[0], "height": window[1], "deviceScaleFactor": dpr, "mobile": False})
        session._view_sized = True
    return native_navigate(session, *args, **kwargs)


pp.navigate = navigate_sized
pp.FirefoxSession = lambda mode: NativeFirefox(mode, extra_prefs={"layout.css.devPixelsPerPx": str(dpr)})
code = ptl.main()
out = Path(sys.argv[sys.argv.index("--out") + 1])
report = json.loads(out.read_text())
report["dprRequested"] = dpr
report["windowRequested"] = list(window)
report["runner"] = (f"probe_typing_latency_view.py {hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}"
                    f" over probe {PROBE[:16]}")
out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
sys.exit(code)
