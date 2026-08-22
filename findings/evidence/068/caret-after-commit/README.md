# The caret after a text commit: seven runs, read from the state, not the pixels

Arm `caret-state-after-commit`
(`wasm_sdk_probe/tools/probe_064_format_reaches_typing.py`), Chrome,
2026-08-22, against the shipped `e2-editor-v3` artifact `29ec627b…` through a
mirrored page. `evidenceClass: "diagnostic"`.

## Why this arm exists

Five earlier attempts measured the caret in PIXELS and could say *what*
happened but never *why*, because `paint()` has four ways to draw nothing and
all four look identical on a canvas: no cached tiles, no editorState or
document, no `caret` in the state, or `selection.collapsed === false` (which
suppresses the caret on purpose so a range highlight never gets one painted
inside it).

So this arm asks the page instead of the canvas. Every state update records
what the snapshot held; every `paint()` records which of the four branches it
took; both are labelled with the step that caused them.

## Result: 2 PASS / 7

| runs | `sourceSequence` across the commit | caret `x` |
|---|---|---|
| 5 (FAIL) | 3 → **5** | unchanged |
| 2 (PASS) | 3 → **6** | updates |

`paint()` reported `drew-caret` in **every** run. The page is not declining to
draw. What differs is the rectangle it is given.

Representative failing run (`f068-rep2.json`):

```
click    x   = [1418, 1418, 1418, 1598, 1598]   src = [1, 1, 1, 3, 3]
commit   x   = [1598, 1598, 1598, 1598, 1598]   src = [3, 3, 3, 5, 5]
move     x   = [1598, 1598, 1598, 2984, 2984]
```

Representative passing run (`f068-rep5.json`):

```
commit   x   = [1598, 1598, 1598, 3131, 3131]   src = [3, 3, 3, 6, 6]
```

`sourceSequence` counts every editor callback that changed state. The commit
window advances it by **two** when the caret stays put and by **three** when
the caret follows the text. The third callback is the one carrying the new
cursor rectangle, and it is missing five times in seven.

When it is missing, the caret is drawn at the **pre-commit** rectangle — i.e.
one whole run of typed characters behind where the text now ends. Type one
character and the caret sits in front of it. That is the operator's original
description, word for word, and it is now reproduced from the state rather
than argued from a screenshot.

## Two positive controls, both required

1. **Drawing.** Some `paint()` must report `drew-caret` after the move, or the
   instrument never saw the page draw a caret and its silence elsewhere means
   nothing.
2. **Staleness.** The caret `x` must change on the move, or the arm cannot
   detect an `x` that fails to change, and "it did not move after the commit"
   is unfalsifiable.

Both hold in all seven runs. The arm returns `NOT_ESTABLISHED`, not `FAIL`,
if either fails.

## What one run would have said, and why the count is the result

Run 1 of this arm failed and run 2 passed — same arm, same page, opposite
outcomes. Either one alone would have supported a confident and wrong claim:
"the caret is never updated" or "the caret follows typed text". The defect is
**intermittent**, so the number of runs is not a robustness detail here, it is
the measurement.

## What is NOT established

- **Why the third callback goes missing.** LOK's `paste()` is what commits the
  text (finding 067 measured `method: "paste"`), and this arm cannot see LOK's
  side of the boundary — only that the engine's state did not change. Whether
  paste emits the cursor callback unreliably, or emits it and the payload fails
  to parse, is unmeasured. The engine already distinguishes those: a callback
  in the cursor range whose payload does not parse emits
  `editor-callback-parse-error` (`probe_engine.cpp:2316`). Nobody has looked
  for that event during a commit; that is the next measurement and it needs no
  link.
- **Reconciliation with the pixel arm**, which found *no* caret-height run on
  that line after typing rather than one at the stale position. A caret drawn
  at the pre-commit rectangle should still leave a run somewhere on the line.
  Not forced into agreement here: this arm reads the state directly and is the
  stronger instrument, and the discrepancy stays named.

---

# Second round, same day: the engine was never the problem

Four more runs (`f068-cb1..4.json`) with two further mirror patches, and they
answer the question the section above left open — differently from the way it
was framed.

The engine's `editor-state` events carry a `source` naming the callback that
caused them, and a cursor-range callback whose payload will not parse emits
`editor-callback-parse-error`. The worker already forwards both. Both are
gated behind `editorDiscoveryEnabled()`, which is **false on a product
profile** because the builder pops `diagnostic` from the manifest — so on the
shipped page these events are constructed and then dropped. The mirror ungates
exactly those two forwards.

