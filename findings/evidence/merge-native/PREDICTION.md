# Paragraph merge, native — predictions (written 2026-10-06, before the first run)

Probe `wasm_sdk_probe/tools/merge_native_boundaries.cpp`, runner `tools/run_merge_native.sh`, fixture `wasm_sdk_probe/test-docs/merge/boundaries.fodt`, native LibreOffice 26.8 (`native-lok-26-8`), `SAL_USE_VCLPLUGIN=svp`, 3 rounds. Owner's request (2026-10-06): make a delete at a paragraph boundary merge the paragraphs instead of being refused (finding 109's option C).

Per case: arm **select** = Shift+Left/Right (the barrier's one-unit selection), readback (type, code points, rectangles), then `.uno:SwBackspace` / `.uno:Delete` on that selection, save, `.uno:Undo`, save; arm **key** = Backspace / Delete on the collapsed caret, save. The key arm is the reference: what Writer does for the user's own key.

Written as a guess so that a wrong one is visible. "Unknown" is a prediction that I do not know, not a hedge.

| Case | Boundary | Unit selection (prediction) | select = key? | Undo restores? |
|---|---|---|---|---|
| C01, C02 | body\|body | text, one code point U+000A (LF), rectangles unknown (1 or 2) | yes | yes |
| C03 | body\|numbered heading, Backspace at the heading's start | as C01 | **no**: the key removes the heading's number first (Writer's Backspace at a numbered paragraph's start), the select arm merges | yes |
| C04, C05 | numbered heading\|body | as C01 | yes (the merged paragraph keeps the heading) | yes |
| C06 | body\|empty | as C01 | yes | yes |
| C07 | empty\|body, Backspace | as C01 | yes, possibly differing in which paragraph's style survives — unknown | yes |
| C08 | body\|bullet item, Delete | as C01 | yes | yes |
| C09, C11 | Backspace at a bullet item's start | as C01 | **no**: the key removes the bullet / list membership first | yes |
| C10, C12 | bullet item\|bullet item, bullet item\|body, Delete | as C01 | yes | yes |
| C13 | bullet item\|body, Backspace | as C01 | yes | yes |
| C14 | Backspace at a numbered item's start | as C01 | **no**, as C09 | yes |
| C15 | body\|table, Delete | unknown: the selection may enter the first cell; text may still be one LF, which would make it indistinguishable from C01 by text alone | **unknown**; Writer's key probably does nothing | yes |
| C16 | table\|body, Backspace | unknown, as C15 | unknown | yes |
| C17 | cell\|cell, Delete at a cell's end | none (the selection stays in the cell) or a table selection | key does nothing | — |
| C19, C20 | body\|body carrying a paragraph-anchored frame | as C01 | yes; the frame stays anchored to the merged paragraph | yes |
| C21, C22 | body\|body with a page break before | as C01 | yes; whether the break survives on the merged paragraph is unknown | yes |
| C23, C24 | body\|section | unknown | unknown | yes |
| C25, C26 | section\|body | unknown | unknown | yes |
| C27, C28 | line break inside a paragraph | text, one code point U+000A — **indistinguishable from a paragraph separator by text** | yes | yes |
| C29 | document start, Backspace | none; nothing dispatched | key does nothing | — |
| C30 | document end, Delete | none; nothing dispatched | key does nothing | — |

What decides the design: whether the cases that must stay refused (tables, sections if they differ, the list/number cases where the key does something other than merge) can be told apart from the plain ones by what the barrier can see before dispatch (type, code points, rectangle count and geometry). If they cannot, the barrier needs another readback, or the page has to keep the refusal for them.
