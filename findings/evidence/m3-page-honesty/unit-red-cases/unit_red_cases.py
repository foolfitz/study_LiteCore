"""Re-run the four unit-test red cases of SPEC-M3-page-honesty (V3, U3) on a
scratch copy of the shell, never on the tree.  Prints one JSON document."""
import json, shutil, subprocess, sys, hashlib
from pathlib import Path
PROBE = Path('/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe')
ROOT = Path(sys.argv[1])
TARGET = 'editor-shell-v2/narrow-editor-v2-session.js'
TEST = 'editor-shell-v2/tests/narrow-editor-v2-session.test.mjs'
KNOWN = ["set-bold", "set-italic", "set-underline", "set-strikethrough", "clear-format", "set-paragraph-heading",
         "set-paragraph-body", "set-list-unordered", "set-list-ordered", "set-list-none", "delete-backward",
         "delete-forward", "insert-paragraph-break", "insert-line-break", "insert-text", "undo", "redo", "save"]
MUTANTS = {
    "gate removed": [("if (this._viewOnly && options?.mutation === true) {",
                      "if (false && this._viewOnly && options?.mutation === true) {")],
    "gate refuses default options too (mutation !== false)": [
        ("if (this._viewOnly && options?.mutation === true) {",
         "if (this._viewOnly && options?.mutation !== false) {")],
    "actionMutates defaults to false": [("return !BOUNDARY_CAPABLE_MOVES.has(name);",
                                          "return BOUNDARY_CAPABLE_MOVES.has(name) ? false : "
                                          + json.dumps(KNOWN) + ".includes(name);")],
    "unsaved compares revisions": [
        ("  hasUnsavedEdits() {\n    const snapshot = this.state.snapshot;\n"
         "    return snapshot.dirty === true || (snapshot.pending ?? 0) > 0;\n  }",
         "  async save(...args) { const r = await super.save(...args);"
         " this.__savedRev = this.state.snapshot.revision; return r; }\n"
         "  hasUnsavedEdits() {\n    const snapshot = this.state.snapshot;\n"
         "    return (snapshot.pending ?? 0) > 0 || Number(snapshot.revision) > Number(this.__savedRev ?? 0);\n  }")],
    "unsaved compares revisions with !==": [
        ("  hasUnsavedEdits() {\n    const snapshot = this.state.snapshot;\n"
         "    return snapshot.dirty === true || (snapshot.pending ?? 0) > 0;\n  }",
         "  async save(...args) { const r = await super.save(...args);"
         " this.__savedRev = this.state.snapshot.revision; return r; }\n"
         "  hasUnsavedEdits() {\n    const snapshot = this.state.snapshot;\n"
         "    return (snapshot.pending ?? 0) > 0 || Number(snapshot.revision) !== Number(this.__savedRev ?? 0);\n  }")],
    "unsaved ignores pending": [("return snapshot.dirty === true || (snapshot.pending ?? 0) > 0;",
                                 "return snapshot.dirty === true;")],
}
def fresh():
    if ROOT.exists(): shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)
    for d in ('editor-shell-v2', 'editor-shell', 'input', 'reader-shell', 'sdk'):
        shutil.copytree(PROBE / d, ROOT / d, ignore=shutil.ignore_patterns('node_modules'))
    (ROOT / 'dist').symlink_to(PROBE / 'dist')
def run():
    p = subprocess.run(['node', '--test', '--test-reporter=tap', TEST], cwd=ROOT, capture_output=True, text=True, timeout=600)
    tail = [l for l in p.stdout.splitlines() if l.startswith(('# pass', '# fail', '# tests'))]
    failed = [l.strip() for l in p.stdout.splitlines() if l.lstrip().startswith('not ok')]
    lines = p.stdout.splitlines()
    errors = [" ".join(x.strip() for x in lines[i:i + 3]) for i, l in enumerate(lines) if l.strip().startswith("error:")]
    return {"exit": p.returncode, "summary": tail, "failedTests": failed, "assertions": errors}
out = {"target": TARGET, "targetSha256": hashlib.sha256((PROBE / TARGET).read_bytes()).hexdigest(),
       "testSha256": hashlib.sha256((PROBE / TEST).read_bytes()).hexdigest(), "cases": {}}
fresh(); out["unmutated"] = run()
for name, edits in MUTANTS.items():
    fresh()
    src = (ROOT / TARGET).read_text()
    for old, new in edits:
        assert src.count(old) == 1, (name, old[:60])
        src = src.replace(old, new)
    (ROOT / TARGET).write_text(src)
    out["cases"][name] = {"edits": edits, **run()}
print(json.dumps(out, ensure_ascii=False, indent=1))
