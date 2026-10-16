#!/usr/bin/env python3
"""T3: is the md4c the harness compiles the md4c the cores link?

Usage: md4c_version_check.py REPO EMPTY_SCRATCH_DIR REPORT_FILE

Checks, printing each fact with its source:
  1. libreoffice-26-8/download.lst names the tarball and its sha256;
  2. the tarball in libreoffice-26-8/external/tarballs has that sha256;
  3. the tarball, extracted into EMPTY_SCRATCH_DIR (untrusted data: extracted
     only, nothing in it is run), is file-for-file identical to
     workdir/UnpackedTarball/md4c of each core tree (external/md4c applies no
     patch: UnpackedTarball_md4c.mk has none);
  4. each tree's libmd4c.a is built from that UnpackedTarball (its objectlist),
     and the WASM link-deps / the native libswlo.so carry it;
  5. CMakeLists.txt's VERSION.
Exit 0 if 2 and 3 hold for every tree found.
"""

import filecmp
import hashlib
import os
import re
import subprocess
import sys
import tarfile

TREES = ["wasm-lite/build-headless-probe/workdir", "wasm-lite/build-a11y-gate0/workdir",
         "native-lok-26-8/build/workdir"]


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def same_tree(a, b):
    """Every file under a equals the same path under b, and vice versa."""
    diffs = []

    def walk(cmp, rel):
        diffs.extend(os.path.join(rel, n) for n in cmp.left_only + cmp.right_only + cmp.funny_files)
        _, mismatch, errors = filecmp.cmpfiles(cmp.left, cmp.right, cmp.common_files, shallow=False)
        diffs.extend(os.path.join(rel, n) for n in mismatch + errors)
        for name, sub in cmp.subdirs.items():
            walk(sub, os.path.join(rel, name))
    walk(filecmp.dircmp(a, b), "")
    return diffs


def main(argv):
    repo, scratch, report = argv[1:4]
    lines = []
    ok = True
    dl = open(os.path.join(repo, "libreoffice-26-8/download.lst")).read()
    want_sha = re.search(r"^MD4C_SHA256SUM := (\S+)", dl, re.M).group(1)
    tar_name = re.search(r"^MD4C_TARBALL := (\S+)", dl, re.M).group(1)
    lines.append("download.lst: MD4C_TARBALL := %s, MD4C_SHA256SUM := %s" % (tar_name, want_sha))
    tar_path = os.path.join(repo, "libreoffice-26-8/external/tarballs", tar_name)
    got = sha(tar_path)
    lines.append("external/tarballs/%s sha256 %s -> %s" % (tar_name, got, "MATCHES download.lst" if got == want_sha
                                                          else "DIFFERENT"))
    ok &= got == want_sha
    mk = open(os.path.join(repo, "libreoffice-26-8/external/md4c/UnpackedTarball_md4c.mk")).read()
    lines.append("external/md4c/UnpackedTarball_md4c.mk patches: %s" % (
        "none" if "add_patches" not in mk else "PRESENT"))
    os.makedirs(scratch, exist_ok=True)
    if os.listdir(scratch):
        raise SystemExit("scratch dir must be empty")
    with tarfile.open(tar_path) as tar:
        tar.extractall(scratch, filter="data")
    top = os.path.join(scratch, os.listdir(scratch)[0])
    cm = open(os.path.join(top, "CMakeLists.txt")).read()
    lines.append("tarball CMakeLists.txt: %s" % re.search(r'VERSION "[^"]+"', cm).group(0))
    for tree in TREES:
        ut = os.path.join(repo, tree, "UnpackedTarball/md4c")
        if not os.path.isdir(ut):
            lines.append("%s: no UnpackedTarball/md4c" % tree)
            continue
        diffs = same_tree(top, ut)
        lines.append("%s/UnpackedTarball/md4c vs extracted tarball: %s" % (
            tree, "IDENTICAL (every file)" if not diffs else "DIFFERS: %s" % diffs[:10]))
        ok &= not diffs
        version = open(os.path.join(repo, tree, "UnpackedTarball/md4c.version")).read().strip()
        lines.append("  md4c.version: %s" % version.replace(repo, "<repo>"))
        lines.append("  src/md4c.c sha256 %s, src/md4c.h sha256 %s" % (
            sha(os.path.join(ut, "src/md4c.c")), sha(os.path.join(ut, "src/md4c.h"))))
        objlist = os.path.join(repo, tree, "LinkTarget/StaticLibrary/libmd4c.a.objectlist")
        if os.path.exists(objlist):
            objs = open(objlist).read().split()
            lines.append("  libmd4c.a objectlist: %s" % " ".join(o.replace(repo, "<repo>") for o in objs))
        build = os.path.dirname(os.path.join(repo, tree))
        linkdeps = os.path.join(build, "instdir/program/soffice.js.linkdeps")
        if os.path.exists(linkdeps):
            hits = [w for w in open(linkdeps).read().split() if "libmd4c" in w]
            lines.append("  instdir/program/soffice.js.linkdeps: %s" % [h.replace(repo, "<repo>") for h in hits])
        swlo = os.path.join(build, "instdir/program/libswlo.so")
        if os.path.exists(swlo):
            nm = subprocess.run(["nm", swlo], capture_output=True, text=True).stdout
            hit = [line for line in nm.splitlines() if line.endswith(" md_parse")]
            lines.append("  instdir/program/libswlo.so nm: %s" % hit)
    lines.append("RESULT: %s" % ("PASS" if ok else "FAIL"))
    text = "\n".join(lines) + "\n"
    with open(report, "w") as handle:
        handle.write(text)
    print(text, end="")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
