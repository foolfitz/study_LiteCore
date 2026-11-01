# F4-83: the four ABI6 product arms on frozen generation 83 (v29), both browsers (2026-11-01)

Spec section 6 T3, append 2. Tools: `tools/run_v83_four_arms.py`, `judge_v83_product_four_arms.py`, `v83_four_arms_identity.py`, closed-list derivations (`../derive/derive_v83_tools.py`), parents not edited; stale scan `../stale-scan/`.

**Preflight** (`../t3/f4-preflight-*`): READY; the two identity reds, exit 1 (tool default v76; the v82 manifest).

**First Chrome attempt refused, by the runner's own guard, before any browser** (`chrome-refused-foreign-cc1plus/`, `refused-*`): `foreignCpu.ok` false, a `cc1plus` from another project's build (`~/OSSII/study_OxOffice_AI`) at 99.8 %, load 5.45. Not a product result. Re-run when the machine was quiet.

**Runs**: `chrome/` (re-run) and `firefox/`, wrapper exit 0, all four arms PASS in each. `aggregate-judge.json`: **24/24 PASS**, `problems: []`.
