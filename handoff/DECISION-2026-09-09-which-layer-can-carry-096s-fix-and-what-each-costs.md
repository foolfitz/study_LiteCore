# Where finding 096's fix can live, and what each layer costs

**Purpose.** The owner ruled on 2026-09-09 that 096 is fixed **now** — not for the
cutover, but because it is a zero-cost data-loss defect on the product that ships
today. The finding's own closing paragraph says the next step is not to land a fix
but to find out **which layer it has to live in, and therefore what it costs in
identity**. This is that answer.

**Status of this document.** Static reading of the tree plus the banked 096
evidence. **Nothing was built, linked, repackaged or edited.** No cause is named
beyond what is cited, and §2 says plainly where the trace stops being measurement
and becomes code reading.

**What is already measured and is not re-opened here**:
`findings/096-arrow-key-at-a-document-boundary-kills-the-session-with-no-checkpoint.md`
and `findings/evidence/096/RESULT.md` — four arms, 40/40, including the shipping
bytes; `ready → busy` on the boundary press and `recoverable-error` 30002–30003 ms
later; `TIMEOUT：editorActionV2 timed out after 30000 ms`; nothing crashed; the
worker's JS thread answered a CDP evaluate in 0.0 s afterwards.

---

# 1. The one-page answer: options against what dies

The gate's counting judge is `wasm_sdk_probe/tools/check_soak_bank.py`. Every one
of the six banked runs is judged on nine clauses (`:305-333`), of which four are
byte identities:

* `page-sha` — `candidateCutover.pageSha256 == 31787584290e42bd…`
* `one-served-shell` — `servedShell.servedSha256 == ea69984c8ad25c40…`, the digest
  of **thirteen** files (`wasm_sdk_probe/e2/editor-shell-v2-bundle-v49.json`)
* `reconciled-profile` — `e2-editor-v13`
* `pass-count` + `ne-set-exact` — 39 PASS and exactly two named NE

The thirteen bound files are the four `editor-shell-v2/`, four `editor-shell/`,
two `input/`, `reader-shell/tile-scheduler.js`, `sdk/document-sdk.js`, and
`web/e2-editor-app.js` as the entrypoint. **`sdk/sdk-worker.js` is not among
them**, and neither is `web/e2-editor.html`.

| # | layer a fix could live in | moves `pageSha256`? | moves served-shell digest? | needs a relink? | needs a profile repackage? | what dies |
|---|---|---|---|---|---|---|
| **A** | **engine** — `wasm_sdk_probe/src/probe_engine.cpp` | **yes** (the pin is substituted from `wasmSha256`) | **yes** (the entrypoint is one of the thirteen) | **yes** — `Makefile:1679`, `ALLOW_FROZEN_RELINK=1`, run by the owner | yes | **everything bound to `31787584…` / `0fe25650…`**: all 6 soak runs, 4a's 8/8, condition 2's three diagnostics, the ODT round trip, the revert rehearsal, and the T4 manual round that was taken on this page. A new candidate identity (v14) and the horizon restarts from zero. |
| **B** | **worker** — `wasm_sdk_probe/sdk/sdk-worker.js` | no | no | **no** | **yes** — it is a prerequisite of the manifest (`Makefile:1723`, passed at `:1731`); only `workerSha256` and the manifest bytes move | **no gate clause goes red at all.** That is not a saving, it is the hazard — see §1.1. |
| **C** | **shell** — `editor-shell-v2/narrow-editor-v2-session.js` (or any of the other twelve bundle files) | no | **yes** | no | no | all 6 soak runs (`one-served-shell`), plus `differsOnlyInTheEntrypoint` stops being true, so the candidate-run legitimacy rule needs a new frozen generation (v50) and `DEFAULT_SERVED_SHELL` must move. 4a and condition 2 keep their page identity but were run on a shell that no longer exists. |
| **D** | **page** — `web/e2-editor-app.js` | **yes** | **yes** (it *is* the entrypoint) | no | no | all 6 soak runs twice over (`page-sha` **and** `one-served-shell`), 4a term `1-identity`, condition 2's page pin, and the T4 round. Same evidence loss as A, without the relink and without a new wasm. |
| **E** | **manifest only** — withhold `move-line-*` gestures (repackage, no code change anywhere) | no | no | no | **yes** | no *identity* clause moves, but `the-vertical-arrows-move-the-caret` turns from PASS to NOT_ESTABLISHED by its own registered branch (`tools/run_e2_c_product_path.py:7306-7315`), so `pass-count` (39→38) and `ne-set-exact` both fail: **all 6 soak runs die on composition.** |
| **F** | **page HTML** — `web/e2-editor.html` | no | no | no | no | nothing goes red — finding 094. There is also nothing here that can fix 096; the row exists only to answer the question. |

