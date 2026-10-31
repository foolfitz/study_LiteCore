#!/usr/bin/env python3
"""SPEC-M3-K-0.2.44 append 2, red cases of the merge keying (RULING.md Q5).

  check_keying.py red-cases --out DIR   R1-R5, R7, offline
  check_keying.py proof DIR             the mirror proof's ten records, then R6 on copies

No browser here.  Writes only under --out and temp directories.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PROJECT = REPO / "wasm_sdk_probe"
TOOLS = PROJECT / "tools"
sys.path.insert(0, str(TOOLS))

import judge_counted_m2 as judge  # noqa: E402
import k_0244_merge_keying as keying  # noqa: E402

m = judge.m
HIST = REPO / "findings/evidence/release-0.2.26/merge-m2"
SMOKE = REPO / "findings/evidence/k-0.2.44/merge-smoke/shakedown-chrome.json"
V28 = PROJECT / "dist/profiles/e2-editor-v28/probe.wasm"
INVENTORY = json.loads((REPO / "findings/evidence/k-0.2.44/k-binding-inventory.json").read_bytes())
BOUND = INVENTORY["proposedMergeBinding"]["wasmSha256"]
FIVE = ("C15", "C16", "C17", "C29", "C30")
NOOP_CLAUSES = ("unchangedText", "markerOnce", "revision", "generation", "noToast", "caretUnchanged")
rows = []


def check(name, ok, detail=""):
    rows.append({"check": name, "ok": bool(ok), "detail": str(detail)[:300]})
    print(f"{'ok  ' if ok else 'FAIL'}  {name}" + (f"  [{str(detail)[:190]}]" if detail else ""), flush=True)


def run(*argv):
    return subprocess.run([sys.executable, *map(str, argv)], cwd=REPO, capture_output=True, text=True)


def installed_cases():
    key = keying.read_key(V28, m.BOUNDARY_NOOP_FRAGMENT, BOUND)
    keying.require_ordered(key)
    keying.install(m, judge, key)
    return judge.population(True)[0]


def child(code):
    """A fresh interpreter: `install` replaces module attributes, so a case that forces a table cannot share this one."""
    return subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(HERE)!r}); import check_keying as c\n{code}"],
                          cwd=REPO, capture_output=True, text=True)


def synthetic(directory: Path):
    """A holding input for read_k_0244_merge.py: the 0.2.26 reports rebound, reds copied, with the record the wrapper writes."""
    proposed = INVENTORY["proposedMergeBinding"]
    key = keying.read_key(V28, m.BOUNDARY_NOOP_FRAGMENT, BOUND)
    for browser in ("chrome", "firefox"):
        for stem in ("counted-{}", "counted-control-{}", "m2-1b-{}", "m2-4-{}"):
            name = stem.format(browser)
            report = json.loads((HIST / f"{name}.json").read_text())
            report.update(counted=True, binding=proposed, bound=proposed)
            report["candidate"]["profile"] = "e2-editor-v28"
            (directory / f"{name}.json").write_text(json.dumps(report))
            (directory / f"{name}.stderr.txt").write_text("")
            (directory / f"{name}.json.binding-override.json").write_text(json.dumps({"binding": {"applied": True}, "keying": key}))
        shutil.copy(HIST / f"red-{browser}.json", directory)
        shutil.copy(HIST / f"red-{browser}.stderr.txt", directory)


def red_cases(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    # Positive: the real keying.
    v28 = keying.read_key(V28, m.BOUNDARY_NOOP_FRAGMENT, BOUND)
    check("the bound v28 wasm is on the ordered table, by its ABI, without the fragment",
          v28["table"] == keying.ORDERED and v28["abiVersion"] == 6 and v28["fragmentInBytes"] is False, v28)
    v21 = keying.read_key(PROJECT / "dist/profiles/e2-editor-v21/probe.wasm", m.BOUNDARY_NOOP_FRAGMENT, BOUND)
    check("v21 stays on the C table", v21["table"] == "c" and v21["abiVersion"] == 5, v21["table"])
    v19 = keying.read_key(PROJECT / "dist/profiles/e2-editor-v19/probe.wasm", m.BOUNDARY_NOOP_FRAGMENT, BOUND)
    check("v19 stays on the refusal table", v19["table"] == "refusal", v19["table"])
    # The table the ruling states, from the tool, per class.
    answer = child("""
