# Finding 046's residual — the disposition, not the verdict

Measured 2026-08-17. Shell **v14** `d1f49e170f0d511b…`, artifact `d538ce0b…`
(unchanged — this is a shell-only change), Firefox, driven through the product
page's own buttons by `tools/run_e2_c_product_path.py`.

## What changed, stated narrowly

| | before | after |
|---|---|---|
| the barrier declines to say which paragraph it read | yes | **yes, unchanged** |
| the session after a blank-line bullet | `recoverable-error`, queue blocked | **`ready`, queue open** |
| what the product tells the user | roll back to the checkpoint | dispatched, unverified, check it and undo if wrong |
| the error code the host receives | `MUTATION_OUTCOME_UNKNOWN` | **`MUTATION_OUTCOME_UNKNOWN`, unchanged** |

The verdict was never the defect. The barrier is right that a two-paragraph
read cannot describe one paragraph. What was wrong is that this got translated
into "discard everything since the checkpoint" for an edit that had in fact
applied — pressing the bullet button on a blank line.

`recovery` gains a fourth value, `review` (SPEC E2-C 2.6b, written in the same
shell generation because a host-facing enum value is contract surface).

## The measurement

[`product-path-shell-v14.json`](product-path-shell-v14.json) —
`bulleting-a-blank-line-does-not-demand-a-rollback`:

```json
{"state": "ready", "queueStillOpen": true}
```

[`product-path-mutation-review-disposition.json`](product-path-mutation-review-disposition.json) —
the same cell with the sentinel disabled:

```json
{"state": "recoverable-error", "queueStillOpen": false}
```

Detected. The check can fail, against the behaviour that shipped until today.

## The first attempt, kept because it is the finding

[`product-path-first-attempt-message-only.json`](product-path-first-attempt-message-only.json)
is the run where the fix was "make `_blockQueueIfDispatched` decline to block".
**The message changed and the session blocked anyway** — `state:
recoverable-error` alongside the new review text.

Declining to block is not enough: the frozen base class blocks on the error
*code*. `editor-shell/editor-session.js:20` lists `MUTATION_OUTCOME_UNKNOWN` in
`RECOVERY_ERRORS`, reached at `:325`. That file is hash-registered by E1-C and
cannot be edited. Reading the code would have said the fix was complete; running
it said otherwise.

## How it is actually done

The base class only reaches that decision when the operation **rejects** —
`item.reject(error)` at `:316` runs first, and the block is a side effect keyed
on the code afterwards. So the enqueued operation *resolves* with a sentinel and
the original error is rethrown outside the drain
(`editor-shell-v2/narrow-editor-v2-session.js`). The caller sees the same error
object with the same code, plus `recovery: "review"`.

**It revokes itself.** The sentinel carries no `state`, so the drain's success
path takes its fallback at `:301-302` and asks the engine for one. If the engine
is wedged that call raises `TIMEOUT`, which **is** in `RECOVERY_ERRORS`, and the
queue blocks after all. The softening only holds while the engine can show it is
alive. This was not designed in; it falls out of the frozen plumbing, and it is
the reason this shape is safe to soften at all.

## Not established, and one thing actively disclaimed

* **That the bullet applied.** The barrier could not verify it and neither does
  this check. Saying otherwise is the claim finding 046 was filed against. What
  is checked is the disposition.
* **A blank line at the END of the document.** Measured previously: it does not
  reach a readback at all (`stage-deadline:awaiting-selection`, a different
  path — see [`../overshoot/README.md`](../overshoot/README.md)) and still maps
  to rollback. Do not describe this change as "bulleting a blank line no longer
  demands a rollback": for the commonest blank line — the one you are typing on
  at the end of the document — that sentence is false.
* **Verify-block[0] was rejected, not deferred.** The existing evidence shows
  the target first and already carrying the requested state, but that is one
  engine run over one cell shape, read post-hoc; two browsers are not two
  measurements of a core-selection claim. Counterexample to the guarded form: an
  upward overshoot whose neighbour above is already bulleted and whose action
  failed presents exactly one block in the target state, at index 0, and the
  guard certifies a failure. The sound version — verify by quantifier, all
  blocks or no blocks — is queued as engine-side work
  (`queue-quantifier-check-for-multi-block-readback`).

## The cost, measured in both directions

This cell was the **only** route this runner had into `recoverable-error`, so
keeping the queue open costs `notice-action-recovers-the-session` its inducer;
it now reports `NOT_ESTABLISHED`. The mutation run shows the pair moving
together — sentinel off, this check red and the recovery check `PASS` again.

The recovery path is not broken and is not covered. A new inducer is owed and is
queued (`queue-recovery-path-lost-its-inducer`).

Adjudicated by an external reviewer (fable, 2026-08-17), which rejected both of
the approaches tried here first: invalidating the drain strands the session in
`busy`, and substituting the error code makes the host-observed code diverge
from what the engine emitted.
