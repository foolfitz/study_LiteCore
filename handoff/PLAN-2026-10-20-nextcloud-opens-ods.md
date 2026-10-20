# Plan, 2026-10-20: clicking an `.ods` in Nextcloud opens it

**Status: draft for fable's adversarial review.** Nothing below has been run, linked, installed or committed beyond this file. After the review this file is append-only: corrections go at the end and name what they replace. Criteria are pinned before any run that would satisfy them (CLAUDE.md §9.1).

**Owner's words (2026-10-20, ~18:45):** 「Nextcloud 裡點 .ods 就能開」. Earlier the same evening the owner chose A, "spreadsheets first", which pauses v23 (`handoff/HANDOFF-2026-10-20e-…`). The owner's reason was 「我主要想早點做出一個成果（可以開試算表）」.

**What "opens" means here.** Reading, not editing. This is the 09-03 decision (route B, a separate read-only viewer; `handoff/PLAN-2026-09-03-ods-reading.md` §0), now inside the host. Editing a spreadsheet is M5 and out of scope. XLSX, ODP and ODG are out of scope.

## 1. Facts this plan rests on (each read or measured, with its source)

**Cores**
- The shipping editor line v8–v22 links `wasm-lite/build-headless-probe`. That core is `--with-wasm-module=writer` with `ENABLE_WASM_STRIP_CALC=TRUE` and strips accessibility (`autogen.input`, `config_host.mk:256-259`).
  - v22's `probe.wasm` holds `ScDocShell` 0 times.
  - It cannot open a spreadsheet.
- `wasm-lite/build-a11y-gate0` is `writer calc`, with Calc and accessibility on. The a11y candidate line v9–v14 linked it (`Makefile:113-127`, `:2298-2317`, `:2508-2527`).
  - `e2-editor-v14/probe.wasm` is 135,237,060 B, of which 47,987,197 B gzip -9 and 36,078,637 B zstd -19 (`specs/SPEC-M3-zstd.md` §1).
- **ODS on that core, diagnostic only** (the file goes in under a spoofed `.odt` name, finding 013):
  - W2: it opens, `parts == 3`, and `view-ready` arrives (`findings/evidence/m4-ods/RESULT-W2-…`);
  - W5: 100k cells cost 23.6 MiB of `sbrk`;
  - the 306-file sweep: 303 open; the three failures are encrypted; `tdf149752.ods` is finding 089.
- **Finding 089:** the switch is the 64 KB default pthread stack. On a mirror-patched v12, 256 KB, 1 MB and 8 MB open the stuck files 3/3 (`findings/089-…`, outcome O-S). `link_product_stack_1m` (1 MiB) exists since v22 (`Makefile:867-882`).
  - **Not measured:** a calc-core link carrying 1 MiB.

**Engine**
- `oxsdk_document_open` refuses any name not ending in `.odt` (`src/sdk_api.cpp:77`).
- The engine has no `setPart`, `getPartName` or `getDocumentType` export. `getParts` is read at open only (`probe_engine.cpp:3076`).
- The worker passes named reply fields only (`sdk/sdk-worker.js:627-630` for `opened`). It is pinned per profile by sha (v21/v22: `0d55bcfa…`).

**Viewer draft (W9; `viewer-shell/`, `web/ods-viewer{.html,-app.js}`; diagnostic)**
- Everything W7 lacks is isolated in `viewer-shell/w7-adapter.js`:
  - the name spoof;
  - `documentType` "unknown (pre-W7)";
  - generated sheet names;
  - part switching refused;
  - no read-back.
- The page imports `./sdk/document-sdk.js`, which is inside the E2-C shell bundle and bound by v75.
- The draft opens bytes from a file input. Its last ~12 CSS px of width go unpainted, because it does not refit after the first paint's `documentSizeChanged`.

