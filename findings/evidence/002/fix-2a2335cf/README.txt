Finding 002 fix run, 2026-11-11, LibreOffice core master 2a2335cf

Summary
  F1 (the draft's fix (a)) removes the reported error. vcldemo now loads soffice.data, gets past UNO bootstrap and creates its window.
  It still does not paint. There is no "DemoWin::Paint" line, and the canvas stays blank (dark grey) for 90 s with no error.
  F2 adds soffice_bin's PROXY_TO_PTHREAD/OFFSCREENCANVAS flags. It moves main into a worker but changes nothing visible: still no paint and no error.
  Criteria 2, 3 and 5 of PREDICTIONS.txt are not met by either arm. Per the stop rule there, the run stopped here.

Tree and build
  Source: wasm-lite/upstream-master/src, detached worktree at 2a2335cf. Why not e42678e7: see PREDICTIONS.txt and e42678e7-configure-fail.log.
    The local branch finding002-vcldemo-fs-image has two commits:
      5d2be0e614ed  F1    same content as f1.patch
      31e17b64ec13  F1+F2 same content as f1f2.patch
  Full build: build.sh build-nosym, 2026-11-11 12:02:59 to 12:55:50 +08:00, make exit 0. Started by the agent at the owner's request. Log: build-nosym.log.gz.
  Relinks: relink_vcldemo.sh, which runs make Executable_vcldemo.clean, then make Executable_vcldemo.
    F1   13:02:42 to 13:05:36, exit 0, log relink-F1.log.gz
    F12  13:07:39 to 13:10:24, exit 0, log relink-F12.log.gz
    The ~10,000 "overriding recipe" warnings in these logs come from chart2 makefiles. They appear in every top-level make of this tree and are not caused by the patch.
  Side effect: each relink also regenerated workdir/CustomTarget/static/emscripten_fs_image/soffice.data, because setuprc and versionrc were re-echoed.
    Compared with the installed copy used by C1: same size and same metadata (sha256 df6a3208db5f7639...).
    72 bytes differ, all in /instdir/program/setuprc and /instdir/program/versionrc (36 bytes each).
    F1 and F12 were served the regenerated copy.

Outputs (workdir/LinkTarget/Executable)
  unpatched  vcldemo.js 282,679 B (sha256 5d89e6eab8d4c27e...), no "loadPackage"
             vcldemo.wasm 149,670,826 B (e7f0ef75c6a859e3...)
             Both kept in wasm-lite/upstream-master/archive-unpatched-vcldemo/.
  F1         vcldemo.js 297,061 B, "loadPackage" once. Bytes not kept: the F12 relink overwrote them.
  F12        vcldemo.js 301,776 B (c44caec8aa50f169...), contains _emscripten_proxy_main
             vcldemo.wasm 149,671,118 B (265bdb5e1496f0e4...)

Results
  Probe: wasm-lite/tools/pw/probe.js unchanged, 90 s per run, emrun with COOP/COEP. Files: <arm>-qt_*.txt / .png / .emrun.log.

  arm  soffice.data req.  Bootstrap exc.  window      Paint lines  screenshot
  C0   no                 yes, 0.6 s      -           0            4254 B blank
  C1   yes, 0.6 s         no              Start Ctr   n/a          153599 B Start Center
  R1   yes, 0.5 s         no              yes, 0.9 s  0            4255 B dark grey
  F1   yes, 0.5 s         no              yes, 0.9 s  0            4255 B dark grey
  F12  yes, 0.5 s         no              yes, 2.4 s  0            4255 B dark grey

  "window" means the console line "QObject::connect(QWindow, QtSvpSalFrame): invalid nullptr parameter". qt_soffice.html also prints it when it creates its frame.
  F12 also starts a worker at 0.7 s: the proxied main.
  In every vcldemo arm the page was still responsive at 90 s (page.evaluate returned), and the console had no error line.
  R1 is the no-relink preview (preview_f1.py, files R1-preview-not-evidence-*). It is not evidence. It matched F1 line for line.

Against the predictions (PREDICTIONS.txt, committed 293468b1b before the first probe)
  C0, C1: as predicted.
  R1/F1: as predicted, the data was requested and "Cannot open uno ini" was gone. As I leaned, there was no paint.
    The reason I gave (main thread without a thread pool) is not supported: F12 removes that condition and fails the same way.
    The thread-pool warning did not appear either.
  F12: I leaned toward a paint. It did not paint.

What is established
  F1 is needed for vcldemo to get past bootstrap: C0 against F1, same tree, the only difference is the vcldemo link.
  F1 is not enough for vcldemo to paint, and neither is F1+F2.
Not established
  Why vcldemo stops after creating its window.
  Whether F2 is needed at all.
