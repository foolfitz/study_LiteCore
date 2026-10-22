# Fallback F: finding 159's bridge signatures in `build-a11y-gate0` (2026-10-22)

The owner chose A, the fallback (SPEC-M4-viewer-v2 §7.1), and ran `handoff/ods-viewer-v2/build-core-fallback-gate0.sh` at 09:15. Incremental, in v1's core tree; make re-ran autogen first (configure.ac changed since the tree was configured on 08-22).

| file | what |
| --- | --- |
| `timing.txt` | `make exit 0 after 3 min` (log `wasm-lite/build-a11y-gate0/build-fallback-20261022T091518.log`, kept in the build dir) |
| `bridge-before.sha256` | the three bridge outputs before the script deleted them. After the build: `exports` unchanged (`06900596…`), `generated-asm.s` and `generated-cxx.cxx` new (`d812ed15…`, `0bd5b371…`) |
| `config-before/` | `config_host.mk` and the 51 `config_host/*.h` before autogen re-ran |
| `config-after-autogen.txt` | 51 headers `same`; **`config_host.mk` DIFFERS** -- read below |
| `k2-gate0.json` | K-2a true (80 signatures, the four 159 needs present), K-2b true (equal to the offline set), K-2e true (the five link inputs), **K-2c false as required** (700 constructors, `OFormsCollection` absent, the three scaddins present), K-2f recorded: `soffice.wasm` 149,236,537 bytes (149,208,138 before, +28,399), `soffice.data` 108,527,803 (unchanged) |
| `build-fallback-compiled.txt` | every compile/generate/link line of the make, and the five sw sources' mtimes |

## `config_host.mk` differs: only the `export PATH=` line

`config-before/config_host.mk` against `wasm-lite/build-a11y-gate0/config_host.mk` differs in one line, line 558, `export PATH=`. The same directories in a different order: the owner's shell now has `~/.cargo/bin` and `~/.deno/bin` ahead of `~/.nvm/versions/node/v24.16.0/bin` (before: after it). The moved directories share no executable name (`~/.cargo/bin` + `~/.deno/bin`: cargo, cargo-*, clippy-driver, deno, rls, rust-*, rustc, rustdoc, rustfmt, rustup, xmlprocess; nvm's bin: ccs*, corepack, node, npm, npx, omx, playwright-mcp), so every lookup through that PATH finds the same file as before [observed]. Reading: no effect on the build. The §7.1 expectation "all 52 the same" did not hold to the letter; this is the one difference, and it was read before going on.

## Five sw objects were recompiled; their sources are HEAD

Besides the bridge, make recompiled `sw/source/core/layout/pagechg.cxx`, `sw/source/core/text/frmform.cxx`, `sw/source/core/text/porrst.cxx`, `sw/source/core/txtnode/fntcache.cxx` (mtime 2026-09-25 21:48) and `sw/source/filter/xml/xmltble.cxx` (2026-09-26 12:20), all newer than gate0's objects. In the `libreoffice-26-8` worktree all five have `git diff HEAD` empty and none is in `wasm-lite/patches/INVENTORY.md`. The 09-26 pair (`xmltble.cxx` and `sw/qa/extras/odfexport/odfexport4.cxx`, touched the same second) is exactly the source half of the `lo-submit` worktree's `tdf#173931` commit `3b0548b0`: a patch applied in this worktree and reverted. Reading: the objects were rebuilt from the same source text as v1's core [inferred: assumes the files were at HEAD when gate0 was built in August; the old objects are gone and cannot be compared]. `build-headless-probe`'s objects for these files (08-01) are older too, so its next make recompiles them as well.
