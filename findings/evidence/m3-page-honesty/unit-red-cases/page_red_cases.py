"""Red cases for the page half of U3 (editor-shell-v2/tests/page-unsaved-work.test.mjs):
each mutation of hasUnsavedWork() in web/e2-editor-app.js, on a scratch copy,
must turn that test red.  Prints one JSON document."""
import hashlib, json, shutil, subprocess, sys
from pathlib import Path
PROBE = Path('/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe')
ROOT = Path(sys.argv[1])
PAGE = 'web/e2-editor-app.js'
TEST = 'editor-shell-v2/tests/page-unsaved-work.test.mjs'
BODY = "  return (session ? session.hasUnsavedEdits() : false) || savesUnsettled > 0;"
MUTANTS = {
    "revision greater than zero": "  return (session ? Number(session.state.snapshot.revision) > 0 : false) || savesUnsettled > 0;",
    "revision against a saved revision (review's example)":
        "  return (session ? session.state.snapshot.revision !== savedRevision : false) || savesUnsettled > 0;",
    "fail open (optional call)": "  return (session?.hasUnsavedEdits?.() ?? false) || savesUnsettled > 0;",
    "unsettled saves ignored": "  return (session ? session.hasUnsavedEdits() : false);",
}
def fresh():
    if ROOT.exists(): shutil.rmtree(ROOT)
    for rel in (PAGE, TEST):
        (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PROBE / rel, ROOT / rel)
def run():
    p = subprocess.run(['node', '--test', '--test-reporter=tap', TEST], cwd=ROOT, capture_output=True, text=True, timeout=300)
    lines = p.stdout.splitlines()
    return {"exit": p.returncode,
            "summary": [l for l in lines if l.startswith(('# pass', '# fail', '# tests'))],
            "failedTests": [l.strip() for l in lines if l.lstrip().startswith('not ok')],
            "assertions": [" ".join(x.strip() for x in lines[i:i + 3]) for i, l in enumerate(lines) if l.strip().startswith("error:")]}
out = {"page": PAGE, "pageSha256": hashlib.sha256((PROBE / PAGE).read_bytes()).hexdigest(),
       "testSha256": hashlib.sha256((PROBE / TEST).read_bytes()).hexdigest(), "cases": {}}
fresh(); out["unmutated"] = run()
for name, line in MUTANTS.items():
    fresh()
    src = (ROOT / PAGE).read_text()
    assert src.count(BODY) == 1
    (ROOT / PAGE).write_text(src.replace(BODY, line))
    out["cases"][name] = {"line": line, **run()}
print(json.dumps(out, ensure_ascii=False, indent=1))
