# Adversarial review: v18 (`cjk-sub-e10`, finding 116, spec §28), 2026-10-08

## SUMMARY

**No BLOCKING finding.** Nothing I read says the e10 pack is wrong, or that v18 must not be cut over once W4 and W6 land. The gaps are in how the remaining criteria are worded and in how the reports bind to the pack.

- **Tool (read).** `verify()` really does compare every table of each built face with its input, byte for byte, reading the raw bytes at the TTC face's own offsets.
  - Shared-table saving keys on exact bytes, so it cannot alias a Mono table onto a different Sans table.
  - The `TC_FACE` patch is restored in `finally`.
  - The Mono name records are checked against full-TTC faces 5–9, which is the right reference.
  - Correctness against face 8 rests only on the subset tool's own verify (cmap, hmtx/vmtx, outlines). Vertical metrics, VORG/BASE, layout tables and hints are not compared.
- **fontconfig view (read from the W3/W5 logs).** The subset Mono KR face equals the full one in every printed field: index 6, version, capability, genericfamily 3.
  - Neither face has a spacing element, so the dual/mono classification does not differ. The file sits at the same scan position in both arms.
  - Its charset has 25,767 code points, set-equal to the Sans half. The full face has 44,810.
  - It loses language coverage for exactly `bin gn ig ko miq`.
