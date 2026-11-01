# ST2 and ST3 of SPEC-M3-own-stack (2026-11-01)

Nine runners, one shakedown round each, unedited, through the adapter, on the host still at 0.2.44. ST3 is the Files workflow in the same chain. `run.sh` and `resume.sh` started them, `log.txt` has the times.

**`read_st2.py` -> `reading.json`: `ST2_ST3_HOLD`.** It reads the recorded reports, cell by cell, against the ddev shakedowns, and needs no host. `self-test.json`: ALL_RED, 13 mutations. Run it again with `python3 read_st2.py`.

| runner | cells against ddev | note |
|---|---|---|
| `host_entry` | equal | |
| `page_honesty` | equal | |
| `new_document` | equal | |
| `locks` | equal | exit 1 on the page pin only |
| `versions` | equal | exit 1 on the page pin only |
| `same_second` | two differ, green here | below |
| `production_ui` | two differ, green here | below |
| `autosave` | equal, `as5` red on both | below |
| `assets` | red as recorded, clean after the transplant | below |
| Files workflow | 52/52, the same check ids as 0.2.44's | ST3 |

**The page pin.** The runners compare the tree's page with their pin. The tree went to v29 before the cutover, the host stayed on 0.2.44, so `locks`, `versions`, `same_second` exit 1 on one problem, `page {...}`. The reader accepts it only while the report's host files and host commit equal the baseline's.

**`assets`.** Its 14 problems looked like the same cause, and were tested as a claim. The runner derives the closure and the dist hashes from the tree. The reader replaces only those fields with the baseline's and runs the runner's own `score()`: clean. Decoded, gzip and zstd hashes, the manifest and the wire address equal the baseline's. The control, one bad `.gz` after the transplant, stays red, so the transplant does not launder a real difference.

**`same_second`, `*-foreign`.** The instrument moved, not the stack. The baseline pressed at phase .05 and on v28 X crossed S1's second (`premise`: that run measured nothing about 103). `3d78bd5c6`, after the baseline, set `FOREIGN_PHASE` to 0.60 (SPEC-M3-K-0.2.44 append 2) and it was not re-run until this chain. The reader checks the recorded press phases and the runner hash. This is also that fix's first run: `premise` holds on v28.

**`production_ui`, `P`.** The baseline's one failure is A3-1 on `button[paste-markdown]`. `4c4e7b639`, after the baseline, added that entry to `KEEP_ACTIONS` (SPEC-M3-K-0.2.44 append 3). The two reports carry different `runnerSha256`. The instrument moved, not the stack. The reader checks both facts.

**`autosave`, `as5`.** Red on both stacks, the same shape: 19 of 20 letters reach the server. The missing letter is timing (`i` on ddev; `n` Chrome and `i` Firefox here). This is a product result on v28, not a stack result. Spec v29 section 7 re-runs it on 0.2.45.

**What this does not say.** One round per runner. A difference that shows up only in repeats is not excluded; K repeats them.

Corrected while reading: the first draft of the reader had no `P` row, and it said so. The row was added only after the two facts above were checked. **Wrong reason, corrected:** the `same_second` rows first said the baseline was a chance outlier, on the strength of the history. The runner's own comment says otherwise, the recorded phases confirm it. The conclusion (not the stack) did not move, the reason did.
