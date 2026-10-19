# Handoff, 2026-10-20: v22 done up to K — every mirror and host criterion PASS, v75 frozen, host 0.2.27 installed

**First line (ruling 7 item 14, shape (a)): ddev runs host 0.2.27, the uncounted candidate, and all four host arms PASS in both browsers, so it stays for daily use.**

To go back to 0.2.26, run these (also in `findings/evidence/host-0.2.27/README.md`):

```
rm -rf ~/Projects/Nextcloud_Apps/litecore/engine
cp -a wasm_sdk_probe/build/archive/host-0.2.25-engine-f5f0df762e1855f2 ~/Projects/Nextcloud_Apps/litecore/engine
rm ~/Projects/Nextcloud_Apps/litecore/engine/ATTRIBUTION.md
git -C ~/Projects/Nextcloud_Apps/litecore revert --no-edit d7c0a5e
cd ~/Projects/Nextcloud_Apps/litecore && ddev occ upgrade
```

Nextcloud does not downgrade an app, so after this `app:list` still says 0.2.27 while the bytes served are 0.2.26's.

This continues `HANDOFF-2026-10-19c-v22-shell-items-evidence-chain-running.md` and replaces it as the entry point. It covers `4d78b111..0c3e1b8b`. The main session was opus.

## Authority this stretch

- The owner chose to send every disposition to fable:
  - 「A 送 fable 裁決」 for item 2's M5/M6, which became ruling 6;
  - 「A 交 fable 當裁決 6 附錄」 for item 1's four NE cells, which became ruling 6 addendum 1.
- Then, at about 01:40 before sleeping, the owner said:
  - 「全部都跑，我先去睡，有疑義的發給fable，我授權給他代我決定」;
  - 「本session不受token軟上限約束，你一直自己跑下去就好了」;
  - 「需要建置的話也請代替我建置」.
- One fable subagent ruled on everything: rulings 6, 6-addendum-1 and 7, each committed verbatim with the main session's check appended (`review/ruling-fable-6*.md`, `ruling-fable-7.md`).
- **Tell the owner the plain-language sections** (§1 of each ruling). The session relayed rulings 6 and 6-a1 in the conversation; ruling 7's plain section has not been relayed yet.
- No compiling build was needed. Nothing was pushed or deleted. The one history rewrite is noted under Hazards.

## State

