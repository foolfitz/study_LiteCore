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
