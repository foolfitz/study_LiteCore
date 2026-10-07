# H-mono discriminator (before the run)

Written 2026-10-08 after the counted corpus comparison went red on `test-docs/e1/paragraph-content.odt` (`../RESULT.md`) and before any run here. Diagnostic, not a criterion; spec 21.2's verdict on the counted run stands whatever this shows.

## Question

Is the 3 px shift (control arm lower from band 10, the `Preformatted Text` paragraph, ASCII only) caused by that paragraph's **Asian font slot**, which can be a Noto Sans Mono CJK face with the full TTC (`cjk-r5`, 10 faces) and cannot with the subset (`cjk-sub-e5`, 5 faces, no Mono)?

## Arms

`make_variants.py` (output hashes `variants.sha256`; A is byte-identical to the fixture): A the fixture; B the same with that one paragraph's `style:font-name-asian` set to Noto Sans CJK TC (in both packs); C the same set to Liberation Mono (in the base pack, both arms). `run.py` measures A, B, C on `e2-editor-v17` and `e2-editor-v17-cjk-r5-ab` with the corpus tool's own `measure` (same page, same settle rule), one Chrome session per profile, one tool at a time.

## Readings

- Positive control (required): A reproduces the counted run: v17 band 10 top 206, control 209 (3 px), bands 0-9 equal. If A does not differ, the discriminator says nothing; stop.
- **H-mono holds**: B equal in both arms with band 10 at the control's height (about 209), and C equal in both arms at v17's (about 206). That is: naming a CJK font in the slot makes v17 look like the control, naming a Latin font makes the control look like v17.
- **H-mono fails**: B or C still differs between arms by more than 2 px. Then the slot is not the (only) cause; report the bands and do not write a second explanation before looking at the paragraph's fonts in the engine.

## What follows (not decided here)

If H-mono holds: a finding (the CJK subset since v15 has no Noto Sans Mono CJK family; Latin-only lines in styles whose default Asian font is the fixed-pitch CJK one are about 3 px shorter at this zoom than with the full TTC, and than v8). Whether to add a Mono subset to the pack, accept it as a named limit, or something else is the owner's decision, like finding 113's A/B.