cases = c.installed_cases()
print(c.json.dumps({k: list(v["expected"]) for k, v in cases.items() if k in c.FIVE}))
print(c.json.dumps(c.judge.kept_expected(cases)))
print(c.json.dumps(list(c.judge.expectation("refused-k2-x", True))))
""")
    lines = answer.stdout.strip().splitlines()
    table = json.loads(lines[0]) if lines else {}
    check("all five expect the no-op under the ordered table", set(table) == set(FIVE)
          and all(v[0] == m.BOUNDARY_NOOP for v in table.values()), answer.stderr[-200:] or table)
    check("kept documents are the ruling's after-key 78, follow 63, reopened 0",
          lines[1:2] and json.loads(lines[1]) == {"after-key": 78, "follow": 63, "reopened": 0}, lines[1:2])
    check("refused-k2-* is not moved", lines[2:3] and json.loads(lines[2])[1] == "refused", lines[2:3])
    # R1
    r1 = run(TOOLS / "run_k_0244_merge.py", "--browser", "chrome", "--mode", "m2-1-red", "--candidate-profile", "e2-editor-v8",
             "--out", out / "r1-must-not-exist.json")
    check("R1 the wrapper refuses the v8 profile before any browser", r1.returncode != 0 and "e2-editor-v8" in r1.stderr
          and not (out / "r1-must-not-exist.json").exists(), r1.stderr.strip()[-160:])
    # R2
    args = ("--dir", HIST, "--profile", "e2-editor-v21", "--uncounted")
    bare, wrapped = run(TOOLS / "judge_counted_m2.py", *args), run(TOOLS / "judge_k_0244_merge.py", *args)
    (out / "r2-bare.stdout.txt").write_text(bare.stdout)
    (out / "r2-wrapped.stdout.txt").write_text(wrapped.stdout)
    check("R2 inert on ABI 5: wrapped stdout equals the bare judge's, exit 4 both",
          bare.stdout == wrapped.stdout and bare.returncode == wrapped.returncode == 4 and bare.stdout, (bare.returncode, wrapped.returncode))
    # R3
    r3 = child(f"""
key = c.keying.read_key(c.PROJECT / "dist/profiles/e2-editor-v21/probe.wasm", c.m.BOUNDARY_NOOP_FRAGMENT, None)
key["table"] = c.keying.ORDERED
c.keying.install(c.m, c.judge, key)
code, lines = c.judge.judge(c.HIST, "e2-editor-v21", list(c.judge.BROWSERS), True)
print(code); print("\\n".join(lines))
""")
    (out / "r3-forced-ordered.stdout.txt").write_text(r3.stdout)
    first = r3.stdout.split("\n", 1)[0]
    named = [c for c in ("C15", "C16", "C17") if c in r3.stdout]
    check("R3 ABI forced to 6 on v21's records: FAIL, and on C15-C17", first == "1" and "M2-3" in r3.stdout and len(named) == 3,
          (first, named))
    # R4
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        os.symlink(V28, scratch / "probe.wasm")
        manifest = json.loads(V28.with_name("sdk-manifest.json").read_text())
        manifest["editorContract"]["wasmSha256"] = "0" * 64
        (scratch / "sdk-manifest.json").write_text(json.dumps(manifest))
        key = keying.read_key(scratch / "probe.wasm", m.BOUNDARY_NOOP_FRAGMENT, BOUND)
        try:
            keying.require_ordered(key)
            refused = False
        except SystemExit:
            refused = True
        check("R4 the manifest does not name the served wasm: refused, the wrapper stops before a browser",
              refused and key["table"] == "refusal", key["table"])
    other = keying.read_key(V28, m.BOUNDARY_NOOP_FRAGMENT, "0" * 64)
    check("R4 the served wasm is not the bound one: not the ordered table", other["table"] != keying.ORDERED, other["table"])
    # R5
    r5 = child("""
