# F4-81: the four ABI6 product arms on frozen generation 81 (v27), both browsers (2026-10-30)

Spec `specs/SPEC-M3-v27-finding-176 7.3` F4-81.

The tools are `wasm_sdk_probe/tools/run_v81_four_arms.py`, `judge_v81_product_four_arms.py` and `v81_four_arms_identity.py`, committed `33842e1fe` before the first run. They are closed-list derivations of the v80 tools (docstrings); the bound parents are not edited. Stale-value scan: `../stale-scan/`.

**Preflight** (no browser):
- `preflight-ready/`: `READY`. The shell manifest is overridden to `e2/editor-shell-v2-bundle-v81.json` (file `91f18023…`); the v27 profile, the page `b63d8ee5`, and the live shell equal frozen 81.
- Declared identity reds, both `NOT_ESTABLISHED`:
  - `preflight-red-without-override/`: the tool default v76, so the served narrow client is not that generation;
  - `preflight-red-v80-manifest/`: the served page is not generation 80's.

**Runs:**
- `chrome/` (9.6 min) and `firefox/` (9.9 min): wrapper exit 0, all four arms PASS in each browser.
- `aggregate-judge.json` (`judge_v81_product_four_arms.py` over both `report.v23-four-arms`, absolute paths): **24/24 PASS**, `problems: []` (insert-then-shift, merge-then-shift, held-shift-one-second, held-shift-two-seconds; 3 rounds x 2 browsers each).
