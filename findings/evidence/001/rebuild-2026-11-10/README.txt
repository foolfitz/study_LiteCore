Kept from wasm-lite/upstream-master, which was deleted on 2026-11-10 at the owner's request (disk 99% full; the five build trees, their ccache and the three git worktrees took 42 GB).

Path mapping for references in the other evidence files:
  wasm-lite/upstream-master/<name>.log                     -> logs/<name>.log
  wasm-lite/upstream-master/build.sh, run_probe.sh         -> ./build.sh, ./run_probe.sh
  wasm-lite/upstream-master/src-*.local-modifications.diff -> ./src-*.local-modifications.diff
  wasm-lite/upstream-master/<build>/autogen.input           -> config/<build>.autogen.input
  wasm-lite/upstream-master/<build>/config_host.mk          -> config/<build>.config_host.mk

Builds (all from detached git worktrees of the LibreOffice core repository):
  build-nosym            master 2a2335cf, stock (--with-distro=LibreOfficeWASM32) + --disable-symbols
  build-lite-nosym       master 2a2335cf, July lite flags, --with-lang=en-US
  build-2682-lite-nosym  libreoffice-26.8.2.2 9dea406a, same as above
  build-2682-july-nosym  libreoffice-26.8.2.2 9dea406a + the two July fs-image patches + translations 171ac7d0, exact July flags
  build-671c-july-nosym  671c848b + the two July fs-image patches + translations 222323f2, exact July flags
Toolchain for all: emsdk 4.0.10 (wasm-lite/tools/emsdk), Qt 5.15.2+wasm (wasm-lite/tools/qt5-wasm). Rebuilding one takes about 40 minutes.
