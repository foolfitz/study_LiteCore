# Finding 066 — the toolbar takes the keyboard and never gives it back

`focus-and-forced-click.json`, produced by
`wasm_sdk_probe/tools/probe_064_format_reaches_typing.py --browser chrome
--arms focus-after-toolbar,click-between-format-and-typing` on artifact
`29ec627b`, shell v25.

Reported by an operator on 2026-08-22 ("after pressing a style button the focus
stays on the button", "styles apply sometimes, mostly not, no pattern I can
see"). Both halves measured the same day.

## Arm 1 — `focus-after-toolbar` (FAIL)

A **real** click, delivered through CDP `Input.dispatchMouseEvent` so that the
default action runs. `HTMLElement.click()` would not do: it dispatches the event
without running the default action, so it does not move focus, and the whole
defect would be invisible.

| | |
|---|---|
| focus after a canvas click | `{id: "sink", tag: "TEXTAREA"}` — the positive control: focus does reach the editing surface |
| focus after the **button** click | `{tag: "BUTTON", action: "set-bold"}` |
| typing with focus untouched | dispatched to `BUTTON`; revision `1 → 1`; `MKNOFOCUS` **not in the document** |
| typing with focus restored | dispatched to `sink`; revision `1 → 2`; `MKREFOCUS` **in the document** |

The second typing step is the arm's positive control, and it is what makes the
first one readable: the same dispatch, differing only by `sink.focus()`, does
reach the document. Without it, "typing did nothing" and "the probe types
wrongly" would look identical.

## Arm 2 — `click-between-format-and-typing` (FAIL)

One variable: whether the canvas is clicked between the format press and the
typing — the click being the only thing that returns the keyboard to the text.

| | marker | result |
|---|---|---|
| type straight after the press | `MKNOCLICK` | **bold true**, `carrier: span`, `T1` |
| click the canvas first, then type | `MKAFTERCLICK` | **bold false**, `carrier: paragraph`, `P2` |

The first arm is the control: it shows the format does reach typed text on this
build, so the second arm's failure is the click and nothing else.

## Read with the fixed oracle

Both arms ran **after** `inline_styles_of()` was corrected on 2026-08-22 to
resolve paragraph-level formatting (`fromParagraphStyle` is in the records).
Findings 064 and 065 were retracted because they were read with the broken
version; this one is not exposed to that, and arm 1 does not use the ODF oracle
at all — it reads `document.activeElement`.
