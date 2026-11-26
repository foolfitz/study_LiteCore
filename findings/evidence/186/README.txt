Finding 186 -- master: configure of the documented WASM build fails ("VCLplugs to be built: gtk3 qt5")

Date of these runs: 2026-11-18. Only configure (autogen.sh) was run. Nothing was built.

Source
  wasm-lite/upstream-master/submit, upstream master ac53621f754f (2026-11-17), branch emscripten-configure-gtk.
  Each log records the commit, the dirty files and the sha256 of configure.ac it ran with.
  Unpatched configure.ac  3aa218a1c2f5e590f17853ed0c9ef111ee42f166a0b21ac196e7fa9a732ebd57
  Fix M configure.ac      1f6ff193a21d742c648f061f6c40f3972ad81ceb34895601446a9a7c6ac410f9
  Fix R configure.ac      ba1268b77ed2f116b741f2d3c8ce6e9cd324edd50eb81ec8ca15ac7550e1dbb5  (= commit 4847e69dd326, clean tree;
                          later amended, message only, to 0b1e99d3be44 and then b7f3bd7eb41c, all with the same tree 83ca8bd08bae)

Environment
  emsdk 4.0.10, Qt 5.15.2 for WASM (wasm-lite/tools/qt5-wasm), same as wasm-lite/upstream-master/build.sh.
  autogen.input for every arm: --with-distro=LibreOfficeWASM32 --disable-symbols --enable-ccache
  --with-build-platform-configure-options=--enable-ccache --with-parallelism=10, plus --disable-gui for the "nogui" arms.
  These are the flags of the 2026-11-11 failing run and of the pre-regression build used as reference.

Arms (arms/<name>.log is the complete autogen output)
  C1-unpatched-gui     exit 1   VCLplugs to be built: gtk3 qt5; "Can't build --disable-dynamic-loading without --disable-gui and a single VCL plugin"
  C4a-unpatched-nogui  exit 0   VCLplugs to be built: qt5
  M2-fixM-gui          exit 0   VCLplugs to be built: qt5
  M4-fixM-nogui        exit 0   VCLplugs to be built: qt5
  R2-fixR-gui          exit 0   VCLplugs to be built: qt5
  R4-fixR-nogui        exit 0   VCLplugs to be built: qt5

The two candidate fixes
  fix-M-test-gtk-only.patch            test_gtk3=no and test_gtk4=no in the emscripten platform block.
  fix-R-clear-using-unix-desktop.patch clear USING_UNIX_DESKTOP for Emscripten after the with_x block. This is what was committed.

