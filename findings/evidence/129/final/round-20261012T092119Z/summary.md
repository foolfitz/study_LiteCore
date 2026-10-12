## chrome (Chrome/151.0.7922.169)

started 2026-10-12T09:21:19Z, completed 2026-10-12T09:33:43Z (UTC); loadavg [0.96, 0.96, 0.99] -> [1.2, 1.14, 1.08]; MemAvailable 11754 -> 8872 MB, SwapFree 26455 -> 25772 MB

arms by kind/status: {'m4/counted': 54, 'shift/counted': 2, 'reach/counted': 8, 'red/counted': 3}
not fresh: []; selection-mismatch: []; other not counted: []
wrap offsets: S1 [101, 195, 292] (native 101, line 3 starts at 201); token [87, 175, 261] (native 89, 180, 270); S1 lines: 5 (native 5)

### where `#` landed: WASM against native ref / emu (flat index in the whole document text)

| shape | key | WASM | native ref | native emu | = ref (exact) | = emu (exact) | by rule: ref / emu | note |
|---|---|---|---|---|---|---|---|---|
| p2-forward | Left | 43 | 43 | 43 | True | True | True / True |  |
| p2-forward | Right | 45 | 45 | 45 | True | True | True / True |  |
| p2-forward | Up | 24 | 24 | 24 | True | True | True / True |  |
| p2-forward | Down | 75 | 75 | 75 | True | True | True / True |  |
| p2-forward | Home | 25 | 25 | 25 | True | True | True / True |  |
| p2-forward | End | 50 | 50 | 50 | True | True | True / True |  |
| p2-backward | Left | 33 | 33 | 33 | True | True | True / True |  |
| p2-backward | Right | 35 | 35 | 35 | True | True | True / True |  |
| p2-backward | Up | 13 | 13 | 13 | True | True | True / True |  |
| p2-backward | Down | 63 | 63 | 63 | True | True | True / True |  |
| p2-backward | Home | 25 | 25 | 25 | True | True | True / True |  |
| p2-backward | End | 50 | 50 | 50 | True | True | True / True |  |
| s1 | Left | 100 | 100 | 100 | True | True | True / True | rule: ref 100, emu 100 |
| s1 | Right | 102 | 102 | 102 | True | True | True / True | rule: ref 102, emu 102 |
| s1 | Up | 0 | 0 | 0 | True | True | True / True | rule: ref 0, emu 0 |
| s1 | Down | 195 | 201 | 201 | False | False | True / True | rule: ref 195, emu 195 |
| s1 | Home | 101 | 101 | 101 | True | True | True / True | rule: ref 101, emu 101 |
| s1 | End | 194 | 200 | 200 | False | False | True / True | rule: ref 194, emu 194 |
| s2 | Left | 483 | 483 | 483 | True | True | True / True |  |
| s2 | Right | 485 | 485 | 485 | True | True | True / True |  |
| s2 | Up | 406 | 406 | 406 | True | True | True / True |  |
| s2 | Down | 503 | 503 | 503 | True | True | True / True |  |
| s2 | Home | 464 | 464 | 464 | True | True | True / True |  |
| s2 | End | 484 | 484 | 484 | True | True | True / True |  |
| s3 | Left | 541 | 541 | 541 | True | True | True / True |  |
| s3 | Right | 543 | 543 | 543 | True | True | True / True |  |
| s3 | Up | 507 | 507 | 507 | True | True | True / True |  |
| s3 | Down | 543 | 543 | 543 | True | True | True / True |  |
| s3 | Home | 542 | 542 | 542 | True | True | True / True |  |
| s3 | End | 542 | 542 | 542 | True | True | True / True |  |
| s4 | Left | 586 | 586 | 586 | True | True | True / True |  |
| s4 | Right | 588 | 588 | 588 | True | True | True / True |  |
| s4 | Up | 554 | 554 | 554 | True | True | True / True |  |
| s4 | Down | 619 | 619 | 619 | True | True | True / True |  |
| s4 | Home | 577 | 577 | 577 | True | True | True / True |  |
| s4 | End | 592 | 592 | 592 | True | True | True / True |  |
| s5 | Left | 592 | 592 | 592 | True | True | True / True |  |
| s5 | Right | 594 | 594 | 594 | True | True | True / True |  |
| s5 | Up | 543 | 543 | 543 | True | True | True / True |  |
| s5 | Down | 625 | 625 | 625 | True | True | True / True |  |
| s5 | Home | 593 | 593 | 593 | True | True | True / True |  |
| s5 | End | 608 | 608 | 608 | True | True | True / True |  |
| s1d | Left | 100 | 100 | 100 | True | True | True / True | rule: ref 100, emu 100 |
| s1d | Right | 102 | 102 | 102 | True | True | True / True | rule: ref 102, emu 102 |
| s1d | Up | 0 | 0 | 0 | True | True | True / True | rule: ref 0, emu 0 |
| s1d | Down | 195 | 201 | 199 | False | False | True / False | rule: ref 195, emu 194 |
| s1d | Home | 101 | 101 | 101 | True | True | True / True | rule: ref 101, emu 101 |
| s1d | End | 194 | 200 | 200 | False | False | True / True | rule: ref 194, emu 194 |
| m1d | Left | 86 | 88 | 88 | False | False | True / True | rule: ref 86, emu 86 |
| m1d | Right | 88 | 90 | 90 | False | False | True / True | rule: ref 88, emu 88 |
| m1d | Up | 0 | 0 | 0 | True | True | True / True | rule: ref 0, emu 0 |
| m1d | Down | 175 | 180 | 270 | False | False | True / False | rule: ref 175, emu 261 |
| m1d | Home | 87 | 89 | 89 | False | False | True / True | rule: ref 87, emu 87 |
| m1d | End | 175 | 180 | 180 | False | False | True / True | rule: ref 175, emu 175 |

