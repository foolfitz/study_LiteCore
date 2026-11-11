Runtime re-check: rebuild of the July crash build at its own commit, 2026-11-10

Source:    671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb (the July commit), fresh worktree, translations at 222323f2 (the July gitlink), the two July fs-image patches applied (diff sha256 f2d97dedb296fb28…, identical to the 26.8.2.2 replica)
Configure: wasm-lite/retired-builds/build/lite-configure-args.txt unchanged plus --with-parallelism=10; LITE_EXTRA_FONTS_DIR=wasm-lite/tools/extra-fonts; emcc 4.0.10; Qt 5.15.2+wasm unchanged since 2026-07-31 10:44; Emscripten system-library cache: no library changed since 2026-07-31 (only symbol_lists/*.json)
Build:     fresh build directory, 2026-11-10T21:24:46+08:00 to 2026-11-10T22:02:06+08:00, exit 0; 285 localedata_*.cxx compiled, no LTO, no wasm-ld signature-mismatch warnings
Outputs:   soffice.wasm 134362567 B (July crash build: 130971980 B); soffice.data 102087692 B (July: 102087692 B, identical); soffice.data.js.metadata 150276 B (July: identical)
Result: july-nosym-qt_soffice.{txt,png}. Start Center reached, no uncaught exception. The July crash is not reproducible from source; see ../july-crash-build-stale-lto.txt for what was different about the July tree.

2026-11-10 cleanup: wasm-lite/upstream-master was deleted after this was written; its logs, scripts and configure inputs are in findings/evidence/001/rebuild-2026-11-10/ (see the path mapping in its README.txt).
