# Handoff — 2026-08-19: the checklist went green, and it cost two relinks

> Entry point. Reading this page is enough to take over.
> Previous: `HANDOFF-2026-08-18-predicate-and-disposition.md`.
> The plan this day started from: `PLAN-2026-08-18-usable-editor-autonomous.md`.
>
> **English by decision of 2026-08-19** (`AGENTS.md`): the only reader of a
> handoff is the next agent. `devlog/`, `research/`, `specs/` stay zh-TW.
>
> The filename says "every row has a check". That was true by mid-afternoon and
> is now an understatement; the name is kept because other files link to it.

## 0. Bindings

| | |
|---|---|
| artifact | **`29ec627bf8a5588b…`** — relinked **twice** today (`d538ce0b…` → `296f3ea7…` → `29ec627b…`); all archived under `build/archive/` |
| shell | **v25 `07143f961d82c4b3…`** (v17 → v25; the builder mints one generation per shell change and refuses to reuse one) |
| matrix | `e2/validation-matrix-v2.json`, **D0 still not run** |
| checklist | **13 done / 1 partial / 0 unverified / 0 missing / 2 blocked** |
| `KNOWN_RED` | **empty** — a first for this tree |
| queue | 45 items, **`P1 complete: True`**, nothing blocking |
| product path | 22 checks, 21 PASS, 1 NOT_ESTABLISHED |

Everything above reconciles: `check_usable_editor.py --report`,
`check_relink_queue.py` and `audit_product_path_coverage.py` are green, and every
tool's self-test passes.

## 1. What shipped

**Two relinks, both authorised by the user after the evidence was complete.**
Every engine change is guarded by `OXSDK_E2_FORMAT_BARRIER`, so the frozen
`e1-editor` profiles keep the exact behaviour E1-C validated at their hash.

**Relink 1 — `296f3ea7`**

* **finding 059** — the engine stops gating the four inline formats on core's
  `success`. That field was measured *anti-correlated* with the request being
  honoured: `success: true` appeared on exactly the two arms where core ignored
  the argument and toggled. It now calls `inlineFormatArgumentResolved()` —
  observed state against requested state, with `…Known` required so "I don't
  know" can never read as "yes".
* **finding 062's second half** — `handlePaintTile` re-reads `getDocumentSize`
  and reports it on the reply, so a document that grew a page is no longer drawn
  at the size it had when it was opened.

**Relink 2 — `29ec627b`**

* Underline and strikethrough reach `editorState.format`, so the toolbar and the
  new keyboard shortcuts can toggle them **off** as well as on. They were always
  in core's `GetKitUnoCommandList` and always broadcast; nobody had written the
  cache, and a comment in the engine asserting the opposite was the reason.

**Shell-side, no link:** finding 061 (the notice takes `recoveryNotice()`'s
three-way decision), finding 063 (a refused cut no longer bricks the session and
no longer swallows its error), finding 062's first half (tiles split at 32,767),
Ctrl+B/I/U, and the paragraph range arm.

## 2. Findings filed today

| | |
|---|---|
| **061** | A failed checkpoint save was reported to the user as "there was never a checkpoint". **Fixed.** Fixing it also retired finding 054's cause — both came from the page re-deriving a decision the shell already makes. |
| **062** | A long document drawn as a blank page, in silence. **Both halves fixed** — the page renders in strips, the engine reports the document size. The engine limit itself (an unpainted buffer above 32,767 px, reported as success) is *still there*; the product routes around it. |
| **063** | A refused cut told the user to discard their work. **Fixed.** |

## 3. What is left

| | |
|---|---|
| **`cut` (partial)** | Cut is **effectively copy**: `delete-backward` is declared caret-only and a cut is always a range, so the delete half is refused every time. `queue-cut-cannot-remove-text` — the fix is to *measure* range delete and then declare it, not to widen the manifest first. No link needed. |
| **`redo`, `move-by-line` (blocked)** | Need wire ids. That is an ABI change and a third relink, and it changes the *contract* rather than an implementation — ask before starting. |
| **Clipboard** | Automation proves the product hands the selection to the engine without error. It does **not** prove what landed on the clipboard. Cheap next step: a `navigator.clipboard.readText()` round-trip inside the page (permission is already granted). Only a human can settle the OS boundary, the permission prompt and a real Ctrl+V — and that round is worth more *after* cut can actually delete. |
| **Recovery's second inducer** | Coverage is still tied to finding 038 staying broken (`queue-recovery-inducer-depends-on-an-unfixed-defect`). The check reports NOT_ESTABLISHED and names 038 rather than passing quietly, which is why this is a debt and not a hole. |
| **D0** | Still not run. Once it is, moving the shell means changing the matrix. |

15 queue items remain open; none blocks a link.

## 4. The four traps that cost time today

These are the reusable part. Each cost at least a round.

**A probe that sweeps a parameter in one session carries state between its
arms.** I concluded finding 062 was page-side, committed it, and was wrong. The
probe swept canvas heights *ascending* in one engine session, so the first render
was always under the limit and painted, and every over-limit arm came back
carrying content — which exonerated the engine. One render per page load returns
an unpainted buffer every time. **Ascending order is exactly what hides a
cold-start limit.** Recorded in `probe-measurement-discipline`.

**The worker's replies are allowlists — and I hit it twice.** The engine started
reporting the document size on the paint reply and every client saw nothing,
because `sdk-worker.js` names the fields it forwards. Then the engine started
reporting underline state and the product saw `null`, for the same reason, the
same afternoon. The file's own comment says this is how `itemCount` came to be
"measured natively and reported nowhere". **An engine field nobody forwards does
not exist.**

**A path can be unreachable rather than untested, and it looks green.** The cut
check passed for weeks while only ever exercising one branch: WebDriver denied
the clipboard, so the copy failed, so the delete never ran. Granting the
permission (*and* emulating focus — `writeText` needs both) made the delete run
for the first time and immediately surfaced finding 063.

**A duplicated id silently swallows edits.** Two queue items shared an id; my
update hit the first, and the second went on blocking a link for work that had
shipped. `check_relink_queue.py` now catches it, and the shell-bundle builder
now catches a path listed as both included and excluded — which happened the same
day, when the page began importing `recovery-notice.js` and its stale exclusion
came along for the ride.

## 5. Do not repeat

* **Do not compare wording in an oracle.** The recovery check used to assert the
  notice's sentence; a rephrase would have made it green with the defect intact.
  It now asserts that the two surfaces — status pill and notice — *agree*, via
  `#notice[data-rescue]`.
* **Do not widen a check to close a row.** Ctrl+A was removed and the row's
  sentence changed instead, because the geometric substitute was measured
  selecting nothing. A shortcut that looks like it worked is worse than none.
* **Do not trust a checklist note.** The `format-a-paragraph` note said range
  gestures were blocked by the gesture mask. They were not — that mask is on the
  four inline formats. Nothing was blocking it; nothing had driven it.
* **Do not name a layer without measuring it** (040, 048, and 062 again today).
* **Iterating on the page mints a shell generation each time.** Verify page
  changes with a standalone probe first, then mint one generation.
* **`make e2-c-assets` after every `web/` or `sdk/` edit.** The bundle builder
  compares source against the `dist/` copy and will tell you — but only if you
  run it.
