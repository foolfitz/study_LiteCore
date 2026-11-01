# Handoff: K 0.2.45 pinned and ready; the chain waits for the owner's hand tests and word

Checkpoint **2026-11-02 ~01:15 +0800**. Supersedes `HANDOFF-2026-11-01d-own-stack-holds-host-0245-installed.md` for what is next.

## State

- **K has not run. No counted step exists.** Nominal shipped stays **0.2.26**.
- Host **0.2.45** on the own stack, `https://litecore.localhost:18443`, identity in `specs/SPEC-M3-K-0.2.45.md` section 1. 0.2.44 is still the daily uncounted candidate on paper, until the owner's hand tests.
- **The owner's gate:** `boundaries` commit <= 16 ms (spec v29 append 8). In `judge_p2.py`, moved by `repin_0245.py`. T1 holds under it.
- The chain is ready: `--preflight-only` reads clean but for P5, the owner's word.

## Done this session

| Item | Result | Evidence |
|---|---|---|
| K spec | pinned, a closed list of differences on K 0.2.44's protocol | `specs/SPEC-M3-K-0.2.45.md` |
| Tools, repin | derived by closed list; 25 sites in 11 files | `k-0.2.45/derive_k_tools.py`, `repin_0245.py` |
| Pre-chain | every item of spec section 6 holds | `k-0.2.45/README.md`, spec section 11 |
| Counted dry run | production UI P, versions, assets, new_document in real counted mode; autosave `binding_problems` empty | `k-0.2.45/counted-dry-run/` |

**Three holes that would have sunk the count, caught before it.** None is a product defect. Spec section 11 has them: the `SHELL_MANIFEST` pins, `M8 (page)` red since the icon toolbar, N9 on a mixed commit. The third only a counted-mode run could see.

## Next, in order

1. **The owner's hand tests**: typing and the toolbar on 0.2.45. Then 0.2.45 replaces 0.2.44 as the daily uncounted candidate, or a finding opens and K does not start.
2. **Start the chain on the owner's word**, 8-10 hours. The command is in `k-0.2.45/README.md`, quote the owner in `--owner-window`. Check first: lock table empty, `preflight-only` clean. **Never open the litecore site during it**: runners clear the whole lock table. Ask the owner to close desktop Chrome and zen, or C2 is refused and run later.
3. After `DONE`: `bash findings/evidence/m3-production-ui/runs-0.2.45/read-0.2.45.sh <logdir>`, read against K1-K8. Not while it runs. If a C2 round was refused for the desk, run that round on a clean desk: spec section 5, a round that never ran is not a re-run.
4. K holds: nominal shipped moves to 0.2.45, write release notes. K does not hold: a finding per red cell, nominal stays.

## Cautions that cost time this session

- **A commit is part of the instrument.** `repo_static` reads git: until the chain ends, a commit touching `ROUND_PATHS` must not touch `PRODUCT_PATHS`. `findings/evidence/new-document/` is a round path.
- **Run counted-only code in counted mode.** Reading the branches found nothing; a real run found N9 in three minutes.
- **`new_document` waits for "other runners" by command line**, a `bash -c` holding the word included. It timed out 280 s waiting for itself; the caution was already in the last handoff, I still walked into it. Start runners from a file.
- **Dry runs leave lock rows.** new_document's Chrome arms left two, on its own test files, P5 refused. Let them expire and read the files.
- **`git add <evidence dir>` takes the mirrors.** K 0.2.44 left `*/mirror*` and `*.docs/` untracked. Amended out.
- A red case of mine caught my own fix: `data-tip` carries the same words as the label.

## Section 34.4

- **Fixed-by-execution: 5.** `SHELL_MANIFEST`, M8, M8's match, N9's commit, H1's witness (v28 report against v29's closure).
- **Fixed-by-review: 0. Fable rulings: 0.**

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English; specs and findings in zh-TW. Linking and compiling `make` stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.

## Addendum (2026-11-02 ~01:40 +0800): the chain is running

The owner: 「手測完成，都符合預期 / 請繼續跑」. 0.2.45 is the daily uncounted candidate (`host-0.2.45/README.md`).

**Started 01:37 +0800, detached, PID 1724100**, log `wasm_sdk_probe/build/m3-count-20261101T173658Z/chain.txt`, tree `fe6c3cc7d`. Preflight P0-P6 ok. About 8-10 hours, so it ends around 09:30-11:30. It survives this session. `start-when-lock-clears.sh` launched it, because the hand-test editor was still holding a live lock at 01:35; it released at 01:36:18.

**Do not, until `DONE`:** open the litecore site; edit anything a runner imports; commit anything that touches `ROUND_PATHS` and `PRODUCT_PATHS` together; run a browser or anything heavy during C2 at the end. A shell line naming a runner makes `new_document` wait on it.

**zen was still open at 01:35** (Chrome 0, the VM closed). If it is open at C2, the rounds are refused by `desk_gate` and run later on a clean desk. Not a red (spec section 5).

**A shakedown that is not clean stops the chain** before any count, about 80 minutes in: read `chain.txt`, it is the STOP line. After `DONE`: `bash findings/evidence/m3-production-ui/runs-0.2.45/read-0.2.45.sh wasm_sdk_probe/build/m3-count-20261101T173658Z`, against K1-K8 (spec section 7).
