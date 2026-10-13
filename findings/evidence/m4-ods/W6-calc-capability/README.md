## SUMMARY

W6 (ODS plan `handoff/PLAN-2026-09-03-ods-reading.md` section 6): `wasm_sdk_probe/tools/check_core_build_provides.py` now judges a second capability, `calc-spreadsheet`, next to `writer-lok-accessibility`. Touches no product bytes, no link, no profile; `PRODUCT_CORE_BUILD` is NOT repointed.

- **Switches (all read from the trees, not assumed).** Calc has exactly ONE configure input (`--with-wasm-module=...calc` clears `ENABLE_WASM_STRIP_CALC`, `configure.ac:4382`) and NO C++ macro (the name is `AC_SUBST`ed only, `configure.ac:4414`; `sc/` contains no `ENABLE_WASM_STRIP_*`; of all `config_host/*.h`, only `config_wasm_strip.h` differs between the two WASM builds and only in `ENABLE_WASM_STRIP_ACCESSIBILITY`). The tool therefore judges four switches: `makeVariable`, `objects`, `libraries`, `registration`.
- **How they differ, writer-only (`build-headless-probe`) vs writer+calc (`build-a11y-gate0`):** `config_host.mk:259` `TRUE` vs empty; `.o` under `CxxObject/{sc,scaddins,sccomp}` 0 vs 894/7/2 (all five listed objects present only in the latter); `libsclo.a` absent vs 49,016,254 bytes and `-lsclo` absent vs present in `soffice.js.linkdeps`; `Calc.SpreadsheetDocument` / `Calc.XMLOasisImporter` unregistered in `services.rdb` and unmapped in `component_maps.cxx` vs registered under `libsclo.a` and mapped. All four are red on the writer-only build and green on the writer+calc and native builds.
- **Identical in the two WASM builds (so NOT switches):** `share/registry/{calc,main,static,writer}.xcd` (`cmp`), every `config_host/*.h` except `config_wasm_strip.h`, `config_host.mk` except the two `ENABLE_WASM_STRIP_*` lines and `PATH`.
- **Self-test: 22/22** (was 5/5). The five accessibility lines are unchanged in meaning and now select their capability by name. Calc lines: writer-only NOT providing and names what is missing; writer+calc and native providing (positive controls); switch set is exactly the four; every switch red on writer-only and green on both controls; relaxing any ONE switch leaves the writer-only verdict red (x4); relaxing all the OTHER switches leaves each one alone enough to keep it red (x4, this is what shows every switch is wired into the verdict); `--capability` narrows and no flag judges all; a non-existent directory provides nothing.
- **Red cases (each run, tails below; mutated code not committed):** (a) swap writer-only/writer+calc paths in the self-test: 9/22, exit 1, 13 FAIL lines. (b) misspell `xmlimprt.o`: 19/22, exit 1, both positive controls go red while the writer-only line stays "not providing" (the look-alike case). (c) `--build /nonexistent/core-build`: `ok: false`, all 5 objects missing, `makeVariableValue: null`, every library/registration item missing, exit 1, no crash. Extra: (d)/(e) making the verdict ignore `registration` / `makeVariable` each turns exactly one line red (the all-others-relaxed line), which is why those four extra lines exist.
- **Exit codes, before -> after (no flag):** `build-headless-probe` 1 -> 1, `build-a11y-gate0` 0 -> 0, `build-native-26-8` 0 -> 0. With `--capability writer-lok-accessibility` the output file is byte-identical (`cmp`) to the pre-change output for all three builds. `tools/probe_a11y_gate0.py` (not edited) reads the same 0/1/0.
- **Latent hazard (named, not fixed):** `probe_a11y_gate0.py:build_provides_accessibility()` calls the tool with `--build` only and reads exit 0 as "provides accessibility", so a future core that has accessibility but not Calc (inferred from `configure.ac:4388`, not built: `--with-wasm-module=writer impress` clears `ENABLE_WASM_STRIP_ACCESSIBILITY` and leaves `ENABLE_WASM_STRIP_CALC` set) would exit 1 for calc's sake and be read as "no accessibility"; the one-argument fix is `--capability writer-lok-accessibility` at that call site.
- Commit: see the git log entry "W6: check_core_build_provides gains calc-spreadsheet capability".

## What the tool now judges

`calc-spreadsheet` asks whether the objects that ARE "open and lay out an ODS" exist, are linked and are registered. It does not claim an ODS was opened (that is W2/W5/W7 territory).

