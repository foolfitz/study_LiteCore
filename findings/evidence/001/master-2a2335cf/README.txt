Runtime re-check on upstream master, 2026-11-10

Source:    LibreOffice core 2a2335cf091104f36d44809b2fb70a9cd32258df (master, 2026-11-10), no local modifications (git status clean)
Toolchain: emcc emcc (Emscripten gcc/clang-like replacement + linker emulating GNU ld) 4.0.10 (b7dc6e5747465580df5984e723b9d1f10d8e804b); Qt 5.15.2+wasm (allotropia qt5 3d440b7787f9, wasm-lite/tools/qt5-wasm), same as 2026-07-31
Configure: build-nosym/autogen.input =
             --with-distro=LibreOfficeWASM32
             --disable-symbols
             --enable-ccache
             --with-build-platform-configure-options=--enable-ccache
             --with-parallelism=10
           resolved: ENABLE_SYMBOLS_FOR='' ENABLE_QT5=TRUE ENABLE_EMSCRIPTEN_PROXY_TO_PTHREAD=TRUE
           (--disable-symbols equals the default for a non-debug build; static/README.wasm.md recommends --with-distro=LibreOfficeWASM32)
Build:     2026-11-10T18:24:59+08:00 to 2026-11-10T19:13:33+08:00, make exit 0
soffice.wasm: 157197465 bytes, sha256 e335442971166c49…, no custom sections (no name section, no DWARF)
Probe:     wasm-lite/tools/pw/probe.js unchanged (sha256 5629a2b02db417b3…), Playwright 1.62.1 headless Chromium 151.0.7922.34 (same as 2026-07-31); served by emrun with COOP/COEP; driver wasm-lite/upstream-master/run_probe.sh

Result: qt_soffice.html reaches the Start Center (nosym-qt_soffice.png, visually identical to ../screenshot-stock-working.png from 2026-07-31). No uncaught exception; the configmgrWriter thread starts at 1.1 s and the app goes on to start thread-pool and BufferedDecompositionFlusher threads. The 2026-07-31 crash is NOT reproduced by the stock configuration plus --disable-symbols.

Second build, same day: the 2026-07-31 crash configuration (wasm-lite/retired-builds/build/lite-configure-args.txt) on master.
Configure: build-lite-nosym/autogen.input = the July list with one change, --with-lang=en-US instead of 'en-US zh-TW' (zh-TW needs the translations submodule), plus --with-parallelism=10. The two July fs-image patches (language list, CJK fonts) were not applied; they were also present in the July t3 build that did not crash.
           resolved ENABLE_SYMBOLS_FOR='' (same as July). Remaining config_host.mk differences vs July are paths, the language, and master's own changes (-std=c++23 vs c++20, ICU 79.1 vs 78.3, PRODUCTVERSION 27.2).
Build:     2026-11-10T19:18:38+08:00 to 2026-11-10T19:55:30+08:00, make exit 0
soffice.wasm: 136654110 bytes, sha256 c0a7a965088f4dfe…
Result: lite-nosym-qt_soffice.{txt,png}. Start Center reached, no uncaught exception; same thread sequence as the stock build. The July crash is NOT reproduced on master by the July configuration either.

2026-11-10 cleanup: wasm-lite/upstream-master was deleted after this was written; its logs, scripts and configure inputs are in findings/evidence/001/rebuild-2026-11-10/ (see the path mapping in its README.txt).
