## Instrument checks
- arms read: 273 over rounds [1, 2, 3]; fatal arms: 0
- arms whose selection read-back differs from the expectation (shapes ['m1d', 'm1e', 'm1r', 's1d', 's1e', 's5'] excluded, their expectation is unknown): 0
- arms where the final text does not contain exactly one '#': 0
- wrap offset found by `discover-s1` per round: {1: 101, 2: 101, 3: 101}
  - discover-s1 round 1: cursor at start `1418, 1418, 0, 276`; after 100 Rights `10961, 1418, 0, 276`; after 101 Rights `1418, 1694, 0, 276`
    line 1 ends with `...ike november oscar papa `
  - discover-s1 round 2: cursor at start `1418, 1418, 0, 276`; after 100 Rights `10961, 1418, 0, 276`; after 101 Rights `1418, 1694, 0, 276`
    line 1 ends with `...ike november oscar papa `
  - discover-s1 round 3: cursor at start `1418, 1418, 0, 276`; after 100 Rights `10961, 1418, 0, 276`; after 101 Rights `1418, 1694, 0, 276`
    line 1 ends with `...ike november oscar papa `

## The ref arms on the old fixture against `round-20261012T020528Z/arms.jsonl`
- 36 of 36 (arm, round) pairs give exactly the old round's text (12 arms x 3 rounds; none when this folder has no old-fixture arms)

## ref vs emu (whole-document text after the key and '#'; index = position of '#' in that text)

### p2-forward
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 43, `LPHA BETA GAMM<#>A DELTA⏎P3 thi` | 43, `LPHA BETA GAMM<#>A DELTA⏎P3 thi` | same | 3992,1694 / 3992,1694 | 3 |
| Right | 45, `HA BETA GAMMA <#>DELTA⏎P3 third` | 45, `HA BETA GAMMA <#>DELTA⏎P3 third` | same | 4212,1694 / 4212,1694 | 3 |
| Up | 24, `aragraph above<#>⏎P2 ALPHA BETA` | 24, `aragraph above<#>⏎P2 ALPHA BETA` | same | 3770,1418 / 3770,1418 | 3 |
| Down | 75, `aragraph below<#>` | 75, `aragraph below<#>` | same | 3850,1970 / 3850,1970 | 3 |
| Home | 25, `ragraph above⏎<#>P2 ALPHA BETA ` | 25, `ragraph above⏎<#>P2 ALPHA BETA ` | same | 1418,1694 / 1418,1694 | 3 |
| End | 50, `TA GAMMA DELTA<#>⏎P3 third para` | 50, `TA GAMMA DELTA<#>⏎P3 third para` | same | 4957,1694 / 4957,1694 | 3 |

### p2-backward
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 33, `above⏎P2 ALPHA<#> BETA GAMMA DE` | 33, `above⏎P2 ALPHA<#> BETA GAMMA DE` | same | 2505,1694 / 2505,1694 | 3 |
| Right | 35, `ove⏎P2 ALPHA B<#>ETA GAMMA DELT` | 35, `ove⏎P2 ALPHA B<#>ETA GAMMA DELT` | same | 2725,1694 / 2725,1694 | 3 |
| Up | 13, `P1 first para<#>graph above⏎P2` | 13, `P1 first para<#>graph above⏎P2` | same | 2591,1418 / 2591,1418 | 3 |
| Down | 63, `A⏎P3 third par<#>agraph below` | 63, `A⏎P3 third par<#>agraph below` | same | 2551,1970 / 2551,1970 | 3 |
| Home | 25, `ragraph above⏎<#>P2 ALPHA BETA ` | 25, `ragraph above⏎<#>P2 ALPHA BETA ` | same | 1418,1694 / 1418,1694 | 3 |
| End | 50, `TA GAMMA DELTA<#>⏎P3 third para` | 50, `TA GAMMA DELTA<#>⏎P3 third para` | same | 4957,1694 / 4957,1694 | 3 |

### s1
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 100, `ber oscar papa<#> quebec romeo ` | 100, `ber oscar papa<#> quebec romeo ` | same | 10961,1418 / 10961,1418 | 3 |
| Right | 102, `r oscar papa q<#>uebec romeo si` | 102, `r oscar papa q<#>uebec romeo si` | same | 1538,1694 / 1538,1694 | 3 |
| Up | 0, `<#>S1 alpha bravo` | 0, `<#>S1 alpha bravo` | same | 1418,1418 / 1418,1418 | 3 |
| Down | 201, `ive six seven <#>eight nine ten` | 201, `ive six seven <#>eight nine ten` | same | 1418,1970 / 1418,1970 | 3 |
| Home | 101, `er oscar papa <#>quebec romeo s` | 101, `er oscar papa <#>quebec romeo s` | same | 1418,1694 / 1418,1694 | 3 |
| End | 200, `five six seven<#> eight nine te` | 200, `five six seven<#> eight nine te` | same | 11174,1694 / 11174,1694 | 3 |

