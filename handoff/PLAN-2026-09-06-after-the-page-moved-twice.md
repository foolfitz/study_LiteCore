# Plan, 2026-09-06 — after the page moved twice: what runs, in what order, and who runs it

Written by the fable main session from
`HANDOFF-2026-09-06-the-page-moved-twice-and-the-4b-instrument-broke.md`.
This document carries the *judgement*: sequence, delegation, and the decisions
that are the owner's. Facts are checked against the tree where stated; where a
fact is inherited from the handoff without re-checking, it says so.

## Working form for this line (adopted from `study_OxODF`, 2026-09-04 "B form")

The main session is fable and does judgement only. Cost is roughly context size
times turn count, so the loops, the code edits and the large-file reads go to
subagents, and each subagent's report starts with `## SUMMARY` of at most 30
lines, which is all the main session reads.

| kept by fable | delegated to |
|---|---|
| decisions, the ten-line brief for each task, one pre-read of an assembled object, the sentence that says a gate condition passed | — |
| expanding a brief into a pre-registered protocol (criteria written before the run), adversarial review of a protocol or a verdict | **opus** subagent |
| Task 0, gate operations (4a, condition 2, ODT round trip, revert condition 3), soak runs, measurement loops, handoff drafts | **sonnet** subagent |
| review seat b | **codex** — *off by default* in this project (memory, 2026-08-23: its quota runs out; delegating is not saving, it is paying elsewhere). The owner may switch it on per task. |

Isolation: a task that touches only tracked files runs in a git worktree
(`Agent isolation: worktree`) and the main session fast-forwards its branch after
reading the diff. A task that needs `wasm_sdk_probe/dist/` (untracked, 0 files in
git), a browser or the desktop runs in the main tree and commits only its own
files.

Discipline for the main session: no code edits, no loops, no `cat` of a large
file (grep a section), no `fork` (a fork inherits the whole context and runs on
fable).

## State at the start of this plan (checked 2026-09-06)

| | value | source |
|---|---|---|
| tree | clean, 555 commits unpushed, `main` has no upstream | `git status` |
| candidate page | `39895d15…` (`build_cutover_page.py --profile e2-editor-v12`) | handoff, not rebuilt here |
| frozen generation | v45, `bundleSha256 a46c8518a7ebfb12…` | `wasm_sdk_probe/e2/editor-shell-v2-bundle-v45.json` |
| `check_soak_bank.py` `DEFAULT_SHA` / `DEFAULT_SERVED_SHELL` | `20f09cc9…` / `78c23684…` — **stale** | lines 108, 217 |
| `check_caret_diagnostics.py` `DEFAULT_SHA` | `20f09cc9…` — **stale** | line 50 |
| soak bank | 10 runs + 3 diagnostics + condition-2 verdict, all on the dead page | `findings/evidence/queue-v12-cutover-soak/` |
| soak count | **0 of 12** | ruling of 2026-09-06 |
| `/tmp` | 4% of 16 GB used; the 98% trap is gone | `df` |
| desktop | `DISPLAY=:0`, Orca and google-chrome installed; agent-driving consent on file | `manual-round-v12b-20f09cc9/CONSENT.md` |

## Critical path

```
T0  re-point the judges, void the dead runs, self-test both   [sonnet, worktree]  ── no desktop
 │
 ├── T1a design the 4b instrument-reproduction protocol         [opus]             ── no desktop
 │    └── T1b run it                                            [sonnet, main tree, desktop idle]
 │         └── T1c only if it reproduces: v45 vs v46, same protocol   [sonnet]
 │              └── D1 (owner): land v46 + freeze generation in the same commit, or ship v45
 │
 └── after D1 the page is FINAL for this gate; everything below is bound to it
      T2  re-earn 4a, condition 2, ODT round trip, revert condition 3   [sonnet, main tree]
      T3  soak: 12 clean runs, >=3 UTC days, >=2 per day                [sonnet, scheduled]
      T4  the owner's manual round: condition 3's six cells + 4b's judgement half   [owner]
```

T0 and T1a start now, in parallel. T1b waits for two things: T1a's protocol
committed, and a window in which the owner is not using the desktop — the
handoff's cleanest-looking failed walk was Orca narrating a company-registry
page in another window, and no instrument can subtract the owner's own typing
from the log.

