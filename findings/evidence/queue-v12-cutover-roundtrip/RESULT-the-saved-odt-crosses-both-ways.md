# The saved ODT crosses both ways on `20f09cc9…` — revert condition 2, re-taken

**2026-09-06.** `tools/probe_odt_roundtrip.py --candidate e2-editor-v12`.
Report: `odt-roundtrip-v12-20f09cc9.json`.

The 2026-08-28 take satisfied this condition on the unsplit `e2-editor-v11` and
on a page the human round of 2026-09-04 has since moved. The candidate is now
`e2-editor-v12` and the page is `20f09cc9…`, so the condition is re-earned here
rather than carried forward. See
`../queue-v11-cutover-soak-not-started/RESULT-2026-08-28-the-saved-odt-crosses-both-ways.md`
for the original, unedited.

## Identity

| | |
|---|---|
| candidate profile | `e2-editor-v12` |
| candidate page | `20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95` — the sha the ten banked soak runs carry |
| shipped page | `5aeae0e1dbfe492d7de478962ac15bffd22aa6cfcdeea89737f529b6aa8d2de7` |
| pins | before `4a2710bba1ef07d9`, after `4ec1e389aaab3b03` |
| sentinel | `ROUNDTRIP-SENTINEL` |

## Result — `ok: true`, both directions

| | candidate → shipped | shipped → candidate |
|---|---|---|
| document actually in front of the page | `from-candidate.odt` | `from-shipped.odt` |
| state | ready | ready |
| re-opened file is an ODT | **true** | **true** |
| sentinel survived | **true** | **true** |
| the six fixture lines | all present, including `E1-LC-BULLET-TWO 中文項目` | all present |

Saved on the candidate: 13,024 bytes, sentinel present. Saved on the shipped
profile: 13,713 bytes.

**Revert condition 2 is satisfied on the current page.**

## The 2026-08-28 guard earned its place again

That round's failure was a probe that waited for `state == "ready"` and got it
instantly, because the page was already ready with the **boot fixture** still
loaded — a false cross-version incompatibility, the most expensive kind of
wrong result. The fix was to record *which document is in front of you* beside
*are you ready*.

It matters here. In the shipped → candidate direction the toast is
`點一下放游標，或拖曳選一段，再按動作`, not `已開啟 from-shipped.odt`: the caret
hint has already replaced the open notice by the time the probe reads it. A
check written against the toast would have been ambiguous. `doc:
"from-shipped.odt"` is unambiguous, and it is what the report is judged on.
