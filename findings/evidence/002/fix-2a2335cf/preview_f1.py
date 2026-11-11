#!/usr/bin/env python3
"""R1 preview of fix F1 for finding 002, without a relink. NOT evidence.

Pastes static/emscripten/environment.js and soffice.data.js.link into a copy of
vcldemo.js at the place where emcc emits --pre-js files (emsdk src/shell.js:130-132):
right after the end of the environment detection block. The output JS is minified
onto one line, so the place is found by an anchor, the last statement of that
block. Every other file is symlinked from the build. Before writing anything it
checks that soffice.js of the same build has its (minified) pre-js right after the
same anchor (the positive control for the method).

usage: preview_f1.py <build-dir> <out-dir>
"""
import pathlib
import re
import sys

build = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(sys.argv[2]).resolve()

cfg = (build / "config_host.mk").read_text()
src = pathlib.Path(re.search(r"^export SRC_ROOT=(.*)$", cfg, re.M).group(1))
exe = build / "workdir/LinkTarget/Executable"
link = build / "workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link"
env = src / "static/emscripten/environment.js"
soffice_js = next((p for p in [exe / "soffice.js",
                                build / "workdir/installation/LibreOffice/emscripten/soffice.js"]
                   if p.exists()), exe / "soffice.js")

ANCHOR = 'worker_threads["workerData"]=="em-pthread"}'
ENV_MINIFIED = 'if(!("preRun"in Module))Module["preRun"]=[];Module.preRun.push(function(){ENV.MAX_CONCURRENCY="4"});Module.ignoreApplicationExit=true;'
prejs = "\n" + env.read_text() + "\n" + link.read_text() + "\n"


def split_at_anchor(text, name):
    n = text.count(ANCHOR)
    if n != 1:
        sys.exit(f"{name}: expected the anchor once, found {n}")
    i = text.index(ANCHOR) + len(ANCHOR)
    return text[:i], text[i:]


# Positive control: in soffice.js the minified environment.js, then the packager
# code, follow the anchor directly.
_, soffice_tail = split_at_anchor(soffice_js.read_text(), "soffice.js")
if not soffice_tail.startswith(ENV_MINIFIED + "var Module=typeof Module"):
    sys.exit(f"soffice.js: pre-js not right after the anchor: {soffice_tail[:200]!r}")
if "expectedDataFileDownloads" not in soffice_tail[:400]:
    sys.exit("soffice.js: packager code not near the anchor")
print(f"positive control ok: {soffice_js.name} has environment.js + packager code right after the anchor")

vcldemo_js = (exe / "vcldemo.js").read_text()
if "loadPackage" in vcldemo_js or "soffice.data" in vcldemo_js:
    sys.exit("vcldemo.js already mentions loadPackage/soffice.data; was it relinked?")
head, tail = split_at_anchor(vcldemo_js, "vcldemo.js")
print(f"vcldemo.js after the anchor: {tail[:60]!r}")

out.mkdir(parents=True, exist_ok=True)
(out / "vcldemo.js").write_text(head + prejs + tail)
for name in ["vcldemo.wasm", "soffice.data", "soffice.data.js.metadata",
             "qtloader.js", "qtlogo.svg", "qt_vcldemo.html"]:
    dst = out / name
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    dst.symlink_to(exe / name)
print(f"wrote {out / 'vcldemo.js'} (+{len(prejs)} chars) and symlinks; serve {out}")
