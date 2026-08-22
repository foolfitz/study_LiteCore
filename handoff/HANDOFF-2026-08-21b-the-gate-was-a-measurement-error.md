# Handoff — 2026-08-21b: the one thing gating the link was a measurement error

> # SUPERSEDED — read `HANDOFF-2026-08-22-the-oracle-was-the-defect.md`
>
> **The headline of this page is right and its mechanism is wrong.** Finding 064
> is retracted, but not because "each arm's paragraph break destroys the
> previous arm's evidence" — that does not happen. Both 064 and the finding 065
> this page files were **the same false negative in `inline_styles_of()`**,
> which could not see formatting carried on a paragraph's own automatic style.
> An operator found it by seeing bold on the canvas that the saved document
> denied.
>
> Kept because §2's adjudication and §6's corrections are an honest record of
> being carefully wrong twice.


> Entry point for the next session. Reading this page is enough to take over.
> Previous: `HANDOFF-2026-08-21-the-link-is-authorised.md`, whose §1 named
> **finding 064's mechanism** as *the* remaining thing that could change the
> link payload, and said to start there.
>
> **English per `AGENTS.md`.** `devlog/`, `research/`, `specs/` stay zh-TW, and
> so do `findings/*.md` — only `findings/evidence/**` is English.
>
> **The title is the whole of it: finding 064 is retracted.** No artifact was
> rebuilt, no `web/`, `sdk/` or `editor-shell*/` file was touched, and no link
> has happened.
>
> **The link does NOT execute yet** — §2. An earlier version of this page said
> it did; that was adjudicated against and is corrected there. The gate did not
> vanish, it moved to finding 065's unattributed layer, and two cheap rounds
> settle it.

## 0. Bindings

| | |
|---|---|
| artifact | **`29ec627bf8a5588b…`** — unchanged. No relink, no engine rebuild |
| shell | **v25 `07143f961d82c4b3…`** — unchanged. Only `tools/`, `e2/`, `findings/`, `handoff/` and the Makefile's static-test list were edited |
| matrix | `e2/validation-matrix-v2.json` — **untouched**; it records D0, not product-path checks |
| `KNOWN_RED` | **1** — `formatting-survives-the-next-paragraph-break`, **finding 065**. 064's declaration is gone |
| product path | Chrome and Firefox both `ok: true`, `staleKnownRedDeclarations: []` — durable copies in `findings/evidence/065/` |

## 1. What happened

The handoff's candidate was named and answerable: the `renderDocument()` the
product performs between a format action and the typing
(`web/e2-editor-app.js:377-382`). A prediction was written first
(`findings/evidence/064/PREDICTION-render-between-format-and-typing.md`), a
probe was built with a three-state positive control for its own instrument, and
the candidate was measured.

**The baseline did not reproduce.** A single `set-italic` arm on a freshly
booted page put italic on the marker — shipped behaviour, repaint and all. The
probe's verdict logic refuses to read any arm after the negative control comes
back green, and that refusal is the only reason this was found rather than
walked past.

Walking the ladder from there:

* The runner's inline block, replayed **verbatim** on one page load, fails all
  eight arms — `set-bold` first among them.
* The same sequence with **a save after every arm** has all eight arms
  **correct at the moment their marker is typed** — the same eight results D1
  reports.
* At any moment the document holds **exactly one `<text:span>`**, around the
  marker just typed.
* One action at a time: the thing that takes it away is
  **`insert-paragraph-break`, alone**, taken immediately after typing the
  formatted text. `spans` — a **global** count over `content.xml` — goes 1 → 0,
  so the span left the document rather than moving next door. Two caret moves
  inside the run do not do it. (Whether a break *elsewhere* is harmless is **not
  established** — see §6.)

So the format reaches the text. Each arm's opening paragraph break destroys the
previous arm's marker, and reading all eight verdicts from one save at the end
reported eight failures where there were none. **The isolation device added
that same day to defeat the coalescing trap became a worse version of it.**

Full reading: `findings/evidence/064/RESULT-render-between-format-and-typing.md`.
Reports: `findings/evidence/064/product/` (five, with a README).

## 2. What this does to the link — **attribute first, then link**

This was adjudicated externally (fable, 2026-08-21) because it is a fork, and
**the adjudication went against my first answer.** I had concluded "the gate is
discharged, execute with six". That is wrong, and the reason is worth carrying:

> The gate's stated function was "the only remaining thing that can change the
> payload". **That property transferred to 065; it did not vanish.** My own
> evidence says 065's remedy, if it is on our side at all, is not in the shell —
> "no product code sits between the format and the loss". The previous
> handoff's dichotomy mapped exactly this situation to *wait*. Escaping it
> because the finding got renumbered is formally correct and substantively
> evasive.

