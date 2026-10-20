# Handoff, 2026-10-20f: the ODS-in-Nextcloud plan, reviewed by fable and amended; nothing run or linked for it yet

**First line:**
- **The owner's goal: 「Nextcloud 裡點 .ods 就能開」.** The plan is `3e2d89c5`. fable's adversarial review and the plan's amendment are `5c89bc27`. **Verdict: the plan holds, with changes before the link.**
- **Nothing for it has been run, linked or installed.** Next is Step 0, which is done by reading: the spec, and the draft page's fixes.
- **The real benefit of the calc core is Calc, not a11y.** The shipping core `build-headless-probe` has no Calc. `build-a11y-gate0` (writer+calc+a11y) is already built.
- v23 is paused exactly as `HANDOFF-2026-10-20e-v23-paused-ruling-3-spreadsheets-first.md` left it. Its detail is there, not here.
- The main session's context passed its soft limit. The owner said to hand off at the end of this round.

Sources to read, in this order:
- `handoff/PLAN-2026-10-20-nextcloud-opens-ods.md`. **Its amendment at the end supersedes parts of the body:** D2, E2–E6, E8, O3, O6, H1, H2, H4, H6, the 089 register, and D5's "× 1.4" (withdrawn).
- `handoff/REVIEW-2026-10-20-fable-ods-in-nextcloud.md`. §1 is the owner's plain-language summary. §4 is the cheaper first step.

## What happened (commits in order)

