# Finding 129 — criterion 129-B on the bytes that ship (0.2.13's page), 2026-10-12

Spec `specs/SPEC-M3-autosave.md` §9.4 129-B. M4 (`../m4/`) measured the fix on a MIRROR (0.2.12's page + `page-129.patch`); the shipped page `c7f904fa…` carries the fix with review 2's changes (the move is sent as-is when there is no caret rectangle or the session refuses; `lastSelectionShape` is set after the click returns), so the same probe was run again with the page under test = `dist/` itself.

| | |
|---|---|
| tool | `wasm_sdk_probe/tools/probe_129_m4_wasm.py --final` (added for this run: page under test = `dist/e2-editor-app.js`, which must be `c7f904fa…`; red control = 0.2.12's page decoded from `wasm_sdk_probe/build/archive/host-0.2.12-engine-45cdcedfc0fe7e61/files/e2-editor-app.js.gz`, which must be `8909564e…`; both checked in `report-<browser>.json` → `preflight.final`). Driver `tools/run_probe_129_final.sh` (M4's with the paths changed). Analysis `tools/analyze_129_m4.py` unchanged |
| documents | M4's three converted fixtures (`round-*/docs/`, hashes in `round-*/inputs.sha256`) |
| rounds | `round-20261012T062205Z` (Chrome 06:22–06:34Z, Firefox 06:34–06:47Z) and `round-20261012T064814Z` (06:48–07:14Z); browsers one after the other, nothing else running on the machine except two read-only reviews of another tool |
| analysis | `analysis-stdout.txt`; per round `summary.md`, `analysis.json` |

## Result, against 129-B's clauses

| Clause | Chrome | Firefox |
|---|---|---|
| the 42 brief cells (old 12 + S1–S5 × 6 keys) land where native `ref` lands | 12/12 exact; S1–S5 30/30 by rule (28/30 exact; `s1/Down`, `s1/End` differ only by WASM's wrap offsets, S1 lines start 101/195/292 vs native 101/201) — both rounds | same, both rounds |
| `#toolbar[data-selection-shape]` after the key | `collapsed` in every m4 arm (before the key `range-single` or `range-cross`) | same — 216/216 arms over both browsers and rounds |
| no toast; key → move complete < 400 ms | 0 toasts; max 298.3 ms over all arms of both browsers and rounds | same |
| Shift+arrow: the caret does not move, no toast | `shift-collapsed`, `shift-range`: no move, no toast, revision unchanged | same |
| L-129 cells: recorded, not judged | `s1d`/`m1d` Down follow native `ref` (as M4: the page's own drag leaves the caret at line 2's start) | same |
| red control: 0.2.12's page | refuses with the developer toast 「◀：EDITOR_FORMAT_GESTURE_UNSUPPORTED：…」 | same |

Chrome against Firefox: 54/54 cells equal; each browser's round 2 against its round 1: 54/54 equal, wrap offsets the same. Identical to M4's mirror rounds in every landing cell. As in M4, the 7 key arms that do not move the caret take 283–298 ms (the engine's own ~250 ms for a no-move key, M4's control), the moving ones < 200 ms.

**129-B holds on 0.2.13's page.** Not measured here: the toast predicate (130-U, `../../130/replay-output-0.2.13.txt`), 128-B (`../../128/`).

## Round 3 on the 131-fixed page (2026-10-12; page `d761f1ce…`; SPEC-M3-autosave §9.12 re-opened 129-B)

`round-20261012T092119Z` (driver `tools/run_probe_129_final.sh … 3 1`; the probe's `FINAL_PAGE_SHA256` re-pinned to `d761f1ce…` in `d049b534`; `report-*.json` → `preflight.final`: page under test `d761f1ce…`, red control `8909564e…`, both `true`). Analysis `analysis-stdout.txt` (`analyze_129_m4.py round-20261012T092119Z round-20261012T064814Z`). A first attempt passed a non-integer round label and stopped at argparse; its directory held no data and was removed.

| Clause | Chrome | Firefox |
|---|---|---|
| 42 brief cells against native `ref` | 12/12 exact; S1–S5 30/30 by rule (28/30 exact, `s1/Down`, `s1/End` by wrap offsets) | same |
| toolbar shape after the key | `collapsed` 54/54 | `collapsed` 54/54 |
| no toast; key → move done < 400 ms | 0 toasts; max 285.1 ms (moving keys 81.0–91.3) | 0 toasts; max 307.3 ms (moving keys 83.8–88.5) |
| Shift+arrow | no move, no toast, revision unchanged | same |
| red control (0.2.12's page) | refuses with the developer toast | same |

Chrome against Firefox 54/54 equal; each browser against round 2 54/54 equal, wrap offsets the same. **129-B holds on the 131-fixed page.**
