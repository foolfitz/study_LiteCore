# TASK — finding 096: which of v13, v12 and v8 die when an arrow key is pressed at a document boundary?

Pre-registered measurement protocol for
`findings/096-arrow-key-at-a-document-boundary-kills-the-session-with-no-checkpoint.md`.

**Written and committed before any arm of it was run.** Nothing below may be
edited after the first attempt that counts; corrections go in an appended
`## Execution record` section that names what it supersedes (AGENTS.md §10).

**The one question.** The owner, by hand, on candidate profile `e2-editor-v13`,
in a real document longer than the viewport, with no screen reader: arrow to the
first line and press Up again — or to the last line and press Down again — and
the session dies into a notice that says the work since the last save is gone.
**Which of `e2-editor-v13`, `e2-editor-v12` and `e2-editor-v8` do this?**

**The one thing this protocol may not do.** It may not name a cause. It
measures whether a boundary arrow press takes the session into a dead state, on
three engines. *Why* it does is not measured here and must not appear in any
file this task produces. Finding 040's precedent, and 089's two refusals.

**Do not merge 096 with the two other things the owner recorded** — the viewport
not following the caret during ordinary arrow movement, and (with a screen
reader) the caret not following the browse cursor. 096 registers those as
possibly-separate and does not assume one cause. Neither is measured here.

---

## 1. The three arms, and what makes them three rather than two

`repointed_page(source, profile, manifest)` rewrites exactly two things in
`web/e2-editor-app.js`: the one worker URL and the one pinned wasm hash. So all
three arms carry the **same page source** — the current one, which already
contains 093's page half (commit `18eefcce`). Computed before any run:

| arm | page sha256 | probe.wasm | what it is |
| --- | --- | --- | --- |
| **A — v13** | `31787584290e42bd…` | `0fe25650bec1bac5` | the candidate. The owner's exact bytes: this sha256 is the one written into `findings/evidence/manual-round-v13-31787584/notes-owner-T4.md` before the round. |
| **B — v12** | `db2ed393f3433e2e…` | `4ec1e389aaab3b03` | the previous candidate's engine (the a11y core, repackaged), under the same page |
| **C — v8** | `1ec7baf9fb53c808…` | `4a2710bba1ef07d9` | **the shipped bytes.** `sha256(web/e2-editor-app.js) == sha256(dist/e2-editor-app.js) == 1ec7baf9…`, so repointing to v8 reproduces the shipping page byte for byte. |

All three manifests offer `move-line-up` and `move-line-down`, so the page's
`keydown` handler takes the key on all three (`web/e2-editor-app.js:1425-1432`
gates on `session.offers(action)`). **The arms are comparable at the key path.**
Checked before the run; recorded here so that a later reader does not have to
take it on faith.

### 1.1 The correction this table forces to the finding's own wording

Finding 096 §「決定後果的那一題」 describes arm B as 「舊引擎、舊頁面」. That is
**not** what is measured here, and the difference changes what an outcome
licenses. Because all three arms hold the page source constant, this triple
isolates the **engine**, and **cannot** by itself attribute anything to the page
change. Registered as a limitation, not as a result.

### 1.2 Conditional arm D — only if the first three make it necessary

If B and C both reproduce (i.e. "the engine is not the discriminator"), the page
change is still not excluded, because it is in all three arms. **Arm D**: the
page as it was *before* commit `18eefcce` (`git show 18eefcce^:wasm_sdk_probe/web/e2-editor-app.js`),
repointed to the same profile as a reproducing arm. Run it only in that case,
and label it what it is: a page that never shipped.

---

## 2. What each outcome licenses — written before anything runs

Let R(arm) be "reproduced at least once in the registered number of attempts".

