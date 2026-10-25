# Conditional exact asynchronous Escape fallback

This is a staged alternative, **not established and not active**. The synchronous Q candidate is measured first in DELETE and FORMAT. If Q establishes the needed restoration, do not run this fallback merely to expand coverage. If Q fails or cannot be established for DELETE, adjudicate that result and activate this finite fallback with a separate output directory. FORMAT does not inherit the fallback; its known Escape limitation remains.

The shared versioned native harness contains two operations to avoid a second owner compilation:

- `F5122` runs K1 Shift+Left, reads its selection synchronously, and calls `postUnoCommand(".uno:Escape", nullptr, false)` **within the same runOp and poll**. The record includes `k1AtReturn` and `escapeNotify:false`.
- Immediately following `Gbefore|1283` runs under `uni1f`. Before posting Backspace, it reads selection and the cached cursor and requires NONE, empty text, and equality with the recorded pre-K1 cursor rectangle. If any prerequisite fails it records `guardPassed:false,keyPosted:false` and does not send the key. It records the guard read and requested key independently.

Every op records `pollIndex`. A counted fallback must show G's index exactly F's index plus one. There is no quiet window, sleep or fixed delay between them: the uni1f micro-steps are adjacent and F is not the final operation, so its returned settle is empty. The X trigger and its setup settle precede F; F, not X, is the measured command start. Any same-poll, skipped-poll or stabilized sequence is not evidence for the exact fallback.

The predeclared population is three original P2 fixtures (plain, numbered, first-line-indented), each with direct Backspace, `F5122;Gbefore|1283`, and a wrong-point guard `F5122;Gwrong|1283`, in uni1f, N=5: 45 processes. Direct Backspace supplies the same saved shape/locator/undo reference as the Q cohort. The candidate must establish all prerequisites, actually send Backspace, and match direct landing and undo. The wrong-point guard must refuse without sending the key. K1 must read separator TEXT. Exact timing, content, subsequent Shift behavior, provenance and non-vacuity are separate required observations; an elapsed-time threshold cannot replace any of them.

The binary instrumentation is prepared now. A dedicated fallback runner/reader and its red controls must be completed before activating this staged cohort; they are not claimed ready by this document. No additional native compilation should be necessary. If never activated, the fallback remains `NOT_ESTABLISHED` and no engine path may use it. A failed pre-K1 caret restoration is a failed prerequisite, not permission to send a key at the current caret or to insert another wait.
