# Markdown paste natively, round 2: unmeasured positions, a paste with no undo action, the md4c pre-scan premise (link batch v21)

Spec: `specs/SPEC-M3-link-batch-v21.md` §4.2, §9.3, §9.4, §9.12 (first bullet, opus S14). Round 1: `../README.md` (same install, same paste call). Run 2026-10-16, native LibreOffice 26.8 only. No browser, no WASM, no `make`, nothing committed. Round 1's files are unchanged (its `SHA256SUMS` still verifies, see "Files").

Labels as in round 1: **[OBS]** observed in this run (native); **[SRC]** read in source, file:line in `libreoffice-26-8` (HEAD `671c848b`, the install's buildid); **[INF]** inference. **Nothing about WASM is observed here.**

## Bottom line

- **T1 (spec §9.12, opus S14; the positions behind L-md-unmeasured-positions)** [OBS, 20 arms x 3, every arm 3/3 identical]: in a table cell, on an empty cell and in a page header the paste behaves as round 1's P4/P1 did, inside that region: `paste()` true, **one** `Paste clipboard` undo action, **one Undo restores**, 60/60. A GFM table pasted into a cell becomes a **nested table**; into a header, a table in the header. **Exception, a range over two cells (P11):** the selection is not replaced; the paste lands in **every selected cell**, appended after its text. The first cell gets the converted Markdown; the second gets the **Markdown source** as one paragraph with line breaks as U+00A0 (`B1 text# Heading one  ## Heading two…`, M2 converted without bold), and for CJK (M8) **mojibake** (`B1 text# jL�…`). One Undo still restores it all.
- **T2 (spec §9.4: a paste that adds no undo action)** [OBS, 3/3 each]: **found, seven ways.** Caret in a protected section, a range across a protected section, caret in a protected table cell, in a protected section in the header, in a drop-down content control, in a protected text frame, and any position in a document opened read-only (file mode 0444): `paste()` returns **true** in 0.1-0.3 ms, the document is unchanged (both detectors), `.uno:UndoCount` stays 0 and the **`.uno:Undo` payload is byte-identical**. That is the red case the engine's postcondition must catch (proposed M9: the protected section, reachable with plain keys). Positive control: a normal paste changes the payload (3/3). Not refused: the LOK read-only view (`setViewReadOnly`) refuses typing (control 3/3) but **not `paste()`**; plain-text and rich-text content controls; an input field.
- **"Payload changed, document unchanged" besides empty input** [OBS]: yes: whitespace-only ASCII input (spaces, tabs, newlines only, mixed), an HTML comment only, and a lone `<link rel=stylesheet>`. Each adds a `Paste clipboard` action and `.uno:ModifiedStatus=true` and changes nothing visible. All of them have no text by md4c, so §9.3's no-text rule refuses them before dispatch.
- **Input field: data loss** [OBS, 3/3]: a Markdown paste with the caret inside a `text:text-input` field garbles the paragraph (the field is duplicated into a new paragraph, `Plain ` and the `S` of the next paragraph vanish) and **one Undo does not restore** the document (the stack is then empty). Control: the same bytes as `text/plain` (today's Ctrl+V flavour) go into the field correctly, but **Undo does not restore that either** (`Field value` becomes `FieldPlain `). So the garbling is Markdown's; the incomplete Undo is not.
- **T3 (spec §9.3's pre-scan premise)** [OBS + SRC]: md4c (0.5.3, byte-identical to the tarball in all three core trees, checked) classifies every Markdown image as the spec expects: inline, `https://hostname`, reference-style, two images, data+remote → remote; code-block, inline-code, escaped and autolink look-alikes → no image; and Writer agrees natively for every Markdown-syntax image (a request to the local listener for each one md4c called remote, none otherwise), except `DATA:` (below). **But the premise "what Writer fetches = `MD_SPAN_IMG`" is false:** Writer hands raw HTML blocks to its **HTML import** (`swmd.cxx:591-603`), which fetches `<img src>` (and a `<link rel=stylesheet>`). `Intro text.` + an HTML-block `<img src="http://…">` (H7), and an inline `<img>` followed by any HTML block (H4), **pass** the §9.3 rule (text, no `MD_SPAN_IMG`) and natively send `OPTIONS` + `GET` to the URL and insert a linked image (3/3). md4c reports these as `MD_BLOCK_HTML` / `MD_TEXT_HTML`, so the scan can see them. The no-text rule also **refuses** inputs Writer would paste: an image with empty alt (`![](data:…)`, embedded natively) and a lone `---` (a rule natively); a case-sensitive `data:` test calls `DATA:` remote (embedded natively, no fetch).

## What was run

| item | value |
| --- | --- |
| install | `native-lok-26-8/build/instdir/program`, buildid `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb` (round 1's; hashes in `../README.md`). |
| probe | `tool/md_paste_probe2.cpp`, one file, from round 1's probe. Built in `tool/`: `g++ -std=c++17 -O2 -Wall -I <repo>/libreoffice-26-8/include md_paste_probe2.cpp -ldl -lpthread -o <scratch>/native-md2/md-paste-probe2`. Counted runs: binary sha256 `425a8b0113366c3466bc816f8b256bd8d19611922ba1f4d98d78e780ab89c5f8`; rebuilding exactly so reproduces it (the source path given to g++ is embedded, so building from another directory gives other bytes). g++ 15.2.0. |
| md4c harness | `tool/md4c_scan.c` + the core's own `md4c.c`: `gcc -std=c99 -O2 -Wall -I wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c/src tool/md4c_scan.c wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c/src/md4c.c -o <scratch>/native-md2/md4c-scan`; binary sha256 `49495bc0e2d12dad944283caa42deb2c0316d2a0a4c84a2dcc010630d9e65cff`. Flags exactly `MD_DIALECT_GITHUB \| MD_FLAG_WIKILINKS` (`sw/source/filter/md/swmd.cxx:951`). |
| runner | `tool/run_arms2.py`: one process at a time; `env -i HOME PATH LANG=zh_TW.UTF-8 SAL_USE_VCLPLUGIN=svp`, `nice -n 10 timeout 120`, a fresh empty profile and a fresh copy of the document per process; the probe's 20 s watchdog around load, every placement script, save, the paste and every undo (it never fired). The exact command of every process is in `out/<arm>/run<k>/cmd.txt`. |
| waiting for other probes | Before each process the runner waits until two scans 0.5 s apart find no LOK probe (finding 142's `f142*`/`native-142*`, `md-paste-probe*`, a `soffice`/`oosplash` started from this repo, or any non-shell process with an `.../instdir/program` argument). Total waited in the counted runs: **1,677 s**, of which 1,577 s for finding 142's D1 chain (`f142-d1-marker`, which runs back to back; its runner waits for ours too). Every wait is in `out/runner.log` and in each `summary.json` (`waitedForOtherLokSeconds`). The owner's desktop LibreOffice (`/opt/libreoffice26.8 … soffice.bin --writer ~/Downloads/…`) was open from 15:45:53 through all counted runs; it is not a probe and is not waited for (see "Fixed because of execution" 2), but it is recorded per run (`nonRepoOfficeProcessesAtStart`, 201/201) with the 1-minute load average (1.12-2.46). Overlap with finding 142's processes: `out/overlap-with-142.txt` (2 counted pairs touch only within its whole-second log resolution, each after the other runner had waited for ours; the dry run had 5 real overlaps, placement only). |
| N | 3 processes per arm (T1, T2, T3). |

**Placement.** Each position is two step scripts (`tool/run_arms2.py`, `POS`): SETUP runs once after load (it can record a caret rectangle as a point), PLACE runs before the read-back and again before the paste, from an absolute anchor: Ctrl+Home pressed until the document start (inside one table that is 3 presses, finding 142 item 3; a Mod1 key waits for 400 ms of callback quiet because Ctrl+Home is not FIFO with keys Writer handles itself, finding 142 item 12) or an engine click (`postMouseEvent` DOWN+UP, count 1, button 1) at a recorded point. The read-back is what Shift+End selects from the caret (then PLACE runs again) or the selection itself for ranges. Expected read-backs were written before the counted runs; six were learned from the dry run (`out/dry-run/`, one process per position) and are marked `(dry run)` in `POS`.

**What each process records** (`out/<arm>/run<k>/stdout.jsonl`, derived into `summary.json`): the read-back, caret rectangle and selection at the paste; before and after the paste the raw `getCommandValues(".uno:UndoCount")`, `(".uno:Undo")` and `(".uno:ReadOnly")` strings and the last `.uno:Paste` / `.uno:Undo` state callbacks; `paste()`'s return and wall time; every callback for 1.5 s after the call; the document saved as flat ODT before and after; `.uno:Undo` until the undo depth is back, each step saved. **"Document changed"** is judged twice, independently: by the structure reader (`tool/md_structure.py` signature) and by a reader-free fingerprint (every text node under `office:body` and `office:master-styles` plus counts of 12 structural tags, `run_arms2.py fingerprint`). **"Undo payload changed"** is a byte comparison of the two `.uno:Undo` strings. An undo step that did not restore the document is kept as `undo-<k>.fodt.gz`.

**Inputs.** Round 1's `../tool/inputs/{empty-template.odt,positions.fodt}`; round 2's `tool/inputs/` from `tool/make_fixtures.py` (hashes in `SHA256SUMS`): `cells.fodt` (text / 3x3 table, B2 empty / text), `header-footer.fodt` (byte-identical to finding 142's fixture, sha256 `32d90335…b225`), `protected-section.fodt`, `protected-cell.fodt` (`table:protected="true"`), `content-control.fodt` (drop-down, plain-text and rich-text content controls), `input-field.fodt` (`text:text-input`), `frame-protected.fodt` (page-anchored text frame, `style:protect="content"`), `header-protected-section.fodt`. Two more fixtures (`protect-form.fodt`, `protect-fields.fodt`) were dropped: see "Fixed because of execution".

**Corpus.** Round 1's `M1 M2 M4 M5 M8 M13` (`../tool/corpus/`) and round 2's `tool/corpus/` from `tool/make_corpus2.py` (28 items, below). Every URL is `127.0.0.1:18765` (the runner's logging HTTP listener: 404 for GET/HEAD, 501 for OPTIONS/PROPFIND, as round 1's listener answered) or `localhost:18768` (a logging socket that reads 64 bytes and closes). No external host was contacted.

## Results

Generated tables: `out/RESULTS.md` (every arm, every column from `out/*/run*/summary.json` and `out/T3-md4c/scan.jsonl`, by `tool/aggregate2.py`; structures of run 1 of every arm) and `out/results.json`.

### Reader extension and its checks (before any judgement used it)

`tool/md_structure.py` is round 1's reader plus, **only when present**: page headers/footers (`headerFooter`, one region per `style:header*`/`style:footer*`), nested tables (`parentCell`; table indices reserved before the cells are walked, round 1 gave an outer and an inner table the same index), and text frames (`textBox`, and page-anchored frames, which round 1 skipped).

- `out/reader-compat.txt` (`tool/check_reader_compat.py`): on a scratch copy of round 1's `out/`, the extended reader recomputes `after`, `afterSignatureSha256`, `afterHuman`, `before`, `afterSameAsBefore` of all 150 runs that kept an `after.fodt.gz` (2 M14b runs keep none) with **0 mismatches**, and round 1's unchanged `aggregate.py` then writes `RESULTS.md` and `results.json` **byte-identical** to round 1's (sha256 `7f66965f…a7b`, `44d3e354…313`). PASS.
- `out/reader-red2.txt` (`tool/check_reader_red2.py`, exit 0): header text changed → DIFFERENT; header removed → DIFFERENT; table nested in A1 vs the same table after the outer one → DIFFERENT; the nested summary vs the same with `parentCell` deleted → DIFFERENT; text-box text changed → DIFFERENT; re-serialised → SAME (positive control); and the compatibility check itself goes **red** (exit 1) with a reader whose `human()` pads one column less (150 field mismatches, `RESULTS.md` DIFFERENT) and with one whose signature drops the heading level (46 mismatches), and green with the reader unchanged.

### T1: positions round 1 did not measure [OBS]

Corpus M1 (three headings), M2 (one inline paragraph), M4 (nested bullets + numbered), M5 (GFM table 3x2 with a heading row), M8 (CJK heading, bold, list), all `text/markdown;charset=utf-8`, zh_TW.UTF-8.

| position | fixture, how reached | read-back (3/3 as expected) | what happens (3/3 every arm) |
| --- | --- | --- | --- |
| P8 inside a cell with text | `cells.fodt`, Ctrl+Home x3, Down, Right x2: `A1\| text` | `' text'` | As round 1's P4, inside cell A1: the **first block joins `A1`** and loses its block format (`A1Heading one` is body text; `A1apple` is not a list item; `A1標題` is not a heading), later blocks are new paragraphs **in the same cell** (headings stay `Heading_20_n`, lists stay lists), ` text` stays its own paragraph in the cell. **M5 → a 3x2 table nested in A1** (`A1`, the table, an empty paragraph, ` text`). The outer table stays 3x3. |
| P9 empty cell | Ctrl+Home x3, Down x2, End, Right: B2 (caret x = column B, 4630 twips) | `''` | As round 1's P1, inside B2: headings stay headings, lists stay lists, M2 is one paragraph; a trailing empty paragraph in the cell (`Text_20_body` after M1/M8, `Standard` after M2/M4). **M5 → a table nested in B2** with an empty paragraph before and two after. |
| P10 page header | `header-footer.fodt` (finding 142's), setup Down, Right x5, record; `.uno:JumpToHeader`, Right x6, record; place = **click** on the body point, **click** on the header point (finding 142's `place-hdr-click`): `Header\| line text` | `' line text'` | As P4, inside the header region; the body is unchanged: `HeaderHeading one` (style `Header`), `Heading two`/`three` keep `Heading_20_2/3`, ` line text` its own `Header` paragraph. M4's list items take the `Header` style; M8's take `Text_20_body`. **M5 → a 3x2 table in the header.** |
| P11 range over two cells | Ctrl+Home x3, Down, Right x2, **Shift+Right x6** (from `A1\| text` across the cell boundary) | `'A1 text\tB1 text\n'` (a two-cell table selection; `getSelectionType` = 1, `LOK_SELTYPE_TEXT`) | **Not replaced.** Each selected cell gets the paste **appended after its own text**: A1 the converted Markdown (`A1 textHeading one`, h2, h3 …; M5 → a nested table in A1), **B1 the Markdown source** in one paragraph with U+00A0 for line breaks (`B1 text# Heading one  ## Heading two  ### Heading three `; `B1 text- apple - banana   - nested one …`; `B1 text\| Name \| Value \| \| --- \| --- \| …`), M2 in B1 with italic and monospace but **no bold**, and M8 in B1 as **mojibake** (`B1 text# jL�  �\|Ԛ-N�e …`). The B1 text is decoded differently from A1's; the path was not traced [INF]. |

Every T1 arm: `paste()` true, 1.4-5.3 ms, `.uno:UndoCount` 0 → 1 with one `Paste clipboard` action, and **one `.uno:Undo` gives a document equal to `before`** by the reader signature **and** by the fingerprint (60/60, P11 included). No watchdog fired, every process exited 0.

### T2: does any paste add no undo action? [OBS]

Every arm 3 processes, all 3 identical (reader signatures agree 3/3). "payload" = the raw `getCommandValues(".uno:Undo")` string before vs after the call. M2 unless named.

| arm | where the caret is (read-back) | `.uno:Paste` state before | `paste()` | ms | document changed (reader / fingerprint) | `.uno:UndoCount` | **undo payload changed** | one Undo restores |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **T2-ctl-normal-M2** (positive control) | round 1's P4, `Alpha \|Beta Gamma` | enabled | true | 1.8-2.1 | yes / yes | 0 → 1 | **yes** | yes |
| T2-ref-empty-M13 (round 1's empty input) | P4 | enabled | true | 1.7-1.8 | no / no | 0 → 1 | yes | (nothing to restore) |
| **T2-sec-M2** protected section | `Inside\| locked section` | **disabled** | true | 0.1 | no / no | 0 → 0 | **no** | - |
| **T2-secrange-M2** range across a protected section | `Start \|paragraph` … `After\| section` | **disabled** | true | 0.1 | no / no | 0 → 0 | **no** | - |
| **T2-cell-M2** protected cell (`table:protected`) | `Locked\| cell` | **disabled** | true | 0.1 | no / no | 0 → 0 | **no** | - |
| **T2-hdrsec-M2** protected section in the header (click, as P10) | `Header\| line text` | **disabled** | true | 0.1 | no / no | 0 → 0 | **no** | - |
| **T2-ccdrop-M2** drop-down content control | `R\|ed` | **disabled** | true | 0.1-0.2 | no / no | 0 → 0 | **no** | - |
| **T2-frame-M2** text frame, `style:protect="content"` (click at 2385,4970 twips, Home, Right x7) | `Inside \|frame text` | enabled | true | 0.3 | no / no | 0 → 0 | **no** | - |
| **T2-filero-M2** document file mode 0444 | document start (keys do not move the caret in a read-only document) | **disabled** | true | 0.1 | no / no | 0 → 0 | **no** | - |
| T2-viewro-M2 LOK read-only view (`setViewReadOnly(view, true)` after placing) | `Alpha \|Beta Gamma` | enabled | true | 1.8-2.0 | yes / yes | 0 → 1 | yes | yes |
| T2-ctl-typekey (control: one typed `x`, normal view) | same | enabled | (no call) | - | yes / yes | 0 → 1 | yes | yes |
| T2-viewro-typekey (control: one typed `x`, read-only view) | same | enabled | (no call) | - | **no** / no | 0 → 0 | no | - |
| T2-ccplain-M2 plain-text content control | `pl\|ain words` | enabled | true | 1.7-1.8 | yes / yes | 0 → 1 | yes | yes |
| T2-ccrich-M2, -M1 rich-text content control | `ri\|ch words` | enabled | true | 1.5-2.1 | yes / yes | 0 → 1 | yes | yes |
| T2-input-M2, -M1 input field (`text:text-input`) | inside the field after `Field` (caret x 2610; Shift+End selects `Field value end`) | enabled | true | 1.6-2.3 | yes / yes | 0 → 1 | yes | **no** |
| T2-input-plain-M2 (control: the same bytes as `text/plain;charset=utf-8`) | same | enabled | true | 1.1-1.3 | yes / yes | 0 → 1 | yes | **no** |

Reading the table:

- **The red case for spec §9.4 exists natively.** Seven positions give `paste()` = true with **no** undo action and a byte-identical `.uno:Undo` payload, so "派送前後讀 `.uno:Undo`，整份內容不同且至少一個動作" reports them as not confirmed, which is the intended `MUTATION_OUTCOME_UNKNOWN` path. The detector is not blind: the positive control and every pasting arm report the payload as changed (T2-ctl-normal 3/3). For a WASM M9 the protected section is the simplest: it is document content (no special API), reached with Down from the first paragraph, and `Writer/Cursor/Option/ProtectedArea` defaults to true (`officecfg/registry/schema/org/openoffice/Office/Writer.xcs:2176-2183`) [SRC] — whether the WASM engine's profile keeps that default is [INF].
- Why `paste()` says true [SRC]: `doc_paste` returns false only if `doc_setClipboard` fails or `comphelper::dispatchCommand` finds no dispatch object (`desktop/source/lib/init.cxx:6178-6192`), and `dispatchCommand` returns true as soon as it has one (`comphelper/source/misc/dispatchcommand.cxx:48-65`). `SID_PASTE` carries `DisableFlags="SfxDisableFlags::SwOnProtectedCursor"` (`sw/sdi/_basesh.sdi:90-95`) and `ReadOnlyDoc = FALSE` (`sfx2/sdi/sfx.sdi:3206-3211`); the view sets that flag when `HasReadonlySel()` (`sw/source/uibase/uiview/view.cxx:714-722`), and `SfxDispatcher::FindServer_` then refuses the slot (`sfx2/source/control/dispatch.cxx:1641-1643`; read-only document `:1649-1652`). Drop-down/checkbox/picture content controls are read-only by type (`sw/source/core/crsr/pam.cxx:960-985`). The protected frame refused although the last `.uno:Paste` state said enabled; where it is refused was not traced.
- **LOK read-only view** [OBS + SRC/INF]: the view refuses typing (control 3/3) but not `paste()`. `SwEditWin` checks `IsLokReadOnlyView()` for keys (`sw/source/uibase/docvw/edtwin.cxx:1440`, `:5775-5780`), while `FindServer_` tests the document's own read-only flag (`dispatch.cxx:1603`, `:1649-1652`) and `doc_paste` has no view check [SRC]; that this is the whole reason is [INF]. Not relevant to our engine unless it ever uses read-only views.
- **Input field** [OBS, 3/3 both mimes]: the Markdown paste writes `Name: [Field value]bold and italic and inline code end.` / `[Field value]econd paragraph` / `Second paragraph` (the field duplicated into a new paragraph; `Plain `, ` end` and an `S` lost). After the one Undo: `Name: [Fiel][Field value]Second paragraph` / `Second paragraph` with the undo stack empty (`out/T2-input-M2/run*/undo-1.fodt.gz`). Plain text pastes correctly into the field (`[FieldPlain **bold** … end. value] end`), and its one Undo leaves `[FieldPlain ] end` (`out/T2-input-plain-M2/run*/undo-1.fodt.gz`). So today's Ctrl+V into an input field already loses text on Undo natively [OBS]; whether WASM does the same is not known.
- Not measured: `ProtectForm` and `ProtectFields` (the fixtures' `office:settings` did not take effect, see "Fixed because of execution" 3; `ProtectForm` is also in Writer's not-loaded-unless-user-settings list, `sw/source/filter/xml/xmlimp.cxx:1258-1288`). No header-level protection exists to test (no such attribute in `sw/source`; the header case above is a protected section in the header).

**"Payload changed but document unchanged", other than empty input** [OBS, T3 arms at P1, 3/3]: `W1` spaces, `W2` tabs, `W5` newlines only, `W6` mixed ASCII whitespace, `H1` an HTML comment only, `H6` a lone `<link rel="stylesheet" href=…>`: each adds one `Paste clipboard` action and sends `.uno:ModifiedStatus=true`, and the document is unchanged by both detectors. All six have no text by md4c (§9.3's rule refuses them before dispatch). H6 also fetches the URL (below).

### T3: the md4c pre-scan premise [OBS unless marked]

**Version.** `out/T3-md4c/md4c-version.txt` (`tool/md4c_version_check.py`, PASS): `download.lst` names `md4c-release-0.5.3.tar.gz` sha256 `353c346f…9b9e`; the tarball in `external/tarballs` has that sha256; `external/md4c` applies no patch; the tarball extracted is **file-for-file identical** to `workdir/UnpackedTarball/md4c` of `wasm-lite/build-headless-probe`, `wasm-lite/build-a11y-gate0` and `native-lok-26-8/build` (`md4c.c` sha256 `f1290781…c1f8`, `md4c.h` `4efd19bf…9f18`, `CMakeLists.txt` `VERSION "0.5.3"`); each tree's `libmd4c.a` objectlist is that tree's `GenCObject/UnpackedTarball/md4c/src/{entity,md4c,md4c-html}.o`; both WASM trees' `soffice.js.linkdeps` list their `libmd4c.a`; the native `libswlo.so` has `t md_parse`. Red demo for the tree comparison: one byte of `md4c.c` changed → reported (`out/T3-md4c/version-check-red.txt`). Note [SRC]: v20's product link takes `LINKDEPS` from `LOBUILD ?= ../wasm-lite/build-headless-probe` (`wasm_sdk_probe/Makefile:2`, `:20`, `:1573-1576`), the a11y rules from `E2_V5_CORE = ../wasm-lite/build-a11y-gate0` (`:127`, `:1610-1655`); both carry the same md4c, so either header is the linked one.

**Controls** (`out/T3-md4c/controls.txt`, `tool/run_t3_scan.py`, PASS): S01, M11, M11b must be remote → remote; S08, M10, S06 must not → not; S08 and M10 have exactly one `data:` image; M13 and W1 have no text; M1 has text.

`out/T3-md4c/scan.jsonl` has the full scan. "Rule" = §9.3 as written: any non-`data:` `MD_SPAN_IMG` (case-sensitive prefix) → `MARKDOWN_REMOTE_IMAGE`; else no `MD_TEXT_NORMAL/CODE/ENTITY/NULLCHAR` with a non-ASCII-blank byte **outside** image spans (alt text is not inserted as text, `mdcallbcks.cxx:278-286`) → `NO_TEXT`; else pass. Native = round 2's arms at round 1's P1 (3 runs each) or round 1's `out/P1-*`; "requests" = requests to the local listener/closer per run.

| item | input | md4c: images non-data / data; text; HTML blocks / HTML text | rule | native (3/3) | agrees? |
| --- | --- | --- | --- | --- | --- |
| S01 | `![remote](http://127.0.0.1:18765/s01.png)` in a sentence | 1 / 0; text; 0 / 0 | REMOTE | linked image; `OPTIONS`+`GET` | yes |
| S02 | `![remote](https://localhost:18768/s02.png)` | 1 / 0; text | REMOTE | linked image; 1 connection to the closer starting `16 03 01` (a TLS ClientHello), 7.8-14.6 ms | yes |
| S03 | reference-style `![alt][r]` + `[r]: http://…/s03.png` | 1 / 0; text | REMOTE | linked image; `OPTIONS`+`GET` | yes |
| S04 | two remote images | 2 / 0; text | REMOTE | 2 linked; 2x(`OPTIONS`+`GET`) | yes |
| S05 | one `data:` + one remote | 1 / 1; text | REMOTE | 1 linked + 1 embedded; `OPTIONS`+`GET` | yes |
| S12 | `[![a](http://…/s12.png)](https://example.org)` | 1 / 0; **no text outside the image** | REMOTE | linked image; `OPTIONS`+`GET` | yes |
| M11, M11b, M11c (round 1) | remote, refused / 404 / silent | 1 / 0; text | REMOTE | linked image; connect (strace, round 1) / `GET` / accept | yes |
| S06 | the image inside a fenced code block | 0 / 0; text (code) | pass | literal, `Preformatted_20_Text`, no request | yes |
| S07 | inside inline code | 0 / 0; text | pass | literal, no request | yes |
| S09 | indented code block | 0 / 0; text | pass | literal, `Preformatted_20_Text`, no request | yes |
| S10 | escaped `\![x](…)` | 0 / 0; text | pass | `!` then a hyperlink `x` to the URL (the escape turns the image into a link), no request | yes |
| S11 | autolink `<http://…/s11.png>` | 0 / 0; text | pass | a hyperlink, no request | yes |
| S13 | `![[s13.png]]` | 0 / 0; text | pass | literal `![[s13.png]]`, no request | yes |
| S08, M10 | `data:` image in a sentence | 0 / 1; text | pass | embedded image, no request | yes |
| **S14** | `![](data:…)` alone (empty alt) | 0 / 1; **no text** | **NO_TEXT** | **embedded image**, document changed | **no**: refused, Writer would paste it |
| **S15** | `![u](DATA:image/png;base64,…)` | **1** / 0 (case-sensitive; 0 by a case-insensitive test); no text outside | **REMOTE** | **embedded**, no request | **no**: refused, nothing would be fetched |
| **N1** | `---` alone | 0 / 0; no text (one `HR` block) | **NO_TEXT** | a horizontal-line paragraph, document changed | **no**: refused, Writer would paste it |
| W1 W2 W5 W6 | spaces / tabs / newlines / mixed ASCII whitespace | 0 / 0; no text; **no block at all** | NO_TEXT | undo +1, **document unchanged** | yes (refusal wanted) |
| W3, W4 | `U+3000 U+3000` / `U+00A0` | 0 / 0; **text** (a `P` block; 0 by a Unicode-whitespace test) | pass | a paragraph holding those characters | yes (md4c's notion of blank = Writer's) |
| M13 (round 1) | empty | no text | NO_TEXT | undo +1, unchanged | yes |
| H1 | `<!-- just a comment -->` | 0 / 0; no text; **1 / 2** | NO_TEXT | undo +1, unchanged, no request | yes (refusal wanted) |
| **H2** | `<img src="http://…/h2.png">` alone | 0 / 0; no text; 1 / 2 | NO_TEXT | **linked image; `OPTIONS`+`GET`+`GET`** | refused, but only because it has no text |
| H3 | `Before <img src="http://…/h3.png"> after.` | 0 / 0; text; 0 / 1 | pass | `Before  after.` (the inline HTML is dropped), **no request** | yes |
| **H4** | H3 then a blank line and `<div>block</div>` | 0 / 0; text; 1 / 3 | **pass** | **linked image (the inline `<img>` is imported with the later block); `OPTIONS`+`GET`+`GET`** | **no: a remote fetch passes the rule** |
| H5 | `<img src=… width="10" height="10">` alone | 0 / 0; no text; 1 / 2 | NO_TEXT | **linked image; `OPTIONS`+`GET`** (size given, fetched anyway) | refused only for having no text |
| H6 | `<link rel="stylesheet" href="http://…/h6.css">` alone | 0 / 0; no text; 1 / 2 | NO_TEXT | **`OPTIONS`+`HEAD`+`GET`**, document unchanged, undo +1 | refused only for having no text |
| **H7** | `Intro text.` then `<img src="http://…/h7.png">` | 0 / 0; text; 1 / 2 | **pass** | **linked image; `OPTIONS`+`GET`+`GET`**, 5.6-6.2 ms | **no: a remote fetch passes the rule** |

Every other round-1 item (M1-M9, M12, M14a/b) passes the rule and was pasted in round 1 without a request.

What this means for §9.3 [OBS + SRC]:

- md4c's `MD_SPAN_IMG` is exactly Writer's Markdown image path: among the Markdown-syntax items Writer fetched for every item md4c called remote except S15, and for none it called not remote.
- **Raw HTML is a second fetch path the premise misses.** `MD_BLOCK_HTML` → `SwMarkdownParser::BeginHtmlBlock`/`EndHtmlBlock` → `InsertHtmlData` → `SwReader(...).Read(*ReadHTML)` (`sw/source/filter/md/mdcallbcks.cxx:71-72`, `:131-132`; `swmd.cxx:583-603`); `MD_TEXT_HTML` is accumulated into `m_htmlData` (`mdcallbcks.cxx:272-275`) and only written out by the next HTML block, which is why H3 drops it and H4 imports it. The HTML import fetches `<img>` through `GraphicDescriptor` when no size is given (`sw/source/filter/html/htmlgrin.cxx:685-692`); H5 (size given) and H6 (a stylesheet) were fetched too, through paths not traced. md4c reports all of these as `htmlBlocks`/`htmlText` (the scan's columns), so a pre-scan that refuses any `MD_BLOCK_HTML` or `MD_TEXT_HTML` would cover every H item [INF: the rule is the caller's choice; Writer parses with HTML enabled, `swmd.cxx:951`, not `MD_FLAG_NOHTML`].
- The no-text rule refuses three things Writer would paste (S14 image with empty alt, N1 a rule; and S15 via the case-sensitive test). All three are refusals, not fetches (the safe direction).
- Whitespace: md4c (and so the rule) treats U+3000 and U+00A0 as text, and Writer pastes them; only ASCII whitespace is "no block".

## Fixed because of execution (declared)

1. **Placement expectations from the dry run.** Six read-backs (`P11`, `SECRANGE`, `FILERO`, three content controls) were not predicted but learned from one dry-run process each (`out/dry-run/`, kept) and written into `POS` before the counted runs, marked `(dry run)`. `FILERO` was changed to the document start because keys do not move the caret in a document opened read-only.
2. **Runner busy rule.** The dry-run runner (which matched any `soffice`) waited on the owner's desktop LibreOffice, opened at 15:45:53 on a document in `~/Downloads`; it was stopped (no LOK process of ours was running; noted at the end of `out/dry-run/runner.log`). Since then a `soffice`/`oosplash` counts only when it runs from this repo, and quiet means two scans 0.5 s apart; the owner's process is recorded per run instead. Finding 142's runner matches `soffice.bin` by name, so it waited on the owner's LibreOffice as well; its chain resumed later on its own.
3. **Dropped arms.** `PFORM` (ProtectForm) and `PFIELDS` (ProtectFields): the dry run's saved `before.fodt` showed both settings `false`, so the fixtures' `office:settings` did not take effect; the arms were removed before the counted runs (reason in `run_arms2.py`). Their dry-run results are in `out/dry-run/` and are not used.
4. **Controls added after the dry run.** `T2-ctl-typekey` and `T2-viewro-typekey` (the read-only view did not stop `paste()`: did `setViewReadOnly` take effect at all? It did: typing is refused). The probe gained the `typekey` flag for them; every counted run used that final binary (`425a8b01…`; the dry run's first part used `f8531221…`, the same probe without `typekey`).
5. **Arms added after the counted runs**, each with its reason in the source: `H7` (H2 alone has no text, so the rule refuses it by accident; H7 is the clean case) and `T2-input-plain-M2` (is the input-field damage Markdown's?). `make_corpus2.py` gained H7; the other 28 corpus files are byte-identical (checked against the generator, and every run's `corpusSha256` matches the final file).
6. **Runner/listener details before the counted runs:** the HTTP listener answers `OPTIONS`/`PROPFIND` with 501 as round 1's did (it had briefly answered 404, dry run only); summaries store image facts directly (`afterImages`); an undo step that does not restore is kept as `undo-<k>.fodt.gz`.
7. **Overlap file.** The first version of `out/overlap-with-142.txt` read finding 142's log time as an end time; it is the start (`run_d1.py`: `start = utc()` before the process). Rewritten.

Fixed because of review: 0 (no review ran).

## Predictions written before the run (`out/predictions-before-run.txt`) against the results

| # | prediction | result |
| --- | --- | --- |
| 1 | P8 as P4 inside the cell | held |
| 2 | M5 in a cell → nested table | held (P8, P9; also P11's first cell) |
| 3 | P9 blocks fill the cell | held |
| 4 | P10 as P4 in the header | held |
| 5 | P11 selection not deleted, content at the cursor | **half wrong**: not deleted, but pasted into **every** selected cell, the second one as source text / mojibake |
| 6, 7 | positive control changes the payload; M13 as round 1 | held |
| 8 | protected section/cell/header section/range, drop-down CC, read-only view → nothing happens | held except the **read-only view, which pastes** |
| 9 | file 0444 → as 8 | held |
| 10 | plain/rich content controls paste | held |
| 11 | input field: M2 goes in, M1 unsure | **wrong**: both garble the text and Undo does not restore |
| 12 | ProtectForm pastes | not tested (settings did not load) |
| 13 | protected frame refused if the click gets in | held (the click gets in) |
| 14-16 | md4c classification | held, except S12 has no text outside the image and S15 is remote only case-sensitively (as predicted) |
| 17 | native remote/literal/embedded | held |
| 18 | whitespace-only → undo +1, unchanged | held |
| 19 | H2 fetched; H4 fetched; H3 dropped, no request; **H5 no request at paste**; H6 a request | held except **H5, which was fetched** |
| 20 | H1: undo action, maybe an empty paragraph | undo action, **no** change at all |

## What this does NOT show

- **Anything about WASM.** No WASM process ran. Whether the WASM engine refuses the same positions (its profile's `ProtectedArea`, its dispatcher), garbles input fields, fills multi-cell selections the same way, or fetches HTML-block URLs from inside the worker is not known.
- What the user **sees**: structure was read from saved flat ODT only; nothing was rendered (nested tables, header tables, the second cell's mojibake on screen).
- Positions not tried: footers, footnotes, frames that are not protected, a document that starts with a table, a caret at the start or end of a cell with text, a selection inside one cell, more than two cells, a selection made through the engine's text-handles path (P11 used Shift+Right), a backward range; an input field with the caret at its edge; ProtectForm/ProtectFields/ProtectBookmarks; checkbox and picture content controls (same read-only rule as the drop-down by source, not run).
- HTML: only `<img>`, `<div>`, a comment and `<link rel=stylesheet>`. Other HTML that can reference URLs (`<iframe>`, `<object>`, `<embed>`, `background=`, CSS `url()` in `<style>`, `<script src>`) was not tried; nor was HTML in a list item, a table cell or a blockquote.
- Why the protected frame and the P11 second cell behave as they do (not traced); why Undo does not restore input-field pastes (not traced; it also happens for text/plain).
- Undo after further edits, Redo, a non-empty undo stack before the paste, an undo stack at its limit (L-md-undo-collision).
- Timing beyond this host: the owner's desktop LibreOffice was open during every counted run (load 1.12-2.46); call times are for orientation only.

## Reproduce

```
R=findings/evidence/link-batch-v21/native/markdown-paste; E=$R/round-2; S=<scratch>/native-md2
M=wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c/src
(cd $E/tool && g++ -std=c++17 -O2 -Wall -I <repo>/libreoffice-26-8/include md_paste_probe2.cpp -ldl -lpthread -o $S/md-paste-probe2)
gcc -std=c99 -O2 -Wall -I $M $E/tool/md4c_scan.c $M/md4c.c -o $S/md4c-scan
python3 -I -B $E/tool/make_fixtures.py $E/tool/inputs        # byte-identical fixtures (prints sha256)
python3 -I -B $E/tool/make_corpus2.py $E/tool/corpus           # byte-identical corpus
python3 -I -B $E/tool/check_reader_compat.py $R <empty dir> $E/out/reader-compat.txt
python3 -I -B $E/tool/check_reader_red2.py $R $E/tool/inputs <empty dir> $E/out/reader-red2.txt
python3 -I -B $E/tool/run_arms2.py $S/md-paste-probe2 $S/runs $E/out [--runs=N] [ARM_ID_PREFIX ...]
python3 -I -B $E/tool/run_t3_scan.py $S/md4c-scan $E/out/T3-md4c
python3 -I -B $E/tool/md4c_version_check.py <repo> <empty dir> $E/out/T3-md4c/md4c-version.txt
python3 -I -B $E/tool/aggregate2.py $E/out $R/out $E/out/T3-md4c/scan.jsonl   # out/RESULTS.md, out/results.json
```

`run_arms2.py` skips a run whose `summary.json` exists; it starts the 18765 listener and the 18768 closer itself. Run Python with `-B` so nothing is written into round 1's `tool/__pycache__` (`make_corpus2.py` imports round 1's `make_corpus.py` for the PNG).

## Files

- `tool/`: `md_paste_probe2.cpp` (probe), `run_arms2.py` (arm matrix, placements, runner), `md_structure.py` (extended reader), `check_reader_compat.py`, `check_reader_red2.py`, `make_fixtures.py` + `inputs/`, `make_corpus2.py` + `corpus/`, `md4c_scan.c`, `run_t3_scan.py`, `md4c_version_check.py`, `aggregate2.py`.
- `out/<arm>/run<k>/`: `cmd.txt`, `stdout.jsonl`, `stderr.txt`, `before.fodt.gz`, `after.fodt.gz`, `undo-<k>.fodt.gz` (only when that undo did not restore), `summary.json`. 67 arms, 201 processes.
- `out/RESULTS.md`, `out/results.json`, `out/runner.log`, `out/predictions-before-run.txt`, `out/reader-compat.txt`, `out/reader-red2.txt`, `out/overlap-with-142.txt`, `out/T3-md4c/{scan.jsonl,controls.txt,md4c-version.txt,version-check-red.txt}`, `out/dry-run/` (23 placement processes, not counted).
- `SHA256SUMS`: every file in this folder except itself. Round 1's `../SHA256SUMS` still verifies (`sha256sum -c`, run after this round).
