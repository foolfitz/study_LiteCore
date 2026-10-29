# F3-80: three Chrome cells moved -- investigation (2026-10-30 ~07:20 +0800)

Spec `specs/SPEC-M3-select-all-v26.md` 5.6: "a moved cell: stop and investigate, do not rerun it away; if 174 moves a cell that reads the toast, first append to this spec naming the cell and the reason, then judge." This file is the investigation. No rerun was made to wash anything out; no judgement is made here.

## What the readers say

- `read-01.json` (`tools/read_v25_f3.py --v25 ../findings/evidence/select-all-v26/f3/run-01`, unchanged): **`F3_RED`**, problems: `chrome an-aborted-gesture-stops-selecting [no-regression]: v24 PASS -> v25 NOT_ESTABLISHED`; `chrome an-inline-format-reaches-a-selection [P]: v24 FAIL -> v25 FAIL`; `chrome the-page-agrees-with-the-engine-about-the-selection [no-regression]: v24 PASS -> v25 NOT_ESTABLISHED`.
- `equal-01.json` (`tools/read_v80_f3_equal.py --v80 …`): **`F3_80_MOVED`**: the same three Chrome cells, F3-79 `PASS` -> v80 `NOT_ESTABLISHED` / `FAIL` / `NOT_ESTABLISHED`. Firefox 46/46 equal; Chrome 43/46 equal.

## Mechanism (read in the source, not inferred)

`wasm_sdk_probe/tools/run_e2_c_product_path.py` (bound, not edited) takes the ENGINE's selected text from the product's copy toast by parsing its `U+XXXX` list, at three places:

- line ~7515 (`an-aborted-gesture-stops-selecting`, every arm): `text = "".join(chr(int(point, 16)) for point in re.findall(r"U\+([0-9A-Fa-f]{4,6})", reach))`;
- line ~8408 (`an-inline-format-reaches-a-selection`): the same expression into `selection_format["selectedText"]`;
- line ~8504 (`the-page-agrees-with-the-engine-about-the-selection`): `agreement["engineCodePoints"] = len(re.findall(r"U\+([0-9A-Fa-f]{4,6})", copied_s))`.

Finding 175's fix (generation 80, `7745a26e9`, spec append 1) changed that toast from `已複製 U+004B,U+0049,… 字` to `已複製 5 字`. Every parse above now yields the empty string / zero, so the three checks lose their observable: two refuse to judge (NE, by their own preconditions) and the inline-format check's bold delta is compared against an empty selection (FAIL).

Spec append 1 named this pattern only for the `copy-lies` mutation (L-copy-lies-pattern-stale) and stated that F3-80/F4-80, which run without `--mutate`, are unaffected. That statement is false: three ordinary checks read the same toast.

Firefox did not move because its copy was already denied in F3-79 (`複製：CLIPBOARD_DENIED：clipboard write was denied`): the same three cells were NE / FAIL / NE there before and after.

## A second run on generation 80, and what the records still show

F4-80's runner executes the whole product-path suite before its four arms (`../f4/{chrome,firefox}/report.json`). Against F4-79's suite (`../../shell-v79-173/f4/*/report.json`): Chrome moved in exactly the same three cells and nothing else (46 cells each); Firefox moved in none.

The counts the new toast carries, against the text F3-79/F4-79 parsed at the same positions:

| cell / arm | F4-79 Chrome text (parsed from the U+ list) | len | F3-80 / F4-80 Chrome toast |
|---|---|---|---|
| aborted-gesture control | `E1-LC-ISOLATED 前後都不是清單的` | 23 | `已複製 23 字` |
| aborted-gesture reference | `E1-LC-ISOLAT` | 12 | `已複製 12 字` |
| aborted-gesture pointercancel | `E1-LC-ISOLAT` | 12 | `已複製 12 字` |
| aborted-gesture blur | `E1-LC-ISOLAT` | 12 | `已複製 12 字` |
| page-agrees | `KITAL` | 5 | `已複製 5 字` |

`an-inline-format-reaches-a-selection` records no toast of its own copy, but its save delta does survive: in F3-80 Chrome `boldBefore` starts `MKBOLDON…` and `boldAfter` starts `KITALMKBOLDON…` -- the text newly bold is `KITAL`, which is what F4-79 recorded as `selectedText` for the same check.

So every number that is still readable equals the old run's, position for position. What is no longer readable is the TEXT: the aborted-gesture check compares strings, not counts, on purpose (finding 078: the engine's selection string can carry a list prefix and a paragraph separator a count cannot tell apart).

## What this means beyond F3-80

After generation 80, these three properties have no working net in either browser: Firefox's copy is denied, Chrome's toast no longer carries the text. `an-inline-format-reaches-a-selection` is a `[P]` (must-pass) cell for `read_v25_f3.py`.
