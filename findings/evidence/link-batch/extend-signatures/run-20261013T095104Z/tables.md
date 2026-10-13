Rounds: 3 (arms-r1.jsonl, arms-r2.jsonl, arms-r3.jsonl).  Window: 1500 ms after the key's KEYINPUT post.
Abbreviations: SEL=TEXT_SELECTION (SEL0 = empty payload), CUR=INVALIDATE_VISIBLE_CURSOR, SS/SE=TEXT_SELECTION_START/END, STATE=STATE_CHANGED, TILES=INVALIDATE_TILES.
`seq` = SEL/CUR/SS/SE callbacks in arrival order; `others` = counts of the other types in the window.
`order` = whether the LAST CUR comes after the LAST SEL.  `last ms` = last SEL/CUR/SS/SE callback / last callback of any type.
Per-round values are joined with `/` when they differ.

## Table 1. Shift+key on every shape

| shape | key | seq | #SEL | #CUR | order | last ms (core / any) | selection changed | others |
|---|---|---|---|---|---|---|---|---|
| caret-mid | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323 | text | STATEx3 |
| caret-mid | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/323 | text | STATEx3 |
| caret-mid | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 324/323/322 | text | STATEx3 |
| caret-mid | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322 | text | STATEx3 |
| caret-mid | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| caret-mid | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| range-fwd | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0 / 322 | text | STATEx1 |
| range-fwd | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 322/323/322 | text | STATEx1 |
| range-fwd | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx1 |
| range-fwd | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx1 |
| range-fwd | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx1 |
| range-fwd | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 321/323/323 | text | STATEx1 |
| range-bwd | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/0/1 / 322/322/323 | text | STATEx1 |
| range-bwd | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 0/1/1 | text | - |
| range-bwd | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/322/323 | text | STATEx1 |
| range-bwd | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 323/323/322 | text | STATEx1 |
| range-bwd | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx1 |
| range-bwd | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 322/321/322 | text | STATEx1 |
| range-one | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 0 / 323/323/322 | text | STATEx3 |
| range-one | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 1 | text | - |
| range-one | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx1 |
| range-one | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx1 |
| range-one | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 322/323/322 | text | STATEx1 |
| range-one | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 322 | text | STATEx1 |
| range-cross | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 1 | text | - |
| range-cross | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 0/1/1 | text | - |
| range-cross | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx1 |
| range-cross | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/0 / 322 | text | STATEx1 |
| range-cross | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx1 |
| range-cross | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 322/321/322 | text | STATEx1 |
| range-kbd | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0 / 622 | text | STATEx1 |
| range-kbd | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0 / 0 | text | - |
| range-kbd | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/0 / 322/323/322 | text | STATEx1 |
| range-kbd | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 322 | text | STATEx1 |
| range-kbd | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0 / 623 | text | STATEx1 |
| range-kbd | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/0/1 / 622/623/623 | text | STATEx1 |
| doc-start | Left | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-start | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx3 |
| doc-start | Up | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-start | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| doc-start | Home | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-start | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/322/321 | text | STATEx3 |
| doc-end | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322 | text | STATEx3 |
| doc-end | Right | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-end | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 765/766/764 | text | CONTEXT_CHANGEDx1,RULER_UPDATEx1,STATEx5 |
| doc-end | Down | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-end | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| doc-end | End | `-` | 0 | 0 | n/a | - / - | none | - |
| empty-para | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/302 | text | STATEx2 |
| empty-para | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 302 | text | STATEx2 |
| empty-para | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx3 |
| empty-para | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx2 |
| empty-para | Home | `-` | 0 | 0 | n/a | - / - | none | - |
| empty-para | End | `-` | 0 | 0 | n/a | - / - | none | - |
| wrap-line-end | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| wrap-line-end | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 323/322/321 | text | STATEx3 |
| wrap-line-end | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| wrap-line-end | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| wrap-line-end | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| wrap-line-end | End | `-` | 0 | 0 | n/a | - / - | none | - |
| cjk-mid | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| cjk-mid | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 323/323/322 | text | STATEx3 |
| cjk-mid | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/321 | text | STATEx7 |
| cjk-mid | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 324/323/322 | text | STATEx9 |
| cjk-mid | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| cjk-mid | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| heading-mid | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| heading-mid | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| heading-mid | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx12 |
| heading-mid | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 766/765/762 | text | CONTEXT_CHANGEDx1,RULER_UPDATEx1,STATEx7 |
| heading-mid | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx3 |
| heading-mid | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/321 | text | STATEx3 |
| list-mid | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 323/322/322 | text | STATEx3 |
| list-mid | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| list-mid | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 767/766/763 | text | CONTEXT_CHANGEDx1,RULER_UPDATEx1,STATEx7 |
| list-mid | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 765/766/764 | text | CONTEXT_CHANGEDx1,RULER_UPDATEx1,STATEx6 |
| list-mid | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx3 |
| list-mid | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/321 | text | STATEx3 |
| cell-end | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| cell-end | Right | `SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 404/404/403 | text | STATEx10 |
| cell-end | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| cell-end | Down | `SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 404/404/401 | text | STATEx10 |
| cell-end | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 321/323/322 | text | STATEx3 |
| cell-end | End | `-` | 0 | 0 | n/a | - / - | none | - |

