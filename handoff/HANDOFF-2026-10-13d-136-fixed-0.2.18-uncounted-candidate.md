# Handoff, 2026-10-13d — finding 136 and the restore flash fixed: page `b24d754a…`, shell v66, host 0.2.18 (an uncounted candidate)

This round continues `HANDOFF-2026-10-13c-136-accepted-on-0.2.18-guard-chain-paused-for-reboot.md` after the owner's reboot. It ran that handoff's step 3 (the guard chain) twice, then did step 4 in full. Record: `specs/SPEC-M3-held-key.md` §17.

## Commits (this round, oldest first)

| commit | what |
|---|---|
| `b2b4dda2`…`826e5cd1` (sonnet, 9 incl. pins `1b5efdbb`, `a0ed713f`) | **Guard chain run 1** (`TASK-2026-10-13d`). Every Chrome half died at its first `Page.navigate` (180 s), so nothing in Chrome was measured. Every Firefox half passed. |
| `1725eedc` | Cause of the Chrome hang: **the KDE wallet `kdewallet` was locked** after the reboot. The owner's Plasma runs inside TigerVNC, so no PAM unlocks it. Headless Chrome waits on the Secret Service for its cookie key before a profile's first request. Paired control (one flag differs, `--password-store=basic`): rc 124 with 0 requests reaching the server, against rc 0. `findings/evidence/136/guard/chrome-wallet-diagnosis.txt`. |
| `2d36a90e` | Run 2's task (`TASK-2026-10-13e`), written before it ran. Run 2 is the verdict of record; run 1's Firefox halves are an extra sample that cannot overrule it; a wallet check and a Chrome health check run before every browser step. |
| `5aa8e239`…`8bd1399e` (sonnet, 7) | **Guard chain run 2: every step PASS in both browsers.** The main session re-ran every judge and read the same verdicts. 132-B 12/12; 131-B 12/12; 128-B single presses ≤ 27.0 ms (host segment `NOT_JUDGED` first, as in every chain, then PASS on the one bounded rerun, red control red ×4); 121-B 4/4; 129-B 54/54 with 0 cells different from both reference rounds; C2 12 cells; restore-window 6/6 with `scrollTop` never at 0; G6 43.8 / 50.8 ms. |
| `60819c4a` | **Shell generation v66** `70c34178…` frozen. It differs from v65 only in the page. `make test-e2-c-static` exit 0 (pass 232 + 5), E1-C intact. |
| host `96a87d8` | **Host 0.2.18** (`info.xml` only). Engine package buildId `d6d04880f56e31da`, archived read-only in `build/archive/host-0.2.18-engine-d6d04880f56e31da/`. |
| `1969bbb6` | Spec §17 (results by ruling-3 condition, the correction of §16's FIFO by addendum 4, new named limits, the owner's hand-test list). Finding 136 → fixed (uncounted candidate), with a plain-language ruling section. Finding 135 gets the 0.2.18 counts. Ruling-1 condition 2 gets an appended correction. |

## State

| item | state |
|---|---|
| Uncounted candidate | **0.2.18**: page `b24d754a…`, shell v66 `70c34178…`, host `96a87d8`, buildId `d6d04880f56e31da`. It supersedes 0.2.16 and differs only in the page. 0.2.17 (`aebef525…`) was never committed or released. The nominal shipped release is still 0.2.12. |
| Count | Still batched with the next engine-changing release (SPEC-M3-autosave §9.21). It now carries 127–136. The six M3 runners' page pins are still on `d761f1ce…` / 0.2.14. The 129-B probe and the two C2 judges now pin `b24d754a…`. |
| Finding 136 | Fixed (uncounted candidate). |
| L-134-restore-flash | Closed. |
| L-134-judge-per-paragraph | Retired for the arms ruling-3 condition 3 covers; still named for any other arm. |
| Owner hand test of 0.2.18 | **Not done.** The list is spec §17, last part: six items, two of them new (Delete at a table-cell end and then type; Delete at the document end and watch the view). The owner needs a document with a table for item 5. |

## Deviation to know about (recorded in spec §17 condition 6 and finding 135)

