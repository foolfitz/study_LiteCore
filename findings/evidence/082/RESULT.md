# Result: the gate was refusing a correct mutation, and the fix let the lineage be measured

Measured 2026-08-26. Answers
[`PREDICTION-which-paragraph-was-read.md`](PREDICTION-which-paragraph-was-read.md)
(**refuted**),
[`PREDICTION-2-why-the-two-fingerprints-differ.md`](PREDICTION-2-why-the-two-fingerprints-differ.md)
(**held**), and the prediction in
`handoff/RUNBOOK-relink-v10-a11y-identity.md` (**held, all five points**).

## 1. It was not a different paragraph

Widening the worker's `productFormatBarrier` allowlist in a mirror — the engine
already sends more than the product keeps — put the whole barrier object in the
report. On the failing `內文` arm of `e2-editor-v9`:

```json
{ "stage": "awaiting-restore", "command": ".uno:StyleApply",
  "expectedStyles": ["Body Text"],
  "resultSuccess": true, "resultModified": true,
  "readback": { "parsed": true, "blockCount": 1, "blockTag": "p",
                "html": "… <p>E1-LC-HEADING</p> …" },
  "containment": { "checked": true, "held": true,
                   "selectionTop": 1418, "selectionBottom": 1693,
                   "restoreCentre": 1625 } }
```

The readback described **the paragraph the action was dispatched on**, and it is
a `<p>` — the style change had landed. The engine's own result callback agrees.
So the first prediction (stale restore geometry landing in the next paragraph)
was wrong, and the finding had to be rewritten rather than extended.

## 2. It was the fingerprint, and the fingerprint was the empty string

The trace of `editorState.caretParagraph` on every state transition
(`product-path-v9-paragraph-trace.json`, 66 rows). Every distinct reading:

| n | listPrefixLength | contentLength | fingerprint | text |
|---:|---:|---:|---|---|
| 13 | 0 | 25 | `d389fc99dd9a78cf` | `E1-LC-ISOLATED 前後都不是清單的段落` |
| 9 | 0 | 20 | `76f09d751bb341f7` | `E1-LC-END甲一乙二丙三插入鈕標記` |
| 3 | 2 | 22 | `76f09d751bb341f7` | `• E1-LC-END甲一乙二丙三插入鈕標記` |
| **7** | **13** | **13** | **`cbf29ce484222325`** | **`E1-LC-HEADING`** |
| **3** | **2** | **2** | **`cbf29ce484222325`** | **`• `** |
| 3 | 3 | 19 | `d0586a07b98862c6` | `1. E1-LC-NUMBER-ONE` |

Two things at once:

* **The stripping works.** A paragraph and the same paragraph with a bullet in
  front of it report ONE fingerprint (`76f09d751bb341f7`). That is why the
  slice exists and it must not be taken away.
* **A thirteen-character heading and an empty bulleted paragraph are the same
  number**, and that number is `cbf29ce484222325` — the FNV-1a 64 offset basis,
  the value that means *nothing was hashed*. `listPrefixLength == contentLength`
  on both: finding 074, upstream, `getListPrefixSize()` returning the end of the
  first ATTRIBUTE RUN rather than the length of a numbering prefix.

So the barrier compared a degenerate value against a real one and concluded "a
different paragraph". `MUTATION_OUTCOME_UNKNOWN` is in `RECOVERY_ERRORS`, so the
queue blocked and the session went to `recoverable-error` **with no
checkpoint** — the state whose notice tells the user their unsaved work is gone.
Over a paragraph format that had worked.

## 3. The fix, and what it does not do

The gate now **declines** the comparison when either end's fingerprint is
degenerate, instead of failing it. Rule and hash live together in
`src/a11y_paragraph_identity.hpp`; `tests/a11y_paragraph_identity_test.cpp`
drives them on the host and reproduces six fingerprints the engine really
reported, so it is a cross-implementation check. Four mutations of the rule are
each detected.

It does **not** fix finding 074 (upstream), and it does not make the fingerprint
usable as an identity in general — 22% of the r7-compat corpus collides on text
alone (`queue-a11y-prefix-swallows-the-paragraph`).

