# The second link — the fix worked, and it uncovered a platform difference

Artifact `d538ce0b91478426…` (linked 2026-08-17, the second attempt), shell v12
`98a8dc48…`, Firefox.  The first attempt (`4dbe9b74…`) is archived and its
measurement is in [`../after-link-v3/`](../after-link-v3/).

| prediction | outcome |
|---|---|
| **D-BI-1** (answer under 200 ms) | **FAILED** — 251 ms |
| **D-BI-1, substance** (bounded, not 30 s) | **HELD** |
| **D-BI-2** (the paragraph datum is live) | **FAILED** — for a new reason |
| **D-BI-3 control** (no false positive) | **HELD** |
| **D-BI-3 empty** (the new shape fires) | **FAILED** — no input to fire on |

## What the second link bought

Not a fix — a **located** problem, said by the engine instead of inferred by me.

The first attempt failed silently: every paragraph hashed to the empty string,
and I had to work backwards from that to "accessibility is off".  This time the
engine answers the question directly:

```json
{"enabled": true, "unavailable": "", "paragraphFresh": true,
 "changeCount": 0, "unparsedCount": 0, "observed": false,
 "contentLength": 0, "paragraphFingerprint": "cbf29ce484222325"}
```

Accessibility **is** on and no capability guard refused; **this** synchronous
read succeeded; and **not one `A11Y_FOCUS_CHANGED` callback has ever arrived**,
parsed or otherwise.  Three different questions, three separate answers — which
is exactly what the observability change was for.

## The native control refuted my own hypothesis

The tree had a comment saying accessibility must be re-attached "so the snapshot
reflects that selection instead of an early empty focus", so I expected the fix
to be "enable later".  `native-attach-timing/captures.jsonl` (core 26.8, the
product's exact sequence) says otherwise:

| moment | `content` | `position` |
|---|---|---|
| enabled at open, before any caret exists | **`BI-ANCHOR-ONE`** | 0 |
| after paint | `BI-ANCHOR-ONE` | 0 |
| after the first click | `BI-ANCHOR-ONE` | **5** |
| after re-attaching | `BI-ANCHOR-ONE` | 5 |
| after the second click | **`BI-AFTER-EMPTY`** | 5 |

Populated at the earliest possible moment, and re-attaching changes nothing.
**It is not a timing problem**, and it was cheaper to find that out here than by
spending a third link on it — which is the step that was skipped before the
second one.

Filed as [finding 056](../../../056-accessibility-produces-no-focused-paragraph-under-wasm.md).
Where inside core the two diverge is **not** established and is not guessed
(findings 040 and 048 are the precedents).

## What does work, and is worth the link on its own

| click | elapsed | how |
|---|---|---|
| first, far below the text | **38 ms** | callback |
| second, same point | **251 ms** | deadline readback |
| third, same point | **251 ms** | deadline readback |

`editorPlaceCaretV2` answers a click that changes nothing.  That half does not
depend on the paragraph datum, and it replaces the thirty-second wait finding
052's residual was made of.  **D-BI-1 fails by 51 ms and stays failed**: the
appendix written before the first link says the deadline is 250 ms and that the
threshold would not be moved to make the prediction pass.

## One more thing this run exposed

The empty-paragraph cell reports:

```json
"paragraphIdentity": {"checked": false, "dispatchKnown": true, "readbackKnown": true}
```

Both reads were available and the check still says it did not run — because
`multi-block-readback` returns before it.  The two flags are consistent, but
`checked` reads as "the data was missing" when it means "something else answered
first".  A field that can be read two ways is a field that will be.  Queued to
set it where the data becomes known rather than in the verdict path.

## Not established here

* **Anything about Chrome.**  Firefox only.
* **Why the two platforms differ.**  Named as the open question, not answered.
* **That the barrier comparison is well-behaved.**  Its control passes, but with
  every fingerprint equal the comparison cannot fire either way, so the control
  is not yet evidence about it.
