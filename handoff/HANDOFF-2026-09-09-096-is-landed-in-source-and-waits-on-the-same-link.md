# 096's fix is landed in source; both halves wait on one owner-run link

Written 2026-09-09. **No link, no wasm, nothing written under `dist/profiles/**`** —
measured, not asserted: the sha256 of all 334 files under `dist/profiles` and
`build/e2` is identical before and after this round.

Read `findings/096-*.md` from the section titled 「修法落地」 for the record with
its numbers. This file is the shorter thing: what is in the tree, what is
measured, what is not, and what the next agent must not conclude.

## What landed

The owner ruled **A + C, both, together**
(`handoff/DECISION-2026-09-09-which-layer-can-carry-096s-fix-and-what-each-costs.md`).

**A — engine, `src/probe_engine.cpp`.** The key path in `handleEditorAction`
now arms `readbackDeadlineArmed`, in the shape its two siblings use. On expiry
`completePendingEditorActionByReadback()` answers from a readback of where the
caret actually is, under the completion name `verified-move-readback`, with
`changed: false` and the revision unmoved. Three edits carry it: a third
`CommandType` (`EditorActionReadback`), a three-way choice in `engineLoop`'s
deadline wake-up, and a dispatch arm with the same requestId/handle correlation
guard the other two have.

**C — shell, `editor-shell-v2/`, generation v51.**
`NarrowEditorV2Session.action()` calls `_checkpointBeforeBoundaryMove()` before
any of the six key-path moves, reusing the base class's
`_checkpointBeforeSelection` rather than copying it.
`narrow-editor-v2-client.js` accepts `verified-move-readback` as a movement
completion.

**The regression net gains a forty-second check**,
`a-boundary-arrow-press-does-not-cost-the-work`, with one `MUTATIONS` entry
(`boundary-move-takes-no-checkpoint`). Its admission is registered against
AGENTS.md §9's four conditions in
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, written before the code.
Clean composition moves **39 PASS / 2 NE → 40 / 2**;
`tools/check_soak_bank.py` is deliberately NOT moved yet, for the reason the
forty-first check's amendment gives.

## Four things the next agent needs and would otherwise have to rediscover

**1. The client widening is not tidying, it is half the fix.** Without it the
engine change makes the product *worse*: the boundary press is answered in
250 ms, `_validateInherited` rejects the completion as `EDITOR_RESULT_INVALID`,
that code is in `RECOVERY_ERRORS`, and the session dies 29.75 seconds earlier
than it does today. If anyone is tempted to "simplify" the two accepted
completions back to a prefix test, that is what it costs.

**2. `editor-shell/editor-client.js` cannot be widened and it does not need to
be today.** It is hash-registered by E1-C. A v1 profile relinked in the future
would meet `verified-move-readback` on a boundary character move and reject it.
No v1 artifact moves for this change. This is recorded in the engine comment
beside the arming, not only here.

**3. The 250 ms is the siblings' number with its own arithmetic.** The sibling
deadlines are 250 because that is an order of magnitude above the 22-28 ms a
click takes (finding 048). What this one bounds was measured on this path:
37-39 ms, 20/20, two engines. 250 is 6.4x that, not 10x, and the code says so.
**Nobody has measured this path under load**, and that is the first thing to
measure after the link.

**4. `mainLoopDrainCommands` was deliberately not touched.** The attribution
profiles keep pure callback semantics — the rule `EditorPendingOperation`'s own
comment already states for the select deadline, and the one finding 018's
attribution turns on. Default conclusion if never revisited: an attribution
profile relinked later still wedges at a boundary, on purpose.

## What is measured, and on what

**C, on the shipping bytes** (`findings/evidence/096/checkpoint-before-the-gesture.json`,
two arms differing in exactly the two lines that constitute half C, judged on
`content.xml` of what the product's own save button produced after its own
recovery button was pressed):

| arm | outcome | `data-rescue` | `#s-checkpoint` | the typed text came back |
| --- | --- | --- | --- | --- |
| `without` | **WORK_LOST** 3/3 | `none` | `無` | **no** |
| `with` | **RECOVERED** 3/3 | `checkpoint` | `有（r1）` | **yes** |

The `without` arm reproduces the owner's sentence character for character.

**Unit level**, red before green: removing the client widening turns the
v1/v2 comparison matrix red on a declared divergence; removing the two session
lines turns four tests red (30 pass → 26 pass, 4 fail).

**The engine TU compiles** with the v13 flags (1.95 s, zero warnings), output
to scratch — nothing under `build/` or `dist/`. Also compiled with the shipping
v8 flags and with `-DOXSDK_MAINLOOP_ENGINE`. Two define combinations
(`-UOXSDK_EDITOR_DISCOVERY`, and the scheduler probe) **already failed on HEAD's
file** — 14 and 6 errors, verified against the pristine source, unrelated.

## What is NOT measured and must not be reported as if it were

* **A's effect. There is no artifact in this tree that carries the move-path
  deadline.** In every one of the six red-case attempts,
  `boundaryPressAnsweredSeconds` is `null`: both arms still wedge and still
  spend the SDK's 30 seconds. C removes the loss, not the hang.
* **Clause B2 of the new check** — that an *answered* press leaves the session
  usable at the revision it started from — is a per-instance property over the
  presses that get answered, and that set is empty today. The check reports
  `clausesExercised` so a green run cannot be quoted for it. It starts biting
  by itself after the link, with nothing to edit.
* **Home/End and the two character moves.** The deadline and the checkpoint are
  armed for the whole key path, but 096 measured Up/Down and 018 measured End.
  Home and the character moves are unmeasured in both directions.
