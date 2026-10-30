# v28 pre-link evidence (SPEC-M3-v28-last-line-fallback 7.2), engine half

The engine source carries every v28 change under `OXSDK_E2_V28_LAST_BLOCK`: `src/probe_engine.cpp` (11 blocks), `src/ordered_format.inc` (3 blocks) and the `#error` guard in `src/editor_api.h`.

| gate | evidence | result |
|---|---|---|
| E1 red first | `e1-red-before-inc-edit.txt` | the inc before its edit (= v27 behaviour), with the v28 define: 20 FAIL lines. The first half of (f), plus (g) and (i), hold there by construction (no fallback), as spec 7.2 declares |
| E1/E2 | `e1-e2-green.txt` (`tests/test_ordered_format_v28.py`) | original green; v27-behaviour red; all 8 mutations red |
| E3 | `e3-*.txt` | see below |
| E4 | `e4-v28.txt` (`tests/test_format_readback_v28.py`) | v27's 18 rows identical under the v28 define; 26 tool-closed fallback rows agree with the saved documents (the 3 pseudo-heading rows with the recorded reader); the red-first checks inside |
| V0-v28 | `v0_preprocess.py HEAD` -> `v0-v28.json` | `V0_V28_HOLDS`, 16/16 rows (v23, v24, v25, v27 x 4 sources); positive control `v0-v28-positive-control.json`: exactly the four `probe_engine` rows differ |
| S | `s_syntax.py` -> `s-v28.json` | `S_V28_HOLDS`: 4 sources clean under the v28 define; the v28-only error is caught with the define and not without it; the v28 define without v27 hits `#error` in `editor_api.cpp` |

## E3

**Green.** All of these are green (`exit 0`):
- `make test-v27-first-block-static`;
- `tests/test_ordered_format.py`, `tests/test_ordered_format_v25.py`, `tests/test_ordered_format_v27.py`, `tests/test_format_readback_v27.py`;
- `tests/test_ordered_format_scope.py`, which has to be run as a script (`python3 tests/...`): it imports a sibling module. v27 ran it the same way.

**`make -k test-e2-c-static` stops at its first line.** That line is `node --test editor-shell-v2/tests/*.test.mjs`. Its one red is L-select-all-u2-pins-v26-profile (`../u-v28/README.md`). Because the recipe stops there, `-k` leaves the rest unrun.

**`make -i test-e2-c-static` ran every line** (`e3-make-i-test-e2-c-static.txt`). The red lines it reports all predate this change; v28 adds none:
- the three named in `findings/evidence/v27-176/pre-link/README.md`:
  - `test_e2_c_shell_bundle ... real_manifest_matches_the_real_tree`;
  - `copy-lies`;
  - `inducing_arms_hold_the_guard_off`;
- L-select-all-u2-pins-v26-profile;
- `tools/check_relink_queue.py` and its `--self-test`. Three items have drifted, none in a file or string this change touched:
  - `queue-no-select-all-action` (the narrow client has had `select-all` since v26);
  - `queue-v11-cutover-soak-not-started` (it wants the page on the v22 worker);
  - `queue-f119-barrier-callback-late-after-insert` (a session-file string).

  Named here **L-relink-queue-drift-v26-v27**, not fixed (owner, 2026-10-30).

## Fixed by execution (counted)

- E1's fake primary markup had no `<body>`, which the real parser (now cut into the harness) needs. It was fixed before any green was recorded.
- E4's expectation for a row the parser must refuse (`cl-t1`, a table) was first "the saved document", but a refused row is never satisfied. It was fixed before any green was recorded.