| switch | what is read | why it is a separate switch |
|---|---|---|
| `makeVariable` | `config_host.mk`: `export ENABLE_WASM_STRIP_CALC=` must be empty (`None`, i.e. no such line, is NOT accepted) | The configure input. Gates modules `sc`, `scaddins`, `sccomp`, `basctl` (`RepositoryModule_host.mk:57,134`), `Library_wpftcalc` (`writerperfect/Module_writerperfect.mk:27`), and the scalc UI files in the FS image (`static/CustomTarget_emscripten_fs_image.mk:1143`). |
| `objects` | `workdir/CxxObject/sc/source/{ui/docshell/docsh, filter/xml/xmlimprt, core/data/document, ui/unoobj/docuno, ui/view/gridwin4}.o` | What the Make variable produces. A tree can be configured for Calc and not (fully) built. Each of the five is a member of `libsclo.a` (`llvm-ar t`, measured), named for its job: `ScDocShell`, `ScXMLImport` (ODS content.xml), `ScDocument`, `ScModelObj` (LOK `getParts`/`getPartName`/`setPart`), `ScGridWindow::PaintTile`. |
| `libraries` | static (`DISABLE_DYNLOADING=TRUE`): `instdir/program/libsclo.a` exists AND `soffice.js.linkdeps` lists the token `-lsclo`; dynamic: `libsclo.so` exists | Objects compiled is not objects linked. An unreadable build is judged by the static rules (fail closed). |
| `registration` | `services.rdb`: `com.sun.star.comp.Calc.SpreadsheetDocument` and `...Calc.XMLOasisImporter` registered with the expected constructor under `libsclo.{a,so}`; static builds also need the mapping line (not just the declaration) in `workdir/CustomTarget/static/component_maps.cxx` | Without the constructor map a static build has no dlopen to find the code. The implementations are named in full: the writer-only `services.rdb` DOES register five `com.sun.star.comp.Calc.*` names (xmloff's `XMLCalc*ImportOOO`), so a search for the word "Calc" would be fooled. |

The accessibility capability keeps its own two switches (`objects`, `macro`) and its report entry keeps the same keys in the same order. Calc declares `macro=None`: nothing on the caller side exists to consult, and none was invented.

### Measured, by build

| | writer-only `build-headless-probe` | writer+calc `build-a11y-gate0` | native `build-native-26-8` |
|---|---|---|---|
| `--with-wasm-module` (`autogen.input`) | `writer` | `writer calc` | (native) |
| `ENABLE_WASM_STRIP_CALC` | `TRUE` | empty | empty |
| `ENABLE_WASM_STRIP_ACCESSIBILITY` | `TRUE` | empty | empty |
| `DISABLE_DYNLOADING` | `TRUE` | `TRUE` | empty |
| `.o` under `CxxObject/sc` / `scaddins` / `sccomp` | 0 / 0 / 0 | 894 / 7 / 2 | 968 / 7 / 4 |
| `libsclo` | none | `libsclo.a`, listed `-lsclo` | `libsclo.so` |
| `services.rdb` components | 91 | 100 | 172 |
| `Calc.SpreadsheetDocument`, `Calc.XMLOasisImporter` in `services.rdb` | absent | `libsclo.a` | `libsclo.so` |
| `soffice.wasm`: occurrences of the string `ScDocShell` (`grep -a -o -F`) | 0 | 18 | n/a |

Also differ between the two WASM builds, but are NOT required by the tool because nothing measured says ODS import/layout needs them: `-lscfiltlo -lscuilo -lscdlo -lwpftcalclo -lanalysislo -ldatelo -lforuilo -lpricinglo -lsolverlo` in `soffice.js.linkdeps`; nine Calc `.component` files in `services_componentfiles.list` (sc, scd, scfilt, scui, analysis, date, pricing, solver, wpftcalc); `instdir/share/config/soffice.cfg/modules/scalc/` (only in writer+calc; same Make variable, FS-image UI files).

Looked at and found IDENTICAL in the two WASM builds: `share/registry/calc.xcd` (174,069 bytes, defines the `calc8` type and filter), `main.xcd`, `static.xcd`, `writer.xcd` (all `cmp`-identical); every `config_host/*.h` except `config_wasm_strip.h` (same file list, same contents after path normalisation); `config_host.mk` except `ENABLE_WASM_STRIP_ACCESSIBILITY`, `ENABLE_WASM_STRIP_CALC` and `PATH`; `config_options_calc.h` (holds `ENABLE_FORMULA_LOGGER 0` only, unrelated). The type registration being present in the writer-only build is the plan's limit 2 ("presence of the type registration says nothing about whether the module is linked"); it is deliberately not a switch.

Inferred, not measured: that a future writer-only build with accessibility is configurable as `writer impress` (read from `configure.ac:4380-4392`); that after the cutover repoint of `PRODUCT_CORE_BUILD` the self-test's accessibility negative control (which still uses that constant, unchanged by design) will need its own dedicated writer-only path the way the calc controls already have (`WRITER_ONLY_CORE_BUILD`, `WRITER_CALC_CORE_BUILD`).

## Self-test (`self-test.txt`)

```
  ok    the product's core build is reported as NOT providing a11y
  ok    ...and names the compiled-out objects
  ok    ...and names the macro that removes the callers
  ok    a real core build that provides a11y is reported as providing it
  ok    the two switches are checked independently
  ok    calc: the writer-only core build is reported as NOT providing it
  ok    ...and names what is missing: objects, Make variable, library, registration
  ok    calc: the writer+calc WASM build is reported as providing it
  ok    calc: the native build is reported as providing it
  ok    calc: the capability consults exactly the intended switches
  ok    calc: every switch is red on the writer-only build
  ok    calc: ...and green on both controls
  ok    calc: relaxing libraries alone does not turn the writer-only verdict green
  ok    calc: relaxing makeVariable alone does not turn the writer-only verdict green
  ok    calc: relaxing objects alone does not turn the writer-only verdict green
  ok    calc: relaxing registration alone does not turn the writer-only verdict green
  ok    calc: with every other switch relaxed, libraries alone keeps it red
  ok    calc: with every other switch relaxed, makeVariable alone keeps it red
  ok    calc: with every other switch relaxed, objects alone keeps it red
  ok    calc: with every other switch relaxed, registration alone keeps it red
  ok    --capability judges only the named capability, and no flag judges all
  ok    a build directory that does not exist provides nothing, for every capability, with every item missing

self-test: 22/22 checks moved the verdict
```

Before this change the same command printed `self-test: 5/5 checks moved the verdict`. The calc lines look the writer-only verdict up by capability NAME (`by_name`), never by list index; the switch set is written out in the self-test (`CALC_SWITCHES`) so deleting a switch from the capability turns a line red instead of silently shrinking the check.

## Red cases (AGENTS.md section 6)

The mutants are copies in a scratch directory with `WORKSPACE` pinned to the repo root (a copy outside the tree cannot derive it from `__file__`); nothing mutated is committed. With `T=wasm_sdk_probe/tools/check_core_build_provides.py`, `R=$(pwd)`, `pin() { sed "s#^WORKSPACE = .*#WORKSPACE = Path('$R')#"; }`:

```
(a) pin < $T | sed -e '/^WRITER_ONLY_CORE_BUILD/s/build-headless-probe/build-a11y-gate0/' \
                   -e '/^WRITER_CALC_CORE_BUILD/s/build-a11y-gate0/build-headless-probe/'
(b) pin < $T | sed -e 's#sc/source/filter/xml/xmlimprt\.o#sc/source/filter/xml/xmlimprt_typo.o#'
(d) pin < $T | sed -e 's#for name, ok in switches.items())#for name, ok in switches.items() if name != "registration")#'
(e) pin < $T | sed -e 's#for name, ok in switches.items())#for name, ok in switches.items() if name != "makeVariable")#'
```

Each was run with `--self-test`; full output in `redcase-*.txt`. The FAIL lines below are abbreviated by hand (payloads shortened with `...`, groups of four condensed); the files keep them whole:

**(a) swapped controls: 9/22, exit 1** (`redcase-a-swapped-controls.txt`)

```
  FAIL  calc: the writer-only core build is reported as NOT providing it  -- the writer-only build came back ok, so the check is blind
  FAIL  ...and names what is missing: ...  -- {"missingObjects": [], "makeVariableValue": "", "missingLibraries": [], "missingRegistrations": []}
  FAIL  calc: the writer+calc WASM build is reported as providing it  -- [{"capability": "calc-spreadsheet", "objectsCompiled": false, "missingObjects": [...docsh.o ...
  FAIL  calc: every switch is red on the writer-only build  -- {"objects": true, "makeVariable": true, "libraries": true, "registration": true}
  FAIL  calc: ...and green on both controls  -- [{"objects": false, "makeVariable": false, "libraries": false, "registration": false}, {"objects": true, ...}]
  FAIL  calc: relaxing {libraries,makeVariable,objects,registration} alone does not turn the writer-only verdict green     (4 lines)
  FAIL  calc: with every other switch relaxed, {libraries,makeVariable,objects,registration} alone keeps it red            (4 lines)

self-test: 9/22 checks moved the verdict
```

**(b) misspelled object path: 19/22, exit 1** (`redcase-b-misspelled-object.txt`). The writer-only line stays `ok` (a typo and a missing module look identical from the negative side); the positive controls are what catch it:

```
  FAIL  calc: the writer+calc WASM build is reported as providing it  -- [{"capability": "calc-spreadsheet", "objectsCompiled": false, "missingObjects": ["workdir/CxxObject/sc/source/filter/xml/xmlimprt_typo.o"], ...
  FAIL  calc: the native build is reported as providing it  -- [{"capability": "calc-spreadsheet", "objectsCompiled": false, "missingObjects": ["workdir/CxxObject/sc/source/filter/xml/xmlimprt_typo.o"], ...
  FAIL  calc: ...and green on both controls  -- [{"objects": false, "makeVariable": true, "libraries": true, "registration": true}, {"objects": false, "makeVariable": true, "libraries": true, "registration": true}]

self-test: 19/22 checks moved the verdict
```

**(c) non-existent directory, CLI** (`redcase-c-nonexistent-directory.json`; `--build /nonexistent/core-build --capability calc-spreadsheet`): exit 1, `"ok": false`, no traceback. Tail of the entry:

```
"objectsCompiled": false,  "missingObjects": [ all five ],
"makeVariable": "ENABLE_WASM_STRIP_CALC",  "makeVariableValue": null,  "makeVariableAllows": false,
"disableDynloading": null,
"librariesLinked": false,  "missingLibraries": ["instdir/program/libsclo.a: not built", "instdir/program/soffice.js.linkdeps: missing, so -lsclo is not shown linked"],
"registered": false,  "missingRegistrations": [ 4 items: 2 x services.rdb, 2 x component_maps.cxx ],
"provided": false     ->     "notProvidedByCoreBuild": ["calc-spreadsheet"], "ok": false
```

Without `--capability` the same directory reports both capabilities not provided, exit 1. An unknown `--capability bogus` is an argparse error, exit 2.

**(d), (e) extra: the verdict ignores one switch** (`redcase-d-...txt`, `redcase-e-...txt`): 21/22 each, exactly one line red, `calc: with every other switch relaxed, registration alone keeps it red` and the `makeVariable` equivalent respectively. The 4 "relaxing one alone" lines stay green in both, which is why they cannot stand alone: they only show the OTHER switches are red.

## Exit codes and the accessibility entry (`exit-codes.txt`)

| build | before | after, no flag | after, `--capability writer-lok-accessibility` | after, `--capability calc-spreadsheet` |
|---|---|---|---|---|
| `wasm-lite/build-headless-probe` | 1 | 1 | 1 | 1 |
| `wasm-lite/build-a11y-gate0` | 0 | 0 | 0 | 0 |
| `build-native-26-8` | 0 | 0 | 0 | 0 |
| no `--build` (product core) | 1 | 1 | | |

With `--capability writer-lok-accessibility` the `--output` file is `cmp`-identical to the pre-change file for all three builds (`before-*.json` are those pre-change files, made by running the committed tool in place before editing). With no flag the report gains a second entry; the accessibility entry inside it is equal to the old one, key order included. `probe_a11y_gate0.py --check-build-only --core-build X` (file untouched) reports `exitCode`/`provides` 0/True, 1/False, 0/True for the gate0, headless-probe and native builds.

## Files here

- `README.md` (this file), `self-test.txt`, `exit-codes.txt`
- `report-build-headless-probe.json`, `report-build-a11y-gate0.json`, `report-build-native-26-8.json`: `--output` of the tool, no flag, run from the repo root with the repo-relative `--build` path
- `before-*.json`: the same three builds judged by the tool before this change
- `redcase-a-swapped-controls.txt`, `redcase-b-misspelled-object.txt`, `redcase-c-nonexistent-directory.json`, `redcase-d-verdict-ignores-registration.txt`, `redcase-e-verdict-ignores-makevariable.txt`
