# F4-82: the four ABI6 product arms on frozen generation 82 (v28), both browsers (2026-10-30)

Spec `specs/SPEC-M3-v28-last-line-fallback.md` 7.3 F4-82.

Tools: `wasm_sdk_probe/tools/run_v82_four_arms.py`, `judge_v82_product_four_arms.py`, `v82_four_arms_identity.py`, committed `00e3f352f` before the first run; closed-list derivations of the v81 tools by `../derive/derive_v82_tools.py`, the parents not edited. Stale-value scan: `../stale-scan/`.

**Preflight** (no browser):
- `preflight-ready/`: `READY`. Shell manifest overridden to `e2/editor-shell-v2-bundle-v82.json` (file `da4e595d…`); the v28 profile (= the v28 archive), the page `3b0a2ebb` and the live shell equal frozen 82.
- Declared identity reds, both `NOT_ESTABLISHED`:
  - `preflight-red-without-override/`: the tool default v76, so the served narrow client is not that generation;
  - `preflight-red-v81-manifest/`: the served paragraph client is not generation 81's (82 differs from 81 in the client and the page).

**Runs** (`../f3-f4-run.sh`): `chrome/` (22:44-22:54) and `firefox/` (22:54-23:04), wrapper exit 0, all four arms PASS in each browser.

`aggregate-judge.json` (`judge_v82_product_four_arms.py` over both `report.v23-four-arms`, absolute paths): **24/24 PASS**, `problems: []` (insert-then-shift, merge-then-shift, held-shift-one-second, held-shift-two-seconds; 3 rounds x 2 browsers each).