cases = c.installed_cases()
report = c.json.loads(c.SMOKE.read_text())
print(c.json.dumps({r["case"]: c.judge.status(c.judge.m2_3_record(r, cases[r["case"]], c.SMOKE)) for r in report["cases"] if r["case"] in c.FIVE}))
""")
    statuses = json.loads(r5.stdout.strip().splitlines()[-1]) if r5.stdout.strip() else {}
    check("R5 the smoke's refusal-branch records are not PASS under the ordered table",
          set(statuses) == set(FIVE) and "PASS" not in statuses.values(), statuses or r5.stderr[-200:])
    # R7
    with tempfile.TemporaryDirectory() as scratch:
        synthetic(Path(scratch))
        holds = run(TOOLS / "read_k_0244_merge.py", "--dir", scratch)
        check("R7 the reader holds on a synthetic rebinding with a keying record", holds.returncode == 0, holds.stdout[:200])
        self_test = run(TOOLS / "read_k_0244_merge.py", "--dir", scratch, "--self-test")
        (out / "r7-reader-self-test.json").write_text(self_test.stdout)
        check("R7 every reader mutation red, the three new ones included", '"selfTest": "ALL_RED"' in self_test.stdout
              and all(n in self_test.stdout for n in ("no-keying-record", "served-wasm-is-not-bound", "abi-5-on-the-ordered-table")),
              self_test.stdout[:120])
    verdict = {"tool": "check_keying.py red-cases", "held": sum(r["ok"] for r in rows), "of": len(rows), "rows": rows}
    (out / "report.json").write_text(json.dumps(verdict, indent=1, ensure_ascii=False) + "\n")
    return 0 if all(r["ok"] for r in rows) else 1


def without_marker(raw: bytes) -> bytes:
    """The kept document with the marker taken out of the body."""
    source, target = zipfile.ZipFile(io.BytesIO(raw)), io.BytesIO()
    with zipfile.ZipFile(target, "w") as out:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "content.xml":
                head, body = data.split(b"<office:text", 1)
                assert m.MARKER.encode() in body
                data = head + b"<office:text" + body.replace(m.MARKER.encode(), b"", 1)
            out.writestr(info, data)
    return target.getvalue()


def proof(directory: Path):
    cases = installed_cases()
    records = {}
    for browser in ("chrome", "firefox"):
        path = directory / f"{browser}.json"
        report = json.loads(path.read_text())
        check(f"proof {browser}: the five cases, bound to v28, one round",
              sorted(r["case"] for r in report["cases"]) == sorted(FIVE) and (report.get("bound") or {}).get("wasmSha256") == BOUND,
              [r["case"] for r in report["cases"]])
        override = json.loads(path.with_name(path.name + ".binding-override.json").read_text())
        check(f"proof {browser}: keying record", override.get("keying", {}).get("table") == keying.ORDERED, override.get("keying"))
        for record in report["cases"]:
            clauses = judge.m2_3_record(record, cases[record["case"]], path)
            status = judge.status(clauses)
            records[(browser, record["case"])] = (record, path)
            detail = {k: clauses.get(k) for k in NOOP_CLAUSES}
            check(f"proof {browser} {record['case']}: {record.get('outcome')}", record.get("outcome") == m.BOUNDARY_NOOP
                  and status == "PASS" and all(clauses.get(k) is True for k in NOOP_CLAUSES)
                  and (path.parent / f"{path.stem}.docs" / f"{record['case']}-r1-after-key.odt").is_file(), detail)
    # R6, on copies.
    (record, path) = records[("chrome", "C15")]
    judged = lambda r, p=path: judge.m2_3_record(r, cases[r["case"]], p)  # noqa: E731

    def mutated(mutate):
        copied = copy.deepcopy(record)
        mutate(copied)
        return copied

    for name, mutate, clause in (
            ("generation moved", lambda r: r.update(generation=["1", "2"]), "generation"),
            ("a toast", lambda r: r.update(toasts=["x"]), "noToast"),
            ("the caret moved", lambda r: r["caretAfterKey"]["caret"].update(x=r["caretAfterKey"]["caret"]["x"] + 1), "caretUnchanged"),
            ("the outcome is a refusal", lambda r: r.update(outcome="refused"), "outcome"),
            ("the revision moved", lambda r: r["afterKey"].update(revision=str(r["afterKey"]["revision"]) + "1"), "revision")):
        result = judged(mutated(mutate))
        check(f"R6 {name}", result.get(clause) is False, {clause: result.get(clause)})
    with tempfile.TemporaryDirectory() as scratch:
        docs = Path(scratch) / "chrome.docs"
        docs.mkdir()
        name = "C15-r1-after-key"
        raw = without_marker((path.parent / "chrome.docs" / f"{name}.odt").read_bytes())
        (docs / f"{name}.odt").write_bytes(raw)
        parts = m.odt_parts(raw)
        changed = mutated(lambda r: r["afterKeyDocument"].update(sha=parts["sha"], paragraphs=len(parts["paragraphs"])))
        result = judged(changed, Path(scratch) / "chrome.json")
        check("R6 the marker removed from the kept document", result.get("unchangedText") is False and result.get("markerOnce") is False,
              {k: result.get(k) for k in ("unchangedText", "markerOnce")})
    verdict = {"tool": "check_keying.py proof", "held": sum(r["ok"] for r in rows), "of": len(rows), "rows": rows}
    (directory / "read.json").write_text(json.dumps(verdict, indent=1, ensure_ascii=False) + "\n")
    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    if sys.argv[1] == "red-cases":
        code = red_cases(Path(sys.argv[sys.argv.index("--out") + 1]))
    else:
        code = proof(Path(sys.argv[2]))
    print(f"\n{sum(r['ok'] for r in rows)}/{len(rows)} hold")
    raise SystemExit(code)
