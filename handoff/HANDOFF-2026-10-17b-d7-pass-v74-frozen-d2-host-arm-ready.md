# Handoff, 2026-10-17b: D7 passes in Firefox after a pinned calibration, shell v74 is frozen, and the D2 host arm is written but not yet run

This continues `HANDOFF-2026-10-17-v21-shakedown-item1-only.md` and covers commits `0351f8b2..HEAD`. The main session is opus. The owner was present for most of the round. They answered both of the earlier handoff's questions:
- D7 went to fable (option B);
- the next-link order is **C**.

The owner then chose to stop before ddev (「C」), and asked whether they can run the count chain by hand and open a session afterwards to have it read. The answer is yes, once the chain is prepared on host 0.2.25 (see "Next").

## State

| item | state |
|---|---|
| Nominal shipped version | **0.2.24**, unchanged. v21 is an uncounted candidate |
| v21 scope | Item 1 only (Ctrl/Cmd+Home/End, finding 142). Item 2 is withheld (finding 153, spec §12.3 (e)) |
| Item-1 evidence | **Judge `VERDICT PASS (0 criterion cell(s) not PASS)`** in Chrome and Firefox, N=3 (`evidence/judge-item1-after-d7-rerun-2.txt`, `e08f6afb`). M7 PASS; D2 no-host predictor PASS; 0.2.24 red cases red |
| D7 Firefox | **PASS**, at the observer's constant +455 ms, by spec §12.4 (e) 1. The window, the wording and the judge are unchanged |
| Shell | **Generation v74 frozen** (`4628c9d3`). bundleSha256 `27f33a13…`. The page `605cf24b…` is cut over to `e2-editor-v21` in the tree. `dist/` holds v21's copies, and the shell digest over `dist/` is `e35923a0…`, equal to every evidence report's. E1-C intact. `make test-e2-c-static` exit 0 |
| Engine | `e2-editor-v21`, wasm `db3408f5…`, worker `0d55bcfa…`. Unchanged |
| D2 host arm | **Written, not run** (`run_v21_d2.py --mode host`, `1fe9588d`). ddev was not touched this round |
| Host | 0.2.24 installed (`1479e56`, buildId `d3cd39bbc71ec311`). 0.2.25 not built |
| Next link | **Order C**: finish v21 (host 0.2.25, D2 host arm, binding, count). Then v22 changes **one variable**, the engine thread's stack size (finding 153). Item 2's re-enable and fix 3 (finding 152, shell-only) ride along |
| Tree | Clean after this handoff's commit |

## What happened

1. **Ruling request 2 to fable** (`review/brief-fable-2-d7.md`, `269e1f9b`).
   - The brief gave D7's history: codex review 2 S4 turned 「≥500 ms」 into 「500±50 ms 的單次」. The ±50 has no stated derivation.
   - It gave the delay distributions (`review/d7-delay-distribution.{py,txt}`), options A, A0, A″ and C, and it flagged A's unverified premise: that the lateness is additive.
2. **Ruling 2** (`review/ruling-fable-2.md`, `7a5cc0e9`, verbatim, with the main session's pre-adoption check).
   - A0 first: three silent sentinels and paint stamps, no heartbeat.
   - The constant by a pinned rule: 470, else 455, else none.
   - Chrome's D7 and both browsers' D10 and D11a stand on their +500 reports.
   - Exactly one Firefox D1 re-run. Any read outside the window would have withheld item 1 from v21.
   - §34: execution +1 (J3).
   - It found the brief's F6 false: the runner drains the page every 50 ms inside the window.
3. **Spec §12.4 and README §5.5 J3 / §5.7**, before any browser ran (`9d516094`). Append-only.
4. **A0** (`wasm_sdk_probe/tools/diag_v21_d7_timer.py`, `70c55853`; record `review/diag-d7-timer/`). It is a diagnostic, not evidence, and the desktop Chrome was closed for it.
   - 0 of 72 `t-*` +500 reads were late.
   - The sentinels fired on time. The paint replies came only at +0.8 to +12.8 ms.
   - So A0 was uninformative, and the rule gave **455**: 「premise unmeasured, maximum slack chosen」.
   - A0 cannot separate three confounds: the desktop Chrome, the sentinels themselves, and the arm order.
5. **The constant** (`303e6296`): one token, `}, 500);` → `}, 455);` in `v21_item1_observer.py`. The item-1 snippet changed from `52c08695…` to `9063835a…`.
6. **The single Firefox D1 re-run** (`e08f6afb`): D7 Firefox PASS.
   - The edit took effect: 192/192 reads in the window, median 455.2 ms.
   - The lateness is reduced, not gone: 6 reads at least 15 ms late, the latest +50.4 ms. At the old constant that one read would have posted at 550.4 ms.
   - The `092410` report moved to `superseded/item1/`.
7. **v74 freeze** (`4628c9d3`).
   - The cutover used `--expect-sha256 605cf24b…`.
   - `make e2-c-assets` was run **by the owner**: the auto-mode classifier refused it to the session. Before the copy, `dist/`'s 0.2.24 copies were backed up to `wasm_sdk_probe/build/archive/dist-shell-v73-before-v74-20261017/` (with `SHA256SUMS`; the 5 bundle files are byte-identical to v73's manifest).
   - The relink queue's `queue-v11-cutover-soak-not-started` went DRIFT, by design, the moment the v21 page was written. Witnesses are in `findings/evidence/host-0.2.25/`. The item was re-anchored to `profiles/e2-editor-v21/sdk-worker.js`, as on 2026-10-14. v21's manifest has no `documentOutline` (0 matches, checked), so the expectation stays `absent`.
