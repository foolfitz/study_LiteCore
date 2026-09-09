# The saved ODT crosses both ways on `31787584…` (candidate `e2-editor-v13`) — revert condition 2, re-taken

**2026-09-09.** `tools/probe_odt_roundtrip.py --candidate e2-editor-v13`.
Report: `odt-roundtrip-v13-31787584.json`.

The `9b29e39b…` take (`RESULT-the-saved-odt-crosses-both-ways-on-9b29e39b.md`,
beside this file) is the immediately preceding one. Finding 093 option B was
linked today, the candidate became `e2-editor-v13` and the candidate page moved
to `31787584…`, so everything bound to `9b29e39b…` is void and the condition is
re-earned here. The earlier takes are left where they are, unedited.

## Identity

| | |
|---|---|
| candidate profile | `e2-editor-v13` |
| candidate page | `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a` |
| shipped page | `1ec7baf9fb53c808cf127476346d69d56cf93a802f6c72680fa84416f7599ecc` |
| pins | before `4a2710bba1ef07d9`, after `0fe25650bec1bac5` |
| sentinel | `ROUNDTRIP-SENTINEL` |

The shipping page still points at `e2-editor-v8`; the probe builds the
candidate page in a mirror and never writes it into the tree.
`git status --short` after the run shows only this report and the 4a evidence
directory, both untracked additions.

## Result — `ok: true`, both directions

| | candidate → shipped | shipped → candidate |
|---|---|---|
| document actually in front of the page | `from-candidate.odt` | `from-shipped.odt` |
| dispatch | dispatched | dispatched |
| state | ready | ready |
| re-opened file is an ODT | **true** | **true** |
| sentinel survived | **true** | **true** |
| the six fixture lines | all present, including `E1-LC-BULLET-TWO 中文項目` | all present |

Saved on the candidate: **13,026 bytes**, sentinel present. Saved on the
shipped profile: **13,713 bytes**.

**Revert condition 2 is satisfied on the current page.**

## One number moved, and it is recorded rather than rounded away

The candidate-side save is **13,026** bytes here against **13,024** on both the
`9b29e39b…` and `20f09cc9…` takes — two bytes larger. The shipped side is
13,713 on all three, unchanged. The candidate is a different linked artifact
today (`e2-editor-v13`, finding 093 option B), so a two-byte difference in what
its save path emits is not surprising in the way an unchanged binary emitting
different bytes would be; it is noted because the two earlier takes both quoted
13,024 as a stable value and a future reader comparing against them should not
read the difference as instrument drift. **Not investigated here** — the
condition is about whether the document crosses, and it crosses.

## Not affected by anything else measured today

This probe never reads the accessibility live region, the AX tree, or the
structure projection: only save, open in the other profile, reopen, and the
reopened document's text. Condition 4a's records
(`../gate-4a-on-31787584/`) are independent measurements taken in a separate
browser session, one at a time.
