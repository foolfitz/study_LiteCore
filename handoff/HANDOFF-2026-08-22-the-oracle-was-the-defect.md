# Handoff — 2026-08-22: both findings were the oracle, and an operator found it

> Entry point. Reading this page is enough to take over.
> Supersedes `HANDOFF-2026-08-21b-the-gate-was-a-measurement-error.md`, which is
> **wrong about the mechanism** and carries a forward pointer.
> Before that: `HANDOFF-2026-08-21-the-link-is-authorised.md`.
>
> **English per `AGENTS.md`.** `devlog/`, `research/`, `specs/` and
> `findings/*.md` stay zh-TW; only `findings/evidence/**` is English.

## 0. Bindings

| | |
|---|---|
| artifact | **`29ec627bf8a5588b…`** — unchanged. No relink, no engine rebuild, no `web/`, `sdk/` or `editor-shell*/` edit |
| shell | **v26 `b25b6c29d1e74012…`** — one file changed (`web/e2-editor-app.js`, finding 066's fix), bundle re-minted, matrix binding re-stated |
| matrix | `e2/validation-matrix-v2.json` — untouched |
| `KNOWN_RED` | **empty** — third time in this file's life. Findings 064 and 065 both came off through its own stale-declaration mechanism |
| findings | **064 and 065 are both RETRACTED**, filenames prefixed `NNN-RETRACTED-`. **066 filed, measured, fixed and netted** the same night |
| product path | **Chrome and Firefox both `ok: true`**, `knownRed: []`, `staleKnownRedDeclarations: []`, and the three inline checks all PASS. Durable copies: `findings/evidence/064/after-the-fix/` |

## 1. What actually happened

`inline_styles_of()` — the oracle every inline-format check in this tree depends
on — contained this:

```python
# Found, and deliberately NOT inheriting the paragraph's style: this asks
# about INLINE formatting, and text that is not in a span has none of it.
```

**False for ODF.** A **uniformly formatted** paragraph carries its character
properties on its own automatic style and emits no `<text:span>`:

```xml
<style:style style:name="P3" style:family="paragraph" style:parent-style-name="Standard">
  <style:text-properties fo:font-weight="bold" .../></style:style>
<text:p text:style-name="P3">RETLADDERONE</text:p>
```

Every arm of these checks presses `insert-paragraph-break` and then types its
marker, so **every marker ends up alone in its paragraph** — the uniform case.
Every one read as unformatted.

Two findings were built on that and **both are retracted**:

* **064** "an inline format never reaches the text you type" — it does. With the
  oracle fixed, even the original one-save-at-the-end reading is correct on all
  four formats in both directions.
* **065** "pressing Enter takes the formatting off" — it does not. `spans` going
  1 → 0 across a break is **correct export**: the paragraph became uniform, so
  the bold moved from a span onto the paragraph's style.

**Inline formats work.** Nothing here needs an engine change.

## 2. Who caught it, and why nothing else could have

An **operator**, running `RUNBOOK-operator-2026-08-21-finding-065.md`. They
reported "A: it is bold" from the canvas while the ODT they had just saved read
`bold: false`.

Nothing automated in this tree could have caught it: every check that could —
`every-inline-format-reaches-the-document`,
`clear-format-removes-every-inline-format`,
`formatting-survives-the-next-paragraph-break`, and the whole diagnostic ladder
— is **downstream of the same function**. An oracle's error is invisible to the
checks that depend on it.

The unit tests did not catch it either: `tests/test_inline_styles_of.py` had
nine cases and **every one put the marker in a span**, so the paragraph-carrier
branch was never exercised.

## 3. The shape this got wrong twice in two days

Both rounds asked the document a question it does not answer that way, then read
a mechanism out of the answer:

* Round 1 read "no span on seven of eight markers" → *the product path is
  broken*, complete with a D1 comparison and a plausible physical story.
* Round 2 read "1 span → 0 across one break" → *the span follows the caret*,
  complete with a clean A/B and raw XML.

Both were internally consistent. Both survived adversarial review **of their
reasoning** — an external adjudication examined round 2 closely, found a real
flaw in its control arm, and still accepted the finding, because the reviewer
was also reading through the broken oracle. What killed them was a person
looking at a screen.

Reusable:

* **A deliberate wrong decision is harder to find than a careless one.** The
  comment explaining why the paragraph style was skipped is what made it look
  already-considered.
* **An oracle cannot be validated by the checks that use it.** It needs its own
  tests, and those tests need to cover the shapes the checks actually produce.
* **A count is not a measurement of the thing you care about** until you have
  asked what else can move it. `spans: 1 → 0` was re-expression, not loss.
* **The negative-control discipline worked and was not enough.** The probe
  refused to read its arms when the baseline came back green — that is what
  produced the correct headline in round 1. It cannot catch an oracle that is
  wrong in the same direction for every arm.
* **The human round was scheduled as a confirmation and functioned as a
  refutation**, and was nearly deprioritised as nice-to-have.

## 4. What changed in the tree

* **`inline_styles_of()`** resolves the paragraph's style when there is no span,
  and reports `fromParagraphStyle` so a caller can still tell the two apart. A
  span still wins over its paragraph.
* **`tests/test_inline_styles_of.py`** — four paragraph-carrier cases added;
  **three of them fail against the pre-fix function** (the fourth passes both
  ways and says so in a comment).
* **`KNOWN_RED` is empty.** Both retractions ran through the mechanism designed
  for it, and it worked both times.
* **`formatting-survives-the-next-paragraph-break`** stays, as a **passing**
  check. Press B, type, press Enter, is it still bold — nobody had asked that
  before this round.
* **`every-inline-format-reaches-the-document`** reads each arm from its own
  save. That is no longer *needed* (the one-save reading is correct once the
  oracle is), but it is cheap and it records more. Its comments say so.
* **`clear-format-removes-every-inline-format`** passes, after days of
  `NOT_ESTABLISHED`. Two causes: this bug, plus a genuinely mistimed read (its
  precondition was taken from the **cleared** document, a moment that document
  no longer records).
* **`tools/probe_064_format_reaches_typing.py`** — the diagnostic. Mirrors one
  file, `probe.wasm` byte-identical, never writes `dist/`. Registered in
  `make test-e2-c-static`.
* Findings, evidence and the checklist updated; `turn-formatting-off` is back to
  `done`.

## 4b. Finding 066 — the same operator round, later the same night

The operator went back for a second round and reported three more things. One of
them turned into a measured, fixed, netted defect:

> "after pressing a style button the focus does not return to the editing
> surface, it stays on the button (feels like HTML behaviour)"
>
> "styles apply sometimes, mostly not, I cannot see a pattern"

**Those are one thing, and the first causes the second.** Measured, both halves:

* A **real** click (CDP `Input.dispatchMouseEvent` — `HTMLElement.click()` runs
  no default action and never moves focus, so a synthetic press cannot see this)
  leaves `document.activeElement` on the button. Typing then goes to the button:
  revision does not move and nothing reaches the document. Positive control: the
  same dispatch with `sink.focus()` first lands.
* The canvas click a person is **forced** into to get the keyboard back **moves
  the caret**, and the pending format goes with it: type straight after the
  press → bold; click first → not bold. One variable, control arm passes.

`el.sink.focus()` appeared exactly once in the whole page, inside the canvas
`pointerdown` handler. The toolbar's click handler never restored it.

**And nothing automated could have caught it:** every keyboard helper in
`run_e2_c_product_path.py` — `TYPE_KEY`, `DELETE_KEY`, `COMPOSE`, `CUT` — opens
with `sink.focus()`. The harness handed back, on every run, the focus a user
could only recover by clicking. *The line the harness added was the defect.*

**Fixed** (`findings/066-*.md`): a `mousedown` listener on the toolbar,
`preventDefault` plus a focus of the sink, buttons only. Verified:

| | |
|---|---|
| shipped Chrome | `the-toolbar-gives-the-keyboard-back` **PASS**; both browsers `ok: true` |
| shipped Firefox | the check **NOT_ESTABLISHED** — no CDP, no real click, so it says it measured nothing rather than passing |
| `--mutate focus` | reverting the two lines turns **only** that check red |
| coverage | the audit caught `listener:mousedown` as an unaccounted path the moment it was added, and it is now registered |

**Shell identity moved: v25 → v26** (`b25b6c29d1e74012…`). `web/e2-editor-app.js`
is the bundle's entrypoint, so this is a new generation by construction. The
matrix's fifth binding was re-stated in place with a `refreezeLog` entry; **the
artifact did not move** and four of the five hashes are unchanged.

The second half — that a canvas click discards the pending format — is **not
fixed** and 066 does not claim it should be. Users are simply no longer forced
into it.

**A trap sprung twice in two days:** the first placement of the new check ran
before `formatting-survives-the-next-paragraph-break`, left bold ON, and the
page decides `enabled` from its cache — so the next check's "turn it on" sent
`enabled: false` and killed its own precondition. The comment warning about
exactly this was already in the file. Order changed; the reason is in the code.

## 5. What is left

| | |
|---|---|
| **The two-browser confirmation** | **Done.** Both `ok: true`, nothing stale, three inline checks green. The remaining NOT_ESTABLISHEDs are the ones that abstain on purpose (two on Chrome; Firefox adds the two that need CDP for the clipboard). `findings/evidence/064/after-the-fix/` |
| **D0 against the re-frozen matrix** | **Done, `pass: true`, `problems: []` on both browsers**, entry assertion satisfied. Written into `findings/evidence/sdk-e2/e2-c-validation/**d0-shell-v26**/`, deliberately NOT over the 2026-08-21 run: that record is the v25 round and `--overwrite` would discard it. **The namespace question is a decision, not a default** — the tree's convention namespaces D0 evidence by ARTIFACT, and the artifact did not move, so by that convention this belongs in the same directory. Left non-destructive for a human to settle. Check the result before quoting it |
| **`validate_e2_c.py` is hard-coded to round ONE's matrix** | `MATRIX = e2/validation-matrix-v1.json`, no `--matrix` flag, and v1's baseline binds shell bundle **v1** while the tree is on v26 — so its `E2_STOP_OR_RESCOPE` has been standing since bundle v2 and is not about anything done today. It is not a build gate (the Makefile only `py_compile`s it and runs its `--self-test`). Same family as the two other always-red gates below |
| **The link** | Authorised, payload six, **not started**. Nothing gates it now: 064 and 065 both do not exist, so no item 7. §6. Note the shell is v26, not the v25 the previous handoff recorded |
| **067 — a real Enter does nothing, and the revision says it worked** | Filed and measured tonight: revision `1 → 2`, `content.xml` **byte-identical**, typing on both sides of the key works (the control). Two source-readable candidates, both ours: the input adapter turns Enter into `commitText("\n")` instead of dispatching `insert-paragraph-break` (`input/input-adapter.js:248-251`), and `handleInsertText` increments the revision unconditionally (`src/probe_engine.cpp:2730-2755`). **Not fixed, and the reasons are named in the finding** — the adapter is finding 050's neighbourhood, the change is an interface change not a line change, one shell generation was already minted tonight, and the engine half would need a link. **Cheap next step: surface the engine's `method` field**, which already distinguishes `paste` from the `postKeyEvent` fallback and is already returned by the SDK |
| **All four formats on the KEYBOARD path — PASS** | The question the second manual round existed to ask, now automated because 066's fix made it askable: real CDP clicks for every button, typing through `#sink` with nothing restoring focus. bold / italic / underline / strikethrough all land on the typed marker (`span T1`, each with its own property). `findings/evidence/066/after-the-fix/keyboard-formats-all-four.json`. **The shipped inline-format check still drives the insert FIELD, not the keyboard** — this arm lives in the probe, and promoting it into the regression net is open work |
| **068 — the caret is DRAWN in the wrong place** | Filed. The model is right (typing twice gives `CARETONECARETTWO`, contiguous and in order, and the operator's own `r2-caret.odt` is clean), so **editing correctness is unaffected**. The **offset is not measured**: six isolation attempts failed and each failure is written down in the finding — the page borders are full-band-height strokes that differ between reads and swamp a caret a few columns wide; the exact `#1a1a1a` colour signature yields four anti-aliasing pixels; the operator's screenshot is downscaled ~2× so a 2-px caret cannot be separated from letter stems. **Next step is written**: capture the canvas at FULL resolution as an image (CDP `Page.captureScreenshot` clipped to the canvas, or `toDataURL()`) and look for the isolated vertical stroke — stop counting columns |
| **Operator round two, all four parts** | `findings/evidence/operator-2026-08-22-round-2/`. Part 1 (italic/underline/strikethrough by hand) **all correct**, agreeing exactly with the automated `keyboard-formats` arm through the same path. Part 2 sharpens 067: the Enter added no paragraph **and** the text typed after it landed contiguously in the same one. Part 4 **contradicts their 2026-08-21 report** — the line break now works, caret and all; the only change in between is 066's fix and that explanation is **not independently measured** |
| **Three operator observations** | `devlog/DEVLOG-2026-08-22-operator-observations-caret.md`. Two are eyewitness and **unmeasured**: the caret is drawn before the last character rather than after it, and `insert-line-break` does not move the caret to the next line. The third **is** measured, from the operator's own two saves: a **real keyboard Enter changed nothing at all** — the two `content.xml` are byte-identical. All three point at the `#sink` / `beforeinput` path, which the toolbar-button checks do not cover and which `backspace-and-arrows-reach-the-document` covers only for backspace and the arrows. **No finding filed**; the design for measuring each, with positive controls, is in that file |
| **The mutation net** | `save` and `ime` fail on the **HEAD** runner too; `copy` passes on both. Stale declared-collateral bookkeeping, not escaped detection. Evidence and reasoning in `findings/evidence/mutation-net-already-red/`. **Do not widen `alsoRed` to make a round pass** |
| **`cut`** | Unchanged. The `paste("")` probe belongs inside the link work |
| **`blur` / `pointercancel`** | Unchanged. Abstaining on purpose; next step is the copy path's `codePoints` |
| **Recovery's second inducer** | Unchanged. Open and narrowed |
| **a11y gate 0** | Unchanged. Prepared, not run; the rebuild is the user's hours |
| **Nothing is committed** | Still true, and there is now a lot of it |

## 6. The link

The 2026-08-21 gate — "064's mechanism is the only thing that can change the
payload" — is **discharged**, and this time for a reason that survives: there is
no defect to attribute. The payload stays at six.

The intermediate position recorded in the superseded handoff ("attribute 065
first, then link") was correct **given what was believed at the time** and is
now moot, because 065 does not exist.

**Re-confirm with the user before executing anyway.** The authorisation was
given on a factual basis that has now moved twice in two days, and the execution
discipline is unforgiving: archive the profile first, no rebuild between sweep
and verdict, re-state all five bindings and re-run D0 on both browsers
immediately after, land it **before** M2a.

## 7. Do not repeat

* **Do not add machinery to fix a defect you have not confirmed exists.** The
  per-arm saves and the whole 065 apparatus were built on a false reading. They
  survive because they are cheap and harmless, not because they were needed.
* **Do not swap a tracked file to compare two versions.** The HEAD-vs-current
  mutation batch overwrote `tools/run_e2_c_product_path.py` in the working tree
  and made `git diff` meaningless while it ran. Frozen copies in a scratch
  directory cost nothing; `build_mirror` is this tree's own pattern.
* **Verify an edit took effect when anything else writes that file.** Clearing
  `KNOWN_RED` was silently reverted, and the next two-browser run came back red
  for a stale declaration that had supposedly been removed. `assert
  t.count(old) == 1` proves what you wrote, not what runs. Import the module and
  assert the value, print the sha256, and print it again after the run — the
  final confirmation does exactly that.
* **Check `/tmp` before a long browser batch.** It is a 16 GB tmpfs shared with
  other work; it hit 100% mid-run and silently voided three mutation rounds
  (they came back "NOT DETECTED"). `TMPDIR=/home/jiajun/.cache/litecore-probe-tmp`
  is on the real filesystem.
* **When a subagent reviews a finding, it inherits your oracle.** The
  adjudication on round 2 was careful, adversarial, correct on every point it
  could check from disk — and it ratified a finding that was zero, because the
  numbers it was checking came from the same broken function.
