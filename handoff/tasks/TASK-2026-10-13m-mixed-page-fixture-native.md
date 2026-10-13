# TASK 2026-10-13m — P1's mixed-page fixture, and its page rectangles on native LibreOffice

**Why.** `specs/SPEC-M3-link-batch.md` §5 P1 (as written by §10.8) needs, beside the 60-page document, "a new
fixture with **mixed page sizes and orientations**", so that the page number cannot pass by assuming every page
has the same height or the same x. The v20 engine does not exist yet (the owner links it later); this task only
prepares the fixture and measures it on native LibreOffice, so that the v20 round has a reference. **No browser,
no WASM, no product bytes.**

**Do not touch:** `dist/`, `Makefile`, `src/`, `sdk/`, `editor-shell*/`, `web/`, any profile, pin or binding.

## 1. The generator (new file)

`wasm_sdk_probe/tools/create_mixed_page_document.py`, in the shape of `tools/create_long_document.py` (read it:
exact page counts by explicit breaks, a marker on every line, `--out`, `--self-test`). Requirements:

- Exactly **8 pages**, in this order of page styles (each page its own master page, switched by a paragraph style
  with `style:master-page-name`, which also forces the break):
  1. A4 portrait (21 × 29.7 cm); 2. A4 landscape (29.7 × 21 cm); 3. A4 landscape; 4. A5 portrait
  (14.8 × 21 cm); 5. US Letter portrait (21.59 × 27.94 cm); 6. A4 portrait; 7. A3 landscape (42 × 29.7 cm);
  8. A4 portrait.
- Margins 2 cm everywhere. Each page carries a heading `MP-PAGE-{n}` and enough lines `MP-P{n}-L{k}` to be
  visibly non-empty but **never overflow** onto a second sheet (keep the line count well under what the smallest
  page, A5, holds).
- `--self-test` verifies the XML it writes (8 master pages referenced, each page's dimensions as listed) and exits
  non-zero on a mutation of its own output (show it red once).
- Commit the generator; **do not commit the .odt** (the runner builds it into a scratch directory, as for the
  60-page document).

## 2. The native measurement

Reuse `tools/native_page_rectangles.cpp` unchanged (read `findings/evidence/link-batch/page-rectangles/README.md`
for how it is built and run; `native-lok-26-8/build/instdir` is read-only; `SAL_USE_VCLPLUGIN=svp`). Write a small
runner `tools/run_native_mixed_page_rectangles.sh` (or extend nothing: do not edit `run_native_page_rectangles.sh`)
that generates the fixture into `SCRATCH_DIR` (outside the repository) and runs 3 fresh processes. Output under
`findings/evidence/link-batch/page-rectangles/mixed-round-<UTC stamp>/` (raw `.jsonl`, `.stderr`, `.exit`,
`inputs.sha256` with the fixture's sha256, the commands).

**Predictions** (write them into the README **before** the first run, then do not edit them):
- P-M1: 8 rectangles; `getParts()` = 8.
- P-M2: each rectangle's width × height equals its page style's size in twips (1 cm = 566.93 twips) within 1 %;
  pages 2, 3, 7 are wider than tall.
- P-M3: rectangles' `y` strictly increase in string order, with a gap between consecutive pages.
- P-M4 (open, no expectation): how `x` relates across pages of different widths (left-aligned at one x, or
  centred on the widest page). Record what native does; the page-number rule intersects both axes, so either is
  fine, but the v20 runner must know which.

## 3. Deliverables

- Commits: the generator, the runner, and `findings/evidence/link-batch/page-rectangles/MIXED.md` (English,
  beginning with `## SUMMARY` ≤ 20 lines): the predictions block (verbatim), the eight rectangles as measured (all
  three rounds; say whether they are identical across rounds), each prediction's verdict, the fixture's sha256 and
  how to regenerate it byte-identically (is the generator deterministic? show two runs' sha256).
- English commit messages ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, no
  `Claude-Session:` line. Retry if `.git/index.lock` exists.
- If native LibreOffice does not lay out a page style as expected (for example a page that overflows), report it;
  do not tune the fixture until the prediction passes — a changed fixture is a new fixture, say so.
