#!/usr/bin/env python3
"""T1 ahead of the cut-over: the unchanged typing probe, with the tree's page repointed at a profile in the mirror only (the
same `repointed_page` the merge runner uses).  dist/ and web/ do not change.  argv: PROFILE BROWSER DOCUMENT GAP CHARS OUT"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4] / "wasm_sdk_probe"
sys.path.insert(0, str(ROOT / "tools"))
import probe_typing_latency as p
profile, browser, document, gap, chars, out = sys.argv[1:7]
source = p.pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8")
page, _, _ = p.pp.repointed_page(source, profile, p.DIST / "profiles" / profile / "sdk-manifest.json")
build = p.pp.build_mirror
p.pp.build_mirror = lambda src, mirror, overrides: build(src, mirror, {**overrides, "e2-editor-app.js": page.encode("utf-8")})
sys.argv = ["probe_typing_latency.py", "--browser", browser, "--document", document, "--gap", gap, "--chars", chars, "--out", out]
raise SystemExit(p.main())
