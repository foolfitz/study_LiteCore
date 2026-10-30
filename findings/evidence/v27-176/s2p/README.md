# S2′: finding 083's path stays a toast, and the strip says 待確認 -- the owner's path (2026-10-30)

Spec `specs/SPEC-M3-v27-finding-176.md` 7.3 S2′.

The tool is `wasm_sdk_probe/tools/check_v81_blank_bullet.py`. It imports the bound `check_v80_blank_bullet.py` (S2) and, through it, `check_v79_blank_bullet.py` (B1), and edits neither. Products: `tools/v81_f_products.py`:
- before = generation 80: page `3b6c023e` from git `7745a26e9`, profile v26;
- after = the generation-81 candidate as `dist/` serves it: page `b63d8ee5`, profile v27.

Both identities are `ok`. Local mirror, no DDEV.

## Procedure

It is B1's procedure, unchanged:
- the host's blank template, opened through the page's file input;
- two arms: `noclick`, and `click` into the paragraph;
- a real click on the bullet button, the marker typed with real keys, the product's save.

B1's four clauses and S2's three are judged through S2's `judge_after`. S2′ adds one clause for after: `press.latency == typed.latency == "• 項目符號：待確認"`. Before is red for 176's shell item when S2's `judge_after` passes on it and `press.latency == "• 項目符號 失敗"`.

## run-01 (Chrome 156, Firefox 157; 2 arms x N=3): **S2P_HOLDS** (`run-01/report.json`, exit 0)

| | Chrome | Firefox |
| --- | --- | --- |
| after: B1 + S2 + strip 待確認 | 6/6 PASS | 6/6 PASS |
| before: red for 176's shell item | 6/6 | 6/6 |

**Every run, both products:**
- the bullet's reply is 083/173's shape: `select-text-returned-none`, collapsed, dispatched. The 083 path is unchanged by v27, as spec 2 and L-083-stays-a-toast say;
- pill `ready`, no notice;
- the toast is 083's sentence 「…這一段是空的…」, not in the error style;
- the queue stays open and the saved marker is in a list.

**The strip:**
- after (v27): `• 項目符號：待確認` at the press and still after typing;
- before (generation 80): `• 項目符號 失敗` at both points. This is the owner's 0.2.42 observation (a), with the toast 083's instead of 046's.

`self-test-01.json`: **ALL_RED, 11/11 mutations.**
- B1/S2's clauses through S2's judge: toast bad, code shown, notice shown, marker out of list, other shape.
- S2′'s own: after press strip `失敗`, after typed strip moved, before strip `待確認`, before toast lost.
- One run missing, one identity failed.
