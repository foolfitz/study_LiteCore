# Handoff: v29 is linked, T2 holds, the page is not cut over yet

Checkpoint **2026-11-01, after `c0fb5e21d`** (HEAD when this was written). **Supersedes `HANDOFF-2026-11-01-k-stopped-finding-177-v29-next.md` for what is next.** For the session's findings (H1-H4, merge table, finding 177, the 34.4 counts) read that file and its Addendum; they are not repeated here.

## State

- **K has not run on any identity. No counted step exists.** Nominal shipped stays **0.2.26**. **0.2.44** stays the daily uncounted candidate.
- **ddev:** the owner released it; `litecore` is left running and idle. **Do not use ddev without asking.** The owner's desktop may have a Firefox open: not ours, never touch it.
- **v29 is linked.** The agent ran the link on the owner's word 「幫我跑」. wasm `e61e5890`, worker `a5df83db` (v28's bytes), manifest `a0352c83`, `withheld: []`. Archived read-only at `wasm_sdk_probe/build/archive/e2-editor-v29-e61e5890-worker-a5df83db`.
- **The page is NOT cut over.** `web/` and `dist/` still pin v28.
- Measured on the real engine with the page repointed in a mirror: spec `specs/SPEC-M3-v29-tick-pacing.md` section 10 is the record. **T2 holds** (medians of three runs, 8 of 8 cases). Scripts and raw JSON: `findings/evidence/v29-177/post-link/` (`typing_on_v29.py`, `idle_cpu.py`).
- Untracked and not ours: `codex-claude-code-delegation.md` and the pre-chain leftovers under `findings/evidence/k-0.2.44/` and `findings/evidence/new-document/shakedown/`.

## Next, in order

1. **Cut the page to v29.** In `web/e2-editor-app.js` change the wasm pin and `workerUrl`. Template: how v28 was cut over, `handoff/HANDOFF-2026-10-30k-v28-link-handed-to-owner.md` and its Addendum. Copy with `make e2-c-assets` (cp-only steps are the agent's). **Freeze shell generation 83 with `--manifest`**: the bound tool `build_e2_c_shell_bundle.py` is never edited, its default stays v76.
2. **Spec section 6 on the mirror** (P is done; the rest is not):
   - **T1:** C2, 12 cells, 3 rounds, quiet desk, nothing else running.
   - **T3:** generation 83 F3, F4, V0'; S4 live tool on v29; merge through the K wrappers including `--control` and `--pair`; typing probe at `--gap 290` and `--gap 310` (either side of the 300 ms grace). v23-v28 evidence was taken at 85 ms, so timer-vs-reply order may have changed.
   - **T4:** Chrome typing for 60 s, engine worker JS heap (`Runtime.getHeapUsage`), must not grow linearly with typing. Red case: `diag_tick.py immediate` (`findings/evidence/k-0.2.44/first-contact/typing-control/diag_tick.py`).
3. **`run_k_0244_merge.py` and the K pins name v28 and generation 82.** They belong to the K 0.2.44 spec; a new K spec re-values them. **Do not edit them to pass T3: derive.**

Then, before host 0.2.45: **the move off ddev.** Owner, 2026-11-01: 「本專案不要依賴ddev了，不然每次都互相卡住」. Inventory is in the earlier handoff's Addendum: 19 real calls in 9 files, most through `check_m3_skeleton_open.Instance`, plus mkcert TLS, the admin password in `.ddev/config.local.yaml`, and the container's Apache access log (K2 reads `%O`). Direction: this project's own Docker Compose stack, own ports, no ddev router, runners through one adapter. **Leave `.ddev` in place until the new stack has passed the runners.** The ddev rule in memory holds until the move is done.

## Open decision for the owner (not the agent)

The C2 `boundaries` commit gate is <= 10 ms, written on v20. On v29 medians land at 9.0-10.2 ms, so K6 can go red by a fraction of a millisecond. **Do not move the gate on v29 and do not tune the 300 ms grace to fit.** Decide before the next K spec.

## Carry to host 0.2.45 and the next K

- AS-5 re-run on v29. The lost-letter symptom is only inferred to share finding 177's root; if still red it is a new finding.
- Production UI P arm re-run (the retained-list fix for `paste-markdown` was never verified).
- Same-second R3: `FOREIGN_PHASE` was set for v28's save speed; set it again if v29 saves faster.
- The next K spec copies `SPEC-M3-K-0.2.44` appends 1-3 and **lists the counted-only paths before the chain** (five defects this session were unreachable by a shakedown).
- Named limit to carry: `L-K-0244-no-engine-refusal-exercised`. v29's own limits are in spec section 8.

## Cautions that cost time this session

- `setsid nohup ... &` leaves `$!` on a dead parent. Find the real PID with `ps` and check its args before `tail --pid`.
- A batch rename mangled a define in the Makefile. Read `make -n` before trusting it.
- `EM_ASM` can split `=>` and `===`. Use plain functions.
- Read `pass`, not `outcome`, in runner JSON.
- A measurement that overlapped other work is a lead, not a result.
- Runner `--help` may write evidence. Point `--out` at the scratchpad and check `git status`.
- The owner said mid-session: do not get stuck fixing machinery or prose. One review round; adopt only what changes behaviour or a criterion.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff files in English; specs and findings in zh-TW. Linking and compiling `make` stay the owner's unless the owner says 「幫我建置」/「幫我跑」; check `uptime` and `pgrep -a make` first.
