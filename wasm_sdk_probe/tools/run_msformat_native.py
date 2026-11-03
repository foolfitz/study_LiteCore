#!/usr/bin/env python3
"""Microsoft formats, native measurement M0 (specs/SPEC-P-ms-formats.md): the corpus through tools/msformat_native.cpp on the
native 26.8 core, two arms per file, every file copied fresh for every run (a `.~lock` left by an earlier run makes the next
load read-only and silent, memory 2026-11-03).

  true-name  the file under its own name; saved in its own format twice -- LOK's saveAs (the engine's save) and
             `own.EXT`, storeToURL with the filter the file was loaded with (Collabora's `.uno:Save`) -- and in ODF,
             every output loaded again.
  odf-name   the same bytes named `.odt` / `.ods`, the name the shipped engine's open boundary accepts today (finding 013);
             saved in ODF only.  Answers whether type detection picks the same filter when the suffix lies, which decides
             whether a no-link WASM measurement under that name says anything about the real one.

Per run: exit, wall time, stderr tail, the harness's JSON, and the content dumps compared (source, own-format round trip,
own-filter round trip, ODF round trip, odf-name source).  Observations, not verdicts.

Evidence is kept lean: after each run the LibreOffice user profile and the input copy are deleted (the input is named by
sha256 in the report), every saved document is replaced by its sha256 and size, and the dumps are gzipped.

  run_msformat_native.py --harness build/msformat-native/msformat-native --out DIR [--only NAME]
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
LO = ROOT / "libreoffice-26-8"
PROGRAM = ROOT / "build-native-26-8/instdir/program"
R7 = ROOT / "wasm_sdk_probe/test-docs/r7-compat"

# Picked 2026-11-03 from LibreOffice's QA tree (core 671c848b) by tools/... survey: files whose docProps/app.xml names a
# Microsoft application, under 400 KB, most features first (tables, headers, lists, images, redlines, real CJK text; sheets,
# formulas, merges, charts, conditional formats).  Legacy binaries: the first three files of 20-200 KB by name.
MS_AUTHORED = [
    "sw/qa/extras/ooxmlexport/data/FDO76312.docx",
    "sw/qa/extras/ooxmlexport/data/lvlPicBulletId.docx",
    "sw/qa/extras/ooxmlexport/data/n830205.docx",
    "sw/qa/extras/ooxmlexport/data/tdf105688.docx",
    "sw/qa/extras/ooxmlexport/data/tdf123705.docx",
    "sw/qa/extras/ooxmlexport/data/tdf149089.docx",
    "sw/qa/extras/ooxmlexport/data/tdf142407.docx",
    "sc/qa/unit/data/xlsx/forum-mso-de-104083.xlsx",
    "sc/qa/unit/data/xlsx/orderOfCNumFmtElements.xlsx",
    "sc/qa/unit/data/xlsx/tdf134769.xlsx",
    "sc/qa/unit/data/xlsx/tdf167019.xlsx",
    "sc/qa/unit/data/xlsx/MissingPathExternal.xlsx",
    "sc/qa/unit/data/xlsx/empty_ext_defined_name.xlsx",
    "sc/qa/unit/data/xlsx/formats.xlsx",
    "sc/qa/unit/data/xlsx/forum-mso-en4-134670.xlsx",
    "sc/qa/unit/data/xlsx/column-style-autofilter.xlsx",
    "sc/qa/unit/data/xlsx/tdf130104_indent.xlsx",
]
LEGACY_DIRS = [("sw/qa/extras/ww8export/data", "doc"), ("sc/qa/unit/data/xls", "xls")]
ODF = {"docx": "odt", "doc": "odt", "xlsx": "ods", "xls": "ods"}


def legacy():
    picked = []
    for directory, suffix in LEGACY_DIRS:
        files = sorted(p for p in (LO / directory).glob(f"*.{suffix}") if 20_000 <= p.stat().st_size <= 200_000)
        picked += [str(p.relative_to(LO)) for p in files[:3]]
    return picked


def corpus():
    items = [{"name": Path(p).name, "path": LO / p, "origin": f"libreoffice-26-8/{p}"} for p in MS_AUTHORED + legacy()]
    items += [{"name": p.name, "path": p, "origin": f"wasm_sdk_probe/test-docs/r7-compat/{p.name}"}
              for p in sorted(R7.glob("*.docx"))]
    for item in items:
        item["sha256"] = hashlib.sha256(item["path"].read_bytes()).hexdigest()
        item["bytes"] = item["path"].stat().st_size
        item["suffix"] = item["path"].suffix[1:].lower()
    return items


def run(harness, item, arm, work):
    work.mkdir(parents=True)
    (work / "in").mkdir()
    (work / "out").mkdir()
    own = item["suffix"]
    name = item["name"] if arm == "true-name" else f"{Path(item['name']).stem}.{ODF[own]}"
    target = work / "in" / name
    shutil.copyfile(item["path"], target)
    formats = [own, f"own.{own}", ODF[own]] if arm == "true-name" else [ODF[own]]
    argv = [str(harness), str(PROGRAM), (work / "profile").as_uri(), str(target), str(work / "out"), ",".join(formats)]
    started = time.monotonic()
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=180)
        code, stdout, stderr = done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired as e:
        code, stdout, stderr = "timeout", (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), ""
    record = {"arm": arm, "inputName": name, "formats": formats, "argv": argv, "exit": code,
              "wallSeconds": round(time.monotonic() - started, 2), "stderrTail": stderr.splitlines()[-8:]}
    (work / "stderr.txt").write_text(stderr)
    try:
        record["report"] = json.loads(stdout)
    except json.JSONDecodeError:
        record["stdout"] = stdout[-2000:]
    pack(work, record)
    return record


def pack(work, record):
    shutil.rmtree(work / "profile", ignore_errors=True)
    shutil.rmtree(work / "in", ignore_errors=True)
    (work / "stderr.txt").unlink(missing_ok=True)  # its tail is in the record
    record["outputs"] = {}
    for path in sorted((work / "out").iterdir()):
        if path.name.startswith(".~lock"):
            record["outputs"][path.name] = "lock file left by a load that did not finish"
            path.unlink()
        elif path.name.endswith(".dump.txt"):
            path.with_name(path.name + ".gz").write_bytes(gzip.compress(path.read_bytes(), mtime=0))
            path.unlink()
        else:
            data = path.read_bytes()
            record["outputs"][path.name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            path.unlink()


def dump(path):
    packed = path.with_name(path.name + ".gz")
    if packed.exists():
        return gzip.decompress(packed.read_bytes()).decode("utf-8", errors="replace").splitlines()
    return path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else None


def compare(a, b):
    if a is None or b is None:
        return {"comparable": False}
    if a == b:
        return {"comparable": True, "equal": True, "lines": len(a)}
    sa, sb = set(a), set(b)
    return {"comparable": True, "equal": False, "lines": [len(a), len(b)], "onlyInFirst": len(sa - sb),
            "onlyInSecond": len(sb - sa), "firstOnlySample": sorted(sa - sb)[:5], "secondOnlySample": sorted(sb - sa)[:5]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--harness", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--only")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    harness = args.harness.resolve()
    items = [i for i in corpus() if not args.only or i["name"] == args.only]
    if not items:
        raise SystemExit("empty corpus: the QA tree or r7-compat moved")  # a census of zero is not a result
    report = {"schema": 1, "harnessSha256": hashlib.sha256(harness.read_bytes()).hexdigest(),
              "core": str(PROGRAM), "loCommit": subprocess.check_output(["git", "-C", str(LO), "rev-parse", "HEAD"], text=True).strip(),
              "uptime": subprocess.check_output(["uptime"], text=True).strip(), "files": []}
    for index, item in enumerate(items):
        entry = {k: (str(v) if isinstance(v, Path) else v) for k, v in item.items()}
        base = out / f"{index:02d}-{item['name']}"
        entry["runs"] = [run(harness, item, arm, base / arm) for arm in ("true-name", "odf-name")]
        own, odf = item["suffix"], ODF[item["suffix"]]
        t, o = base / "true-name/out", base / "odf-name/out"
        entry["compare"] = {
            "ownRoundTrip": compare(dump(t / "source.dump.txt"), dump(t / f"saved.{own}.dump.txt")),
            "ownFilterRoundTrip": compare(dump(t / "source.dump.txt"), dump(t / f"saved-own.{own}.dump.txt")),
            "odfRoundTrip": compare(dump(t / "source.dump.txt"), dump(t / f"saved.{odf}.dump.txt")),
            "odfNameVsTrueName": compare(dump(t / "source.dump.txt"), dump(o / "source.dump.txt")),
        }
        report["files"].append(entry)
        (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
        src = entry["runs"][0].get("report", {}).get("source", {})
        print(f"{item['name']}: load={src.get('ok')} filter={src.get('filter')!r} "
              f"odfName={entry['runs'][1].get('report', {}).get('source', {}).get('filter')!r} "
              f"own={entry['compare']['ownRoundTrip'].get('equal')} odf={entry['compare']['odfRoundTrip'].get('equal')} "
              f"sameUnderOdfName={entry['compare']['odfNameVsTrueName'].get('equal')}", flush=True)


if __name__ == "__main__":
    main()
