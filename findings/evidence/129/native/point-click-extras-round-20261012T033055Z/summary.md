## Instrument checks
- arms read: 117 over rounds [1, 2, 3]; fatal arms: 0
- arms whose selection read-back differs from the expectation (shapes ['m1d', 'm1e', 'm1r', 's1d', 's1e', 's5'] excluded, their expectation is unknown): 0
- arms where the final text does not contain exactly one '#': 0
- wrap offset found by `discover-m1` per round: {1: 89, 2: 89, 3: 89}
- wrap offset found by `discover-s1` per round: {1: 101, 2: 101, 3: 101}
  - discover-s1 round 1: cursor at start `1418, 1418, 0, 276`; after 100 Rights `10961, 1418, 0, 276`; after 101 Rights `1418, 1694, 0, 276`
    line 1 ends with `...ike november oscar papa `
  - discover-m1 round 1: cursor at start `1418, 1418, 0, 276`; after 88 Rights `11202, 1418, 0, 276`; after 89 Rights `1418, 1694, 0, 276`
  - discover-s1 round 2: cursor at start `1418, 1418, 0, 276`; after 100 Rights `10961, 1418, 0, 276`; after 101 Rights `1418, 1694, 0, 276`
    line 1 ends with `...ike november oscar papa `
  - discover-m1 round 2: cursor at start `1418, 1418, 0, 276`; after 88 Rights `11202, 1418, 0, 276`; after 89 Rights `1418, 1694, 0, 276`
  - discover-s1 round 3: cursor at start `1418, 1418, 0, 276`; after 100 Rights `10961, 1418, 0, 276`; after 101 Rights `1418, 1694, 0, 276`
    line 1 ends with `...ike november oscar papa `
  - discover-m1 round 3: cursor at start `1418, 1418, 0, 276`; after 88 Rights `11202, 1418, 0, 276`; after 89 Rights `1418, 1694, 0, 276`

## The ref arms on the old fixture against `round-20261012T020528Z/arms.jsonl`
- 0 of 0 (arm, round) pairs give exactly the old round's text (0 arms x 3 rounds; none when this folder has no old-fixture arms)

## ref vs emu (whole-document text after the key and '#'; index = position of '#' in that text)

### s1e
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 99, `mber oscar pap<#>a quebec romeo` | 99, `mber oscar pap<#>a quebec romeo` | same | 10855,1418 / 10855,1418 | 3 |
| Right | 101, `er oscar papa <#>quebec romeo s` | 101, `er oscar papa <#>quebec romeo s` | same | 1418,1694 / 1418,1694 | 3 |
| Up | 0, `<#>S1 alpha bravo` | 0, `<#>S1 alpha bravo` | same | 1418,1418 / 1418,1418 | 3 |
| Down | 198, `r five six sev<#>en eight nine ` | 198, `r five six sev<#>en eight nine ` | same | 10948,1694 / 10948,1694 | 3 |
| Home | 0, `<#>S1 alpha bravo` | 0, `<#>S1 alpha bravo` | same | 1418,1418 / 1418,1418 | 3 |
| End | 100, `ber oscar papa<#> quebec romeo ` | 100, `ber oscar papa<#> quebec romeo ` | same | 10961,1418 / 10961,1418 | 3 |

### m1r
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 88, `insxdinsxchmrw<#>bglqvafkpuzejo` | 88, `insxdinsxchmrw<#>bglqvafkpuzejo` | same | 11202,1418 / 11202,1418 | 3 |
| Right | 90, `sxdinsxchmrwbg<#>lqvafkpuzejoty` | 90, `sxdinsxchmrwbg<#>lqvafkpuzejoty` | same | 1538,1694 / 1538,1694 | 3 |
| Up | 0, `<#>afkpuzejotydin` | 0, `<#>afkpuzejotydin` | same | 1418,1418 / 1418,1418 | 3 |
| Down | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | same | 1418,1970 / 1418,1970 | 3 |
| Home | 89, `nsxdinsxchmrwb<#>glqvafkpuzejot` | 89, `nsxdinsxchmrwb<#>glqvafkpuzejot` | same | 1418,1694 / 1418,1694 | 3 |
| End | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | same | 11282,1694 / 11282,1694 | 3 |

### m1e
| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |
|---|---|---|---|---|---|
| Left | 88, `insxdinsxchmrw<#>bglqvafkpuzejo` | 88, `insxdinsxchmrw<#>bglqvafkpuzejo` | same | 11202,1418 / 11202,1418 | 3 |
| Right | 90, `sxdinsxchmrwbg<#>lqvafkpuzejoty` | 90, `sxdinsxchmrwbg<#>lqvafkpuzejoty` | same | 1538,1694 / 1538,1694 | 3 |
| Up | 0, `<#>afkpuzejotydin` | 0, `<#>afkpuzejotydin` | same | 1418,1418 / 1418,1418 | 3 |
| Down | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | 270, `puzekpuzejotyd<#>insxchmrwbglqv` | differs | 1418,1970 / 1418,2246 | 3 |
| Home | 89, `nsxdinsxchmrwb<#>glqvafkpuzejot` | 89, `nsxdinsxchmrwb<#>glqvafkpuzejot` | same | 1418,1694 / 1418,1694 | 3 |
| End | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | same | 11282,1694 / 11282,1694 | 3 |

## Bottom line, ref vs emu
| shape | same | differs | unstable |
|---|---|---|---|
| s1e | 6 | 0 | 0 |
| m1r | 6 | 0 | 0 |
| m1e | 5 | 1 (Down) | 0 |

## click-only (where the collapse itself lands)
| shape | landing of '#' after the click alone | click (x, y) | cursor rect at click | selection after click |
|---|---|---|---|---|
| s1e | 100, `ber oscar papa<#> quebec romeo ` | 10961, 1556 | 10961, 1418, 0, 276 | `` |
| m1r | 89, `nsxdinsxchmrwb<#>glqvafkpuzejot` | 1418, 1832 | 1418, 1694, 0, 276 | `` |
| m1e | 89, `nsxdinsxchmrwb<#>glqvafkpuzejot` | 11322, 1556 | 11322, 1418, 0, 276 | `` |

## Table shapes: what the selection and the click looked like
| arm group | made (selection read-back) | TABLE_SELECTED / TEXT_SELECTION_START / END at the selection | StateTableCell seen after the click | click-only landing |
|---|---|---|---|---|

## Callbacks after the click (times relative to the click; grace 400 ms)
| arm group | arms | any callback within 400 ms | page-relevant (inferred) within 400 ms | first any (ms, median) | first page-relevant (ms, median) |
|---|---|---|---|---|---|
| s1e | 21 | 21/21 | 21/21 | 0.3 | 0.3 |
| m1r | 21 | 21/21 | 21/21 | 0.4 | 0.4 |
| m1e | 21 | 21/21 | 21/21 | 0.3 | 0.4 |
| ALL | 63 | 63/63 | 63/63 | | |

- arms where getTextSelection after the click is NOT empty (the selection survived the click): 0 []

Callback types seen after the click, per shape (union over arms, all times):
- s1e: MOUSE_POINTER, STATE_CHANGED, TEXT_SELECTION
- m1r: MOUSE_POINTER, STATE_CHANGED, TEXT_SELECTION
- m1e: MOUSE_POINTER, STATE_CHANGED, TEXT_SELECTION

