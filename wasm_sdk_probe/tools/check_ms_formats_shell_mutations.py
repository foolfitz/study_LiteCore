#!/usr/bin/env python3
"""SPEC-P-ms-formats 10.2: red cases for the shell's format tests.  Each mutation edits one source in place, runs the one test file,
puts the source back (verified byte for byte), and must turn red on the test named for it.  Writer: 9 mutations of
editor-shell-v2/narrow-editor-v2-session.js and sdk/document-sdk.js against editor-shell-v2/tests/ms-formats-session.test.mjs;
Calc: 8 of spreadsheet-shell/calc-editor-session.js against tests/calc-ms-formats.test.mjs.  Exit 0 iff every one is red where expected.
Do not run while anything serves these files.
  python3 tools/check_ms_formats_shell_mutations.py
"""
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def writer():
    root = PROJECT
    S = root / "editor-shell-v2/narrow-editor-v2-session.js"
    K = root / "sdk/document-sdk.js"
    T = "editor-shell-v2/tests/ms-formats-session.test.mjs"
    src = S.read_text(); sdk = K.read_text()
    save_block = src[src.index("  save(options = {}) {\n    return this._enqueue(\"save\""):]
    save_block = save_block[:save_block.index("\n  }\n")]
    ck = src[src.index("  async _checkpointBeforeSelection(document) {"):]
    ck = ck[:ck.index("\n  }\n")]
    MUT = {
     "save-odt": (S, save_block, save_block.replace("{ format: documentFormatOf(document) }", '{ format: "odt" }'), "DOCX: save"),
     "checkpoint-odt": (S, ck, ck.replace("{ format: documentFormatOf(document) }", '{ format: "odt" }'), "DOCX: save, checkpoint"),
     "save-keeps-dirty": (S, save_block, save_block.replace("        dirty: false,\n", ""), "ODT: the override's save"),
     "save-keeps-checkpoint": (S, save_block, save_block.replace("      this._checkpointBytes = null;\n", ""), "ODT: the override's save"),
     "checkpoint-no-stamp": (S, ck, ck.replace("      this._checkpointStamp = contentStamp;\n", ""), "ODT: the override's checkpoint"),
     "checkpoint-error-code": (S, ck, ck.replace('"CHECKPOINT_FAILED"', '"EDITOR_ERROR"').replace("error?.code ||", ""), "ODT: the override's checkpoint"),
     "copy-marks-clean": (S, "      return { bytes, format, revision: document.revision };\n    });", "      return { bytes, format, revision: document.revision };\n    }, { finalize: (r) => { this.state.update({ dirty: false }); return r; } });", "Save As is a copy"),
     "copy-is-authority": (S, "      return { bytes, format, revision: document.revision };\n    });", "      this._authorityBytes = bytes.slice(0);\n      return { bytes, format, revision: document.revision };\n    });", "Save As is a copy"),
     "sdk-drops-format": (K, "    this.format = typeof metadata.format", "    this.format = null && typeof metadata.format", "the SDK handle"),
    }
    out = []
    for name, (path, old, new, expect) in MUT.items():
        text = path.read_text()
        assert text.count(old) == 1, name
        path.write_text(text.replace(old, new))
        try:
            p = subprocess.run(["node", "--test", T], cwd=root, capture_output=True, text=True)
        finally:
            S.write_text(src); K.write_text(sdk)
        failed = [l[2:].split(" (")[0] for l in p.stdout.splitlines() if l.startswith("✖ ")]
        hit = any(f.startswith(expect) for f in failed)
        out.append((name, p.returncode, hit, failed))
        print(f"{name:24s} exit={p.returncode} red_where_expected={hit} failed={failed}")
    assert S.read_text() == src and K.read_text() == sdk
    ok = all(r[1] != 0 and r[2] for r in out)
    print("writer:", "ALL_RED_WHERE_EXPECTED" if ok else "SOME_MUTATION_SURVIVED")
    return ok


def calc():
    root = PROJECT
    S = root / "spreadsheet-shell/calc-editor-session.js"
    T = "tests/calc-ms-formats.test.mjs"
    src = S.read_text()
    copy = src[src.index("  saveCopy(format,target) {"):]; copy = copy[:copy.index("\n  scheduleViewport")]
    MUT = {
     "save-ods-literal": ("        const format=this.documentFormat();\n", '        const format="ods";\n', "an XLSX is saved as XLSX"),
     "host-not-told": ("const result=await target(bytes,{name:this.state.fileName,format});", "const result=await target(bytes,{name:this.state.fileName});", "an XLSX is saved as XLSX"),
     "odt-accepted": ('export const CALC_SAVE_FORMATS = Object.freeze(["ods", "xlsx"]);', 'export const CALC_SAVE_FORMATS = Object.freeze(["ods", "xlsx", "odt"]);', "the save format"),
     "copy-moves-saved": ("        return {bytes,result,format};", "        this._savedRevision=this.document.revision;\n        return {bytes,result,format};", "Save As: the chosen"),
     "copy-no-commit": ("      await this._commitNow();\n      this._saving++;this._emit();\n      try {\n        const bytes=await this.document.save({format});", "      this._saving++;this._emit();\n      try {\n        const bytes=await this.document.save({format});", "Save As: the chosen"),
     "copy-no-readonly": ('      if (this._readOnly)\n        throw new DocumentSdkError("READ_ONLY", "this spreadsheet cannot be saved");\n'
                          '      if (!CALC_SAVE_FORMATS', "      if (!CALC_SAVE_FORMATS", "Save As refuses"),
     "copy-any-format": ("      if (!CALC_SAVE_FORMATS.includes(format))\n", "      if (false)\n", "Save As refuses"),
     "copy-saving-leak": ("        return {bytes,result,format};\n      } finally { this._saving--;this._emit(); }", "        return {bytes,result,format};\n      } finally { }", "a failed copy"),
    }
    ok = True
    for name, (old, new, expect) in MUT.items():
        assert src.count(old) == 1, name
        S.write_text(src.replace(old, new))
        try:
            p = subprocess.run(["node", "--test", T], cwd=root, capture_output=True, text=True)
        finally:
            S.write_text(src)
        failed = sorted({l[2:].split(" (")[0] for l in p.stdout.splitlines() if l.startswith("✖ ")} - {"failing tests:"})
        hit = p.returncode != 0 and any(f.startswith(expect) for f in failed)
        ok &= hit
        print(f"{name:20s} exit={p.returncode} red_where_expected={hit} {[f[:30] for f in failed]}")
    assert S.read_text() == src
    print("calc:", "ALL_RED_WHERE_EXPECTED" if ok else "SOME_MUTATION_SURVIVED")
    return ok

if __name__ == "__main__":
    sys.exit(0 if all([writer(), calc()]) else 1)