**Cross-cutting, and it applies to A–E alike.** If the fix comes with a regression
check in `tools/run_e2_c_product_path.py` — and on this tree a fix without one is
the thing §5 of AGENTS.md was written about — the composition moves from 39 PASS /
2 NE, `pass-count` fails, and **all six runs die regardless of which layer the fix
lived in**. Adding a criterion mid-flight is permitted by AGENTS.md §9 but only
with its four conditions, and the 2026-09-08 forty-first check is the worked
precedent (`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md:1976-2079`).

## 1.1 The trap in row B, stated before anyone reaches for it

`sdk/sdk-worker.js` is deliberately excluded from the shell bundle
(`tools/build_e2_c_shell_bundle.py`, the exclusion carries the reason "bound
separately and more precisely as `workerSha256`"). Its only binding is
`editorContract.workerSha256` inside each **packaged profile's** manifest, and no
soak clause reads that field.

So a worker fix, repackaged into `dist/profiles/e2-editor-v13/` with the same
`probe.wasm`, moves `workerSha256` and the manifest bytes and **nothing else**:
the wasm hash is unchanged, so the page's `PINNED_WASM_SHA256` is unchanged, so
`pageSha256` is unchanged, so `servedSha256` is unchanged, and the profile is
still called `e2-editor-v13`. All nine clauses still pass. **The six banked runs
would go on being judged clean while describing a worker that no longer exists.**

That is finding 094's shape one layer out, and it must be adjudicated the same
way 094 was: *no check goes red* is not *nothing changed*. If row B is chosen, the
count should be zeroed by adjudication, or the profile given a new name (which
then moves the page's worker URL, and B collapses into D).

## 1.2 The other thing the table cannot show

The product that ships today is `e2-editor-v8`; the candidate is `e2-editor-v13`;
096 is 40/40 on both. But there is only **one** `web/e2-editor-app.js`, and the
cutover page is that file with two lines substituted
(`tools/run_e2_c_product_path.py:415-440`). **A fix that reaches the shipping
product through the page or the shell is the same edit that moves the candidate's
page sha256.** There is no version of "fix v8 only and leave the candidate's
evidence alone" in rows C or D.

---

# 2. Where the request stops being answered

Every hop below is cited. The last hop — the one inside core — is **not measured**,
and §2.3 says what would measure it.

## 2.1 The trace, hop by hop

1. **Key.** `web/e2-editor-app.js:1322-1329` maps `ArrowUp → move-line-up`,
   `ArrowDown → move-line-down`. The `keydown` listener on `#sink` is at `:1331`;
   at `:1426-1433` it gates on `session.offers(action)`, calls `preventDefault()`
   and dispatches `editorAction(action)`.
2. **Page dispatch.** `web/e2-editor-app.js:986-997` → `run(label, () =>
   session.action(action, options))`; `run` is at `:890-897`. The toast text the
   evidence banked is composed at `:901-903`.
3. **Shell session.** `editor-shell-v2/narrow-editor-v2-session.js:275-317` —
   `action()` puts the call on the FIFO with `{ mutation: true }`.
4. **The queue.** `editor-shell/editor-session.js:250` `_enqueue` (this is the
   `pending` counter the evidence watched climb 1→6), `:279-330` `_drain` — one
   item in flight at a time. **Presses 3–7 never reached the worker**; they sat in
   `this._queue`. That is why the six toasts are identical and arrive together.
5. **v2 client.** `editor-shell-v2/narrow-editor-v2-client.js:266-308`; the wire
   call is `:299-305`, `_engine._request("editorActionV2", …)`.
6. **SDK.** `sdk/document-sdk.js:152-210`. The deadline is `_defaultTimeoutMs`
   (`:88`), which the page sets to 30000 at `web/e2-editor-app.js:1562-1566`. The
   timer is armed at `:187` and rejects with `SdkTimeoutError` (`:14-19`) —
   verbatim the string in the evidence.
7. **Worker.** `sdk/sdk-worker.js:1365-1409`: argument validation, then
   `manifestAllowsAction` (`:110-130`), then `accept(request, () =>
   callStatus("oxsdk_editor_action", …))`. `accept` is at `:487-508`: **status 0
   means "queued in the engine", and no response is posted.** The reply, if it
   ever comes, comes later from the engine's event pump.
8. **Engine entry.** `src/editor_api.cpp:152-166` → `probe::editorAction`
   (`src/probe_engine.cpp:6082-6096`), which pushes a `CommandType::EditorAction`
   onto the engine's command queue.
9. **Engine loop.** The shipped and candidate profiles are built **without**
   `OXSDK_MAINLOOP_ENGINE` (`Makefile:1649-1657` for v13; `-DOXSDK_MAINLOOP_ENGINE`
   appears only in the attribution profiles at `Makefile:782-790`), so the loop is
   `engineLoop` at `src/probe_engine.cpp:5368+`. It pops the command and calls
   `handleEditorAction` (`:4607`).
10. **Dispatch.** `handleEditorAction` refuses with `BUSY` if a callback-correlated
    operation is already in flight (`:4624-4628`), applies the gesture gate
    (`:4700-4712`), and for `move-line-*` reaches the key path at `:4820-4890`:

    * `gEditorPending` is armed with
      `requiredCallback = EditorCaretOrSelectionCallback` (`:4878-4880`; the
      constant is `-2` at `:975`, meaning *either* `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`
      *or* `LOK_CALLBACK_TEXT_SELECTION`);
    * `markAsynchronous(command.requestId)` (`:4885`);
    * two `postKeyEvent` calls, KEYINPUT then KEYUP (`:4886-4889`).

    Then `handleEditorAction` returns. **The request is now owed a broadcast.**
11. **The only way out.** `completePendingEditorOperation`
    (`src/probe_engine.cpp:2062-2127`) is the sole function that clears
    `gEditorPending` for this shape and emits `editor-action-completed` with
    `completion: "documented-callback-…"`. It runs **only** from a matching LOK
    callback. Nothing else on this path ever answers.

**So: the request stops being answered at step 11.** The command was dispatched,
the key was posted, and the engine is waiting for a callback that did not arrive
within 30 s. This is consistent with every number in the evidence — no crash, an
empty worker console, the worker's JS thread answering in 0.0 s, `revision` fixed
at 0, and the queue filling above.

## 2.2 There is no deadline on this path, and the tree already knows the shape

The engine has a bounded-completion mechanism for exactly this failure. Its
declaration carries its own diagnosis — `src/probe_engine.cpp:397-405`:

> SPEC E1-D. A range that selects nothing when nothing was selected before
> changes no state, so core emits no `LOK_CALLBACK_TEXT_SELECTION` and **waiting
> for one wedges the operation for good** — the finding 018 shape.

`readbackDeadlineArmed` is armed by `handleEditorSelect` (`:4941-4944`) and
**always** armed by `handleEditorPlaceCaret` (`:5069-5073`, 250 ms, with the
comment "the case it covers — a click that changes nothing — is not an edge here;
it is the one a user reaches by clicking twice in the same place"). It is honoured
by `engineLoop` at `:5380-5400`.

`handleEditorAction`'s key path arms **nothing**. A boundary arrow press is
precisely "a gesture that changes no state", and it is the one gesture of the
three that has no deadline.

Two consequences follow from the same reading, both citable:

* **The wedge is permanent for the life of the worker.** The SDK posts a cancel on
  timeout (`sdk/document-sdk.js:171-183`); the worker forwards it
  (`sdk/sdk-worker.js:1556-1568`); the engine refuses it, because
  `probe::cancel` returns `NotCancellable` for anything in `asynchronousRequests`
  (`src/probe_engine.cpp:6198-6209`). `gEditorPending` therefore stays set, and
  every later `editorActionV2` (`:4624`) **and every later caret placement**
  (`:5053-5057`) answers `BUSY`.
* **Nothing above the engine can un-wedge it.** That is why the session's only
  honest disposition is a fresh worker — which is what the manifests declare and
  nothing enforces (§3).

## 2.3 What is NOT determined, and the cheapest measurement that would settle it

Step 11 says *where* the answer must come from. It does not say **why it does not
come**, and three explanations are still open and are not distinguishable from the
banked evidence:

1. core moved nothing at a boundary and therefore broadcast nothing (the E1-D
   comment's own reasoning, applied to the cursor callback);
2. core broadcast something that `completePendingEditorOperation`'s match test
   (`:2062-2075`) rejected;
3. the engine thread or core's own loop is not running the work at all.

**Do not build a fix on a guess between these.** They lead to different fixes: (1)
wants a bounded completion, (2) wants a corrected correlation, (3) wants neither.

**Cheapest measurement — no rebuild, no relink, no product byte moves.** Extend
`findings/evidence/096/probe_096_boundary_arrow.py`, which already attaches a CDP
session to the live document worker (the attach route is documented in the task
file's execution record). After the verdict, in the **worker's own realm**, wrap
`self.postMessage`, then hand the worker's own message handler two synthetic
requests with request ids the SDK will never use:

* `editorGetStateV2` — it is dispatched by `handleEditorGetState`
  (`src/probe_engine.cpp:5083-5104`), which answers synchronously and does **not**
  touch `gEditorPending`. If it answers, the engine thread is draining commands and
  core's synchronous read path is alive; and its `sourceSequence` says whether core
  broadcast anything at all since the press.
* a second `editorActionV2` — the positive control. If it comes back
  `BUSY: another callback-correlated editor operation is in flight`
  (`src/probe_engine.cpp:4626`), the command queue is provably being drained and
  explanation (3) is excluded.

Outcomes and what each licenses:

| answer | what it licenses |
|---|---|
| both answer, `sourceSequence` unchanged | core broadcast nothing. Explanation (1). The fix has to supply a completion the callback cannot; that is an **engine** fix or a capability withdrawal. |
| both answer, `sourceSequence` advanced | a callback arrived and did not complete the request. Explanation (2) — an engine correlation defect, and a much smaller one. |
| neither answers | explanation (3). Everything above is wrong and the trace has to start again at the engine thread. |

**Second measurement, if the first is inconclusive** — and it is worth naming
because it is browser-free: `native-lok-26-8/` is a built tree, and
`wasm_sdk_probe/tools/f059_native_*.cpp` are existing harnesses that post key
events and log callbacks. Asking native LOK "which callbacks does ArrowUp emit at
the first line of a Writer document" answers the same question in the reference
implementation. It needs a compile against the native instdir, which is why it is
second and not first.

## 2.4 The ancestor: finding 018

`findings/018-lok-line-navigation-completion-nondeterministic.md` is 096's
ancestor and it is already attributed (2026-08-06). It measured **these same four
actions** timing out at 30 s with no attributable callback, `gEditorPending`
wedged afterwards, everything subsequent `BUSY` — and its attribution section
names the discriminator directly:

> 差別在引擎等哪一個 callback。`extendSelection` 為真時 `requiredCallback` 是
> `LOK_CALLBACK_TEXT_SELECTION`，那個訊號不需要活迴圈就會到；為假時是
> `EditorCaretOrSelectionCallback`（visible cursor），**End 的那一個在沒有活迴圈時
> 不會在 30 秒內送達**。

Its disposition was `CONFIRMED_CAPABILITY_REDUCTION`, **maintained**: line
navigation was not to be promoted to a product capability, "產品路徑用的是
collapsed caret（非 Shift），而那正是不可靠的那一半".

It was promoted anyway, in the ABI 4 relink, as wire ids 16–21. And the manifests
of v8, v12 and v13 declare those actions with
`limits: ["no-extend-selection"]` — so **the one variant 018 measured as reliable
(36/36, zero timeouts) is forbidden on the product path by the manifest's own
limit**, and the product runs only the half 018 named.

Two cautions, because this is attractive enough to be dangerous:

* 018's non-arrival was **intermittent and position-specific** (first `End`, 14 of
  18 rounds); 096's is **40/40 deterministic at a document boundary**. Same
  mechanism family, different signature. They are not the same measurement and
  must not be written as one.
* 018 did not test Up/Down (its own "待驗證" says so), and 096 did not test
  Home/End. Whether all four are affected is **unmeasured in both directions**.

---

# 3. `boundaryRejectionRequiresFreshWorker` — a declaration nothing enforces

**What declares it.** A hard-coded constant in the profile builder:
`wasm_sdk_probe/tools/build_e2_b_profile.py:155`,
`"boundaryRejectionRequiresFreshWorker": True`, written into
`editorContract` — verified present in all three shipping/candidate manifests
(`dist/profiles/e2-editor-{v8,v12,v13}/sdk-manifest.json`).

**What reads it.** On the product path, **nothing**. Zero occurrences in
`web/e2-editor-app.js`, all four `editor-shell-v2/*.js`, all `editor-shell/*.js`,
`sdk/document-sdk.js` and `sdk/sdk-worker.js`.

The only two readers in the tree are diagnostic pages —
`web/e1-discovery-app.js:362` and `web/finding-016-selection-barrier-app.js:445` —
and both read `manifest.diagnostic.boundaryRejectionRequiresFreshWorker`. The
product profiles have no `diagnostic` block at all: `build_e2_b_profile.py:138`
does `manifest.pop("diagnostic", None)` before writing the contract. **So even the
two readers that exist are reading a key path these manifests do not have.**

The remaining occurrences are the other builders and their mirror tests
(`tests/test_e1_b_profile.py:44`, `tests/test_e1_discovery_profile.py:44`) — form 3
by AGENTS.md §1, a hand enumeration asserting the builder's own constant. Push a
fictional new member into the truth source and no check turns red.

**This is a finding in its own right, and it is worse than "unenforced".** The
product's measured behaviour at a boundary is not a rejection at all. A rejection
would be a typed error arriving promptly; what happens is a request that never
answers, a 30-second deadline, a session that dies with no checkpoint, and an
engine slot that no cancel can clear (§2.2). The manifest says the boundary case is
*handled, expensively*. Forty measured attempts say it is *unhandled*. Registering
it here rather than opening a numbered finding, because the owner may prefer it as
an appendix to 096 — but it should not stay only in this document.

---

# 4. The shapes, layer by layer

Read this with §1's table beside it. The important axis is not cost: it is
**which half of the defect each shape actually removes.** There are two halves and
they are separable:

* **the hang** — the press is never answered; the engine slot wedges permanently;
* **the loss** — when the session dies there is no checkpoint, so everything since
  the last save is gone.

`_checkpointBeforeSelection` (`editor-shell/editor-session.js:472-503`) runs
**only** before a range selection, and only when `dirty`. No checkpoint is ever
taken before a caret move. That is why `data-rescue` reads `"none"`: the product's
protection is attached to the wrong gesture, not missing.

## A — engine (`src/probe_engine.cpp`)

**Shape.** Give the key/move path the bounded completion the select and
place-caret paths already have: arm `readbackDeadlineArmed` in
`handleEditorAction`'s key branch, and on expiry answer from a readback of where
the caret actually is, under its own completion name — the same discipline as
`completePendingEditorSelectByReadback` (`:2139-2168`), which "does not turn a
timeout into a success".

**Fixes.** The hang, and only this layer can: **A is the only option in which the
boundary press is answered.** It also clears `gEditorPending`, so the session stays
usable afterwards — the difference between a 30-second stall and a dead editor.

**Does not fix.** The loss, on its own. If the deadline is short the user gets a
fast honest answer; if there was unsaved work and something else later kills the
session, there is still no checkpoint.

**Two things that must be decided with it, not after it.**
`narrow-editor-v2-client.js:239-247` requires every move action's `completion` to
start with `documented-callback-`; a new completion name fails that postcondition
with `EDITOR_RESULT_INVALID`, which is in `RECOVERY_ERRORS` — so the session dies
anyway, 30 s earlier. The client is a **bundle file**, so widening it drags row C's
cost in alongside A's. Separately, `mainLoopDrainCommands` (`:5572-5612`)
synthesises deadline steps for the selection and format barriers but **not** for
`readbackDeadlineArmed`; the attribution profiles would keep the defect unless the
same change is made there.

## B — worker (`sdk/sdk-worker.js`)

**Shape.** Arm a timer when a callback-correlated editor action is accepted
(`:487-508`) and, on expiry, answer with a typed refusal instead of silence.

**Fixes.** The *latency* and the *wording*. The user learns in 2 s instead of 30 s.

**Does not fix.** The hang. `gEditorPending` is still set and no cancel can clear
it (§2.2), so every subsequent action and every caret placement answers `BUSY`.
Unless the worker also tears itself down and is replaced — which is exactly
`boundaryRejectionRequiresFreshWorker`, and the shell already has that machinery
(`_openFresh`, `editor-shell/editor-session.js:146-201`, capped at three
generations by `_maxWorkerGenerations` at `:81`) — B leaves an editor that is alive
and useless, which is arguably worse than one that dies loudly. And it does not
fix the loss.

## C — shell (`editor-shell-v2/`, and the twelve other bundle files)

`editor-shell/editor-session.js` is hash-registered by E1-C and must not be
edited; `editor-shell-v2/` exists precisely to hold changes that would otherwise
go there (the file's own header says so, and `narrow-editor-v2-session.js:288-296`
and `:383-393` are two worked precedents for doing it by subclass).

Three distinct shapes, with different verdicts:

* **C1 — take a checkpoint before a boundary-capable gesture.** This is the shape
  that removes the **loss**, and it is the only cheap one that does. The precedent
  is already in the tree: `selectRange` bounds its own timeout because "the broken
  engine path never returns" (`editor-shell/editor-session.js:456-462`) and
  checkpoints ahead of the gesture. Does not touch the hang: the user still waits
  30 s, but 「回到檢查點」 becomes true instead of 「重新開啟」.
* **C2 — a shorter timeout for the four line moves.** `options.timeoutMs` already
  flows through to `_request`. Turns 30 s of 「處理中」 into 2 s. **The session
  still dies** — `TIMEOUT` is in `RECOVERY_ERRORS`
  (`editor-shell/editor-session.js:15-22`) and `_blockQueue` (`:342-351`) rejects
  every queued item with the same error. Cosmetic on its own.
* **C3 — do not let a move TIMEOUT block the queue.** Mechanically easy (the
  `DISPATCHED_UNVERIFIED` sentinel at `narrow-editor-v2-session.js:283-311` is the
  pattern). **Do not do this alone**: the engine is wedged, so the queue would stay
  open onto an engine that refuses everything, and the product would report
  nothing at all. That is the failure 095 has the shape of.

C1 + C2 together is the best that can be had without touching the engine: fails
fast, loses nothing, still cannot move the caret afterwards.

## D — page (`web/e2-editor-app.js`)

Every knob in C is also reachable here (the page owns `timeoutMs: 30000` at
`:1562-1566`, the notice text, and whether the key is taken at all at
`:1426-1433`). One shape is unique to the page: **stop taking the key when the
caret is at the document edge**. Reject it unless it is measured: the page would
have to infer "the caret is on the first line of the document" from state that the
action itself changes, which is exactly the fingerprint error finding 086 was, and
093 corrected once already. The page has no boundary knowledge the engine has not
given it.

D costs more than C (it moves `pageSha256` **and** the served digest) and fixes no
more. If the fix is going to move the page anyway, it should be because the fix
belongs there, not because the page is where it is easiest to type.

## E — manifest only: withdraw the capability

**Shape.** Repackage the profile with `gestures: []` for `move-line-up`,
`move-line-down` and — since 018's measured failures were on `End` — probably
`move-line-home` and `move-line-end` too. **Withheld is not absent**: present with
an empty gesture list is the withholding spelling, and omitting an action grants it
(`sdk/sdk-worker.js:118-129`, and the same rule in
`narrow-editor-v2-client.js:165-172`). No source file changes in any layer.

**Fixes.** Both halves, completely, by removing the gesture. The refusal is
enforced three times over — the page never takes the key
(`web/e2-editor-app.js:1431`), the worker refuses with `UNSUPPORTED_OPERATION`
(`:1395-1402`), and the engine's gesture mask refuses it
(`src/probe_engine.cpp:4700-4712`).

**Costs.** The editor loses vertical arrow-key navigation — a capability the
product path has a check for, and a real usability regression on a product whose
short-term goal is 「能用的編輯器」. It is also the disposition finding 018 wrote
and the ABI 4 relink overrode, so choosing it is an admission as well as a fix.
And per §1 it kills the six runs on composition, not on identity.

## F — `web/e2-editor.html`

Finding 094 applies exactly: this file is hashed by nothing, and an edit here
moves no pin and turns no check red. It is also **not** where 096 lives — there is
no CSS or DOM shape that answers an unanswered worker request. Row F is in the
table only so that nobody reaches for the unbound file because it is unbound.

---

# 5. What I would do next, and what I am not deciding

**Not deciding**: which row. The choice trades a product capability, an engine
identity and six banked runs against each other, and AGENTS.md §8 puts that with
the adjudicator, not the drafter.

**What the tree's own rules say about the order**, and this part I will state:

1. **Measure before choosing.** §2.3's probe costs one file under
   `findings/evidence/096/`, moves no product byte, needs no build, and separates
   three explanations that lead to three different fixes. Row A is both the most
   expensive option and the only one that answers the press; buying it on a guess
   is the 040 mistake with a bigger invoice.
2. **The two halves have different prices, and the loss is the cheaper one.** The
   owner's ruling was about data loss. C1 — a checkpoint before the gesture —
   removes the loss without knowing the cause, without an engine change, and
   without a relink. It costs the six runs (served-shell digest) and nothing else.
   The hang would remain, and would remain honest: 30 seconds, then 「回到檢查點」.
3. **Whatever is chosen, the count is probably going anyway.** Only rows B and F
   leave all nine clauses standing, F cannot carry a fix, and B's silence is the
   §1.1 hazard. Every other row kills the six. That is worth knowing *before* the
   choice rather than as a discovered cost afterwards: the horizon is 6 of 12 with
   ≥3 UTC days still owed and all six runs banked on a single UTC day
   (`day-spread: false`), so what is at risk is six runs and one day, not the whole
   twelve.

**Two things this document deliberately did not merge.** Finding 095 (after
ArrowDown at the last line, the next canvas click places no caret: `#s-latency`
blank for 25 s, no error, no toast) has a shape the §2.1 trace predicts — a click
enqueued behind a wedged move, in a page whose probe waited 25 s against a 30 s
deadline. **That is a hypothesis, not a result.** Its discriminator is one
character wide: re-run 095's probe with a wait longer than 30 s and see whether the
TIMEOUT toast appears. Likewise 096's own 「畫面沒有跟著」 note stays where the
finding put it.

---

## Appendix — the numbers this document leans on

| thing | value | where |
|---|---|---|
| candidate page sha256 | `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a` | `check_soak_bank.py:111`; every banked run's `candidateCutover.pageSha256` |
| served shell digest | `ea69984c8ad25c4048de0313a49f3db9e7c4ab3fc6ded0f4cebc84a1a5b0fe52` | `check_soak_bank.py:303` |
| shell bundle generation | v49, `4f8494b6b25736c6…`, 13 files | `e2/editor-shell-v2-bundle-v49.json` |
| clean composition | 39 PASS / 2 NE, NE set exact | `check_soak_bank.py:114-116` |
| candidate profile / wasm | `e2-editor-v13` / `0fe25650bec1bac5` | manifest, and the banked runs' `pinAfter` |
| shipping profile / wasm | `e2-editor-v8` / `4a2710bba1ef07d9` | `web/e2-editor-app.js:49`, `:1564` |
| soak count | 6 of 12, runs 09–14, all UTC 2026-09-09 | `findings/evidence/queue-v12-cutover-soak/` |
| relink guard | `refuse_unasked_relink`, `ALLOW_FROZEN_RELINK=1` | `Makefile:880-890`, invoked at `:1679` |
| the SDK deadline | 30000 ms, set by the page | `sdk/document-sdk.js:88`, `web/e2-editor-app.js:1565` |
| the place-caret deadline that exists | 250 ms, always armed | `src/probe_engine.cpp:416`, `:5069-5073` |
| the move deadline | **none** | `src/probe_engine.cpp:4874-4889` arms no deadline |
