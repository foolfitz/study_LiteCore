# Handoff, 2026-09-10 (c) — 094 and 097 are censused, 098 is registered, and this round rests here

Entry points, in order: this file, then
`handoff/HANDOFF-2026-09-10b-b4-is-watched-on-both-profiles.md` (its open list
and gate still hold), then the three finding files touched this round read
whole: `findings/094-*.md`, `findings/097-*.md`, `findings/098-*.md`.

Tree clean, nothing pushed. Three commits since the morning: `1ad39d10`
(097 census), `b9ea7ecd` (094 census), `02cd2767` (098 registered). No runner,
profile, engine, or shell byte changed — all three are finding-file registration
only. `make test-e2-c-static` was not re-run because nothing under test moved.

The owner set this round's stop line: **finish 094 and 097, then hand off and
rest.** That is done. 098 was already fully written from source when the stop
line arrived, so it is committed as its own unit rather than discarded.

## What was done

### 094 census — closed

The "not checked" section asked which other served files feed the editor page
but sit outside the shell-bundle hash net. Checked three places: the HTML's
static references, runtime `fetch`/dynamic `import` in the product-file graph,
and the non-JS assets actually present under `web/`. Result:
`web/e2-editor.html` is the **only** served file that defines this page's look
and behaviour and lies outside the hash net. Its CSS is inline in it, so 094's
original claim already covers all of the page's CSS — there is no separate
unbound CSS file, icon, or worker HTML. `web/r6.css` / `web/r7.css` belong to
the R6/R7 reader shell, not this page. Runtime fetches are fixtures (test input,
opened by the user) and `sdk-worker.js` (already bound as `workerSha256`); the
static import graph is closed. 094's disposition is unchanged: bind it at
cutover alongside 093.

### 097 census — narrowed, not multiplied

The "not checked" section asked which other contract fields are hard-coded and
read by nothing on the product path. Census (not sample) of every `editorContract`
field against the five product-path files: **14 fields are hard-coded and
product-path-unread**, and `boundaryRejectionRequiresFreshWorker` is one of
them. But it is the **only one contradicted by measurement** (40/40 wedges,
behaviour opposite the declaration). The other 13 are unread-but-not-shown-false
— five honesty declarations ("we do not accept arbitrary keycodes/UNO, we expose
no raw callback") and eight mechanism descriptors (names of a mechanism the
product implements directly). So 097 is a **single-field defect**, not a
"the contract is fiction" systemic problem. Concrete detail: `redo` IS read
(`offersRedo` gates on it because `oxsdk_document_redo` is a newer compiled
export) while `undo` is NOT — same field shape, one load-bearing, one pure
description. Honest limit written into the finding (AGENTS.md §7/§11): "unread"
is measured statically this round; whether the other 13 match behaviour is a
reading-based classification, not a re-measurement, except 078 (inline format)
and the diagnostic-page assertion on `rawCallbackExposed`.

### 098 registered — the new "arrow presses bank a checkpoint" item, explained

T9's shakedown observed that arrow presses alone marked a clean document dirty
enough for half C to bank a checkpoint (turning `rescue: none` into
`rescue: checkpoint`). 098 reads the cause from source: every v2 `action()` —
including the six pure caret moves — is enqueued with `mutation: true`
(`narrow-editor-v2-session.js:388`); the base drain sets `dirty` from that flag
(`editor-session.js:309`) and bumps the content stamp; moves do not advance
revision (v2 client postcondition). So a caret move flips a never-typed document
to `dirty`, and `_checkpointBeforeBoundaryMove`'s "nothing to lose" guard —
which reads `dirty`, meaning to ask "was anything typed" — is defeated: the
second boundary-capable move on a clean document banks one checkpoint save of
bytes identical to authority. **Not data loss** (moves do not move revision, so
restored bytes equal authority bytes); the harm is a misleading dirty/rescue
indicator and one redundant save.

## The open list now

1. **The wrong-gesture wording (061's shape)** — owner's ruling, deliberately
   unfixed. Not touched. My inclination unchanged: it is a real
   literally-true-causally-misleading notice, but the fix branches the notice
   (new machinery) and moves `pageSha256`; it is cheap to fold into the next
   link, which is where I would put it.
2. **094 / 097** — **censused this round, dispositions unchanged.** Both bind /
   revisit at cutover. Their remaining "not done" items are narrowed and named.
3. **098 (new, registered)** — the fix is an **owner decision**: the root line
   `dirty: ... || item.mutation` is in E1-C-bound `editor-session.js` and cannot
   be edited, so the two candidate levers (make moves `mutation: false` in the
   v2 session's `action()`; or make the guard test revision, not dirty) are both
   product-byte changes that move `pageSha256`. Candidate A (moves →
   `mutation: false`) looks correct but needs a check that no other consumer
   relies on a move bumping the content stamp. **Send the fix to adversarial
   review (B′'s opus/codex seat) before landing** — it touches unsaved-work
   handling. Register-only this round (§4).
4. **Closed earlier today, for the record**: 096 "why silent" (arm U, native
   dedup log, direct observation); 095 (T9, re-attributed as 096's pre-death
   window). Neither is on the open list any more.

## The gate

Unchanged from 09-10 (b): soak 0 of 12, reordered to the end of development,
full run on the final identity before any cutover, floor of three calendar days;
T4 to be re-earned on the final identity, the owner's evening; the shipping page
still points at v8. **No cutover has been performed.** Nothing this round
touched any identity-bound evidence.
