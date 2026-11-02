#!/usr/bin/env python3
"""Executable red controls for range targeting/refusal and committed-only save."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = {
    "range-limit": ("calc-document-sdk", "(endColumn-column+1)*(endRow-row+1)>RANGE_CELL_LIMIT", "(endColumn-column+1)*(endRow-row+1)>Infinity"),
    "v1-capability": ("calc-document-sdk", "if(!handle.rangeFormattingSupported)", "if(false)"),
    "reply-target": ("calc-document-sdk", "cell.column!==column", "false"),
    "unconfirmed-draft": ("calc-editor-session", "if(commitDraft)await this._commitNow();", "await this._commitNow();"),
    "explicit-range": ("calc-editor-session", "selected.endColumn,selected.endRow,\n          format", "selected.column,selected.row,\n          format"),
    "uncertain-refresh": ("calc-editor-session", '"MUTATION_OUTCOME_UNKNOWN",`range applied', '"CELL_RESULT_INVALID",`range applied', 2, 0),
    "uncertain-refresh-style": ("calc-editor-session", '"MUTATION_OUTCOME_UNKNOWN",`range applied', '"CELL_RESULT_INVALID",`range applied', 2, 1),
}


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix=".range-red-", dir=ROOT) as directory:
        scratch = Path(directory)
        for name, (module, before, after, *place) in MUTATIONS.items():
            occurrences, index = place or (1, 0)  # setFormat and setStyle share a line: name which one
            source = (ROOT / "spreadsheet-shell" / (module + ".js")).read_text()
            if source.count(before) != occurrences:
                raise RuntimeError("mutation premise is absent or ambiguous: " + name)
            for dependency in ("calc-document-sdk", "calc-editor-session"):
                (scratch / (dependency + ".js")).write_text((ROOT / "spreadsheet-shell" / (dependency + ".js")).read_text())
            mutant = scratch / (module + ".js")
            parts = source.split(before)
            mutant.write_text(before.join(parts[:index + 1]) + after + before.join(parts[index + 1:]))
            variable = "CALC_DOCUMENT_MODULE" if module == "calc-document-sdk" else "CALC_SESSION_MODULE"
            result = subprocess.run(["node", "--test", str(ROOT / "tests" / (module + ".test.mjs"))],
                env={**os.environ, variable: str(mutant)}, text=True, capture_output=True, timeout=15)
            failures = [line for line in result.stdout.splitlines() if line.startswith(("✖", "not ok "))]
            results.append({"id": name, "rejected": result.returncode != 0 and bool(failures), "failures": failures})
    passed = bool(results) and all(item["rejected"] for item in results)
    print(json.dumps({"pass": passed, "controls": results}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
