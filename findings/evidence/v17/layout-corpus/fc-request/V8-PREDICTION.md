# v8 on document A (before the run)

Written 2026-10-08 after `run.py`'s four sessions (RESULT.md is not yet committed), before any v8 session here. Diagnostic, Chrome, uncounted. The handoff lists this as not established: "Whether v8 behaves like the control on this fixture was not measured".

## Why

The fc-request run found that the generic `monospace` request for the `Preformatted Text` paragraph (call it K1: family list beginning `Noto Sans Mono`, `DejaVu Sans Mono`, … with `monospace` at index 56; language `en`, `zh-TW`) is answered with `Noto Sans Mono CJK KR` in the full-TTC arm and with `Liberation Mono` in the subset arm (`summary.txt`). v8, the shipped profile, carries the same full CJK pack as the control arm (`cjk-r5.b76b0433203017ca.data`, read from `dist/profiles/e2-editor-v8/sdk-manifest.json`) and base pack `base-r5` (which still has `35-lang-normalize.conf`; v17 has `base-r5-no35`). Whether the subset changed what the shipped product renders for this document decides how the owner's choice is framed.

## Instrument

`run_v8.py` calls `run.py`'s own `one_session("e2-editor-v8", "A")`: same page source (cutover page repointed to v8), same FC_DEBUG loader edit, same reading of bands. It then compares against the A sessions already recorded in `fc-request.json`.

## Positive control (required)

The session boots `ready`, opens A `ready`, gives 27 settled bands, and loads 22 conf.d files (v8's base pack includes 35; V3 measured 22 on v16, which has the same base pack), with at least one fixture-phase Match block. If any of these misses, stop and report.

## Readings

- **V8-1 (v8 renders like the full-TTC arm):** a fixture-phase block with K1's exact family list is answered `Noto Sans Mono CJK KR`, and v8's 27 bands equal the control's within 2 px (expected: 0 everywhere, band 10 at 209). Then the subset (v15 onward) changed this document's rendering relative to the shipped v8. Expected, because v8 has the same CJK pack and the same `65-nonlatin.conf` monospace list. 35 rewrites language tags only, and K1's language score is 0 on `en` for both candidate faces.
- **V8-2 (v8 renders like the subset arm):** answered `Liberation Mono`, and the bands equal v17's within 2 px. This would contradict the pack-based explanation; report it and do not reconcile.
- **V8-3:** anything else, including no block with K1's exact family list (35 could, in principle, change the expanded list), or bands that equal neither arm. Report the blocks that name `monospace` and the per-band differences against both arms, and draw no conclusion from them.

## Not claimed either way

This says nothing about whether native LibreOffice, or a desktop with other fonts, resolves `monospace` the same way. On a desktop that has `DejaVu Sans Mono` (position 1 in K1's list), that face would rank first in the weak-family order. That is inference from the list, not measured.
