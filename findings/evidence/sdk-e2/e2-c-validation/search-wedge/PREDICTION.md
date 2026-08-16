# Predictions — what wedges a search on a reused engine

Written 2026-08-16, **before `web/e2-c-search-wedge-app.js` existed**.

## The observation being characterised

Relink queue item `queue-search-after-reopen-wedges`, from D4's heap follow-up
(`findings/evidence/sdk-e2/e2-c-validation/d4/heap/`):

> On one engine, cycle 1 (open, search, click, insertText, save, close)
> succeeds; **cycle 2's search times out at 30 s** and every later search
> returns `BUSY` — the worker's own in-flight guard.  Reproduced identically in
> Chrome and Firefox.  The same loop without the search completes 8/8.

So the wedge involves a search.  What is **not** known is which of three things
is required: a second search at all, a reopen between them, or the
click/insert/save that cycle 1 does after its search.

The product does not take this path today — `EditorSession` builds a fresh
engine per session — so this is an SDK-level characterisation, not a product
defect.

## Arms, all on ONE engine

| arm | what it does |
|---|---|
| `two-searches-one-open` | open, search, search — **no close** |
| `search-close-open-search` | open, search, close, open, search — nothing else |
| `full-cycle-then-search` | the recorded shape: open, search, click, insert, save, close, open, search |
| `no-search-then-search` | open, click, insert, save, close, open, **search** (the first cycle never searches) |

Every search gets `timeoutMs: 30000`, the same as the recorded rounds.  Both
browsers.

## Predictions

* **P-W1** — `two-searches-one-open`: the second search **returns** (< 5 s).
  If it hangs, the trigger is "a second search on an engine", and the word
  "reopen" comes out of the queue item entirely.
* **P-W2** — `search-close-open-search`: the second search **hangs** (30 s
  timeout).  This is the minimal reproduction, and it is the load-bearing
  prediction: if it returns, then the click/insert/save between them is part of
  the trigger and the item's title is wrong.
* **P-W3** — `full-cycle-then-search`: hangs.  Control, that this page
  reproduces what D4's page recorded.  If it does not, nothing else on this page
  can be compared with the recorded rounds.
* **P-W4** — `no-search-then-search`: the search **returns**.  Together with
  P-W2 this would say the poison is laid by the FIRST search and collected by
  the second.

## Retreat conditions, named now

* If P-W3 fails, the page is not reproducing the phenomenon and no other arm may
  be read as being about it.
* If P-W1 and P-W2 both hang, the reopen is irrelevant and the finding is "the
  second search on an engine never returns" — a wider claim, and it must then be
  checked against every harness in the tree that searches twice.
* If every arm returns, the wedge is not in these four variables and the item
  stays open with one more thing ruled out.

## What this cannot establish

Where inside the engine the search stops.  This page measures the SDK boundary
only: which sequence wedges, in which browser, at what timeout.  Attribution
past the worker boundary needs the diagnostic profile and is out of scope here
(the shape finding 040 and finding 048 were both disciplined by).
