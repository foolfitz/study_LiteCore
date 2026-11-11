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

Result: reproduced exactly as on 2026-07-31. qt_vcldemo.html never requests soffice.data or soffice.data.js.metadata; at 0.6 s the console shows 'Bootstrap exception Cannot open uno ini file:///instdir/program/unorc'; screenshot blank (4254 bytes, same size as ../screenshot-blank.png). Static loader check: grep -c 'soffice\.data\|loadPackage' = 0 in workdir/LinkTarget/Executable/vcldemo.js, 1 in workdir/installation/LibreOffice/emscripten/soffice.js.

2026-11-10 cleanup: wasm-lite/upstream-master was deleted after this was written; its logs, scripts and configure inputs are in findings/evidence/001/rebuild-2026-11-10/ (see the path mapping in its README.txt).