* **`verified-move-readback` has never been produced.** Until the link it is a
  string no engine emits.

## Registered and deliberately not fixed: the notice names the wrong gesture

C routes the boundary press into the page's `canRescue` branch, whose sentence
is 「這一步可能已經改到文件，而且無法驗證。**回到選取手勢前的檢查點**。」 There was
no selection gesture; the user pressed an arrow key. This is finding 061's
shape, and it is left alone on purpose: the sentence lives in
`web/e2-editor-app.js`, the shell bundle's entrypoint, so changing it moves
`candidateCutover.pageSha256` — the decision document's row D price, for a
change that does not belong in the page. One sentence now serves two gestures,
and making it exact for both means either weakening the warning the delete path
needs or branching on which gesture failed, which is new machinery (AGENTS.md
§4 says stop and report at that point). The minimal honest edit looks like
deleting 「選取」; that is a product-wording decision and belongs to the owner.

## The one thing the owner does

Everything else in this round is done. The link is theirs, and it is the same
one 093 option B is already waiting on — **one link now carries both fixes**:

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v13/sdk-manifest.json
```

`handoff/RUNBOOK-operator-093-engine-geometry.md` is the manual, including its
2026-09-09 correction that step 5.3 is the cutover and must not be followed
there. **Its three pre-link checks are unchanged and still apply**, and one of
them now has a second thing to look for: `make -n` must still show **6** `em++`
lines all writing into `build/e2/e2-editor-v13/`.

## After the link, in this order

1. Record the five hashes; archive immediately; do **not** repoint the page.
2. Re-run `findings/evidence/096/probe_096_boundary_arrow.py --profile <new>`.
   **The prediction, written before the link: the boundary press is answered in
   well under a second and the session stays `ready`, so the probe reports
   `NOT_REPRODUCED` rather than `REPRODUCED`.** That is the first measurement of
   half A that has ever been possible, and if it does not hold, the engine
   change is wrong and this handoff is the place that said what to expect.
3. Re-run `probe_096_checkpoint_before_the_gesture.py`. Expect the `with` arm to
   report `ENGINE_ANSWERED` rather than `RECOVERED` — the probe has that
   outcome for exactly this reason. **A `RECOVERED` there after the link means
   the deadline is not in the artifact.**
4. Then the product path, whose new check reports `clausesExercised` including
   `B2` for the first time.
5. `EXPECTED_PASS 39 → 40` in `check_soak_bank.py` moves with the rest of the
   re-freeze, after the first clean run on the new identity — not before.

---

# Correction (2026-09-09, later): the target is `e2-editor-v14`, not v13

**"The one thing the owner does" above names the wrong target.** The command it
gives —

```
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v13/sdk-manifest.json
```

— would not have failed. It would have **recompiled and relinked into
`dist/profiles/e2-editor-v13/` in place**, because `src/probe_engine.cpp` went
in at 20:21 and v13's objects are from 12:10. Measured before anything was
written: that target already printed **two** `em++` lines. The result would be a
profile *named* v13 whose bytes are not v13's, while six soak runs, the 4a
acceptance, the ODT round, the revert rehearsal and the T4 manual round all bind
to that name (findings 027, 036, 042). The archive makes it recoverable, not
unconfusing — and unconfusing is what `build/archive/`'s naming convention is
for.

**Replaced by:**

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v14/sdk-manifest.json
```

The `E2_V14_*` block now exists in `wasm_sdk_probe/Makefile`, with its own
`build/e2/e2-editor-v14/` and `dist/profiles/e2-editor-v14/`; v13 is not a
prerequisite of any of it. **One link still carries both fixes** — option B's
geometry rides across unchanged (`src/a11y_tree_probe.cpp` untouched since
`c2a7abad`), and 096's deadline is the single variable
(`what_the_link_ships.py --variant a11y --since ec3402bf`: three units identical,
`probe_engine` CHANGED; `sdk/sdk-worker.js` byte-identical to v13's packaged
copy).

**The pre-link check in this handoff changes with it**: `make -n` must show
**6** `em++` lines all writing into `build/e2/e2-editor-v14/`. A line writing
into `build/e2/e2-editor-v13/` means the wrong target is being built — stop.
The hash list to record before the link now has **four** entries, v13 included
(`0fe25650…`), because v13 is the artifact this correction exists to protect.

**"After the link, in this order" stands unchanged** except that `<new>` is
`e2-editor-v14`. The two predictions written before the link are unaffected by
which name the artifact carries.

**One assertion was added that the v13 rule does not have, and the reason is a
gap rather than a preference.** Finding 096 adds no export, no ABI bump and no
manifest field, so all nine manifest declarations would pass on a v14 packaged
from v13's — or v10's, or the shipped v8's — wasm. The rule therefore greps the
packaged `probe.wasm` for `verified-move-readback`, with `verified-caret-readback`
as a positive control that runs first. Measured before it was written: the 096
literal is **absent** from all four of v8, v10, v12 and v13's shipped wasm and
the control is **present** in all four. There is no equivalent literal for
option B's geometry — that code emits only `,"x":`-shaped fragments — so
geometry stays covered by the manifest declaration and the product path's 41st
check, and **not** by these bytes.

Rule, measurements and what is still unvalidated:
`findings/evidence/096/step-build-and-link-rule/RESULT.md`. Operator manual:
`handoff/RUNBOOK-operator-093-engine-geometry.md`, whose own 2026-09-09 (later)
correction carries the same change.
