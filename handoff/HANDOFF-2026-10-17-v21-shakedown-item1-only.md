# Handoff, 2026-10-17: the v21 shakedown found four product defects; v21 now ships item 1 only, and its evidence is green but for one re-run cell

This continues `HANDOFF-2026-10-16b-v21-linked-shakedown-next.md`. It covers commits `897372e3..HEAD`. The main session is opus. The owner was asleep from about 03:00 and authorised fable to decide on their behalf (「我要去睡了，請你自主執行／有疑義的地方可以發給fable，我授權它代我決策」).

## State

| item | state |
|---|---|
| Nominal shipped version | **0.2.24**, unchanged. v21 is an uncounted candidate |
| v21 scope | **Item 1 only** (Ctrl/Cmd+Home/End, finding 142). Item 2, paste as Markdown, is **withheld**: M3 is red on the linked engine (finding 153). The shell hides the entry (`PASTE_MARKDOWN_ENTRY_SHIPS = false`); L-md-sdk-callable; spec §12.3 (e) |
| Engine | `e2-editor-v21`, wasm `db3408f5…`, worker `0d55bcfa…`. **Unchanged**: no relink this round |
| Page and shell under test | page served `605cf24b3dff5a2d…` (from `build_cutover_page.py --profile e2-editor-v21`, no `--write`); `web/e2-editor-app.js` `59553850…`; session `f1509ff2…`; shell digest over the tree sources `e35923a0…`. The tree fixes are at `712f955a` and the pins at `f5f60ac1` |
| Shell generation v74 | **Not frozen.** `dist/` still holds 0.2.24's copies; the runners serve the tree's sources through the mirror |
| Spec | §12.2 (readings for the arms) and §12.3 (fable ruling 1: D8 (e) note, D11's dirty clause withdrawn for 22/23, **new criterion D14**, §9.1 frequency correction, item 2 withheld). Append-only, 0 lines removed |
| Evidence (N=3, Chrome and Firefox) | Every item-1 criterion is PASS in both browsers **except D7 in Firefox, NOT_ESTABLISHED**, twice: in the first run and in the re-run, the page-side +500 ms timer posted late (550–560 ms) on table fixtures, with the carets equal. **An owner decision (A/B/C) is in "D7 re-run".** M7 PASS 6/6 in each browser. The D2 no-host predictor passes, and both 0.2.24 red cases are red |
| New findings | 150, 151, 152, 153 (below) |
| Host | 0.2.24 installed; 0.2.25 not built; nothing touched ddev this round |
| Tree | Clean after this handoff's commit |

## What happened

1. **Arms, before any run** (`8f1dbf0a`).
   - Two opus subagents drafted `ARMS-item1.md` and `ARMS-item2.md`. The main session ruled on their DECISIONS in §8 and §9 and wrote `ARMS.md` (shared instruments S-1 to S-11, rules, order).
   - Spec §12.2 recorded the readings the arms forced.
   - The part-S evidence lacked two mutations (T2, T3); they were re-run, and both are red (`897372e3`).
2. **Phase B.** The instruments, populations and judges were built red-first, then one Chrome smoke per item. The item-2 agent died of context overflow; a successor finished its work.
   - The smokes found the four defects.
   - Rulings S1–S6 after the smokes (`4574b8c4`, results README §1): D4 op name, R-xlc population, M5 judged on the spec's target-host wording, M4 placement by caret or after-paste signature, M6 run alone, `v21_input` punctuation.
3. **Two diagnostics.**
   - `diag-dirty-move/`: V1–V11 and V11g (headed Chrome), candidate fixes 1, 1′, 2 and 3, all mirror-only.
   - `diag-long-paragraph/` (`fddc509a`): threshold, shape, plain text, native, Firefox, crash site mapped, 1 MiB counterfactual.
4. **Fable ruling 1** (`review/ruling-fable-1.md`; brief `review/brief-fable-1.md`): v21 ships item 1 only.
   - Q1 A: fix both range paths.
   - Q2 A: 22/23 take no checkpoint, the arrows deferred.
   - Q3 C: register 152.
   - Q4 A: withhold item 2.
   - Then spec §12.3 (`e25ccc15`) and findings 150–153 (`193143b8`).
5. **Tree fixes** (`712f955a`, red-first evidence in `findings/evidence/link-batch-v21/fixes-ruling-1/`).
   - The shared predicate `clicksBeforeMove`.
   - `CHECKPOINTED_MOVES` for the six arrows, so `BOUNDARY_CAPABLE_MOVES` stays eight.
   - The item-2 entry is switched off.
   - The counted mutation `boundary-move-takes-no-checkpoint` had its `find` text updated, with its witness committed first.
   - Node 596/596; E1-C `intact: true` (both re-run by the main session).
6. **Runner and judge** updated for §12.3: D14, D11b's new reading, E0 entry-hidden, D6 not run (`8b9b1b59` witness, `200f1e8e`, `1b247bdb`).
7. **Evidence runs** (`a46b9267`, 05:40–09:22) and results README §5. One Chrome D1 re-run counts, because the first had foreign CPU from the owner's desktop Chrome extension renderer. Firefox's "rest" arms were re-run in fresh sessions after one session failed every engine init (witness W2).

## The four findings (zh-TW files; read the 「裁決」 section of each)

- **150**: a move key pressed while the page's own delete is out takes the click-then-move range path, and the next key lands at the click.
  - **0.2.24 has it through the arrows**, 6/6.
  - Fixed in the tree for both paths.
  - V6e on the final shell gives the key-order text 3/3 in each browser.
- **151**: after any save, a move pressed within about 300 ms completes by readback with the old caret, so typed text lands at the pre-move caret.
  - Ctrl+Home/End in a dirty document hit it 18/18, because of the checkpoint save before the move. Fixed: 22/23 take no checkpoint, and D14 passes in both browsers.
  - **Remaining:**
    - **the first arrow after an edit on 0.2.24 and v21** (6/6 each). The counted 096 check pins it, so it goes to the ordered-commands batch;
    - a save less than 300 ms before Ctrl+Home/End.
  - Both go in the release text.
- **152**: in Chrome, typing is lost after the Markdown dialog closes (headless and headed). Fix 3 (blur, then focus) is measured. It is registered only, because item 2 is withheld; it ships with item 2, after the owner's hand test in a real Chrome.
- **153**: one long paragraph (≥43,520 bytes CJK, about 10 pages or more) overflows the engine thread's 64 KiB pthread stack (`Makefile:847`).
  - **0.2.24 users reach it by typing into an opened document that already holds such a paragraph** (4/4).
  - A loader with a 1 MiB stack fixes every case, 8/8.
  - The fix is a relink. The next batch's criteria are written in the finding.

## For the owner

1. **First: D7's Firefox instrument miss (A/B/C in "D7 re-run" below).** Item 1 cannot be called shippable until D7 is PASS in Firefox.
2. **Decide the order of the next link (A/B/C).** Finding 153 is reachable on 0.2.24 today, by typing into an opened long paragraph, and v21 does not change that.
   - **A.** Finish v21 first: freeze v74, host 0.2.25, the host arms, binding and the count. Then a v22 relink with the larger stack plus item 2 and fix 3.
   - **B.** Hold 0.2.25. Relink v22 with the stack fix first, shake it down, and ship 0.2.25 with 153 fixed.
   - **C (my lean).** Like A, but make v22 change **one variable only**, the stack size, so that 153 reaches users soon after 0.2.25. Item 2's re-enable and fix 3 ride with it, since they are shell-only.
3. **Before host 0.2.25 is installed:** D2's host red case runs on host 0.2.24, which needs ddev. You will be asked first.
4. **Later, with item 2:** a hand test of finding 152 in a real Chrome (type after 插入, and after 取消).
5. Nothing irreversible was done tonight: no link, no push, no deletes, no ddev, no count chain.

## D7 re-run (main session, 09:24–09:57; commit `fd2f854a`)

`ARMS-item1.md` D7 says a missed window "reads NOT_ESTABLISHED and is re-run", so Firefox D1/D4/D7 was re-run under the lock on a quiet desk (load 0.18).

- The first Firefox report and its docs moved to `evidence/superseded/item1/`, not deleted, as with the earlier Chrome re-run.
- The re-judged output is `evidence/judge-item1-after-d7-rerun.txt`; the first is kept as `judge-item1.txt`.

**Result.** D1 and D4 PASS. **D7 is still NOT_ESTABLISHED, and worse:**
- 6 of 192 +500 ms reads were posted at 554.7–560.3 ms. All were on table fixtures (`t-*`), all were "cursor" presses, and all had the reply caret equal to the read caret.
- One cell was voided by foreign CPU: the owner's desktop Chrome renderer at 79 %.

The first Firefox run had 2 late reads (550.1 and 553.5 ms) on the same fixtures. Chrome's timer posts at 500.1–500.9 ms.

**Reading** [inferred]: an instrument property, not a product one. In Firefox, the page-side `setTimeout(500)` of the observer (`ARMS-item1.md` §2.2 (c), D-15 A) fires 5–60 ms late when the main thread is busy repainting after a move in a table. More re-runs will not fix it. The property D7 measures (the reply's caret is fresh) held in every read.

**For the owner (A/B/C), before the freeze:**
- **A (my lean).** Calibrate the instrument, not the criterion. The observer posts the ask at +470 ms, so a delay of up to 80 ms still lands in [450, 550]. The ±50 ms window and D7's wording stay. This is a §34 change with witnesses: the two honest Firefox reports above, where the instrument missed the window and the property held. Red-first in the judge's self-test is not needed; the judge does not change. Then re-run Firefox D1 only (about 35 min) with the desktop Chrome closed. Chrome's D7 PASS stands, because its runner version differs only in the Firefox-irrelevant timer constant, and that is recorded.
- **B.** Hand it to fable with these numbers.
- **C.** Take D7's default (「第 1 項不出貨」). Nothing in the evidence says the product is wrong, so this would withhold item 1 over an instrument miss.

## Not done / open

- **Shell v74 freeze.** Check `make -n e2-c-assets` first (finding 042 applies after the v21 Makefile block). Then write the v74 bundle manifest. The frozen v74 digest must equal `e35923a0…`, or every evidence report is void (§11.0).
- **Host 0.2.25** (ddev; ask the owner). The D2 host arm comes after the freeze, and its 0.2.24 red case before the install. M11-autosave is not needed, because item 2 is withheld.
- **Binding v21, then the count chain K** (the owner's window, detached, about 8 h), then the 0.2.25 release text. The named limits to carry are:
  - L-142-readback-overtaken (corrected frequency, §12.3 (d)), -steps, -sdk-callable;
  - L-md-sdk-callable;
  - findings 150 (fixed), 151's remaining part (arrows on 0.2.24 and v21; a save less than 300 ms before Ctrl+Home/End), and 153 (open, reachable on 0.2.24).
- **Pre-existing reds:** `tools/audit_product_path_coverage.py` stays red, as the 10-16b handoff lists. The four new `action:paste-markdown` / dialog listener entries do not need registering now, because the entry is hidden.
- **Tools with stale assumptions** (not product): `tools/diag_v21_dirty_move.py`'s fix1/fix2/fix3 patches no longer apply to the fixed tree, and its V5/V11 arms cannot open the dialog. That is by design: item 2 is withheld.
- Carried from 10-16b, unchanged: `Language=` / D12; the ordered-commands spec (now also 151's arrow half); finding 147 on WASM; the earlier carried items.

## §34.4

- **Repaired because of execution: 18 this round.**
  - Item 1's phase B: 2 (the leave prompt; the D2 wrapper's log window).
  - Item 2's development and smoke: 11 (first agent 5, successor R1–R5 and J1).
  - Rulings S3 and S4 in the item-2 judge: 2.
  - The counted mutation's `find` text after fix 1: 1.
  - The evidence run: 2 (J1, the diag tool's stale page pin; J2, the D5-w modifier keydown in Firefox).
  
  Each was witnessed before it was fixed.
- **Repaired because of review: 0.**
- **Running total since 10-14b: execution 27, review 18.**
- Not counted as repairs, because they implement a spec change rather than fix a misjudgment: D14, D11b's §12.3 (b) reading, E0, and D6's not-run record.

## Subagents

- Arms: two opus drafters, D and M. Phase B: the same two, plus a successor for M after M's context overflowed.
- Diagnostics: two opus agents.
- Ruling: one fable, read-only.
- Fixes: two opus agents in parallel, one on the tree and one on the runner and judge.
- Evidence: one opus agent.
- The main session re-ran the node suite, E1-C, the common tests, the page and shell pins and the judges' summaries, and it wrote the spec appends, the findings and this handoff.
