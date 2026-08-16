# The search wedge, characterised — it is the reopen, and nothing else

Measured 2026-08-16 on the shipped `e2-editor-v2` artifact (wasm `572035ac…`),
both browsers, one engine per arm, one page load per arm.
Predictions: `PREDICTION.md`, written before `web/e2-c-search-wedge-app.js`
existed.

## The question

Relink queue item `queue-search-after-reopen-wedges` recorded an observation
from D4's heap follow-up and left three candidates unseparated: does the wedge
need a **second search**, a **reopen**, or the **click/insert/save** that the
recorded cycle did between them?

## Result

| arm | what it does | chrome | firefox |
|---|---|---|---|
| `two-searches-one-open` | open, search, search | **returned, 19 ms** | **returned, 18 ms** |
| `search-close-open-search` | open, search, close, open, search | **wedged, 30001 ms** | **wedged, 30291 ms** |
| `full-cycle-then-search` | the recorded shape | **wedged, 30001 ms** | **wedged, 30089 ms** |
| `no-search-then-search` | open, insert, save, close, open, **search** | **wedged, 30001 ms** | **wedged, 30000 ms** |

## What the arms say

* **A second search is not the trigger.** Two searches on one open return in
  ~19 ms (P-W1 **held**).
* **The reopen is.** `search → close → open → search` is the minimal
  reproduction: nothing else happens between them and the second search never
  returns (P-W2 **held**).
* **A prior search is not needed either.** `no-search-then-search` — where the
  first document is never searched at all — **also wedges** (P-W4 **FAILED**;
  it was predicted to return).
* The recorded shape reproduces here (P-W3 **held**), so the arms are
  comparable with D4's rounds.

**So the statement is narrower and stronger than the queue item's:** on a reused
engine, *the first search after the first close never returns*, whatever
happened before the close.  The word "again" comes out — a search is not needed
before the reopen; the reopen is enough.

P-W4 failing is the whole value of this round.  The prediction assumed a first
search laid the poison and a second collected it; the data says the first
document's search is irrelevant and `close` + `open` is sufficient.  Written
down as failed rather than quietly rewritten — the retreat conditions in
`PREDICTION.md` named this case.

## What this does NOT establish

* **Where inside the engine the search stops.**  This measures the SDK
  boundary only: which sequence wedges, in which browser, at what timeout.
  Attribution past the worker boundary needs the diagnostic profile, and this
  tree has twice been wrong by guessing at that boundary (findings 040, 048).
* **Whether the reopened document is otherwise usable.**  `insertText` and
  `save` after a reopen were not exercised in the wedging arms — the search runs
  first and takes the engine's in-flight slot with it.  D4's `shared-nosearch`
  arm did run open/insert/save/close for eight cycles and completed 8/8, which
  is evidence that reopening itself works.

## Why it is not a product defect today

`EditorSession` builds a fresh engine per session and disposes it on close, so
the product never reaches a second `open` on one engine.  This is an SDK-level
characterisation; it becomes a product question the moment anything reuses an
engine, and that is the reason it stays on the queue rather than being closed.

## Re-run

```
python3 tools/run_e2_c_search_wedge.py --browser chrome
python3 tools/run_e2_c_search_wedge.py --browser firefox
```
