#!/usr/bin/env python3
"""Check SPEC-M4-viewer-v3 K3 before linking ods-viewer-v3.

--stage built reads the core's actual constructor list, component XML sources,
and v2's existing bridge/forms/link-input checks. Size is record-only; F3-2
uses the projectedViewerGzipBytes field separately. Gzip is level 9, mtime 0.

--self-test requires today's pre-build tree to fail K3-a and pass K3-b. It then
adds all dba constructors to a SYNTHETIC list (a/b green), and one constructor
read from dbu.component (b red). It never edits the actual core tree. Run this
before the owner's build; it deliberately stops being applicable after dba is
built. Synthetic results do not establish a built core.

No files are written unless --report PATH is supplied. Exit 0 means all hard
clauses pass (or the requested self-test behaves as specified), 1 otherwise.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from check_ods_viewer_v2_core import (
    DEFAULT_BUILD, REFERENCE, WORKSPACE, Missing, clause, read, sha256, stage_built,
)

SOURCE = WORKSPACE / "libreoffice-26-8"
CONSTRUCTORS = Path("workdir/CustomTarget/postprocess/services_constructors.list")
COMPONENTS = {
    "dba": "dbaccess/util/dba.component",
    "dbu": "dbaccess/util/dbu.component",
    "sdbt": "dbaccess/util/sdbt.component",
    "dbaxml": "dbaccess/source/filter/xml/dbaxml.component",
    "rpt": "reportdesign/util/rpt.component",
    "rptui": "reportdesign/util/rptui.component",
}
FORBIDDEN = ("dbu", "sdbt", "rpt", "rptui")
CORE_GZIP_BASELINE = 49_572_266
VIEWER_GZIP_BASELINE = 49_153_029
GZIP_CAP = 52_428_800


def component_sources(source: Path) -> dict:
    sources = {}
    for name, relative in COMPONENTS.items():
        path = source / relative
        xml = ET.fromstring(read(path))
        constructors = sorted({node.attrib["constructor"] for node in xml.iter()
                               if node.attrib.get("constructor")})
        if name != "dbaxml" and not constructors:
            raise ValueError(f"No constructors in required component: {path}")
        sources[name] = {"path": str(path), "sha256": sha256(path), "constructors": constructors}
    return sources


def component_clauses(constructors: set[str], sources: dict) -> list:
    results: list = []
    required = set(sources["dba"]["constructors"])
    absent = sorted(required - constructors)
    clause(results, "K3-a", not absent, True,
           {"constructorCount": len(constructors), "absent": absent},
           {"contains": sorted(required)})
    present = {name: sorted(constructors.intersection(sources[name]["constructors"]))
               for name in FORBIDDEN}
    clause(results, "K3-b", not any(present.values()), True, present,
           "no constructors from dbu, sdbt, rpt or rptui")
    return results


def size_record(build: Path) -> dict:
    path = build / "instdir/program/soffice.wasm"
    if not path.is_file() or path.stat().st_size == 0:
        raise Missing(str(path))
    size = len(gzip.compress(path.read_bytes(), compresslevel=9, mtime=0))
    delta = size - CORE_GZIP_BASELINE
    projected = VIEWER_GZIP_BASELINE + delta
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path),
            "gzipLevel": 9, "gzipMtime": 0, "gzipBytes": size,
            "baselineCoreGzipBytes": CORE_GZIP_BASELINE,
            "baselineViewerGzipBytes": VIEWER_GZIP_BASELINE,
            "deltaGzipBytes": delta, "projectedViewerGzipBytes": projected,
            "viewerGzipCapBytes": GZIP_CAP, "projectedWithinCap": projected <= GZIP_CAP,
            "interpretation": "Projection only; measure the viewer itself after linking (F3-2)."}


def judge(build: Path, source: Path, reference: Path) -> dict:
    report = {"stage": "built", "build": str(build), "source": str(source),
              "ok": False, "clauses": []}
    try:
        sources = component_sources(source)
        path = build / CONSTRUCTORS
        constructors = set(read(path).split())
        report["componentSources"] = sources
        report["constructorsSha256"] = sha256(path)
        results = report["clauses"] = component_clauses(constructors, sources)
        inherited = [item for item in stage_built(build, reference)
                     if item["clause"] in ("K-2a", "K-2c", "K-2e")]
        clause(results, "K3-c", all(item["ok"] for item in inherited), True, inherited,
               "v2 K-2a, K-2c and K-2e all pass")
        report["sizeRecord"] = size_record(build)
        report["ok"] = all(item["ok"] for item in results if item["hard"])
    except (Missing, OSError, ValueError, ET.ParseError) as error:
        report["error"] = str(error)
    return report


def self_test(build: Path, source: Path) -> dict:
    report = {"selfTest": True, "build": str(build), "ok": False, "cases": {}}
    try:
        sources = component_sources(source)
        constructors = set(read(build / CONSTRUCTORS).split())
        report["componentSources"] = sources
        report["constructorsSha256"] = sha256(build / CONSTRUCTORS)
        complete = constructors.union(sources["dba"]["constructors"])
        injected = sources["dbu"]["constructors"][0]
        cases = (
            ("actual-pre-build", constructors, {"K3-a": False, "K3-b": True}, False),
            ("synthetic-dba-added", complete, {"K3-a": True, "K3-b": True}, True),
            ("synthetic-dbu-added", complete | {injected}, {"K3-a": True, "K3-b": False}, True),
        )
        for name, values, expected, synthetic in cases:
            results = component_clauses(values, sources)
            observed = {item["clause"]: item["ok"] for item in results}
            report["cases"][name] = {"synthetic": synthetic, "clauses": results,
                                     "expected": expected, "ok": observed == expected}
        report["injectedDbuConstructor"] = injected
        report["ok"] = all(case["ok"] for case in report["cases"].values())
    except (Missing, OSError, ValueError, ET.ParseError) as error:
        report["error"] = str(error)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stage", choices=["built"])
    mode.add_argument("--self-test", "--selftest", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = (self_test(args.build.resolve(), args.source.resolve()) if args.self_test else
              judge(args.build.resolve(), args.source.resolve(), args.reference.resolve()))
    report["checkerSha256"] = sha256(Path(__file__))
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output)
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
