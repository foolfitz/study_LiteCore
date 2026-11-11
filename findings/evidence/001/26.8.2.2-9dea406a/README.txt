Runtime re-check on libreoffice-26.8.2.2, 2026-11-10

Source:    LibreOffice core 9dea406ab7695df6325b11b0e19fdca8db4b7276 (tag libreoffice-26.8.2.2), no local modifications at build time
           (after this build, the same worktree got the two July fs-image patches and the translations submodule for the next build; see build-2682-july-nosym)
Toolchain: emcc 4.0.10 (b7dc6e57), Qt 5.15.2+wasm (allotropia qt5 3d440b7787f9), same as 2026-07-31
Configure: build-2682-lite-nosym/autogen.input = byte-identical to the master lite build: the July crash list (wasm-lite/retired-builds/build/lite-configure-args.txt) with --with-lang=en-US instead of 'en-US zh-TW', plus --with-parallelism=10
           resolved: ENABLE_SYMBOLS_FOR='' ENABLE_RELEASE_BUILD=TRUE -std=c++20 ICU 78 PRODUCTVERSION 26.8
Build:     first make stopped at 6 s on the finding 003 race (dragonbox.version); second make 2026-11-10T19:59:49+08:00 to 2026-11-10T20:37:52+08:00, exit 0
soffice.wasm: 134140975 bytes, sha256 8a7d1cedec242675…
Probe:     unchanged wasm-lite/tools/pw/probe.js, Playwright 1.62.1 / Chromium 151.0.7922.34, emrun with COOP/COEP

Result: lite-nosym-qt_soffice.{txt,png}. Start Center reached, no uncaught exception, same thread sequence as on master. The July crash is NOT reproduced on 26.8.2.2 by the July configuration without zh-TW and without the two fs-image patches.

Second 26.8.2.2 build, same day: exact replica of the July crash build.
Source:    same tag 9dea406a with the two July fs-image patches applied (wasm-lite/patches/libreoffice-26.8-emscripten-fs-image-{multilang-registry,extra-fonts}.patch; diff saved as wasm-lite/upstream-master/src-26.8.2.2.local-modifications.diff, sha256 f2d97dedb296fb28…) and the translations submodule at 171ac7d0 (26.8.2.2's gitlink)
Configure: wasm-lite/retired-builds/build/lite-configure-args.txt unchanged (incl. --with-lang=en-US zh-TW, --disable-symbols) plus --with-parallelism=10; LITE_EXTRA_FONTS_DIR=wasm-lite/tools/extra-fonts as in the July lite-env.sh
Build:     first make hit the finding 003 race at 2 s; second make 2026-11-10T20:43:49+08:00 to 2026-11-10T21:19:54+08:00, exit 0
Outputs:   soffice.wasm 134140990 bytes (sha256 bfa917dba447041a…); soffice.data 102099685 bytes; soffice.data.js.metadata 150276 bytes = identical size to the July crash run (150276 B in ../console.txt); fs image holds 3 zh-TW entries and NotoSansCJK-Regular.ttc
Result: july-nosym-qt_soffice.{txt,png}. Start Center reached, no uncaught exception. The July configuration does NOT crash on 26.8.2.2.

2026-11-10 cleanup: wasm-lite/upstream-master was deleted after this was written; its logs, scripts and configure inputs are in findings/evidence/001/rebuild-2026-11-10/ (see the path mapping in its README.txt).
