# The saved ODT crosses both ways on `9b29e39b…` (shell generation v48) — revert condition 2, re-taken

**2026-09-07.** `tools/probe_odt_roundtrip.py --candidate e2-editor-v12`.
Report: `odt-roundtrip-v12-9b29e39b.json`. Task T2 of
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`.

The `20f09cc9…` take (`RESULT-the-saved-odt-crosses-both-ways.md`, beside this
file) is the immediately preceding one; that page moved twice more since
(finding 088's second fix, then the T1d mistake and its v48 correction — see
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, "The page is final"),
so the condition is re-earned here rather than carried forward. The earlier
take is left where it is, unedited.

## Identity

| | |
|---|---|
| candidate profile | `e2-editor-v12` |
| candidate page | `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c` |
| shipped page | `df5f3b6c7dde0b2eb463733975763ba70a5000f8f1345442d59109b153f85143` |
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
profile: 13,713 bytes — the same byte counts as the `20f09cc9…` take, which is
expected: the round trip exercises the ODT save/load path, not the live-region
projection that moved between these two pages.

**Revert condition 2 is satisfied on the current page.**

## Not affected by this task's other reds

Items 1-3 of this T2 pass recorded a reproducible FAIL
(`the-document-region-says-why-it-is-empty`) on plain and diagnostic runs of
this same page (`findings/evidence/queue-v12-cutover-soak/RUNS.md`,
`../gate-4a-on-9b29e39b/RESULT-4a.md`). This probe does not touch that
mechanism — it never reads the accessibility live region or the AX tree, only
the save/open/reopen sequence and the reopened document's text content — and
its own result is unambiguously clean on both legs. Recorded so a reader does
not conflate the two.
