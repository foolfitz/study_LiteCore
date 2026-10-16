# v21 WASM shakedown: results

Arms: `ARMS.md`, `ARMS-item1.md` (rulings §8), `ARMS-item2.md` (rulings §9), committed at `8f1dbf0a`. Those files are not edited after that commit; corrections are appended **here** and say what they replace.

**State (2026-10-17 03:00):**

- Phase B is built.
- One Chrome smoke has run per item: `smoke/item1/`, `smoke/item2/`. The smokes are development runs and are not judged.
- **No evidence run has started.**
- Two diagnostics are running: `diag-dirty-move/` and `diag-long-paragraph/`.

## 1. Rulings after the smoke (main session, 2026-10-17, before any evidence run)

Each ruling names the smoke observation that forced it. None moves a threshold in spec §11.

| # | ruling | forced by | replaces |
|---|---|---|---|
| S1 | **D4: the place-caret request may be `click` or `editorPlaceCaretV2`.** On an open range, the session's place-caret goes out as `click` (`narrow-editor-v2-session.js:734-737`, v67's path). The judge's `DEVIATION-D4-op` line is accepted, and the clause reads "one place-caret request, then the move". | item-1 smoke D4, 6/6 `click` | `ARMS-item1.md` D4's op name |
| S2 | **R-xlc's population is the `x-lc` arms whose script has a Backspace step** (3 arms). The group label alone gives 4. Record arm; no verdict. | item-1 smoke | `ARMS-item1.md` R-xlc "group x-lc" |
| S3 | **M5 is judged on the spec's wording: 0 requests and 0 connection attempts to the item's target hosts.** Targets are every `scheme://host:port` written in the item's bytes, plus the target-port listeners. An item with no URL has no target, so its M5 cell is its refusal. Every other non-mirror request is **recorded** with its host and window, not judged. The positive controls (`probe.wasm` and `/m5-control` in the **proxy's** log) stay required. | item-2 smoke M5: Chrome's own GCM/Google traffic fell in 6 of 38 item windows despite the quieting flags; a policy that stops it needs root | `ARMS-item2.md` M5 "0 requests to any origin other than the mirror's", which was the draft's stronger reading, not spec §11 M5 「對目標主機 0 個請求」 |
| S4 | **M4 placement on round-2 positions is confirmed by either of two checks.** (i) The engine caret equals the native `cursorAtPaste` rectangle. (ii) The after-paste signature equals the native `after.fodt.gz` of the same arm (DM-11 A's rule). Check (ii) reads the document instead of a coordinate, which fonts move on WASM (finding 113). A cell with neither is NOT_ESTABLISHED. | item-2 smoke `M4-T2-ccplain-M2`: caret 17 twips right of native; paste and Undo correct | `ARMS-item2.md` M4 "confirmed by the engine caret equal to the native `cursorAtPaste` rectangle" for round-2 positions |
| S5 | **M6 runs alone in a fresh browser**, as `ARMS-item2.md` M6 already says; the smoke's in-sequence M6 was runner fault R4. A paste the SDK gives up on after 30 s busy reads **FAIL** (the busy span exceeds the 10 s bound), not NOT_ESTABLISHED (judge fault J1, fixed). | item-2 smoke M6 | — |
| S6 | **`v21_input.key` mis-sends `#$%&'(` in Chrome** (as End, Home and the arrows: the character code used as a key code). No item-1 arm types them, so it is recorded, not fixed. Any arm that types them must use the clipboard instrument or a fixed key. | item-2 agent | — |

The judge changes that S3 and S5 need are execution-driven (§34.4): the witness is the smoke report that the old reading misjudged.

## 2. Product observations from the smokes (not verdicts; under diagnosis)

1. **D8 (e), item 1: a move key pressed while a delete is out takes the click-then-move range path.** The barrier's one-character range is read as the user's. A key pressed meanwhile is queued between the click and the move, so it runs at the click point: P2 «Bra scond» instead of «Bra second». [observed: smoke item 1]
   - Source: `web/e2-editor-app.js` `sendDocumentMove` (about line 3330) and the arrows' path (about line 3194) decide the shape without `deletesInFlight === 0`. Finding 131's rule A (`deleteActionFor`, about line 2787), the overlay (132) and the reopen caret (136) all apply that check. [source]
   - The arrows' path is 0.2.24 code, so the gap may predate v21. Measured in `diag-dirty-move/` V6.
2. **In a dirty document, the first Ctrl+Home/End's reply carries the pre-move caret.** The session sends a checkpoint `save` first. The move then completes `verified-move-readback` about 251 ms after its request, with the caret where it was before the move. An engine read later shows the caret at the target.
   - Seen in item-1 smoke D11b-dirty (reply `1564,1418`, later `3657,1970`), D6, and D8 (e). [observed]
   - Clean documents answer `documented-callback-*` in 33–50 ms. [observed: D7]
   - This is the shape of L-142-readback-overtaken (spec §9.1). That limit is registered as a stall case. Here it appears every time after a checkpoint save, and D7's population (clean documents) cannot see it.
   - Whether typed text then lands at the old caret: `diag-dirty-move/` V1–V4.
3. **A 65,536-byte single CJK paragraph pasted as Markdown crashes the WASM worker** (`memory access out of bounds`). Direct to the worker it gets no reply. A 64 KiB corpus of short sections pastes fine. [observed: item-2 smoke and dev-r1]
   - M3's size arms say both complete.
   - The link rules set a 64 KiB pthread stack (`-sDEFAULT_PTHREAD_STACK_SIZE=65536`, `Makefile:483`). [source] That this is the cause is a hypothesis. [inferred]
   - Diagnosed in `diag-long-paragraph/`.
4. **M6's 64 KiB corpus took 32 s in a long browser session and 0.66 s on a fresh page.** [observed: item-2 smoke] Open.
5. **D6's `Z`, typed 3 ms after the Markdown dialog closed, produced no `beforeinput`.** It may be harness timing. Measured in `diag-dirty-move/` V5.
6. **The foreign load during the smokes**:
   - another session's Python script at 99.5 %;
   - the owner's desktop Chrome with an extension relay at 66–126 %;
   - Zen at 60 %.
   
   These made 6 D7 presses, one D9 sub-arm and D10 NOT_ESTABLISHED. [observed: the samples in the item-1 smoke report] The evidence runs need a quiet desk.
