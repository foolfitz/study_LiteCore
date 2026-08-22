# Arrow keys bind if and only if the profile offers the action

Arm `arrow-keys-match-the-profile`
(`wasm_sdk_probe/tools/probe_064_format_reaches_typing.py`), Chrome,
2026-08-22, against `e2-editor-v3`. `evidenceClass: "diagnostic"`.

## Why

An operator noticed Up/Down do not move the caret. They were deliberately
unbound: the engine implements line movement but the v3 contract has no wire id
for it, and the page's own comment said offering a key that cannot dispatch
would be worse than offering nothing.

The ABI 4 link gives those actions ids 16-19. Rather than leave the binding as
a second thing to remember on the day the artifact changes, the page now lists
all six arrows and gates each on `offers()` — so they light up because the
manifest says the action exists.

That creates the risk the page unbound Ctrl+A to avoid: a key **listed but not
gated** is taken from the browser and dispatched into a profile with no such
action.

## Result on v3

| | |
|---|---|
| profile / abiVersion | `e2-editor-v3` / 3 |
| `move-line-up` offered | **false** |
| ArrowUp moved the caret | false |
| ArrowUp taken by the page (`defaultPrevented`) | **false** |
| error shown | none |

ArrowLeft, which v3 does offer, moves the caret (2624 → 2491) and comes back
`defaultPrevented: true`. That is the instrument's own control: if the offered
key were not reported as taken, the watcher would not be observing this page's
handler and its reading of ArrowUp would be worthless.

The arm reads the running profile and asserts the **matching** behaviour, so it
stays correct across the link instead of needing a rewrite on the day.

## The first version passed for the wrong reason

It measured only the caret and the toast. A mutation deleting the gate **still
passed** (`f070-mutated.json`):

- without the gate ArrowUp is `preventDefault`-ed and dispatched
- the client's refusal is swallowed by the `.catch(() => {})` at the call site
- the observable result is an unmoved caret and no toast — **identical** to
  the correct behaviour

So "correctly not bound" and "bound, dispatched, failed silently" were the same
green. The fix was to measure whether the page **took the key**: a bubble-phase
`keydown` listener runs after the page's handler, so `defaultPrevented` there is
the page's answer.

With that, the same mutation fails (`f070-mut2.json`,
`upKeyWasTakenByThePage: [true]`) and the restored tree passes
(`f070-restored.json`, `[false]`).

This is the third time in this project that an arm measuring "X did not happen"
needed a second signal to tell absence from a silently swallowed failure.

## Files

- `f070-arrows.json` — first version, PASS (for the wrong reason)
- `f070-mutated.json` — gate deleted, first version, **still PASS**: the hole
- `f070-fixed.json` — with `defaultPrevented`, PASS
- `f070-mut2.json` — gate deleted, **FAIL**, the mutation now caught
- `f070-restored.json` — tree restored, PASS
