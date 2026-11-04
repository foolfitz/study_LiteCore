# Handoff: owner's hand test of 0.2.56 (9 of 10); Writer zoom on documents with comments fixed on the dev page

Checkpoint **2026-11-04 12:50**. Supersedes `HANDOFF-2026-11-04-cadence-reset-host-0256-installed.md`. One handoff for this session.

## The owner's decisions this session

- **Hand test of host 0.2.56** run with the owner (Firefox, 10:05-10:28): items 2-10 pass, item 1 fails on zoom. Record:
  `findings/evidence/host-0.2.56/handtest-2026-11-04/README.md` (`1632fbe5d`).
- **Fix A** for item 1 (fable's ranked first): page-only, keep one laid-out size, follow a size report only past a tolerance; record the
  engine-side cause as a finding, not submitted. The owner did not answer whether to open an early hand-test slot for it: default kept,
  the fix waits for the next named slot.

## Done

- Machine had rebooted: host stack brought up (`docker compose --env-file litecore.env up -d` in `wasm_sdk_probe/host-stack`), app 0.2.56.
- Fixtures for the hand test in admin's Files, folder `手測-0.2.56/` (kept for item 1's re-test); temporary read-only user `handtest_ro`
  deleted after; no lock rows left.
- Item 1 diagnosed (subagent repro on the host and mirrors, then fable): **not a regression** (0.2.47 blanks too). A Writer document with a
  comment reports a width that moves with the paint scale (`SwPostItMgr::GetSidebarWidth` truncates the tile's zoom percent), the zoomed
  canvas followed every report, every pass ended in a re-layout: white from 100 percent, and at fit in some window widths (780x600). Finding
  185.
- Fix `ee60aa7c2`: `wasm_sdk_probe/web/e2-editor-app.js` -- `laidOut`, `layoutTwips()`, `sizeReportMovesLayout()`,
  `RESIZE_TOLERANCE_PX = 8`; every band request and every point mapping uses the laid-out size. Evidence
  `findings/evidence/zoom-comment-loop/README.md`: Z on l1 red on HEAD's page, `Z_HOLDS` on the fix (both browsers, all arms, 0 paints
  in every quiet second), t3 `Z_HOLDS`; 780x600 fit painted; unit red case in `page-render-bands.test.mjs`; node suite 586/586.
- `check_writer_zoom.py` now takes `--document`; Z2 also requires the page to go quiet; Z0/Z1/Z6 accept a width the page may be laid out
  for (reported, within 1 percent of the last, compared unrounded). Two reader bugs found by execution and fixed (Python banker's rounding;
  the open's `width` not observed).

## Next, in order

1. The next features are the owner's pick. The fix is on the dev page only; the live host still serves 0.2.56's page with the bug.
2. **At the next hand-test slot**: release the page with the fix; re-test item 1 on `手測-0.2.56/1-writer.odt` (then delete that folder);
   run Z with `--document test-docs/r7-compat/l1-layout-table-image.odt` as well as the default t3 in the regression nets.
3. Before the next freeze (unchanged from the last handoff, PLAN section 3.1): one parametrised `four_arms_identity.py`; V0' with two
   stages; workers derived into `build/` only.
4. Later-slot candidates, not started: finding 130's queue depth; the 5 expired lock rows from 0.2.56's diagnostics.

## Cautions

- **The live host still blanks Writer documents with comments** at 100-150 percent (and at fit in some window widths). Word files carry
  comments often; tell the owner before any demo on 0.2.56.
- `tools/run_e2_c_product_path.py`: four Writer mutations (`paragraph-action-swallowed`, `paragraph-action-misrouted`,
  `toolbar-drops-the-list-action`, `copy-lies`) have no anchor on the page -- already so on HEAD before this session; not touched.
- `tests/test_v21_shakedown_common.py` `test_the_real_mirror_reproduces_the_round_identity` still red from before (not touched).
- Finding 185 is upstream-shaped (core `sw/`), native LOK not measured; submissions stay on hold.
- The host repo's working copy is the live app; never check out a candidate there (unchanged).

## Section 34.4

Checks changed because of review: 0.
