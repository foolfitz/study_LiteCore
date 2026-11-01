# Handoff: own stack holds (ST1-ST4), host 0.2.45 installed on it, section 7 done; K waits for the owner's gate decision

Checkpoint **2026-11-01 ~22:55 +0800**. Supersedes the Addendum of `HANDOFF-2026-11-01c-v29-t3-t4-hold-t1-and-cutover-wait.md` for what is next.

## State

- **K has not run. No counted step exists.** Nominal shipped stays **0.2.26**. Accumulated uncounted engine changes since then: v22-v29.
- **The site** is `https://litecore.localhost:18443`, stack `litecore-own`. Host **0.2.45**, main at `eeac22c`, engine `623f51d295ff6030` (v29, wasm `e61e5890`, generation 83, page `022d0cd0`, icon HTML `ca58f40f`). Archive `build/archive/host-0.2.45-engine-623f51d295ff6030`.
- **Daily uncounted candidate: still 0.2.44 on paper**, until the owner's hand tests. 0.2.45 is what is installed.
- ddev's `litecore` and `litecoreprobe` are stopped. `.ddev` stays: `Instance` reads the admin password from `.ddev/config.local.yaml`, and the rollback needs it.
- Commands: `PATH="$PWD/wasm_sdk_probe/host-stack/bin:$PATH"` for bound tools. After a reboot the stack is down until `cd wasm_sdk_probe/host-stack && docker compose --env-file litecore.env up -d`.

## Done this session

| Item | Result | Evidence |
|---|---|---|
| ST2, ST3 | `ST2_ST3_HOLD`, Files 52/52, reader with 14 red cases | `own-stack/st2/` |
| ST4 | `ST4_HOLDS`: own stack 219/219 and 45/45 while ddev's router dropped twice | `own-stack/st4/` |
| 0.2.45 gate | passes; 24 red cases over real evidence, each refused by the v29 gate | `host-0.2.45/gate-red-cases.json` |
| Package, delta, offline | `623f51d2`, `DELTA_HOLDS`, `PACKAGE_HOLDS` 22/22 | `host-0.2.45/` |
| Install, Files, identity | `CANDIDATE_INSTALLED`, 52/52, `holds: true` | `host-0.2.45/` |
| Toolbar in Nextcloud | looks right on both browsers, 780 px fits | `host-0.2.45/first-look/` |
| Section 7: P arm | 6/6 | `host-0.2.45/section-7/` |
| Section 7: `as5`, `as5-held` | 6/6 and 6/6; finding 177's second symptom measured, no new finding | same |
| Section 7: `FOREIGN_PHASE` | 0.60 -> 0.05, prediction pinned in `e4725360b`, 6/6 no red clause | same |

## Next, in order

1. **The owner's hand tests**: typing and the toolbar on 0.2.45. Then whether 0.2.45 replaces 0.2.44 as the daily uncounted candidate.
2. **The owner's gate decision** (spec v29 section 6, section 14): Chrome `boundaries` commit, 8.7 / 11.3 / 12.3 ms against <= 10 set on v20. K6 reads red until decided.
3. **The next K spec**, after 2. It must carry: the single-press replacement (finding 178, or K7 goes red for no product reason); the clear wait on the toast; re-bind `htmlSha256`; the page pins and `HOST_VERSION` to 0.2.45 (every runner's `page` problem reads this today); the new `runnerSha256` of `check_m3_same_second.py`; `DEFAULT_DDEV`-side URLs through the adapter; survey the counted-only paths before the chain (`shakedown-green-does-not-mean-the-count-can-run`).

## Named limits

- ST2 ran each runner once. A difference that only shows in repeats is not excluded; K repeats them.
- ST2 ran on 0.2.44. On 0.2.45 only Files, P, `as5`, `as5-held` and R3 have run. Same-second R2, locks, versions, host entry, page honesty, new document and assets have not. K covers them.
- `run_st4.py` tested two projects of ours. `ddev poweroff` was not tried: it would stop the owner's other projects.

## Cautions that cost time this session

- **When two runs differ, compare the instrument first.** I called `same_second`'s baseline a chance outlier, from the history. The runner's own comment and `runnerSha256` said it had changed. Same conclusion, wrong reason; the recorded press phases settled it.
- **Count what the data holds, not what it looks like.** I told the owner `as5` lost two letters; `LETTERS` has no `q`, so it lost one.
- **A red case's match can hit a sibling.** Two gate cases read `held` because a path suffix also matched `v28-083/` and `shell-v79-173/`.
- The session's `cd` persists: two calls in a row read "No such file" for files that exist. Use absolute paths after a `cd`.

## Section 34.4

- **Fixed-by-execution: 4.** The contract receipt's `--exports`; the password regex in `run_st4.py`; the gate red cases' two suffix matches; `first_look.py`'s leave and pointer.
- **Fixed-by-review: 0. Fable rulings: 0.**
- Wrong statements, corrected in the evidence and to the owner: 2 (`same_second` reason, `as5` count).

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English; specs and findings in zh-TW. Linking and compiling `make` stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.
