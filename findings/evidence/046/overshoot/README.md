# 046 — the overshoot is about the paragraph being empty, not about the caret being at an edge

Criteria in `PREDICTION.md`, registered before the harness existed.  Judged by
`tools/analyze_f046_overshoot.py`; self-test 9/9.  **Evidence class:
diagnostic** — the runner was given `--diagnostic-round <reason>` and the reason
is stamped in every `result.json`.

Two rounds (Chrome, Firefox), eight cells each, on the **frozen** engine: the
diagnostic profile's `probe.wasm` is byte-identical to `e2-editor-v2`.

## The question, and why it mattered

Finding 034 replaced the barrier's old two-command selection because it escaped
to a neighbour **whenever the caret already sat at a paragraph edge**.  An empty
paragraph is one where the caret is at both edges at once.  So the overshoot
measured on the empty paragraph had two candidate scopes:

| scope | who it hits |
|---|---|
| empty paragraphs only | someone bulleting a blank line |
| any caret at a paragraph end | someone who clicks at the end of a line and presses the bullet button |

## The answer: `EMPTY-PARAGRAPH-ONLY`

| cell | caret | blocks | outcome |
|---|---|---|---|
| `text-mid` (control) | mid-text | 1 | succeeds |
| `text-start` | left edge | 1 | succeeds |
| **`text-end`** | **past the last character** (x 3578, beyond the text) | **1** | **succeeds** |
| `empty-mid` | the empty paragraph | **2** | `multi-block-readback` |
| `isolated-mid` | mid-text, non-list neighbours | 1 | succeeds |
| `isolated-end` | past the last character (x 5304) | 1 | succeeds |
| `between-mid` | a paragraph between two lists | 1 | succeeds |
| `bullet-one-mid` | inside an existing list item | 1 | succeeds |

Identical in both browsers.  All six predictions **held**, including P-OV-3's
premise: the caret in the two `-end` cells really did land past the text, so
those cells tested an edge rather than accidentally testing the middle again.

**Only the empty paragraph overshoots.**  The everyday gesture — click at the
end of a line, press the bullet button — is fine.

## What that settles

- The defect stays a **non-blocking** queue item.  It is real, and it refuses a
  mutation that succeeded, but it needs a blank line to happen.
- **Containment cannot catch it**, confirmed on every overshooting cell
  (`held: true` throughout): it asks whether the selection covers the caret,
  never whether it covers **only** the caret's paragraph.  A fix has to compare
  the read against the paragraph the action was dispatched on, not against the
  caret.

## What is still not measured

Named rather than quietly left out — these are variants the registered cells did
not cover:

- an empty paragraph followed by **another empty paragraph**;
- an empty paragraph followed by a **list item** (would the read then show
  `itemCount >= 2` — the combination finding 046 originally inferred?);
- an empty paragraph at the **end of the document** — measured in the readback
  round and it does not even reach a readback
  (`stage-deadline:awaiting-selection`), which is a different path;
- anything outside these two fixtures.

## Reproducing

```
python3 tools/run_e2_c_d0.py --browser chrome --profile e2-readback-diagnostic \
  --page e2-c-046-overshoot.html --namespace __f046_overshoot \
  --diagnostic-round "<why>" --output <new dir>
python3 tools/analyze_f046_overshoot.py <run dirs> --output verdict.json
python3 tools/analyze_f046_overshoot.py --self-test <run dirs>
```