| outcome | what it licenses | what it does **not** license |
| --- | --- | --- |
| **R(A) ∧ R(B) ∧ R(C)** | Like finding 086: **present on shipping too, not a candidate regression.** The disposition question becomes "how long has this been here", not "does the cutover carry it". | It does not license "the page is innocent" — the page change is in all three arms. Trigger arm D. |
| **R(A) ∧ ¬R(B) ∧ ¬R(C)** | **The v13 link introduced it**, at data-loss severity, before a cutover. This is the outcome that blocks. | It does not name *which* change in the link. 093 option B is a hypothesis, not a measurement. |
| **R(A) ∧ R(B) ∧ ¬R(C)** | Not the v13 link. Consistent with **either** the shared page change **or** the a11y core (`4ec1e389`), which B and C also differ in. **Two candidates, not one.** | It does not license "the page change did it", which is what finding 096 §「決定後果的那一題」 assumed this cell meant. Trigger arm D to separate them. |
| **¬R(A) ∧ (R(B) ∨ R(C))** | Nothing clean. Register as an instrument result and stop: the harness reproduces on an arm the owner did not test and not on the one they did. | Nothing. |
| **¬R(A) ∧ ¬R(B) ∧ ¬R(C)** — never reproduces at all | **The harness does not reach what the owner reached.** This is a result about the instrument, reported as one. It does **not** license "the owner was wrong" and does **not** license closing 096. See §6. | Nothing about the product. |

**The default conclusion if this task is never run**: 096 stays
「擁有者目擊，尚未重現、尚未區辨」 and the cutover decision is taken without
knowing whether shipping has it. That is the status quo, and it is written here
because AGENTS.md §2 requires every criterion to carry one.

---

## 3. The gesture — the user's path, not the harness's

The owner pressed **real arrow keys**. This tree has paid twice for measuring a
different path than the user's (`harness-path-vs-user-path`; finding 064's
`caret-after-real-typing`). Therefore:

- **Keys go through CDP `Input.dispatchKeyEvent`**, `rawKeyDown` then `keyUp`,
  with `windowsVirtualKeyCode`/`nativeVirtualKeyCode` 38 (Up) / 40 (Down) and
  `key`/`code` `ArrowUp`/`ArrowDown`. Not `new KeyboardEvent(...)`; not
  `session.action("move-line-up")`; not a toolbar button.
- **The caret is placed by a canvas pointerdown**, which is the only thing that
  moves the caret in this page and which focuses `#sink` on the way — one
  gesture, and it is the user's gesture.
- **The document is handed to the product's own `#file` input** via
  `DOM.setFileInputFiles` with a real path on disk. A user's document does not
  arrive from the host that served the page.

### 3.1 The document

`~/Documents/SLAT/e20-專訪瓦特老師.odt`, sha256
`63bf89cb5d7eb8913fd2e691f5d93b0d42d8715ca9ef8c61cd331048831c53d5`. **The
owner's own file, the one they used.** Not a synthetic fixture: 086 is on record
as a defect that a real document exposes and the built fixtures did not.

"Longer than the viewport" is **measured, not assumed**: every attempt records
`#desk`'s `scrollHeight` and `clientHeight` and the attempt is void if
`scrollHeight <= clientHeight`. Viewport fixed at 1920x1080 via
`Emulation.setDeviceMetricsOverride`, so the arms are compared at one geometry.

### 3.2 Reaching the boundary

The canvas is the whole paper, so a click at a y-fraction of the canvas lands at
that fraction of the *document*, not of the screen.

- **Up arm**: find the **first** row of text ink by scanning the top of the
  canvas; click just inside that line's ink (`caret_click_fractions`' `near`);
  then press ArrowUp.
- **Down arm**: find the **last** row of text ink by scanning the bottom;
  click just inside it; then press ArrowDown.
- Rows where dark pixels span more than half the canvas width are the page
  frame, not text, and are excluded — the same discrimination `LINE_INK` makes.

Presses continue until the session dies or a budget of **12** presses is spent,
with **at least 6** of them delivered after the caret has stopped moving.
"Pressed once at the boundary" and "pressed at the boundary and nothing
happened" must not be told apart by luck.

---

## 4. The predicate — the product's decision fields, not its wording

After each press, `#state-pill`'s `dataset.state` and `#notice`'s
`dataset.show` / `dataset.rescue` are read.

- **DIED** — `dataset.state ∈ {"recoverable-error", "restart-required", "expired"}`
  within **90 s** of the press. (`DEAD_STATES` in
  `tools/run_e2_c_product_path.py`; the same three states its own guard uses, so
  the guard and this probe ask one question rather than two that can drift.)