- **So "v18 resolves like the control" is false in general** (inference, #8). LANG ranks above FAMILY_WEAK. A monospace or fixed-pitch request tagged gn/ig/bin/miq should therefore go to Liberation Mono on v18 and to Noto Sans Mono CJK KR on the control. This limit is not registered.
- **Diagnosis.**
  - GENERIC_FAMILY ranking before LANG is in the source (`fcmatch.c:369-372`), not only in the winners' score vectors.
  - But only fixed-pitch requests carry a genericfamily value. The generic-`monospace` K1 request has none (`48-guessfamily.conf` is not loaded). v17's Liberation Mono answer for K1 is therefore a FONTVERSION / file-order tiebreak, not a monospace classification.
- **"Like the control" is not "like v8".**
  - v8 differs from the control by up to 7 px on the fixed-pitch probe (114). Nothing in W4 or W6 compares v18 with v8 on fixed-pitch text.
  - Glyph forms also differ (TC against KR); that one is registered.
  - Q2 is not load-bearing for the choice of A, but W5 should be cited as "on this probe" only.
- **SHOULD, best fixed before the remaining steps run.** At 07:50 the product path was in round 3 of 6 (Chrome round 3; the Firefox rounds follow, so it finishes about 08:40). Merge, the owner's document and the corpus come after it.
  1. W4 says "VERDICT is not RED", and a reader STOP (exit 2) satisfies that. Pin it to PASS.
  2. `PREDICTION.md:50` says the chain stops on any runner error or missing report. `chain.sh` stops only when a product-path report is missing.
  3. M1–M4 and O1–O2 are not labelled as criterion or descriptive.
  4. No W4/W6 report records the manifest or the CJK pack. v17, v18 and the control share the wasm prefix, which is the only identity the corpus file records. Hash dist's v18 manifest and pack at chain end. At 07:50 they were `456e9a72…` and `06976180…`, matching the archive.
  5. Two W1 clauses are not computed by `--check`. The size bound is printed, never compared. The red cases live in `--self-test`, and an altered pack on disk passes `--check` because it is matched by name only.
- **NOTE.**
  - `check_m3_assets.py:1015-1021` still pins `cjk-r5`. The 10-08 handoff says to re-pin it to e5; §28.4 says e10.
  - v18 is smaller than the shipped v8 raw, gzip and zstd. The registered "+7.2 MB / +6.2 MB" are relative to v17, which never shipped.
  - Finding 116's 未做 bullet on Mono bytes is stale.
  - The product-path selftest output is filtered ("P2 notes:" with no payload). I re-ran it read-only, and the red case is genuine.

## What I did

- Read the files named in the brief, plus `sdk/sdk-worker.js`, `tools/package_m3_engine.py`, `tools/check_m3_assets.py`, `tools/compare_layout_corpus.py`, the fontconfig 2.18.2 source and conf.d in `wasm-lite/build-headless-probe/workdir/UnpackedTarball/fontconfig/`, and host 0.2.7's `engine/MANIFEST.json`.
- Commands run (all light): greps, awk/python parses of committed fc logs and JSON, `sha256sum` of the v18 manifest and e10 data, `python3 --version` for fontTools, and one run of `findings/evidence/v17/product-path/judge.py`. That judge is a reader over committed JSON; it writes nothing.
- Not run: make, any browser, the pack tool (neither `--check` nor `--self-test`), and any `tools/run_*.py`.
- Written: only this file.
- Labels used below: **[read: path]** means read in source or output. **[inference]** means my reasoning, not measured.

## Findings

### 1. SHOULD — W4's pass condition is satisfied by a reader STOP

- **Where.** `specs/SPEC-M3-paragraph-merge.md:930`; `findings/evidence/v18/layout-corpus/judge.py:51-54`, `:136`, `:139`, `:149`; `findings/evidence/v18/PREDICTION.md:41`.
- **Evidence [read].**
  - W4 reads: 「VERDICT 不是 RED」.
  - The reader's `stop()` prints `STOP: … Not judging.` and returns 2, with no VERDICT line. It stops on a missing `comparison.json`, a profile mismatch, a document count other than 76, or a cross-check DISAGREE.
  - PREDICTION C1 expects `VERDICT PASS`.
- **Why it matters.** Read literally, "not RED" is met by a STOP, which means nothing was judged. The prediction is stricter than the criterion it predicts.
- **What settles it.** Append, before the corpus step runs (it is last in the chain): W4 = reader exit 0 and `VERDICT: PASS`; a STOP counts as "not done", so §28.4's never-done default applies.

### 2. SHOULD — the written stop rule is not what `chain.sh` does

- **Where.** `findings/evidence/v18/PREDICTION.md:50` against `findings/evidence/v18/chain.sh:22-25` and `:27-35`.
- **Evidence [read].**
  - PREDICTION says: "A runner error or a missing report stops the chain (`chain.sh` aborts on a missing report). Nothing after it runs."
  - `pp()` aborts only when the product-path report is missing; it records `exit=$RC` and carries on even when the exit code is non-zero.
  - `step()` (merge, control, pair, owner's document, corpus) never aborts on anything.
  - The script's own header (`chain.sh:4`) describes this correctly: "A missing product-path report aborts the chain".
- **Why it matters.** A crash in the merge runner would be followed by the owner's-document and corpus runs, contrary to the pre-written rule. The data stays valid, but the pre-registration is false as written, and a reader of PREDICTION will assume a guard that does not exist.
- **What settles it.** Before the merge step starts (product path ends about 08:40), append an amendment to PREDICTION that states what the chain actually does, or make `step()` abort on a non-zero exit or missing output. Do not do both.

### 3. SHOULD — no W4/W6 report can show which CJK pack it ran on

- **Where.**
  - Runtime identity: `findings/evidence/v18/w1-w2/profile-files.txt`.
  - Product-path report fields: `findings/evidence/v18/product-path/e2-editor-v18-chrome-r1.json`.
  - Reader: `findings/evidence/v17/product-path/judge.py:127-131`.
  - Corpus tool: `wasm_sdk_probe/tools/compare_layout_corpus.py:128`.
- **Evidence [read].**
  - v17 and v18 have byte-identical `probe.js`, `probe.wasm` and `sdk-worker.js`. At runtime they differ only in `sdk-manifest.json` and the CJK pack.
  - The v18 product-path report's `candidateCutover` is `{profile, pageSha256, pinBefore, pinAfter}`, and both pins are wasm hashes.
  - Grepping that report for `456e9a72`, `cjk-sub-e10`, `06976180`, `subset-E10` and `sdk-manifest` finds 0 occurrences of each.
  - The product-path judge's P2 does not assert `candidateCutover.profile`.
  - The corpus tool writes `{"profile", "wasm"[:16]}` per arm. That wasm prefix is the same for v17, v18 and the control, so the reader's "wasm differs" note cannot tell the arms apart.
  - Runtime: the worker rejects a pack whose sha256 differs from the manifest's (`wasm_sdk_probe/sdk/sdk-worker.js:624-628`).
  - Measured by me at 07:50 (+08:00), mid-chain: `dist/profiles/e2-editor-v18/sdk-manifest.json` = `456e9a72ab26…` and `dist/profiles/resources/cjk-sub-e10.06976180177c8bd2.data` = `06976180177c…`, both equal to the archive's `SHA256SUMS`.
- **Why it matters.** CLAUDE.md's archive lesson says a profile is five bound identities, not one artifact. Here the binding from W4/W6 evidence to the e10 pack is indirect: page sha → worker URL path → whatever manifest sits in that dist directory at run time. The worker's own check narrows the residual risk to the manifest file being rewritten during the chain. That is unlikely, but nothing would show it.
- **What settles it.** At chain end, write the sha256 of the v18 manifest and of the e10 `.data` next to the reports, and compare them with `w1-w2/v18-manifest.sha256` and the archive's `SHA256SUMS`. Long term, have the runners record the served manifest's sha256.

### 4. SHOULD — PREDICTION lines M1–M4 and O1–O2 are not labelled criterion or descriptive

- **Where.** `findings/evidence/v18/PREDICTION.md:23-36` and `:46-50`; spec `:932` (W6).
- **Evidence [read].**
  - W6's merge clause is the runner's own result plus the `--pair` document count.
  - PREDICTION M2 adds a split (40 `verified-key-undo` / 14 `refused` / 2 `verified-selection-delete`), per-case refusal reasons, and "M2-0 true on all three fixtures". M3 expects "42 + 42 + 14".
  - "What a miss means" names only Q4, O3 and C4 as descriptive.
- **Why it matters.** Suppose v18 gives 56/56 with a different split, for example a refusal that becomes `verified-key-undo`. Whether W6 is met is then decided by whoever reads the result (CLAUDE.md §2, §8).
- **What settles it.** Append, before the merge step: which of M1–M4 and O1–O2 are criteria and which are descriptive.

### 5. SHOULD — two W1 clauses are not computed by the tool that W1 says decides them

- **Where.** Spec `:927`; `wasm_sdk_probe/tools/build_cjk_subset_mono_pack.py:186-187`, `:204-230`, `:245-260`; `wasm_sdk_probe/tools/build_r5_profiles.py:154-156`.
- **Evidence [read].**
  - W1 has a size bound: 「zstd −19 大小 ≤ cjk-sub-e5 ＋ 300,000 位元組（超過就停）」. Its red cases read: 「`--check` 對「改掉一個 Sans 面的一個表」與「改掉一個 Mono 面的一筆 name 記錄」都必須不過」.
  - The tool computes `sizes` and prints them, but nothing compares them with the bound.
  - The red cases are in `--self-test`, which runs `verify()` on an altered copy built in a temp directory. `--check` always rebuilds from source and cannot be pointed at an altered pack.
  - For the pack in `dist/profiles/resources/`, `--check` tests only existence by name (`:253-255`).
  - `create_pack` rejects an existing hashed file with wrong contents only when it builds into that directory (`build_r5_profiles.py:154-156`). Under `--check` it builds into a temp directory, so that guard does not run.
- **Why it matters.**
  - The size clause is decided by reading `check.txt`, which is drafter judgement (§8), although W1 is labelled form 二. The measured value (+144,587) is far inside the bound, so the impact is nil today.
  - The "--check must fail" wording is not what was demonstrated. A pack altered on disk would pass `--check` and `make`; only the worker's sha256 check would catch it, at load time.
- **What settles it.** Add the bound and an on-disk sha256 comparison to `--check`. Or append a correction to W1 that says what `--check` and `--self-test` actually establish.

### 6. NOTE — what `verify()` establishes, and what it leaves to other evidence

- **Where.** `wasm_sdk_probe/tools/build_cjk_subset_mono_pack.py:90-170`; `wasm_sdk_probe/tools/build_cjk_subset.py:96-141`.
- **Assessment [read; fontTools behaviour from its source as I know it, inference where noted].**
  - `getTableData` on a face of a TTC returns the raw bytes at that face's directory offset whenever the table is not loaded, so the comparison is real.
    - `name` (and `head`, compared field by field) are compiled from the parsed table. Compiled against raw can only produce a false difference, never hide a real one.
  - Shared tables: fontTools' `tableCache` keys on `(tag, exact bytes)`. A Mono table is therefore shared with a Sans table only when the two are identical, which is harmless.
    - `head` is shared within each half, and its `checkSumAdjustment` is overwritten by the last face written. That field is excluded by design.
  - The name reference (full-TTC faces 5–9, compared as sets) is the right one for fontconfig and LibreOffice, which key on names. A face-order swap would be caught twice: by the family check and by the comparison of face *i* with full face 5+*i*%5.
  - The monkeypatch is restored in `finally` (`:94-104`). The only reader of `TC_FACE` is `load_face()`. `sans_collection()` runs before the patch window. If e5's tool were ever called inside the window, e5's `SHIPPED_SUBSET_SHA256` guard would catch it. Acceptable.
  - Gap (a): for the Mono half, `verify()` compares against the very intermediate it was built from. Correctness against face 8 rests entirely on the subset tool's `verify`: cmap for the wanted code points, hmtx/vmtx for kept glyphs (stopping at the first difference), and outlines through a recording pen, which ignores hints.
    - Not compared with face 8: OS/2 and hhea/vhea vertical metrics, `VORG`, `BASE`, GSUB/GPOS, CFF hints. W5's equal bands are the only empirical check on line metrics, and nothing exercises vertical writing.
  - Gap (b): "the same tier-E code points" is not asserted. Each half computes `wanted = tier ∩ that face's cmap` (`build_cjk_subset.py:104-105`).
    - I checked it from fontconfig's side instead. In `findings/evidence/v18/w3-w5/e2-editor-v18-P-fc-log.txt`, the printed charsets of subset Sans KR and subset Mono KR are both 25,767 code points and set-equal (my parse of the hex bitmaps).
  - Gap (c): determinism. The in-process double build covers only `collection()`; the subset is built once.
    - Cross-process determinism is shown by `--check` regenerating the manifest, with the pack's sha256, and matching the committed one. `build.txt`, `check.txt` and `make.txt` all give `06976180…`.
    - Unlike e5's tool, the Mono subset sha is not pinned, and the fontTools version (4.61.1 on this machine) is not recorded. Drift would fail `--check` loudly, and the pack is archived, so this is a reproducibility note only.
  - Gap (d): no red case for a wrong Mono glyph table, or for swapped Mono faces. The logic would catch both, but neither has been shown red (CLAUDE.md §6).

### 7. NOTE — fontconfig sees the subset Mono face like the full one, except for charset and languages [read]

- **Where.** Matched patterns for `Noto Sans Mono CJK KR` in `findings/evidence/v18/w3-w5/e2-editor-v18-P-fc-log.txt` and `…/e2-editor-v17-cjk-r5-ab-P-fc-log.txt`; scan lines 68-98 of `…/e2-editor-v18-A-fc-log.txt`.
- **Same in both arms:**
  - family, style, fullname, foundry `GOOG`, `index: 6`, weight 80, width 100;
  - `fontversion: 131334` (the Sans faces have the same value);
  - capability `otlayout:DFLT cyrl grek hang hani kana latn`, postscriptname `NotoSansMonoCJKkr-Regular`, `genericfamily: 3`.
- **Spacing.** Neither face has a spacing element, i.e. fontconfig classifies both as proportional. So the "dual vs mono" worry does not arise; Liberation Mono is `spacing: 100`.
- **Scan order.** The CJK file is the last file scanned in both arms. The directory holds only `Liberation*`, the CJK file and `opens___.ttf`, so tie-break order is unchanged.
- **No fontconfig cache.** No cache line appears in the logs, so fonts are scanned at every boot. The file is in fact scanned twice per boot (lines 82 and 98).
  - The reason given for the new font path (spec `:914`, avoiding path-keyed caches) is therefore moot in the measured runtime. Harmless.
  - The double scan is relevant to the unmeasured boot-time limit.
- **Differences:**
  - charset: 25,767 code points against 44,810. The 19,043 missing ones are mostly Hangul pages and Extension A.
  - language coverage: the full face covers 108 languages, the subset 103. Lost: exactly `bin gn ig ko miq`.

### 8. SHOULD — a concrete case where v18 should not resolve like the control (inference; not registered)

- **Where.** `…/fontconfig/src/fcmatch.c:369-373` (LANG at index 12, ahead of FAMILY_WEAK at 13); the language sets in #7; Liberation Mono's coverage in `findings/evidence/v17/layout-corpus/fc-request/e2-editor-v17-A-fc-log.txt` (it covers `bin gn ig miq en`).
- **Reasoning [inference].** Take a `monospace` (K1-shaped) or fixed-pitch request whose language is gn, ig, bin or miq.
  - On the control, full Mono KR and Liberation Mono both cover the language. LANG ties, and FAMILY_WEAK picks Mono KR (position 28).
  - On v18, the subset Mono KR misses the language and Liberation Mono covers it, so LANG picks **Liberation Mono**.
  - For `ko`, no face on v18 covers the language. The family answer is the same as the control's, but Hangul goes to glyph fallback and finds nothing (tier E).
  - CHARSET ranks above everything else. Any glyph-fallback request for a code point outside tier E in a Mono run therefore resolves differently from the control. This was already true of e5's Sans half; v18 extends it to the Mono path.
- **Why it matters.** §28.4's registered limits (`:937-940`) list Q2, TC glyphs under JP/KR/SC/HK names, memory and gzip, and not this. Real impact is tiny: those languages in a monospace paragraph, and Liberation Mono draws their Latin text fine. But it falsifies the general reading of W3/W5 as "v18 resolves like the control".
- **What settles it.** Register it as a named limit. Or run fc-request's `one_session` on v18 and on the control with a fixture whose monospace paragraph is tagged `fo:language="gn"`. Prediction: Liberation Mono on v18, Noto Sans Mono CJK KR on the control.

### 9. NOTE — GENERIC_FAMILY before LANG is in the source, but it applies only to fixed-pitch requests

- **Where.**
  - `…/fontconfig/src/fcmatch.c:361-373`: `CHARSET, FAMILY_STRONG, GENERIC_FAMILY, POSTSCRIPT_NAME_STRONG, LANG, FAMILY_WEAK, …, SPACING, …, ORDER, FONTVERSION`.
  - `…/fontconfig/src/fcfreetype.c:2084-2128`: a font's generic family is classified by name, from the gperf table or the substring "mono".
  - `findings/evidence/v17/mono-reach/RESULT.md`, the paragraph beginning "My expectation for the Asian slot missed".
- **Evidence [read].**
  - The ordering claim holds by source; RESULT.md's caveat ("read from the winners' vectors") is more modest than it needs to be.
  - GENERIC_FAMILY is only scored when the request carries a genericfamily value. Tabulating `Match Pattern` blocks in `findings/evidence/v17/mono-reach/e2-editor-v17-P-fc-log.txt`:
    - fixed-pitch requests (`spacing: 100`) carry `genericfamily: 3(i)(w)`;
    - the generic-`monospace` request of K1's shape carries none. `48-guessfamily.conf`, the stock rule that would add one, is not among the 21 conf.d files loaded.
  - v17's K1 winner scores 1e+99 at FAMILY_WEAK and is decided at the last two tiebreaks.
    - FONTVERSION: Liberation `137625` against Noto `131334` (read from the logs).
    - Then font-set order: the `LiberationMono-*` files sort first.
- **Why it matters.**
  - §28.2's mechanism sentence (spec `:906`) is correct for the fixed-pitch path.
  - For K1 on v17, Liberation Mono is an accident of version and file name. With other file names the answer would have been Liberation Sans. That shapes how finding 116's title should be read.
  - It does not affect v18, where K1 is decided at FAMILY_WEAK (`Best score … 28 …`, v18 A log line 6192).
- **What settles it.** Wording only: cite the enum, and say which requests carry genericfamily.

### 10. NOTE — "resolves like the control" (W3, W5) is not "renders like v8"

- **Where.** `findings/evidence/v17/mono-reach/summary-fixed.txt` ("tops e2-editor-v8 minus e2-editor-v17-cjk-r5-ab: [0, 0, 0, -2, -5, -7, -7, 0]"); spec `:938`; finding 116, 裁決 paragraph.
- **Evidence [read, plus inference].**
  - (a) The control is not v8: v8 loads `35-lang-normalize.conf` (finding 114). W5 shows v18 equal to the control (tops and bottoms; I also compared the bottoms: diff 0 on all 8 bands). So v18 differs from v8 by up to 7 px on the probe.
    - W4 compares only against the control, and none of the 16 product-path fixtures declares a fixed-pitch font. This v8→v18 change is intended (114's fix) but is measured on no counted surface.
  - (b) Glyph forms: in Mono runs, the control and v8 draw Han ideographs and punctuation from the KR face's cmap, while v18 draws TC forms. Bands cannot see this. It is registered (`:938`).
  - (c) The finding's 「也換回固定字距…中文行高」 is true relative to v17. Against v8, F1/F2 tops are equal (81, 104), F3 differs by −2 and the later lines by −5 to −7. And line height itself was not measured; only ink bands were.
- **What settles it.** Wording: say "like the control (no 35)", not "like v8". The v8 comparison, if wanted, is the never-run corpus v8-vs-v18.

### 11. NOTE — how much M2's undrawn Q2 carries

- **Where.** Spec `:917-921` (the decision's reasons) and `:931` (W5); `findings/evidence/v17/mono-reach/PREDICTION.md`, Amendment 1.
- **Assessment.**
  - The corpus red alone justifies A at +0.14 MB zstd, so Q2 is not load-bearing for the choice.
  - Where Q2's instrument does carry weight is W5. W5 turns M2's probe into a gate, with an instrument-alive condition (PC-M2a′ without the Courier New clause) written after two runs had missed their own written controls.
    - Under CLAUDE.md §9 this passes: it is a new criterion for v18, written before any v18 data, and forced by a named measurement (Courier New never reaches fontconfig).
    - PC-M2b, the positive control that sees 116, held in all runs.
  - But the probe holds two hand-picked names declared fixed (§1, form 3). W5 PASS should be cited as "on this probe", not as "the fixed-pitch path is fixed".
  - The finding's 裁決 paragraph does not say Q2 is undrawn; its M2 section does.

### 12. NOTE — form of the criteria (CLAUDE.md)

- **Form labels.** W3 and W5 are labelled 一 (`:929`, `:931`). They are fixed single-instance measurements: K1 in one fixture, and two names in a hand-built probe. W4 is per document over a tool-enumerated corpus, which is genuinely form 1. W1 and W2 are tool-closed, except as noted in #5.
- **Never-done default.** One section-wide default (`:935`): v18 unverified means no cutover. Adequate.
- **Corpus reader copy** (`diff` against v17's: only `PROFILES`, `DRY_RUN`, the docstring and the W4 RED clause changed):
  - v17's red cases A–F remain meaningful on unchanged inputs. Case A passes only because v16's not-measured set equals v17's (23 each).
  - The W4 clause compares this run's union of both arms with v17's **arm 0 only** (`judge.py:97-105`). That equals v17's union because v17's two arms had identical sets (its verdict had no not-measured RED), so it is correct here, but asymmetric.
  - v17's counted run is the right reference for instrument stability.
  - The new red cases (`selftest-v18.sh`) are real: v17's own files give RED on `paragraph-content` alone, and an extra not-measured document gives RED by W4.

### 13. NOTE — stale or hard-coded references

- `wasm_sdk_probe/tools/check_m3_assets.py:1015-1021`: the Z2-2 and Z2 D′ red cases hard-code `cjk-r5.b76b0433203017ca.data`. On a v18 host they would raise StopIteration/KeyError [inference]. This is planned for host 0.2.8 (spec `:941`).
  - `handoff/HANDOFF-2026-10-08-v17-v5-and-v6-done-corpus-red-on-one-fixture.md:53` still says to change it to `cjk-sub-e5`. The next handoff must say e10.
- `wasm_sdk_probe/tests/test_probe_fc_debug.py:35` asserts `NotoSansCJK-Regular-subset-E.ttc`. It is a parser fixture; harmless.
- None of the following names the pack, so all pick e10 up from the manifest [read]:
  - the page;
  - the worker, which only checks the path prefix (`sdk-worker.js:597-603`);
  - packaging (`package_m3_engine.py`, which takes the closure from the page's `workerUrl`).
- `tools/r8_release.py:146`'s `packs["cjk-r5"]` is the r6 reader release, not M3.
- `wasm_sdk_probe/Makefile:1420-1422`: the tool reads `sdk/v17-writer-review-manifest.json`, but the rule does not list it as a prerequisite. make would not see v18 as stale; `--check` would still fail when it runs.
- Finding 116, 未做 (line 56): 「加一個 Mono 子集面要多少位元組（未量）」. M1 measured it (+144,340 zstd).

### 14. NOTE — sizes against what actually ships [read]

| Pack | Raw (bytes) | gzip (bytes) | zstd (bytes) | Source |
|---|---|---|---|---|
| v8's `cjk-r5`, as host 0.2.7 ships it | 19,484,784 | 15,503,708 | 12,170,785 | `~/Projects/Nextcloud_Apps/litecore/engine/MANIFEST.json` |
| `cjk-sub-e10` | 14,384,632 | ≈12.45 MB | 5,748,639 | gzip is M1's E5+M5 figure; not measured on e10 itself |

The registered limits (`:939-940`, memory +7.2 MB and gzip +6.2 MB) are relative to v17, which never shipped. Against the shipped product, v18's CJK pack is smaller in all three measures. The 45 MB per-file cap is far away. Boot time is still unmeasured. The fontconfig scan of the 10-face e10 file is presumably cheaper than of the full TTC's 10 faces [inference].

### 15. NOTE — the product-path reader's red case is committed in filtered form

- **Where.** `findings/evidence/v18/product-path/selftest-output.txt`.
- **Evidence.**
  - In the second block, "P2 notes:" is followed by nothing, and the block ends at the P3 header [read].
  - I re-ran `python3 -I findings/evidence/v17/product-path/judge.py --dir findings/evidence/v17/product-path --candidate-page cfc8ba1d…` read-only. Result: P2 MISS with notes `('chrome','v17',1..3): v17 fields differ from PREDICTION`, P3 84 cells and 0 red, `SUMMARY … P2: MISS`, exit 0.
  - So the red case is genuine; only the committed view drops its payload (§7).
- **What settles it.** Commit the unfiltered output.

### 16. NOTE — arm order in the chain

`chain.sh:36-41` runs v8 before v18 in every round, in both browsers. Any order effect, such as warm OS caches or a long-running Chrome profile, falls on the same arm every time. Low risk, but this is a fixed order, not interleaving. Mention it in the report.

### 17. NOTE — W3 and W5 ran on an instrumented path

The sessions served loader `6234897c…`, not the shipped `46b2f40a…` (`w3-w5/sessions.json`); the only edit is `ENV.FC_DEBUG` (`v17/layout-corpus/fc-request/run.py:58-59`). The product path is covered by W6, so this is fine. Just do not cite W3/W5 as product-path evidence.
