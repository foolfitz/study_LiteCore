# Markdown paste through LibreOfficeKit, characterised natively (link batch v21, plan step 1b)

Brief: `handoff/PLAN-2026-10-16-link-batch-v21.md` §2.2 and §4 step 1b; facts: `handoff/link-batch-v21/facts-markdown-cfield.md` ITEM 1; background: `research/RESEARCH-2026-10-14-markdown-paste.md`. The owner chose an explicit 「貼上為 Markdown」 command; Ctrl+V stays plain text. The engine would call LOK `paste(doc, "text/markdown;charset=utf-8", bytes, len)`, the call Collabora's kit makes (`cool-26-04` `c64a7343` `kit/ChildSession.cpp:1897` — the plan and fact sheet say `:1896` — inside an `if (size > 0)` at `:1887`).

Run 2026-10-16 on native LibreOffice 26.8 only. No browser, no WASM, no `make`, no product bytes, nothing committed.

Labels: **[OBS]** observed in this run (native); **[SRC]** read in source, file:line given; **[BYTES]** a byte search of a committed or shipped artifact; **[INF]** inference, needs a measurement before anyone relies on it. **Nothing about WASM is observed here.**

## Bottom line

- [OBS] Every construct converts at the document start: headings, bold, italic, inline code, a fenced code block, bullet/numbered/nested lists, a GFM table (3x2 with a heading row), a hyperlink, a blockquote, a horizontal rule, CJK, Hebrew (CTL), a `data:` image (embedded), a remote image (kept as a linked image), a wiki link. 152 processes, every arm 3/3 identical (two strace diagnostics are 1/1 by design).
- [OBS] **One paste = one undo action ("Paste clipboard"), and one `.uno:Undo` restores the document**, in 152/152 runs, at every position, ranges included. The `.uno:Undo` command result says `"success": false` in 150/150 dispatches although the undo happened.
- [OBS] `paste()` returned `true` in 152/152 runs — **also when nothing was inserted** (empty input), where it still added an undo action and sent `.uno:ModifiedStatus=true`. The engine needs its own postcondition.
- [OBS] Positions: at the start of a paragraph (P3) the blocks go in **before** it as their own paragraphs; in the middle (P4) and on a range (P6, P7) the host paragraph is **split**, the **first** pasted block is merged into the left half **and loses its own block format** (a heading or list item becomes body text in the host's style), and the right half stays a separate paragraph. Even a one-line inline paste (M2) splits the paragraph in the middle. In a bulleted paragraph (P5) the pasted list joins the host list; a pasted heading becomes a list item.
- [OBS] Encoding: the byte flavour is decoded with the thread's locale codeset: right under `zh_TW.UTF-8` and `C.UTF-8`, **mojibake under `LANG=C`** (ISO-8859-1, encoding id 12), while `text/plain` under `LANG=C` stays right. The `charset=` parameter of `text/markdown` is ignored (`charset=utf-16` with UTF-16 bytes is garbage under both locales tried). [INF] Our WASM loader always sets `LANG=<navigator.language>.UTF-8`, and musl answers `UTF-8` for every name except exactly `C`/`POSIX`, so WASM should decode UTF-8 — not measured.
- [OBS] Hazards: a remote image URL is fetched **inside** `paste()` (an `OPTIONS` then a `GET`); a server that accepts and never answers holds `paste()` for **5.0 s** (3/3); empty input makes Writer create its error `MessageDialog`, which LOK cancels at once (no block, natively); wiki links point at `https://zxx.wikipedia.org/...`; 256 KiB takes **3.0-3.1 s** in the call plus about 40,000 accessibility `CORE_LOG` callbacks; `**粗體中文**` is saved bold for the **Western** script only, so CJK text is not bold.

## What was run

| item | value |
| --- | --- |
| install | `native-lok-26-8/build/instdir/program` (read-only). `versionrc` `buildid=671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`; source `native-lok-26-8/src` HEAD `671c848b…`, `git status` clean — the same commit as the WASM core (`coreCommit` of v20). |
| install hashes | `libsofficeapp.so` `9ad354649f183fd31982c24c4b5af9dbbfec07cc980dc789f1b57bb08ec1947c` (as in `../../../new-document/probe-1-native-defaults/README.md`); `libswlo.so` `885566e3e620e3657716e8b008ac9721a07010814a4aebe65046686dd78c71b3`; `libmergedlo.so` `2d49c9ff845d3e2cd3fb5d109ea95e9ce01bf45f2925e9a1ed2176eaedd3f924` |
| sw markdown filter in it | `native-lok-26-8/build/workdir/CxxObject/sw/source/filter/md/{mdcallbcks,mdnum,mdtab,swmd,wrtmd}.o` (2026-08-03 21:50); `nm -C libswlo.so` shows `SwMarkdownParser::CallParser()` and the literal `".wikipedia.org/wiki/"` is in `libswlo.so` once; `config_host.mk:58` `BUILD_TYPE` has `MD4C`. Both native and WASM builds have `ASSERT_ALWAYS_ABORT=FALSE` → `-DNDEBUG` (`config_host.mk:30`, `solenv/gbuild/gbuild.mk:233-236`). |
| why not `build-native-26-8` (named in the plan) | Every recent native harness (129, page-rectangles, probe-1, native-roundtrip) used `native-lok-26-8`, untouched since 2026-08-03. `build-native-26-8` was reconfigured on 2026-09-25 and its `libswlo.so` relinked on 2026-09-26, so it is a different binary from the one earlier evidence describes. Same commit either way. |
| probe | `tool/md_paste_probe.cpp` (sha256 in `SHA256SUMS`), one file, compiled with the repo's native-harness recipe (`wasm_sdk_probe/Makefile:2710`): `g++ -std=c++17 -O2 -Wall -I libreoffice-26-8/include md_paste_probe.cpp -ldl -lpthread -o <scratch>/native-md/md-paste-probe`; binary sha256 `a6cbfca06dade268cbce5d68ebbcbcc06675c3c8858483a8d80b74c7ae61474e`, kept outside the repo. g++ 15.2.0, Ubuntu 26.04, Linux 7.0.0-38, Python 3.14.4. |
| runner | `tool/run_arms.py <binary> <scratch>/runs out` — one process at a time; before each, it waits while any other process has a LOK `instdir/program` argument (another session's probe: the 142 arms ran at the same time; 25 waits, 2,766 s in total, `out/runner.log`). The 142 runner does not wait, so 24 of our 152 processes still overlapped one of its processes (`out/overlap-with-142.txt`). |
| environment per process | `env -i HOME=$HOME PATH=/usr/bin:/bin LANG=<arm> SAL_USE_VCLPLUGIN=svp nice -n 10 timeout 120 …` (`LC_ALL`, `LC_CTYPE`, `LANGUAGE` unset); a fresh empty user profile and a fresh copy of the input document per process; the exact line is in every `out/<arm>/run<k>/cmd.txt`. `locale -a`: `C C.utf8 POSIX zh_TW.utf8` and 21 `en_*` locales. |
| watchdog | inside the probe, around `lok_init_2`, `documentLoad`, every save, the paste, and every undo: if a step has not returned in 20 s (150 s for M11c) the probe prints `{"probe":"blocked",…}` with all callbacks so far and exits 124. It never fired. |

Each process: `lok_init_2` → `documentLoad` (no options, no `Batch`, as `probe_engine.cpp:2992-2993`) → `initializeForRendering("{}")` → `registerCallback` → `setAccessibilityState(view, true)` (the product does this at open) → one `paintTile` → place the caret (key events) → **ask the state**: read back what Shift+End selects (collapsed positions; then place again from scratch) or the selection (ranges) → save `before.fodt` → read `.uno:UndoCount` and `.uno:Undo` → **`paste(doc, mime, bytes, len)`**, timed → 1.5 s for callbacks (all are recorded with ms since the call and whether they arrived during it; `LOK_CALLBACK_CORE_LOG` only counted, first three kept) → undo state → one `paintTile`, timed → save `after.fodt` → `.uno:Undo` (dispatched with a result request) and save `undo-<k>.fodt`, until the undo depth is back where it was. The runner compares each `undo-<k>` with `before` by structure and keeps `before`/`after` gzipped.

**Inputs** (`tool/inputs/`, hashes in `SHA256SUMS`):

- `empty-template.odt`: richdocuments 8.7.3 `template.odt`, byte-identical to probe-1's input (sha256 `a3354bae…`). An empty `office:text`.
- `new-document-en-US_zh-TW_A4.odt`: the host's static template a zh_TW user gets (`~/Projects/Nextcloud_Apps/litecore/blank/`, `specs/SPEC-M3-new-document.md:98-100`, `:153`), sha256 `7e6221b6…`, equal to its `MANIFEST.json` entry. One empty `Standard` paragraph.
- `positions.fodt` (written for this run): `Start` (Standard) / `Alpha Beta Gamma` (Text body) / `Delta Epsilon` (Text body) / bullet list `Item one`, `Item two` / `End`.

**Corpus** (`tool/make_corpus.py` → `tool/corpus/`, UTF-8 bytes, deterministic):

| id | content |
| --- | --- |
| M1 | `# Heading one` / `## Heading two` / `### Heading three` |
| M2 | `Plain **bold** and *italic* and `` `inline code` `` end.` |
| M3 | a fenced code block of two lines, the second indented |
| M4 | bullet list with two nested items, then a numbered list of three |
| M5 | GFM table, heading row + 2 rows, 2 columns |
| M6 | `See [example](https://example.org) here.` |
| M7 | a two-line blockquote, `---`, `after rule` |
| M8 | `# 標題` / `**粗體中文**` / three items `- 第一項` … |
| M9 | `שלום`, no newline — exactly `sw/qa/filter/md/md.cxx:1047-1055` `testCTLPaste` (tdf#172084) |
| M10 | `![dot](data:image/png;base64,…)` (a 4x3 PNG) inside a sentence |
| M11 | `![remote](http://127.0.0.1:9/x.png)` — nothing listens on port 9, so it is refused at once (checked: `connect_ex` = 111) |
| M11b | the same with `127.0.0.1:18765`, a local HTTP listener in the runner that logs every request and answers 404 |
| M11c | the same with `127.0.0.1:18766`, a local socket that accepts and never answers (added after the first full run) |
| M12 | `See [[Page]] here.` |
| M13 | empty (0 bytes) |
| M14a / M14b | 16,594 / 262,262 bytes of repeated sections (heading, paragraph with bold/italic/code and CJK, nested list, numbered list, code block, 2x2 table) |
| C1 | M1 + M2 sent as `text/plain;charset=utf-8` (the red control) |

No external host was contacted: every URL in the corpus is `127.0.0.1`, and `https://example.org` / `zxx.wikipedia.org` are only written into the document as link targets.

**Positions:** P1 the empty template, document start; P2 the zh-TW new-document template, document start; on `positions.fodt`: P3 start of `Alpha Beta Gamma`; P4 after `Alpha ` (middle); P5 start of the bulleted `Item one` (the shape of upstream `testPaste`, `md.cxx:997-1045`); P6 the selection `Beta`; P7 the selection `Beta Gamma¶Delta`. The read-back matched the intended position in 152/152 runs.

## Results

Generated tables: `out/RESULTS.md` (every arm, every column from `out/*/run*/summary.json` by `tool/aggregate.py`) and `out/results.json`. Structure summaries come from `tool/md_structure.py`, which reports paragraph styles by the **programmatic** names ODF stores (`Heading_20_1`, `Text_20_body`, …), never the localized UI names (finding 031).

### Constructs at P1 (LANG=zh_TW.UTF-8, `text/markdown;charset=utf-8`) [OBS]

| arm | what the document holds after the paste | 3 runs |
| --- | --- | --- |
| M1 | `Heading_20_1/2/3` paragraphs (outline levels 1-3); a trailing empty `Text_20_body` | 3/3 |
| M2 | one `Standard` paragraph; runs bold, italic, and monospace (`inline code`) | 3/3 |
| M3 | one `Preformatted_20_Text` paragraph, monospace, the line break and the indent kept (`code line 1\n  indented line 2`) | 3/3 |
| M4 | `apple`, `banana`, `cherry` bullet depth 1; `nested one/two` bullet depth 2; `first/second/third` numbered depth 1 | 3/3 |
| M5 | a 3x2 table, one heading row (`Table_20_Heading`, bold), body cells `Table_20_Contents`; an empty paragraph before it and two after | 3/3 |
| M6 | hyperlink `https://example.org/` on `example` | 3/3 |
| M7 | `Quotations` paragraph `quoted line one`+U+00A0+`quoted line two` (the soft break becomes a no-break space, `mdcallbcks.cxx:293-296`); an empty `Horizontal_20_Line` paragraph; `after rule` | 3/3 |
| M8 | `Heading_20_1` `標題`; `粗體中文` bold **Western only** (see Hazards); three bullet items | 3/3 |
| M9 | `שלום` | 3/3 |
| M10 | the PNG **embedded** (`office:binary-data`), anchored as a character, 0.3472 in square (the 500-twip minimum, `swmd.hxx:56-57`); text `Before  after.` (the alt text is not kept as text) | 3/3 |
| M11 / M11b / M11c | a **linked** image with the `http://127.0.0.1:…/x.png` URL, 0.3472 in square | 3/3 each |
| M12 | hyperlink `https://zxx.wikipedia.org/wiki/Page` on `Page` | 3/3 |
| M13 | unchanged: one empty paragraph | 3/3 |
| M14a | 989 paragraphs, 76 tables 2x2 — the same per-section structure as above | 3/3 |
| M14b | 14,561 paragraphs, 1,120 tables 2x2 | 3/3 |
| C1 (`text/plain`) | six `Standard` paragraphs, literal: `# Heading one`, …, `Plain **bold** and *italic* and `` `inline code` `` end.` — no heading, no bold | 3/3 |

P2 (the zh-TW template) gives the same structure as P1 for M1, M2, M4 and M8 (`md_structure.py --compare`: SAME, 4/4).

### Positions (M1, M2, M4, M8) [OBS, 3/3 each]

| position | what happens |
| --- | --- |
| P1, P2 document start of an empty document | as the table above |
| P3 start of `Alpha Beta Gamma` | the pasted blocks become **new paragraphs before** the host; the host paragraph is unchanged. Body blocks take the host's style (`Text_20_body`); headings keep `Heading_20_n`. Even the one-line M2 becomes its own paragraph instead of joining the host. |
| P4 after `Alpha ` | the host is **split**. The **first** pasted block is joined to the left half and takes the host's style, **losing its own block format**: M1 → `Alpha Heading one` is body text (h2, h3 stay headings); M4 → `Alpha apple` is not a list item; M8 → `Alpha 標題` is not a heading. The other blocks follow as their own paragraphs. The right half `Beta Gamma` is **its own paragraph** (not joined to the last block). M2 (one inline paragraph) → `Alpha Plain bold … end.` and `Beta Gamma` — a one-line paste in the middle of a sentence breaks the paragraph. |
| P5 start of bulleted `Item one` | the pasted content joins the host list: M2 → a bullet item before `Item one` (`Standard`); M4 → all items in the host bullet list, the ordered items kept **numbered by a list-item style override** inside it; M1 and M8 → the **first heading becomes a list item** (a heading paragraph inside the list), later blocks are outside it, the host list goes on. |
| P6 selection `Beta` | the selection is replaced, then as P4: `Alpha <first block>` … ` Gamma` |
| P7 selection `Beta Gamma¶Delta` | the selection is replaced, then as P4: `Alpha <first block>` … ` Epsilon`; one paragraph fewer |

This matches cool#15535's intent as upstream tests it (`md.cxx:997-1045`: at the start of a paragraph, new paragraphs before it, the insertion point's paragraph style kept) [SRC]. The P4 shape (first block merged and stripped of its block format) is not covered by that test [SRC].

### Undo [OBS]

- Every run: `.uno:UndoCount` 0 → 1 (the last `.uno:Undo` state callback `disabled` — or none yet, in 12 runs — → `enabled`; `getCommandValues(".uno:Undo")` empty → one action), the new action's comment is `Paste clipboard`, and **one** `.uno:Undo` gives a document whose structure equals `before` (152/152; P6/P7 included, so the replaced selection comes back too). This is `SwTrnsfrActionAndUndo` around the whole paste (`swdtflvr.cxx:1850-1853`) [SRC].
- The `UNO_COMMAND_RESULT` of `.uno:Undo` reads `"success": false` in all 150 undo dispatches, with the stack decremented and the document restored. The result payload is not a postcondition for undo.
- Empty input (M13) also adds a `Paste clipboard` action, which undoes nothing visible.

### Timing and callbacks [OBS]

| case | `paste()` wall time |
| --- | --- |
| every other corpus item (all ≤ 145 bytes), at every position, every locale and mime | 1.1-8.1 ms |
| M11 (refused connect) / M11b (local 404) | 3.1-3.5 / 4.6-4.9 ms (M6, a link with no fetch: 1.1-1.2 ms) |
| M11c (accepts, never answers) | **5,003.2-5,003.5 ms** |
| M14a 16.6 KB | 80.6-110.8 ms |
| M14b 262 KB | **3,024-3,108 ms** |

- `paste()` is synchronous: the document is changed when it returns, and **no callback arrives during the call** (0 in 152 runs). The first callbacks (`.uno:ModifiedStatus=true`, `INVALIDATE_VISIBLE_CURSOR`) come 1.6-3 ms after the call started (that is, as it returns); `.uno:Undo=enabled` about 300 ms later; the last state callbacks about 460 ms later.
- Ranges (P6, P7) add a `TEXT_SELECTION` callback (the selection is gone).
- Accessibility is on, as in the product, and its listener sends `LOK_CALLBACK_CORE_LOG` lines (`LOK_INFO`, `include/sfx2/lokhelper.hxx:35-54`, emitted unconditionally): 2-16 per small paste, **2,684** for M14a and **40,268** for M14b, plus 391 `DOCUMENT_SIZE_CHANGED`. [INF] The WASM engine would receive the same flood through its callback path; its cost there is not measured.
- One `paintTile` after the paste: 0.4-15.5 ms. The probe process takes 4.7-10.0 s in total.
- stderr (`out/*/run*/stderr.txt`): every paste whose first block stays a heading logs `sw/source/core/docnode/ndnum.cxx:116: <SwNodes::UpdateOutlineNode(..)> - given text node isn't in the correct nodes array. This is a serious defect` once (13 run-1 arms; not when the first heading is merged at P4/P6/P7; nothing wrong is visible in the saved structure). `text/markdown` without `charset` logs `lokclipboard.cxx:220` "Horror type mismatch!" (the requested flavour is a string, the stored one bytes; the bytes are still returned).

### Encoding, observed natively [OBS]

`threadTextEncoding` is `osl_getThreadTextEncoding()` read through `dlsym` in the thread that calls `paste()` — the call is synchronous, so it is the thread that decodes.

| arm | LANG | mime | thread encoding | result |
| --- | --- | --- | --- | --- |
| P1-M8 | zh_TW.UTF-8 | `text/markdown;charset=utf-8` | 76 (UTF8) | right: `標題`, `粗體中文`, `第一項`… (3/3) |
| ENC-C.UTF-8-M8 | C.UTF-8 | same | 76 | right, identical structure (3/3) |
| ENC-C-M8 | C | same | **12 (ISO_8859_1)** | **mojibake**: `æ¨\x99é¡\x8c`… — each UTF-8 byte became one Latin-1 character; the Markdown structure (heading, bold, list) still converted (3/3) |
| ENC-C-M9 | C | same | 12 | mojibake `×©×\x9c×\x95×\x9d` (3/3) |
| ENC-C-M2 | C | same | 12 | right (ASCII only) — the locale breaks non-ASCII text, not the conversion (3/3) |
| ENC-C-M8-plain | C | `text/plain;charset=utf-8` | 12 | right, literal (3/3): LOK decodes `text/plain` as UTF-8 itself |
| MIME-nocharset-M8 | zh_TW.UTF-8 | `text/markdown` | 76 | identical to P1-M8 (same signature) (3/3) |
| MIME-utf16-M8, ENC-C-M8-utf16 | zh_TW.UTF-8 / C | `text/markdown;charset=utf-16`, UTF-16LE bytes | 76 / 12 | garbage, one paragraph, no structure (3/3 each): the `charset` parameter is ignored |

Native `LANG=C` is ISO-8859-1 because glibc names the C codeset `ANSI_X3.4-1968` and `sal/osl/unx/nlsupport.cxx:293` maps that to `RTL_TEXTENCODING_ISO_8859_1` ("fake: ASCII_US") [SRC].

## The byte flavour's codeset in our WASM build (INFERENCE, source reading only)

Nothing in this section was run. Every step is a file:line in `libreoffice-26-8` (671c848b, the WASM core's source), in the emsdk the WASM core was built with (`wasm-lite/build-headless-probe/config_host.mk:152` → `wasm-lite/tools/emsdk`, Emscripten `4.0.10`), or a byte search of the shipped v20 loader.

1. **The decode.** `LOKTransferable` keeps a non-`text/plain` flavour as raw bytes (`desktop/source/lib/lokclipboard.cxx:176-190`, `:192-210`). Writer reads it with `TransferableDataHelper::GetString`, which turns a byte sequence into a string with `osl_getThreadTextEncoding()` (`vcl/source/treelist/transfer.cxx:1491-1523`, the call at `:1517`). The `charset=` parameter of `text/markdown` is never read: `SotExchange::GetFormat` maps `text/markdown` plus any `;params` to `MARKDOWN` (`sot/source/base/exchange.cxx:200`, `:235-263` with `allowMoreParams` at `:249`, `:382-385`), and the only charset handling in `FillDataFlavorExVector` is for `text/plain` (`transfer.cxx:1270-1281`). So `text/markdown;charset=utf-16` is decoded exactly like `charset=utf-8`. By contrast every `text/plain*` flavour is turned into a string from UTF-8 by LOK itself (`lokclipboard.cxx:179-183`, `:203-204`), whatever charset it names.
2. **The thread encoding.** `osl_getThreadTextEncoding()` is a `thread_local` initialised once per thread (`sal/osl/all/threadshared.cxx:30-38`) from `osl_getTextEncodingFromLocale(nullptr)`, with `RTL_TEXTENCODING_DONTKNOW` replaced by `ASCII_US` (`sal/osl/unx/thread.cxx:1032-1044`). The only `osl_setThreadTextEncoding` caller in core is the X11 input method (`vcl/unx/generic/app/i18n_im.cxx:199`), not built for WASM.
3. **The locale name.** `osl_getTextEncodingFromLocale(nullptr)` takes the process locale (`sal/osl/unx/nlsupport.cxx:572-573`), which is read from `LC_ALL`, then `LC_CTYPE`, then `LANG`, else `"C"` (`nlsupport.cxx:626-639`, `imp_getProcessLocale`); nothing in core calls `osl_setProcessLocale` (grep) or `setlocale` (only `i18n_im.cxx`). The name is parsed and re-composed (`nlsupport.cxx:177-226`, `:105-174`): `zh_TW.UTF-8` → `zh_TW.UTF-8`; `C.UTF-8` → `"C."` + `"UTF-8"` = `C.UTF-8`; `C` → no name, so `newlocale` gets `""` and reads the environment itself.
4. **The codeset.** `__EMSCRIPTEN__` selects the Linux table (`nlsupport.cxx:33-38`, `:285`) and `nl_langinfo_l(CODESET, newlocale(LC_CTYPE_MASK, name))` (`:575-594`). In Emscripten's musl, `nl_langinfo_l(CODESET)` is `"UTF-8"` whenever the LC_CTYPE category is non-null, else `"ASCII"` (`system/lib/libc/musl/src/locale/langinfo.c:35`). `__get_locale` returns null for LC_CTYPE **only** for the exact names `"C"` and `"POSIX"`; `"C.UTF-8"` is the built-in UTF-8 map, and any other name — real or not — gets a map object that inherits the C.UTF-8 map (`locale/locale_map.c:45-63`, `:99-116`; Emscripten compiles out `MUSL_LOCPATH`, `:68-97`). An empty name reads `LC_ALL`/`LC_CTYPE`/`LANG` and defaults to `"C.UTF-8"` (`:45-50`); a name longer than 23 bytes falls back to `"C.UTF-8"` (`:53-54`, `internal/locale_impl.h:9`). `"UTF-8"` maps to `RTL_TEXTENCODING_UTF8` (`nlsupport.cxx:466`); `"ASCII"` is **not** in the Linux table (it is only in the BSD tables, `:474`, `:498`), so it would become `DONTKNOW` → `ASCII_US`.
5. **The environment our engine gets.** Emscripten's default environment sets `LANG = (navigator.language || 'C').replace('-', '_') + '.UTF-8'` unless built with `-sDETERMINISTIC` (`upstream/emscripten/src/lib/libwasi.js:49-66`, the default at `:57`), and lets `ENV` override it (`:71-77`). The core's pre-js sets only `ENV.MAX_CONCURRENCY` (`static/emscripten/environment.js:1-4`); our link adds no other pre-js that touches the environment (`wasm_sdk_probe/Makefile:852-854`; the only `--wrap` is `initJsUnoScripting`). [BYTES] The shipped `dist/profiles/e2-editor-v20/probe.js` contains `navigator.language||"C").replace("-","_")+".UTF-8"` once and `ENV.MAX_CONCURRENCY` as its only `ENV.` assignment; `sdk/sdk-worker.js` sets no `LANG`/`LC_*`.

**Inference.** `LANG` in our WASM process always ends in `.UTF-8` (`zh_TW.UTF-8` for a zh-TW browser, `C.UTF-8` if `navigator.language` were missing), so musl reports `UTF-8` and the byte flavour is decoded as UTF-8: the CJK case should come out right **in WASM**, unlike native `LANG=C`. The only ways to get a non-UTF-8 decode would be an environment where `LANG`/`LC_CTYPE`/`LC_ALL` is exactly `C` or `POSIX` — which our loader does not create — and then the result would be `ASCII_US`, not the ISO-8859-1 that glibc gives natively (step 4). This is a reading, not a measurement: the first WASM paste of M8 is the test (plan §4 step 1d or the v21 link).

## Hazards

### Remote image URL (M11, M11b, M11c) [OBS unless marked]

- `![x](http://…)` makes Writer open the URL **inside the `paste()` call** to learn the image size (`GraphicDescriptor(aGraphicURL).Detect(true)`, `swmd.cxx:691-696`, allowed because `allowAccessLink` is true for a document without an untrusted referer, `swmd.cxx:71-80`) [SRC].
- M11b, `strace -e connect,write` (`out/P1-M11b-strace/run1/strace-connect-write.txt`): two `connect()` to `127.0.0.1:18765` from a worker thread, 3.8 ms and 5.3 ms after the probe printed `undo-before`, and 2.6 ms **before** it printed `paste`. The listener logged one `GET /x.png` per run (3/3), `User-Agent: LibreOffice 26.8.0.1 denylistedbackend/8.21.0 OpenSSL/3.5.7`; stderr shows the first request was a WebDAV `OPTIONS`, answered 501. No second fetch at paint or save.
- M11 (port 9, refused): one `connect()` to `127.0.0.1:9` (`out/P1-M11-strace/run1/strace-connect.txt`), `curl_easy_perform failed: (7) Failed to connect` in stderr; the paste took 3.1-3.5 ms.
- M11c (accepts, never answers): **`paste()` returned after 5,003.2-5,003.5 ms** (3/3). The tarpit saw one connection with `OPTIONS /x.png`, and the client closed it only at process exit (about 9.7 s). The 5 s is `UcbLockBytes`'s "server not responding after five seconds" timeout (`unotools/source/ucbhelper/ucblockbytes.cxx:693`, `:727-760`): with no interaction handler it aborts [SRC]. The image is still inserted as a link.
- Not measured: a host that does not answer the TCP handshake at all (curl's connect timeout is `Inet::Settings::ConnectTimeout` = 20 s, `officecfg/registry/schema/org/openoffice/Inet.xcs:112-117`, set at `CurlSession.cxx:759-765`; whether the 5 s moderator timeout or that one wins was not tried).
- [BYTES] The fetch path is in the shipped WASM: `dist/profiles/e2-editor-v20/probe.wasm` (`313b08d5…`) contains the UTF-16 literals `server not responding after five seconds` and `com.sun.star.comp.WebDAVContentProvider` once each and the SAL_WARN strings `curl_easy_perform failed` (1) and `OPTIONS - DAVException` (2); `wasm-lite/build-headless-probe/instdir/program/soffice.js.linkdeps` has `-lucpdav1` and `-lcurl`. [INF] What a fetch does inside the WASM worker (fail at once, try a socket through Emscripten's emulation, or wait 5 s) is unknown.

### Empty input (M13) [OBS]

- No block, natively: `paste()` returned `true` in 1.3-1.6 ms, the document is unchanged, an undo action `Paste clipboard` was added, and `.uno:ModifiedStatus=true` and `.uno:Undo=enabled` were sent exactly as for a real paste. The only difference in the callbacks: no `INVALIDATE_VISIBLE_CURSOR` (the caret did not move).
- `out/DIAG-gdb-M13/` (`tool/run_gdb_diag.py`, `tool/gdb_dialog_trace.py`, release build, return values read from `rax`): `SwTransferable::PasteFileContent` → `SwReader::Read` → `SwMarkdownParser::CallParser` → **`MessageDialog` constructed** → `Dialog::Execute` → `Dialog::ImplStartExecute` **returned 0**, `Execute` returned 0, `PasteFileContent` returned 0 (false). The control `out/DIAG-gdb-M1/`: no `MessageDialog`, `PasteFileContent` returned 1.
- Why 0 [SRC]: the dialog has no parent, so under LOK it has no notifier; `ImplStartExecute` then `return false` (`vcl/source/window/dialog.cxx:900-921`; the `assert` there is compiled out by `-DNDEBUG` in both builds). The empty-input error itself is `ERRCODE_IO_INVALIDCHAR` from `swmd.cxx:931-934`, turned into `STR_ERROR_CLPBRD_READ` and a dialog at `swdtflvr.cxx:2293-2317` because `bMsg` is true for `.uno:Paste` (`:1856`).
- [INF] The WASM core is configured the same way (`ASSERT_ALWAYS_ABORT=FALSE`), so the same early return is expected there; not observed. Collabora never pastes empty data (`if (size > 0)`, `ChildSession.cpp:1887`).

### Wiki links (M12) [OBS]

`[[Page]]` becomes `https://zxx.wikipedia.org/wiki/Page`. The URL takes `GetAppLanguageTag().getLanguage()` (`mdcallbcks.cxx:226-227`), which under LOK is `comphelper::LibreOfficeKit::getLanguageTag()` (`vcl/source/app/settings.cxx:2697-2698`); that tag defaults to `LANGUAGE_NONE` = `zxx` (`comphelper/source/misc/lok.cxx:81-84`) and is set only by a `Language=` load option (`desktop/source/lib/init.cxx:2858-2861`) or `doc_createViewWithOptions` (`:6955-6970`) — `setLanguageAndLocale(u"en-US")` at `:8347` writes the configuration, not this tag [SRC]. Our engine loads without `Language=` (`probe_engine.cpp:2992-2993`), so [INF] WASM would write `zxx.wikipedia.org` links too. Ties to plan §2.6 (`Language=`).

### CJK bold and italic [OBS + SRC]

`**粗體中文**` is saved as a span whose automatic style has only `fo:font-weight="bold"` — no `style:font-weight-asian` (`out/P1-M8/run1/after.fodt.gz`, style `T1`). Writer formats CJK characters with the Asian attributes, so [INF] the text is not shown bold. Cause [SRC]: `MD_SPAN_STRONG` inserts only `SvxWeightItem(WEIGHT_BOLD, RES_CHRATR_WEIGHT)` and `MD_SPAN_EM` only `RES_CHRATR_POSTURE` (`sw/source/filter/md/mdcallbcks.cxx:158-163`), no CJK/CTL counterparts. Headings are bold in all three scripts through the heading style. Possibly an upstream defect; not filed (upstream submissions are on hold) and the rendering was not looked at.

### Large input (M14) [OBS]

16.6 KB: 81-111 ms in the call. 262 KB: 3.0-3.1 s in the call, 14,561 paragraphs, 40,268 `CORE_LOG` and 391 `DOCUMENT_SIZE_CHANGED` callbacks after it. One `.uno:Undo` restored it (3/3). The new path has no size limit of its own; the input adapter's 16 KiB (`input/input-adapter.js:1`) does not apply to it (fact sheet 1(e) 7).

### Other observations

- Soft line breaks inside a paragraph become U+00A0 (`mdcallbcks.cxx:293-296`) [OBS M7, SRC].
- A table pasted at the start of an empty document leaves an empty paragraph before it and two after (M5) [OBS].

## Controls

- **C1, the red control (Ctrl+V unchanged)** [OBS]: M1+M2 as `text/plain;charset=utf-8` stays literal — six `Standard` paragraphs with `#`, `**`, `` ` `` visible, no heading, no bold (3/3). The text has line breaks, so it is six paragraphs, not one.
- **C2, the reader goes red** (`tool/check_reader_red.py`, `out/C2-reader-red/result.txt`, exit 0):
  - a: M1 vs C1 → DIFFERENT (expected DIFFERENT);
  - b: M1 run 1 vs run 2 → SAME (the positive control);
  - c: M2 vs the same file with every bold attribute deleted → DIFFERENT;
  - d: M1 vs the same file with its `text:h` rewritten as `text:p` → DIFFERENT;
  - e: P5-M4 vs the same file without its list-item `text:style-override` → DIFFERENT (see below).
- **Undo comparison**: `undo-1` equals `before` in 152/152 runs; the same comparison says `after` differs from `before` in every run except M13, where nothing changed.
- **Position read-back**: 152/152 as intended (`positionReadbackAsExpected`).

## Fixed because of execution (declared)

1. **Reader** (`md_structure.py`): it ignored `text:style-override` on `text:list-item`, so P5-M4's numbered items read as bullets. Found by reading `out/P5-M4/run1/after.fodt.gz` by hand after the campaign. Fixed; all summaries regenerated from the kept `after.fodt.gz` by `tool/resummarize.py` — only P5-M4 (3 runs) changed signature. P1-M14b runs 2-3 keep no `after.fodt.gz` (size); run 1 did not change and runs 2-3 had the same signature as run 1. Red case e above was added with the fix.
2. **Probe**: a first pass listed every `CORE_LOG` callback (10 MB of stdout for M14b); it was discarded, the probe changed to count them, and **every arm was run again** with the final binary. Nothing from the first pass is used.
3. **Runner**: the busy check first matched its own shell's command line (a diagnostic loop that waited forever; killed, no LOK process ran); it now ignores shells and Python runners.
4. **gdb trace**: release build, no debug info, so `FinishBreakpoint.return_value` was empty; it now reads `rax`. The diagnostic was rerun with the final binary.

Arms added after the first full run, each with the reason in `run_arms.py`: `P1-M11b-strace` (when the fetch happens) and `P1-M11c` (a server that never answers). `make_corpus.py` gained M11c; every other corpus file is byte-identical (checked with `sha256sum` before and after).

## Predictions written before the run (`out/predictions-before-run.txt`) against the results

| # | prediction | result |
| --- | --- | --- |
| 1 | M1-M7 convert | held |
| 2 | one undo action, one Undo restores | held (152/152) |
| 3 | M8 right under UTF-8 locales, ISO-8859-1 mojibake under C | held |
| 4 | `text/plain` under C right | held |
| 5 | no-charset = charset; utf-16 garbage | held |
| 6 | M9 right / mojibake under C | held |
| 7 | **M13 blocks on a modal dialog** | **wrong**: the dialog is created and cancelled at once (no LOK notifier) |
| 8 | M11 connects during the paste, image kept as a link | held (strace) |
| 9 | M11b listener sees a GET during the paste | held, preceded by an `OPTIONS` |
| 10 | **M12 → `en.wikipedia.org`** | **wrong**: `zxx.wikipedia.org` (the LOK language tag is unset, not en-US) |
| 11 | P4: first block + left half, last block + right half | **half wrong**: the first block joins the left half (and loses its block format); the right half stays a separate paragraph |
| 12 | P6/P7 replace the selection | held |
| 13 | C1 literal | held |

## What this does NOT show

- **Anything about WASM.** No WASM process ran. The codeset reading above, the empty-input early return, the remote-image fetch, the wiki-link host and the `CORE_LOG` volume in WASM are inferences. The engine hard-codes `text/plain` (`probe_engine.cpp:3239`), so the first WASM evidence needs a link: plan §4 step 1d (a diagnostic profile, the owner's `make`) or the v21 link itself.
- What the user **sees**: no rendering was checked (CJK bold, list labels, image boxes). Structure was read from the saved flat ODT only.
- Paste into a table cell, a header or footer, a frame, or a document that starts with a table; Markdown that opens or closes inside a list the caret is in (other than P5); nested blockquotes, strikethrough (`~~`), task lists, HTML blocks, footnotes, reference-style links, setext headings — none were in the corpus.
- A host that never completes the TCP handshake (only refused, 404 and accept-then-silence were tried); `https` URLs; redirects.
- Behaviour under `Language=`: every run loaded without load options, as our engine does.
- Undo of a paste followed by more edits, Redo, or an undo stack that is not empty before the paste.
- Desktop LibreOffice's own Paste Special → Markdown (not LOK); Collabora's UI.
- Timing beyond this host: the call times are native x86-64 under `nice -n 10`. 24 of our 152 processes ran at the same time as a 142-arm process (`out/overlap-with-142.txt`): our runner waited for a gap, but the 142 runner does not wait and started its next process during ours. The structure results cannot be affected; the paste times of those runs lie inside their arms' ranges.

## Reproduce

```
S=<scratch>/native-md; E=findings/evidence/link-batch-v21/native/markdown-paste
g++ -std=c++17 -O2 -Wall -I libreoffice-26-8/include $E/tool/md_paste_probe.cpp -ldl -lpthread -o $S/md-paste-probe
python3 -I $E/tool/make_corpus.py $E/tool/corpus          # byte-identical corpus
python3 -I $E/tool/run_arms.py $S/md-paste-probe $S/runs $E/out [ARM_ID_PREFIX ...]
python3 -I $E/tool/run_gdb_diag.py $S/md-paste-probe $S $E/out M13 M1
python3 -I $E/tool/resummarize.py $E/out                   # only needed after a reader change
python3 -I $E/tool/check_reader_red.py $E/out             # C2, exit 0 = all five cases as expected
python3 -I $E/tool/aggregate.py $E/out                    # out/RESULTS.md, out/results.json
python3 -I $E/tool/md_structure.py out/P1-M1/run1/after.fodt.gz      # one summary
python3 -I $E/tool/md_structure.py --compare A.fodt.gz B.fodt.gz     # SAME / DIFFERENT
```

`run_arms.py` skips a run whose `summary.json` exists; delete the arm's folder to run it again. It starts the 18765 listener and the 18766 tarpit itself.

## Files

- `tool/md_paste_probe.cpp` — the probe; `tool/run_arms.py` — the arm matrix and runner; `tool/md_structure.py` — the structure reader; `tool/aggregate.py`, `tool/resummarize.py`, `tool/check_reader_red.py`; `tool/run_gdb_diag.py` + `tool/gdb_dialog_trace.py` — the M13 dialog trace; `tool/make_corpus.py` + `tool/corpus/` — the corpus; `tool/inputs/` — the three documents.
- `out/<arm>/run<k>/`: `cmd.txt` (exact command and environment), `stdout.jsonl` (the probe's own lines: env, opened + thread encoding, position read-back, undo before/after, paste return and time, every callback, paint, save, each undo step), `stderr.txt` (core's SAL_WARN lines; cut to 40 KB if larger — none was), `before.fodt.gz`, `after.fodt.gz` (P1-M14b: run 1 only), `summary.json` (everything the runner derived). `P1-M11-strace`, `P1-M11b-strace` add the strace logs.
- `out/DIAG-gdb-M13/`, `out/DIAG-gdb-M1/` — the gdb traces; `out/C2-reader-red/result.txt`; `out/RESULTS.md`, `out/results.json`; `out/runner.log` (every run and every wait for another session's process); `out/predictions-before-run.txt`.
- `SHA256SUMS` — every file in this folder except itself.