### s2
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 483, `rst visual lin<#>e⏎S2 second vi` | 483, `rst visual lin<#>e⏎S2 second vi` | same | 3064,2798 / 3064,2798 | 3 |
| Right | 485, `t visual line⏎<#>S2 second visu` | 485, `t visual line⏎<#>S2 second visu` | same | 1418,3074 / 1418,3074 | 3 |
| Up | 406, `ynine thirty t<#>hirtyone thirt` | 406, `ynine thirty t<#>hirtyone thirt` | same | 3191,2522 / 3191,2522 | 3 |
| Down | 503, `econd visual l<#>ine⏎S3 text be` | 503, `econd visual l<#>ine⏎S3 text be` | same | 3157,3074 / 3157,3074 | 3 |
| Home | 464, `irtyfive end1⏎<#>S2 first visua` | 464, `irtyfive end1⏎<#>S2 first visua` | same | 1418,2798 / 1418,2798 | 3 |
| End | 484, `st visual line<#>⏎S2 second vis` | 484, `st visual line<#>⏎S2 second vis` | same | 3171,2798 / 3171,2798 | 3 |

### s3
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 541, `mpty paragraph<#>⏎⏎S3 text afte` | 541, `mpty paragraph<#>⏎⏎S3 text afte` | same | 4796,3350 / 4796,3350 | 3 |
| Right | 543, `ty paragraph⏎⏎<#>S3 text after ` | 543, `ty paragraph⏎⏎<#>S3 text after ` | same | 1418,3902 / 1418,3902 | 3 |
| Up | 507, `d visual line⏎<#>S3 text before` | 507, `d visual line⏎<#>S3 text before` | same | 1418,3350 / 1418,3350 | 3 |
| Down | 543, `ty paragraph⏎⏎<#>S3 text after ` | 543, `ty paragraph⏎⏎<#>S3 text after ` | same | 1418,3902 / 1418,3902 | 3 |
| Home | 542, `pty paragraph⏎<#>⏎S3 text after` | 542, `pty paragraph⏎<#>⏎S3 text after` | same | 1418,3626 / 1418,3626 | 3 |
| End | 542, `pty paragraph⏎<#>⏎S3 text after` | 542, `pty paragraph⏎<#>⏎S3 text after` | same | 1418,3626 / 1418,3626 | 3 |

### s4
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 586, `raph⏎S4 cell A<#>1 text⇥S4 cell` | 586, `raph⏎S4 cell A<#>1 text⇥S4 cell` | same | 2297,4178 / 2297,4178 | 3 |
| Right | 588, `ph⏎S4 cell A1 <#>text⇥S4 cell B` | 588, `ph⏎S4 cell A1 <#>text⇥S4 cell B` | same | 2477,4178 / 2477,4178 | 3 |
| Up | 554, `h⏎⏎S3 text aft<#>er the empty p` | 554, `h⏎⏎S3 text aft<#>er the empty p` | same | 2404,3902 / 2404,3902 | 3 |
| Down | 619, `ext⏎S4 cell A2<#> text⇥S4 cell ` | 619, `ext⏎S4 cell A2<#> text⇥S4 cell ` | same | 2417,4454 / 2417,4454 | 3 |
| Home | 577, `pty paragraph⏎<#>S4 cell A1 tex` | 577, `pty paragraph⏎<#>S4 cell A1 tex` | same | 1418,4178 / 1418,4178 | 3 |
| End | 592, `4 cell A1 text<#>⇥S4 cell B1 te` | 592, `4 cell A1 text<#>⇥S4 cell B1 te` | same | 2837,4178 / 2837,4178 | 3 |

### s5
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 592, `4 cell A1 text<#>⇥S4 cell B1 te` | 592, `4 cell A1 text<#>⇥S4 cell B1 te` | same | 2837,4178 / 2837,4178 | 3 |
| Right | 594, `cell A1 text⇥S<#>4 cell B1 text` | 594, `cell A1 text⇥S<#>4 cell B1 text` | same | 6536,4178 / 6536,4178 | 3 |
| Up | 543, `ty paragraph⏎⏎<#>S3 text after ` | 543, `ty paragraph⏎⏎<#>S3 text after ` | same | 1418,3902 / 1418,3902 | 3 |
| Down | 625, ` cell A2 text⇥<#>S4 cell B2 tex` | 625, ` cell A2 text⇥<#>S4 cell B2 tex` | same | 6403,4454 / 6403,4454 | 3 |
| Home | 593, ` cell A1 text⇥<#>S4 cell B1 tex` | 593, ` cell A1 text⇥<#>S4 cell B1 tex` | same | 6403,4178 / 6403,4178 | 3 |
| End | 608, `4 cell B1 text<#>⏎S4 cell A2 te` | 608, `4 cell B1 text<#>⏎S4 cell A2 te` | same | 7822,4178 / 7822,4178 | 3 |

