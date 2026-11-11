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

=====================================================================
Continued 2026-11-11 14:45-15:15: the owner chose to dig further (option A after the stop)
=====================================================================

Summary
  The missing paint has a second cause, in vcldemo.cxx and not in the link.
    On Emscripten (without JSPI), Application::Execute() ends in QApplication::exec().
    QApplication::exec() unwinds the stack with a JS exception (simulateInfiniteLoop).
    With -fwasm-exceptions, that unwinding runs the destructors of the objects vcldemo's Main() keeps on the stack. The main window is disposed right after it has been shown.
    desktop/source/app/sofficemain.cxx documents the same problem for soffice. It leaks its desktop::Desktop on purpose.
  Fix F3 leaks vcldemo's renderer and windows the same way.
  F1+F3 paints the demo grid, zooms on a click and returns on Escape. F2 is not needed.
  Final patch: fix-final.patch (sha256 32e97d257c50819f...), one commit 1c96c7bfd8af on the local branch finding002-vcldemo-fix. It touches vcl/Executable_vcldemo.mk (+8) and vcl/workben/vcldemo.cxx (+17).

Method and order (all on the same build-nosym tree; each step relinks only vcldemo, about 3 min)
  Not possible: SAL_LOG. This stock configuration has ENABLE_SAL_LOG empty, so SAL_INFO/SAL_WARN are compiled out.
  1 DIAG1-3, branch finding002-vcldemo-fs-image (acd78966f80d)
      F1+F2 plus fprintf trace lines prefixed "VCLDEMO-DIAG" in Init/Main.
      Positive control: the strings are present in vcldemo.wasm.
      Three runs, all identical:
        bootstrap ok
        Main reached
        DemoWin constructed
        Show()
        DemoWin::Paint(0,0,1164,669)
        visible=1, size 1165x670
        "before Execute"
        then nothing; canvas blank
      Correction to the first part of this README: F1 and F12 did create and paint the window.
        The "QObject::connect(QWindow, QtSvpSalFrame)" line is printed by QtFrame::Show().
        Without the trace lines no Paint line appeared at all (F12 run).
        Inference, not tested: the first paint is an idle task, and the trace lines (synchronous stderr writes from the pthread) let it run inside Show().
  2 CLICK1, same build, diag/probe_click.js (a separate script, not probe.js): load, 15 s, screenshot, click (300,200), screenshot, Escape, screenshot.
      The click aborts the program:
        Aborted(Assertion failed: false && "emscripten_proxy_async failed", at: .../html5/callback.c,40,_emscripten_run_callback_on_thread)
      The page then shows Qt's "Application exit" text.
      In emsdk's proxying code this fails when the target thread's mailbox is closed, or when an allocation fails.
  3 DIAG4 (8bb65ea8ffae): a trace line in DemoWin::dispose().
      Output: "VCLDEMO-DIAG before Execute", then "VCLDEMO-DIAG DemoWin::dispose" in the same 0.1 s.
      H1 (the unwind disposes the window) holds.
      svmain.cxx has no catch(...), so the unwind goes through every frame up to the top.
  4 CLICK2, F1+F2+F3 (c61485e81baf): grid painted; the click zooms on the text tile with a new Paint line; Escape returns to the grid. No dispose, no abort.
  5 CLICK3, F1+F3 with F2 removed (8fdf8afffafb): same as CLICK2. The window appears at 0.9 s, against 2.3 s with F2. So F2 is not needed.
  6 FINAL, clean branch finding002-vcldemo-fix (1c96c7bfd8af = F1 + F3, no trace lines; 0 "VCLDEMO-DIAG" in vcldemo.wasm).
      Relink log: relink-FINAL.log.gz.
      Outputs:
        vcldemo.js 297,061 B (sha256 53c5e826cfdff671...)
        vcldemo.wasm 149,667,185 B (8dd59df9044afcbd...)
        no _emscripten_proxy_main
      FINAL-qt_vcldemo.* (probe.js unchanged, 90 s):
        soffice.data.js.metadata and soffice.data requested at 0.5 s
        no Bootstrap exception
        DemoWin::Paint(0,0,1164,669) at 1.0 s
        screenshot 146,266 B showing the demo grid
      FINAL-click*: Paint after the click (zoomed text tile) and after Escape (grid again), no error.

Criteria (PREDICTIONS.txt) for the final patch
  1 met (network)
  2 met (no Bootstrap exception; DemoWin::Paint with w,h > 0)
  3 met (screenshot shows the grid, 146,266 B against 4,254 B blank)
  4 met (C0 red, C1 green, same tree, same probe; recorded above)
  5 pending: the owner's own browser. emrun was left serving the final build at http://127.0.0.1:6970/qt_vcldemo.html (wasm-lite/upstream-master/emrun-owner.pid).

Not established
  Whether the --widgets, --popup, --font and --threads modes work. The patch also leaks the widget and popup windows, but only the default mode was run.
    --threads may need -sPTHREAD_POOL_SIZE in main-thread mode (static/README.wasm.md); not tried.
  Whether vcldemo worked before cf0b0f0dd04f: still not built.