So the order is:

1. **The operator round** — `handoff/RUNBOOK-operator-2026-08-21-finding-065.md`.
   Minutes of human time, not yet done. 065 as measured types through the insert
   field and the toolbar button; a human types through `#sink` /
   `beforeinput` / `attachInput` and presses a real Enter. **Both halves of the
   measured sequence differ from the user's path**, and this tree lost three
   defects to that gap in one day. It also gets a first directional signal from
   desktop LibreOffice.
2. **The native round** — the discriminator for 065's layer. Same-day work in
   this tree (046, 048 and the block-identity rounds were all native).
3. **Then the link**, with six or with a *specified* seven, as the measurement
   says. Execution discipline unchanged: archive the profile first, no rebuild
   between sweep and verdict, re-state all five bindings and re-run D0 on both
   browsers immediately after, and land it **before** M2a.

The economics are what settle it. A relink mints a new identity and invalidates
every verdict; if 065 turns out to be our engine *after* the link ships, its fix
costs a whole additional cycle or stays unfixed in M1's closing artifact. The
rounds cost minutes to a day, and there is no deadline pressure by this tree's
own rule (`no-release-deadline-framing`).

**One more reason to re-confirm with the user rather than proceed on the
existing authorisation:** the link was authorised in a world where the standing
red was "engine fine, product broken". The world is now "product fine,
engine-or-core unattributed". The factual basis moved.

Rejected, explicitly: "you cannot close M1 while 065 is open" is *not* a reason
to block. The link neither ships nor worsens 065 — the defect is on the current
artifact too — and the checklist records the cell honestly as `partial` with a
`KNOWN_RED`. The reason to wait is payload economics plus a pending cheap
measurement, not optics.

**The mutation rerun does not gate the link either.** The retraction never
rested on the runner: the probe, D1, and the shipped-page runs each carry it
independently.

## 3. Finding 065, which is real and is not in the payload

**Press B, type, press Enter — the text you just typed is no longer bold.**
No error, no toast, `ready` throughout, revision advancing normally. The span
leaves the text behind and reappears around whatever is typed next, so a second
marker comes out bold **with no press at all**.

`findings/065-pressing-enter-takes-the-formatting-off-the-text-you-just-typed.md`.

**Reproduces 100% on both browsers**, through the shipped runner's own new
check. **The layer is NOT attributed.** The break is one
`startEditorUnoAction(..., ".uno:InsertPara")` (`src/probe_engine.cpp:4413`) and
no product code sits between the format and the loss — but that rules the
product out, it does not name core. **The next step is a native round**: the
same three actions on native LOK. If it drops there it is upstream and a draft
can start; if not, the difference is on our side of the dispatch.

It is **not** added to the link payload as it stands: its layer is unknown, and
putting an unattributed defect into a settled payload is what the freeze
discipline exists to prevent. But that is not a reason to link around it — the
link waits for the *round*, not for the fix (§2). If the native round says our
engine, a **specified** item 7 goes to the user; if it says core, the link
executes with six.

## 4. What changed in the tree

**`tools/run_e2_c_product_path.py`**

* `format_arm` now takes **its own save** and is judged from it, recording all
  four format properties. `every-inline-format-reaches-the-document` reads each
  arm from that save instead of from one at the end. It now **passes** — four
  formats, both directions, on both browsers.
* 064's `KNOWN_RED` entry is **removed**; a declaration that outlived its defect
  would fail the round as stale, which is the mechanism working.
* New check **`formatting-survives-the-next-paragraph-break`**, declared
  `KNOWN_RED` against 065. Its precondition is half the check: a marker that was
  never bold reports `NOT_ESTABLISHED`, not a failure.
* `clear-format-removes-every-inline-format` went from **NOT_ESTABLISHED to
  passing**. Its precondition ("all four were on") was being read from the
  **cleared** document — a moment that document no longer records. It now reads
  MKALLON's own save. Nothing about the button changed; the question was being
  asked too late.

**A hazard I created and you should not repeat:** the HEAD-vs-current batch
swapped a **tracked** file (`tools/run_e2_c_product_path.py`) in the working tree
while other work was reading that tree, which made `git diff` on that path
meaningless for the duration and had to be worked around by hand. Frozen copies
in a scratch directory would have cost nothing and are this tree's own pattern
(`build_mirror`). Do it that way next time.

**`tools/probe_064_format_reaches_typing.py`** — new diagnostic. Mirrors exactly
one file (a counter and an early return at the top of `renderDocument()`, inert
without `globalThis.__f064`), `probe.wasm` byte-identical, never writes `dist/`,
every report `evidenceClass: "diagnostic"`. Arms: `baseline`, `suppressed`,
`save-in-slot`, `iso-bold`, `iso-quiet`, `runner-sequence`,
`runner-sequence-saved`, `retention`, `retention-ladder`,
`retention-ladder-adjacent`. Registered in `make test-e2-c-static`.