## What the engine actually does

```
click       selection-rectangles   caretX=1418  seq=2
click       visible-cursor         caretX=1598  seq=3
commit      visible-cursor         caretX=3131  seq=6      <-- correct, and prompt
commit      format-state           caretX=3131  seq=7..11
move        visible-cursor         caretX=2984  seq=12
```

**The cursor callback arrives, on time, with the right rectangle.** No parse
errors in any run. Every earlier reading of this finding — "no caret drawn",
"the caret rectangle is not refreshed", "LOK's paste does not emit the
callback" — is wrong.

## Where the stale value comes from

The page's snapshot is refreshed only by the drain, which does
`result?.state || await getState()` once per queued operation. Reading the two
streams together:

```
snapshot read  caretX=1598   sourceSequence=5     <-- the page's last read
engine event   caretX=3131   sourceSequence=6     <-- arrives just after
```

The page's last `getState()` is answered at sequence **5**. The cursor callback
is sequence **6**. Nothing asks again, and the engine's own announcement of
sequence 6 is dropped by the worker. So the page keeps the pre-commit
rectangle and draws it faithfully.

This accounts for **all eleven runs**, passing and failing:

| outcome | last `getState()` answered at | caret |
|---|---|---|
| FAIL (9) | sequence 5 — before the cursor callback | pre-commit |
| PASS (2) | sequence 6 — after it | correct |

It is a race between the drain's `getState()` and the cursor callback, and the
reason it is never corrected afterwards is that the product profile drops the
engine's state announcements.

## Consequences

- **Not an engine defect, and not a link.** The engine's behaviour is correct
  and prompt in every run.
- **Not upstream.** LOK emits what it should.
- The remedy is in the worker and the session, and `sdk-worker.js` is one of
  the five identities a profile binds — so a worker fix landed before the ABI 4
  link ships inside that profile at no extra cost.

---

# The remedy, verified before it ships

Two changes, both outside the engine:

- **`sdk/sdk-worker.js`** forwards `editor-state` on every profile instead of
  only a discovery one. Every field it carries is already in the reply the
  product's own `editorGetStateV2` returns, so this exposes nothing new — the
  gate was withholding an announcement, not a surface.
- **`editor-shell-v2/narrow-editor-v2-session.js`** overrides
  `_handleEngineEvent` to adopt that announcement into the snapshot, behind
  two guards: `sourceSequence` must advance, and the session must be
  `ready` or `busy`.

  An override rather than an edit to `EditorSession._handleEngineEvent`,
  which is where it went first. `check_e1_c_bundle_intact.py` refused
  that: `editor-shell/editor-session.js` is bound to E1-C's verdict (shell
  bundle `187706b2…`), so editing it would unbind a verdict that has
  nothing to do with this defect. A subclass reaches the same event at no
  such cost. Re-verified from its new home: `f068-v2sess1..4`, **4/4**.

The monotonicity guard is not decoration. Events and drain reads are now two
sources for one field; without it a slow event could land after a fresher read
and move the caret backwards — trading a caret that lags for one that jitters,
which is worse because it is not reproducible.

## Before and after, same arm

| configuration | PASS |
|---|---|
| neither change (`f068-rep*`, `f068-state2`) | **2 / 7** |
| worker forwards, session ignores (`f068-cb1..4`) | **0 / 4** |
| both changes (`f068-fix1..5`) | **5 / 5** |

The middle row is the isolation, and it was measured before the fix existed
rather than reconstructed afterwards: forwarding alone does nothing, because
nothing was listening. The session half is what closes the defect.

The commit window also goes from five state reads to eleven — the engine's
announcements arriving is directly visible in the count.

## Why the mirror substitutes the worker from source

The v3 profile's copy of `sdk-worker.js` is frozen: it is one of the five
identities that profile binds, and rebuilding the profile to refresh it would
rewrite the manifest and unbind round two's evidence. So a worker fix cannot be
tested by rebuilding anything. The mirror runs the **source** worker against
the **frozen** wasm — `probe.wasm` untouched and byte-identical — and the
report declares the substitution in `workerSubstitutedFromSource`.

The fix ships for real in the v4 profile, whose builder hashes whichever worker
is in the tree at link time. Nothing extra is needed at the link for it.
