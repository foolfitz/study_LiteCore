# fc-request discriminator (before the run)

Written 2026-10-08 after H-mono failed (`../mono-discriminator/RESULT.md`) and before any run here. This is the step that RESULT pre-registered: look at what the engine's fontconfig is asked for the red document in each arm, before writing any other explanation. Diagnostic, Chrome, uncounted. Spec 21.2's verdict on the counted run stands whatever this shows.

## Question

While `test-docs/e1/paragraph-content.odt` is opened and laid out, which font requests reach the engine's fontconfig in each arm, and what does it answer? In particular, what is asked and answered for the `Preformatted Text` paragraph's **Western** font? The fixture's `Preformatted_20_Text` style sets only `fo:font-family="monospace"`. H-mono varied only the Asian slot and never the Western one.

## What the source says the request looks like (read, not run)

- `vcl/unx/generic/fontmanager/fontsubst.cxx:100` (`FcPreMatchSubstitution::FindFontSubstitute`) asks fontconfig about every font selection that is not already in its cache, and the cache is keyed on all the selection's attributes. So the hook does not ask only about missing names: V3's log shows `Liberation Serif` asked although the pack has it. One request per distinct selection per process.
- `vcl/unx/generic/fontmanager/fontconfig.cxx:1073` (`Substitute`): the family is the target name, plus `serif`/`sans` by family type; the language is the selection's language; a charset is added only for glyph fallback. Then `addtopattern` (`:929-942`) adds spacing mono, with `monospace` appended to the family list, only when the selection's pitch is fixed.
- The log prints each pattern **after** `FcConfigSubstitute`, so `askedFamily` is the alias-expanded list. Its first element is not necessarily the name the document gave. For that reason the paragraph's request is **identified by experiment, not by guessing its expanded shape** (next section).

## Arms, documents, instrument

- Profiles `e2-editor-v17` (`cjk-sub-e5`) and `e2-editor-v17-cjk-r5-ab` (`cjk-r5`, the full TTC): the counted run's two arms.
- Documents (`variants.sha256`): **A** is the fixture, byte-identical (`920ca5d5…`, the same bytes as H-mono's A). **D** (`42faf124…`, `make_variant.py`) gives that one paragraph an automatic style whose only added property is `style:font-name` (the Western slot) = Liberation Mono, a font in the base pack and therefore in both arms. Nothing else changes; the content.xml diff is the font-face declaration, the automatic style and the paragraph's style name.
- Four cold Chrome sessions, one at a time, each opening exactly one document as its first: A on v17, A on the control, D on v17, D on the control. A fresh session for D keeps D's requests out of the cache that A's session filled.
- Page: the cutover page source repointed per profile, as `compare_layout_corpus.measure` does. On top of that, `probe_fc_debug`'s two page edits (a Worker wrapper that keeps the forwarded stdout/stderr, and `debug: true`) and its loader edit (`ENV.FC_DEBUG="1153"`). Everything is served from a scratch mirror; `dist/` is not written, and the shipped loader's bytes are checked before and after. Environment locale as in the counted run (`LANG=zh_TW.UTF-8`; `navigator.languages` recorded).
- Readings: bands come from the corpus tool's own `settle`/`runs`; Match blocks come from `probe_fc_debug.match_blocks`. The driver is `run.py`, composed from existing functions; no tool file is edited. The census and diff code was given red cases on V3's committed data first (`selftest.py`, `selftest-output.txt`).
- Census key: (`askedFamily` list, `askedLang` list, `askedCharset`). Answer: (`bestFamily[0]`, file basename, index). Answers are compared across arms by **family name**, because files and TTC indexes differ between the two packs by construction.

## Positive controls (all required; if one misses, stop and report — the run says nothing)

- **PC1 (instrument alive):** every session loads 21 conf.d files (V3's v17 set) and has at least one fixture-phase Match block.
- **PC2 (the effect is in these sessions):** for A, 27 bands in both arms, bands 0-9 equal, and control minus v17 at band 10 is +3 px, with max |difference| 4 px. This is the shape of the counted run and of H-mono's A. If the absolute tops are not 206/209 but the shape holds, PC2 holds and the tops are reported. If FC_DEBUG or `debug: true` changes the layout so that the shape is gone, the logs come from sessions that do not show the red; stop.
- **PC3 (the paragraph's request is identified):** in each arm, the fixture-phase keys present in A and absent in D (`PRE_A`) are non-empty, and at least one `PRE_A` key's family list contains `monospace`. `PRE_A` is the paragraph's Western request, because D differs from A in that slot only. If `PRE_A` is empty, D's style did not change any request (not applied, or the request was cached at boot). The identification has then failed: report the full A census across arms as data, and locate nothing.

## Readings (A across arms, on `PRE_A`)

- **R1 (located at fontconfig's answer):** `PRE_A` has the same key(s) in both arms, and the answer's family differs. The handoff's candidate is the specific shape where the control answers a `Noto Sans Mono CJK *` face and v17 answers something else. If R1 holds in that shape, the candidate is no longer only a candidate at the request level. Whether that face difference accounts for 3 px is a separate question; it is not claimed here (see D). If R1 holds in another shape, report the faces and do not bend the candidate to fit.
- **R2 (located at the request):** `PRE_A`'s keys differ between the arms (family list or language). The cause is then upstream of fontconfig, in the selection the engine builds, and not in the answer. Report.
- **R3 (not located):** `PRE_A` has the same keys and the same answer families in both arms. The paragraph's Western face is then the same in both arms, and the cause is not in this request or its answer. Do not write a second explanation; report every other census difference as data only.

## Readings (D across arms: does naming the Western face remove the red?)

- **D1:** PC3 holds, and D's bands are equal in both arms (same band count, max |difference| ≤ 2 px). Naming Liberation Mono in the Western slot removes the difference, so the difference lives in the Western slot's resolution. Proof that D took effect is PC3 (D's requests differ from A's in that slot). If, in addition, the control's band 10 top moves from its A value toward v17's, that is a second proof, by effect.
- **D2:** PC3 holds and D still differs between the arms by more than 2 px. Naming the Western face does not remove the difference, so the Western slot is not the (only) cause. Report.
- R1 together with D1 locates the cause: the generic `monospace` in that paragraph resolves to a different face when the full TTC is present. Any other combination is reported as it falls, without a story built to join the pieces.

## Recorded, not judged

Every fixture-phase key that appears in only one arm, and every shared key whose answer family differs, in both A and D. Other paragraphs whose fonts differ between the packs by construction will show up here; they are listed for Next 2 of the handoff, but they are not the reading. Bands 0-9 being equal already says those paragraphs do not move anything before band 10.

## What follows (not decided here)

The owner decides what to do about the corpus red (handoff Next 2, in the shape of finding 113's A/B/C), and that decision comes after RESULT.md. Whatever is chosen is written up as an appended spec section before acting.

## If never done

The corpus red stays unexplained, V6 is not met, and v17 is not cut over (handoff's "if never done", unchanged).
