# Handoff, 2026-10-08f — v19 is linked, bound and validated (X1-X7 all have a verdict; X5 and X7 pass after two fable rulings the owner asked for); the cutover is the owner's to approve

Picks up from `HANDOFF-2026-10-08e-reader-review-and-v19-plumbing-done-v56-freeze-next.md`. Its Next 5-7 are done. Its Next 8 (host 0.2.8, then R) has not started, because the cutover comes first and the owner approves it. Repository root `/home/jiajun/LibreOffice/study_LiteCore`; paths are relative to it. Entry points: this file; `findings/evidence/v19/RESULT.md`; spec `specs/SPEC-M3-paragraph-merge.md` §35 and §36 (the last two sections).

## What happened, in order (all 2026-10-08, +0800)

| Commit | What |
|---|---|
| `baea3540` | **Shell generation v56 frozen** (`b256fe04…`). It differs from v55 in exactly `narrow-editor-v2-client.js`, `narrow-editor-v2-session.js` (comment only) and `web/e2-editor-app.js`; still pins `e2-editor-v8`. `make e2-c-assets` copied only `dist/e2-editor-app.js`; `make test-e2-c-static` exit 0 (node 155+5, python 108); no anchor re-set. |
| `c0337ae3` | Runbook §0/§1 gates re-run after the freeze, all green (`v19/pre-link/gates-after-v56.txt`); `make -n` touches only v19 paths. |
| (owner, 19:42) | **The owner linked v19** with the runbook's `env -u … make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v19/sdk-manifest.json`. |
| `8da777d7` | Post-link §3 (v8/v15/v18 hashes unchanged, X1 `VERDICT PASS`, archive `build/archive/e2-editor-v19-1aafd4f9-worker-00882139/`, M1-1 unchanged) and **the binding**: `BINDING` = nine values from the runner's own `bound_values()` (no browser), each checked against a second source (`v19/post-link/README.md`); `test_nothing_is_bound_before_v56` → `test_bound_to_v19_after_v56`. Runner sha `73b2e9ff4b1e6fbe`. |
| `4a335888` | Predictions X2-X7, `chain.sh`, three reader copies from v18 with only their constants changed, each made red offline once. |
| `b8324a85`, `85334a1a` | The round's reports (chain 19:52-22:52, detached). |
| `8d9004f8`, `0ce96b32`, `7ac7fa3d` | X7: fable's ruling (owner chose "B: ask fable"), reader-only §34.1 (b) fix, re-judge `VERDICT PASS`, spec §35. |
| `6847b9ce`, `80385755` | X5: fable's ruling (owner chose "A: ask fable"), census tool, P2 copy fix, spec §36. |

## State

| Item | State |
|---|---|
| **v19** | **Validated** (`v19/RESULT.md`): X1-X5 and X7 pass, X6 (diagnostic) as predicted. Finding 117's fix is measured on both browsers: M2-4 105/105, engine `keyToUndoMs` [30, 32, 36] / [30, 32, 33] ms (v18: 2001 ms). |
| **The two rulings** | **X7** (§35): the paired control compared the KB figure of `已存出 N KB`. That figure moves with `dc:date`/`Rsid`, and C03 sits on the 14.25 KB edge. Fixed in `judge_counted_m2.py` `control()` only; the runner is byte-identical. **X5** (§36): Firefox `recovery-returns-what-the-product-promised` NE'd once on v19 because neither inducer fired. v8 abstains on that cell at the same rate (census: v8 2 of 18, candidates 2 of 23, 0 FAIL ever), so §23 row 1 → row 1′; X5's printed `P3: MISS` stays on record. |
| **§34.4 counts** (since 10-08e) | **Check fixes triggered by runs: 2** (X7 control, §35; X5 P2 reader copy, §36.4). **Triggered by reviews: 0.** Recorded but not counted: the census tool's first window caught by its own red case before first use (§36.2). |
| **§34.1 freeze** | Ended when X7's verdict was read. The runner is still `73b2e9ff…`. Re-judging X7 later means checking out `0ce96b32` (reader with the fix, reports from `b8324a85`, binding from `8da777d7`). |
| **Tree** | Clean after the commit that adds this file. **Not pushed** (`git rev-list --count github/main..HEAD` = 425 before this file). |

