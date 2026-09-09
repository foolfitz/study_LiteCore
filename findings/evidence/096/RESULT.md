# 096 — RESULT: all three profiles die, and so does the page from before 093

Measured 2026-09-09 against
`handoff/tasks/TASK-2026-09-09-096-which-profiles-kill-the-session.md`
(commit `a0f098b5`, registered before the probe was written). The protocol's
outcome table was written before any counted attempt; this document reads it
back rather than composing a new one.

**The verdict cell is `R(A) ∧ R(B) ∧ R(C)`.** The protocol says that licenses:
*"Like finding 086: present on shipping too, not a candidate regression. The
disposition question becomes 'how long has this been here', not 'does the
cutover carry it'."* It also says it does **not** license "the page is
innocent", and requires arm D. Arm D was run, and it reproduces too.

## The matrix — every attempt, not only the ones that reproduced

| arm | page sha256 | probe.wasm | up | down |
| --- | --- | --- | --- | --- |
| **A — `e2-editor-v13`** (candidate) | `31787584290e42bd…` | `0fe25650bec1bac5` | **5/5** | **5/5** |
| **B — `e2-editor-v12`** | `db2ed393f3433e2e…` | `4ec1e389aaab3b03` | **5/5** | **5/5** |
| **C — `e2-editor-v8`** (**the shipped bytes**) | `1ec7baf9fb53c808…` | `4a2710bba1ef07d9` | **5/5** | **5/5** |
| **D — pre-093 page on the shipped engine** | `df5f3b6c7dde0b2e…` | `4a2710bba1ef07d9` | **5/5** | **5/5** |

**40 attempts, 40 REPRODUCED, 0 NOT_REPRODUCED, 0 DIED_WITH_CHECKPOINT, 0 VOID.**
Nothing was intermittent; there is no attempt that behaved differently and no
attempt is being left out.

Every attempt reached the same numbers: the boundary press is press **2**, seven
presses are spent, the scroll room is 2903 px (so the document was longer than
the viewport in all forty), and the wait from the boundary press to the verdict
was 12.0 s of polling after the loop.

Arm A's page sha256 is exactly the number banked in
`findings/evidence/manual-round-v13-31787584/notes-owner-T4.md` before the
owner's round. Arm C's page is byte-identical to `dist/e2-editor-app.js`.

## Did the harness reproduce what the owner saw? Yes, to the sentence.

The owner's words were:

> 走到最上面再按上：**會掛掉！**狀態變成「處理中」，不久跳出「引擎需要重新開啟。
> 沒有檢查點，所以自上次儲存以來的內容不會回來。」提示

In all forty attempts the state pill went `ready → busy` on the boundary press
and the notice that appeared carried, character for character:

```
引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。
```

`noticeMatchesOwnerQuote: true` in every attempt, and it is banked as evidence
rather than used as the predicate — the predicate is the product's own decision
fields, `data-state` and `data-rescue: "none"`. The verdict state was
`recoverable-error` in all forty; `restart-required` and `expired` never
occurred.

## The engine side — the raw payload

`#s-latency`, the state ball and the toast are the page's observations. These
are not.

**1. What the SDK's own error object said**, rendered by `run()` as
`${code}：${message}`:

```
上移一行：TIMEOUT：editorActionV2 timed out after 30000 ms（可能已經改到文件：請回到檢查點）
下移一行：TIMEOUT：editorActionV2 timed out after 30000 ms（可能已經改到文件：請回到檢查點）
```

Six of these per attempt — one for the boundary press and one for each press
that queued behind it.

**2. The transition trace, with page timestamps.** One attempt from each arm:

| arm | `busy` at | dead at | delta |
| --- | --- | --- | --- |
| v8 | 11223 ms | 41225 ms | **30002 ms** |
| v12 | 11286 ms | 41289 ms | **30003 ms** |
| v13 | 11238 ms | 41241 ms | **30003 ms** |

The session does not fail; it waits out the SDK's 30 s deadline to the
millisecond and is then blocked. `pending` climbs 1, 2, 3, 4, 5, 6 across the
presses that follow — the queue fills behind one operation that never returns.
`revision` stays `0` throughout: nothing was written.

**3. Nothing crashed.** Across all forty attempts there is no
`Inspector.targetCrashed`, no `Target.targetCrashed`, no
`Runtime.exceptionThrown` on the page or on the worker, and the page's own
`window.onerror` / `unhandledrejection` boxes are empty:
`{"errors": [], "rejections": []}`. The one `Target.detachedFromTarget` per
attempt is the boot worker being replaced when the document opens, and it
happens ~2 s *before* the gesture.

