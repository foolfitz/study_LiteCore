# D-typed-rsid-spans: native keyboard typing and `.uno:InsertText` save the same rsid structure

Fable ruling 1 (v24 pre-count) §2.2 item 2; spec §16 item 4. Reader `wasm_sdk_probe/tools/read_m1_rsid_spans.py` (new) over M1's native saves: for each of the 16 shape × text pairs typed both by the keyboard (`key`) and by `.uno:InsertText`, each round, it counts in the two after-saves' content.xml the `officeooo:rsid` attributes (any style family), the text automatic styles carrying one, and the `<text:span` elements, and requires the three counts equal; non-vacuity: every key after-save carries at least one rsid attribute.

| Run | Verdict | Pair-rounds equal |
|---|---|---|
| `m1-run-01.json` (v23 `s5-type-route-ruling/m1-run-01/`) | `SAME_RSID_SPAN_STRUCTURE` | 48/48 |
| `m1-run-02.json` (`../m1-rerun/run-02/`) | `SAME_RSID_SPAN_STRUCTURE` | 48/48 |

Structure in both arms, every round: `text` and `cell-caret` — 1 rsid attribute on a text automatic style, 1 span (a run typed inside a paragraph); `table2` and `table4` — 1 rsid attribute on the **paragraph** automatic style, 0 text styles, 0 spans (text that replaces a whole cell's selection). Every before-save: 0. The doc-end `teh` pair (autocorrect, L-typed-no-autocorrect) is reported beside: equal too (1/1/1) in all 3 rounds.

**A reader error caught by its own non-vacuity check before anything was recorded:** the first version counted only text-family styles, so the table shapes read 0 == 0 and the check named all 24 table pair-rounds vacuous. Looking at the saves showed the rsid on the paragraph style; the reader now counts rsid attributes of any family. (Fable's ruling had it right: "one `officeooo:rsid`" per save.)

Red cases (scratch copies of m1-run-01): (a) `text_uno-insert-text-x-r1-after.odt` replaced by its before-save → exit 1, `text/x r1` named with both counts (`red-a.*`); (b) both after-saves of `text/x r2` replaced by their before-saves (0 == 0) → exit 1, `text/x r2: key after-save has no rsid attribute (vacuous)` (`red-b.*`).

So "v24 saves typed text with rsid spans as native keyboard typing does" is now a recorded observation and may appear in the release notes.
