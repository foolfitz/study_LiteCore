# Finding 059, the product half — shell v17's disposition change, validated

2026-08-18. Chrome. Shell **v17** `34289a7bd8ffc3df…`, artifact `d538ce0b…`.
Both runs are UNSHIMMED and unmutated except where stated, and the baseline's
`servedShell.servedSha256` equals the declared v17 digest.

## What changed

`formatFailureDisposition()` returns `dispatched-unverified` for
`LOK_COMMAND_FAILED` instead of falling through to `unknown-rollback`, so the
queue is not blocked and undo stays reachable. SPEC E2-C 2.6c, written in the
same generation.

The basis is checkable rather than analogical: that error code is emitted only
from the engine's UNO command **result** handler, after the payload has been
matched to the command that was sent (`src/probe_engine.cpp:2279-2291`). Core
answered about that command, so the dispatch is **established**. Finding 046's
narrowing exists to stop a *guess* being treated as knowledge; this case is on
the other side of that line.

## Baseline — `product-path-baseline-v17.json`

`ok: true`, "every product path this covers behaves; 1 not established; 2 known
red", and **no stale declarations**.

## The consequence nobody predicted

With the queue no longer blocked, both B presses run, and
`bold-can-be-turned-off-again` **passes**. From the user's seat bold now turns on
and off. The runner immediately reported its KNOWN_RED declaration stale, which
is what that mechanism is for.

So the declarations were restructured rather than left standing:

| check | state | why |
|---|---|---|
| `bold-can-be-turned-off-again` | **green**, removed from KNOWN_RED | it passes; a declared-red check that passes is the thing the runner shouts about |
| `a-format-that-worked-is-not-reported-as-failed` | **KNOWN_RED, finding 059** | the engine half that is actually left: the product reports a failure for an action the saved document shows succeeded |
| `the-caret-is-drawn-where-it-was-placed` | **KNOWN_RED, finding 060** | it was silently confounding mutation rounds |

## Mutation — `product-path-mutation-inline-format-rollback.json`

`inline-format-rollback` turns the new branch off, restoring exactly what
shipped until 2026-08-18.

`ok: true`, "the mutation was detected by the check that owns it".

`mustGoRed` is two checks, not one, and the second is declared collateral rather
than assumed: with the queue blocked again the **second** B press never runs, so
`bold-can-be-turned-off-again` goes red too. That dependency was measured — the
check is green without the mutation and red with it — not reasoned about.

The mutation is deliberately **not** owned by `bold-can-be-turned-off-again`: it
was KNOWN_RED when this was written, and a mutation owned by an already-red check
cannot be shown to have been detected.

## What this does NOT do

It does not make the formatting reliable, and it does not claim the action
succeeded — nothing at runtime verifies that. The engine's predicate is
unchanged and still blocks the next link
(`queue-inline-format-argument-is-rejected-by-core`). The checklist row
`turn-formatting-off` is `partial`, not `done`: pressing B still shows the user a
message saying it failed.
