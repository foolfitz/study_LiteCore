# Handoff: K holds on 0.2.45, the nominal shipped host is 0.2.45

Checkpoint **2026-11-02 ~09:15 +0800**. Supersedes `HANDOFF-2026-11-02-k-0245-ready-owner-go-pending.md`.

## State

- **K holds.** `read_k.py`: `K_HOLDS`, 20 mutations red. `findings/evidence/m3-production-ui/RESULT-0.2.45.md`, spec `SPEC-M3-K-0.2.45` section 12.
- **Nominal shipped: 0.2.45**, replacing 0.2.26. Daily candidate: the same. Nothing is uncounted now.
- Host on the own stack, `https://litecore.localhost:18443`, main at `eeac22c`, engine `623f51d295ff6030`. After a reboot: `cd wasm_sdk_probe/host-stack && docker compose --env-file litecore.env up -d`.
- The site, Chrome, zen and the VM are free again. Nothing of ours is running.
- Local commits are not pushed.

## Numbers to keep

Chain 7 h 20 m. Chrome `boundaries` commit 11.0, 9.2, **14.3** ms against the owner's gate of 16; under the old 10 K6 was red. Over 16 from here on is a new regression; the gate does not move again (spec v29 append 8).

## Open, none blocking

- **L-K-0244-no-engine-refusal-exercised**: no cell reached a v29 engine refusal. A fixture position that reaches `EDITOR_BOUNDARY_UNSUPPORTED` is a work item for the next batch: measure natively first.
- `.ddev` stays: `Instance` reads the admin password from `.ddev/config.local.yaml`, and the rollback uses it. Do not `occ user:resetpassword` admin.
- `report.v23-four-arms/` of the six product-path runs, about 31 MB, is on this disk, not in git.

## What this session proved about K

- The census and the counted-mode dry run each found a hole shakedown cannot reach; keep both as pre-chain steps. Spec section 6 is the list.
- The chain's `git add` of evidence is not a formality: `repo_static` reads commits, and a failed glob drops a whole `git add` silently (`2>/dev/null`). Add by exact path.

## Section 34.4

- **Fixed-by-execution: 6.** The five of the previous handoff, plus the evidence `git add`.
- **Fixed-by-review: 0. Fable rulings: 0.**

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, the release text and specs in zh-TW. Linking and compiling `make` stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.