**Host (`~/Projects/Nextcloud_Apps/litecore`, installed 0.2.28 `0870695`)**
- `src/files.js` registers one action, for `application/vnd.oasis.opendocument.text` only. It navigates to `/apps/litecore/r/e2-editor.html?fileId=`.
- `lib/Controller/EditorController.php`:
  - serves the packaged engine at `/r/{buildId-policyhash}/…`;
  - re-wraps `e2-editor.html` in a template with COOP/COEP and a CSP that allows wasm;
  - `resolve()` refuses any mime but ODT.
- The page gets the bytes through `globalThis.liteCoreHost = { load, save }`, which `js/litecore-editor.js` provides (`web/e2-editor-app.js:53-59`).
- **Packaging:**
  - `tools/package_m3_engine.py` derives one closure from `e2-editor.html`'s static import graph and its one hard-coded `workerUrl` (`tools/probe_m3_assets.py:127`);
  - it refuses any file over `MAX_GZ_BYTES` = 45,000,000 encoded, in either coding. That figure is the largest size Firefox 156 was measured to keep in its HTTP cache (K0-5).
  - **The calc core's wasm is over it in gzip and under it in zstd.** SPEC-M3-zstd §5 says K0-5 is "re-judged at the a11y cutover", with the reason written, and not relaxed in advance.
- ddev is shared. Host installs and host measurements go in the owner's slot (memory `ddev-is-shared`).

## 2. The design decisions

### D1. Two engines: ODS gets its own viewer engine; the ODT editor is not touched

- **Proposed:** a new profile, working name `ods-viewer-v1`, linked on `build-a11y-gate0`. The ODT editor keeps `e2-editor-v22`, shell v75 and worker `0d55bcfa…`, byte for byte.
- **Why:**
  - Moving the editor onto the calc core puts every v15–v22 feature on a core it was never measured on. Merge, Markdown paste, the 1 MiB stack (153) and page rectangles all ran on the writer-only core. That move would be a second variable on a link whose purpose is "open a spreadsheet" (the 10-12 decision "Calc = B, one variable per link").
  - It would also collide with v23, which is paused at red cases on the writer-only core.
