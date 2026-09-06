# Handoff, 2026-09-06 — the page moved twice, the count is at zero, and 4b's instrument stopped reproducing

Written for the next agent. Everything here is checkable in the tree; where it
is not, it says so.

## Read this first: the tree is consistent, the tools are not

The shipping shell was changed twice today and **the two soak judges still
default to a page that no longer exists**. That is fail-safe — they refuse
rather than mis-count — but it is the first landmine you will hit.

| | value |
|---|---|
| shell (`web/` and `dist/`, identical) | `94edc4d9536fa38b2d6f058619537dd017cc8e771594662073cbd1fca42c1483` |
| frozen generation, `MANIFEST` | `e2/editor-shell-v2-bundle-v45.json`, `bundleSha256 a46c8518a7ebfb12…` |
| **candidate page** (`build_cutover_page.py --profile e2-editor-v12`) | **`39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e`** |
| pins | `4a2710bba1ef07d9` -> `4ec1e389aaab3b03` |
| `check_soak_bank.py` `DEFAULT_SHA` | **`20f09cc9…` — STALE** |
| `check_soak_bank.py` `DEFAULT_SERVED_SHELL` | **`78c23684…` — STALE**, must become v45's `a46c8518…` |
| `check_caret_diagnostics.py` `DEFAULT_SHA` | **`20f09cc9…` — STALE** |
| `findings/evidence/queue-v12-cutover-soak/` | still holds **10 runs on the dead page `20f09cc9…`** |

**Task 0, before any new soak run**: re-point those three constants, move the
ten dead runs to a `-void-20f09cc9` directory with a `WHY-THESE-ARE-VOID.md`
naming the page move and this handoff, and re-run `--self-test` on both judges.
A run banked before that lands is banked against a mixed rule.

`git status` is clean. 555 commits unpushed; `main` has no upstream; pushing is
the owner's step.

## What the gate looks like now

**The soak count is 0 of 12.** It restarted because the owner chose to fix a
defect they heard rather than ship it — see "The 088 residue" below. Everything
identity-bound to `20f09cc9…` is void with it: the ten soak runs, condition 4a's
eight terms, condition 2's three diagnostics, the ODT round trip, revert
condition 3, and the 4b walk that found the defect. All of them were taken today
and all of them must be re-earned on `39895d15…`.

Not void, because they are not bound to a page: the owner's confirmation against
**+24.5 MiB** (given today, verbatim 「+24.5 MiB => 同意」), and ruling E-1's
freeze of the shipped shell.

**Still owed, and only the owner can supply them**: condition 3's six manual
cells (open, type with an IME commit, paragraph format, inline format on a
selection, undo/redo, save and reopen) — the gate says of these *"not
substitutable by more automation"* — and 4b's judgement half.

## The adjudication of finding 091, and what it changed

`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` carries the full ruling
(append-only, at the end). The short form:

* **E-1 — the shipped shell was undeclared and is now declared.** `v43` (frozen
  2026-08-27) named an entrypoint the tree stopped serving when findings 087,
  088 and 090 landed, and none of them froze a generation. `v44` records the
  shell as it was; the cutover's generation moved from v44 to v45 as a result,
  and today's fix took v45. **The rule this pays for: a changed shell needs a
  new generation, landed in the same commit as the change.**
* **E-4 — the count now pins `servedShell.servedSha256`.** The page is one of
  thirteen bound files; before this clause a run on a *different* twelve-file
  shell counted clean, which was demonstrated rather than argued (RED 11 of
  `check_soak_bank.py --self-test` is that run). **Its pinned value is stale**
  (see Task 0): it must become the digest the cutover generation will declare.
* **E-3 — revert condition 3 was re-earned** and then voided by the page move.
* **E-6 corrected three things I had asserted.** Chief among them: I wrote in
  finding 091 that *nothing* caught the mismatch. Something did —
  `tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree`
  had been red since 087's fix and **nobody ran it**. That is `AGENTS.md` §3's
  first kind of registration written as the third, which is a mistake this tree
  had already recorded once.

## The 088 residue: heard, fixed, and the fix is what moved the page

During 4b the owner reported 「有些內文行好像重複唸了」. The log agreed exactly:
every non-heading paragraph spoken **twice, ~117 ms apart**; the two headings
once. The walk's own record gave the mechanism — `#a11y-para` carried the same
text as the focused node at all eight doubled stops, was empty at the first
heading and stale at the second. Ten stops, no exception.

