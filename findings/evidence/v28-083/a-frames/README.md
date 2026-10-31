# Spec v28 append 2: the fallback's selection and html read next to a frame (2026-10-31)

L-fallback-html-read-is-new-on-this-path (spec 9). The owner chose to measure it. Tool `wasm_sdk_probe/tools/check_v82_frame_last_line.py` (S4 imported, not edited), fixtures `build-01/` (native core, read through the instrument first). Criteria pinned in spec section 14 append 2, committed `8a4f14de3` before the counted run. Local mirror, no DDEV.

## run-01 (generation 82, v28; Chrome and Firefox x3): **A_FRAMES_HOLD** (30/30)

| cell | result (6/6 each) |
|---|---|
| `frame-para-last` image anchored to the empty last paragraph | `verified-format-readback`; fallback TEXT, 2 blocks, last `ul`/`p`, restore confirmed; frame kept; marker in a bullet list |
| `textbox-para-last` text box anchored there | the same |
| `prev-aschar-image` previous paragraph ends in an as-char image | the same |
| `prev-note-frame` previous paragraph ends in a note whose body has an as-char image (038's shape) | the same |
| `frame-char-last` image anchored at a character of the empty last paragraph | never reaches the fallback: the primary read is COMPLEX, 037's guard answers `selection-type-not-readable` (typed reply, `recoverable-error`) |

No wedge anywhere. Every press answered; no false "verified": the saved paragraph is a bullet in every verified run; the frame count is preserved.

**`frame-char-last` predates v28** (`before-frame-char-last/`, generation 81, 6/6 the same shape). Not this batch's defect, and not a wedge, but it is what a user sees on such a paragraph: the toast shows the code and the English sentence plus 「可能已經改到文件：請回到檢查點」, and the notice says the engine must reopen. Named here L-char-anchored-frame-refuses-the-format-press. It is finding 037's guard.

**Positive control** (`control-swallow-press/`): with the bullet request held back from the worker, both browsers read as a wedge (`a.replied`, `b.ready`, `c.typed` red): `A_FRAMES_CONTROL_RED_AS_WANTED`.

`self-test-01.json`: ALL_RED, 35 mutations.

The first smoke (not counted) found the `frame-char-last` path, which the first draft of the criteria had not foreseen; item 3a was pinned before the counted run.
