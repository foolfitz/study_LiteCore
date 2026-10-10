# opus review of judge_p.py (2026-10-10; subagent, read-only; prompt `review-prompt-judge-p.md`). Final report, verbatim. Its mutated copies are in `opus-mutations-judge-p/`; `opus-mutations-judge-p/judge-on-opus-mutations.txt` is the main session's own run of the reader on them.

Review of judge_p.py (sha 1461fc03…) over wrapper 3dad37cb… and probe dbad93c0…. Repo untouched. I ran `judge_p.py --page 18c8afbe… --prefix shipped`: 8 FAIL, exit 1, the same as judge-shipped.txt. I also ran the reader on mutated copies in scratch. While I was reviewing, the parent committed P (706e8565, page 36c2b18b…), so I checked the reader's assumptions against that real paint() too.

BLOCKING: none found.

Q1. Cells, thresholds and fields: no defect found.
- P1 (judge_p.py:107-130): per letter, it takes the staleBytes delta from the R2 keydown snapshot (blit_bytes_probe.py:136-137) to the next letter's snapshot. The snapshot is a capture listener on document and runs synchronously before the page handles the key. The last key runs to r2.final (:94).
- final and dataset.r2 are written in the same 200 ms tick, so the report is self-consistent. Anything after the last tick is missing from both, and READ comes at least 1.5 s after quiet.
- `f > 0.02` matches "<= 2 %". M6a (exactly 2 %) PASS; M6b (2 % + 4 bytes) FAIL.
- Stale/fresh on the actual P page: every restore is a 7-arg put (web/e2-editor-app.js:1087) of a lastTiles image that paintBand already put with 3 args (:951 new ImageData, then :1122). So restores always count as stale, at dirty-rect size (blit_bytes_probe.py:103-110), and R2-fresh means exactly "new band's first blit".
  - Cross-check on the shipped reports: R2 freshCalls equals len(raw.blits) (228/228 chrome p1, 143/143 firefox 123b), and every fresh dy is a multiple of 1023.
- 123-B fields are right:
  - keys from raw.keys (:133)
  - toasts from raw.r2.toasts (:135-143)
  - allCurrent from the top level (:144)
  - bottom band from raw.blits [t,y,h,rev] against raw.canvasHeight (:147-150)
- Two extras, neither able to flip an honest verdict:
  - The ">= 1 toast" positive control is grounded. #toast is static (e2-editor.html:329), the two boot toasts appear in all five shipped reports, and P does not touch toast().
  - The raw.dpr binding is float-safe. M4 (2.0 / 1.0) PASS; M4b (1.25) REFUSED.

Q2. Constructions (all NON-BLOCKING):
- N1 (spec says FAIL, reader says PASS, but only on a page that breaks §16.1): the reader treats "first put of any ImageData" as fresh (blit_bytes_probe.py:97, :111-115).
  - A restore through a never-seen ImageData is excluded at any size. Examples: save-under via getImageData, or band pixels re-wrapped in a new ImageData.
  - M5 books 6 whole bands per key as fresh, and the reader says PASS.
  - The committed P page does neither, and P-U2 gates this first.
  - Optional per-report guard: every raw.r2.fresh dy % 1023 == 0, and R2 freshCalls == len(raw.blits). Both hold on every shipped report.
- N2 (lost discrimination): the reader binds the requested window (:45) but not the resulting canvas that made the red case red.
  - M2 takes the real 800-wide Firefox report (unfixed shipped page, canvas 1496 x 36,996) and relabels it 797. All three Firefox 123-B cells PASS and nothing is refused.
  - The −12 desk offset belongs to one Firefox version, and this tree has already had a snap auto-update.
  - The release verdict cannot flip while Chrome (Emulation, deterministic) and 123-U still discriminate.
  - Binding raw.canvasWidth/Height = 1490 x 36,847 for 123b (the canvas §16.8 line 799 names) would turn drift into REFUSED.
- Checked, no defect found:
  - Toast observer: #toast is static. It reads textContent at callback time (blit_bytes_probe.py:142), but the TILE_NOT_PAINTED toast is not overwritten within its task, and the other two cells fire with it.
  - raw.blits 600 cap: runs have 142-228 fresh blits.
  - Re-layout: allCurrent and the bottom-band cell both use the final canvasHeight.
  - A band re-rendered after the last key is excluded from P1 and is the evidence 123-B wants.
- N3: the cell "last band blitted after the last key" (:149-150) is implied by allCurrent being non-None on any report the wrapper produces. probe_typing_latency.py:189-201 already needs a blit with t >= last key and y+h >= height. So that cell is redundant and harmless, and K6 is only reachable by hand edit, which §34.2 excludes.

Q3. Red cases: every gated cell has one except 123b "every key typed" (:134). It reads raw.keys, a different field from K7's r2.keys. M3 drops one raw.keys letter and only that cell goes red, so the code is right. The three red cases §16.3 requires are all present, so under §34 this gap doesn't matter.
- For bindings, only the runner has a committed red case. README.md:24 says the 800-wide report is refused for the wrong window, but no committed output shows that: judge-shipped-before-ff797.txt was refused for a missing file. M1 confirms the claim (REFUSED on windowRequested [800,1000]).

Q4. Sound.
- The offsets come from two measured canvases: Chrome at 800 gives 1490, Firefox at 800 gives 1496. The 797 window was predicted to give 1490 x 36,847 before the run, and it did; all three cells FAIL in judge-shipped.txt.
- The per-browser binding is correct (:45, M1).
- The criterion moved before any run that could satisfy it, and §16.3 had pre-written the prescription.
- Counting it as "因執行而修 1" (§16.8 line 803) is right, because an execution's output forced the edit. §16.6 counted the instrument preparation as 0 because no run forced that one.

Minor docs:
- p-release/README.md:3 still gives 123b `--window 800x1000` for both browsers.
- Its claim "sha256 recorded with each reading" is not true of judge-shipped.txt, and the reader's PASS line does not echo the bound --page. Record both with the counted reading.

Scratch: scripts/mutate.py; M1-ff-window800-real/, M2-ff-drift-unfixed-page/, M3-123b-key-missing/, M4-dpr-float/, M4b-dpr-1.25/, M5-whole-band-as-fresh/, M6a-exactly-2pct/, M6b-2pct-plus-4/, M7-last-key-window/ (each holds m-{chrome,firefox}-{p1,123b}.json).
