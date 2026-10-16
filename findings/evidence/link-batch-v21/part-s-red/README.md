# v21 part S: red-first record

These are copied from part S's scratch directory (2026-10-16). Each test the part added had to be red on a deliberate mutation before it counted as green (task brief, hard rules).

- **`run_mutations.py`** applies each mutation in place, runs the named test file, restores the file and checks its sha256.
- **`mutations.json`** is its raw output. It has 31 mutations, all red. The worker, SDK, client, session, page and `.d.ts` mutations are listed in the part S report, summarised in commit `bc6534e0`'s message.
- **`d8-on-head-page.txt`** is spec §11 D8's hold sequences run against the 0.2.24 page logic, `web/e2-editor-app.js` at `07d01cf8` (sha256 `901dd6a6…`). Result: 3 pass, 4 fail. Sequences (a), (c), (d) and (e) are red there, and all seven pass on the new page.

The main session re-ran the suite after commit `bc6534e0`: `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs` gives 561/561. The mutations themselves were not re-run by the main session.

## Appended 2026-10-16 (main session): T2 and T3

`mutations.json` holds 29 entries, not 31: the two `.d.ts` mutations T2 and T3 are defined in `run_mutations.py` but were not in the committed output (found by the shakedown arms draft, `../shakedown/ARMS-item1.md` §7). Re-run alone with `python3 run_mutations.py T2 T3`, output `mutations-T2-T3.json`: **both red** (`declaration-drift.test.mjs`: T2 fails 2 of 15 tests, T3 fails 1 of 15). `sdk/document-sdk.d.ts` was `0e242bf0…` before and after. With these, all 31 mutations have a red result on file.
