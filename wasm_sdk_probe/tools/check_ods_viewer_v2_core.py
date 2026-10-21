#!/usr/bin/env python3
"""Is the core tree the ODS viewer v2 will link against the core SPEC-M4-viewer-v2 section 2 asked for?

Written 2026-10-21, before the core was configured.

Two stages, each a gate the owner's build passes through:

  --stage configure   K-1, after autogen and BEFORE make: DB connectivity is on
                      (finding 158-B), dbaccess and the three SDBC drivers are
                      off, Calc and accessibility are as in build-a11y-gate0, and
                      autogen.input differs from that tree's by exactly the four
                      lines of section 2.1.  One second instead of an hour.
  --stage built       K-2, after make and BEFORE any link: the bridge table has
                      the add-in signatures (finding 159), the component list has
                      the forms collection, and the five link inputs exist.

Signatures are compared as WHOLE symbols.  Finding 159's first check was "the
file contains callVirtualFunction_didddd": wrong signature (SERIESSUM is didddi),
and a substring search finds it anyway inside callVirtualFunction_didddddd.

--self-test runs both stages against build-a11y-gate0 and requires them to be
red on the clauses that tree cannot pass (K-1a/K-1b, K-2a/K-2c) -- a check that
cannot turn red on a real tree that lacks the thing proves nothing.

Exit 0 only if every hard clause holds.  The report is JSON on stdout (and in
--report PATH when given).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
DEFAULT_BUILD = WORKSPACE / "wasm-lite" / "build-ods-viewer-v2"
REFERENCE = WORKSPACE / "wasm-lite" / "build-a11y-gate0"
EXPECTED_SIGNATURES = (WORKSPACE / "findings" / "evidence" / "m4-ods" / "phase-e" / "159-diagnosis"
                       / "bridgegen-offline" / "signatures-scaddins.txt")

# Section 2.1, in the order the spec lists them.
ADDED_AUTOGEN_LINES = [
    "--enable-database-connectivity",
    "--disable-firebird-sdbc",
    "--disable-mariadb-sdbc",
    "--disable-postgresql-sdbc",
]
# SERIESSUM, MULTINOMIAL, YEARFRAC, COUPDAYS (bridgegen-offline/README.md).
ADDIN_SIGNATURES = ["didddi", "diiii", "diiiii", "diiiiii"]
FORMS_CONSTRUCTOR = "com_sun_star_form_OFormsCollection_get_implementation"
SCADDINS_CONSTRUCTORS = [
    "scaddins_AnalysisAddIn_get_implementation",
    "scaddins_ScaDateAddIn_get_implementation",
    "scaddins_ScaPricingAddIn_get_implementation",
]
LINK_INPUTS = [
    "instdir/program/soffice.js.linkdeps",
    "instdir/program/soffice.data",
    "instdir/program/soffice.data.js.metadata",
    "workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link",
    "workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports",
]
SIZED = ["instdir/program/soffice.wasm", "instdir/program/soffice.data"]


class Missing(Exception):
    """A file the clause reads does not exist: the tree is not what the stage expects."""


def read(path: Path) -> str:
    if not path.is_file():
        raise Missing(str(path))
    return path.read_text(errors="replace")


def config_value(config_host_mk: str, name: str) -> str | None:
    match = re.search(rf"^export {re.escape(name)}=(.*)$", config_host_mk, re.M)
    return match.group(1).strip() if match else None


def define_value(header: str, name: str) -> str | None:
    match = re.search(rf"^#define {re.escape(name)}\s+(\S+)", header, re.M)
    return match.group(1) if match else None


def clause(results: list, key: str, ok: bool, hard: bool, observed, expected) -> None:
    results.append({"clause": key, "ok": bool(ok), "hard": hard, "observed": observed, "expected": expected})


def autogen_lines(path: Path) -> list[str]:
    return [line.strip() for line in read(path).splitlines() if line.strip()]


def stage_configure(build: Path, reference: Path) -> list:
    results: list = []
    features = read(build / "config_host" / "config_features.h")
    host_mk = read(build / "config_host.mk")
    strip_h = read(build / "config_host" / "config_wasm_strip.h")

    value = define_value(features, "HAVE_FEATURE_DBCONNECTIVITY")
    clause(results, "K-1a", value == "1", True, value, "1")

    build_type = (config_value(host_mk, "BUILD_TYPE") or "").split()
    clause(results, "K-1b", "DBCONNECTIVITY" in build_type, True,
           "DBCONNECTIVITY" in build_type, True)

    observed = {name: config_value(host_mk, name) for name in
                ("ENABLE_WASM_STRIP_DBACCESS", "ENABLE_FIREBIRD_SDBC", "ENABLE_MARIADBC", "BUILD_POSTGRESQL_SDBC")}
    expected = {"ENABLE_WASM_STRIP_DBACCESS": "TRUE", "ENABLE_FIREBIRD_SDBC": "",
                "ENABLE_MARIADBC": "", "BUILD_POSTGRESQL_SDBC": ""}
    clause(results, "K-1c", observed == expected, True, observed, expected)

    observed = {name: config_value(host_mk, name) for name in
                ("ENABLE_WASM_STRIP_CALC", "ENABLE_WASM_STRIP_ACCESSIBILITY")}
    observed["macro ENABLE_WASM_STRIP_ACCESSIBILITY"] = define_value(strip_h, "ENABLE_WASM_STRIP_ACCESSIBILITY")
    expected = {"ENABLE_WASM_STRIP_CALC": "", "ENABLE_WASM_STRIP_ACCESSIBILITY": "",
                "macro ENABLE_WASM_STRIP_ACCESSIBILITY": "0"}
    clause(results, "K-1d", observed == expected, True, observed, expected)

    mine = autogen_lines(build / "autogen.input")
    theirs = autogen_lines(reference / "autogen.input")
    added = [line for line in mine if line not in theirs]
    removed = [line for line in theirs if line not in mine]
    clause(results, "K-1e", added == ADDED_AUTOGEN_LINES and not removed, True,
           {"added": added, "removed": removed}, {"added": ADDED_AUTOGEN_LINES, "removed": []})
    return results


def signatures(path: Path) -> set[str]:
    return set(re.findall(r"\bcallVirtualFunction_([a-z]+)\b", read(path)))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stage_built(build: Path, reference: Path) -> list:
    results: list = []
    table = signatures(build / "workdir" / "CustomTarget" / "bridges" / "gcc3_wasm" / "generated-cxx.cxx")
    missing = [s for s in ADDIN_SIGNATURES if s not in table]
    clause(results, "K-2a", not missing, True, {"count": len(table), "missing": missing}, {"contains": ADDIN_SIGNATURES})

    expected = {line.strip().removeprefix("callVirtualFunction_") for line in read(EXPECTED_SIGNATURES).splitlines()
                if line.strip()}
    clause(results, "K-2b", table == expected, False,
           {"count": len(table), "extra": sorted(table - expected), "absent": sorted(expected - table)},
           {"count": len(expected), "file": str(EXPECTED_SIGNATURES.relative_to(WORKSPACE))})

    constructors = set(read(build / "workdir" / "CustomTarget" / "postprocess" / "services_constructors.list").split())
    wanted = [FORMS_CONSTRUCTOR] + SCADDINS_CONSTRUCTORS
    absent = [name for name in wanted if name not in constructors]
    clause(results, "K-2c", not absent, True, {"count": len(constructors), "absent": absent}, {"contains": wanted})

    dba = sorted(name for name in constructors if name.startswith("com_sun_star_comp_dba_"))
    clause(results, "K-2d", not dba, False, dba, [])

    inputs = {}
    for relative in LINK_INPUTS:
        path = build / relative
        inputs[relative] = ({"bytes": path.stat().st_size, "sha256": sha256(path)}
                            if path.is_file() and path.stat().st_size > 0 else None)
    clause(results, "K-2e", all(inputs.values()), True, inputs, "every file present and non-empty")

    sizes = {}
    for relative in SIZED:
        sizes[relative] = {tree.name: ((tree / relative).stat().st_size if (tree / relative).is_file() else None)
                           for tree in (build, reference)}
    clause(results, "K-2f", True, False, sizes, "recorded beside build-a11y-gate0 (judged at link, F-2)")
    return results


STAGES = {"configure": stage_configure, "built": stage_built}
# What build-a11y-gate0 must fail, per stage (section 2.3 / 2.4 red cases).
REFERENCE_MUST_FAIL = {"configure": {"K-1a", "K-1b"}, "built": {"K-2a", "K-2c"}}


def judge(build: Path, reference: Path, stage: str) -> dict:
    try:
        results = STAGES[stage](build, reference)
    except Missing as error:
        return {"stage": stage, "build": str(build), "ok": False, "missing": str(error), "clauses": []}
    ok = all(entry["ok"] for entry in results if entry["hard"])
    return {"stage": stage, "build": str(build), "ok": ok, "clauses": results}


def self_test(reference: Path) -> dict:
    report = {"selfTest": True, "reference": str(reference), "stages": {}, "ok": True}
    for stage, must_fail in REFERENCE_MUST_FAIL.items():
        verdict = judge(reference, reference, stage)
        failed = {entry["clause"] for entry in verdict["clauses"] if not entry["ok"]}
        stage_ok = bool(verdict["clauses"]) and must_fail <= failed and not verdict["ok"]
        report["stages"][stage] = {"failedClauses": sorted(failed), "mustFail": sorted(must_fail), "ok": stage_ok,
                                   "missing": verdict.get("missing")}
        report["ok"] = report["ok"] and stage_ok
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--stage", choices=sorted(STAGES))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        report = self_test(args.reference.resolve())
    elif args.stage:
        report = judge(args.build.resolve(), args.reference.resolve(), args.stage)
    else:
        parser.error("--stage or --self-test is required")
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
