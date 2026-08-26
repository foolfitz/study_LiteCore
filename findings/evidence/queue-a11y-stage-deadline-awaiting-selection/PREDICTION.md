# Prediction, written before the shipped core was asked the same question

Written 2026-08-26, after finding 082 was fixed and
`stage-deadline:awaiting-selection` became the only consistent red on the
accessibility lineage (3 rounds of 3 on `e2-editor-v10`).

## What is already measured, on both cores, same recipe, same harness

The cell is finding 046's: click past the end of a line, break the paragraph,
then bullet the blank one that appears.

| | `e2-editor-v8` (product core) | `e2-editor-v10` (a11y core) |
|---|---|---|
| check | **PASS** | **FAIL** |
| toast | `MUTATION_OUTCOME_UNKNOWN`: *the postcondition read covered more than one paragraph* | `MUTATION_OUTCOME_UNKNOWN`: *the format barrier stopped advancing before it could read the paragraph* |
| shape | `multi-block-readback` | `stage-deadline:awaiting-selection` |
| disposition | **review** — queue open, session `ready` | **rollback** — queue blocked, `recoverable-error` |

And the a11y payload says why the barrier stopped:

```json
{ "stage": "awaiting-selection", "selectionResultSeen": true,
  "selectionBeforeResultCount": 0,
  "selectionType": -1, "selectionTypeReadable": false,
  "resultSeen": true, "resultSuccess": false, "resultModified": true,
  "readback": { "parsed": false, "blockCount": 0, "bytes": 0, "html": "" } }
```

`maybeAdvanceFormatBarrierSelection()` needs **both** halves: the select
command's own result *and* a non-empty `selectionRectangles`. The result
arrived. **The rectangles never did** — `selectionBeforeResultCount: 0` says no
selection callback carrying rectangles reached the barrier at any point.

## The prediction

Run the shipped `e2-editor-v8` with `--barrier-details-diagnostic` and read the
same barrier.

1. On v8 the stage is **past** `awaiting-selection` — `awaiting-restore` — so the
   rectangles did arrive.
2. `readback.parsed: true`, `readback.multiBlock: true`, `blockCount >= 2`, and
   `readback.html` carrying **two** paragraphs: the blank one and a neighbour.
3. Therefore the single distinguishing datum is **whether `.uno:SelectText` on a
   blank paragraph produces a selection at all**: on the product core it does
   (by overshooting into the neighbour, which is finding 046), and on the
   accessibility core it does not.

If that holds, the moral inverts: on the accessibility core the selection is
arguably **more correct** — it does not overshoot — and what fails is our
barrier, which has no way to say "the selection command ran and selected
nothing" and waits out a deadline instead, then prescribes a rollback.

## What would refute it

* v8 also stops at `awaiting-selection` — then the difference is not the core
  and something about the run I have not accounted for is doing it.
* v8's readback is a **single** block — then the overshoot story is wrong and
  `multi-block-readback` on v8 is coming from somewhere else.
* v10's other five paragraph-format arms would also have to be re-read: they all
  PASS there, so `.uno:SelectText` demonstrably works on that core for
  paragraphs **with text**. If a refutation makes that inconsistent, the
  hypothesis was aimed at the wrong layer.

---

# Prediction 2, for the fix — written before `e2-editor-v11` was run

`e2-editor-v11` is `e2-editor-v10`'s artifact repackaged: same wasm
(`4ec1e389aaab3b03`), same loader, **only `workerSha256` differs**
(`070229cd` → `03f5b69a`), and the only change in that worker is that
`productFormatBarrier` forwards `selectionResultSeen`. The disposition that
reads it, and the sentence the user sees, are in the shell — generation **v42**,
served from `dist/`, so they reach v10 and v8 too.

1. `bulleting-a-blank-line-does-not-demand-a-rollback` **PASSES** on v11:
   `state: ready`, the queue stays open, and the toast does **not** say
   `請回到檢查點`.
2. The toast carries the NEW sentence — `取不到任何內容` — not the multi-block
   one, and the check records `unverifiedSentence: "empty-selection"`.
   On `e2-editor-v8` the same check keeps recording `"multi-block"`; that is
   what says the two cores still reach `review` by different routes and the
   product now tells the truth about which.
3. `notice-action-recovers-the-session` therefore goes back to
   **NOT_ESTABLISHED** on v11 — the pair in `finish()` demands it, since the
   cell no longer blocks the queue. On v10 it PASSES because the cell does
   block. **This is a declared cost, not a surprise**: it is the same trade
   recorded on 2026-08-17 when finding 046's disposition was softened on the
   product core, and it means the a11y lineage loses the recovery-path coverage
   it accidentally had.
4. No other check moves. In particular `format-a-paragraph-changes-that-paragraph`
   stays PASS at six arms of six — finding 082's fix is in the wasm and this
   changes no wasm.

**What would refute it**: the check still fails on v11 (the disposition did not
reach the page, or the worker field did not reach the client), or some other
check moves — which would mean the shell change was not as narrow as the three
mutations say it is.