bottom line: {"oldArmsEqualNativeRef": "12/12", "briefExactRef": "28/30", "briefByRuleRef": "30/30", "briefNotExact": ["s1/Down", "s1/End"], "dragKeysNonDownByRule": "10/10", "dragDownFollowsRef": ["s1d", "m1d"], "dragDownFollowsEmu": []}

### timing (keydown -> latency record), m4 arms

split by whether the key moved the caret: {"moved": {"n": 47, "keyToMoveDone": {"n": 47, "min": 81.0, "median": 81.9, "max": 91.3}, "keyToClickDone": {"n": 47, "min": 26.3, "median": 27.3, "max": 36.9}, "clickDoneToMoveDone": {"n": 47, "min": 53.2, "median": 54.6, "max": 55.6}}, "notMoved": {"n": 7, "keyToMoveDone": {"n": 7, "min": 281.9, "median": 282.7, "max": 285.1}, "keyToClickDone": {"n": 7, "min": 26.1, "median": 27.0, "max": 29.8}, "clickDoneToMoveDone": {"n": 7, "min": 255.3, "median": 255.7, "max": 256.6}}}
move done: {'n': 54, 'min': 81.0, 'median': 82.0, 'max': 285.1}; click done (the 定位游標 record): {'n': 54, 'min': 26.1, 'median': 27.3, 'max': 36.9}
arms with move >= 200 ms: 7; of those, the key moved the caret: Counter({False: 7}); arms < 200 ms by 'moved the caret': {True: 47}
  - m4-s1-Home: move 282.4 ms, click 27.0 ms
  - m4-s2-End: move 285.1 ms, click 29.8 ms
  - m4-s3-Home: move 282.7 ms, click 27.0 ms
  - m4-s3-End: move 282.1 ms, click 26.6 ms
  - m4-s5-Home: move 284.4 ms, click 27.8 ms
  - m4-s1d-Home: move 281.9 ms, click 26.1 ms
  - m4-m1d-Home: move 283.1 ms, click 27.4 ms
toasts in m4 arms (whole arm after the open): 0 arms []; pill 'stopped' in: []
swap pages during arms: {'pswpinMin': 547, 'pswpinMax': 2089, 'pswpoutMin': 0, 'pswpoutMax': 32928, 'armsWithNoSwapActivity': 0}

shift arms: {"collapsed": {"caretMoved": false, "revision": [0, 0], "hash": {"flatIndex": 34, "paragraph": 1, "offset": 9}, "toasts": [], "keydowns": [["ArrowRight", true], ["ArrowRight", true], ["ArrowRight", true]], "latencyRecords": [], "collapsedAfter": true}, "range": {"textBefore": "BETA GAMMA", "textAfter": "BETA GAMMA", "sameCaret": true, "sameSelection": true, "revision": [0, 0], "toasts": [], "keydowns": [["ArrowRight", true]], "latencyRecords": [], "toolbar": [{"shape": "range-single", "evidence": null}, {"shape": "range-single", "evidence": null}]}}

