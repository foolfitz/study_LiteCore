# Handoff: A holds, K for host 0.2.44 is RUNNING detached -- next: read it with read-0.2.44.sh when it ends

Checkpoint **2026-10-31 ~14:00 +0800**. Supersedes `HANDOFF-2026-10-30l-v28-gen82-frozen-host-0244-ready.md` for what is next.

Study HEAD **1812febad** (chain preflight receipt) plus this file's commit. The chain was started from the tree after **8b50e79fb**. Untracked and to be kept: `codex-claude-code-delegation.md` (not ours). Check `git status` for anything else before you commit.

## A CHAIN IS RUNNING. READ THIS FIRST.

**Do not run any browser, runner, make, or repository-wide search while it runs.** The count includes timing cells. Load and a second Chrome change the result.

- Started **13:55 +0800** with `setsid nohup`. It does not depend on any Claude session.
- Process: `bash findings/evidence/m3-production-ui/runs-0.2.44/chain-0.2.44.sh --owner-window …` (pid 91502 at 13:56). Check with `pgrep -af chain-0.2.44`.
- Length: about **8-10 hours**. Expect it to end around 22:00-00:00 +0800 on 2026-10-31.
- Log: `wasm_sdk_probe/build/m3-count-<UTC stamp>/chain.txt`.
  - At 13:56 the new directory did not exist yet. The newest `m3-count-*` was still `m3-count-20261018T160539Z`. That one is **0.2.26's count, not this one**.
  - Pick the directory whose `chain.txt` has `IDENTITY-START` with `host a97724f` and `version 0.2.44`. Never read the 10-18 directory as K.
  - It ends with a `DONE (read with: …)` line, or with a `STOP`.
- The starting session also left a waiter loop (`pgrep -f chain-0.2.44.sh`, then greps `STOP|DONE|REFUSED`). It is read-only. Do not rely on it.

Identity under test: host **a97724f** (0.2.44), engine package **dacdfa20fd4ff1ea**, engine `e2-editor-v28` (wasm `13f674e4…`), shell **generation 82** (`a02673fa…`), page **3b0a2ebb…**.

## Owner state

- **0.2.44 is the daily uncounted candidate.** Hand tests (a)-(d) passed on 2026-10-31 and the owner chose A (previous handoff, addendum 2).
- On 2026-10-31 the owner chose **B (K)**. Then he wrote: 「請執行A／然後可以跑B／但我不在座位，請自主執行／授權讓你跑編譯和連結」.
- **The owner is away.** The autonomy covers **this A and this K only**. A new DDEV slot, a new install, or any other chain still needs him.
- DDEV is shared. `litecore` was started by the agent (it was paused after the reboot) and **must stay running**:
  - do not `ddev stop` or `ddev poweroff` it;
  - do not open the litecore site;
  - do not `ddev start` any other project;
  - do not touch the owner's desktop processes.
- The lock table must stay empty (P5). Any new lock row means someone opened the site.

## Done this session

| Step | Result | Commit |
|---|---|---|
| **A**: spec v28 append 2, fallback selection and html read next to a frame (L-fallback-html-read-is-new-on-this-path) | `A_FRAMES_HOLD` **30/30** (Chrome and Firefox x3; 5 cells); positive control reads as a wedge; self-test 35/35. Evidence `findings/evidence/v28-083/a-frames/` | criteria `8a4f14de3`, result `d896e38bf` |
| K spec + tools | `specs/SPEC-M3-K-0.2.44.md`: the K ruling of 0.2.39 re-valued for 0.2.44 (no new protocol); inventory, repin (24 sites in 10 files), merge wrapper, two readers, page-gate probe, chain and read scripts | `e8ec0abc6`, `08730c3d0` |
| K pre-chain on the mirror | Page-gate negative `LEGACY_V8_CONTROL_REFUSED` (control PASS, v8 `EXPECTED_REFUSAL`, 0 inserts); Enter replay `V24_ENTER_HOLDS` 3/3 on v28; merge smoke 26/26 with bound == binding; merge reader 10/10 mutations red; path reader 16/16 red and STOP on the 0.2.26 directory (42 != 46); live-bound set 50 paths unmoved (`--flip` red); P6 named reds equal v28's pre-link set | `08730c3d0`, `8b50e79fb` |
| Chain preflight | P0-P6, **0 refusals** | `1812febad` |

- `frame-char-last` never reaches the fallback. Finding 037's guard refuses the primary read. It predates v28 (generation 81 gives 6/6 the same shape). Named **L-char-anchored-frame-refuses-the-format-press**. It is not a v28 defect and not a wedge.
- The expired lock row left by the owner's hand test of 0.2.44 was deleted so P5 reads 0 (`k-0.2.44/lock-row-before.txt`).

## Next

1. **Wait.** Do nothing on the machine until `pgrep -af chain-0.2.44` is empty and `chain.txt` ends with `DONE` or `STOP`.
2. When it ends, read it, **never while the chain runs**:
   `bash findings/evidence/m3-production-ui/runs-0.2.44/read-0.2.44.sh <logdir>`
   (`<logdir>` is the `wasm_sdk_probe/build/m3-count-…` directory of this chain). The script also copies the 0.2.26 red report into the K directory.
3. Judge **K1-K8** of `specs/SPEC-M3-K-0.2.44.md` section 6:

