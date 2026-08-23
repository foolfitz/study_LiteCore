# Finding 077 — the inline-format arms inherit their starting state, and one
# wrong starting value inverts every bold arm after it

Three runs, 2026-08-23. Read them in order; the first two produce a conclusion
that the third destroys, and that sequence is the point.

## What is in here

| file | harness | what it shows |
|---|---|---|
| `v4-shipped-core.json` | waits on `aria-pressed` | 13/13 arms confirm in ~202 ms; run is 35 PASS / 3 NE, `ok: true` |
| `v5-accessibility-core.json` | same | 0/13 arms confirm; 7 sit out a 20 s timeout; run is 22 / 5 / 11 |
| `v5-latency-wait.json` | waits on `#s-latency`, records the cache | the cache moves on **every** arm, and the saved document follows it 13/13 |
| `v5-precondition-established.json` | normalises with `清除格式` and asserts the start state | **13/13 arms PASS**; the check goes FAIL -> PASS and the run 3 FAIL -> 1 FAIL |

## The conclusion the first two invited, and why it was wrong

Two runs of one harness across two cores is a clean variation control, and it
said: the format state cache follows the press on the shipped core and never
follows it on the accessibility core. That was written up as an engine defect.

It was an artefact of the wait itself. The toolbar is a TOGGLE whose request is
derived from the cache:

```js
? { enabled: formatStateFor(action) !== true }
```

So when the cache starts at the wrong value, the press asks for the OPPOSITE of
what the arm wanted, and the cache moves AWAY from the value the wait was
waiting for. It could never be satisfied. Twenty seconds of waiting for
something that, by design, was not going to happen.

The shipped core confirmed 13/13 only because that run's starting values
happened to be right.

## What the third run shows

Same arm, same run, cache and saved document recorded together:

```
MKBOLDON   want=True   cache true ->false   document False   x
MKBOLDOFF  want=False  cache false->true    document True    x
MKITALON   want=True   cache false->true    document True    ok
MKITALOFF  want=False  cache true ->false   document False   ok
MKPREOLD   want=True   cache true ->false   document False   x
MKSURVIVE  want=True   cache false->true    document True    ok
```

The document follows the cache 13 times out of 13. The only anomaly is
`MKBOLDON` — the FIRST arm — whose cache reads `true` **before any press**,
where the shipped core reads `false`. Everything after it is deterministic:
each arm leaves the cache inverted for the next one.

`format_arm` opens each arm with `insert-paragraph-break`, and a new paragraph
INHERITS the caret's formatting. So the starting state is whatever the rest of
the run left behind, and it was never controlled.

## Not established

* **Whether that starting `true` was correct.** If the caret really was in bold
  text, reading `true` is right and the arm's assumption is what is wrong.
  Nobody checked where the caret was.
* **Why the two cores differ there.** The v5 run had several NOT_ESTABLISHED
  checks before this point, so the documents had already diverged. This does
  not need a core difference to explain it, and must not be attributed to one
  until that is ruled out.
* **Whether `清除格式` is reliable on v5.** `clear-format-removes-every-inline-format`
  is NOT_ESTABLISHED there, i.e. unknown — which is why the prescribed fix
  asserts its precondition instead of assuming it worked.

## The fourth run settles it

Establishing the starting state — press `清除格式`, then for an OFF arm one press
to turn the format on, then assert the cache holds what the arm needs — makes
every arm pass on the accessibility core:

```
set-bold MKBOLDON   precondition false, got false -> cache true,  document True   ok
set-bold MKBOLDOFF  precondition true,  got true  -> cache false, document False  ok
```

**Bold was never broken on that core.** The arm was starting from a state it did
not control, and on the shipped core that state happened to be right.

Two side results worth keeping:

* `清除格式` works on the accessibility profile — thirteen normalisations,
  thirteen successes — even though `clear-format-removes-every-inline-format` is
  still NOT_ESTABLISHED there. A check reporting "unknown" is not evidence of
  absence, and this is what it looks like when something else measures it.
* With the page clip reporting its worst scan rather than its last, the run
  reports `pageRange [15, 709]` — the same page range the offline replay derived
  from the captured canvases for finding 075. Two instruments, one number.