- **Cost:**
  - an `.ods` opens with a second engine download (about 36 MB zstd, then cached, in Firefox up to K0-5's measured 45 MB);
  - the package carries two wasm images;
  - two lineages to keep.
- **Rejected for now, registered as the owner's open decision:** one engine on the calc core for both ODT and ODS. If taken, it is its own link with its own criteria, after this plan.

### D2. What the viewer engine contains: read-only, minimal defines

- **Base:** the read-only R5 rule shape (`writer-reader`), not the editor's. Today that rule is `$(CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_READER_PROFILE` (`Makefile:623-624`), linked with `link_r5_product`, which carries the 64 KB stack (`:841-856`). It has no `OXSDK_EDITOR_DISCOVERY`, so no editor actions, no barriers, no merge, no a11y refresh and no v23 code. Plus:
  - the 1 MiB default pthread stack (`link_product_stack_1m`; 089);
  - a new define, working name `OXSDK_ODS_VIEWER`, adding W7 and nothing else.
- **W7 (engine and worker source):**
  - `.ods` accepted at open, beside `.odt` (finding 013's allowlist; content detection still reads the zip `mimetype`);
  - `documentType` on `opened`, from `getDocumentType`;
  - exports `set_part(k)`, `part_name(k)` and `current_part()`, ordered with paints in the worker queue;
  - a capability bit;
  - the worker's whitelist gains `documentType`.
  - This is a new worker sha for this profile only.
- **To check before writing:** that the reader rule's object set compiles with `OXSDK_ODS_VIEWER` on the calc core's include paths, i.e. `E2_V5_CPPFLAGS` and not `E1_CPPFLAGS`. The 09-03 trap is that `LOBUILD` defaults to the writer-only core.

### D3. The viewer's SDK: its own module, so the bound shell does not move

- `sdk/document-sdk.js` is in the E2-C bundle's `included` list. An additive change still mints a new shell generation and re-binds the editor.
- **Proposed:** `viewer-shell/ods-document-sdk.js`, a separate module that speaks the same worker protocol for open, paint, close and the three part calls. The viewer page imports it instead of `sdk/document-sdk.js`.
- **The duplication is the price, and it is guarded:** a test asserts that the shared message shapes (open, paint, close) match `document-sdk.js`'s, read from the source, so a protocol change in one turns the other red.
- **Alternative:** extend `document-sdk.js` and accept shell v76 with the editor re-bound. Rejected for this plan, for D1's reason.

### D4. The host: a second Files action, a viewer route, read-only end to end

- `src/files.js` gains a second action, for `application/vnd.oasis.opendocument.spreadsheet`, navigating to `/apps/litecore/r/ods-viewer.html?fileId=`. The ODT action is unchanged.
- `EditorController`:
  - a viewer route, which re-wraps `ods-viewer.html` the way `editor()` re-wraps the editor (COOP/COEP, CSP);
  - `resolve()` accepts ODS **only on the viewer route** and ODT only on the editor route.
- A host script, working name `js/litecore-viewer.js`, provides `liteCoreHost = { load }` and no `save`. It takes no lock, writes nothing, and creates no version.
- The viewer page reads `liteCoreHost.load()` when present and keeps its file input otherwise (dev).
- Host version **0.2.29**, an uncounted candidate. The count chain stays batched (memory `release-count-batched`).

### D5. Packaging: two closures, and K0-5 re-judged where the spec said it would be

- The closure becomes the union of `e2-editor.html`'s closure and `ods-viewer.html`'s, each from its own static graph and its own `workerUrl`. The manifest lists both pages.
- **K0-5, proposed re-judgement:**
  - keep 45,000,000 as the cap for **zstd**, which Chrome and Firefox take (SPEC-M3-zstd §2, measured);
  - lift the cap for **gzip** to "≤ the zstd cap × 1.4" (the measured gzip/zstd ratio on v14: 47,987,197 / 36,078,637 = 1.33).
  - gzip is then only what a client not declaring zstd gets, and K0-5's basis, Firefox's cache, no longer applies to it.
  - This is "a criterion written for one recipe, changed with the recipe, reason written". Default if not taken: the calc wasm cannot be packaged, and the plan stops at the host.

## 3. Criteria (pinned before any run; form per CLAUDE.md §1; default if never done per §2)

**Phase E: the viewer engine, on a mirror, no host.** It adapts the 09-03 gate G1–G10. The truth source is `test-docs/ods/manifest.json`, generated by `tools/create_ods_corpus.py`.

| id | criterion | form | if never done |
|---|---|---|---|
| E1 | Corpus closure, as G1 (every `.ods` has a manifest entry with a matching sha; one sweep record per entry) | 2 | no corpus claim; Phase H does not start |
| E2 | Open, as G2, **under its real `.ods` name**: `opened`, `view-ready` ≤ 60 s, `documentType == "spreadsheet"`, `parts == manifest.sheets`. `tdf149752.ods` (089) included. Encrypted files are `expect: "refused"` with a typed refusal | 1 | no file is shown to open; stop |
| E3 | Content, as G3: `set_part(k)` + SelectAll + `getTextSelection` equals the manifest text | 1 | fidelity unmeasured; stop |
| E4 | Paint, as G4 against the same-run controls, and `documentSizeChanged == false` on the **second** paint after the viewer's refit | 1 | stop |
| E5 | Sheet switching, as G5: `current_part()` read back equals the request; distinct and identical fixtures as written | 1 | stop |
| E6 | Memory, as G6: peak `sbrk` < 896 MiB per entry. The leak bound comes from W1's noise floor, fixed before any E6 run counts | 1 | stop |
| E7 | **The ODT side is the same bytes:** `e2-editor-v22`'s five bound identities and shell v75's 13 included paths hash as before (`served_shell_identity()`), and the editor page's closure is unchanged | 2 | ODT is assumed unaffected; Phase H does not start |
| E8 | Core identity: the viewer profile's packs are byte-identical to v14's, its `soffice.js.linkdeps` is `build-a11y-gate0`'s, and `tools/check_core_build_provides.py --capability calc-spreadsheet` passes on the core it names | 1 | the profile may carry the wrong core; stop |
| E9 | The user's path on the mirror page, as G9: the page's file input, `parts == 3`, tab text equals `part_name`, clicking tab k makes the **engine's** current part k (read back), first tiles as E5 | 1 | only the harness path is measured; Phase H may start, with this recorded |

**Phase H: the host (owner's ddev slot)**

| id | criterion | form | if never done |
|---|---|---|---|
| H1 | Files actions by mime: for one fixture each of ODS, ODT, XLSX and PDF, the LiteCore action is offered exactly for ODS (viewer) and ODT (editor) | 1 | the entry point is unmeasured; not shipped |
| H2 | Clicking an ODS reaches the viewer route with that `fileId`. The page reports `parts == manifest.sheets` and `documentType == "spreadsheet"`, and **no write reaches the server**: no LOCK, PUT, MOVE or PROPPATCH in Apache's access log for the session, and the file's ETag and version count are unchanged | 1 | read-only is assumed; not shipped |
| H3 | E9's tab read-back, through the host page | 1 | not shipped |
| H4 | ODT unchanged in the host: the existing host arms for 0.2.28 pass on 0.2.29 as they did, and E7's identities hold in the installed package | 2 | not shipped |
| H5 | Package rules: every file's zstd ≤ 45,000,000 and its frame window ≤ 8 MiB; gzip under D5's re-judged cap; both pages in the manifest; a red case packs a synthetic file over each cap | 1 | not packaged |
| H6 | The viewer route sends COOP `same-origin`, COEP `require-corp`, and a CSP with wasm-eval and `'self'` script and worker sources, as the editor route does | 1 | not shipped |
| H7 | **Owner's round:** the owner clicks an `.ods` in Nextcloud in a real browser and sees its sheets. Mechanical half: the page state matches H2/H3. Judgement half: recorded | 1 / recorded | 0.2.29 stays an uncounted candidate; the result is not claimed |

## 4. Work, in order, with who and what it disturbs

| # | item | who | disturbs |
|---|---|---|---|
| O1 | Spec file `specs/SPEC-M4-ods-in-nextcloud.md` (zh-TW) with §3 pinned. This plan's review comes first | us | nothing |
| O2 | W7 in source under `OXSDK_ODS_VIEWER`, red cases first: the `.ods` name accepted only under the define (the editor rules still refuse it); `set_part` out of range refused; `current_part` reads core | us | nothing bound (new define; editor rules do not define it) |
| O3 | Makefile rule `ods-viewer-v1` on `E2_V5_CORE`, the reader object set, `link_product_stack_1m`; its own build/dist dirs; guarded from the first link; a runbook | us | the Makefile (every older target becomes out of date; finding 042's standing caveat) |
| O4 | **The link (the owner's make).** No core rebuild | owner | `build/`, `dist/profiles/ods-viewer-v1/` |
| O5 | Phase E on a mirror (E1–E9). The viewer gains its SDK module (D3) and the width refit | us | nothing bound |
| O6 | Host 0.2.29: `files.js`, the controller route, `litecore-viewer.js`, the packager's two closures, K0-5 (D5), tests | us | the app repo |
| O7 | **Install in the owner's ddev slot**, then H1–H6 | owner + us | ddev |
| O8 | H7, the owner's round | owner | — |

## 5. Named limits and risks (registered, not gated)

- **L-ods-read-only:** no editing, no save, no lock; an `.ods` opened here cannot be changed in LiteCore.
- **L-ods-one-file-type:** XLSX is not opened (the calc core's `calc.xcd` has no `calc_MS_Excel_2007_XML`; PLAN-09-03 §1 limit 3).
- **L-ods-second-engine-download:** the first `.ods` costs about 36 MB zstd more than the first `.odt`.
- **Risk, unmeasured:** 089 on a calc-core link with 1 MiB (measured only by patching v12's loader in a mirror).
- **Risk, unmeasured:** `getDocumentType` and `setPart` under the threaded engine on this core; the paint order after `setPart` (tiles queued before the switch).
- **Risk:** richdocuments or another office app installed beside LiteCore competes for the default action on `.ods`. `order: -1` and `DefaultType.DEFAULT` are what the ODT action does today.
- **Not in this plan:** v23; the product moving to one engine on the calc core; ODP/ODG (an owner core rebuild with `impress`, PLAN-09-03 §7).

## 6. What the review is asked to attack

1. D1: two engines. Is "the editor untouched" worth a second engine, and is anything in the host or the package shared that makes the ODT side move anyway?
2. D2: is the reader rule a sound base on the calc core? What does the minimal define leave out that a viewer needs, and what does it keep that it should not?
3. D3: a second SDK module against a re-bound shell. Is the guard test enough to keep the protocol from drifting?
4. D5: is the gzip re-judgement honest, or is it relaxing a criterion to fit the artefact? What would make it wrong?
5. §3: each criterion's form and default. Which can be satisfied without meaning anything (vacuous), which lack a positive control, and where is "X did not happen" claimed without a control? H2's "no write" needs a positive control, a session that does write, seen in the same log.
6. Anything this plan assumes about the host (`liteCoreHost`, the file action API, the template wrapping) that the host's source contradicts.
7. The order: is there a cheaper first step that would falsify the plan before the owner's link, as W2 did on 09-03?

---

# Amendment, 2026-10-20 ~19:10: fable's adversarial review, disposed (append-only; nothing above is edited)

Review: `handoff/REVIEW-2026-10-20-fable-ods-in-nextcloud.md`. Verdict: **the plan holds, with changes before the link.** The main session spot-checked B1, B2, C2 and C3 against the source; all four are as stated. The other findings are carried as the review states them, and each is re-read when its work item is done.

## What changes (all accepted)

- **D2 is replaced:** the viewer's define adds three things.
  - W7;
  - **a per-part text read-back**, e.g. `oxsdk_document_part_text(handle, k)`. On the engine thread it does setPart(k), `.uno:SelectAll`, `getTextSelection("text/plain")` and a deselect, and replies with the text. Capability string `part-text`. (B1: the reader base has no selection export, so E3 could never be measured);
  - **the tile reply's three size fields** under `OXSDK_E2_FORMAT_BARRIER || OXSDK_ODS_VIEWER` (B2).
  - The viewer **drops save** from its exports and capability bits (M2).
  - W7's worker half also needs `OPERATION_CAPABILITIES` entries and reply cases for the three part calls (M2).
  - The input file's suffix follows the accepted name, so `documentLoad` sees `.ods` (M1).
  - **Each addition gets a red case first.** The accessibility switch at open is registered, not gated (M2).
- **E2:**
  - the refused clause returns to 09-03's G2: "a typed refusal before the engine queue". Encryption is detected in the viewer session from the zip's `META-INF/manifest.xml` (`manifest:encryption-data`) and refused as `ENCRYPTED_DOCUMENT` (C6);
  - new negative control: an ODT through the viewer is refused on `documentType`;
  - "under its real name" holds only after M1's fix.
- **E3** runs on the part-text read-back.
- **E4 is split:**
  - engine half as written;
  - page half: after the first paint the surface's CSS size equals the post-paint width, and a tile covering `x = widthPx − 1` was drawn. The current draft is the red case: it reproduces the 12 px gap (B2).
- **E5** adds: asking for the current part again reads back unchanged, and an out-of-range part is refused.
- **E6:** the leak bound's noise floor is re-measured on the viewer link (5 boots) before any E6 run counts (M8).
- **E8 is replaced:**
  - the base pack is the one sliced from `build-a11y-gate0` (`9901e9be…`);
  - the CJK pack is the shipping `cjk-sub-e10` bytes, one file shared with the editor;
  - `fallback-fonts` stays as today (C1).
- **O3 names the builder.** No existing tool does "reader shape + a11y-core slice" (C1, inference). A builder step is written, red case first.
- **L-ods-second-engine-download** becomes about 43 MB zstd with the CJK pack shared, about 55 MB without (C1).
  - Registered as well: adding files moves the package address, so every warm browser re-downloads the editor once (M6).
- **O6 grows.**
  - **The host:**
    - a page table in `asset()` (page → script constant, resolver mime, template);
    - `templates/viewer.php`;
    - the viewer page keeps one `:root` rule, and its draft chrome is hidden in production;
    - red case: two `:root` give a 500 (C2).
  - **The Files action:**
    - one action whose `enabled` accepts both mimes and whose `exec` picks the route by mime (a duplicate id is silently dropped);
    - `js/litecore-files.mjs` rebuilt and committed (M3).
  - **The packager:**
    - `PAGES` with a page table;
    - manifest schema `litecore-engine/3` with `source.pages`;
    - the viewer hard-codes `workerUrl: "./profiles/ods-viewer-v1/sdk-worker.js"` and drops `?profile=`;
    - red cases for zero or two worker literals, and for a one-page manifest under schema 3;
    - the controller, `check_m3_assets.py` and the release tools follow;
    - staging into `dist/`: `web/ods-viewer*`, `viewer-shell/` and the profile (C3).
  - **The host contract** is named: the viewer's host script provides `{ load }` only, under a name the page shape-checks, `liteCoreViewerHost` (review §3 item 6).
- **H1** reads: offered for ODS and ODT, not offered for the two sampled other mimes. The ODS row is the positive control.
- **H2's positive control:** in the same run, an ODT editor session that does write (LOCK at open), read from the container's Apache `access.log`. Red case: a viewer host script that takes a lock (M4).
- **H4:** the assets arm's K0 closure is re-judged, with the reason written (C3). The other host arms are as written.
- **H6** reads: the viewer page's COOP, COEP and CSP equal the editor page's in the same run, modulo nonce (M5).
- **The 089 register** reads: measured through the loader literal on this core (v12). The unmeasured residual is the reader object set on this core (M7).

## Owner decisions, open at the time of writing

- **D3** (review C5):
  - **A (fable recommends):** subclass the shipped `DocumentEngine` from `viewer-shell/`. Zero bytes change under `sdk/`, no shell generation is minted, and the coupling to `_request`/`_initialize` is registered;
  - B: the separate module as drafted;
  - C: extend `document-sdk.js`, which mints shell v76 and re-binds the editor.
  - Default if not decided: A.
- **D5** (review C4). "× 1.4" is withdrawn.
  - **A (fable leans):** measure once whether Firefox keeps a 48 MB gzip file in its cache (the X1 instrument, one browser, no ddev), and set the gzip cap to what is measured;
  - B: no gzip cap; register `L-ods-gzip-fallback-uncached-in-firefox-nozstd`, and state that Z2-2 is not run on the viewer page.
  - Default if not decided: B. It claims less, and the measurement can still replace it.

## The order, revised (review §4)

0. **Step 0, by reading, now.** Fold the changes above into the spec (O1) and the draft page.
1. **Step 1, a mirror run with no link and no ddev.** The W9 page on `e2-editor-v14` (the same calc core) with 089's loader literal at 1,048,576, through the page's own file input, on `tdf149752.ods`, `three-sheets-distinct.ods`, `numeric-100k.ods` and `password.ods`. It gives E2-like opens, peak `sbrk` and 089 at 1 MiB via the page's path. **It cannot measure the reader object set on this core;** only the link can, so E2 is the link's first run.
2. **Step 2:** D5 decided, by measurement or by registration, before the packager is touched.
3. Then O1–O8 as amended.

**The owner's first visible result:**
- after O4 and E2: the viewer on a mirror page, with real sheet names and tabs;
- second: the host integration (H), where clicking an `.ods` in Nextcloud opens it.