**Nothing in T2–T4 starts before D1**, because every one of them is
identity-bound and the next page move voids it. That is the whole lesson of
today's count going 10 → 0.

## The decisions that are the owner's

**D1 — which page does the gate freeze on?** v45 ships the doubled-paragraph
fix and leaves one audible residue (at the second heading the live region
speaks the previous paragraph). v46 fixes that residue but is
NOT_ESTABLISHED because the instrument stopped reproducing.

- **A (recommended)** — bound pursuit. Run T1 with a budget of **two sonnet
  sessions or 2026-09-08, whichever first**. If the instrument reproduces and
  v46 measures better on the same protocol, land v46 with generation v47 in
  the same commit and freeze there. If the budget runs out, freeze on v45 and
  record the residue under 4b's named-residue clause (the plan already allows
  it: "against a baseline of nothing, a verified-correct tree is the benefit").
- **B** — freeze on v45 now and start T2 today. Fastest to a running soak; the
  residue becomes a post-cutover finding. Risk: the owner already chose once to
  fix what they heard rather than ship it; if that holds, this restarts the
  count later at a higher price.
- **C** — no freeze until v46 is established, no budget. Rejected by the
  drafting party: an open-ended condition is exactly the form `AGENTS.md` §2
  forbids.

Default if the owner says nothing: **A**.

**D2 — finding 086 (setting a heading fails on a real document, on both
profiles, ships on v8 today).** Its fix lives in the shell's barrier, so it
moves the page. Either it is batched into the same freeze as D1, or it waits
for after the cutover. **Recommended: after the cutover.** It is not a
regression, the revert trigger does not fire on it, and batching it means T1
must re-measure on yet another page.

**D3 — codex as review seat b** for T1a's protocol. Off by default (see the
table). The owner can say "codex on" for that one review.

## Parked, and why