Fixed in `projectFocusedParagraph`: stay silent when the structure projection is
already naming this paragraph. `projectStructure` now runs **first** and returns
the text it will speak, because reading `aria-activedescendant` from the DOM
would read the previous snapshot's value. Counted after: **18 utterances became
10, one per paragraph**, headings and list containers intact, and the owner
confirmed 「內文重複部份正常了」.

**Open, with its mechanism measured**: at the *second* heading the live region
still holds the previous paragraph's text and Orca speaks it. `a11y-node-2` is
the only stop with a non-empty live region in every walk that reached it. The
two channels are fed by `caretParagraph` and `documentOutline`, which do not
advance together across a heading boundary, so the one-snapshot disagreement is
let out loud and what it says is the older of the two.

**An attempt (v46) is NOT_ESTABLISHED and was never committed.** It changed the
test from "do the two channels agree" to "does the structure channel have a
focused node". See the next section for why its verdict could not be taken.

## 4b's instrument stopped reproducing, and that is the most important thing here

`findings/evidence/manual-round-v12b-20f09cc9/RESULT-4b-a11y-audible.md` has the
full table. Six walks on **identical v45 bytes**:

| walk | `focusHeldEveryStop` | paragraphs announced |
|---|---|---|
| 5 s dwell | not recorded | **10** |
| 11 s dwell | not recorded | **10** |
| control after reverting v46 | not recorded | 4, then focus lost |
| `hasFocus` instrumented | **false** | 0 — Orca was narrating another window |
| window raised before every press | **true** | **1** |
| window raised once | **true** | **1** |

Two things to carry forward:

1. **A 4b walk without `document.hasFocus()` per stop cannot say which window it
   measured.** One run tonight produced a clean-looking Orca log full of
   「請輸入統一編號或是公司名稱」 — a company-registry page in a different
   window. CDP delivers keys without OS focus; a screen reader follows the
   focused window. `drive_walk_focus.py` (banked) records it and reports
   `focusHeldEveryStop`.
2. **Raising the window before every press makes it worse, not better** —
   measured, 1 of 10 announced with focus held at every stop. The repeated
   activation is itself an event.

**Do not compare v45 with v46 until the same bytes give the same count twice in
a row.** Variables not yet separated: whether Orca must start before Chrome;
whether repeated `orca --replace` degrades its AT-SPI attachment; whether a tab
already walked once projects differently on a second pass.

## Two environment traps that cost time today

* **`/tmp` is tmpfs (16 GB) and it filled to 98%.** Two runs were killed for low
  memory and one `git commit` failed with ENOSPC. Most of it was a neighbouring
  project's `adr00xx-*` directories; ~700 MB was this project's own leftover
  `wasm-sdk-probe-chrome-*`, `aria-baseline-*` and `candidate-round-*` dirs,
  which accumulate one per run. **Clean those before a long session**, and put
  Orca logs on disk rather than under `/tmp`. I first read the swap usage as
  "cold pages, no pressure" — that reading was wrong, and tmpfs is why.
* **`pkill -f` / `pgrep -f` match this agent's own command line.** It happened
  three times today, once killing the shell mid-command (exit 144). Iterate
  `pgrep -x python3` and read `/proc/$p/cmdline` instead.

## The other lines, briefly

* **Finding 089** got three results: the "SDK forces a hard recalculation on
  load" hypothesis is **disconfirmed** at four independent points; the cost is a
  **threshold, not a curve** — and the ladder measured a *diagonal*, so the
  frontier has two axes (`Index >= 35` **and** `Index2 >= 36`, neither alone);
  and the **same ladder is flat natively** (1,399–1,417 ms over twelve files),
  so the cliff is WASM-side. `rows36` does not open in 1,800 s. **No cause is
  named and none should be** on this evidence.
* **Finding 090's guard is still unbuilt** — nothing compares `web/` with
  `dist/`. The finding says it belongs with the runner and that inventing
  machinery while closing a gate is how a gate stops meaning anything. Today
  every run was preceded by a manual `sha256sum` of the two.
* **Finding 086** (setting a heading fails on a real document, on both profiles)
  is still unfixed and still ships on v8.

## What I would do first

1. Task 0 above — re-point the three constants, void the ten runs, re-run both
   `--self-test`s. Nothing else is safe before it.
2. Make the 4b walk reproduce. Until then 4b is not a measurement.
3. Only then: re-earn 4a, condition 2, the ODT round trip and revert condition 3
   on `39895d15…`, and start the soak. The soak needs >=3 UTC days with >=2 runs
   each, so it cannot close sooner than the third day after it starts.
4. The owner's manual round (condition 3's six cells) can happen any time after
   the page is stable — but not before, because it is identity-bound and would
   be voided by the next page move.