red control: [{"arm": "red-p2-forward-Left", "refused": true, "toast": "◀：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged", "latency": "◀ 失敗", "selectionOk": true}, {"arm": "red-p2-forward-End", "refused": true, "toast": "移到行尾：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged", "latency": "移到行尾 失敗", "selectionOk": true}, {"arm": "red-p2-backward-Down", "refused": true, "toast": "下移一行：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged", "latency": "下移一行 失敗", "selectionOk": true}]

reach (the page's own drag; where the visible caret ends): 
  - {'arm': 'reach-s1d-0', 'farX': 10961, 'lineEndX': 10961, 'caret': [10961, 1418], 'selectionEnd': [10961, 1418], 'text': 'scar papa'}
  - {'arm': 'reach-s1d-100', 'farX': 11061, 'lineEndX': 10961, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'scar papa '}
  - {'arm': 'reach-s1d-400', 'farX': 11361, 'lineEndX': 10961, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'scar papa '}
  - {'arm': 'reach-s1d-900', 'farX': 11861, 'lineEndX': 10961, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'scar papa '}
  - {'arm': 'reach-m1d-0', 'farX': 11029, 'lineEndX': 11029, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'xdinsxchmr'}
  - {'arm': 'reach-m1d-100', 'farX': 11129, 'lineEndX': 11029, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'xdinsxchmr'}
  - {'arm': 'reach-m1d-400', 'farX': 11429, 'lineEndX': 11029, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'xdinsxchmr'}
  - {'arm': 'reach-m1d-900', 'farX': 11929, 'lineEndX': 11029, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'xdinsxchmr'}

## firefox (157.0.1)

started 2026-10-12T09:33:43Z, completed 2026-10-12T09:47:14Z (UTC); loadavg [1.2, 1.14, 1.08] -> [0.7, 0.89, 1.02]; MemAvailable 10433 -> 8990 MB, SwapFree 25772 -> 25785 MB

arms by kind/status: {'m4/counted': 54, 'shift/counted': 2, 'reach/counted': 8, 'red/counted': 3}
not fresh: []; selection-mismatch: []; other not counted: []
wrap offsets: S1 [101, 195, 292] (native 101, line 3 starts at 201); token [87, 175, 261] (native 89, 180, 270); S1 lines: 5 (native 5)

### where `#` landed: WASM against native ref / emu (flat index in the whole document text)

| shape | key | WASM | native ref | native emu | = ref (exact) | = emu (exact) | by rule: ref / emu | note |
|---|---|---|---|---|---|---|---|---|
| p2-forward | Left | 43 | 43 | 43 | True | True | True / True |  |
| p2-forward | Right | 45 | 45 | 45 | True | True | True / True |  |
| p2-forward | Up | 24 | 24 | 24 | True | True | True / True |  |
| p2-forward | Down | 75 | 75 | 75 | True | True | True / True |  |
| p2-forward | Home | 25 | 25 | 25 | True | True | True / True |  |
| p2-forward | End | 50 | 50 | 50 | True | True | True / True |  |
| p2-backward | Left | 33 | 33 | 33 | True | True | True / True |  |
| p2-backward | Right | 35 | 35 | 35 | True | True | True / True |  |
| p2-backward | Up | 13 | 13 | 13 | True | True | True / True |  |
| p2-backward | Down | 63 | 63 | 63 | True | True | True / True |  |
| p2-backward | Home | 25 | 25 | 25 | True | True | True / True |  |
| p2-backward | End | 50 | 50 | 50 | True | True | True / True |  |
| s1 | Left | 100 | 100 | 100 | True | True | True / True | rule: ref 100, emu 100 |
| s1 | Right | 102 | 102 | 102 | True | True | True / True | rule: ref 102, emu 102 |
| s1 | Up | 0 | 0 | 0 | True | True | True / True | rule: ref 0, emu 0 |
| s1 | Down | 195 | 201 | 201 | False | False | True / True | rule: ref 195, emu 195 |
| s1 | Home | 101 | 101 | 101 | True | True | True / True | rule: ref 101, emu 101 |
| s1 | End | 194 | 200 | 200 | False | False | True / True | rule: ref 194, emu 194 |
| s2 | Left | 483 | 483 | 483 | True | True | True / True |  |
| s2 | Right | 485 | 485 | 485 | True | True | True / True |  |
| s2 | Up | 406 | 406 | 406 | True | True | True / True |  |
| s2 | Down | 503 | 503 | 503 | True | True | True / True |  |
| s2 | Home | 464 | 464 | 464 | True | True | True / True |  |
| s2 | End | 484 | 484 | 484 | True | True | True / True |  |
| s3 | Left | 541 | 541 | 541 | True | True | True / True |  |
| s3 | Right | 543 | 543 | 543 | True | True | True / True |  |
| s3 | Up | 507 | 507 | 507 | True | True | True / True |  |
| s3 | Down | 543 | 543 | 543 | True | True | True / True |  |
| s3 | Home | 542 | 542 | 542 | True | True | True / True |  |
| s3 | End | 542 | 542 | 542 | True | True | True / True |  |
| s4 | Left | 586 | 586 | 586 | True | True | True / True |  |
| s4 | Right | 588 | 588 | 588 | True | True | True / True |  |
| s4 | Up | 554 | 554 | 554 | True | True | True / True |  |
| s4 | Down | 619 | 619 | 619 | True | True | True / True |  |
| s4 | Home | 577 | 577 | 577 | True | True | True / True |  |
| s4 | End | 592 | 592 | 592 | True | True | True / True |  |
| s5 | Left | 592 | 592 | 592 | True | True | True / True |  |
| s5 | Right | 594 | 594 | 594 | True | True | True / True |  |
| s5 | Up | 543 | 543 | 543 | True | True | True / True |  |
| s5 | Down | 625 | 625 | 625 | True | True | True / True |  |
| s5 | Home | 593 | 593 | 593 | True | True | True / True |  |
| s5 | End | 608 | 608 | 608 | True | True | True / True |  |
| s1d | Left | 100 | 100 | 100 | True | True | True / True | rule: ref 100, emu 100 |
| s1d | Right | 102 | 102 | 102 | True | True | True / True | rule: ref 102, emu 102 |
| s1d | Up | 0 | 0 | 0 | True | True | True / True | rule: ref 0, emu 0 |
| s1d | Down | 195 | 201 | 199 | False | False | True / False | rule: ref 195, emu 194 |
| s1d | Home | 101 | 101 | 101 | True | True | True / True | rule: ref 101, emu 101 |
| s1d | End | 194 | 200 | 200 | False | False | True / True | rule: ref 194, emu 194 |
| m1d | Left | 86 | 88 | 88 | False | False | True / True | rule: ref 86, emu 86 |
| m1d | Right | 88 | 90 | 90 | False | False | True / True | rule: ref 88, emu 88 |
| m1d | Up | 0 | 0 | 0 | True | True | True / True | rule: ref 0, emu 0 |
| m1d | Down | 175 | 180 | 270 | False | False | True / False | rule: ref 175, emu 261 |
| m1d | Home | 87 | 89 | 89 | False | False | True / True | rule: ref 87, emu 87 |
| m1d | End | 175 | 180 | 180 | False | False | True / True | rule: ref 175, emu 175 |

bottom line: {"oldArmsEqualNativeRef": "12/12", "briefExactRef": "28/30", "briefByRuleRef": "30/30", "briefNotExact": ["s1/Down", "s1/End"], "dragKeysNonDownByRule": "10/10", "dragDownFollowsRef": ["s1d", "m1d"], "dragDownFollowsEmu": []}

### timing (keydown -> latency record), m4 arms

split by whether the key moved the caret: {"moved": {"n": 47, "keyToMoveDone": {"n": 47, "min": 83.8, "median": 84.6, "max": 88.5}, "keyToClickDone": {"n": 47, "min": 27.8, "median": 29.1, "max": 33.3}, "clickDoneToMoveDone": {"n": 47, "min": 53.3, "median": 55.6, "max": 57.0}}, "notMoved": {"n": 7, "keyToMoveDone": {"n": 7, "min": 285.4, "median": 286.7, "max": 307.3}, "keyToClickDone": {"n": 7, "min": 28.0, "median": 28.6, "max": 39.8}, "clickDoneToMoveDone": {"n": 7, "min": 257.4, "median": 258.2, "max": 278.9}}}
move done: {'n': 54, 'min': 83.8, 'median': 84.6, 'max': 307.3}; click done (the 定位游標 record): {'n': 54, 'min': 27.8, 'median': 29.05, 'max': 39.8}
arms with move >= 200 ms: 7; of those, the key moved the caret: Counter({False: 7}); arms < 200 ms by 'moved the caret': {True: 47}
  - m4-s1-Home: move 286.4 ms, click 28.6 ms
  - m4-s2-End: move 286.7 ms, click 28.1 ms
  - m4-s3-Home: move 285.4 ms, click 28.0 ms
  - m4-s3-End: move 286.6 ms, click 28.6 ms
  - m4-s5-Home: move 288.9 ms, click 30.7 ms
  - m4-s1d-Home: move 298.6 ms, click 39.8 ms
  - m4-m1d-Home: move 307.3 ms, click 28.4 ms
toasts in m4 arms (whole arm after the open): 0 arms []; pill 'stopped' in: []
swap pages during arms: {'pswpinMin': 701, 'pswpinMax': 17211, 'pswpoutMin': 0, 'pswpoutMax': 16113, 'armsWithNoSwapActivity': 0}

shift arms: {"collapsed": {"caretMoved": false, "revision": [0, 0], "hash": {"flatIndex": 34, "paragraph": 1, "offset": 9}, "toasts": [], "keydowns": [["Shift", true], ["ArrowRight", true], ["Shift", true], ["ArrowRight", true], ["Shift", true], ["ArrowRight", true]], "latencyRecords": [], "collapsedAfter": true}, "range": {"textBefore": "BETA GAMMA", "textAfter": "BETA GAMMA", "sameCaret": true, "sameSelection": true, "revision": [0, 0], "toasts": [], "keydowns": [["Shift", true], ["ArrowRight", true]], "latencyRecords": [], "toolbar": [{"shape": "range-single", "evidence": null}, {"shape": "range-single", "evidence": null}]}}

red control: [{"arm": "red-p2-forward-Left", "refused": true, "toast": "◀：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged", "latency": "◀ 失敗", "selectionOk": true}, {"arm": "red-p2-forward-End", "refused": true, "toast": "移到行尾：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged", "latency": "移到行尾 失敗", "selectionOk": true}, {"arm": "red-p2-backward-Down", "refused": true, "toast": "下移一行：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged", "latency": "下移一行 失敗", "selectionOk": true}]

reach (the page's own drag; where the visible caret ends): 
  - {'arm': 'reach-s1d-0', 'farX': 10961, 'lineEndX': 10961, 'caret': [10961, 1418], 'selectionEnd': [10961, 1418], 'text': 'scar papa'}
  - {'arm': 'reach-s1d-100', 'farX': 11061, 'lineEndX': 10961, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'scar papa '}
  - {'arm': 'reach-s1d-400', 'farX': 11361, 'lineEndX': 10961, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'scar papa '}
  - {'arm': 'reach-s1d-900', 'farX': 11861, 'lineEndX': 10961, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'scar papa '}
  - {'arm': 'reach-m1d-0', 'farX': 11029, 'lineEndX': 11029, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'xdinsxchmr'}
  - {'arm': 'reach-m1d-100', 'farX': 11129, 'lineEndX': 11029, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'xdinsxchmr'}
  - {'arm': 'reach-m1d-400', 'farX': 11429, 'lineEndX': 11029, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'xdinsxchmr'}
  - {'arm': 'reach-m1d-900', 'farX': 11929, 'lineEndX': 11029, 'caret': [1418, 1694], 'selectionEnd': [1418, 1694], 'text': 'xdinsxchmr'}

## cross-check: chrome vs firefox landing index equal in 54/54 cells; differ: []

## cross-check: chrome this round against round-20261012T064814Z: {'compared': 54, 'differ': [], 'wrapOffsetsSame': True}

## cross-check: firefox this round against round-20261012T064814Z: {'compared': 54, 'differ': [], 'wrapOffsetsSame': True}

