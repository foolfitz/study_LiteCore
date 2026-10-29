# Work order: finding 173 page fix -> shell generation 79 -> host 0.2.41

Opened 2026-10-29 ~22:10 +0800. Owner decision (zh-TW, translated): **"A: fix the page, ship 0.2.41."**
Nothing of this order is implemented yet. No spec is pinned yet (step 0 is to write one).

## The defect (already established -- do not re-derive)

`findings/173-…md`, evidence `findings/evidence/173/` (commit `d14186167`). Owner's hand test on host 0.2.40: in a
blank document from Files "+ New -> New document", the bullet button ends in 「引擎需要重新開啟。沒有檢查點…」.
Reproduced on the mirror with the host's own template `/home/jiajun/Projects/Nextcloud_Apps/litecore/blank/en-US_zh-TW_A4.odt`:

| Product | failureShape | engine `dispatched` | page |
| --- | --- | --- | --- |
| v22 (0.2.38's engine) | `stage-deadline:awaiting-selection` | absent (inferred true) | `ready`, the finding-083 sentence |
| v24 | `select-text-returned-none` | absent, stage `idle` (projection false) | `recoverable-error` |
| v25 (0.2.40) | `select-text-returned-none` | **true**, stage `awaiting-result` | `recoverable-error` |

Mechanism: `wasm_sdk_probe/editor-shell-v2/paragraph-editor-client.js` `formatFailureDisposition` keeps the queue open
(`dispatched-unverified`) only for `multi-block-readback` (finding 046) and `stage-deadline:awaiting-selection` +
`selectionResultSeen` (finding 083). The ordered engine (v23+) reports finding 083's situation as
`select-text-returned-none` (`wasm_sdk_probe/src/ordered_format.inc` `finishOrderedFormatReadback`, `LOK_SELTYPE_NONE`).
Unknown name -> `dispatched-rollback` -> queue blocked -> no checkpoint in a new document -> restart notice.
F1/F3 measured a blank line INSIDE a document (overshoots -> `multi-block-readback`); a whole blank document has no
next paragraph and no check covers it.

## Scope

Page side only; **no engine change, no relink**. Profile stays `e2-editor-v25` (pin `44cb15ea8d36f0e0`, worker URL unchanged).

1. `editor-shell-v2/paragraph-editor-client.js`: the finding-083 branch also accepts `select-text-returned-none`, with the
   same three conditions (`dispatched === true`, `route === "collapsed"`, `selectionResultSeen === true`). Narrow: no
   other ordered shape (`selection-type-not-readable`, `footnote-apparatus-readback`, `unknown-structural-tag`,
   `malformed-readback-nesting`, `block-extraction-failed`, `postcondition-not-met`) is added -- whether v22 kept any
   of those open is unmeasured.
2. `web/e2-editor-app.js`: the review toast's finding-083 sentence (「動作已送出，但這一段是空的…這是檢查的極限，不是文件壞了」,
   around `:2166`) must also be chosen for `select-text-returned-none`; otherwise the toast falls to the
   "covered more than one paragraph" sentence, which is false for this document (finding 061's precedent).
3. Both files are members of generation 78 (not of E1-C's bundle `e1/editor-shell-bundle-v2.json`, which binds
   `editor-shell/*` and `input/*` only) -> freeze **generation 79** after both changes; the page gets a new hash.

## Step 0: pin a spec before any implementation or browser run

Write `specs/SPEC-M3-shell-v79-finding-173.md` (zh-TW, append-only once committed), criteria each with a red case and
a "never done" default (CLAUDE.md sections 1-9). Proposed, to be pinned or changed there:

- **U1 (unit, red first)**: a test beside finding 083's in `editor-shell-v2/tests/paragraph-editor-client.test.mjs`:
  the new shape with the three conditions -> `dispatched-unverified`; `selectionResultSeen` false/null, route
  `range-cross`, `dispatched` false, and `selection-type-not-readable` each keep their present disposition. Run it on
  the unchanged code first and keep the red output (witness).
- **B1 (browser, mirror, form 2)**: a new tool (derive from `findings/evidence/173/blank_bullet.py`): the host's blank
  template through the page's file input; arms no-click and click; Chrome and Firefox; N = 3 each. PASS: pill `ready`,
  notice hidden, toast is the finding-083 sentence, the queue stays open (a following insert-text succeeds), and the
  saved ODT has that paragraph inside a `text:list` (the bullet applied; "review" is honest). **Red case: the current
  page (`6e66c930` + the current `paragraph-editor-client.js`) must be red FOR 173** (`select-text-returned-none`,
  `recoverable-error`) in the same run.
- **Regression**: F3 with the section 16 / 16.1 rule (`tools/read_v25_f3.py`) must hold on the new page, and every
  check's outcome must equal v25 F3 run-02's (`findings/evidence/link-batch-v25/f3/run-02/`), differences named; F4
  four arms 24/24. The change touches one disposition branch, so any other moved cell is a finding, not noise.
- E1-C `intact: true`; V0′ for the carried-over v24 counts with BOTH declared shell files restored (recipe:
  `findings/evidence/link-batch-v25/cutover/README.md`).

## Order

spec pinned (commit) -> B1 tool, red on the current dist -> U1 red (witness) -> implement -> `node --check`, all
`node --test editor-shell-v2/tests/*.test.mjs` green -> `make e2-c-assets` (check `make -n` first: expect two `cp`
lines, page and `editor-shell-v2/paragraph-editor-client.js`; `cmp` each) -> B1 green with the before-product red ->
freeze generation 79 (`build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v79.json --write
--frozen-date …`, v78's eight exclusions verbatim; `Makefile:4947` -> v79 with red-before / green-after / red-on-v78)
-> F3 and F4 with v79 wrappers -> V0′, E1-C -> host 0.2.41 package -> owner slot -> install -> Files workflow ->
post-install read.

## Traps (each is live in this tree)

- **Serve the "before" product from its own bytes.** After the change, `dist/` serves the fixed page.
  `tools/v25_f_products.py` pins v25 to page `6e66c930` and generation 78 and will refuse the new dist; that is correct
  and it must not be edited (F1/F2 evidence binds it). B1 needs its own products: before = page and
  `paragraph-editor-client.js` from git at `d14186167` over the dist mirror (identity = generation 78 file by file);
  after = dist as served (identity = generation 79 file by file).
- **Do not edit the v78 tools**: `run_v25_f3.py`, `run_v25_four_arms.py`, `judge_v25_product_four_arms.py`,
  `v25_four_arms_identity.py` pin v78 / page `6e66c930` and are bound by committed evidence. Derive v79 copies (closed
  list of differences in each docstring), as v25's were derived from v24's.
- The bundle tool's default `MANIFEST` stays v76 by design; freeze by `--manifest`. If anything forces a shell change
  after 79 is frozen, that is 80.
- Opening a document starts a new worker: an engine-record observer attached before the open loses its CDP session
  (finding 173 run-01). Re-attach after the open.
- `make test-e2-c-reachability` is red at the coverage-audit line since v21 (pre-existing); the freeze is witnessed on
  the bundle line itself.

## Host 0.2.41

Derive the scripts from `findings/evidence/host-0.2.40/` (do not edit those): parent = live `main` **ae1f9db** (0.2.40),
predecessor archive `wasm_sdk_probe/build/archive/host-0.2.40-engine-a08bc6ecb7241448` (verify live engine equals it
first), new worktree branch `host-0.2.41` (info.xml only). The editor page identity is the new page; profile files
unchanged from 0.2.40; expect exactly two changed records (page, `paragraph-editor-client.js`) against 0.2.40. Evidence
gate adds U1, B1 and the regression re-runs to 0.2.40's. Install needs a NEW owner slot with an explicit no-site
answer (record it in `slot.json`); fgp-nc and nc-bridge stay stopped by the owner's choice of 2026-10-29. After
install, the Files workflow (`run_calc_editor_host.py`) and `capture-after.py` as for 0.2.40. Suggest the owner
repeats the hand test (new blank document -> bullet).

## Not in this order

Ctrl+A select-all (`handoff/WORKORDER-v26-select-all.md`); K; the other ordered failure shapes; the
`what_the_link_ships.py` blind spots (handoff 10-29g/h).