| K | Needs |
|---|---|
| K1 | `DONE`; `IDENTITY-START` == `IDENTITY-END`; P0-P6 ok |
| K2 | production UI count, two files exit 0; red cases `28/28`, 13 x `no passing B3x run` (B3x stays withdrawn) |
| K3 | six runners' counts landed; each `--red-cases` exit 0 |
| K4 | autosave and new-document counts landed; red cases exit 0 |
| K5 | `read_k_0244_merge.py` holds; `judge_counted_m2.py --uncounted --profile e2-editor-v28` exit 4, `red PASS`, `oneRunner true` |
| K6 | C2 three rounds by the J-b.2 table (only the Chrome owner-gap80 on-screen max, red and < 200 ms, belongs to finding 135) |
| K7 | `read_k_0244_product_path.py` `K_PATH_HOLDS` |
| K8 | page-gate negative and Enter replay hold (already done pre-chain) |

4. Write **`findings/evidence/m3-production-ui/RESULT-0.2.44.md`** in English (evidence rule). Say which K held, which did not, and which log directory was read.
5. **If a shakedown STOPs** (before the count):
   - decide product versus instrument first;
   - fix an instrument red only with a red case and a witness (section 34);
   - then restart. A restart is a new chain from START with the same preflight.
6. **A counted red is a result.** Open a finding. K does not hold. Nominal stays 0.2.26.
   - **Do not change a criterion. Do not re-run to green.**
7. **If K holds:** nominal shipped moves from **0.2.26 to 0.2.44**, and v22-v28 stop being "uncounted". **Otherwise it stays 0.2.26** and 0.2.44 stays the daily uncounted candidate.
8. **If the chain is not running and has no `DONE` or `STOP`** (a reboot or a kill): the spec does not cover resuming. Do not resume from the middle and do not call it a count. Find out why, and ask the owner with A/B.

**Default if K is never read:** K NOT RUN. Nominal shipped stays 0.2.26 (spec section 8).

## Cautions

- **C2 is the last step and it is timing.** While it runs, do not run anything that matches the chain's `OURS` pattern (spec section 4 item 5 added `run_v8|run_k_|read_k_`, on top of the 0.2.26 list). Keep subagent work off the whole repo. Keep the desk quiet.
- **Bound tools: derive, never edit.** The K tools are now bound: `tools/read_k_0244_merge.py`, `tools/run_k_0244_merge.py`, `tools/read_k_0244_product_path.py`, `tools/check_v82_shift_enter.py` (thin wrapper; the original tool's preflight pins the v24 page), `repin_0244.py` and the pins it moved.
- **Reading is not re-running.** `read-0.2.44.sh` reads products. Do not re-run a runner to get a greener reading.
- **Sentinel and retired cells.** `recoveryPairing` is not judged (`held false`, `ok false`). The two bulleting cells are retired and read by FAIL shape only (spec section 3). Do not "fix" them to PASS.
- **Do not "tidy" the K evidence directory.** The mirror directories under `findings/evidence/k-0.2.44/` are receipts of the pre-chain runs.
- Evidence runners write by default. Do not run one to see its `--help`.

## Section 34.4 this session

- **Fixed-by-execution: 3** (after the previous handoff's four).
  - The frame criteria's item 3a (`frame-char-last` never reaches the fallback). Found by the first smoke, before the counted run. Pinned before the counted run.
  - `HOST_COMMIT` in the repin must be the short hash (the runners compare with `git log --oneline`). Before any run.
  - The Enter replay's v24 preflight. The bound tool pins the v24 page and refused on the first attempt. Fixed with a thin wrapper, reading unchanged (`enter-replay-run-01-refused/` is kept).
- **Fixed-by-review: 0.**
- **Fable rulings: 0.** The K spec is the existing protocol re-valued; no new ruling and no review round.

## Language

- Replies to the owner: Taiwan Traditional Chinese, with A/B/C options.
- Evidence and handoff: English (so `RESULT-0.2.44.md` is English).
- Specs and findings: zh-TW.

## Addendum (2026-10-31 ~22:35 +0800): the chain STOPPED at 14:57, read this first

**K did not run. No counted step started.** Chain log `wasm_sdk_probe/build/m3-count-20261031T055523Z/chain.txt` (copy: `findings/evidence/m3-production-ui/runs-0.2.44/chain-stop-1.out`). Clean shakedowns: page_honesty, locks, versions. Then `STOP: shakedown assets not clean` at 06:57:03Z. host_entry, same_second, autosave and new_document were never reached.

**Nobody noticed for 7.5 hours, by my mistake.** The background waiter looped on `pgrep -f 'chain-0.2.44.sh'`, and that matched the waiter's own command line, so it never ended and the session was never woken. The owner found it by asking. Wait on a PID instead: `tail --pid=<chain pid> -f /dev/null`.

**The red is the instrument, read in the code, not yet changed** (`findings/evidence/m3-assets/shakedown/2026-10-31T065458+0000.json`). `check_m3_assets.py` assumes a one-page package. Its last live run was the 0.2.26 count; since 0.2.29 the package has three pages.
- K2-1 (`:682`) requires first-open requests == every manifest file. Opening the Writer page cannot request the ODS pages' closures.
- K1-1 (`score_wire`, `:352`) skips only `DOC`; `ods-editor.html` and `ods-viewer.html` are pages too, and the asset route answers them 404.

**Next.** Spec section 6's rule for an instrument red: this report is the witness; fix K2-1 and K1-1 to read per page, keep their red cases (`RUN_CASES`, the K1-1 cases) red, add one for "a file of the opened page was not requested". Check the same one-page assumption in the runners not reached yet before restarting. Restart from scratch: P0 needs a clean output tree, and every shakedown must be clean in one chain. Fixed-by-execution so far this session: add this one when done.

litecore is running and idle; the lock table may have rows from the shakedowns (P5 needs 0; inspect, do not assume).
