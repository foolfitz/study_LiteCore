# Handoff, 2026-10-20i: Phase E's first runs on `ods-viewer-v1`; the residual reds are findings 158/159 and need the owner

**First line:**
- **The owner's goal: 「Nextcloud 裡點 .ods 就能開」.** Spec `specs/SPEC-M4-ods-in-nextcloud.md` (pinned `d7ab2815`, addenda 1–7; **6 and 7 are new this round** and supersede parts of §4's E3/E4a/E5/E6 readings).
- **Phase E ran for the first time** on `ods-viewer-v1` (wasm `f6ab3cdb…`, worker `cc2d6514…`), all evidence in `findings/evidence/m4-ods/phase-e/` (its README lists every report and what counts). Commit `38763d3c`.
- **Where the viewer stands after two full-corpus runs:** E1, E2, E5, E6, E4b, E9 green. **E3 red 8/303 and E4a red 5/304, every one product-side** — five files with form controls cannot paint at all (finding 158, core-build level), two files recalculate to `#VALUE!` where the desktop computes values (finding 159), one UDF (no Basic). Plus finding 157 (hidden sheets offered as tabs) and 160 (SelectAll unconfirmed 2/482 once), which the readings absorb but the product still has.
- **Three owner decisions are open** (below). Phase H does not start before they are taken: E3/E4a are red and the spec's default for a never-done E is "stop".
- The previous handoff (`HANDOFF-2026-10-20h-…`) is still accurate for everything up to the link.

## What ran, in order (all on `f6ab3cdb`, headless Chrome 151, desk clean: wallet unlocked, 0 other Chrome, load < 0.3)

