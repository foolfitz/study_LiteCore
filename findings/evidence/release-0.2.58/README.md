# Release 0.2.58: shell generation 91, ods-editor-v6 frozen, the release regression

The owner named the hand-test slot on 2026-11-05 (option A, "現在就發布 0.2.58"; CLAUDE.md, the section on cadence, item 1). The
release carries three features built on dev on 2026-11-05 (`handoff/HANDOFF-2026-11-05-key-burst-and-calc-structure.md`):
Writer key bursts (SPEC-P-key-burst, finding 130), Calc row and column headers (SPEC-P-calc-headers) and Calc insert/delete rows
and columns (SPEC-P-calc-structure). The host release itself is `../host-0.2.58/`.

## Writer: shell generation 91 (`gen-91/`)

- `freeze/`: generation 90 plus `editor-shell-v2/narrow-editor-v2-session.js` at `2b806e92e`. The argv is generation 90's with the
  manifest `e2/editor-shell-v2-bundle-v91.json` and the date 2026-11-05. The dry run reports the same "neither included nor
  excluded" list as 90's dry run (a new manifest has no exclusions until written) plus the stale dist copy. `make e2-c-assets`
  copied only that file. After the write: shell `d796a776`, problems `[]`. E1-C `intact: true` before and after.
- `e2/generations/generation-91.json`: page `0749bb91`, HTML `5a193961`, profile `e2-editor-v33` and its pins and archive are
  generation 90's. frozenCommit `2b806e92e` holds every bundled module and the HTML at these bytes; each was checked with
  `git show` at the freeze. The Makefile's static check names the v91 manifest. Commit `56d6bfed2`.
- `v0/`: `v0_prime.py --generation 91` with generation 90's K arguments gives `V0_PRIME_HOLDS` in about 2 s. F4-90 is red on the
  generation-91 tree, then re-read byte for byte with generation 90's session restored. K 0.2.45's reader is unchanged. After the
  put-back E1-C is intact.

## Calc: ods-editor-v6 frozen (`calc-v6-freeze/`)

`freeze.sh` copies `build/ods/editor-v6/profile` (wasm `47e3792c`, worker `cbf3c1ef`, linked 2026-11-05 01:34,
`../calc-structure/link/`) to `dist/profiles/ods-editor-v6`. Three copies are equal file for file: the source, dist and the
read-only archive `build/archive/ods-editor-v6-dev-47e3792c`. The archive also passes its own SHA256SUMS. The link's four-file
receipt agrees (`FROZEN_EQUAL`). `make ods-editor-assets` copied only the page and the Calc shell.

In the same commit (`3d1ffa921`), `web/ods-editor-app.js` points at v6. Four mirror tools now alias v6's URL:
`check_calc_sheet_view.py`, `check_calc_style.py`, `check_calc_undo_cu.py` and `run_calc_editor_browser.py`. Without that, a page
URL their list lacks loads nothing.

## Units before the chain (`units/`)

The node suite passes 1037/1037 (every `*.test.mjs` outside build/ and dist/). The handoff's 1038 was counted before spec
calc-structure append 3 withdrew the hidden-endpoint fallback and its test. The three Calc mutation tools pass.

## The release regression (`chain-0258.sh`, `chain-0258.log`)

The chain ran serially from 10:16 to 12:15 +0800 on tree `3d1ffa921`, detached (`setsid`), with nothing else building.

| Net | Result |
|---|---|
| P5, P4, S1, P1 (generation 91) | `P5_HOLDS`, `P4_HOLDS`, `S1_HOLDS`, `P1_HOLDS` |
| Z on t3 and on l1 (the document with a comment) | `Z_HOLDS`, `Z_HOLDS` |
| KB on dist (`check_key_burst.py`, default subject: source == dist == generation 91) | `KB_HOLDS`, Chrome 10/10, Firefox 10/10 |
| F4 (`--generation 91`) | 24 rows, problems `[]`, every arm `PASS` |
| F3 (`--generation 91`) | `F3_83_EQUAL`, moved `[]`, self-test `ALL_RED`. The two runners exit 1, as generation 90's did; the reader judges |
| C, CU | all pass (14 + 11 per browser); `CU_HOLDS` 18/18 per browser |
| cell, range, autosave, P2 | 31/31, 40/40, 18/18, 33/33 per browser |
| Calc headers P on dist v6 | `P_HOLDS`, Chrome 145/145, Firefox 121/121 |
| Calc structure P on dist v6 | `P_HOLDS`, 18/18 per browser |

`check_key_burst.py`'s docstring still names its `--subject baseline` as "dist (generation 90)". Since this freeze, dist holds
generation 91, so the baseline red is `../key-burst/red-baseline/` (run on generation 90's dist). The tool was not changed.

`probe_calc_autosave.py` runs the page on `dist/profiles/ods-editor-v1` with a host double, as it did for v5. It measures the
page's autosave, not v6.
