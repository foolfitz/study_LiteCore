# Handoff: selected text can be emboldened, and five of the day's conclusions were my own instruments

Written 2026-08-23, continuing `HANDOFF-2026-08-23b-the-garbage-in-the-margins.md`.
Read that one first for findings 075/076/077; this one starts where the operator
did a manual pass.

## State

**`e2-editor-v7` is the shipped profile** (cut over this session; validation run
in flight when this was written — see "Verify before trusting" below).

v7 is v4's loader, wasm and worker **byte for byte** (`f923cfa5…` / `e6ee92ca…`).
One manifest difference: the four inline formats are offered for range
selections as well as for a caret. **No relink.** The pinned hash did not move
with the worker URL, for the first time, because the artifact did not move.

| finding | what | state |
|---|---|---|
| 075 | harness lost two paragraphs to off-page garbage | closed |
| 076 | the tile buffer is `malloc`'d, so uninitialised heap is painted where a person can see it | **fixed in source, waits for a relink** |
| 077 | the inline-format arms inherited their starting state | closed |
| **078** | **selected text could not be emboldened** | **closed, shipped as v7, operator-confirmed** |
| **079** | **the toolbar's availability comes from a stale selection shape** | **open, no prescription** |
| — | the format barrier's `stage-deadline` on the a11y core | **open, the only real FAIL left there** |

## Finding 078, end to end

The operator selected text, pressed bold, got
`EDITOR_FORMAT_GESTURE_UNSUPPORTED`. Thirty seconds of manual use; 38 green
checks had not seen it.

**The manifest offered the four inline formats for `collapsed` only.** That was
honest — range dispatch had been characterised for the paragraph actions and not
for these, and `build_e2_b_profile.py` declines to declare a gesture nobody
measured. What failed is what came after: **"not characterised" became "the user
cannot do it", and nothing tracked the cost.**

The net could not have caught it. `format_arm` drives a collapsed caret BECAUSE
that is the only gesture offered — the runner says so in its own comment. **The
harness had taken the product's declaration as the specification**, so an
under-offer was invisible to every check at once.

### The grant could not be partial

The first plan (and the first adjudication) was to grant `range-single` and
withhold `range-cross`. **It cannot be built.** For a selection it has not
classified the engine requires BOTH range bits; classifying needs an HTML read
that findings 037/038 identify as an engine wedge, so the gate is conservative.

Measured three ways: single-only refused, cross-only refused, both accepted.
`e2-editor-v6` is that dead identity, kept with a `SUPERSEDED.md` saying why.
The AND-semantics limit is recorded in `e2/expected-gesture-offers.json` so
nobody re-derives it by minting three profiles again.

### What was measured before granting

* All four inline formats, both range shapes: **the formatted text equals the
  selected text**, baseline clean.
* **Native LibreOffice 26.8 writes the same shapes** — paragraph-level for a
  fully selected paragraph, a span for a partial one, same extents
  (`tools/f078_native_range_format.cpp`). Not even a divergence to record.
* On **`e2-editor-v7` itself**, not on the diagnostic profile: eight arms
  text-exact, product path 36 PASS / 3 NOT_ESTABLISHED, `ok: true`.
* **The operator, with a real mouse: all four buttons pass.** This project
  treats that as closure, not the harness going green.

## The check that should have existed, and the one that matters more

`an-inline-format-reaches-a-selection` asks the user's question instead of the
manifest's, with mutation `format-ignores-a-selection` (format buttons can only
send `enabled: false`) taking it PASS → FAIL. **Named weakness**: wide blast
radius, so it proves the check CAN fail, not that it is the one that would
notice.

More important is `tools/check_gesture_offers.py` + `e2/expected-gesture-offers.json`,
now in `test-e2-b-static`. The expectation lives OUTSIDE the manifest, so the two
can disagree, and **both directions fail**: narrower is 078, wider is a claim
nobody measured. It reported the shipped v4 as NARROWER — 078 visible to an
automated check for the first time.

**Never edit the expectation to make it pass.** Either the manifest is wrong, or
a measurement was taken and both move together with the evidence named.

## Finding 079, found by a mutation that did nothing

The first version of 078's mutation returned early when
`lastSelectionShape !== "collapsed"`. It **never fired**, on two runs — at press
time, after a drag, the page still thinks the selection is collapsed.

That explains a thing that had been a puzzle: on a profile granting one range
bit, the BUTTON was enabled while the ENGINE refused. The page's shape is stale
and `collapsed` was offered. **The operator's experience had two layers, and I
had only found the first.**

Urgency drops with v7 shipped (all three gestures granted, so format buttons no
longer depend on the shape) but does not vanish: `delete-selection` is offered
for ranges only, so a stale `collapsed` would show it DISABLED when it is
available. **Derived from the gesture table, not measured.** That is the next
thing to do.

**Keep the inert-mutation run** (`mutation-that-never-fired.json`). A mutation
that does nothing looks exactly like a check that cannot fail, and the
difference was only visible because the nothing was investigated instead of
replaced.

