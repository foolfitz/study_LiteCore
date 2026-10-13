# TASK 2026-10-13g — W6: `check_core_build_provides.py` gains a `calc` capability

ODS plan `handoff/PLAN-2026-09-03-ods-reading.md` §6, work item W6: "`tools/check_core_build_provides.py`
gains a `calc` capability; self-test: the writer-only build must fail it". Touches no product bytes,
needs no link, disturbs no gate.

## Why the tool exists (read its docstring first)

`wasm_sdk_probe/tools/check_core_build_provides.py` asks whether the CORE build we link against provides
what the product needs, by requiring EVERY independent switch that can remove a capability (finding 057:
the Make variable decides whether objects are compiled, a C++ macro decides whether callers are). Today it
knows one capability, `writer-lok-accessibility`.

## What to add

A capability for "this core can import and lay out an ODS spreadsheet" (name it `calc-spreadsheet`).

1. **Find its switches in the two WASM builds, by reading, not assuming.** In
   `libreoffice-26-8/configure.ac` (around line 4371) `--with-wasm-module=calc` clears
   `ENABLE_WASM_STRIP_CALC` (and `ENABLE_WASM_STRIP_ACCESSIBILITY`). Find every place that switch (or
   anything else) decides whether Calc is present in a linked WASM engine:
   - the Make variable as the build recorded it (`config_host.mk` in each build dir);
   - any C++ macro in `config_host/*.h` that gates Calc callers (there may be none — say so if so);
   - compiled objects that ARE the capability: at minimum the document shell
     (`sc/source/ui/docshell/docsh.o`) and the ODS import (`sc/source/filter/xml/xmlimprt.o`), exact
     paths taken from the builds' `workdir/CxxObject/` trees;
   - whatever makes the type detection / filter for ODS available at runtime in a static WASM build
     (filter/type registration in the build's registry data, e.g. a `calc` `.xcd` in `instdir/share/registry/`,
     and whether the static link lists the Calc libraries). Include what you can show differs between the
     two WASM builds; record what you looked at and found identical.
2. Generalise `Capability` only as far as needed (e.g. a Make-variable switch next to the header macro).
   Keep the existing a11y capability's behaviour and output byte-for-byte the same for every build.
3. Add `--capability NAME` (repeatable) to restrict which capabilities are judged. With no flag the tool
   judges all of them, as today. **Do not edit `tools/probe_a11y_gate0.py`**: it calls the tool with
   `--build` only and reads the exit code as "provides accessibility". Show in the README that for every
   existing build its exit code is unchanged (`build-a11y-gate0` provides both, `build-headless-probe`
   provides neither, `build-native-26-8` provides both), and name the latent hazard in one sentence (a
   future writer-only a11y build would exit 1 for calc's sake) instead of fixing it.
4. **Do not repoint `PRODUCT_CORE_BUILD`.** That obligation belongs to the cutover (ODS plan §6 traps).

## Self-test (AGENTS.md §6: make it red before trusting green)

`--self-test` must additionally check, by capability NAME (not by list index):
- `wasm-lite/build-headless-probe` (writer-only, the product's core) is reported NOT providing
  `calc-spreadsheet`, and names what is missing;
- `wasm-lite/build-a11y-gate0` (writer+calc) IS reported providing it — the positive control on the SAME
  platform; without it a typo in an object path would look identical to "writer-only";
- `build-native-26-8` IS reported providing it;
- each independent switch is consulted: show, for each switch you list, that relaxing it alone does not
  turn the writer-only verdict green (the existing a11y self-test does the same for its two switches).

Red cases to exhibit and record in the README (run them, paste the tail of the output; do not commit
mutated code): (a) swap the writer-only and writer+calc build paths in the self-test → it goes red;
(b) misspell one object path → the positive control goes red; (c) point `--build` at a non-existent
directory → `ok: false` with every item missing, not a crash and not green.

## Deliverables

- The tool change in `wasm_sdk_probe/tools/check_core_build_provides.py` (keep the file's comment style:
  say WHY each switch is listed).
- `findings/evidence/m4-ods/W6-calc-capability/README.md` (English), starting `## SUMMARY` (≤ 30 lines):
  the switches found and how each differs between the two WASM builds, the self-test output (N/N), the
  three red cases, the exit codes per build before/after the change, the latent hazard sentence.
  Also save `--output` JSON reports for the three builds next to it.
- Commit only those paths (`git add … && git commit -m "…" -- <paths>`; if `.git/index.lock` exists,
  wait and retry — other agents commit in parallel). English commit message ending with
  `Co-Authored-By: Claude Sonnet <noreply@anthropic.com>`; no `Claude-Session:` line.

Do not touch anything else (no Makefile, no profiles, no `dist/`, no `PLAN-*.md`; the main session
appends to the plan after reading your README).
