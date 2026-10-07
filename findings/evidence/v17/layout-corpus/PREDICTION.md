# Prediction, before the run: the COUNTED corpus layout comparison, v17 vs v17-cjk-r5-ab (spec 26.3 V6, 21.2 as amended by 27)

Written 2026-10-07, before any run of `compare_layout_corpus.py` on these profiles. The reader (`judge.py`) and its red cases (`selftest.sh`, `selftest-output.txt`) were committed in `d6db60ea`, also before the run.

## Command (one invocation, Chrome, machine quiet, after the product-path chain and the merge shakedown have finished)

```
python3 tools/compare_layout_corpus.py --profiles e2-editor-v17 e2-editor-v17-cjk-r5-ab --out ../findings/evidence/v17/layout-corpus
```

Tool `wasm_sdk_probe/tools/compare_layout_corpus.py` sha256 `21f90c31…` (the dry run's; recorded before and after the run). The two profiles share wasm `ad3f68bb…`, loader, worker and base pack `base-r5-no35`; they differ only in the CJK pack (`cjk-sub-e5` = the E-level subset under five family names, against `cjk-r5` = the full TTC). Single variable, as 20.3/21.2 intend.

## Criterion (not restated here; `judge.py` is its executable form)

Spec 21.2 per comparable document, 27.1 T = 2 px, 27.2 "not measured" and the equal-sets conditions, and the count of measured documents stated. Verdict PASS or RED as `judge.py` prints it. The red case for the instrument (it sees 113) is v16/v15 and is not redone (27.3).

## Predictions

- **K1.** `judge.py` VERDICT PASS.
- **K2.** Not comparable: the dry run's 5 (3 non-zip, `l3-high-ratio.odt`, `l3-too-many-entries.odt`), in both arms.
- **K3.** Not measured: the dry run's 23, in both arms (judge's spec-27.3 note says "same set: True"); measured 48.
- **K4.** No measured document has a top difference above 0 px. (Weaker than the criterion on purpose: if 1-2 px differences appear they pass the criterion but are reported as such.)

## Named risk (why K1 could miss on v17 and not on the dry run)

With 35 gone, a font name that is not one of the five Noto Sans CJK families (`思源黑體` and the like) resolves to a regional face (KR, by V3), in both arms. In `cjk-sub-e5` all five faces carry the same E-level TC glyphs and metrics; in `cjk-r5` the KR face carries Korean glyphs, whose advances for some punctuation may differ from TC's. If a measured document goes red, look first at which characters sit on its first differing line (by Unicode class and code point, no document text in the evidence), and only then at anything else.

## What a miss means

- K2/K3 miss: first suspect the instrument (spec 27.3), not v17; do not judge.
- K1 miss on a measured document: spec 21.2 says that document is red; 26.3 V6 is not met until it is explained. Not adjusted.
- If this run is never made: 20.3's "never done" sentence (v17's layout is measured against v8 only on the product-path fixtures and 113's probe fixture, not on the corpus).