Comparison against the configuration before the regression (cmp/, produced by compare.sh)
  Reference: wasm-lite/upstream-master/build-nosym, a stock LibreOfficeWASM32 build of 2a2335cf0911, which does not contain
  d98a796946ff (git rev-list --count 2a2335cf..d98a796946ff is 8). Build and source paths are replaced before diffing.

  pre-vs-fixR-gui    config_host.mk: DEFAULT_BRAND_IMAGES (commit 8bf7db1184dc, unrelated), a new empty USING_UNIX_DESKTOP,
                     PATH (same entries, different order: the shell's), SOURCE_DATE_EPOCH. Headers: 52 compared, 1 differs:
                     config_vclplug.h gains "#define USING_UNIX_DESKTOP 0".
  pre-vs-fixM-gui    the same, and in addition USING_UNIX_DESKTOP=TRUE, ENABLE_OPENGL_TRANSITIONS=TRUE, ENABLE_OPENGL_CANVAS=TRUE,
                     "#define HAVE_FEATURE_OPENGL 1", "#define USING_UNIX_DESKTOP 1". This arm is also the positive control
                     for the comparison: it shows that compare.sh reports a difference when there is one.
  nogui-unpatched-vs-fixR   with --disable-gui, fix R changes none of the 52 headers and, in config_host.mk, only
                     SOURCE_DATE_EPOCH, which is the committer date of HEAD (the fix R arms ran on the commit itself).
                     An earlier run with the change uncommitted on top of ac53621f754f gave an empty diff.

Full builds of both fixes were made later the same night: see build/README.txt. The two paragraphs below describe what
the configure-only runs showed on their own.

What this does and does not show
  Shown: master cannot configure the documented WASM build; with fix R the generated configuration equals the one from
  before the regression; fix M makes configure pass but leaves the Unix-desktop switches on.
  Not shown: that a WASM build of current master with fix R compiles, links and runs. No build was made. Other commits
  between 2a2335cf0911 and ac53621f754f could affect that independently of this fix.
  Not shown: what a build with fix M would do. That USING_UNIX_DESKTOP=TRUE turns on code that was never part of an
  Emscripten build is read from the makefiles (vcl/Library_vcl.mk, vcl/Module_vcl.mk, Repository.mk,
  desktop/Module_desktop.mk) and from configure.ac (OpenGL block), not observed in a build.

Earlier evidence of the same failure
  findings/evidence/002/fix-2a2335cf/e42678e7-configure-fail.log (2026-11-11, master e42678e7).

Parent versus the regressing commit (added 2026-11-18 15:41, after Chris Mayo asked on 211916 whether this is new)
  B1-d98a-parent-gui  8e543468540d (parent of d98a796946ff)  exit 0   VCLplugs to be built: qt5
  B2-d98a-gui         d98a796946ff                          exit 1   VCLplugs to be built: gtk3 qt5; the same error as C1
  Same flags and environment; source was a temporary detached worktree (src-186-bisect, removed afterwards),
  run through conf_arm.sh with LO_SRC set (that option was added to conf_arm.sh for these two arms).

Upstream state: see upstream-state-2026-11-18.txt.

Review
  review-codex-2026-11-18.txt: adversarial read-only review by Codex of the first version of the commit (5db4539e85e3).
  C1, C2, C4, C5 hold. C3 found two overstated sentences in the commit message: (1) not everything that d98a796946ff
  moved to USING_UNIX_DESKTOP was off in an Emscripten build before -- fontconfig packaging and the LibreOfficeKit
  objects in sofficeapp have other conditions that keep them on; (2) the "same as before apart from" sentence left out
  PATH order and SOURCE_DATE_EPOCH. Both were checked against the sources and corrected; the commit was amended to
  4847e69dd326 (message and the configure.ac comment only) and the fix R arms were re-run on it.
  Known limits of compare.sh, not fixed: a header that exists only on the right-hand side is counted but not diffed
  (both sides have 52 here and every left-hand header exists on the right, so there is none).

To re-run: conf_arm.sh <arm-dir> [--disable-gui], then compare.sh <arms-dir> <out-dir>. About 30 seconds per arm.
The arm directories themselves were in a session scratch directory and are not kept; the logs and the diffs are.

Variant A, for patch set 2 (added 2026-11-19 10:06, after Christian Lohmaier preferred disabling the plugins on 211916)
  fix-A-test-gtk-kf-off.patch: test_gtk3=no, test_gtk4=no, test_kf5=no, test_kf6=no in the emscripten platform block.
  configure.ac c64ccdc26e55e768108471e6ec009942f8c9d623d4f1944021195bca6056427c, on ac53621f754f, in a temporary worktree
  (src-186-A, removed afterwards). Committed as 399a9df475a7 on local branch emscripten-configure-gtk-ps2 (same Change-Id).
  A2-fixA-gui    exit 0   VCLplugs to be built: qt5
  A4-fixA-nogui  exit 0   VCLplugs to be built: qt5
  cmp/fixM-gui-vs-fixA-gui.*         config_host.mk and 52 headers identical to fix M (configure-only arm M2)
  cmp/build186M-vs-fixA-gui.*        identical to the configuration of the full build build-186-M, apart from SOURCE_DATE_EPOCH
  cmp/fixM-nogui-vs-fixA-nogui.*     identical
  cmp/nogui-unpatched-vs-fixA.*      identical: --disable-gui is unaffected
  cmp/fixR-gui-vs-fixA-gui.*         positive control: differs (USING_UNIX_DESKTOP, ENABLE_OPENGL_*, 2 headers)
  So the full build and the probes of arm M (build/README.txt) stand for variant A as well; A itself was not built.
  Pushed 2026-11-19 02:44 UTC as patch set 2 of Gerrit 214345 (revision 399a9df475a79d849816bc9c60e890372e5fad4f).
