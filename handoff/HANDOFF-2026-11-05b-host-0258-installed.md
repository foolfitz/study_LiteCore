# Handoff: host 0.2.58 installed (Calc headers, Calc structure, Writer key bursts); waiting for the owner's hand test

Checkpoint **2026-11-05 12:55**. Supersedes `HANDOFF-2026-11-05-key-burst-and-calc-structure.md`. One handoff for this session.

## The owner's decision this session

- Hand-test slot: **A, "現在就發布 0.2.58"**. The agent did the whole release, as the option said.

## Done, all committed

- Writer **shell generation 91** = 90 + `narrow-editor-v2-session.js` (`56d6bfed2`). It has its own `e2/generations/generation-91.json`
  and manifest `e2/editor-shell-v2-bundle-v91.json`, and the Makefile's static check names v91. E1-C was intact before and after.
  V0' 91 holds.
- Calc **`ods-editor-v6` frozen** into `dist/profiles/` (three copies equal to the link's receipt). The page points at v6, and the
  four Calc mirror tools learned v6's URL (`3d1ffa921`). The node suite passes 1037/1037 (1038 counted a test that spec append 3
  withdrew), and the three Calc mutation tools pass.
- **Release regression** (`findings/evidence/release-0.2.58/`, 2 h serial, both browsers) is all green: P5 P4 S1 Z(t3, l1) P1, KB on
  dist, F4 24/24, F3 equal; Calc C CU cell range autosave P2, headers P and structure P on dist.
- **Host 0.2.58** (`findings/evidence/host-0.2.58/`, `c400b232f`): host `0bf488a`, engine `9e9310e3`. Gate 39/39, `DELTA_HOLDS`,
  `PACKAGE_HOLDS`, `CANDIDATE_INSTALLED`, Files 52/52, capture holds.
- **New host arm** `calc-host-arm/`: the two Calc page criteria run unchanged on the host route. Header geometry holds there too, so
  Nextcloud's button CSS does not distort the DOM headers. P-H5's `pending` clause cannot be observed on the host, which has no
  `?diagnostics=1`; `read_run.py` registers that, with reds.
- Finding 130's status: released with 0.2.58.
- The hand-test fixtures are in admin's Files under `手測-0.2.58/` (`1-calc.ods` = `create_calc_structure_fixture.py`'s output,
  `2-writer.odt` = `test-docs/t1-plain-zh.odt`). The script is `HANDTEST-2026-11-05-host-0.2.58.md` (repo root, zh-TW, 10 items).

## Next, in order

1. **The owner's hand test** of 0.2.58 with `HANDTEST-2026-11-05-host-0.2.58.md`. Record it the way 0.2.56's was recorded
   (`findings/evidence/host-0.2.56/handtest-2026-11-04/README.md`). Afterwards, ask whether to delete `手測-0.2.58/`. My DAV DELETE
   may be refused by the classifier, so let the owner decide.
2. Next features after the hand test (the owner picks): drag to resize column width and row height; freeze panes. The named
   limits of this release are in the hand-test script's last section.

## Cautions

- `check_key_burst.py --subject baseline` reads dist. Since this freeze, dist is generation 91, so the docstring's "(generation 90)"
  no longer holds. The baseline red is `findings/evidence/key-burst/red-baseline/`.
- Host-route readers: anything that reads `window.__calcEditor.inputState`, `.autosave` or `.lastExport` is diagnostics-only, and
  the host never passes `?diagnostics=1`. Wait with `window.__calcEditor?.state?.…`, because the module runs after the shell is
  drawn.
- Unchanged: `build/archive` is hardlinked or read-only; never check out a candidate in the host repo's working copy; submissions
  are on hold; the four Writer mutations in `run_e2_c_product_path.py` still have no anchor.

## Section 34.4

Checks changed because of review: 0.
