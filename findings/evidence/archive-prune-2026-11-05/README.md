# Pruning old host engine archives (2026-11-05)

The owner chose option D ("D", 2026-11-05) after the 0.2.58 hand test, to recover disk space (94 percent used, 56 GB free). This is
not in git: `wasm_sdk_probe/build/archive/`.

## What was deleted

- **45 host engine archives** `build/archive/host-0.2.x[-prefix]-engine-*`, from 0.2.7 to 0.2.56: 2,356 MiB freed (measured with
  `df`; the archives are hardlink-deduplicated, so this is less than the sum of their `du`).
- **Kept**: `host-0.2.24` (named by `tools/run_v21_shakedown_item1.py`), `host-0.2.45` (the last counted K), `host-0.2.57` (0.2.58's
  rollback restores it), `host-0.2.58` (the next release checks the live engine against it).
- Also removed, outside the archive:
  - the agent worktree `.claude/worktrees/agent-a0a318793f1c3f64d` (2026-10-27; its commit `48c190c3f` is in main). Its
    uncommitted diff and untracked `r1-source/` are saved read-only in
    `build/archive/worktree-agent-a0a318793f1c3f64d-leftover/`, with SHA256SUMS.
  - `build/scratch-m3-new-document` (Firefox temporary profiles from 2026-10-31).
  - `build/host-0.2.57` (the candidate clone; rollback reads the archive, not the clone).
  - the mirror folders of the Calc page tools (`build/calc-headers`, `calc-structure`, `calc-editor-browser`, `calc-style`,
    `calc-sheet-view`, `calc-undo-cu`). Each run recreates them, and their reports record the hashes.

## The record

- `deleted-host-engine-archives.json`: each deleted folder with its version, buildId, file count, bytes, its `MANIFEST.json`
  sha256, and whether the repo has its `archive.sha256` (24 of 45) and `release.json` (24 of 45).
- `manifests/`: each deleted archive's `MANIFEST.json`, copied before deletion and checked against the recorded sha256. These list
  every packaged file with its sha256.
- `raw-bytes-still-on-disk.json`: the deleted packages name 219 distinct files. **125 are still on disk raw**, unchanged, in
  `dist/`, the profile archives, `build/e2` or `build/ods`; that covers every wasm and every profile file.
- `missing-bytes-in-git.json`: **the other 94 are all in git history**, byte for byte. They are page and shell files
  (`editor-shell-v2/`, `spreadsheet-shell/`, `sdk/`, `e2-editor-app.js`, the two HTML pages and the others), and the file names
  the commit for each.

So no unique bytes were lost. What is gone is the assembled package folders (the `.gz` and `.zst` encodings and their layout).

## The check before deleting was incomplete

Before deleting, the agent searched only `tools/*.py` for the `build/archive/host-` prefix and reported that only 0.2.24 was named.
After deleting, a search for the folder names across `tools/`, `tests/` and `findings/evidence/` found more scripts that name a
deleted archive. **These no longer run as written:**

- the retired per-release scripts of 0.2.29 to 0.2.55 (`prepare-release.py`, `rollback-package.sh`, `install-*.{sh,py}`,
  `derive_host_*.py`). Rolling back to those versions is no longer possible as scripted;
- `findings/evidence/k-0.2.45/inventory-k-bindings.py` (reads 0.2.25's `MANIFEST.json`; a copy is in `manifests/`),
  `k-0.2.45/counted-paths/check_counted_paths.py` (0.2.12, 0.2.25) and `k-0.2.45/derive_k_tools.py` (0.2.44). These are one-time
  audits and derivations of K 0.2.45; their results are committed. K's reader `k-0.2.45/read_k.py` names none of them;
- `tools/probe_129_m4_wasm.py` and `tools/run_probe_129_final.sh` (0.2.12's old page, finding 129's probe) and
  `findings/evidence/131/ghost-20-ab.sh` (0.2.12, 0.2.13, 0.2.13-prefix);
- `tools/check_m3_production_ui.py` names 0.2.23 only as an example in its help text.

If one of them is needed again, its inputs can be reassembled: the raw files from `where` in `raw-bytes-still-on-disk.json`, or
from git with the commits in `missing-bytes-in-git.json`.

## Still holds after the prune

- `Generation(91).identity()` passes (it reads `build/archive/e2-editor-v33-444519df-worker-b35359ce`).
- `v0_prime.py --generation 91`, with the K 0.2.45 arguments and output in the session scratchpad, gives `V0_PRIME_HOLDS`, and the
  working tree is clean afterwards.
