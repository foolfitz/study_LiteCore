# Finding 156 evidence: LOK unipoll's runLoop returns at once on core 671c848b

- `runloop_returns.cpp`: the minimal native client. Build: `g++ -std=c++17 -O2 -Wall -I libreoffice-26-8/include runloop_returns.cpp -ldl -o runloop-returns`.
- `runloop-returns-output.txt`: four runs against `native-lok-26-8/build/instdir/program` (built from a clean upstream tree at 671c848b, `env-native-src.txt`), each with `SAL_USE_VCLPLUGIN=svp` and a fresh profile.
  - With `SAL_LOK_OPTIONS=unipoll`, runLoop returned after 0.027 ms and 0.020 ms, with 0 polls both times.
  - With `load`, the following documentLoad crashed: exit 139, SIGSEGV.
  - The threaded runs are recorded but are not a control: runLoop is the unipoll API.
  - Run on 2026-10-20 after the ordered-commands counted run had finished, so the two did not overlap.
- `harness-smoke-1/`: the first observation, the ordered-commands harness's smoke 1. Its init record shows `runLoopReturnedMs` 0.018 with 0 polls. The stderr is kept, with the i18nlangtag lines removed.
- `env-native-src.txt`, `env-libreoffice-26-8.txt`: `findings/env-snapshot.sh` for the tree the native install was built from (clean) and for the tree the headers came from (5 local modifications in build files, none in vcl/ or desktop/source/).
- Source, at 671c848b: `vcl/source/app/svmain.cxx:196-197` (the early return since `caa4036188ed`), `desktop/source/lib/init.cxx:7722-7743` (`lo_runLoop`) and `:8378-8387` (unipoll `InitVCL`), `desktop/source/app/sofficemain.cxx:78-94` (the stack Desktop natively, the leaked one on Emscripten), `vcl/source/app/svapp.cxx:165-168` (`~Application`). For comparison, Collabora co-26.04: `cool-26-04/engine/vcl/source/app/svmain.cxx` still runs `mpApp->Main()` when VCL is initialised.
- origin/master at `016fd5d04925` (2026-10-11) still has the early return. Its last change to `svmain.cxx` is `caa4036188ed`.
- Not measured: the positive side. No native build before `caa4036188ed` was available to show runLoop blocking.
