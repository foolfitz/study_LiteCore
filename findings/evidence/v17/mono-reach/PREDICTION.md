# Option C for finding 116: two measurements before the owner chooses A or B (before the runs)

Written 2026-10-08. The owner chose C: measure two things, then choose between A (add a Mono face to the CJK pack) and B (accept the difference as a named fidelity limit). Inputs: `../layout-corpus/fc-request/RESULT.md`, `findings/116-…md`. Nothing here is a gate criterion. Both measurements are diagnostic and uncounted. Nothing in `dist/` or `sdk/` is written.

## M1: what A costs in bytes (`measure_mono_cost.py`, offline, fontTools)

Construction, following finding 113's A (`tools/build_cjk_subset_ttc_pack.py`): one tier-E glyph set cut from the TC face of the full TTC and carried under five family names. For Mono, the same tier-E code points are cut from the full TTC's **Mono TC** face (face 8; faces 5-9 are Mono JP/KR/SC/TC/HK, read from the pack with fontTools). The subset tool's own `build`/`verify` are used, with the same subsetter options; only the face number differs. The result is named per region in the same way the tool renames the Sans faces. The Mono faces are appended after the five Sans faces, in the full TTC's order.

- **E5+K:** the five shipped faces plus one `Noto Sans Mono CJK KR`. This is the minimum that puts back the face the stock monospace list names (K1 in fc-request).
- **E5+M5:** the five shipped faces plus five Mono faces (JP KR SC TC HK). This mirrors 113's A fully. It also covers documents that name a Mono CJK face, and the zh-TW FIXED default's `Noto Sans Mono CJK TC` (VCL.xcu).
- Reported for each: raw bytes (what the WASM file system holds), gzip -9 and zstd -19 (what is downloaded; the host serves zstd first since 0.2.5), and the difference from the shipped `cjk-sub-e5` data (7,210,328 bytes raw).
- **Positive control (required):** the same script rebuilds the five-face collection with the tool's own `subset` + `collection`, and the result must be byte-identical (sha256) to the shipped `dist/profiles/resources/cjk-sub-e5.ce59153d3861ef9c.data`. If it is not, the deltas are not deltas from what ships; stop.
- **Verification of the Mono subset:** the subset tool's `verify` against the source Mono face (cmap, hmtx/vmtx, every outline). In the built collections, each Mono face carries exactly the Mono subset's glyph tables, and the five Sans faces are unchanged.
- No expectation is written for the size. The full TTC's two halves suggest a Mono glyph set of about the size of the Sans one, but that is not a measurement.

## M2: does 116 reach fixed-pitch 細明體 / MingLiU? (`make_fixed_probe.py`, `run_fixed.py`, Chrome)

Why these two: they are the fixed-pitch faces Taiwanese documents name most often. LibreOffice's `addtopattern` (`vcl/unx/generic/fontmanager/fontconfig.cxx:929-942`) appends `monospace`, with spacing mono, to every request whose pitch is fixed. Such requests therefore pass through the same preference list as K1. Whether real documents declare these faces with `style:font-pitch="fixed"` is not established here. It is the way LibreOffice records a fixed-pitch font, and the owner's own document declares neither face nor any fixed pitch (read from its XML).

Probe document (generated, deterministic; each line is `<label> ABC abc 123 中文字測試`; every paragraph has Western language en-US and Asian language zh-TW):

| line | Western font | Asian font | role |
|---|---|---|---|
| F1 | 細明體 (modern, fixed) | 細明體 (modern, fixed) | under test |
| F2 | MingLiU (modern, fixed) | MingLiU (modern, fixed) | under test |
| F3 | Liberation Serif (roman, variable) | 細明體 (modern, fixed) | under test (the usual Word pairing) |
| N1 | 新細明體 (roman, variable) | 新細明體 (roman, variable) | negative control: not fixed |
| N2 | Courier New (modern, fixed) | default | negative control: the metric alias names Liberation Mono |
| PC | `fo:font-family="monospace"` | default | positive control: K1's shape |

Sessions: v17, control (`e2-editor-v17-cjk-r5-ab`) and v8, each cold and one at a time, with fc-request's own `one_session` (same page, loader edit and readings). v8 is shown for reference only: 35 rewrites its language tags, so its keys are not comparable one for one.

Readings (v17 against control; answers compared by family name):

- **PC-M2a (instrument):** every session is `ready` and settled, with 6 bands, 21/21/22 conf.d files, and fixture-phase Match blocks. If not, stop.
- **PC-M2b (the probe sees 116):** a fixture-phase request whose family list starts `Noto Sans Mono` and contains `monospace` is answered Liberation Mono on v17 and Noto Sans Mono CJK KR on the control. If not, the probe cannot see the known difference; stop and report.
- **Q2-yes:** some request whose first family is 細明體 or MingLiU is answered with a different family on v17 than on the control. Then 116 reaches fixed-pitch 細明體/MingLiU as declared here. Report which slot (by the request's language: `en` first means Western, `zh-tw` first means Asian) and both answers.
- **Q2-no:** every such request is answered with the same family in both arms. Then 116 does not reach them as declared here.
- **Negative controls:** requests whose first family is 新細明體 or Courier New get the same answer family in both arms. If one differs, report it; it means the packs differ for something other than the Mono family, and Q2's attribution to Mono is weakened accordingly.
- **Bands (secondary, described, not judged):** per-band top differences, v17 minus control. The Sans and Mono faces of the full TTC have identical vertical metrics (hhea 1160/-288 in all ten faces, read with fontTools), so an Asian-slot change between them should not move a band. A Western-slot change from Liberation Mono to Mono CJK can move one, as in the fixture. Horizontal changes (Latin advances) are invisible to bands. **So Q2 is read from the answers, not from the bands.**

My expectation (written so a miss can be seen): Q2-yes in both slots. For the Western slot (`en`), Liberation Mono on v17 against Noto Sans Mono CJK KR on the control, as for K1. For the Asian slot (`zh-tw`), a Noto Sans CJK face on v17, because the language criterion ranks before the weak family list and Liberation Mono does not cover zh-TW, against Noto Sans Mono CJK KR on the control. Bands: little or no vertical change on F1-F3, because their lines carry CJK text whose height dominates.

## What follows (not decided here)

With M1's bytes and M2's reach, the owner chooses A or B. Under A, a new pack identity and profile (no link needed) and a rerun of what the pack touches. Under B, an appended spec section that names the limit and says what "V6 met" means, with the criterion not edited.

## If never done

The owner chooses without these numbers, or V6 stays not met.
