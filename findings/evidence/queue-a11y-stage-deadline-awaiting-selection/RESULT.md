# Result: the two cores disagree about whether a blank paragraph can be selected

Measured 2026-08-26. Answers [`PREDICTION.md`](PREDICTION.md), which was written
before the shipped core was asked. **All three points held.**

Same recipe, same harness, same fixture cell — finding 046's: click past the end
of a line, break the paragraph, bullet the blank one that appears. The only
difference is the profile.

| | `e2-editor-v8` (product core) | `e2-editor-v10` (a11y core) |
|---|---|---|
| `stage` | **`awaiting-restore`** — got past it | **`awaiting-selection`** — died there |
| `failureShape` | `multi-block-readback` | `stage-deadline:awaiting-selection` |
| `selectionResultSeen` | true | **true** |
| `selectionBeforeResultCount` | 0 | 0 |
| `selectionType` | **1** (`LOK_SELTYPE_TEXT`) | **-1** |
| `selectionTypeReadable` | true | **false** |
| `readback.parsed` | true | **false** |
| `readback.blockCount` / `itemCount` | **2 / 2** | 0 / 0 |
| `readback.bytes` | 592 | **0** |
| `containment` | checked, held, band `[4884, 5548]` | never checked |
| `resultSeen` / `resultSuccess` / `resultModified` | true / false / true | true / false / true |
| disposition the user gets | **review** — queue open, session `ready` | **rollback** — queue blocked, `recoverable-error` |

## What that says

**The action behaves identically on both cores.** `.uno:DefaultBullet` reports
`success: false, wasModified: true` on each — finding 020's known shape, and the
engine already declines to act on either field.

**The barrier's own read does not.** `.uno:SelectText` on the blank paragraph:

* on the product core it selects **two paragraphs** — the blank one and its
  neighbour. That is finding 046's overshoot, measured over 8 cells and 2
  browsers, and it is why the barrier reports `multi-block-readback`.
* on the accessibility core it selects **nothing at all**. The select command's
  own result arrives (`selectionResultSeen: true`) and no selection callback
  carrying rectangles ever does (`selectionBeforeResultCount: 0`,
  `selectionType: -1`).

`maybeAdvanceFormatBarrierSelection()` needs both halves — the result *and*
non-empty rectangles — so the barrier waits out its 5000 ms and calls it a
stall.

## And a withdrawal turns out to have been core-specific

`p1-3b-empty-readback` was **withdrawn on 2026-08-16** with: *"measured: there is
nothing for it to name … NO arm produced a parsed readback with zero blocks"*.
That measurement was taken on a diagnostic profile byte-identical to
`e2-editor-v2` — the **product** core. On the accessibility core the case it was
built for does occur, one stage earlier than it looked for: not an empty
readback, but **no selection to read**. The item's own escape clause said if it
ever occurs, the round-two cell is what would show it. It did.

## Two things NOT established, and the second is ours to fix anyway

1. **Why the cores differ on that command.** The accessibility core is
   `writer calc` WITH accessibility against a writer-only build WITHOUT it —
   **two differences and one measurement**. Naming a layer here would be
   findings 040 and 048's mistake a third time. It is also not obvious which
   behaviour is *right*: not overshooting into the neighbour is arguably the
   better one.

2. **Our barrier has no verdict for "the select ran and selected nothing".**
   That is independent of which core is right, and it is the defect this
   evidence supports fixing: the barrier calls an answer a stall, and the
   disposition attached to a stall is `rollback` — telling the user to discard
   everything since the last checkpoint, over a bullet that had applied, on a
   session that may have no checkpoint at all.

   The engine already emits enough to tell the two apart —
   `selectionResultSeen: true` beside empty rectangles means the engine
   *answered* and the answer was "nothing" — but `productFormatBarrier` in
   `sdk-worker.js` drops that field, so no host can act on it.

---

# Result 2: the fix, measured — and prediction 2 held on all four points

`e2-editor-v11` is `e2-editor-v10`'s artifact repackaged: same wasm
`4ec1e389aaab3b03`, same loader, **only `workerSha256` moves**
(`070229cd10bda4a0` → `03f5b69a002895a9`). No link. The disposition and the
sentence live in the shell (generation **v42**), which is served from `dist/`.

## Three rounds on the accessibility lineage

| round | verdict | `bulleting-…` | sentence recorded | `caret-follows-the-text-you-type` |
|---|---|---|---|---|
| 1 | **37 PASS / 3 NE, `ok: true`** | PASS | `empty-selection` | PASS |
| 2 | 36 PASS / 1 FAIL / 3 NE | PASS | `empty-selection` | FAIL |
| 3 | **37 PASS / 3 NE, `ok: true`** | PASS | `empty-selection` | PASS |

Two of three are **clean runs with no FAIL at all** — the first the accessibility
lineage has ever produced. The one red is the intermittent caret defect filed as
`queue-a11y-caret-does-not-move-on-the-first-commit`, which is unrelated to this
finding and which was invisible until finding 082 was fixed.

## And the shipped product, with the same shell served to it

`e2-editor-v8`, no profile flag, after the shell change:

**38 PASS / 2 NOT_ESTABLISHED, `ok: true`** — the best it has produced. Its
`bulleting-…` still PASSES and still records `unverifiedSentence: "multi-block"`,
so the two cores keep reaching `review` by different routes and the harness keeps
saying which. `servedShell` matches the declared v42 digest
(`dbafd0ec74944791`), so this is the new shell and not a stale copy.

## The prediction, line by line

| predicted | measured |
|---|---|
| `bulleting-…` PASSES on v11: `ready`, queue open, no `請回到檢查點` | **yes, 3 rounds of 3** |
| the toast carries the NEW sentence; the check records `empty-selection` | **yes, 3 of 3** — and v8 still records `multi-block` |
| `notice-action-recovers-the-session` back to NOT_ESTABLISHED, pairing holds | **yes**, `recoveryPairing.held: true` |
| nothing else moves; the paragraph-format arm stays PASS at six of six | **yes** |
