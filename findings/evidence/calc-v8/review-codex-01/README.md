# Codex review of the v8 engine and page (2026-11-07)

`codex exec -s read-only -C <repo> -o codex-reply.md - < brief.md`, on commits `baa1176ed` (engine) and `381869ee8` (page), after the link and before any P verdict. The owner authorised this round to proceed unattended.

Seven findings. Six were adopted because they change behaviour (1, 2, 3, 5, 6, 7), and one became a named limit (4). The table is in `specs/SPEC-P-calc-zoom.md` section 9 (append 3). Finding 3, that the zoom group stays disabled after a click selection, was reproduced independently by `p-zoom-01`: Chrome hung in P-Z6 with all three controls disabled after a click at 200%. It forced a new criterion, P-Z9.

## Fixes

- **Page.** No grid pointer input while zooming. `renderZoom` now runs inside `renderFormatControls`, the way the style controls do, so a drag's end redraws the zoom group. `centrePoint()` replaces the header-based centre cell. A copy generation stops an older fallback from overwriting a newer copy.
- **Session.** `setZoom` takes the centre as a point and asks op 5 which cell is there. If a read after op 16 fails, it sends op 16 back with the previous zoom; if that fails too, the session is uncertain.
- **SDK.** The handle's size follows the zoom reply.
- **Tests.**
  - `tests/calc-zoom.test.mjs` now passes 9 tests, two of them new: failure restore and handle size.
  - `tests/calc-format-entry.test.mjs` asserts that the zoom group comes back with the formats.

## Suite after the fixes

`node-suite-after-fixes.txt` is 1069/1070. The one red is `editor-shell-v2/tests/place-caret-second-pass.test.mjs` defect 2: 24 ms returned against a 26-32 ms window, a timing check in the Writer shell, which this work did not touch. That suite ran while P's browsers were running, and the file alone passed 7/7 three times. The full suite is re-run when the machine is quiet. All three Calc mutation tools pass.

## Section 34.4

Checks changed because of review: 1 (P-Z9 added).