1. **The core fact (no commit; also in 10-20e's First line).**
   - The owner asked what the a11y core would buy.
   - `build-headless-probe` is `--with-wasm-module=writer` with `ENABLE_WASM_STRIP_CALC=TRUE`. v22's `probe.wasm` contains `ScDocShell` 0 times.
   - `build-a11y-gate0` is writer+calc (+a11y), already built.
   - The benefit for the owner's goal is Calc. **The owner chose A: spreadsheets first.**
2. **Research (no commit; a research agent's report, summarised).**
   - The shipping line was never on the calc core.
   - v9–v14 were an a11y candidate line on `build-a11y-gate0` that was never cut over:
     - 09-09: the owner deferred the soak gate;
     - 09-30: a packaging limit was registered;
     - 10-06: paragraph merge went to the v8 line only;
     - 10-12: "Calc = B, one variable per link".
   - `handoff/PLAN-2026-09-03-ods-reading.md` stopped half way, and no pause was recorded:
     - G1–G10 were never run as gates;
     - the diagnostic runs W2, W5, W6 and W9 were done: 303 of 306 files open, and 100k cells cost 23.6 MiB.
   - Finding 089 (some `.ods` hang) is cured by a pthread stack of ≥ 256 KB. That was measured on v12 through the loader literal. v22 carries 1 MiB, but v22 is writer-only.
3. **A demo of the W9 draft viewer for the owner (no commit; diagnostic).**
   - What it is: a symlink mirror of `wasm_sdk_probe/dist`, plus the five viewer files.
   - Where: `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/219d1e09-eaf4-4529-b0a7-a93d93cf3c18/scratchpad/ods-demo/root`.
   - Served by `wasm_sdk_probe/web/serve.py` on port 8771, at `http://127.0.0.1:8771/ods-viewer.html?profile=e2-editor-v14`.
   - Its limits: sheet 1 only, a spoofed `.odt` name, about 12 px left unpainted, and 089 on some files.
   - **The server and the scratchpad die with this session.** To rebuild it:
     - make one symlink per top-level entry of `dist/`;
     - copy `web/ods-viewer.html` and `web/ods-viewer-app.js`;
     - copy `viewer-shell/{ods-viewer-session,w7-adapter,viewer-error}.js`.
   - **Nobody knows whether the owner tried it.** Ask.
4. **The plan, a draft for review (`3e2d89c5`).**
   - A separate read-only viewer engine, `ods-viewer-v1`, on `build-a11y-gate0` with the 1 MiB stack.
   - The ODT editor is untouched: `e2-editor-v22`, shell v75 and worker `0d55bcfa…` stay byte for byte.
   - Plus: a second Files action, a read-only route, and host 0.2.29 as an uncounted candidate.
   - Criteria: E1–E9 on a mirror and H1–H7 in the host, each with its default.
5. **fable's review, verbatim, and the amendment that disposes it (`5c89bc27`).**
   - The main session spot-checked B1, B2, C2 and C3 against the source. All four are as stated. The rest are carried as the review states them, and each is re-read when its work item is done.
   - **B1:** the reader base has no text read-back. The fix is a per-part read-back, `oxsdk_document_part_text`, with the capability `part-text`.
   - **B2:** the tile reply has no size fields on the reader base. They go under `OXSDK_E2_FORMAT_BARRIER || OXSDK_ODS_VIEWER`, and E4 is split into an engine half and a page half.
   - **C1:** the first `.ods` costs about 43 MB zstd with `cjk-sub-e10` shared, and about 55 MB without it. E8 now pins base `9901e9be…` and the shipping CJK pack.
   - **C2:** two `:root` rules make the host answer 500.
   - **C3:** the packager takes one page, one worker literal and one profile. The amendment moves it to manifest `litecore-engine/3`.
   - **C4:** "× 1.4" is withdrawn. This became D5.
   - **C5:** subclass `DocumentEngine` rather than duplicate it. This became D3.
   - **C6:** the encrypted-file refusal was vacuous. Encryption is now detected before the engine, from `META-INF/manifest.xml`, and refused as `ENCRYPTED_DOCUMENT`.
   - The viewer drops save (M2).

## Next (the plan amendment's revised order)

0. **Step 0, by reading, now.**
   - Write `specs/SPEC-M4-ods-in-nextcloud.md` (zh-TW). Pin the criteria, with the amendment folded in. This is O1.
   - Fix the draft page:
     - one `:root` rule;
     - a hard-coded `workerUrl: "./profiles/ods-viewer-v1/sdk-worker.js"`, and no `?profile=`;
     - the draft chrome hidden in production;
     - encryption detection in the session.
1. **Step 1: a mirror run, with no link and no ddev.**
   - The W9 page on `e2-editor-v14` (the same calc core), with 089's loader literal set to 1,048,576, through the page's own file input.
   - Files: `tdf149752.ods`, `three-sheets-distinct.ods`, `numeric-100k.ods` and `password.ods`.
   - It gives opens of the E2 kind, peak `sbrk`, and 089 at 1 MiB on the page's path.
   - It **cannot** measure the reader object set on this core. Only the link can, so E2 remains the link's first run.
   - The literal patch lives in `tools/probe_ods_on_profile.py` (`--pthread-stack-size`, anchor `,!ENVIRONMENT_IS_WEB,65536,false);` exactly once). `run_ods_viewer_draft_smoke.py` has no such option.
   - (Inference) In the demo mirror, `profiles/` is a symlink into the real `dist/`. Patch a copied profile directory, and never write through the link.
2. **Step 2: decide D5,** by measurement or by registration, before the packager is touched.
3. **Then O1–O8 as amended.**
   - **O4, the owner's link, is the first point at which a real ODS viewer engine exists.** The owner's first visible result comes after O4 + E2: the viewer on a mirror page, with real sheet names and tabs.
   - **O7, the host install, needs the owner's ddev slot.** H7 is the owner clicking an `.ods` in Nextcloud.

## Hazards

- **Never `cd` in shell commands.** It slipped once this session and was reverted at once.
- **Compiling `make` targets belong to the owner.** Give the command, the directory and the expected time.
- **ddev is shared.** Host work goes only in the owner's slot.
- **The spec is append-only once pinned.** So is the plan, after its review.
- **`LOBUILD` defaults to the writer-only core** (`wasm_sdk_probe/Makefile:2`). Any calc rule must name `E2_V5_CORE` explicitly. This was the 09-03 trap.
- **Headless Chrome:**
  - `tools/run_ods_viewer_draft_smoke.py` refuses to start while any other Chrome runs, and the owner's Chrome was running on 10-20;
  - before any headless Chrome, check the KDE wallet: `busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`.
- **Fixed at hand-off:** `wasm_sdk_probe/tools/make_caret_delete_fixture.py` had been left out of `2266b090` (only its `.tsv` output was in it). It is committed together with this handoff; `--check` reproduces the committed fixture.

## §34.4

- **This stretch:**
  - because of execution: +0;
  - because of review: +0.
- **Running total since 10-14b: 33 / 27.**
- **No new tool landed after 10-20e.** The review touched no counted check. 10-20e's list of tools not yet reviewed carries over unchanged.

## Owner decisions still open

- **D3: the viewer's SDK** (review C5). Default if not decided: **A**.
  - **A (fable recommends):** subclass the shipped `DocumentEngine` from `viewer-shell/`. Zero bytes change under `sdk/`, no shell generation is minted, and the `_request`/`_initialize` coupling is registered.
  - B: the separate module, as drafted.
  - C: extend `document-sdk.js`. This mints shell v76 and re-binds the editor.
- **D5: the gzip cap** (review C4). Default if not decided: **B**.
  - **A (fable leans):** measure once whether Firefox keeps a 48 MB gzip file in its cache (the X1 instrument, one browser, no ddev), and set the cap to what is measured.
  - B: no gzip cap. Register `L-ods-gzip-fallback-uncached-in-firefox-nozstd`, and state that Z2-2 is not run on the viewer page.
- **Carried over from 10-20e:**
  - whether the product moves to one engine on the calc core (registered; kept out of this plan by D1);
  - A3 for L-C (the feature link only).
