# Smoke runs before the counted run (2026-10-20; not counted)

These runs made the harness work. None of them counts toward ruling 1 §2.6.

**Smoke 1** (`d2`, all three modes):
- seq and q ran end to end. The q mode reordered: `.uno:Delete` ran before the queued Left, at the end of the document.
- **unipoll crashed (SIGSEGV)** in `vcl::Window::ImplUpdateGlobalSettings` under `WorkWindow::WorkWindow` ← `framework::TaskCreator::createTask` ← `lo_documentLoadWithOptions` ← the harness's poll callback ← `SvpSalInstance::ImplYield` ← `Application::Execute` (gdb, frames copied from the session's output).
- The cause was read in source.
  - `lo_runLoop` → `soffice_main` → `ImplSVMain` returns at once, because VCL is already initialised (`vcl/source/app/svmain.cxx:196-197`, since upstream `caa4036188ed`, 2026-02-27).
  - Natively, `soffice_main`'s `desktop::Desktop aDesktop` lives on the stack (`desktop/source/app/sofficemain.cxx:94`). Its destructor `~Application` runs `ImplDeInitSVData()` and clears `mpApp` (`vcl/source/app/svapp.cxx:165-168`).
  - On Emscripten without JSPI the Desktop is deliberately leaked instead (`sofficemain.cxx:78-92`).
- The harness therefore does `lo_runLoop`'s three registrations itself, without `soffice_main`.

**Smoke 2** (`d2` unipoll):
- SIGSEGV in `SfxApplication::GetFilterMatcher()` ← `SfxFrameLoader_Impl::load` ← `lo_documentLoadWithOptions`. No SfxApplication exists, because `Desktop::Main` never ran.
- The harness therefore calls `SfxApplication::GetOrCreate()`, the line iOS's LOK init adds (`desktop/source/lib/init.cxx:8294`).

**Smoke 3** (`d2` unipoll): runs end to end. `.uno:Delete` deleted `d` 0.5 ms after the queued Left was posted, the same as seq.

**Smoke 4** (every arm, every mode, one round; this directory):
- Reader: `VERDICT C-HOLDS` (`reader-output.txt`).
- Self-test: 5/5, the four red cases of ruling §2.6 plus the control (`self-test.txt`).
- **d7i's placement was wrong in the first version, and was corrected before any counted run.**
  - The first version put the caret at the end of P2, in front of P3's label. Writer's Delete there merged the paragraphs (`Delete paragraph`).
  - Review 6's position (i) is GoToStartOfDoc, then an unshifted Left, which puts the caret in front of P1's label: x 2138 → 1778 (`findings/evidence/link-batch/review/review-6-engine-code.md:23`).
  - Re-run with that placement, d7i reads `Number On/Off`, as review 6 did, with cursor callbacks `1778` then `2138`. The files here are that re-run, and `run-log.jsonl` keeps both runs.
- The first version of d7i ran on review 6's own `bullet.fodt` as well, with the same `Delete paragraph`. That ruled out the fixture before the placement was found.

**Recorded, not fixed:** the native unipoll harness's initialisation is not the product's.
- WASM: `runLoop` with a leaked Desktop.
- Here: no `soffice_main`, InitVCL's bare Application, and `SfxApplication::GetOrCreate()`.
- Neither path runs `Desktop::Main`. Collabora's co-26.04 core still runs `mpApp->Main()` from `ImplSVMain` when VCL is initialised (`cool-26-04/engine/vcl/source/app/svmain.cxx`).
- What the arms measure is the dispatch topology: inline posted events, synchronous accelerators, synchronous `postUnoCommand`. That topology does not depend on which Application object is installed (by source; not measured).
