#!/usr/bin/env python3
"""Build the ODS corpus and its manifest, over UNO with the system LibreOffice.

`handoff/PLAN-2026-09-03-ods-reading.md`, work item W3.  The manifest is the
gate's TRUTH SOURCE, so two things about it are load-bearing:

* **It is generated, not hand-written.**  `AGENTS.md` §1: a hand-kept
  enumeration cannot be a gate criterion, because its members live somewhere
  other than the claim.  This tool writes the manifest FROM the directory it
  just produced, so criterion G1 ("every file has an entry, every entry has a
  file, and the sha256s match") is tool-closed: drop a file in without
  regenerating and G1 reddens.
* **The synthetic fixtures carry their OWN expected text**, written by the
  generator that placed the cells -- not read back from the document it just
  wrote.  Reading the expectation out of the artifact under test is how an
  oracle stops being one.  The upstream fixtures get their expectations from
  the native oracle (W4) instead, and are marked `expectedFrom: "native-oracle"`
  with the field left null until that runs.

## The ladder, and why these sizes

The kill line is a peak `sbrk` (plan §4), so the ladder has to CROSS the
interesting region rather than sample near one end: 1 cell, 10k, 100k (the
class boundary the owner fixed), 100k of formulas rather than literals, ten
sheets sharing a total, and 1M as the deliberate over-the-line probe.  Charts
and images are separate because they allocate differently and the owner's class
excludes images -- they are measured and recorded, and they do not gate.

## What is deliberately NOT here

No `.xlsx`.  The a11y core's `calc.xcd` does not register
`calc_MS_Excel_2007_XML`, so an XLSX in this corpus would measure the absence of
a filter and report it as a spreadsheet defect.

Usage:
  create_ods_corpus.py --out test-docs/ods \
      --upstream ../libreoffice-26-8/sc/qa/unit/data/ods
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import uno

PROJECT = Path(__file__).resolve().parent.parent

# The owner's must-open class, 2026-09-03: up to 10 sheets, up to 100,000
# populated cells, no images.  Recorded here as data so the manifest can class
# every fixture without a human deciding per file.
CLASS_MAX_SHEETS = 10
CLASS_MAX_CELLS = 100_000


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def file_url(path: Path) -> str:
    return uno.systemPathToFileUrl(str(path.resolve()))


def property_value(name: str, value: object):
    prop = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    prop.Name = name
    prop.Value = value
    return prop


def connect(port: int, attempts: int = 120):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    url = (f"uno:socket,host=127.0.0.1,port={port};"
           "urp;StarOffice.ComponentContext")
    for _ in range(attempts):
        try:
            return resolver.resolve(url)
        except Exception:
            time.sleep(0.25)
    raise RuntimeError(f"unable to connect to LibreOffice on port {port}")


def new_calc(desktop):
    hidden = (property_value("Hidden", True),)
    return desktop.loadComponentFromURL(
        "private:factory/scalc", "_blank", 0, hidden)


def store(doc, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.storeToURL(file_url(path), (property_value("FilterName", "calc8"),))


def sheet_names(doc) -> list[str]:
    return list(doc.Sheets.ElementNames)


def ensure_sheets(doc, names: list[str]) -> None:
    """Leave the document with exactly `names`, in order.

    A new Calc document starts with one sheet whose name is locale-dependent,
    so the names are SET rather than assumed -- G5 compares `part_name` against
    the manifest, and a manifest that recorded whatever the generator's locale
    produced would make that criterion measure the generator's locale.
    """
    sheets = doc.Sheets
    while sheets.Count > 1:
        sheets.removeByName(sheets.ElementNames[sheets.Count - 1])
    sheets.getByIndex(0).Name = names[0]
    for name in names[1:]:
        sheets.insertNewByName(name, sheets.Count)


# ---------------------------------------------------------- the expectations
#
# DECLARED SEPARATELY FROM THE BUILDING, and that separation was forced.  The
# first version held these inside the makers, so `--skip-ladder` -- which
# regenerates the manifest WITHOUT rebuilding the fixtures -- silently produced
# a manifest with no generator truth in it at all: four expectations the corpus
# depends on, gone, and nothing said so.
#
# The truth source has to be reconstructible without re-running the thing it
# describes.  Every maker below returns one of these when handed `desktop=None`,
# so describing and building are the same statement read two ways.

EXPECT_EMPTY_ONE_SHEET = {
    "sheets": [{"name": "Sheet1", "text": ""}], "cells": 0,
    "note": "G4's empty control: the tile of this sheet is what a 'nothing was "
            "painted' tile must equal",
}
EXPECT_ONE_CELL = {
    "sheets": [{"name": "Sheet1", "text": "A1-ONLY"}], "cells": 1,
    "note": "G4's content control: this tile must NOT equal the empty one",
}
EXPECT_THREE_DISTINCT = {
    "sheets": [{"name": "Alpha", "text": "SHEET-0"},
               {"name": "Beta", "text": "SHEET-1"},
               {"name": "Gamma", "text": "SHEET-2"}],
    "cells": 3,
    "note": "G5's discriminator: three parts whose tiles must be pairwise "
            "DISTINCT",
}
EXPECT_THREE_IDENTICAL = {
    "sheets": [{"name": n, "text": "SAME-ON-EVERY-SHEET"}
               for n in ("One", "Two", "Three")],
    "cells": 3,
    "note": "G5's control: three parts whose tiles must be pairwise IDENTICAL. "
            "Without it an instrument that returns the same tile for every part "
            "would pass the distinct case by accident and fail nothing",
}


def expect_numeric(cells: int) -> dict:
    return {"sheets": [{"name": "Data", "text": None}], "cells": cells,
            "expectedFrom": "native-oracle",
            "note": f"{cells} numeric cells; the expected text is read by the "
                    "native oracle rather than carried inline"}


def expect_formula(cells: int) -> dict:
    return {"sheets": [{"name": "Chain", "text": None}], "cells": cells,
            "expectedFrom": "native-oracle",
            "note": "a dependency chain, not literals: the formula tree is a "
                    "different allocation shape from the cell store, and the "
                    "kill line is about peak sbrk rather than file size"}


def expect_ten_sheets(per_sheet: int) -> dict:
    return {"sheets": [{"name": f"S{i}", "text": None} for i in range(10)],
            "cells": 10 * per_sheet, "expectedFrom": "native-oracle",
            "note": "the class boundary on the SHEET axis: ten sheets is the "
                    "owner's maximum"}


# --------------------------------------------------------------- the fixtures
#
# Each maker returns `(relative path, expected)` where `expected` is
#   {"sheets": [{"name": str, "text": str}], "cells": int, "note": str}
# and `text` is what `.uno:SelectAll` + getTextSelection("text/plain") must
# return for that sheet -- tab-separated columns, newline-separated rows, which
# is what LibreOffice's plain-text selection of a cell range produces.


def grid_text(rows: list[list[str]]) -> str:
    return "\n".join("\t".join(row) for row in rows)


def make_empty_one_sheet(desktop, out: Path):
    if desktop is None:
        return ("ladder/empty-one-sheet.ods", EXPECT_EMPTY_ONE_SHEET)
    doc = new_calc(desktop)
    try:
        ensure_sheets(doc, ["Sheet1"])
        store(doc, out / "ladder" / "empty-one-sheet.ods")
    finally:
        doc.close(False)
    return ("ladder/empty-one-sheet.ods", EXPECT_EMPTY_ONE_SHEET)


def make_one_cell(desktop, out: Path):
    if desktop is None:
        return ("ladder/one-cell-a1.ods", EXPECT_ONE_CELL)
    doc = new_calc(desktop)
    try:
        ensure_sheets(doc, ["Sheet1"])
        doc.Sheets.getByIndex(0).getCellByPosition(0, 0).setString("A1-ONLY")
        store(doc, out / "ladder" / "one-cell-a1.ods")
    finally:
        doc.close(False)
    return ("ladder/one-cell-a1.ods", EXPECT_ONE_CELL)


def make_three_sheets(desktop, out: Path, distinct: bool):
    name = "three-sheets-distinct" if distinct else "three-sheets-identical"
    names = ["Alpha", "Beta", "Gamma"] if distinct else ["One", "Two", "Three"]
    if desktop is None:
        return (f"ladder/{name}.ods",
                EXPECT_THREE_DISTINCT if distinct else EXPECT_THREE_IDENTICAL)
    doc = new_calc(desktop)
    sheets_expected = []
    try:
        ensure_sheets(doc, names)
        for index, sheet_name in enumerate(names):
            sheet = doc.Sheets.getByIndex(index)
            value = f"SHEET-{index}" if distinct else "SAME-ON-EVERY-SHEET"
            sheet.getCellByPosition(0, 0).setString(value)
            sheets_expected.append({"name": sheet_name, "text": value})
        store(doc, out / "ladder" / f"{name}.ods")
    finally:
        doc.close(False)
    return (f"ladder/{name}.ods",
            EXPECT_THREE_DISTINCT if distinct else EXPECT_THREE_IDENTICAL)


def make_numeric(desktop, out: Path, cells: int, label: str):
    """`cells` numeric cells down one column, in one sheet."""
    if desktop is None:
        return (f"ladder/{label}.ods", expect_numeric(cells))
    doc = new_calc(desktop)
    try:
        ensure_sheets(doc, ["Data"])
        sheet = doc.Sheets.getByIndex(0)
        # setDataArray in one call: cell-by-cell over 100k cells takes minutes
        # of UNO round-trips, and the fixture is not what is being measured.
        data = tuple((float(i),) for i in range(cells))
        sheet.getCellRangeByPosition(0, 0, 0, cells - 1).setDataArray(data)
        store(doc, out / "ladder" / f"{label}.ods")
    finally:
        doc.close(False)
    return (f"ladder/{label}.ods", expect_numeric(cells))


def make_formula(desktop, out: Path, cells: int):
    if desktop is None:
        return ("ladder/formula-100k.ods", expect_formula(cells))
    doc = new_calc(desktop)
    try:
        ensure_sheets(doc, ["Chain"])
        sheet = doc.Sheets.getByIndex(0)
        sheet.getCellByPosition(0, 0).setValue(1.0)
        formulas = tuple((f"=A{i}+1",) for i in range(1, cells))
        sheet.getCellRangeByPosition(0, 1, 0, cells - 1).setFormulaArray(formulas)
        store(doc, out / "ladder" / "formula-100k.ods")
    finally:
        doc.close(False)
    return ("ladder/formula-100k.ods", expect_formula(cells))


def make_ten_sheets(desktop, out: Path, per_sheet: int):
    names = [f"S{i}" for i in range(10)]
    if desktop is None:
        return ("ladder/ten-sheets-10k.ods", expect_ten_sheets(per_sheet))
    doc = new_calc(desktop)
    try:
        ensure_sheets(doc, names)
        for index in range(10):
            sheet = doc.Sheets.getByIndex(index)
            data = tuple((float(index * per_sheet + i),) for i in range(per_sheet))
            sheet.getCellRangeByPosition(0, 0, 0, per_sheet - 1).setDataArray(data)
        store(doc, out / "ladder" / "ten-sheets-10k.ods")
    finally:
        doc.close(False)
    return ("ladder/ten-sheets-10k.ods", expect_ten_sheets(per_sheet))


LADDER = [
    ("empty-one-sheet", lambda d, o: make_empty_one_sheet(d, o)),
    ("one-cell-a1", lambda d, o: make_one_cell(d, o)),
    ("three-sheets-distinct", lambda d, o: make_three_sheets(d, o, True)),
    ("three-sheets-identical", lambda d, o: make_three_sheets(d, o, False)),
    ("numeric-10k", lambda d, o: make_numeric(d, o, 10_000, "numeric-10k")),
    ("numeric-100k", lambda d, o: make_numeric(d, o, 100_000, "numeric-100k")),
    ("formula-100k", lambda d, o: make_formula(d, o, 100_000)),
    ("ten-sheets-10k", lambda d, o: make_ten_sheets(d, o, 10_000)),
    ("numeric-1m", lambda d, o: make_numeric(d, o, 1_000_000, "numeric-1m")),
]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(expected: dict) -> str:
    """In or out of the owner's must-open class, decided from data."""
    sheets = len(expected.get("sheets") or [])
    cells = expected.get("cells") or 0
    if expected.get("expect") == "refused":
        return "refusal"
    if expected.get("hasImages"):
        return "out-of-class:images"
    if sheets > CLASS_MAX_SHEETS:
        return f"out-of-class:sheets={sheets}"
    if cells is not None and cells > CLASS_MAX_CELLS:
        return f"out-of-class:cells={cells}"
    if cells is None:
        # An upstream fixture whose cell count nobody counted.  It is IN the
        # class on the sheet axis and UNKNOWN on the cell axis, and saying so is
        # the honest answer -- "must-open" would be a claim the corpus cannot
        # support, and "out-of-class" would quietly excuse a file from the gate.
        return "in-class-on-sheets-cells-uncounted"
    return "must-open"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=PROJECT / "test-docs" / "ods")
    parser.add_argument("--upstream", type=Path, default=None,
                        help="a directory of upstream .ods fixtures to copy in "
                             "and register; their expectations come from the "
                             "native oracle, not from here")
    parser.add_argument("--soffice",
                        default=shutil.which("soffice") or "soffice")
    parser.add_argument("--from-oracle", type=Path, default=None,
                        help="an oracle.jsonl from tools/run_ods_native_oracle.sh; "
                             "fills in sheet counts, names and per-sheet text "
                             "for the entries this generator cannot know")
    parser.add_argument("--skip-ladder", action="store_true",
                        help="regenerate the manifest only, without rebuilding "
                             "the synthetic fixtures")
    args = parser.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    version = subprocess.run([args.soffice, "--version"], check=True,
                             capture_output=True, text=True).stdout.strip()
    # ALWAYS describe; build only when asked.  The manifest must be
    # regenerable from the corpus that exists.
    expectations: dict[str, dict] = {}
    for label, maker in LADDER:
        rel, expected = maker(None, out)
        expectations[rel] = expected

    if not args.skip_ladder:
        port = free_port()
        with tempfile.TemporaryDirectory(prefix="ods-corpus-lo-") as profile:
            accept = (f"socket,host=127.0.0.1,port={port};"
                      "urp;StarOffice.ServiceManager")
            process = subprocess.Popen(
                [args.soffice, "--headless", "--nologo", "--nodefault",
                 "--nofirststartwizard", "--norestore",
                 f"-env:UserInstallation={file_url(Path(profile))}",
                 f"--accept={accept}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                context = connect(port)
                desktop = context.ServiceManager.createInstanceWithContext(
                    "com.sun.star.frame.Desktop", context)
                for label, maker in LADDER:
                    print(f"  building {label} ...", flush=True)
                    rel, expected = maker(desktop, out)
                    expectations[rel] = expected
                try:
                    desktop.terminate()
                except Exception:
                    pass
            finally:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()

    if args.upstream is not None:
        target = out / "upstream"
        target.mkdir(parents=True, exist_ok=True)
        copied = 0
        for src in sorted(args.upstream.glob("*.ods")):
            shutil.copy2(src, target / src.name)
            copied += 1
        print(f"  copied {copied} upstream fixtures")

    # ---- the native oracle's answers, if given ---------------------------
    #
    # ONE TOOL OWNS THE MANIFEST.  The oracle writes its own file and never
    # touches this one; the fold happens here, so there is a single place where
    # a manifest entry can come into being and a single place to look when one
    # is wrong.
    #
    # The oracle's answers are marked `expectedFrom: "native-oracle"` and stay
    # distinguishable from the generator's for the life of the corpus: they were
    # produced by READING a document, not by writing one, and a reader that
    # forgets the difference will eventually compare the candidate against an
    # expectation the candidate's own family produced.
    oracle: dict[str, dict] = {}
    if args.from_oracle is not None:
        for line in args.from_oracle.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            key = record["file"].split("/test-docs/ods/")[-1]
            oracle[key] = record

    # ---- the manifest, generated FROM the directory ----------------------
    entries = []
    for path in sorted(out.rglob("*.ods")):
        rel = str(path.relative_to(out))
        expected = expectations.get(rel)
        if expected is None:
            expected = {
                "sheets": None, "cells": None,
                "expectedFrom": "native-oracle",
                "note": "upstream fixture: sheet count and per-sheet text are "
                        "filled in by tools/ods_native_oracle, and until then "
                        "this entry cannot satisfy G2 or G3",
            }
        seen = oracle.get(rel)
        if seen is not None and expected.get("sheets") is None:
            if not seen.get("loaded"):
                # A file the ENGINE ITSELF cannot open is not a product defect
                # waiting to be found; it is an entry whose required outcome is
                # a typed refusal.  G2 has a clause for exactly this, and the
                # reason is carried so nobody has to rediscover it.
                expected = {
                    "sheets": [], "cells": None,
                    "expect": "refused",
                    "refusedReason": str(seen.get("error"))[:200],
                    "expectedFrom": "native-oracle",
                    "note": "the native oracle on the same commit could not "
                            "open this either, so the candidate is required to "
                            "REFUSE it in a typed way rather than to open it",
                }
            else:
                expected = {
                    "sheets": [{"name": sheet["name"], "text": sheet["text"]}
                               for sheet in seen.get("sheets") or []],
                    "cells": None,
                    "expectedFrom": "native-oracle",
                    "note": "sheet count, names and per-sheet text read by "
                            "tools/ods_native_oracle on the same commit the "
                            "candidate is built from",
                }

        entries.append({
            "path": rel,
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
            "sheets": (len(expected["sheets"])
                       if expected.get("sheets") is not None else None),
            "sheetNames": ([s["name"] for s in expected["sheets"]]
                           if expected.get("sheets") is not None else None),
            "expectedText": ({s["name"]: s["text"] for s in expected["sheets"]}
                             if expected.get("sheets") is not None else None),
            "cells": expected.get("cells"),
            "expectedFrom": expected.get("expectedFrom", "generator"),
            "expect": expected.get("expect", "opens"),
            "refusedReason": expected.get("refusedReason"),
            "class": (classify(expected)
                      if expected.get("sheets") is not None else "unclassified"),
            "note": expected.get("note"),
        })

    manifest = {
        "schemaVersion": 1,
        "release": "m4-ods-corpus",
        "generatedBy": "tools/create_ods_corpus.py",
        "sofficeVersion": version,
        "mustOpenClass": {"maxSheets": CLASS_MAX_SHEETS,
                          "maxCells": CLASS_MAX_CELLS, "images": False,
                          "decidedBy": "owner, 2026-09-03"},
        "why": "This file is the gate's truth source and is GENERATED from the "
               "directory it describes. A hand-kept list cannot be a gate "
               "criterion (AGENTS.md §1): adding a file without regenerating "
               "must redden G1, and it does, because G1 compares this list "
               "against the directory in both directions.",
        "entries": entries,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"\n{len(entries)} entries -> {out / 'manifest.json'}")
    inline = sum(1 for e in entries if e["expectedFrom"] == "generator")
    print(f"  {inline} carry generator truth; "
          f"{len(entries) - inline} await the native oracle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
