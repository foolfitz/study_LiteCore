Finding 186 -- two full WASM builds of upstream master ac53621f754f, 2026-11-18 (owner asked for them; agent ran them)

Why
  The configure-only comparison (../README.txt) showed that the fix a maintainer suggested (arm M: test_gtk3=no,
  test_gtk4=no) leaves USING_UNIX_DESKTOP=TRUE, while the committed fix (arm R) clears it. That says the two
  configurations differ; it does not say what a build of M does. These builds answer that.

Arms
  M  src-186-M, branch finding186-fixM-test-only, 099c40da1a99 (TEST ONLY, never to be pushed)  configure.ac 1f6ff193...
  R  src-186-R, detached at 4847e69dd326                                                         configure.ac ba1268b7...
     The commit prepared for Gerrit was amended afterwards (message only) to 0b1e99d3be44; both have tree 83ca8bd08bae.
  PRE (reference, not built today): build-nosym, the stock build of 2a2335cf0911 from 2026-11-11, before the regression.
  Same machine, same environment (emsdk 4.0.10, Qt 5.15.2), same flags, a fresh build directory each
  (build-186-M, build-186-R), one after the other. build_186_arm.sh is the driver; *.receipt.txt and *.log.gz its output.

Predictions: PREDICTIONS.txt, written after M was started and before any output was read.

Results
  Build        M: make exit 0, 2794 s.   R: make exit 0, 2813 s.   Neither hit finding 003.          (P1 held, P2 held)
  Start        qt_soffice.html, unchanged probe.js, 90 s: both reach the Start Center, no page error. The screenshots of
               M, R and the 2026-11-11 control (findings/evidence/002/fix-2a2335cf/C1-qt_soffice.png) are byte-identical
               (sha256 5e78187201ef2658...). probe/.                                                 (P4 held for R)
  Products     compare-products.txt, cmp/.                                                           (P3 held)
    soffice.wasm   M 157,427,819 B   R 157,427,267 B   M - R = 552 B
    soffice.data   M  86,756,016 B   R  86,738,178 B   M - R = 17,838 B, all of it main.xcd
    image files    1598 in both, the same names; only /instdir/share/registry/main.xcd differs
    instdir        8 files only in M: program/sbase scalc sdraw simpress smath swriter, share/psprint/psprint.conf,
                   share/psprint/driver/SGENPRT.PS. None only in R. These 8 are not in the file system image.
    main.xcd       686 formatted lines only in M, none only in R (cmp/main.xcd.M-vs-R.diff.gz):
                   org.openoffice.Inet (six proxy settings), org.openoffice.UserProfile (givenname, sn),
                   org.openoffice.Office.Paths (Template, Work, Temp), org.openoffice.Office.Common (ExternalMailer,
                   SourceViewFont, View/Dialog/MiddleMouseButton=2, Help/System=UNIX), an empty org.openoffice.VCL, and
                   org.openoffice.Office.Accelerators with 106 Command properties, 88 of them with an en-US value (the unxwnt set: .uno:FullScreen,
                   .uno:DesignerDialog, .uno:RepeatSearch, .uno:ResetAttributes, .uno:SpellingAndGrammarDialog,
                   .uno:SearchDialog, the Calc number formats, paragraph navigation ...).
                   13 of the values are oor:external="com.sun.star.configuration.backend.DesktopBackend ...".
                   None of the keys overlaps with static/config/wasm-accelerators.xcu.
    objects        vcl/unx/generic/desktopdetect/desktopdetector.o exists in M only.
  Behaviour    keys/, probe_keys.js via run_keys_probe.sh: open a Writer document from the Start Center, type "abc",
               press F11, press Ctrl+H; a screenshot after each step.
                 step                 PRE              R                M
                 Start Center         5e78...          5e78...          5e78...   (all three identical)
                 Writer opened        6360...          3722...          3722...   (R and M identical)
                 typed abc            7b28...          af57...          af57...   (R and M identical; text visible)
                 after F11            = typed abc      = typed abc      2f4d...   Styles deck open in the sidebar
                 after Ctrl+H         = typed abc      = typed abc      = after F11
               So F11 does nothing in PRE and in R and opens the Styles deck in M. Typing is the positive control
               that keys reach the application in every arm.
               PRE's Writer screenshots differ from R's because of the 255 commits in between; that was not looked into.
               Ctrl+H changed nothing in any arm. In M it was pressed after F11 had opened the sidebar; whether it
               would open Find & Replace when pressed first was not tested.

What this shows and does not show
  Shown: both fixes give a WASM build that completes, starts, opens Writer and takes typing. M is not broken in the
  default configuration. M differs from R, and from the build before the regression, in the registry content it ships
  and in at least one user-visible behaviour (F11).
  Not shown: anything about configurations other than the default module set (for example with Impress, where
  slideshow is built and ENABLE_OPENGL_TRANSITIONS=TRUE adds OGLTrans); what the 13 DesktopBackend values resolve to at
  run time; whether any of the other bindings acts; unit tests (not part of a cross build).
  One run per arm for each probe.

Tool fix during the run
  compare_builds.sh first sorted file lists in the session locale and comm complained; changed to LC_ALL=C and re-run.
  The counts did not change (8 / 0).

Left on disk (not in git): wasm-lite/upstream-master/build-186-M, build-186-R (6.1 GB each), src-186-M, src-186-R
(1.5 GB each, git worktrees), and the local branch finding186-fixM-test-only.
