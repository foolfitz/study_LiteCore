# Runbook: the core rebuild for a11y gate 0

Written 2026-08-22. The operator's half of
[`handoff/a11y-gate-0/README.md`](a11y-gate-0/README.md) steps 3–5 — the only
part of gate 0 that is not mine. Read
[`a11y-gate-0/PREDICTION.md`](a11y-gate-0/PREDICTION.md) first; it fixes the
pass/fail criterion and it was written before any of this.

The gate asks **one** question: does LOK emit a focused paragraph on WASM?
This build is what makes that question askable. It is **not** a product build
and nothing shipped depends on it.

## What is already done (do not redo)

| | |
|---|---|
| `configure.ac` patched | applied to `libreoffice-26-8` — `git diff configure.ac` shows 12+/1- |
| patch snapshotted | `wasm-lite/patches/libreoffice-26.8-wasm-strip-accessibility-single-input.patch`, listed in `INVENTORY.md`, `git apply --check --reverse` passes for all six patches |
| v4 archived | `build/archive/e2-editor-v4-f923cfa5-worker-e6ee92ca-manifest-cbf93923/` is **byte-identical** to `dist/profiles/e2-editor-v4/` on all four files (verified, not assumed) |
| read-only protection | none is set anywhere under `wasm_sdk_probe/dist` or `build` — nothing to lift |
| build dir prepared | `wasm-lite/build-a11y-gate0/` with `autogen.input` and `env.sh` written |

## Two decisions this runbook makes, and why

**A new build directory, not a rebuild in place.** `build-headless-probe` is
the core the shipped v4 artifact was linked from. Rebuilding it in place would
destroy it, and a WASM build is not reproducible
(`wasm-build-not-reproducible`) — so any future product relink would land on a
core that carries calc and a11y, whether or not the gate passes. A separate
directory costs disk and buys the option to walk away from the result. It is
also not much slower: the config header changes either way, so an in-place
build would recompile nearly everything too.

**`--with-wasm-module='writer calc'`, exactly as `PATCH.md` prescribes.** Worth
knowing, because it changes the risk: **upstream's default is `'calc writer'`**
(`configure.ac:2326`). A build with the accessibility objects compiled in is
therefore the well-trodden upstream path, and *our* writer-only product build
is the deviation. `calc` here is the lever that clears the Make variable; the
patch is what makes clearing it also remove the C++ macro. Nothing else in
`autogen.input` changes — the delta against `build-headless-probe` is that one
line and only that line (checked with `diff`).

## Before you start

* **Disk**: `/` is at 95%, 49 GB free. This build needs roughly 6–9 GB
  (`build-headless-probe` is 5.5 GB and calc is not free). It fits, but do not
  start a second big thing alongside it.
* **Memory**: 30 GB RAM with 16.6 GB of swap already in use. The 2026-08-01
  precedent for this build was max RSS 5.9 GB at `-j12` with no swapping, so
  `-j12` is fine — but if the machine is loaded, `-j8` costs little.
* **Optional, helps**: ccache is full (5.0/5.0 GiB, 8691 cleanups, 24% lifetime
  hit rate). `ccache -M 15G` before the build lets it keep more of this
  configuration. Nothing depends on it; skip it if disk feels tight.

## The commands

### 1. Environment

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
source wasm-lite/build-a11y-gate0/env.sh
```

It prints three lines. All three must be right before you continue:

* `emcc: ... 4.0.10 ...` — if it says 3.1.69 you have the system emscripten,
  **stop**;
* `LITE_EXTRA_FONTS_DIR: ... (NotoSansCJK-Regular.ttc)` — non-empty, and the
  font is listed;
* `build dir: .../wasm-lite/build-a11y-gate0`.

### 2. Configure

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm-lite/build-a11y-gate0
/home/jiajun/LibreOffice/study_LiteCore/libreoffice-26-8/autogen.sh 2>&1 | tee configure.log
```

About 40 seconds.

### 3. **The falsifier — run this before `make`**

This is G0-1, and it is checkable in one second instead of one hour. If the
patch did not take, **everything downstream measures nothing**, and this is the
moment to find out.

```bash
cat config_host/config_wasm_strip.h
```

**Required**: `#define ENABLE_WASM_STRIP_ACCESSIBILITY 0`.

If it still says `1`, **stop and report** — do not start the build. For
context, the same file in the product's core build says `1`, and that is
correct there.

Second half of the same check, on the Make side:

```bash
grep -E '^export ENABLE_WASM_STRIP_(ACCESSIBILITY|CALC|WRITER)' config_host.mk
```

**Required**: `ACCESSIBILITY` and `CALC` empty, `WRITER` empty. (`TRUE` means
stripped; empty means built.)

### 4. Build

```bash
make -j12 2>&1 | tee build.log
```

Expect **roughly 40–80 minutes**. The precedent for the writer-only build of
this same tree was 35 min 42 s at `-j12`; calc adds to it.

**Known first-run failure, and it is not yours**: if `make` dies after a couple
of seconds inside `workdir/UnpackedTarball/...`, that is finding 003, a
directory race. **Re-run the identical command once.** It succeeded on the
retry last time. Do not change flags. If it fails a second time, stop and send
the log.

### 5. What to report back

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm-lite/build-a11y-gate0
B=$PWD

cat config_host/config_wasm_strip.h

ls -l $B/instdir/program/soffice.js.linkdeps \
      $B/instdir/program/soffice.data \
      $B/instdir/program/soffice.data.js.metadata \
      $B/workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link \
      $B/workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports

sha256sum $B/instdir/program/soffice.js.linkdeps \
          $B/instdir/program/soffice.data \
          $B/instdir/program/soffice.data.js.metadata \
          $B/workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link \
          $B/workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports

grep -c "libreofficekit_hook_2\|lok_preinit_2" \
  $B/workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports   # >= 2

ls -l $B/instdir/program/soffice.wasm $B/instdir/program/soffice.js
du -sh $B
```

Plus the wall-clock time and whether it needed the finding-003 retry. Those
five artifacts are the same list SPEC-R1-A §4 accepts a core build on, and
sizes are recorded because G0-5 asks for a size baseline (recorded, **not**
judged — M2a is where size gets judged).

## What happens after, so you know what you are waiting for

Mine, once the build exists:

1. Point `check_core_build_provides.py` at this build (it takes `--build DIR`;
   the product's core stays red, which is the honest reading) and teach
   `probe_a11y_gate0.py` to pass it through.
2. Link a **gate-only** probe profile against this core — its own dist
   directory and its own identity. `e2-editor-v4` is not touched, not
   relinked, and stays the product.
3. Run `probe_a11y_gate0.py` and compare against PREDICTION.md — three caret
   placements, ≥ 2 distinct paragraph identities, each matching the paragraph
   actually targeted.
4. Before naming a layer: check the callback is forwarded through the worker
   allowlist. "Core does not support it" is one hypothesis out of four, and
   this tree has been bitten by the allowlist twice in one afternoon.

A FAIL means **stop**, per roadmap §3.3 and G0-3, and the result goes to M3's
product positioning. That was decided before the measurement so that a FAIL
cannot be reread later as "needs more investigation".