## Bottom line, ref vs emu
| shape | same | differs | unstable |
|---|---|---|---|
| p2-forward | 6 | 0 | 0 |
| p2-backward | 6 | 0 | 0 |
| s1 | 6 | 0 | 0 |
| s2 | 6 | 0 | 0 |
| s3 | 6 | 0 | 0 |
| s4 | 6 | 0 | 0 |
| s5 | 6 | 0 | 0 |

## click-only (where the collapse itself lands)
| shape | landing of '#' after the click alone | click (x, y) | cursor rect at click | selection after click |
|---|---|---|---|---|
| p2-forward | 44, `PHA BETA GAMMA<#> DELTA⏎P3 thir` | 4152, 1832 | 4152, 1694, 0, 276 | `` |
| p2-backward | 34, `bove⏎P2 ALPHA <#>BETA GAMMA DEL` | 2565, 1832 | 2565, 1694, 0, 276 | `` |
| s1 | 101, `er oscar papa <#>quebec romeo s` | 1418, 1832 | 1418, 1694, 0, 276 | `` |
| s2 | 484, `st visual line<#>⏎S2 second vis` | 3171, 2936 | 3171, 2798, 0, 276 | `` |
| s3 | 542, `pty paragraph⏎<#>⏎S3 text after` | 1418, 3764 | 1418, 3626, 0, 277 | `` |
| s4 | 587, `aph⏎S4 cell A1<#> text⇥S4 cell ` | 2417, 4316 | 2417, 4178, 0, 276 | `` |
| s5 | 593, ` cell A1 text⇥<#>S4 cell B1 tex` | 6403, 4316 | 6403, 4178, 0, 276 | `` |

## Table shapes: what the selection and the click looked like
| arm group | made (selection read-back) | TABLE_SELECTED / TEXT_SELECTION_START / END at the selection | StateTableCell seen after the click | click-only landing |
|---|---|---|---|---|
| s4 | `cell A1` | table `{ "columns": { "left": 0, "right": 9972, "tableOffset": 1418, "entries": [ { "position": 4985, "min": 0, "max": 9972, "hidden": false}]}, "rows": { "left": 0, "right": 552, "tableOffset": 4178, "entries": [ { "position": 276, "min": 0, "max": 9223372036854775807, "hidden": false}]}}`; start `1731, 4178, 0, 275`; end `2417, 4178, 0, 275` | [] | 587, `aph⏎S4 cell A1<#> text⇥S4 cell ` |
| s5 | `S4 cell A1 text⇥S4 cell B1 text⏎` | table `{ "columns": { "left": 0, "right": 9972, "tableOffset": 1418, "entries": [ { "position": 4985, "min": 0, "max": 9972, "hidden": false}]}, "rows": { "left": 0, "right": 552, "tableOffset": 4178, "entries": [ { "position": 276, "min": 0, "max": 9223372036854775807, "hidden": false}]}}`; start `2477, 4178, 0, 275`; end `2837, 4178, 0, 275` | ['.uno:StateTableCell=T1:B1'] | 593, ` cell A1 text⇥<#>S4 cell B1 tex` |

## Callbacks after the click (times relative to the click; grace 400 ms)
| arm group | arms | any callback within 400 ms | page-relevant (inferred) within 400 ms | first any (ms, median) | first page-relevant (ms, median) |
|---|---|---|---|---|---|
| p2-forward | 21 | 21/21 | 21/21 | 0.4 | 0.4 |
| p2-backward | 21 | 21/21 | 21/21 | 0.4 | 0.4 |
| s1 | 21 | 21/21 | 21/21 | 0.5 | 0.5 |
| s2 | 21 | 21/21 | 21/21 | 0.3 | 0.3 |
| s3 | 21 | 21/21 | 21/21 | 0.3 | 0.3 |
| s4 | 21 | 21/21 | 21/21 | 0.4 | 0.4 |
| s5 | 21 | 21/21 | 21/21 | 0.4 | 0.4 |
| ALL | 147 | 147/147 | 147/147 | | |

- arms where getTextSelection after the click is NOT empty (the selection survived the click): 0 []

Callback types seen after the click, per shape (union over arms, all times):
- p2-forward: MOUSE_POINTER, STATE_CHANGED, TEXT_SELECTION
- p2-backward: MOUSE_POINTER, STATE_CHANGED, TEXT_SELECTION
- s1: MOUSE_POINTER, STATE_CHANGED, TEXT_SELECTION
- s2: MOUSE_POINTER, STATE_CHANGED, TEXT_SELECTION
- s3: MOUSE_POINTER, STATE_CHANGED, TEXT_SELECTION
- s4: MOUSE_POINTER, STATE_CHANGED, TEXT_SELECTION
- s5: MOUSE_POINTER, RULER_UPDATE, STATE_CHANGED, TEXT_SELECTION