## Table 2. Plain key on a range (item 3)

| shape | key | seq | #SEL | #CUR | order | last ms (core / any) | selection changed | others |
|---|---|---|---|---|---|---|---|---|
| range-fwd | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 301 | text | STATEx3 |
| range-fwd | Right | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/301/301 | text | STATEx3 |
| range-fwd | Up | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/301/301 | text | STATEx3 |
| range-fwd | Down | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 301 | text | STATEx3 |
| range-fwd | Home | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/0 / 302/302/301 | text | STATEx3 |
| range-fwd | End | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/301/301 | text | STATEx3 |
| range-bwd | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx3 |
| range-bwd | Right | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301 | text | STATEx3 |
| range-bwd | Up | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 301/302/301 | text | STATEx3 |
| range-bwd | Down | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx3 |
| range-bwd | Home | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx3 |
| range-bwd | End | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/302/301 | text | STATEx3 |
| range-cross | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 302/301/301 | text | STATEx3 |
| range-cross | Right | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/302/301 | text | STATEx3 |
| range-cross | Up | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/302/301 | text | STATEx3 |
| range-cross | Down | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx3 |
| range-cross | Home | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 301/302/301 | text | STATEx3 |
| range-cross | End | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 300/301/300 | text | STATEx3 |
| range-kbd | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/0 / 302/301/301 | text | STATEx3 |
| range-kbd | Right | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301 | text | STATEx3 |
| range-kbd | Up | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 301/302/301 | text | STATEx3 |
| range-kbd | Down | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 301 | text | STATEx3 |
| range-kbd | Home | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/302/301 | text | STATEx3 |
| range-kbd | End | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 301 | text | STATEx3 |

## Table 3. Window control (no key)

| arm | callbacks in the 1500 ms window per round | callbacks in the 500 ms before the post | shape settle ms per round |
|---|---|---|---|
| control-caret-mid | [0, 0, 0] | [0, 0, 0] | [809, 809, 810] |
| control-range-fwd | [0, 0, 0] | [0, 0, 0] | [1263, 1263, 1261] |
| control-range-kbd | [0, 0, 0] | [0, 0, 0] | [810, 809, 810] |

## Table 4. Interaction arms (question 7)

| arm | round | pass | selection after the first key | selection after the step | cursor after the step | expected |
|---|---|---|---|---|---|---|
| inter-Shift+Down-a | r1 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Down-a | r2 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Down-a | r3 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Down-b | r1 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Down-b | r2 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Down-b | r3 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Down-c | r1 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Down-c | r2 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Down-c | r3 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+End-a | r1 | PASS | 'TA GAMMA DELTA' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+End-a | r2 | PASS | 'TA GAMMA DELTA' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+End-a | r3 | PASS | 'TA GAMMA DELTA' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+End-b | r1 | PASS | 'TA GAMMA DELTA' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+End-b | r2 | PASS | 'TA GAMMA DELTA' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+End-b | r3 | PASS | 'TA GAMMA DELTA' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+End-c | r1 | PASS | 'TA GAMMA DELTA' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+End-c | r2 | PASS | 'TA GAMMA DELTA' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+End-c | r3 | PASS | 'TA GAMMA DELTA' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Right-a | r1 | PASS | 'T' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Right-a | r2 | PASS | 'T' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Right-a | r3 | PASS | 'T' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Right-b | r1 | PASS | 'T' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Right-b | r2 | PASS | 'T' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Right-b | r3 | PASS | 'T' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Right-c | r1 | PASS | 'T' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Right-c | r2 | PASS | 'T' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Right-c | r3 | PASS | 'T' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |

## Table 5. Findings lists (cells; `rN` = rounds in which it held)

- **last CUR comes AFTER the last SEL** (98): plain-Down@range-bwd [r1,2,3]; plain-Down@range-cross [r1,2,3]; plain-Down@range-fwd [r1,2,3]; plain-Down@range-kbd [r1,2,3]; plain-End@range-bwd [r1,2,3]; plain-End@range-cross [r1,2,3]; plain-End@range-fwd [r1,2,3]; plain-End@range-kbd [r1,2,3]; plain-Home@range-bwd [r1,2,3]; plain-Home@range-cross [r1,2,3]; plain-Home@range-fwd [r1,2,3]; plain-Home@range-kbd [r1,2,3]; plain-Left@range-bwd [r1,2,3]; plain-Left@range-cross [r1,2,3]; plain-Left@range-fwd [r1,2,3]; plain-Left@range-kbd [r1,2,3]; plain-Right@range-bwd [r1,2,3]; plain-Right@range-cross [r1,2,3]; plain-Right@range-fwd [r1,2,3]; plain-Right@range-kbd [r1,2,3]; plain-Up@range-bwd [r1,2,3]; plain-Up@range-cross [r1,2,3]; plain-Up@range-fwd [r1,2,3]; plain-Up@range-kbd [r1,2,3]; shift-Down@caret-mid [r1,2,3]; shift-Down@cell-end [r1,2,3]; shift-Down@cjk-mid [r1,2,3]; shift-Down@doc-start [r1,2,3]; shift-Down@empty-para [r1,2,3]; shift-Down@heading-mid [r1,2,3]; shift-Down@list-mid [r1,2,3]; shift-Down@range-bwd [r1,2,3]; shift-Down@range-cross [r1,2,3]; shift-Down@range-fwd [r1,2,3]; shift-Down@range-kbd [r1,2,3]; shift-Down@range-one [r1,2,3]; shift-Down@wrap-line-end [r1,2,3]; shift-End@caret-mid [r1,2,3]; shift-End@cjk-mid [r1,2,3]; shift-End@doc-start [r1,2,3]; shift-End@heading-mid [r1,2,3]; shift-End@list-mid [r1,2,3]; shift-End@range-bwd [r1,2,3]; shift-End@range-cross [r1,2,3]; shift-End@range-fwd [r1,2,3]; shift-End@range-kbd [r1,2,3]; shift-End@range-one [r1,2,3]; shift-Home@caret-mid [r1,2,3]; shift-Home@cell-end [r1,2,3]; shift-Home@cjk-mid [r1,2,3]; shift-Home@doc-end [r1,2,3]; shift-Home@heading-mid [r1,2,3]; shift-Home@list-mid [r1,2,3]; shift-Home@range-bwd [r1,2,3]; shift-Home@range-cross [r1,2,3]; shift-Home@range-fwd [r1,2,3]; shift-Home@range-kbd [r1,2,3]; shift-Home@range-one [r1,2,3]; shift-Home@wrap-line-end [r1,2,3]; shift-Left@caret-mid [r1,2,3]; shift-Left@cell-end [r1,2,3]; shift-Left@cjk-mid [r1,2,3]; shift-Left@doc-end [r1,2,3]; shift-Left@empty-para [r1,2,3]; shift-Left@heading-mid [r1,2,3]; shift-Left@list-mid [r1,2,3]; shift-Left@range-bwd [r1,2,3]; shift-Left@range-cross [r1,2,3]; shift-Left@range-fwd [r1,2,3]; shift-Left@range-kbd [r1,2,3]; shift-Left@range-one [r1,2,3]; shift-Left@wrap-line-end [r1,2,3]; shift-Right@caret-mid [r1,2,3]; shift-Right@cell-end [r1,2,3]; shift-Right@cjk-mid [r1,2,3]; shift-Right@doc-start [r1,2,3]; shift-Right@empty-para [r1,2,3]; shift-Right@heading-mid [r1,2,3]; shift-Right@list-mid [r1,2,3]; shift-Right@range-bwd [r1,2,3]; shift-Right@range-cross [r1,2,3]; shift-Right@range-fwd [r1,2,3]; shift-Right@range-kbd [r1,2,3]; shift-Right@range-one [r1,2,3]; shift-Right@wrap-line-end [r1,2,3]; shift-Up@caret-mid [r1,2,3]; shift-Up@cell-end [r1,2,3]; shift-Up@cjk-mid [r1,2,3]; shift-Up@doc-end [r1,2,3]; shift-Up@empty-para [r1,2,3]; shift-Up@heading-mid [r1,2,3]; shift-Up@list-mid [r1,2,3]; shift-Up@range-bwd [r1,2,3]; shift-Up@range-cross [r1,2,3]; shift-Up@range-fwd [r1,2,3]; shift-Up@range-kbd [r1,2,3]; shift-Up@range-one [r1,2,3]; shift-Up@wrap-line-end [r1,2,3]
- **last CUR comes BEFORE the last SEL** (0): none
- **more than one SEL** (0): none
- **more than one CUR** (0): none
- **no SEL at all** (10): shift-Down@doc-end [r1,2,3]; shift-End@cell-end [r1,2,3]; shift-End@doc-end [r1,2,3]; shift-End@empty-para [r1,2,3]; shift-End@wrap-line-end [r1,2,3]; shift-Home@doc-start [r1,2,3]; shift-Home@empty-para [r1,2,3]; shift-Left@doc-start [r1,2,3]; shift-Right@doc-end [r1,2,3]; shift-Up@doc-start [r1,2,3]
- **no SEL/CUR/SS/SE at all** (10): shift-Down@doc-end [r1,2,3]; shift-End@cell-end [r1,2,3]; shift-End@doc-end [r1,2,3]; shift-End@empty-para [r1,2,3]; shift-End@wrap-line-end [r1,2,3]; shift-Home@doc-start [r1,2,3]; shift-Home@empty-para [r1,2,3]; shift-Left@doc-start [r1,2,3]; shift-Right@doc-end [r1,2,3]; shift-Up@doc-start [r1,2,3]
- **no callback of any type** (10): shift-Down@doc-end [r1,2,3]; shift-End@cell-end [r1,2,3]; shift-End@doc-end [r1,2,3]; shift-End@empty-para [r1,2,3]; shift-End@wrap-line-end [r1,2,3]; shift-Home@doc-start [r1,2,3]; shift-Home@empty-para [r1,2,3]; shift-Left@doc-start [r1,2,3]; shift-Right@doc-end [r1,2,3]; shift-Up@doc-start [r1,2,3]
- **a SEL/CUR/SS/SE callback later than 300 ms** (0): none
- **INTERMITTENT (core sequence differs between rounds)** (0): none
- **all-types sequence differs between rounds, core sequence identical** (0): none
- **SEL payload kind (empty vs not) differs between rounds, type sequence identical** (0): none
- shape not as expected before the key: none; Shift+Home/End selection not as expected: none; settle cap hit: none

## Table 6. Prediction verdicts

- P-a: HELD; selection text changed in 74 of 84 Shift cells; failing: none; cursor changed but selection text same: none
- P-b: no SEL/CUR/SS/SE in the four edge cells: HELD; no callback of any type: HELD
  - shift-Left@doc-start: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-Right@doc-end: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-Up@doc-start: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-Down@doc-end: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-Home@doc-start: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-End@doc-end: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
- P-c: HELD; cell shift-Left@range-one: {'coreSeqPerRound': ['SEL0 CUR', 'SEL0 CUR', 'SEL0 CUR'], 'selPayloadsPerRound': [[''], [''], ['']], 'selBefore': ['B', 'B', 'B'], 'selAfter': ['', '', '']}
- P-d: HELD; interaction arms per round 9; failing: none