1. **Ladder** (`--only ladder/`, 9 entries + ODT control): E1–E6 all green, 28 s. First numbers on the link: `view-ready` 0.9–4.5 s; boot `open.begin` 236,523,520 (v12 was 290,066,432 — this reader-shape core without a11y boots ~51 MiB lighter; stated as the order of magnitude, not a controlled delta); `document-destroy-enter` present on every case (addendum 1's fix is live); `selectAllConfirmed` true everywhere; `textNull` true only on the empty sheet.
2. **Full corpus** (306 + control, 598 s): E1/E2/E6 green (303 open, 3 encrypted refused before any engine, `view-ready` p50 0.93 s / max 31.0 s on `tdf37341.ods`, peak sbrk max 553 MB on `many_charts.ods`); **E3 17 red, E4a 6 red, E5 1 red.** The first red is the measurement: nothing was changed until every red was classified (addendum 7). The engine's actual text was read with a new diagnostic switch (`--record-text`, `diagnostic-text/`).
3. **E6's B** (`run_ods_viewer_e6_leak.py`, A6.1/A6.2): five boots byte-identical → **B = 0**. One engine reopening the same file: `open.begin` +9.7 MB, +4.2 MB, 0, 0 (numeric-100k: +23.5, +18.0, 0, 0). `open.begin[n+1]` equals the previous cycle's peak: the break is a **high-water mark**, it never comes down. The spec's leak clause assumed it does; **withdrawn and reworded** (A7.1: the first two steps are recorded, Δ₃ and Δ₄ must be ≤ B). The counted run (`--bound 0`) is green, numbers identical to the forcing run to the byte.
4. **E4b/E9 on the real page** (`run_ods_viewer_e4b_e9.py`, A6.3/A6.4): surface 1785 = ceil(26775/15), right edge painted after the scroll, three tabs from the engine, clicks read back 1/2/0, the page's live engine paints E5's 1024-px tile byte-identical to the Phase E report. **Red case** (`--red-case no-refit`): 1773 vs 1785 — the 12 px — reproduced; `redCaseReproduced: true`.
5. **Full corpus again** under the new readings (594 s): E1/E2/E5/E6 green; E3 red 8, E4a red 5 (the product list above); 7 volatile sheets recorded; `selectAllConfirmed` false 0/464 (was 2/482).

## How each first-run red was classified (addendum 7; read the raw case records before trusting this)

| red | count | red on | what was done |
| --- | --- | --- | --- |
| text = `10/20/26` where the oracle (run 09-03) says `09/03/26`; RAND values | 7 sheets | the oracle's premise (text is a function of the file) | runner derives `volatileParts` from content.xml (TODAY/NOW/RAND/RANDBETWEEN formulas, `text:date`/`text:time` fields); E3 **records** these, does not judge (A7.3); `L-volatile-sheets-not-compared` |
| `PART_READBACK_MISMATCH` on parts 12–23 of `fdo67682-2.ods` | 12 sheets | the criterion's premise (every sheet can be shown) — Calc cannot switch to a hidden sheet (`ScTabControl` only inserts visible pages, `tabcont.cxx:60`) | runner derives `hiddenParts` (`table:display="false"`); E3/E4a skip them, E5 demands a refusal and a read-back that is not it (A7.2). **Product gap = finding 157**: tabs are enabled, engine has no `part_info` |
| `UNO_EXCEPTION … fails to supply service com.sun.star.form.Forms` on every paint | 5 files (6 sheets) | **the product (core build)**: `OFormsCollection` gated on `HAVE_FEATURE_DBCONNECTIVITY` (`native-code.py:186`), which is `0` in `build-a11y-gate0` | **finding 158**; stays red |
| `#VALUE!` for `TIMEVALUE("6:45 PM")`, `SERIESSUM`, `MULTINOMIAL`, `CONVERT`, every financial function | 3 sheets, 2 files | **the product**: recalculated at load; cached values in the file are not shown; scaddins ARE in the core's services list | **finding 159**, cause open (candidates: `ENABLE_WASM_STRIP_LOCALES`, string→number setting, recalc-on-load); stays red |
| `#NAME?` for a Basic UDF | 1 sheet | the viewer core has no Basic (`ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS`) | `L-no-basic-udf`; stays red |
| `selectAllConfirmed: false`, 1 char read of 74 | 2 reads of 482 | the product, intermittently (0/2 on re-run, 0/464 on the second sweep) | **finding 160**; E3 stays red on such a read; no retry in the harness |
| E5 tile controls red with an empty detail on the diagnostic `--only` run | — | the runner (controls not staged) | `--only` now stages all three ladder controls (A7.5) |

Also found while deriving `hiddenParts`: 10 corpus files carry a cached external-link sheet (`<table:table>` with `<table:table-source>`) which is not a part; excluded, after which the runner's table count equals the manifest's `sheets` for all 303 opened entries.

## Owner decisions (A/B, my inclination first)

1. **Finding 158, form controls (5 of 303 files, blank canvas with an exception on every paint).**
   - **A.** v1 ships with a typed refusal before any engine: the session's package probe (C6, already reads `content.xml` for encryption) also detects `<office:forms>` and refuses `FORM_CONTROLS_UNSUPPORTED`; no link, pure JS, one day. Registered limitation.
   - **B.** Rebuild the core with DB connectivity (or re-gate the forms components); hours of build, bigger binary, voids E7's "ODT bytes unchanged" if the editor moves to it. Not for v1.
   My inclination: A now, B queued. (The editor profile shares the core; an ODT with form controls is **not measured**.)
2. **Finding 159, `#VALUE!` where the desktop computes values.** Diagnose first (a generated .ods with one formula per candidate cause, read through `part_text`; no link). If it is `STRIP_LOCALES`, the fix is a core rebuild (same batch as 158-B). Until then E3 stays red on 2 files; the owner decides whether v1 may ship with "some functions show #VALUE!" registered.
3. **Finding 157 + 160, the next viewer link's batch:** `part_info` (hidden → disabled tab) and a longer/verified SelectAll wait. Both need a relink → `ods-viewer-v2`. **A.** batch them with whatever 158/159 force; **B.** relink now for 157 alone. Inclination: A.

Hidden sheets are already shown correctly as *refused* by the session (`PART_READBACK_MISMATCH`), so the user sees an error, not a wrong sheet.

## Next, in order (after the decisions)

1. 158-A if chosen: extend `viewer-shell/odf-package-probe.js`, red case first (a generated .ods with one control must be refused with no engine; the 298 others must not), rerun the full corpus — the five E3/E4a reds should turn into E2-style refusals (a spec addendum must say so first, A7-style).
2. 159 diagnosis (no link): `tools/create_ods_corpus.py` cannot be regenerated without touching ladder bytes — make the probe file in a scratch dir and run it through the Phase E harness with `--record-text`, or through `run_ods_viewer_draft_smoke.py`'s mirror.
3. **The owner's first look**: `python3 wasm_sdk_probe/web/serve.py --port 8792 --root wasm_sdk_probe/dist` then `http://127.0.0.1:8792/ods-viewer.html?diagnostics=1` — the page's worker literal already names `ods-viewer-v1`, no mirror needed (nothing is written). `three-sheets-distinct.ods` shows the three tabs; `tdf149752.ods` is 089's file. Tell the owner the hidden-sheet and form-control caveats before they try `fdo67682-2.ods` or `tdf134161.ods`.
4. O6, host 0.2.29 (`~/Projects/Nextcloud_Apps/litecore`), O7 in the owner's ddev slot, H7 — unchanged from 10-20h, but **not before E3/E4a are green or their reds are registered limitations by the owner's decision**.

## Hazards

- `cd` slipped once more this session (`cd …/upstream && for …` in a corpus inspection) and **changed the session's working directory** for two calls; every path afterwards was absolute. Use absolute paths; never `cd`.
- The spec's E3/E4a/E5 "clean" definition changed (A7.2/A7.3); the counted run for those three is `report-2026-10-20T135954Z.json`, not the first full run.
- The Phase E harness and runner changed after the first run (`--record-text`, hidden/volatile readings, `--only` controls); each report records `pageFiles` shas, so a report's harness is identifiable; the runner's own sha is not recorded (as before).
- `latest_phase_e_report()` in `run_ods_viewer_e4b_e9.py` takes the newest `phase-e/report-*.json` at the top level only; diagnostic reports live in subdirectories on purpose.
- The E6 tool imports from `run_ods_viewer_phase_e.py`; do not edit that file while an E6 run is in flight (the 10-15 rule).

## §34.4

- This stretch: because of execution **+3** — the `--only` ladder controls (witness `diagnostic-text/report-2026-10-20T134644Z.json`), the hidden/volatile readings in E3/E4a/E5 (witness `report-2026-10-20T133240Z.json`), the E6 tail reading (witness `e6-leak/report-2026-10-20T134946Z.json`); because of review **+0**.
- **Running total since 10-14b: 40 / 27.**
- New tools not yet reviewed: 10-20g's list plus `run_ods_viewer_e6_leak.py`, `run_ods_viewer_e4b_e9.py`, `web/ods-viewer-e6-harness*`. The Phase E judges have now been exercised by one real red list each (E3/E4a/E5) and found right on every item they flagged; the three fixes above are their first review-by-execution.

## Owner decisions still open (carried)

- From 10-20e: whether the product moves to one engine on the calc core; A3 for L-C.
