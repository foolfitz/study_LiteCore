# Operator report, 2026-09-03 — 標題 on an ordinary paragraph of a real document

Found during the v12 cutover gate's manual round (condition 3), by the operator,
on their own document. Both arms are the operator's own keystrokes in a real
browser; nothing here came through the harness.

**Document**: `/home/jiajun/Documents/SLAT/e20-專訪瓦特老師.odt`,
sha256 `63bf89cb5d7eb891…`, 35 paragraphs, **no two paragraphs share their text**
(checked in code over `content.xml`).

**Paragraph acted on**: index 4, beginning 「在那之前，我的資訊能力…」 — an
ordinary body paragraph with text in it, not empty, not a heading, not a list
item.

**Action**: press the product's own 標題 button.

## Arm 1 — the candidate, `e2-editor-v12`, page `3dfdcfef…`

```json
{"notice":"這一步可能已經改到文件，而且無法驗證。回到選取手勢前的檢查點。",
 "toast":"標題：MUTATION_OUTCOME_UNKNOWN：the postcondition read describes a different paragraph from the one this action was dispatched on, so it says nothing about whether the action took effect（可能已經改到文件：請回到檢查點）",
 "state":"recoverable-error","rev":"1","checkpoint":"有（r1）","pending":"0",
 "latency":"標題 失敗","doc":"e20-專訪瓦特老師.odt"}
```

Failure shape: **`readback-is-a-different-paragraph`** — the fingerprint
comparison. Prescription: **rollback**, and a checkpoint existed.

## Arm 2 — the shipped profile, `e2-editor-v8`, page `28e03e5b…`

```json
{"notice":"引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。",
 "toast":"標題：MUTATION_OUTCOME_UNKNOWN：the paragraph selected for the postcondition read does not cover the caret this action was dispatched from（可能已經改到文件：請回到檢查點）",
 "state":"recoverable-error","latency":"標題 失敗","rev":"0"}
```

Failure shape: **`selection-does-not-contain-restore-point`** — the containment
check, which sits *before* the fingerprint comparison in the barrier's verdict
path. Prescription: **restart**, and there was no checkpoint.

## What the two arms establish, and what they do not

**Established: this is not a cutover regression.** The same ordinary action on
the same paragraph of the same document fails on the profile that ships today
and on the candidate. The pre-written revert trigger "any user-visible
regression reported by a human" does not fire on it.

**Established: the failure shapes differ**, and the barrier's own verdict order
explains why. `selection-does-not-contain-restore-point` is checked before
`readback-is-a-different-paragraph`. The incumbent stops at the first; the
candidate gets past it and stops at the second. Both report
`MUTATION_OUTCOME_UNKNOWN`, which is the barrier being honest: it does not
claim the action failed, it says it cannot tell.

**NOT established: that the candidate handles it better.** The candidate arm
had a checkpoint and the incumbent arm did not — but the two runs had different
histories. The operator had already typed on the candidate (`rev: 1`, so an
edit had been committed and a checkpoint taken) and had not typed on the
incumbent (`rev: 0`). **The checkpoint difference is explained by the edit
history and not by the profile**, and a comparison that quoted it as a profile
difference would be measuring one thing and signing for another. A clean
comparison needs both arms at the same revision.

## Why the regression net never saw this

`format-a-paragraph-changes-that-paragraph` PASSES on all eight banked soak runs
and on the shipped profile's runs. It drives `set-paragraph-heading` on
`E1-LC-ISOLATED` in `list-contexts.odt` — a **nine-paragraph synthetic fixture**
whose paragraphs are short and structurally simple.

The operator's document is 35 paragraphs of real prose, several hundred
characters each. Nothing in the corpus is shaped like it. **The net is green
because the corpus cannot produce the state the defect needs**, which is not the
net being wrong — it is the corpus being a corpus.

This is the third time this tree has recorded the same shape: the harness's path
is not the user's path, and the user is the only observer that does not share
the harness's instruments.