| item | state |
|---|---|
| Nominal shipped version | **0.2.26** (count `efb8ae77`). Unchanged: K is deferred (§13) |
| Host on ddev | **0.2.27 installed** (`app:list`), buildId `817413d5ad5bd502`, host commit `d7c0a5e` (local, not pushed). **Uncounted candidate for daily use** |
| Engine | v22, `e2-editor-v22`: wasm `f7a40bcc…`, loader `dc4c2c84…`, worker `0d55bcfa…`, manifest `000921c1…` |
| Shell | **Generation v75 frozen** (`5b14038e…`, `1d8c9e5f`). The product page is cut over to `e2-editor-v22`: page `3b96cb16…`, HTML `b9c2b975…`. `dist/` holds them. Shell digest `e35923a0…` (unchanged). E1-C intact. `make test-e2-c-static` 0 |
| Item 2 (Markdown paste) | **E2 PASS** in both browsers (§11.2.1, composed: M5 and Firefox M6 from the re-run). **I2-v22 PASS** (13 blocks). **M11-autosave PASS** on the host. The entry ships |
| Finding 152 | F3 PASS (10-19). F3-hand (the owner's) is open |
| Finding 154 | **H-154c PASS, H-154o PASS** on 0.2.27 |
| Item 1 (Ctrl/Cmd+Home/End) | **I1-rerun PASS** with E0-v22 (§11.4.1, §11.4.2). **D2-v22 PASS** 6/6 on the host |
| Finding 155 (new) | The open dialog sits at the viewport's **top left** on the host, as §11.5 predicted. Cosmetic; registered. The fix is for the next host version |
| K | Deferred and batched (§13). Not started |

## What happened (in order)

1. **Item 2's first reading** gave `VERDICT NOT PASS`. All cells were PASS except two:
   - **M5 NE in both browsers.** The runner's `positive_control` defaulted to profile `e2-editor-v21`, which `f0f9b3fd`'s hand list missed.
   - **Firefox M6 r2 NE.** The owner's desktop Chrome extension renderer was at 81 %.

   Ruling 6 decided the response:
   - fix the binding as a required argument (`1b393f8f`; §34.4 execution +1, witness `22bc3df4` committed first);
   - re-run only Chrome M5 and Firefox M6+M5;
   - read the cells per report (spec §11.2.1, `7475d52d`).

   The re-run passed: Chrome M5 114, Firefox M5 111, Firefox M6 3/3. **E2 PASS** (`63362c9d`).
   - Recorded in `shakedown/item2/README.md`: the I2-v22 reader's first version looked up the wrong keys, and that version is kept.
2. **Item 1's first reading** (the chain to 18:22): two expected E0 FAILs, plus four NE cells and no FAIL. The NEs and their causes:
   - **D5w Firefox: W2 again.** The chain ran Firefox's rest in one session, which v21 had already split into three.
   - **D7 in both browsers and D9 Firefox: foreign CPU.** The sources were the desktop Chrome renderer, an OxOffice `make -j 4`, zen, and ruling 6's own repo-wide search.

   Ruling 6 addendum 1 decided the response:
   - re-run those four reports' arms, with Firefox's rest as W2's A/B/C;
   - move the replaced reports to `item1/superseded/`;
   - run a desk gate before every step (spec §11.4.2, `c44ead09`).

   The re-run chain, `5624b770`, 01:42–03:07, was clean at every gate. **I1-rerun PASS** (`98508912`): exactly `E0 chrome FAIL` and `E0 firefox FAIL`, every other line PASS, E0-v22 PASS on 396 reads.
3. **Freeze v75 and cut over** (`1d8c9e5f`; `findings/evidence/link-batch-v22/freeze-v75/README.md`):
   - `dist/` was backed up to `build/archive/dist-shell-v74-before-v75-20261020/`;
   - `make e2-c-assets` was run by the session;
   - the relink queue was re-anchored to v22 after its by-design DRIFT, with the witness kept;
   - `expected-gesture-offers` profile → v22.
4. **Ruling 7 (the ddev window).** The owner's words named no time slot, so fable named tonight under the delegation: this window only, until 07:00 or until the owner is awake (spec §13.1, `7915fe27`). The order:
   - the HTTP checker copied with only its v21 paths moved, red first on the untouched 0.2.26;
   - package (`817413d5ad5bd502`), archive, bump, `ddev occ upgrade`. The upgrade was **not refused this time**: run by the session, exit 0;
   - HTTP green;
   - `HOST_EXPECT["v22"]` (`ab17a35c`).
5. **Host arms** (`3af9e296` chain, 03:25–03:35): **H-154c, H-154o, D2-v22 and M11-autosave all PASS, N=3, in both browsers** (`0c3e1b8b`; `findings/evidence/host-0.2.27/README.md`). M11's auto save came 30.2–30.6 s after the paste.

## Next

1. **Relay ruling 7's plain section to the owner** (§1 of `review/ruling-fable-7.md`). Tell them that tonight's window was named by fable and that §13's rule is unchanged.
2. **The owner's hand tests on 0.2.27** (they replace the pending 0.2.26 test, ruling 5 item 17):
   - **F3-hand:** in a real Chrome, type once after 插入 and once after 取消; the typed text must land in the document. **If never done, 0.2.27 is never called shippable and the next host version withdraws the entry** (§11.3);
   - Ctrl/Cmd+Home/End (item 1);
   - how the dialog looks, closed and open. Plain words for H-154o: **when opened, the box appears at the top-left corner of the window, not centred**. Typing and both buttons work. Finding 155 is the fix for the next host version.
3. **Release text for the version that ships v22** (spec §8; addendum 1 item 7). **Drafted**: `handoff/RELEASE-TEXT-DRAFT-0.2.27.md` (`acbd973b`, zh-TW for the owner). It stays a draft until K and the owner's hand tests. It covers:
   - remove §4.1's long-paragraph sentence (`handoff/RELEASE-TEXT-0.2.25-0.2.26.md:55-58`);
   - add L-153-no-overflow-check and the 1 MiB stack / memory sentence (spec §8);
   - make no ordering claim for "large paste, then Ctrl+End, then typing" (D6 unmeasured);
   - name the dialog's top-left position (finding 155);
   - make no "verified census" claim about the host's hidden parts (§11.1).

   L-md-sdk-callable is not needed: the entry is on.
4. **K**, when the owner schedules it, in their window, detached, and only after asking. It brings:
   - the page-honesty witness and exemption (§11.6);
   - `repin_0227.py`;
   - the merge runner's `BINDING` (still v21's wasm at `run_merge_wasm_shakedown.py:176`);
   - `chain-0.2.27.sh`.

   **Prepare these only when K is scheduled.** The next chain script must be written from the checklist under Hazards.
