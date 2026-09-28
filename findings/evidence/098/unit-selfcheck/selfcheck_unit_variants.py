#!/usr/bin/env python3
"""Findings 098/099: which unit tests go red when only part of the fix is present.

Usage (S is any scratch directory):
  git show a7daa562:wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js > S/head.js
  python3 selfcheck_unit_variants.py S

`a7daa562` is the last commit before the fix.  Each variant is the pre-fix
session with exact-text replacements applied (asserted to match once), served
beside a copy of editor-shell-v2/ whose test file is the tree's CURRENT one, so
every variant is judged by the same tests.  The last variant reads the tree's
session file as it stands.
"""
import os, re, shutil, subprocess, sys, json
from pathlib import Path
P = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
S = Path(sys.argv[1])
head = (S / "head.js").read_text()
A_OLD = "      { mutation: true },\n    )"
A_NEW = "      { mutation: !BOUNDARY_CAPABLE_MOVES.has(action) },\n    )"
C_OLD = "        && this._checkpointRevision === document.revision) {"
C_NEW = "        && this._checkpointStamp === this._currentContentStamp) {"
C3_OLD = ("    if (this.state.snapshot.hasCheckpoint\n"
          "        && this._checkpointRevision === document.revision) {\n"
          "      this.boundaryCheckpointsSkipped += 1;\n"
          "      return;\n    }\n")
def rep(t, old, new):
    assert t.count(old) == 1, old
    return t.replace(old, new)
variants = {
  "baseline (HEAD)": head,
  "A only": rep(head, A_OLD, A_NEW),
  "C1 only": rep(head, C_OLD, C_NEW),
  "A + C3 (guard 2 deleted)": rep(rep(head, A_OLD, A_NEW), C3_OLD, ""),
  "A + C1 (the fix, as in the tree)": (P / "editor-shell-v2/narrow-editor-v2-session.js").read_text(),
}
# The adversarial review's wrong guard (codex, 2026-09-28): the fix, plus a
# skip whenever the old checkpoint's revision is one above the new Worker's.
# It passed the single-case 099 test; the grid must catch it.
tree = variants["A + C1 (the fix, as in the tree)"]
variants["A + C1 + codex's revision+1 skip"] = rep(
    tree, C_NEW,
    "        && (this._checkpointStamp === this._currentContentStamp\n"
    "            || this._checkpointRevision === document.revision + 1)) {")

# The second review's four wrong versions (opus, 2026-09-28).  Each passed all
# 33 tests of the file as it stood; each must now go red somewhere.
GUARD_HEAD = "    if (this.state.snapshot.hasCheckpoint\n" + C_NEW + "\n"
SKIP = ("      this.boundaryCheckpointsSkipped += 1;\n      return;\n    }\n")
assert tree.count(GUARD_HEAD + SKIP) == 1
variants_late = {
  "V1 revision+3 skip": rep(tree, C_NEW,
      "        && (this._checkpointStamp === this._currentContentStamp\n"
      "            || this._checkpointRevision === document.revision + 3)) {"),
  "V2 no retry after a failed save": rep(tree, GUARD_HEAD,
      "    if (this.state.snapshot.checkpointError) {\n" + SKIP + GUARD_HEAD),
  "V3 shift-move counted as a mutation": rep(tree,
      "      { mutation: !BOUNDARY_CAPABLE_MOVES.has(action) },",
      "      { mutation: !BOUNDARY_CAPABLE_MOVES.has(action)"
      " || options.extendSelection === true },"),
  "V4 revision guard in generation one": rep(tree, C_NEW,
      "        && (this._checkpointStamp === this._currentContentStamp\n"
      "            || (this._generation === 1\n"
      "                && this._checkpointRevision === document.revision))) {"),
}
variants.update(variants_late)
out = {}
for name, text in variants.items():
    root = S / re.sub(r"[^a-z0-9]+", "-", name.lower())
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    for d in ("editor-shell", "dist", "input", "sdk", "reader-shell"):
        os.symlink(P / d, root / d)
    shutil.copytree(P / "editor-shell-v2", root / "editor-shell-v2", symlinks=True)
    (root / "editor-shell-v2/narrow-editor-v2-session.js").write_text(text)
    r = subprocess.run(["node", "--test", "editor-shell-v2/tests/narrow-editor-v2-session.test.mjs"],
                       cwd=root, capture_output=True, text=True)
    fails = sorted(set(l.split("✖ ",1)[1].rsplit(" (",1)[0] for l in r.stdout.splitlines()
                       if l.startswith("✖ ")))
    tot = re.search(r"ℹ tests (\d+)", r.stdout); ps = re.search(r"ℹ pass (\d+)", r.stdout)
    out[name] = {"tests": int(tot.group(1)), "pass": int(ps.group(1)), "red": fails}
print(json.dumps(out, indent=1, ensure_ascii=False))