- **Finding 090's guard** (compare `web/` with `dist/`): not built. The finding
  itself says inventing machinery while closing a gate is how a gate stops
  meaning anything (`AGENTS.md` §4's self-check). Every run keeps the manual
  `sha256sum` of both directories in its record. Revisit after the cutover.
- **Finding 089** (the ODS cliff, two axes, WASM-side, no cause named): a
  separate line, not on this gate. Untouched until the soak is running.
- **Pushing the 555 commits**: the owner's step.
- **Environment traps**: `/tmp` is clear now; Orca logs go on disk under
  `findings/evidence/`, never `/tmp`; never `pkill -f`/`pgrep -f` — iterate
  `pgrep -x python3` and read `/proc/$p/cmdline`.

## Task briefs

Each brief is ten lines or fewer. The executor expands it; the expansion is
committed before the work it governs.

### T0 — re-point the judges and void the dead runs (sonnet, worktree)

1. `check_soak_bank.py`: `DEFAULT_SHA` → `39895d15…`; `DEFAULT_SERVED_SHELL` →
   v45's `a46c8518…`, **verified** by recomputing `shell_bundle_digest` over the
   tracked `web/` (the worktree has no `dist/`) and by reading
   `editor-shell-v2-bundle-v45.json`. `check_caret_diagnostics.py`:
   `DEFAULT_SHA` → `39895d15…`.
2. Void by the per-instance rule, not by name: every `*.json` under
   `queue-v12-cutover-soak/` whose page sha is `20f09cc9…` (soak runs,
   diagnostics, and the condition-2 verdict judged on them) moves with `git mv`
   to the sibling `queue-v12-cutover-soak-void-20f09cc9/`, with
   `WHY-THESE-ARE-VOID.md` (English) naming the page move and the handoff.
   Files bound to any other page stay; the classification table goes in the
   report. Append the void to `RUNS.md`.
3. `--self-test` on both judges, then a real run of `check_soak_bank.py` on the
   now-empty bank: expected **0 of 12**, not RED.
4. One commit, zh-TW subject, `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`,
   no session line. Report `## SUMMARY` ≤ 30 lines: the three old/new values,
   the classification table, both self-test outputs, the 0-of-12 line.

### T1a — the 4b instrument-reproduction protocol (opus, design only)

1. Object: `drive_walk_focus.py` (banked in `manual-round-v12b-20f09cc9/`) on
   the candidate page `39895d15…`; new evidence directory
   `manual-round-v12c-39895d15/`.
2. Reproduction criterion, per-instance: two consecutive walks on identical
   bytes with `focusHeldEveryStop: true` give the same announced-paragraph
   count, **and** that count equals the number of stops at which focus was held
   and the paragraph's text reached the Orca log. Two walks that agree at 1
   are a reproducible broken instrument, not a reproducing one; say so.
3. Separate the three named variables one at a time, each against a control:
   Orca before Chrome vs after; a fresh Orca per walk vs `orca --replace`
   cycling; a fresh tab per walk vs the same tab walked twice. Never raise the
   window before every press (measured worse, 1 of 10).
4. Pre-register the stop rule and the budget (walks, not minutes). Say what
   each outcome means before anything runs.
5. Environment constraints to write in: `DISPLAY=:0`, consent file cited,
   desktop idle, logs on disk, no `pkill -f`.
6. Deliverable: `handoff/tasks/TASK-2026-09-06-4b-instrument-reproduction.md`
   (English), committed, plus `## SUMMARY` ≤ 30 lines. No desktop use, no runs.

### T1b, T2, T3 — briefs written after T0 and T1a land.

---

## Decisions recorded (2026-09-07, append-only)

- **D1 = A**, by the owner, verbatim 「D1: A」. The pursuit of v46 is bounded:
  two sonnet sessions or 2026-09-08, whichever first; then freeze on whatever
  is established.
- **D2 = after the cutover**, decided by the fable main session under the
  owner's delegation (「D2 D3 你幫我決定」). Finding 086 is not a regression,
  the revert trigger does not fire on it, and its fix lives in the shell's
  barrier and therefore moves the page. It is not batched into this freeze.
- **D3 = codex stays off.** The second model line for T1a's protocol is the
  fable main session's own pre-read (fable ≠ opus); a second opus seat would be
  the same line as the author. The protocol must carry its own red case
  (`AGENTS.md` §6); a wrong protocol costs at most D1's budget.

---

## T1a landed, and what it corrected (2026-09-07, append-only)

`handoff/tasks/TASK-2026-09-06-4b-instrument-reproduction.md` (commit
`ad1c3501`) passed the fable pre-read (D3's second model line). Two statements
above are corrected by it, and the corrections are recorded here rather than
edited in:

- "Raising the window before every press makes it worse" (the handoff, and the
  T1a brief above) overstates the banked numbers: raise-every-press and
  raise-once both announced 1; the separation is **raise at all (1, 1) vs no
  raise at all (10, 10)**, and the two 10-count walks were driven by a different
  script. The protocol adds arm A0 for that confound, under `AGENTS.md` §9's
  four conditions.
- "Nothing compares `web/` with `dist/`" (Parked, finding 090) is too broad:
  `problems()` in `build_e2_c_shell_bundle.py` compares source and dist hashes
  for every bound path and `tests/test_e2_c_shell_bundle.py` runs it. What 090
  still owes is the guard **with the runner**. The protocol uses the existing
  test as its shell gate and builds nothing.

### Consent for the T1b walks, ruled by the main session

The owner was asked (2026-09-07, by the main session) for a window in which the
desktop is not in use, with the purpose stated: the sonnet executor runs the
protocol on the desktop, Orca narrates, keys are sent to the browser window,
and anything the owner types voids the walk. The owner's reply, verbatim:
「現在可以」. The main session rules that this is the consent §1.4 of the
protocol asks for — given for this page (`39895d15…`, the protocol's only
object) and this purpose (instrument-reproduction walks; not condition 3, not
4b's judgement half) — and the executor records it verbatim in
`manual-round-v12c-39895d15/CONSENT.md` instead of asking again.

### T1b — run the protocol (sonnet, main tree, desktop)

1. Execute `TASK-2026-09-06-4b-instrument-reproduction.md` as written; the
   structure rule and role in its header bind you.
2. Consent: write `CONSENT.md` from the paragraph above; do not ask again.
3. Stop rules are the protocol's; STOP-SUCCESS ends the run at the first pair
   meeting §2.2 at n ≥ 2. Do **not** run T1c (§8) — the main session decides.
4. One commit at the end (evidence directory + the appended Execution record),
   zh-TW subject, `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`,
   no session line.
5. Report `## SUMMARY` ≤ 30 lines: identity gate before/after, one row per
   walk (arm, setting, `focusHeldEveryStop`, `announced`, `文件內容` count,
   valid/void), the outcome letter of §5, the settled configuration if any.

---

## T1b: outcome O-A, and T1c is opened (2026-09-07, append-only)

`findings/evidence/manual-round-v12c-39895d15/` (commits `09e59653`,
`9da0bd8f`). First attempt: zero walks, because the desktop held two Chrome
processes (an orphaned headless probe from 2026-09-06 20:21 and the owner's own
browser); the protocol's one-Chrome precondition held and nothing was killed by
the executor. The main session terminated the orphan and a stale page server
after checking parent and driver; the owner quit their browser. Second
attempt: **arm A0 setting X, the banked `drive_walk_focus.py` unmodified
(sha256 `414f1245…`), two consecutive walks, `focusHeldEveryStop: true`,
`announced` 10 and 10, `文件內容` 2 and 2, no foreign speech line — §2.2 met at
n = 10 on the first pair, STOP-SUCCESS.** Settled configuration: Orca before
Chrome, fresh Orca and fresh Chrome process per walk, one tab, raise once.

What this says about the handoff's headline: **the instrument never stopped
reproducing; the desktop stopped being quiet.** The six banked walks that
disagreed were taken with a second Chrome (another agent's ODS probe) and the
owner's own windows present, and the discriminator that separates the two
populations perfectly is whether Orca ever spoke `文件內容`, the document
group's label. The variables the handoff listed as "not yet separated" (Orca
start order, `--replace` cycling, tab reuse) were never reached because the
first arm settled it.

The residue reproduced in both walks: `這一行是普通內文` at 2, every other
paragraph at 1 — the exact shape §8.3 names. That is what makes T1c worth
running.

### T1c: go, with v46 taken from the previous session's artifact

§8.1 forbids reconstructing v46 from a sentence. It does not have to be:
`/tmp/candidate-round-tx3ue8b9/root/e2-editor-app.js` (mirror of 2026-09-06
23:15) has sha256 `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`,
matching the banked `orca-v46-9b29e39b.log`, and its diff against the v45
candidate page is exactly one hunk: `const doubled = structureSpeaks !== null;`
in place of `structureSpeaks === text`, plus the comment above it. The
executor preserves those bytes and the diff into the v46 evidence directory
before anything else, builds the v46 page by placing that one file into a
fresh v45 mirror (no edit to the tree; no generation is frozen for a
measurement), and pins V1 to `9b29e39b…` for the v46 walks.

**Consent, ruled by the main session:** the owner chose D1 = A knowing it
includes "v46 measures better on the same protocol", said 「現在可以」 for the
desktop and 「Chrome 關了」 when asked to clear it. That consent covers the
T1c walks on both pages; the executor records those three utterances verbatim
in `manual-round-v12d-9b29e39b/CONSENT.md` and does not ask again.

Budget: §8.4's eight walks. Verdict form: §8.3's three clauses, written before
the run; the main session reads the result and decides D1's landing. The
executor does not land v46.

---

## T1c: v46 measures better; D1 = A lands it (2026-09-07, append-only)

`findings/evidence/manual-round-v12d-9b29e39b/RESULT-4b-v45-vs-v46.md`
(commit `de0299a3`). Six walks, all VALID, no spare used, zero environment
voids, settled configuration throughout. v45 pair: announced 10/10,
`這一行是普通內文` 2/2. v46 pair: announced 10/10, every paragraph at 1. v45
return pair: 10/10, 2/2 — no drift. §8.3's three clauses all MET. The v46
bytes were the previous session's own artifact (sha `9b29e39b…`), preserved
into the evidence directory with the one-hunk diff before any walk.

**Decision (D1 = A, second branch): land v46.** The rule of ruling E-1
applies — the changed shell and its new frozen generation (**v47**) land in the
**same commit**, together with `dist/` brought to byte identity with `web/`
and the three judge constants re-pointed. The soak bank is empty, so nothing
is voided by this move; `RUNS.md` records the move with zero runs voided.

**Conditional ruling, written before the landing:** if the candidate page
built from the landed tree has sha256 exactly
`9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`, then the
two v46 walks in `manual-round-v12d-9b29e39b/` were taken on the final page
and constitute **4b's mechanical half on it** (agent-driven under the consent
on file: ten paragraphs reaching the log, headings announced with level, the
residue absent), leaving 4b's judgement half to the owner's ear at T4. If the
sha differs, the walks are not on the final page and 4b is re-taken on it;
the landing still stands, because the measured difference is the one hunk.

The earlier worry that 4a's probe reads the live region (the 2026-09-06
revert's reason) is already discharged: the amendment of 2026-09-05 made
term 4's reading the text under the active descendant of the focused node,
with the live region only as a fallback when no such relation exists. T2 will
show whether that holds on v47; the executor reports a red, never edits the
judge.

After the landing the page is **final for this gate**. T2 opens.

---

## T1d overshot into the cutover; corrected by v48 (2026-09-07, append-only)

Commit `000a57e2` landed the v46 hunk and froze v47 — and also performed the
cutover: the executor used `build_cutover_page.py --write`, which rewrote
`web/e2-editor-app.js` (and thence `dist/`) to `PINNED_WASM_SHA256
4ec1e389aaab3b03` and `workerUrl …/e2-editor-v12/…`. `f7f20317` carried
`4a2710bba1ef07d9` and `e2-editor-v8` (sha `94edc4d9…`, the handoff's "shell"
row). The executor's report said v45's source "similarly carries its cutover
repoint"; it does not. v47 is therefore a generation frozen on cut-over bytes
before the gate passed.

**Disposition:** no history rewrite. One further commit restores the two
shipping lines (v8 profile, v8 pin), keeps the v46 hunk, brings `dist/` back
to identity, freezes **v48** on that shell and points `MANIFEST` at it; v47
stays in the tree as the record of the mistake. The candidate page sha is
expected to remain `9b29e39b…` — the repoint of the v8 shell with the v46
hunk is by construction the page T1c measured — and is re-measured without
`--write`. The judges' served-shell pin moves to v48.

**What the main session takes from it:** the brief said "build the candidate
page … and hash it" and the tool has a write mode. A measurement build must be
named as one — "never `--write`; the page is a measurement, not a landing" —
because "build" was read as the tool's default landing path. The rule joins
the delegation notes.

The conditional ruling above (v12d walks = 4b's mechanical half if the built
page is `9b29e39b…`) is decided on the v48 measurement, not on `000a57e2`'s.

---

## The page is final: `9b29e39b…` on shell generation v48 (2026-09-07, append-only)

Commit `2d319677`. Checked by the main session against the tree: the diff
from `f7f20317` in `web/e2-editor-app.js` is one hunk (the v46 change); the
shell ships `e2-editor-v8` with pin `4a2710bba1ef07d9`; `web/` and `dist/`
are byte-identical; `MANIFEST` is v48 (`bundleSha256 ecfb6866…`); both judges
pin page `9b29e39b…`, the soak judge pins served shell `ecfb6866…`. The
candidate page built without `--write` is `9b29e39b…`, the page T1c measured.

**Ruling (the conditional one above, now decided):** the two v46 walks in
`findings/evidence/manual-round-v12d-9b29e39b/` were taken on the final page
and are **4b's mechanical half on it**, agent-driven under the consent on
file — ten paragraphs reach the log, headings are announced with level, the
second-heading residue is absent, and the same session's v45 return control
still shows it. 4b's judgement half (order, verbosity, what it sounded like)
remains the owner's at T4, together with condition 3's six cells.

Five bound identities for this gate, for the record: profile `e2-editor-v12`
(pins `4a2710bba1ef07d9` → `4ec1e389aaab3b03`), candidate page `9b29e39b…`,
shell generation v48 `ecfb6866…`, E1-C binding intact.

### T2 — re-earn the identity-bound evidence on `9b29e39b…` (sonnet, main tree, headless)

Order chosen for the calendar: the soak's first two runs go first so that
UTC day 2026-09-06 (which ends 08:00 CST 2026-09-07) can be banked; then 4a,
condition 2, the ODT round trip, revert condition 3. Each item re-executes
the procedure its 2026-09-06 predecessor recorded, into a directory named for
this page; each is judged by the existing judge, never by the executor's
reading. A red is reported with its payload, not fixed.

1. Before every run: the shell bundle test (or `sha256sum` of `web/` vs
   `dist/` over the 13 bound paths) — finding 090's manual rule.
2. Soak runs 1 and 2: `run_e2_c_product_path.py --browser chrome
   --candidate-profile e2-editor-v12`, banked per `RUNS.md`'s conventions,
   judged by `check_usable_editor.py` and `check_soak_bank.py`.
3. 4a: `gate-4a-on-9b29e39b/`, per `gate-4a-on-20f09cc9/` and the 2026-09-05
   amendment (three runs, one mutation stamped never banked, one control on
   the shipped page), judged by `check_4a.py`, all eight terms.
4. Condition 2: three diagnostic runs, judged by `check_caret_diagnostics.py`.
5. ODT round trip, per `queue-v12-cutover-roundtrip/`.
6. Revert condition 3, per `queue-v12-cutover-revert-rehearsal/` and ruling
   E-3; the rehearsal must leave the tree exactly as it found it.
7. Commits: one per item, zh-TW subjects. Report `## SUMMARY` ≤ 30 lines with
   each judge's verdict line verbatim.

---

## T3 — the soak, scheduled to run unattended (2026-09-07 01:50 CST, append-only)

The owner is asleep and asked the main session to continue on its own
(「這輪任務完成之後，你可以繼續自主執行下去嗎」). The soak's calendar
clause needs >= 12 clean runs across >= 3 UTC days with >= 2 on each; T2 banks
runs 1–2 on UTC 2026-09-06 (which ends 08:00 CST 2026-09-07). The rest are
scheduled as one-shot wake-ups of this session (they die with the session, so
the terminal stays open and the machine must not suspend):

| wake (CST) | UTC day | runs | target bank |
|---|---|---|---|
| 2026-09-07 08:17 | 09-07 | 3 | 5 |
| 2026-09-07 15:47 | 09-07 | 2 | 7 |
| 2026-09-08 08:17 | 09-08 | 3 | 10 |
| 2026-09-08 15:47 | 09-08 | 2 | 12 |

Two sessions per UTC day rather than one, because the three-day spread exists
for defects that depend on machine state and elapsed time.

Each wake: the main session checks T2's report and the bank
(`check_soak_bank.py`), dispatches **one sonnet agent** for that session's
runs (shell bundle test before every run; the runner with
`--candidate-profile e2-editor-v12`; `check_usable_editor.py`; banked per
`RUNS.md`; committed), reads its `## SUMMARY`, and appends the bank's verdict
line here.

**FAIL policy, decided now.** Any FAIL, extra NE, or different NE id is banked
and restarts the count — the criterion, not an exception. A sonnet agent
drafts the finding from the run's payload. Then:

- if the failing id is the **known intermittent** the gate document already
  names (`clear-format-removes-every-inline-format` abstaining), the count
  resumes at the next scheduled session and the schedule is extended by the
  runs lost;
- **anything else stops the schedule.** The main session writes a handoff for
  the owner and does not decide a fix, because a fix moves the page.

A red from T2 on 4a, condition 2, the round trip or revert condition 3 also
stops the schedule: no soak run is taken on a page whose other conditions are
red, since the fix would void it.

**What the main session will not do unattended:** T4 (the owner's six cells
and 4b's judgement half) and the cutover itself. When the bank reaches 12
clean across >= 3 UTC days, it writes
`handoff/HANDOFF-<date>-soak-closed-only-T4-remains.md` and stops.

### T3 ledger (append one line per session)

---

## T2 came back red; the schedule is stopped (2026-09-07 ~04:00 CST, append-only)

Commits `f4e16c63` (soak 1–2), `37b6def7` (4a), `25670d0e` (condition 2),
`d450f6ff` (ODT round trip), `dbabc3c9` (revert condition 3). Condition 2,
the round trip and revert condition 3 are **discharged on `9b29e39b…`/v48**
(judges' `ok: true`). Three reds, each with its mechanism read by the main
session:

**R-1 (product path, blocks the count).** Soak runs 1 and 2 both FAIL on
`the-document-region-says-why-it-is-empty`, payload `{"present": true,
"text": "", "reason": "paragraph", "offers": "1"}`; reproduced 6/6 on every
v12-pinned page in items 1, 3 and 5 and 0 times on the v8 control. The
check's oracle (`run_e2_c_product_path.py` ~7286): *the accessibility region
always carries something to read … empty is the failure*, read from
`#a11y-para`'s text. Finding 088's fix (from v45 on, not v46) is *one
paragraph, one voice*: that region says nothing when the structure channel
already names the paragraph, and it marks `data-deferred-to-structure="1"`
so a probe can tell that silence from "nothing to say". The check never
learned the attribute. The ten runs on `20f09cc9…` predate 088's fix; no
soak run was ever taken on v45. **So this is not a v46 regression: the 088
fix family and this check's oracle contradict by design, measured tonight
for the first time.** Not the known intermittent → the schedule stops (four
wake-ups deleted). Disposition is the owner's, because it changes what
"clean" means (§9's count semantics); the main session's recommendation is
recorded in finding 092 as a recommendation, not a ruling.

**R-2 (judge pin, corrected now).** `one-served-shell: false` because
`DEFAULT_SERVED_SHELL` pinned v48 (`ecfb6866…`), the shell as the tree
serves it, while a candidate run's `servedSha256` is computed over the
mirror **as served**, entrypoint repointed — by construction the digest of
the cut-over shell, which is v47 (`cf7f9233…`). Ruling E-4's own words are
"the digest the cutover generation will declare"; the runner's comment at
`served_shell_identity` says the same. T0's value (v45's `a46c8518…`, from
the handoff's Task 0) was wrong in the same way and never exercised. **The
pin moves to v47's digest.** v47, frozen by mistake, is exactly the cutover
generation.

**R-3 (instrument, corrected now as a test change).** 4a's term-6 mutation
`projection-not-wired` finds 0 occurrences of its anchor after the v46 hunk;
seven of eight terms pass. `make test-e2-c-static` exits 2 on the committed
tree for the same reason — a red test on the tree, the E-6 shape. The
pattern is re-anchored on the v46 source with its red case re-proven (the
mutation reddens the projection term(s) and nothing else; page restored by
sha). No product change.

Unattended work tonight: R-2, R-3, finding 092, and a handoff for the owner.
Nothing that moves the page; nothing that changes a criterion.

---

## The follow-up landed, with one downgrade (2026-09-07 ~05:00 CST, append-only)

Commits `53961163` (R-2: served-shell pin → v47, both banked runs now
`one-served-shell: true`), `c668b812` (R-3: mutation re-anchored on
`projectFocusedParagraph(snapshot, structureSpeaks);`, static mutation tests
green, `make test-e2-c-static` exit 0), `17b7740b` (finding 092),
`c0769105` (handoff). The soak judge's `--self-test` still declines: it
builds its fixtures from the real bank, and the bank holds only R-1 runs, so
RED 11 cannot be isolated until a clean run exists — recorded, not a defect.

**Downgrade, ruled by the main session.** `RESULT-4a.md` and the handoff
record 4a term 6 as MET because the mutation run reddens exactly
`the-document-region-says-why-it-is-empty` and nothing else. On this page
that check is red **unmutated** (R-1), so the mutation run's composition
(37/2/1) is identical to the baseline's: a mutation that changed nothing
would score the same. The set comparison passed; the causal claim — *the
instrument can fail here* — is unsupported (`AGENTS.md` §6: a red that was
red before the change proves nothing; §7: verify the claim, not the proxy).
**Term 6 is NOT_ESTABLISHED on `9b29e39b…` pending R-1; 4a stands at 7 of 8.**
What R-3 did earn is narrower and real: the pattern matches once, the
harness applies it, the tree's static test is green again. When R-1's
disposition lands and a baseline candidate run is green, term 6 is re-taken
against that baseline in the same session.

Where the handoff of 2026-09-07 says 4a is discharged in full, this
paragraph supersedes it; the handoff carries the same correction appended.

---

## R-1 = A, by the owner (2026-09-07, append-only)

The owner's reply, verbatim: 「A」. The check
`the-document-region-says-why-it-is-empty` is amended to verify the claim
("there is something to read") rather than the proxy (one DOM node's text):
the source may be the live region **or** the structure channel's focused
node, and the region's own attribute `data-deferred-to-structure="1"` is the
signal that names which. This changes the clean-run predicate, so the count
restarts — it is at 0; runs 1–2 stay banked FAIL under the old wording and
are not re-judged. The criterion lands before any run that could satisfy it.

### T5a — amend the criterion and implement it (opus, main tree)

1. Append to `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` an
   amendment dated 2026-09-07: the rewritten oracle; `AGENTS.md` §9's four
   conditions stated (prior to satisfaction — count 0; forced by finding 092;
   form — per-instance; deadline — closes with the 12th clean run); count
   semantics; and the red cases named before the code exists: (i) both
   channels silent; (ii) region deferred while the structure's focused node
   has no text; (iii) the existing inconsistency cases; (iv)
   `projection-not-wired`. Each must FAIL exactly this check.
2. Implement in `run_e2_c_product_path.py`: the region reader also returns
   `deferredToStructure` and the text under the structure channel's active
   descendant; the check passes iff present ∧ reason known ∧ consistent ∧
   (text ≠ "" ∨ (deferred = "1" ∧ structureText ≠ "")); when deferred = "1",
   reason must be `paragraph` and offers `1`. Observed payload carries the
   new fields. Oracle string rewritten to match the amendment.
3. Add mutations (i) and (ii) to the mutation table with exact-once patterns;
   `make test-e2-c-static` green. No product file changes.
4. Append the disposition to finding 092. Commit per item; report. The runs
   are T5b's (sonnet): four red cases, one baseline candidate run banked as
   the next soak run if clean, 4a term 6 re-taken against it.

---

## T5a landed and passed the pre-read; T5b opens (2026-09-07, append-only)

Commits `02b0a7d4` (amendment, text first), `7dbbcc70` (runner: the reader
returns `deferredToStructure`, `activeDescendant`, `structureText` from one
evaluation; the check's predicate is the amendment's formula; oracle
character-identical), `dbf0a820` (mutations
`structure-names-nothing-while-the-region-defers`,
`the-region-defers-with-a-reason-it-owed-the-user`), `7ac0b3ea` (finding 092).
`make test-e2-c-static` exit 0, 108 tests. The main session read the
amendment (forcing facts, oracle, formula, §9's four conditions, count
semantics, red cases (i)–(iv), the default) and the predicate hunk; they
agree clause by clause. One correction to the T5a brief, made by the author
and accepted: red case (ii) as the brief phrased it would *pass* the new
predicate on the candidate (the structure channel really does have text), so
(ii) is instead a deferral with an illegitimate `reason`, which isolates the
implication clause. Both mutations' `alsoRed` are declared unmeasured until
T5b runs them.

### T5b — red cases, the first run under the amendment, term 6 (sonnet, main tree, headless)

1. Before every run: `make test-e2-c-static` (or the shell bundle test).
2. Four red-case runs on the candidate path, one per mutation ((i), (ii),
   `projection-not-wired`, and one existing inconsistency case if the harness
   has one; else record (iv) as covered by static tests): each must FAIL
   `the-document-region-says-why-it-is-empty`; record what else reddened and
   correct the `alsoRed` lists to what was measured (a table edit in the
   mutation module, nothing else). Page restored by sha after each; runs
   stamped, never banked.
3. One baseline candidate run under the amended predicate. If 38 PASS / 2 NE
   with the fixed NE set: bank as `soak-run-03-candidate.json` — the first
   run that can count — and run `check_soak_bank.py` (expect 1 of 12,
   `one-served-shell: true`) and its `--self-test` (now buildable). If not
   clean: bank it, report the payload, stop.
4. 4a term 6 re-taken against that green baseline (`projection-not-wired`
   run reddens exactly the check, baseline green), `check_4a.py` for all
   eight terms; append to `RESULT-4a.md`.
5. Commit per item; `## SUMMARY` ≤ 30 lines with every judge line verbatim.