**4. The document worker's own console** carried exactly two lines per attempt,
both from boot and both before the gesture:

```
Thread name: "configmgrWriter"
Thread name: "lo_startmain"
```

Nothing at all at the moment of the boundary press.

**5. The worker's JavaScript thread is alive.** After the verdict, one
`Runtime.evaluate` addressed to the live worker's own CDP session answered in
**0.0 s** in every attempt:

```json
{"now": 37420, "post": "function", "onmsg": "object"}
```

So "the worker's JS thread is blocked" is excluded: the worker is running its
event loop and answering. What did not answer is behind it. **This document
stops here** — the protocol forbids naming a cause, and 040's precedent is that
a confident wrong attribution costs more than the open question.

## What this does and does not license

**Licensed by the registered table:**

- The defect is **present on the shipped `e2-editor-v8`**, at the same rate
  (10/10) and with the same engine-side payload as on the candidate. **It is
  not a candidate regression** and it is not something the v13 link introduced.
- Arm D adds: **the page change is not necessary either.** The page as it stood
  before 093's page half (`18eefcce`), on the shipping engine, dies 10/10 with
  the same notice.

**Not licensed, and stated so that nobody reads it in:**

- **No cause is named.** Not the v13 link, not 093 option B, not the
  accessibility core, not `boundaryRejectionRequiresFreshWorker` (which all
  three manifests declare `true` — that is a declaration, not a measurement).
- **How long it has been there** is not measured. Four artifacts is not a
  bisect; the earliest artifact tested here is `e2-editor-v8`.
- **The two other things the owner recorded stay separate** — the viewport not
  following the caret, and the caret not following the browse cursor. Finding
  096 registers them as possibly-separate and this measurement gives no reason
  to merge them.
- **Whether the disposition restarts the soak count is not decided here.** The
  gate document's line 31 and the fact that T4 is condition 3's round belong to
  whoever adjudicates; a drafter must not declare it (AGENTS.md §8).

## Two things worth writing down

**The severity is worse than "the session dies", and the product says so
itself.** The notice is the no-checkpoint variant, `data-rescue: "none"`,
`#s-checkpoint` reading 無, and the button says 重新開啟 rather than
回到檢查點. There is no recovery offered other than starting again. Every
attempt here had an unmodified document, so nothing was actually lost; a user
who has typed for an hour and then presses Up at the top of the page loses the
hour. **It costs no edit to trigger** — no save, no format, no typing; the
document had `revision: 0` and one arrow key was enough.

**The 30-second wall is the whole latency.** The user presses a key, gets 30
seconds of 「處理中」, and then loses the session. That is what the owner
described as 「不久跳出」.

## Instrument limitations, named

1. **The keys are injected at the renderer** by `Input.dispatchKeyEvent`, not
   typed on a physical keyboard through the compositor. This is as close to the
   user's path as this harness gets, and it reproduced the owner's sentence
   exactly, so the gap did not matter here — but it is not zero.
2. **The session had no history.** The owner had done the whole of T4 §3.1–3.6
   in the same page before they walked with the arrows. These attempts open a
   document and press an arrow. That the defect reproduces *without* a history
   is a stronger result, not a weaker one, but the two are not the same
   scenario.
3. **`workerLiveness` accumulates stale sessions.** Detached worker sessions are
   removed from the map when Chrome sends `Target.detachedFromTarget`, but
   sessions from earlier attempts in the same browser linger and answer
   `Session with given id not found`. The list therefore reads
   `[False, …, False, True]`, and **the last entry is the live worker**. Every
   attempt's live worker answered. Recorded rather than tidied, because a
   reader of the raw JSON will see the `False`s.
4. **Headless Chrome, 1920x1080, one machine, one document.** No claim is made
   about other geometries, browsers or documents.

## Incidental, recorded and NOT merged

On the down arm the caret was placed at `sinkTop` 3142 in a `#desk` whose
`clientHeight` is 864 and whose `scrollTop` was **0** — i.e. the caret sat far
below the visible band and the viewport had not moved to it. That is the shape
of the owner's separate 「畫面沒有跟著」 note. **It is not measured here**: this
probe places the caret deliberately deep in the document and never asked the
page to follow it, so this number is compatible with several explanations and
supports none of them. It is written down only so that a later measurement
knows the observation is present in this data too.
