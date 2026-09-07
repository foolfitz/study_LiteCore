# Handoff, 2026-09-07 — the gate needs six more soak runs, and 089 is waiting, not computing

Written for the next agent, at the owner's request before compacting the
session. Everything here is checkable in the tree; where it is not, it says so.
Entry points, in order: this file, then
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md` (append-only; its last
sections carry the live state), then the gate document
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` (append-only, ~1,900
lines — grep it, never read it whole).

Tree at `c2e64475`, clean, **610 commits unpushed**, `main` has no upstream.
Pushing is the owner's step.

## The five bound identities — nothing may move them

| | value |
|---|---|
| profile | `e2-editor-v12`, pins `4a2710bba1ef07d9` → `4ec1e389aaab3b03` |
| **candidate page** | **`9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`** |
| shipping shell | `web/` = `dist/`, 13 bound paths byte-identical; `e2-editor-app.js` = `df5f3b6c…`; still points at `e2-editor-v8` |
| frozen generation, `MANIFEST` | **v48**, `bundleSha256 ecfb6866117673c21a7c21995f7ea76fe60beb9f94a73c222053a18cc573a6ef` |
| cutover generation (judges' served-shell pin) | **v47**, `cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4` |

Why the pin is v47 and not v48: a candidate run serves the shell with its
entrypoint repointed, so `servedShell.servedSha256` is by construction the
digest of the *cut-over* shell. Ruling E-4 says "the digest the cutover
generation will declare". v47 was frozen by mistake during a premature cutover
(commit `000a57e2`, corrected by `2d319677`) and happens to be exactly those
bytes. Do not "fix" it to v48 — a run would then fail `one-served-shell`.

**A page move voids every identity-bound measurement below.** That is how the
count went 10 → 0 twice this week.

## Gate state

| condition | state |
|---|---|
| 1 — twelve clean runs, ≥3 UTC days, ≥2 per day | **6 of 12**, all six on UTC 2026-09-07 |
| 2 — three caret diagnostics | discharged on this page (`VERDICT-condition-2.json`) |
| 3 — the owner's six manual cells | **owed; only the owner can** |
| 4a — eight machine-checkable terms | **8 of 8** (`findings/evidence/gate-4a-on-9b29e39b/`) |
| 4b mechanical half | discharged by agent-driven Orca walks on this page (`manual-round-v12d-9b29e39b/`) |
| 4b judgement half | **owed; only the owner can** |
| ODT round trip | discharged (`queue-v12-cutover-roundtrip/`) |
| revert condition 3 | discharged (`queue-v12-cutover-revert-rehearsal/`) |

**Six more clean runs are owed, and at least two of them on each of two
further UTC days.** UTC 2026-09-06 holds one run (03) and does not qualify. A
UTC day starts at 08:00 CST. Two sessions of three, or three of two, on two
different UTC days closes criterion 1; the earliest close is the second of
those days.

### How to run a soak session

The schedule was handed back to the owner (「明早的任務我晚點會再開」) and the
one-shot wake-ups were deleted, so a session starts when the owner says so.
Dispatch **one sonnet executor** per session; the recipe is in the plan's
section "The schedule is handed back to the owner" and the shape of every run
is in `findings/evidence/queue-v12-cutover-soak/RUNS.md` (runs 04–08). In
short: `make test-e2-c-static` before every run; the runner with
`--browser chrome --candidate-profile e2-editor-v12`; `check_usable_editor.py`
saved to the **sibling** `-checklists/` directory, never into the bank (the
judge refuses unclassified files there); a RUNS.md section and one commit per
run; then `check_soak_bank.py`.

Clean = `ok: true`, `complete: true`, checklist `ok: true` with
`reconciledFor.kind == "candidate-cutover"`, 38 PASS / 2 NE, NE set exactly
`{notice-action-recovers-the-session,
a-refused-action-is-reported-and-changes-nothing}`.

**FAIL policy** (plan, section "T3 — the soak, scheduled to run unattended"):
any FAIL is banked as measured, never re-run, and restarts the count. Only the
already-named intermittent (`clear-format-removes-every-inline-format`
abstaining) resumes without the owner; anything else stops the schedule and is
handed off.

## What changed today, and the two rulings behind it

* **v46 landed and the page is final.** The 088 residue (at the second heading
  the live region still spoke the previous paragraph) is fixed by one hunk:
  `const doubled = structureSpeaks !== null`. Measured before landing —
  `manual-round-v12d-9b29e39b/RESULT-4b-v45-vs-v46.md`, six Orca walks, v46
  announces all ten paragraphs once each, the v45 return control still doubles,
  no drift.
* **The 4b instrument never broke; the desktop was dirty.** Yesterday's six
  walks on identical bytes gave 10, 10, 4, 0, 1, 1. On a clean desktop the
  unmodified banked instrument gave 10 and 10 on the first pair. The
  discriminator that separates the two populations perfectly is whether Orca
  ever speaks `文件內容` (the `#a11y-doc` label): never in a failing walk,
  twice in every good one. Count the Chrome processes before any walk.
* **R-1: the region check now verifies the claim, not the node.** The 088 fix
  makes `#a11y-para` deliberately silent when the structure channel names the
  paragraph, and stamps `data-deferred-to-structure="1"`; the product-path
  check read only the region's text and so failed 6/6 on every v12 page and 0/6
  on v8. The owner chose disposition **A**. The amendment is at the end of the
  gate document (`# Amendment, 2026-09-07`), the predicate is
  `present ∧ reason ∈ known ∧ consistent ∧ (text ≠ "" ∨ (deferred == "1" ∧
  structureText ≠ "")) ∧ (deferred == "1" → reason == "paragraph" ∧ offers ==
  "1")`, and it has three measured red cases. Finding 092 carries the whole
  case. Runs 01–02 stay banked FAIL under the old wording and are not
  re-judged.
* **4a term 6 was NOT_ESTABLISHED for a while and now is not.** Its mutation
  reddens exactly the region check — but that check was red *unmutated* on this
  page, so the mutation run's composition equalled the baseline's and proved
  nothing. Re-taken against a green baseline after R-1 landed: 8 of 8.

## Finding 089 — two results today, and what they license

* **Phase 1: the hang is a wait, not a computation.**
  `findings/evidence/089/cpu-or-wait-2026-09-07/RESULT.md`. Over a 160.5 s hang
  window the whole process tree (13–14 processes, 153–159 threads) accumulates
  ~1% of one core; 3–4 of 42,000+ samples are `R`, all on browser housekeeping;
  zero `D`. The same worker tids burned ~1 s of CPU during their boot burst
  minutes earlier, which is what excludes "the instrument never attached".
  `wchan` is `futex_do_wait` or `ep_poll`, **recorded and not interpreted**.
* **The sharpest datum, for whoever picks this up**: one `DedicatedWorker`
  thread yields voluntarily **~1,600 times (≈10/s)** across that window while
  doing essentially no work, reproducing across both runs. Something wakes it
  on a fixed cadence and it goes back to sleep.
* **Phase 2: a 26.6x timing discrepancy, and it is not systematic.**
  `tdf161948_NaturalSortSaveLoad.ods` is banked at 30,688 ms and opened in
  1.0–1.4 s in five measurements today; `rows35` and `index36/index2-35`
  reproduce their banked figures within 1.1–1.3x; `rows36` still times out 3/3.
  Pre-registered outcome **(ii)** obtained on its written trigger and stands.
* **The obligation it carries, and how much is left**: the claim
  `Index ≥ 35` **and** `Index2 ≥ 36` may not be repeated until re-measured.
  Today discharged the *diagonal* half of that. **What is owed is the
  off-diagonal grid** — `Index2 = 36` with `Index` in 20–34, and `Index = 100`
  with `Index2 = 35` — the points that actually carry "both axes are needed".
  Roughly ten opens; budget and pre-registration first.
* **Named unmeasured**: why only the 30-s-class file moved. If "the machine was
  busy on 09-06" were the whole story the second-class opens should have
  inflated too, and they did not.
* **No cause is named anywhere in 089 and none should be.** It has refused
  attribution twice; `futex_do_wait` is a measurement.

## What only the owner can do

1. **T4** — condition 3's six cells and 4b's judgement half. The runbook is
   written and is in Chinese on purpose (its reader is the owner, not an
   agent): `handoff/RUNBOOK-operator-T4-manual-round.md`. It warns in cell 3
   that finding 086 will very likely fire and says to record it and continue.
   T4 can be done any time now; it is identity-bound to this page, so it must
   not be done if the page moves.
2. **The cutover** — four steps, in the gate document's section "The cutover
   itself, and the revert that must be armed first". Not started. A runbook
   for it against v48 was offered and deferred until close.
3. **The push** (610 commits) and **the decision on finding 086's fix**, which
   D2 deferred to after the cutover because it moves the page.

## Working form, and the traps that cost time this week

Delegation is `study_OxODF`'s B form, recorded in the plan's first section and
in memory: the main session (fable) does judgement, ten-line briefs and one
pre-read; **opus** turns a brief into a pre-registered protocol or reviews one;
**sonnet** runs gate operations, measurement loops and drafts; **codex** is off
by default in this project. Reports start with `## SUMMARY` ≤ 30 lines and that
is all the main session reads. The main session does not edit code, run loops,
or `cat` large files.

* **Name the tool mode in the brief.** "Build the candidate page and hash it"
  was read as `build_cutover_page.py --write`, which performed the cutover
  before the gate passed and froze a generation on cut-over bytes. Say "never
  `--write`; this is a measurement, not a landing".
* **Count the Chrome processes before any desktop measurement**, and never
  `pkill -f`/`pgrep -f` — they match the agent's own command line and have
  killed a shell mid-command. Iterate `pgrep -x` and read `/proc/$p/cmdline`.
* **Checklist outputs go in the sibling directory**, not the soak bank; the
  judge refuses unclassified files there, which is the membership rule working.
* **A red case that was red before the change proves nothing.** That is what
  demoted 4a term 6 for half a day.
* `/tmp` is tmpfs, 16 GB. It filled to 98% on 09-06. Clean per-run dirs; leave
  `/tmp/candidate-round-tx3ue8b9` (it mirrors the v46 page and is cited as
  evidence).