- **REPRODUCED (the owner's variant)** — DIED **and** `#notice` shown **and**
  `dataset.rescue == "none"`. That last field is the product's own decision that
  there is no checkpoint; it was adjudicated on 2026-08-19 as the thing a check
  may assert, precisely because the sentence around it may be rephrased.
- **DIED-WITH-CHECKPOINT** — DIED but `rescue != "none"`. A different, less
  severe shape. Recorded separately; it is **not** a reproduction of 096.

The notice's rendered text is recorded verbatim as well, and compared to the
owner's quote 「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。」
— as evidence, not as the predicate.

---

## 5. Ask the engine, not the page

`#s-latency`, the status ball and the toast are the **page's** observations. On
this tree "the screen shows nothing" has had four indistinguishable causes.
Every attempt therefore captures, and banks **raw**:

1. **Every CDP event on the page target**, verbatim, from before the document is
   opened: `Runtime.consoleAPICalled`, `Runtime.exceptionThrown`,
   `Log.entryAdded`, `Inspector.targetCrashed`, `Target.*`, `Network.*`.
   `ChromeSession.call` discards every message whose id does not match while it
   waits for its own, so this probe overrides `call` to **buffer** them instead.
   That discarding has already cost this tree one wrong conclusion
   (`induce_worker_failure`'s docstring, 2026-08-27).
2. **The document worker's own console and uncaught errors.** The worker cannot
   be found by asking for it (`Target.getTargets` reports empty urls);
   `Target.setAutoAttach` with `flatten: true` is the route that works. On every
   attached worker session, `Runtime.enable` and `Log.enable`, and every event
   carrying that `sessionId` is banked with the session's target url.
3. **Every toast the product raised**, through the `MutationObserver` shim
   `INSTALL` installs — not `#toast.textContent`, which the next message
   overwrites. `run()` renders `${code}：${message}` from the SDK's own error
   object, so the toast carries the engine's **code**, which is the payload.
4. **The state transition trace**: `#state-pill` polled at 150 ms and every
   *change* recorded with a monotonic timestamp, so 「就緒 → 處理中 → 需要回復」
   is a sequence with times rather than a sentence.

**Payloads, not summaries of payloads** (AGENTS.md §7): the raw event objects go
into the JSON. A per-attempt cap of 4000 events guards the file size; when it
trips, the attempt says so.

---

## 6. Repeats, and what a non-reproduction means

**Attempts, fixed here before any of them: 5 per direction per arm** — 5 Up + 5
Down × 3 arms = **30 attempts**. Each attempt gets a **fresh page load**: a dead
session refuses everything, and 093's phase-3 probe measured that after a
down-arrow walk reaches the end of the document every subsequent canvas click
comes back 定位游標 失敗, so an attempt that reuses the page cannot set its own
starting caret.

**Every attempt is reported, not only the ones that reproduced.** Finding 084 is
the precedent: 27 runs dropped 3, and a single run would have given a confident
wrong answer in either direction.

**If an arm reproduces 0/5**, the registered claim is "did not reproduce in 5
attempts under this harness", **not** "does not have the defect".

**If nothing reproduces anywhere**, that is reported plainly as a gap between
the harness's path and the owner's, and the report must say what would close it.
Named in advance, so the answer is not invented afterwards: the differences
between this harness and the owner's hand are (a) headless Chrome versus a
windowed one, (b) CDP-injected key events versus a physical keyboard through the
compositor, (c) the owner had done 3.1–3.6 of the T4 round in the same page
before they walked with the arrows — typing, an 086 failure with a checkpoint
offered, a drag-selection, an undo/redo pair and a save — so **their session had
a history and these attempts do not**. (c) is the cheapest to close and is the
first thing to try; it is registered here as a hypothesis, not run as part of
this protocol.

---

## 7. Constraints on the executor

- **Do not fix anything.** If the cause becomes visible, write it down; do not
  patch it.
- Write **only** (a) files under `findings/evidence/096/`, (b) one appended
  section at the end of finding 096, (c) one appended `## Execution record`
  at the end of this file. Nothing under `web/`, `dist/`, `src/`, `sdk/`,
  `build/archive/`; no check in `run_e2_c_product_path.py` (its clean predicate
  is fixed at 39 PASS / 2 NE and moving it restarts a soak count now at 6).
- Never a bare `make`. Never `build_cutover_page.py --write`.
- **Count Chrome processes before starting and after finishing**, by browser
  main + `crashpad-handler-pid`. The owner has one Chrome and a
  `serve_candidate_page.py` on port 8765; both are theirs. Never `pkill -f` /
  `pgrep -f`; kill nothing you did not start; leave nothing running.
- The probe serves from a **scratch mirror** of `dist/` on a free port obtained
  from the kernel — port 8765 is not assumed free.

---

## Execution record

### 2026-09-09 — shakedown, and three changes it forced (before any counted attempt)

Four shakedown attempts were run on `e2-editor-v13` under `--label shakedown…`
**before any attempt that counts**, and are reported separately from the matrix.
They forced three changes to what §3.2 registered. Each is named with the
measurement that forced it, per AGENTS.md §9; none of them moves a **verdict**
criterion (§4 is untouched).

1. **The ink-row floor.** §3.2 said "rows where dark pixels span more than half
   the canvas width are the page frame". That is necessary and **not
   sufficient**: the paper's left and right borders put a handful of dark
   pixels in *every* row inside the page, so "has any ink" is true of blank
   line spacing too. Shakedown 1 reported the first text row 628 px down a
   3727 px canvas, with a "contiguous run" of 1218 rows, and the up-arm walked
   12 presses without reaching the top. A lower floor of **20 dark pixels** is
   now applied as well (a glyph row measured 162–225; two borders carry a
   handful). Recorded in every attempt as `inkRow.floor`.
2. **The press budget, 12 → 40.** Forced by the same measurement: a budget set
   for "click on the first line" is not a budget for "click near the first
   line". `after_still` stays at 6, and 6 presses at the boundary is still the
   registered minimum.
3. **The worker console was attached to the wrong worker.** Opening a document
   **replaces** the document worker (`Target.detachedFromTarget` at t=9.5 s,
   a new `Target.attachedToTarget` right after), so the session
   `Target.setAutoAttach` delivered at boot is detached by the time the gesture
   runs — shakedown 3's liveness probe came back `Session with given id not
   found`. The attach/detach events are now tracked and the console is enabled
   again after the open. **Without this, §5.2 would have banked the console of
   a worker nobody was using.**

**One instrument was added**, and it is an observation rather than a criterion:
after the wait, one `Runtime.evaluate` is addressed to the live worker's own CDP
session. "The worker's JS thread is blocked" and "the worker is idle and
something behind it never answered" are indistinguishable at the page, and this
tree's standing lesson is that a screen showing nothing has several
indistinguishable causes. Banked as `workerLiveness`; it names no cause.

Shakedown outcomes, reported because §6 says every attempt is reported:
`v13 up` NOT_REPRODUCED (instrument defect 1, void), `v13 up` REPRODUCED,
`v13 down` REPRODUCED, `v13 up` REPRODUCED. **None of these four counts toward
the matrix**; the matrix was run afterwards, from zero, with the instrument
above.

### 2026-09-09 — the matrix, and arm D

Run to completion. **40 attempts, 40 REPRODUCED**, no other outcome and no void
attempt. Full result: `findings/evidence/096/RESULT.md`; raw per-attempt
evidence in the four `findings/evidence/096/boundary-arrow-*.json`.

| arm | up | down |
| --- | --- | --- |
| A — `e2-editor-v13` | 5/5 | 5/5 |
| B — `e2-editor-v12` | 5/5 | 5/5 |
| C — `e2-editor-v8` (shipped bytes) | 5/5 | 5/5 |
| D — pre-`18eefcce` page on `e2-editor-v8` | 5/5 | 5/5 |

**The verdict cell is §2's `R(A) ∧ R(B) ∧ R(C)`**, read back rather than
composed: like finding 086, present on shipping too, **not a candidate
regression**. §2 also required arm D in this cell, because the page change is in
all three arms; arm D was run on the shipping engine with the page as it stood
before 093's page half, and it reproduces 10/10 — so **the page change is not
necessary either**.

The engine-side payload is the same in all four arms: `ready → busy` on the
boundary press, then `recoverable-error` **30002–30003 ms later**, with
`TIMEOUT：editorActionV2 timed out after 30000 ms` from the SDK's own error
object; no crash, no exception anywhere, an empty worker console at the moment
of the press, and the worker's JS thread answering a CDP evaluate in 0.0 s
afterwards. **No cause is named**, per this protocol's second paragraph.

**§6's non-reproduction clause did not apply**: the harness reproduced the
owner's sentence character for character (`noticeMatchesOwnerQuote: true` in
every attempt), so the three named gaps between this harness and the owner's
hand were not load-bearing here. Gap (c) — that the owner's session had a
history and these have none — turned out to be unnecessary rather than
untested: the defect fires on a document with `revision: 0`.

**One arm was added that §1.2 had registered as conditional, and nothing else
moved.** No criterion in §4 was edited; §6's attempt count was met exactly.