## Next, in order

1. **Ask the owner to approve the cutover to v19** (it changes the product page and, after it, the host; §29.2's rule). Nothing below runs without that approval.
2. **Cutover, four steps** (the pattern in `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md:186-207`; the product page is the shell bundle's entrypoint, so a new generation is part of it):
   - `python3 tools/build_cutover_page.py --profile e2-editor-v19 --write --expect-sha256 e00ab76a550dc12fda5dee1849d9cfb73343b9cfab9c8e9436a8bd035a0a4be8` (from `wasm_sdk_probe/`);
   - `make e2-c-assets` (copies the page to `dist/`);
   - freeze generation **v57** with a `--frozen-date` and point `MANIFEST` at it, with a comment block in the v55/v56 style;
   - `make test-e2-c-static` exit 0.
   After the cutover, `BINDING.pageSourceSha256` no longer matches the tree. That is expected; the binding is a record of the counted run (rule z).
3. **Host 0.2.8**: re-read `wasm_sdk_probe/tools/check_m3_assets.py` (its `cjk-r5.b76b0433203017ca.data` pins around lines 1015-1021) and move them to `cjk-sub-e10`; package v19 in the Nextcloud app (`~/Projects/Nextcloud_Apps/litecore`, see the memory on the ddev scaffold).
4. **R** (spec §4.4): host 0.2.8 packaging v19, the six M3 runners recounted, the product-path net per M2-5, `make test-e2-c-static` exit 0, and the host merge arm's reduced `content.xml` = native key arm.
5. Any later X5-type round: its reader copy implements §36.2's row 1′ **before** it runs (the census tool is `findings/evidence/v19/x5-product-path/census_recovery_cell.py`).

## Open, not diagnosed (carried; nothing new beyond these)

- Why finding 038's drag sometimes does not wedge (about 1 in 9 on Firefox, on v8 and candidates alike); the §23 blind spot stays named.
- Holding Delete (M2-4 rests ≥ 0.5 s between presses); M2-4/M2-1b only on an instrumented page; the §33.4 registrations; the v19 Makefile rule still packs from `build/` (re-point to the archive before any re-pack).
- Carried from 10-08e unchanged: the ~628 ms emitters' cause; the Firefox reds `an-inline-format-reaches-a-selection` (3/3 on both arms again) and the NE-only cells; finding 115 (E02's soft page breaks); the §28.5 limits.

## Standing rules

Rules a-cc of the earlier handoffs stand. New:

- **(dd) A save confirmation's KB figure is not an identity.** It is the file size rounded to 0.1 KB, and every save changes `dc:date` and `Rsid`. Compare `已存出 N KB` as a family, as §33.3 writes it (§35).
- **(ee) A copied reader carries its era's facts.** When copying a reader to a new round, read every hard-coded expectation, not only the constants you came to change. `distPageWasTheSame is False` was true for v17/v18 and false after v56 (§36.4).
- **(ff) A census window must admit every outcome it judges.** A key that only one outcome carries (`fallbackInducer`, NE only) makes a window where a FAIL can never appear. The red case "insert a FAIL" is what showed it (§36.2).

## Lessons this stretch

- **Both reds were the dice, and both were in the checks.** The product passed every claimed clause. Each fix was reader-side and had a committed honest-run witness, and the runner never moved, so neither needed a re-run.
- **The ruling's own recommendation needed a red case too.** fable's recommended census window was wrong in the same way the census was meant to guard against. The tool's red case, not a re-read, caught it.
- **Counting first was cheap.** The census (41 reports per browser) turned "this looks like noise" into 2/18 against 2/23, and the ruling rests on those numbers, not on the impression.