## 4. `e2-editor-v10`, one variable against v9

`what_the_link_ships.py --variant a11y --since c82a642`: three translation units
preprocess identically, `sdk-worker.js` byte-identical, every
`probe_engine.cpp` hunk belonging to this finding, `configurationDrift: []`.
The manifests differ in `wasmSha256` and `loaderSha256` and nothing else; same
21 actions, same gestures, `select-all` present-but-empty on both.

| | v9 | v10 |
|---|---|---|
| wasm | `b60cc46fcc6bf572` | `4ec1e389aaab3b03` |
| loader | — | `96f18d0c1f6b9b11` |
| worker | `070229cd10bda4a0` | `070229cd10bda4a0` |
| manifest | — | `d57de339939bfbc9` |

## 5. The measurement, against the prediction written before it

| predicted | measured |
|---|---|
| the run does not stop; 40 of 40 recorded | **`sessionDied: null`**, 40 checks |
| `set-paragraph-body` PASSES | **PASS** — and so do all six arms of that check |
| no `readback-is-a-different-paragraph` anywhere | **none**; one barrier failure remains and it is the other shape |
| `bulleting-a-blank-line…` still red with `stage-deadline:awaiting-selection` | **still red, that shape** |
| `notice-action-recovers-the-session` keeps passing | **PASS**, and `recoveryPairing.held: true` |

`format-a-paragraph-changes-that-paragraph`: **PASS**, six arms of six —
`set-paragraph-heading`, `set-paragraph-body`, `set-list-unordered`,
`set-list-ordered` and both `set-list-none`. On v9 this check never got past its
second arm, four runs out of four.

Whole run: **35 PASS / 2 FAIL / 3 NOT_ESTABLISHED**.

**Three rounds of three**, and the fix is the stable part of them:

| round | verdict | format arm | `caret-follows-the-text-you-type` |
|---|---|---|---|
| 1 | 35 PASS / 2 FAIL / 3 NE | **PASS**, 6 arms of 6 | **FAIL** |
| 2 | 37 PASS / 1 FAIL / 2 NE | **PASS**, 6 arms of 6 | PASS |
| 3 | 37 PASS / 1 FAIL / 2 NE | **PASS**, 6 arms of 6 | PASS |

No round stopped early, no round produced a
`readback-is-a-different-paragraph`, and the one page error in every round is
the same `stage-deadline:awaiting-selection` on the bulleting cell — the other
defect, untouched, as predicted.

### The one remaining barrier failure reads correctly now

```json
{ "failureShape": "stage-deadline:awaiting-selection",
  "paragraphIdentity": { "checked": false, "dispatchKnown": true,
                         "readbackKnown": false,
                         "dispatchUsable": false, "readbackUsable": false,
                         "declined": "" } }
```

`dispatchUsable: false` is the new field doing its job: that barrier was
dispatched on the paragraph holding only `• `, whose fingerprint is the
degenerate one. `declined: ""` beside `checked: false` means the barrier ended
**before the identity gate was reached** — the stage deadline fired first. The
empty string is readable only next to `checked`; a later link should make it say
so in words.

## 6. What the fix bought, and it is the point

**The 23 checks after the seventeenth got their first reading on this lineage**,
and one of them is red: `caret-follows-the-text-you-type`.

```
round 0  leftBefore 163 -> leftAfter 163   revisionAdvanced: true   moved: false
round 1  leftBefore 163 -> leftAfter 393   revisionAdvanced: true   moved: true
round 2  leftBefore 393 -> leftAfter 509   revisionAdvanced: true   moved: true
```

The text reached the document all three times; the caret did not move on the
**first** one. And it is **intermittent**: rounds 2 and 3 moved on all three.
1 of 3.

That is a new observation, it is not this finding's, and it is filed as
`queue-a11y-caret-does-not-move-on-the-first-commit` rather than written up —
one round out of three inside one check is exactly the shape this tree has been
fooled by before. It could not have been seen at all while the session was dying
at check 17, which is the point.
