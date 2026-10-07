# fc-request discriminator: result

Two runs, each committed before it ran:

- `run.py`, per `PREDICTION.md` (`2b782a5c`). Run 2026-10-08 02:11:52-02:12:10 (+08:00), exit 0, stderr empty. Four cold Chrome sessions of about 5 s each.
- `run_v8.py`, per `V8-PREDICTION.md` (`e53fc859`, written after the four sessions and before v8's). Run 02:15:52-02:15:57, exit 0, stderr empty.

Raw output: `fc-request.json`, `fc-request-v8.json`, one `*-fc-log.txt` per session, `summary.txt` and `summary-v8.txt`. The tools are imported, not edited: `probe_fc_debug.py` `246a69b1…`, `compare_layout_corpus.py` `21f90c31…` (the same file as the counted run), `run_e2_c_product_path.py` `b52779e4…`. Repointed page for v17: `4c0088c7…`, the candidate page. Each session's engine stderr is 72 lines of `configmgr` warnings, the same in every session.

## Positive controls

| | v17 A | control A | v17 D | control D | v8 A |
|---|---|---|---|---|---|
| boot / open | ready / ready | ready / ready | ready / ready | ready / ready | ready / ready |
| conf.d loaded | 21 | 21 | 21 | 21 | 22 (`35-lang-normalize.conf` included) |
| Match blocks (fixture phase) | 38 (28) | 39 (28) | 34 (24) | 35 (24) | 39 (29) |
| bands, settled | 27 | 27 | 27 | 27 | 27 |
| band 10 | 206-215 | 209-219 | 206-215 | 206-215 | 209-219 |

- **PC1 HIT.** All four sessions loaded 21 conf.d files and every session has fixture-phase blocks. v8 loaded 22, its own required count.
- **PC2 HIT.** For A, control minus v17 per band is `[0 ×10, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 3, 3, 3, 3, 0, 0, 0]`. The tops are 206 and 209, exactly the counted run and H-mono's A.
- **PC3 HIT.** v17's `PRE_A` (fixture-phase keys in A and not in D) is one key, K1. The control's `PRE_A` is K1 plus one more key (see R1). K1's family list has 58 names, starts `Noto Sans Mono`, `DejaVu Sans Mono`, `Inconsolata`, …, and has `monospace` at index 56. Its language is `en`, `zh-TW`, with no charset. In v17 it is asked 4 times; in the control, also 4 times.

## A across the two arms: R1 HIT, in the candidate's shape

| | K1 answer | `Best score`, element 12 (LANG) | element 13 (FAMILY_WEAK) |
|---|---|---|---|
| v17 (`cjk-sub-e5`) | **Liberation Mono** (`LiberationMono-Regular.ttf`) | 0 | 1e+99 |
| control (`cjk-r5`) | **Noto Sans Mono CJK KR** (`NotoSansCJK-Regular.ttc`, index 6) | 0 | 28 |

- The key is the same in both arms and the answer differs, which is R1. The control answers a `Noto Sans Mono CJK *` face, which is the candidate's shape. The face is the **KR** one, not TC as the handoff's candidate guessed.
- The score elements are named from fontconfig 2.18.2's `FcMatcherPriority` order (`src/fcmatch.c:359-390` in the unpacked tarball the WASM build uses): index 12 = `PRI_LANG`, index 13 = `PRI_FAMILY_WEAK`. On language, both answers score 0: each face covers `en`, the first language in the request. On weak family, `Noto Sans Mono CJK KR` scores 28, its position in K1's list. In v17 nothing on the list exists in the pack (1e+99), so the choice falls to later criteria and lands on Liberation Mono.
- The rule that puts the face on the list: K1's index 28 is `Noto Sans Mono CJK KR`. It comes from the stock `65-nonlatin.conf`: line 173 of the pack's copy (extracted from the shipped v17 pack into `wasm_sdk_probe/build/wasm-fontset-v17/`, sha256 `2a0232e5…`, the value its `MANIFEST.json` lists), inside the `<prefer>` of the alias whose `<family>monospace</family>` is at its line 154, commented `hangul (ko)`. It is **the only Mono CJK face on the list**, and it is the only face on the list that the full pack has. The subset pack has no Mono family at all (read from the pack, `../RESULT.md`).
- How the readings were applied to the key sets (stated rather than glossed): the control's `PRE_A` has a second key. Its family list starts with K1's answer (`Noto Sans Mono CJK KR`, …), its language is `zh-TW`, and it is answered with the same face. Its v17 counterpart (`Liberation Mono`, …, `zh-TW`) is present in v17's A too. It drops out of v17's `PRE_A` only because D asks exactly that request. So the difference in key sets follows from K1's answer, not from a different selection. R2 as written ("the cause is upstream of fontconfig, in the selection") is not what this shows.
- **Census of everything else in A:** 12 shared keys, and none answered differently. The only keys found in one arm alone are the two follow-up requests just described. **In this document, the generic `monospace` request is the only font request whose answer depends on the pack.**

## D across the two arms: D1 HIT

- D's bands are identical in both arms: 27 each, and control minus v17 is 0 at every band. D's census is identical too: 12 shared keys, none in one arm only, no answer differs.
- Proof that D took effect is two-fold. First by request: PC3, i.e. D's requests differ from A's in that slot in both arms. Second by effect: the control's band 10 moved from 209 (A) to 206 (D), v17's value.

## v8 on A: V8-1 HIT

v8 answers K1 with **Noto Sans Mono CJK KR** (4 of 4; its language reads `en`, `tw`, which is 35's rewrite, and the scores are identical to the control's). Its 27 bands equal the control's at every band (difference 0) and differ from v17's exactly as the control does (+3 from band 10, max 4). **The shipped v8 renders this document as the full-TTC arm does. The subset (v15 onward, so v16 and v17) changed it.**

## Reading

R1 + D1, with V8-1. The corpus red on `test-docs/e1/paragraph-content.odt` is located. The `Preformatted Text` paragraph's Western font is the generic name `monospace`. With the full CJK TTC (v8, and the control arm), fontconfig resolves it to `Noto Sans Mono CJK KR`, the only face on the stock monospace preference list that the pack has. With the CJK subset (v15+), which has no Mono family, it resolves to `Liberation Mono`. Naming Liberation Mono in that slot makes the two arms identical.

Limits:

- The 3 px is shown to come from this slot by D (naming the face removes it). It is not derived from the two faces' metrics; that arithmetic was not computed.
- Which answer is "right" is not a measurement question. Native LibreOffice resolves `monospace` from whatever the machine has: on a desktop with `DejaVu Sans Mono` (position 1 in K1's list) it would be that face. This is read from the list, not measured.

## Other observations (read, not measured)

- **Reach in the corpus.** Of the 73 readable corpus documents, only this one names `monospace`, a fixed pitch, `Preformatted_20_Text`, `Source_20_Text`, `Teletype`, `Example`, `User_20_Entry`, `Variable`, `Mono` or `Courier` in `styles.xml` or `content.xml` (a regex over the XML). So this mechanism is not the explanation for the eight documents that differ by 1 px (`../judge-output.txt`): all eight carry 110 to 20,746 CJK characters and name none of these. Their cause is still not looked at.
- **What else would be affected** (not measured): any document whose Western text resolves through the generic monospace list, through `fo:font-family="monospace"`, or (by the same rule) through a fixed-pitch request that `addtopattern` appends `monospace` to. That includes a font name the pack lacks when its pitch is fixed. On v15+ such text gets Liberation Mono where v8 gave Noto Sans Mono CJK KR.

Next: the owner's decision on the corpus red (handoff Next 2). This result supplies the facts for it.