8. **D2 host arm** (`1fe9588d`).
   - It uses the probe's own host route: login, then Files → open.
   - After the arm, a real Ctrl+S, settled through the host's `data-litecore` save log (`outcome == "saved"`). Then a WebDAV GET and the paragraph-text comparison.
   - A save that did not land is caught by `serverChanged`.
   - The positive control comes more than 1 s later (findings 103/104). Each round opens its own copy, in a folder the tool creates and deletes. `judge_d2` is unchanged.
   - **Host identity** is read from the host checkout's files, with no ddev command: version, packaged page, packaged engine, and the S-1 shell digest computed from `engine/MANIFEST.json`. A mismatch refuses the run.
   - Red first: self-test 19/19, and 12/19 with the identity check mutated to accept everything.
   - Real data (`evidence/d2/host-identity/`): on the installed host the `0224` expectation passes (shell `e7c4eefe…`, equal to the dist0224 reports'), and `v21` is refused on all four fields.

## Next, in order (each ddev step needs the owner's yes)

1. **D2's red case on host 0.2.24, before 0.2.25 is installed**:
   ```bash
   cd wasm_sdk_probe
   python3 tools/run_v21_d2.py --mode host --page 0224 --browser chrome --rounds 3 --out <dir>
   ```
   Then the same with `--browser firefox`. Run `--identity-only` first.
   - Never run against the host before: the first run may expose route or timing issues in the new arm. Fix them with a witness (§34.4).
   - The judge expects 0.2.24 red: `verified-selection-delete`, revision +1, no `move-document-*`.
2. **Host 0.2.25**:
   - bump the version;
   - package the v21 engine and the v74 shell;
   - `ddev occ upgrade`;
   - archive read-only;
   - check the served bytes over HTTP under gzip and zstd (0.2.24's evidence shapes are in `findings/evidence/host-0.2.24/`).
3. **D2 on host 0.2.25**: `--page v21`, Chrome and Firefox, N=3. Its default if red or not done: 「第 1 項不出貨」.
4. **Re-pin** (the 0.2.24 shape: `findings/evidence/host-0.2.24/repin_0224.py`, every value from two sources) and **prepare the count chain**. Then `BINDING` for v21 in its own commit.
5. **Count chain K**: about 8 h.
   - **The owner said they will run it by hand** and open a session afterwards to have it read. So prepare the chain's start command and a read script (as `read-0.2.24.sh`) for them.
   - Per `release-count-batched`, v21 changes the engine, so the count runs.
6. **The 0.2.25 release text.** The named limits to carry:
   - L-142-readback-overtaken, -steps, -sdk-callable;
   - L-md-sdk-callable;
   - findings 150 (fixed), 151's remaining part, and 153 (open, reachable on 0.2.24).
7. **v22** (order C): the stack-size relink alone (finding 153's criteria are in the finding), with item 2's re-enable and fix 3.

## Hazards the next session must know

- **`dist/` is v21 now.** The `dist0224` variants read `dist/e2-editor-app.js` and `dist/`'s shell, both in `run_v21_shakedown_item1.py` (d8red) and in `run_v21_d2.py --mode nohost --page dist0224`. For such a source, `build_mirror` checks only the profile hashes (`v21_shakedown_common.py:317-323`; `pageServed` and `shellDigest` are skipped when `source_page` is given). So **a re-run of a no-host 0.2.24 red case would serve v21's page and shell with `identityOk: true`.**
  - Every such run so far predates the freeze, so no recorded evidence is affected.
  - If one is needed again, point it at the archive above or add the missing check, under §34.4 with a witness.
- **The tree page is cut over.** `web/e2-editor-app.js` is now `605cf24b…` (pinned to v21). No tool pins the old source `59553850…` (grep), and S-1 checks only the served page and the shell digest, so the v21 runs are unaffected.
- **Writing `dist/`.** The owner's rule (2026-10-17): short steps like `make e2-c-assets` (cp only) are the session's own. Only long-running commands go to the owner. If the auto-mode classifier refuses, ask A/B (owner runs it / add an allow rule). Do not work around it. Keep handed-over commands to short lines: a long one was cut off when pasted this round.
- **The desktop Chrome** (its extension renderer) voided three D7 cells on 10-17. Close it for timing-bound arms. This round the session closed it with SIGTERM at the owner's request, which was a clean exit.

## Not done / open

- Everything in "Next".
- Pre-existing reds: `tools/audit_product_path_coverage.py` stays red (as 10-16b lists).
- Carried, unchanged:
  - `Language=` / D12;
  - the ordered-commands spec (also 151's arrow half);
  - finding 147 on WASM;
  - the earlier carried items.
- The observer's docstring still says "500 ms" (`v21_item1_observer.py:16`). Ruling 2 allowed one token and nothing else; fix it with the next observer change.

## §34.4

- **Repaired because of execution: 1 this round** (J3, the observer constant; witnesses: the two Firefox D1 reports and their judge outputs, `a46b9267` / `fd2f854a`).
- **Repaired because of review: 0.**
- **Running total since 10-14b: execution 28, review 18.**
- **Not counted:**
  - the relink queue re-anchor. It is the check doing its designed job at a cutover, done as on 2026-10-14, with a witness;
  - two new tools, the A0 diagnostic and the D2 host arm. Neither is a repair.

## Subagents

- **Fable**, ruling 2, read-only. The main session recomputed its numbers before adopting it. One small difference: the round trip after a late post reads 0.9–1.7 ms by the main session's split, against fable's 0.8–1.5.
- Nothing else was delegated. The main session ran A0, the re-run, the judge, the freeze checks, the host arm and its tests.