## Five times in one day I signed one thing's name with another thing's measurement

This is the pattern to carry forward; every instance was caught by the same
rule, and never by reading code.

| what | caught by |
|---|---|
| assembled "the cache does not follow" across two runs | recording cache and document in the same arm |
| "the fix is refuted" from v5 alone | the v4 variation control |
| about to grant four actions on bold's evidence | the external adjudicator |
| `e2-inline-range`'s green taken as `e2-editor-v6`'s | v6 refusing on its first run |
| a unit test "proving" the parser correct | a self-closing style element in a real document |

The last one is the sharpest: **a test whose fixture you wrote can only prove
the parser correct on shapes you already thought of.** The parser was wrong four
times today — blind to paragraph-level styles, running past self-closing
elements, counting a list prefix as selected text, and looking only at
`fo:font-weight` when asked about italic. Each wrong version produced a
confident, reproducible, plausible finding.

**A stable wrong answer looks exactly like a real discovery.** Two of them were
only caught by putting the parser's own input — the style markup it read —
into the record beside its verdict.

## The oracle's normalisation is named, not promised

`probe_inline_range_format.py --self-test` runs the table of what whitespace
squeezing can and cannot hide: a dropped paragraph, a dropped character and an
extra character all still fail; **a difference that is only whitespace is
invisible, deliberately**, and nothing has measured whether a format can miss a
space between two words it covered.

An earlier round of this write-up said "exact" without that qualifier. It
reported the oracle more strongly than it earns.

## Verify before trusting this document

The cutover's own validation run was still going when this was written. **Check
it before building on the "shipped" claim above:**

```sh
cd wasm_sdk_probe
# what the page actually loads, with no --profile: it measures the shipped page
python3 tools/run_e2_c_product_path.py --out /tmp/ship.json
python3 tools/check_gesture_offers.py           # expects e2-editor-v7
make test-e2-b-static                            # includes the two above
```

### The result, and a criterion I had written too rigidly

The cutover run came back **34 PASS / 5 NOT_ESTABLISHED, `ok: true`**, with
`an-inline-format-reaches-a-selection` PASS and all three gestures offered.

That is two PASSes fewer than the mirrored v7 run (36/3). The two that moved —
`format-a-paragraph-changes-that-paragraph` and `cut-removes-the-selected-text`
— are the pair that reports NOT_ESTABLISHED when the canvas band count and the
line count disagree, and that disagreement is the **known intermittent** one
measured earlier the same day (the SHIPPED core reported 10 bands at rest in one
of five rounds; see finding 075's repeats).

I had written "if it is not 36/3, revert". **That criterion was wrong** — it
treats a precondition that did not hold as if it were a product failure, which
is the distinction NOT_ESTABLISHED exists to make. The honest criterion:

* **any FAIL, or `ok: false`** → revert the cutover.
* **NOT_ESTABLISHED on the band-dependent pair** → re-run; it is the known
  flake. If it persists across runs, it is not the flake and wants
  investigating before it is trusted.

Reverting is one line: `workerUrl` in `web/e2-editor-app.js` and its copy in
`dist/`, back to `e2-editor-v4`. The pin does not move either way, because the
artifact does not.

## Loose ends left running on the machine

A preview server for the SHIPPED profile is on **port 8796**
(`tools/serve_manual_preview.py --profile e2-editor-v7`). It serves a mirror;
`dist/` is not written by it.

**Port 8792 is serving `e2-editor-v4` from an older session** — not this
session's, and not killed, because it is not mine to end. It has no banner. If
anyone is asked to look at "the editor" and opens 8792, they are looking at the
profile from before this cutover. Every preview this session served carries a
green banner naming the profile and both hashes, for exactly that reason
(finding 068 was confirmed against half a fix because nobody could tell).

## Open work, in the order I would take it

1. **Finding 079** — stop caching the selection shape, or refresh it before the
   toolbar reads it. Measure the `delete-selection` direction first: it is the
   one a user hits, and it is currently derived rather than observed.
2. **The format barrier's `stage-deadline`** on the accessibility core — the
   only real FAIL left there, and possibly the same thing as the product path
   stalling on that profile (4 of 8 runs, never on the shipped one). The
   `[step]` trace added this session names the two most expensive steps;
   attach to a stalled run and ask where it is.
3. **Finding 076's relink** — `calloc` is in the source and nothing ships it.
   Whatever else rides that link, this should.
4. The a11y projection's own gaps, from `DESIGN-2026-08-22-aria-projection.md`
   §7.4: emphasis is not projected, tables are a blank, and five criteria are
   about the shell and have never been checked.

## Two things a new session should not re-derive

* **The AND-semantics of the gesture gate.** In
  `e2/expected-gesture-offers.json`. It cost three minted profiles to find.
* **The product path stalls on the accessibility profile and produces nothing
  when it does** — the report is written only at the end. Use `timeout 3600`,
  read the `[step]` trace on stderr, and expect to lose runs.