**Findings and evidence** — 064 revised in place with a revision record and a
banner; 065 filed; `findings/evidence/064/` holds the prediction, the result and
the five reports.

**`e2/product-path-coverage.json`**, **`e2/usable-editor-checklist.json`** —
notes rewritten. `turn-formatting-off` **stays `partial`**: the reason it was
demoted is gone, but it now carries a `KNOWN_RED` check, and a cell with one of
those is not done. The uncovered part is named.

## 5. What is left

| | |
|---|---|
| **The link** | Authorised, payload settled at six, **not started, not blocked** |
| **065's layer** | A native round. Until then it may not be called upstream and must not be drafted |
| **065's second limit** | The two ladder arms differ in two coupled ways (the caret left the run *and* the break landed elsewhere). Separating them needs a click that returns to exactly the end of the run |
| **`cut`** | Unchanged. The `paste("")` probe still belongs *inside* the link work |
| **`blur` / `pointercancel`** | Unchanged. Still abstaining on purpose; next step is the copy path's `codePoints` |
| **Recovery's second inducer** | Unchanged. Open and narrowed |
| **a11y gate 0** | Unchanged. Prepared, not run; the rebuild is the user's hours |
| **The mutation net was ALREADY red at HEAD** | **Measured, six runs, HEAD runner vs this session's, alternating, on a real filesystem: `findings/evidence/mutation-net-already-red/`.** `save` and `ime` fail on **both**; `copy` passes on **both**. **No round's verdict changed.** The rounds fail on stale declared-collateral bookkeeping, not on escaped detection — the owning check goes red every time. Fixing it means judging each collateral red as structural-or-real, per entry; widening `alsoRed` to make a round pass is the trap, so it was left. **Open work, not caused by today** |
| **Nothing is committed** | Still true, and now there is more of it. `e2/`'s checklist and coverage are among the changes |

## 6. Two things the adjudication caught that I had wrong

**The A/B was not a matched control, and its own report said so.** I wrote "the
identical break, after the caret has left the run, does not do it". The
surviving arm's record carries `derived: false` — `LINE_INK` found no ink on
that page load, so its clicks used the fallback viewport fractions (`near 0.06`,
the left margin, which the runner's own comments record as snapping the caret to
character position 0), and its break consequently landed at the **paragraph
start**, inserting an empty `<text:p text:style-name="P2"/>` before the marker's
paragraph. Three differences, not two. **The field that declares an arm degraded
is worth nothing if the write-up does not read it.**

Withdrawn accordingly: finding 065 now claims only that the break taken
**immediately after** typing formatted text removes it. Whether a break
elsewhere is harmless is not established. What carries 065 is
`retention-ladder-adjacent` **on its own** — a within-arm before/after, one
action at a time, on a **global** `<text:span` count over the whole
`content.xml` (so 1 → 0 means the span left the document, not that it moved next
door) — plus the shipped runner's own check, red on both browsers.

**The 064-era check exists in no preserved file.** HEAD predates the whole of
2026-08-21, so neither frozen runner copy contains the version that read eight
verdicts from one save. That the check had that shape rests on finding 064's own
contemporaneous text plus the replay reproducing its exact final-save
fingerprint. Adequate, but it cannot be re-audited. Commit more often on a day
that rewrites a check.

## 7. The traps this round paid for

**A negative control that does not reproduce must stop the run.** Write that
into the probe's verdict, not into your own alertness. It is the only reason
this was a retraction and not a second wrong candidate.

**Every question about a document has a time.** Reading N answers from one save
is not N measurements. If a check's arms mutate the thing the earlier arms were
about, the oracle has to be taken per arm.

**An isolation device can be the thing that destroys the evidence.** After
adding one, measure *what it did to the other arms*, not whether it fixed the
symptom you added it for.

**Two harnesses disagreeing is not two measurements.** D1 and the product path
agreed all along. Ask, in order: same moment? same oracle? — and only then,
different path. `harness-path-vs-user-path` is for designing cells, not for
explaining disagreements.

**Checks are coupled through the product's cache.** The toolbar decides
`enabled` from `editorState.format`, so a check that leaves bold ON makes the
next check's "turn it on" press send `enabled: false`. Placing the new 065 arm
before `clear-format` knocked out that check's precondition — measured, then
moved. A toggle read from a cache is an ordering dependency between checks.

**Asking a changed document what it used to look like** asks it about a moment
it no longer records. That is what kept `clear-format` abstaining for days.