5. **The next host version** (0.2.28, needs the owner; item 17 (3) allowed one host version this round): finding 155's `#litecore-editor-root dialog[open] { margin: auto; }`, host only. Its criterion is H-154o's box reading.

## Accumulated uncounted changes since 0.2.26's count (`efb8ae77`)

As listed in 10-19c (engine v22, the shell entrypoint and HTML), plus these, all now shipped in 0.2.27:
- shell generation v75;
- `HOST_EXPECT["v22"]` in `run_v21_d2.py`;
- the required `profile` argument in `v21_network` and `v21_workers`;
- the HTTP checker copy in `host-0.2.27/`;
- the desk gate and the two re-run chain scripts (evidence-side additions).

None of these is imported by K's chain runners.

## Hazards

- **ddev runs 0.2.27.** §13's rule stands: later ddev steps, K included, run in a window the **owner** names. Tonight's naming by fable was one-time (§13.1). Do not read 「全部都跑」 as a standing window.
- **Desk gate and idle session for every timing step** (§11.4.2; memory `timing-runs-need-quiet-desk-and-idle-session`):
  - run `findings/evidence/link-batch-v22/shakedown/desk_gate.py --wait 600` before each step; dirty → stop;
  - while a timing step runs, the session and any subagent do nothing CPU-heavy: no repo-wide search, no tests, no large reads;
  - the owner's desktop Chrome `--extension-process` renderer has voided timing cells four times.
- **The checklist for the next chain script** (ruling 6 addendum 1 item 12):
  - Firefox's item-1 rest runs as three sessions (A `d2p,d8,d8red,d11b`; B `d11a,d11c,d12`; C `d5w,xlc,table,d6`);
  - every step passes `--rounds 3` (the item-1 runner's default is 1);
  - the desk gate runs before each step.
- **`m11_autosave.py` leaves its Firefox profiles under `--out`.** It creates `<out>/.scratch-firefox-<stamp>/` (`:166`), about 189 MB with `cookies.sqlite`. One got into a local commit and was removed by `git commit --amend` before anything was pushed (`e85276cf` → `0c3e1b8b`). The directory was moved, not deleted, to the session scratchpad. **Before `git add` on an M11 `--out`, check for `.scratch-*`.** A fix (scratch outside `--out`, or cleanup) is a registered work item.
- Commit messages: no `Claude-Session:` line. Use `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Never pass `ALLOW_FROZEN_RELINK=1` for a frozen profile. A compiling `make` is the owner's unless they say 「幫我建置」.

## §34.4

- **This stretch:** repaired because of execution **+1** (the positive control, witness `22bc3df4`), because of review **0**.
- **Combined with 10-19c's +2**, the batch's stretch is **+3 / 0**. **Running total since 10-14b: 32 / 18.**
- **Bindings and additions (0/0):**
  - the `shipped_worker_text` default;
  - the HTTP checker copy;
  - `HOST_EXPECT["v22"]`;
  - the desk gate;
  - the two re-run chains;
  - the host-arm chain.
- **Runs lost and re-run** (not tool repairs):
  - harness: +1 (W2, the second time);
  - desk: +3 (Chrome d1, Firefox d1, Firefox d9-d10-d14);
  - item 2: Chrome M5 and Firefox M6+M5, for the binding and the desk.

## Registered work items (not gates)

- **Instruments:**
  - a form-two guard against `profile` defaults in `tools/v21_*` (ruling 6 item 15);
  - the item-2 proxy log should keep every round's start (ruling 6 item 16);
  - the `bytes`/`trace` identity should record which worker text was patched (ruling 6 item 5);
  - the HTTP checker should derive its worker and wasm paths from the manifest (ruling 7 item 5);
  - `m11_autosave.py`'s scratch location (above).
- **Item 1 and the product path:**
  - implement D6 before the next item-1 run on a page with the entry (addendum 1 item 8);
  - a Ctrl+Home/End cell in the product-path net, with a §34.3 review before its first count.
- **Host:**
  - finding 154's work item 2: a DOM census of hidden parts (§11.1);
  - level-2 `STACK_OVERFLOW_CHECK` on the owner's next diagnostic link (§3.3);
  - finding 155's host rule (Next 5).
- **Carried unchanged:** `HANDOFF-2026-10-17c`'s "Not done / open" list, as 10-19c carried it.
