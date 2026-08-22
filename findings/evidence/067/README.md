# Finding 067 — a real Enter advances the revision and changes nothing

`real-enter-does-nothing.json`, from
`probe_064_format_reaches_typing.py --browser chrome --arms real-enter`, on
artifact `29ec627b`, shell **v26** (finding 066 already fixed, which is what made
this askable at all).

A **real** key through CDP `Input.dispatchKeyEvent`, for the same reason finding
066 needed a real click: only a real key runs the default action that produces
`beforeinput` with `inputType: "insertParagraph"`.

| | |
|---|---|
| focus when the key was sent | `{id: "sink", tag: "TEXTAREA"}` — on the editing surface, not a button |
| typing before the Enter | revision `0 → 1`, text in the document |
| **the Enter** | revision **`1 → 2`** |
| paragraphs before / after | **9 / 9** |
| `content.xml` before vs after | **byte-identical** |
| typing after the Enter (control) | revision `2 → 3`, `ENTAFTER` in the document |
| toast | the save toast only — no error, no warning |

The control is what makes the rest readable: the keyboard is demonstrably
working on both sides of the key that did nothing. The operator's 2026-08-21
round hit the same wall but could not tell "Enter is dead" from "the keyboard is
dead", because finding 066 had focus parked on a toolbar button throughout.

**The revision moving is the sharp part.** This is not a refusal — nothing
refused. The product's own progress counter advanced, so every surface that
reads it believes an edit happened.


## `engine-route-and-which-key.json` — two more facts, 2026-08-22

The page's `onInputTrace` already receives the whole commit result; nothing
forwards it anywhere a probe can see. A mirror records it (one file, one added
line, inert without `globalThis.__f067`).

### The engine took its `paste` route and reported success

```json
{"label": "commit-end", "requestNumber": 1, "result": {"method": "paste", "revision": 2}}
```

`method: "paste"` means LOK's `paste("text/plain;charset=utf-8", "\n", 1)`
**returned true**. The engine did **not** fall back to `postKeyEvent`. So the
story is not "paste refused it": **paste accepted a bare newline and did nothing
with it**, and `handleInsertText` then incremented the revision unconditionally.
That is the engine half of 067, now attributed rather than open.

### Plain Enter and Shift+Enter cannot be told apart

| key | `inputType` at the commit boundary |
|---|---|
| Enter | `insertLineBreak` |
| Shift+Enter | `insertLineBreak` |

`distinguishable: false`. The sink is a `<textarea>`, and a textarea reports
Enter as `insertLineBreak`; `insertParagraph` is what a **contenteditable**
reports, so the adapter's `insertParagraph` branch is **dead code on this
page**.

This is a design fact, not a defect: any fix that decides at
`commit(text, metadata)` can offer **one** of the two breaks from the keyboard,
not both, unless `shiftKey` is captured somewhere else.

### A trap this cost twice

The first version of this arm read `entry.action` looking for `commit-end` and
found nothing, then reported "the Enter never reached the commit boundary" —
the opposite of the truth. `eventSnapshot()` puts the trace **label** in
`type`; `action` only exists when a caller passed it in `extra`. And
`commit-end` is traced with a **null event**, so it carries no `inputType` of
its own — the two have to be paired by `requestNumber`.
