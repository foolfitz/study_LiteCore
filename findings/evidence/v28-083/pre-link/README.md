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

## Identity and link machinery (spec 5)

- **Makefile.** A v28 block follows v27's: `E2_V28_*`, archive `build/archive/e2-editor-v27-c089dfd6-worker-8152448a`, worker pin `8152448a…`, defines v27's plus `-DOXSDK_E2_V28_LAST_BLOCK`. A new `test-v28-last-block-static` is green (`test-v28-last-block-static.txt`).
- **Tools** derived from v27's with the names changed:
  - `tools/check_v28_last_block_contract.py`;
  - `tools/build_e2_v28_last_block_profile.py`;
  - `tools/link_v28_last_block_owner.sh` (`bash -n` only);
  - `tests/test_v28_last_block_profile.py` (7 tests).
- **M1-1.**
  - Without the v28 carrier: red (`m1-1-red-without-v28-carrier.*`, the three E2_V28 objects).
  - With it: green (`m1-1-green-with-v28-carrier.*`, 0 FAIL, 62 s, `taskset -c 0`).
- **Fixed by execution (counted), caught by M1-1.** The first green attempt (`m1-1-run1-red-mangled-define.*`) was red. Deriving the Makefile block by a blanket `E2_V27_` → `E2_V28_` rename had also renamed `-DOXSDK_E2_V27_FIRST_BLOCK` into a nonexistent `-DOXSDK_E2_V28_FIRST_BLOCK`. The v28 compile line therefore lacked the v27 define, and `editor_api.h`'s new `#error` fired. It was fixed in the Makefile only; no other file carried the mangled name.

## L, PIN, ships (spec 5, 7.2)

- **ships** (`ships.stdout.txt`, `--json`): `what_the_link_ships.py --since 3a6998b33 --variant link-batch-v28 --shipped-profile dist/profiles/e2-editor-v27`. Result `ok`: only `probe_engine` changes (9 hunks, all in the `.cpp`). The `.inc` changes are invisible to it, as declared; `ships-text.stdout.txt` is the first, text-format run.
- **L** (`tools/check_v28_ships_confined.py`, derived from v27's) → `l-confined.json`: **`CONFINED_V28_HOLDS`**.
  - **D**: 15 groups = the 15 declared hunks. With them stripped, every file equals 3a6998b33's byte for byte. No group is nested in a v27 branch.
  - **A**: the 158 differing preprocessed lines all lie inside v28 branches.
  - **B, C**: v27's line equals v27's link.
  - **Red cases** (`l-confined-red-cases.txt`): a line added outside any group → B and D red; the `parser-push` hunk removed → D red.
- **Fixed by execution (counted) for L.** The first L run (`l-run1-red-alignment.json`) was red. It found one line "outside" (`ordered_format.inc:410`, a `}`).
  - **The cause:** an alignment ambiguity. The v28 group in `startOrderedFormatAction` ended in a bare `    }`, which preprocessed identically to the line before the group (comments are stripped by `-E`), and difflib paired the wrong one.
  - **The fix:** the group now ends in a statement, `gFormatBarrier.fallbackRan = gFormatBarrier.fallbackSelectionType >= 0;`, which replaces the `fallbackRan = true` at its start. The meaning is the same: the type starts at -1 and is set by the read. The reader's algorithm is unchanged.
  - **Re-run after this change, all green:** E1/E2, E3's inc tests, `test-v28-last-block-static`, S (its control anchor moved to `stepBack`'s line), V0, M1-1, ships.
- **V0 baseline correction (counted with the above).** V0 was re-run against **3a6998b33** (v27's link source): `V0_V28_HOLDS` 16/16, positive control exactly the four `probe_engine` rows. A re-run against HEAD after the engine commit would have compared v28 with itself; the first V0 (against 201b9edbb, before the engine commit) was valid when it ran.
- **PIN.**
  - `source_pin.py` (v27's, with v28's files added) → `source-pin.json`: 11 files, both trees (LOSRC `../libreoffice-26-8` at 671c848b, and `native-lok-26-8/src`) agree.
  - Red case: an unmodified copy passes (`source-pin-control-copy.txt`); one byte added to `swcrsr.cxx` → `PIN_RED` on exactly that file (`source-pin-red-case.txt`).
  - The v27 archive's `SHA256SUMS` all OK (`v27-archive-sha256sums-check.txt`).
  - `frozen-set-before.sha256`: 2,862 files under `dist/profiles/` and `build/archive/`.
  - `make-n-owner-command.txt`: v28's four compiles and one guarded link, no other profile's objects.
  - `build/e2/editor-v28`, `dist/profiles/e2-editor-v28` and the link log do not exist.
