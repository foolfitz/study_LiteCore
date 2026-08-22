# Finding 066, after the fix — shell v26 (2026-08-22)

The shipped `dist/` tree with the `mousedown` listener in place, artifact
`29ec627b` unchanged, shell bundle **v26** (`b25b6c29d1e74012…`).

| | Chrome | Firefox |
|---|---|---|
| `ok` | **true** | **true** |
| `the-toolbar-gives-the-keyboard-back` | **PASS** | **NOT_ESTABLISHED** |

Firefox abstaining is the design, not a gap being papered over: the check needs a
**real** mouse click, `HTMLElement.click()` runs no default action and so never
moves focus, and only CDP can deliver one. A synthetic press would pass this
check on a page where the defect is present — which is exactly how finding 066
survived until an operator hit it — so on a browser that cannot deliver a real
click the check says it measured nothing.

Chrome's record: `afterButtonClick` is `{id: "sink"}`, the text typed straight
afterwards with **nothing restoring focus** reaches the document (revision
`48 → 49`), and the marker is in the saved ODT.

`mutation-focus-detected.json` is the round that proves the check can fail:
reverting the two lines (`--mutate focus`) turns it red, and **only** it — the
declared `alsoRed: []` is measured, not asserted.

`probe-focus-after-toolbar.json` is the diagnostic probe's own arm, which went
from FAIL to PASS across the same change; before the fix `MKNOFOCUS` never
reached the document, after it, it does.

The before-picture is one directory up: `../focus-and-forced-click.json`.


## `keyboard-formats-all-four.json` — the operator's question, answered

The second manual round was going to ask whether italic, underline and
strikethrough reach text typed on the **keyboard**; only bold had ever been
tried by hand, and the shipped inline-format check drives the "insert text"
field (`session.commitText`), which never touches a key.

With 066 fixed that arm can be automated, and it is the user's path on both
ends: a **real** click through CDP for every button press, and typing through
`#sink`'s `beforeinput` with **nothing restoring focus**.

| format | outcome | focus after the press | style on the marker |
|---|---|---|---|
| bold | **PASS** | `sink` | `span T1`, `bold: true` |
| italic | **PASS** | `sink` | `span T1`, `italic: true` |
| underline | **PASS** | `sink` | `span T1`, `underline: true` |
| strikethrough | **PASS** | `sink` | `span T1`, `strikethrough: true` |

Each arm gets its own paragraph, its own `clear-format` (the caret carries
formats forward, so without it each arm would inherit the one before), and its
own save. A marker that never reached the document reports NOT_ESTABLISHED
rather than "no format" — the question has no answer if the text is not there.

**Before the fix this arm could not have run at all**: the real click parked the
keyboard on the button and nothing typed afterwards reached the document, which
is exactly what "styles apply sometimes, mostly not" was.