Run 2's G4 (C2) was started twice. The first start was at 1-min load 1.58, just after G3 ended; the subagent killed it about 24 s in and restarted at load 0.38. By then the first start's Chrome gap-80 cell had already written **158.3 ms** (keys 10–11, finding 135's signature). The C2 README has no load threshold, so this abort was not a pre-written rule. The restarted run (43.1 ms) is the record, as the task fixed in advance. The aborted cell is counted in finding 135: 1 of 4 complete runs on `b24d754a…` spiked. **For future tasks:** say in the task either "abort only if load ≥ X at start" or "never abort a started chain". Otherwise an agent makes this call on the spot.

## Environment (temporary, revert when the owner says so)

- **The ddev router listens on all interfaces** (`router_bind_all_interfaces: true` in `~/.ddev/global_config.yaml`, set 2026-10-13 ~15:20 local). The owner needed `litecore` from their laptop over VPN for a demo; it listens on `0.0.0.0:8443`, and every running ddev project is now reachable on the LAN. **Revert once the owner confirms the demo is over:** `ddev config global --router-bind-all-interfaces=false`, then `ddev poweroff` and `ddev start` in `~/Projects/Nextcloud_Apps/litecore`. Check `ss -tln | grep 8443` shows `127.0.0.1:8443`.
- **Launcher vs. wallet.** The owner chose A: add `--password-store=basic` in `ChromeSession.__init__` (`wasm_sdk_probe/tools/run_browser_probe.py`). The owner also said it is **not urgent; do not push it**. The design is in memory (`reboot-locks-kwallet-headless-chrome-hangs`): follow the 112 precedent in SPEC-M3-production-ui §17.23; write the prediction as §17.27 first; witnesses W1 (the wallet locked: 121-B Chrome ×2 plus the `hostseg` arms complete, and the wallet is still locked afterwards) and W2 (121-B identical field by field to run 2's flagless Chrome cells, milliseconds masked); §34.4 因執行而修 +1. Until it lands, check `kdewallet` `Locked` before any Chrome probe after a reboot.

## Named limits and open items

- **L-136-rule-iii-residual** (new name for the residual handoff 10-13c listed): stages raised between Escape #1 and Escape #2 leave the caret one unit off. The document is unchanged. Unmeasured.
- **L-136-toast-stage**: the toast cannot tell `anchor-mismatch` from the other "unchanged" stages. A backward hold into `anchor-mismatch` has no instance on the table fixture.
- Engine items for the link batch, beside C (spec §14/§16/§17): (1) no refusal exit leaves a selection behind; (2) a refusal carries the pre-barrier caret.
- Finding 135 follow-ups (the owner's): repeat semantics for the C2 cell before the next count; a worker-side timestamp shim; gap-200 ×10.
- `static.shellBundle` read `exit 1` in every probe report of both runs, because v66 was not frozen while they ran. It is expected and now resolved by the freeze.

## Next

1. **The owner's hand test of 0.2.18** (the list is in spec §17).
2. Then the owner chooses: **A** the link batch (C, the two engine items above, Shift+arrow selection, page numbers, and the full count of 127–136, overnight), or **B** small items.
3. Revert the ddev router binding when the owner says the demo is over (above).

## §34.4

- This segment (after the reboot): 因執行而修 **0**, 因審核而修 **0**. The pin commits are instrument pins, not check fixes; nothing in a check, judge or launcher changed.
- Round total, unchanged from 10-13c: 因執行而修 **2**, 因審核而修 **1**.

## Subagents (not reachable from a new session)

- sonnet: guard chain run 1 and run 2. Their outputs are the READMEs in `findings/evidence/136/guard/` and `guard-r2/`.

**Addendum (2026-10-13, owner hand test).** Next 1 is done. The owner reported 「1~9 通過」 for the ten-item list given orally (spec §17's list plus the 0.2.15 items; item 10, the optional copy save, was not reported; browsers not stated). Recorded in `specs/SPEC-M3-held-key.md` §18. Checked after the report: `occ app:list` gives 0.2.18; host `96a87d8` is clean; the served `e2-editor-app.js.gz` and `.zst` both decode to `b24d754a…`. The owner then raised the two requests discussed on 10-12 and still not done (Shift+Arrow selection; a page number while scrolling) and asked when ODS reading will progress. Both requests are the content of the link batch (Next 2 A, `handoff/PLAN-2026-10-12-link-batch-shift-selection-and-page-number.md`). ODS needs the writer+calc core switch after that (`handoff/PLAN-2026-09-03-ods-reading.md` W6–W12; the owner chose Calc = B on 10-12). The order is the owner's call. §34.4 this addendum: 0 / 0.
