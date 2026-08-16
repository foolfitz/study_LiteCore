#!/usr/bin/env python3
"""Judge D3's corpus half offline, against criteria frozen before it ran.

The page collects; this applies `e2/validation-matrix-v1.json`'s D3 corpus
oracle and the cell-level detail registered in
findings/evidence/sdk-e2/e2-c-validation/d3-corpus/PREDICTION.md.  No browser is
involved, so the verdict can be recomputed from the files at any time.

What "the edit happened" means here is deliberately structural.  Finding 048 is
the reason: eight cells once reported `verified-format-readback` while acting on
a paragraph nobody had asked about, and every completion code and count agreed
with them.  So the check is "the anchor's own paragraph is inside a
`<text:list>` in the saved document and was not in one in the fixture" -- read
out of the bytes, not out of the page's report.

Usage:
  analyze_e2_c_d3_corpus.py RUN_DIR [RUN_DIR ...] [--carried DIR] [--output F]
  analyze_e2_c_d3_corpus.py --self-test RUN_DIR
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1_support import inspect_odt  # noqa: E402
from r7_support import desktop_pdf_roundtrip  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
DRAW_NS = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"

# The fixture each cell opened, and where it lives.  Kept here rather than read
# from the run so that a run naming the wrong fixture cannot quietly redefine
# what it was compared against.
FIXTURES = {
    "l0-t1": PROJECT / "test-docs/r7-compat/l0-t1-plain-zh.odt",
    "l0-t2": PROJECT / "test-docs/r7-compat/l0-t2-styled.odt",
    "l0-t3": PROJECT / "test-docs/r7-compat/l0-t3-long.odt",
    "l1-review": PROJECT / "test-docs/r7-compat/l1-review.odt",
    "l4-stress-100": PROJECT / "test-docs/r7-compat/l4-stress-100.odt",
    "list-contexts": PROJECT / "test-docs/e1/list-contexts.odt",
    "list-split": PROJECT / "test-docs/e2/list-split.odt",
}

# Anchors that must survive, per fixture.
#
# Patterns for the paginated corpora, because naming only pages 1 and 22 would
# let a save that dropped pages 12-21 pass, and that is exactly the loss this
# phase is for.  The patterns end in fixed text so they cannot run on.
#
# LITERAL strings for the list corpora, and that is a correction: the first
# version used `E1-LC-[A-Z-]+`, which is greedy and ran into whatever followed.
# It extracted `E1-LC-BULLET-ONEE` from the fixture and `E1-LC-HEADINGE` from
# the save, then reported the mismatch as two lost anchors.  A criterion whose
# answer depends on the text NEXT to the anchor is measuring itself.
ANCHOR_PATTERNS = {
    "l0-t1": [r"Final line：ODT round-trip 完整性檢查。"],
    "l0-t2": [r"文件結尾：請確認表格、圖片、註解與標題樣式均保留。"],
    "l0-t3": [r"第 \d+ 頁：長文件記憶體與效能測試"],
    "l1-review": [r"Lorem ipsum"],
    "l4-stress-100": [r"R7 stress page \d+ 頁面錨點"],
    "list-contexts": [re.escape(a) for a in (
        "E1-LC-HEADING", "E1-LC-ISOLATED", "E1-LC-BULLET-ONE",
        "E1-LC-BULLET-TWO", "E1-LC-BETWEEN", "E1-LC-NUMBER-ONE",
        "E1-LC-NUMBER-TWO", "E1-LC-END")],
    # Read out of the fixture rather than guessed: the first attempt named
    # FIRST/MID/LAST, and only MID exists.
    "list-split": [re.escape(a) for a in (
        "E2-LS-HEADING", "E2-LS-BEFORE", "E2-LS-ONE", "E2-LS-MID",
        "E2-LS-THREE", "E2-LS-AFTER", "E2-LS-BULLET-ONE", "E2-LS-BULLET-MID",
        "E2-LS-BULLET-THREE", "E2-LS-END")],
}

# A harness that types into a corpus document would leave one of these behind.
# This round never types, so any hit is a leak.
FORBIDDEN = re.compile(r"E2C-[A-Z0-9-]+")


def structure_counts(path: Path) -> dict[str, int]:
    """Counted from content.xml, not from the page's report."""
    if not zipfile.is_zipfile(path):
        return {}
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("content.xml"))
    tags = {
        "paragraphs": f"{{{TEXT_NS}}}p",
        "headings": f"{{{TEXT_NS}}}h",
        "lists": f"{{{TEXT_NS}}}list",
        "listItems": f"{{{TEXT_NS}}}list-item",
        "annotations": f"{{{OFFICE_NS}}}annotation",
        "trackedChangeRegions": f"{{{TEXT_NS}}}changed-region",
        "frames": f"{{{DRAW_NS}}}frame",
        "images": f"{{{DRAW_NS}}}image",
        "tables": f"{{{TABLE_NS}}}table",
    }
    nodes = list(root.iter())
    return {name: sum(node.tag == tag for node in nodes) for name, tag in tags.items()}


def anchor_counts(text: str, fixture: str) -> dict[str, int]:
    return {pattern: len(re.findall(pattern, text))
            for pattern in ANCHOR_PATTERNS.get(fixture, [])}


def body_bytes(path: Path) -> bytes | None:
    """`<office:body>` only.  Two saves of the same document differ in metadata
    (generator stamp, edit duration) for reasons that say nothing about the
    content, and comparing whole files would report those as differences."""
    if not zipfile.is_zipfile(path):
        return None
    with zipfile.ZipFile(path) as archive:
        content = archive.read("content.xml")
    start = content.find(b"<office:body")
    end = content.find(b"</office:body>")
    if start < 0 or end < 0:
        return None
    return content[start:end + len(b"</office:body>")]


def anchor_paragraph_is_in_a_list(path: Path, anchor: str) -> bool | None:
    """Is the paragraph carrying `anchor` inside a `<text:list>`?

    None when the anchor is not found at all -- which is a different answer from
    False and must not be folded into it.
    """
    if not zipfile.is_zipfile(path):
        return None
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("content.xml"))
    parents = {child: parent for parent in root.iter() for child in parent}
    found = False
    for node in root.iter():
        if node.tag not in (f"{{{TEXT_NS}}}p", f"{{{TEXT_NS}}}h"):
            continue
        if anchor not in "".join(node.itertext()):
            continue
        found = True
        walker = parents.get(node)
        while walker is not None:
            if walker.tag == f"{{{TEXT_NS}}}list":
                return True
            walker = parents.get(walker)
    return False if found else None


def judge_cell(cell: dict, saved: Path, fixture_path: Path,
               skip_desktop: bool = False, control: Path | None = None) -> dict:
    fixture = cell.get("fixture")
    anchor = cell.get("anchor")
    report: dict = {"cell": cell.get("cell"), "fixture": fixture, "anchor": anchor,
                    "checks": {}, "notes": []}

    if cell.get("error"):
        report["checks"]["dispatched"] = False
        report["error"] = cell["error"]
        report["pass"] = False
        return report

    report["checks"]["dispatched"] = bool(cell.get("result"))
    report["checks"]["caretProved"] = cell.get("caretArrivedAfterMs") is not None

    after = inspect_odt(saved)
    before = inspect_odt(fixture_path)
    report["savedExists"] = after["exists"]
    report["checks"]["zip"] = bool(after["zip"] and after["crc"])
    report["checks"]["xml"] = bool(after["xml"])

    before_anchors = anchor_counts(before["text"], fixture)  # against the fixture
    after_anchors = anchor_counts(after["text"], fixture)
    report["anchors"] = {"before": before_anchors, "after": after_anchors}
    report["checks"]["anchorsPreserved"] = (
        bool(before_anchors) and before_anchors == after_anchors)

    # Structure is compared against the CONTROL -- the same document opened and
    # saved with no action -- and not against the fixture on disk.
    #
    # Measured on 2026-08-16, and the reason this is a correction rather than a
    # relaxation: `l4-stress-100` carries 100 `<draw:frame
    # text:anchor-type="as-char">` directly under `<office:text>`, and both
    # LibreOffice builds on this machine drop every one of them on a plain
    # ODT->ODT convert with no editing at all (system 26.8 and
    # build-native-26-8, frames 100 -> 0 each).  Compared against the fixture,
    # every cell touching that document reports content loss caused by an edit
    # that did not cause it.  The control is the only comparison that can tell
    # a corpus defect from a product defect -- the same lesson L6 learned in the
    # list half, at a much larger size.
    baseline_path = control if control and control.is_file() else fixture_path
    report["structureBaseline"] = ("control" if baseline_path is control
                                   else "fixture")
    before_structure = structure_counts(baseline_path)
    after_structure = structure_counts(saved)
    report["structure"] = {"before": before_structure, "after": after_structure}
    # Lists and list items are SUPPOSED to move -- that is the action.  Every
    # other structural count must be untouched.
    moving = {"lists", "listItems", "paragraphs", "headings"}
    report["structureDifferences"] = {
        name: [before_structure.get(name), after_structure.get(name)]
        for name in before_structure
        if name not in moving and before_structure.get(name) != after_structure.get(name)
    }
    report["checks"]["structurePreserved"] = not report["structureDifferences"]

    report["checks"]["editHappened"] = (
        anchor_paragraph_is_in_a_list(saved, anchor) is True
        and anchor_paragraph_is_in_a_list(fixture_path, anchor) is False)

    leaked = sorted(set(FORBIDDEN.findall(after["text"])))
    report["forbiddenFound"] = leaked
    report["checks"]["noForbiddenContent"] = not leaked

    if skip_desktop:
        report["checks"]["desktopReopen"] = None
        report["notes"].append("desktop round trip skipped (--skip-desktop)")
    else:
        with tempfile.TemporaryDirectory(prefix="d3-corpus-") as directory:
            desktop = desktop_pdf_roundtrip(saved, Path(directory) / "out.pdf")
        report["desktop"] = {"returnCode": desktop.get("returnCode"),
                             "pass": desktop.get("pass")}
        report["checks"]["desktopReopen"] = bool(desktop.get("pass"))

    report["pass"] = all(value for value in report["checks"].values()
                         if value is not None)
    return report


def load_run(run: Path) -> dict:
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    result["_dir"] = str(run)
    return result


def judge_run(run: Path, skip_desktop: bool = False) -> dict:
    result = load_run(run)
    cells = {name: value for name, value in (result.get("cells") or {}).items()
             if name != "d0-inventory"}
    reports = {}
    controls = {cell.get("fixture"): run / "saved" / f"{name}-after.odt"
                for name, cell in cells.items() if cell.get("control")}
    for name, cell in cells.items():
        if cell.get("control"):
            continue
        saved = run / "saved" / f"{name}-after.odt"
        fixture_path = FIXTURES.get(cell.get("fixture"))
        if fixture_path is None:
            reports[name] = {"cell": name, "pass": False,
                             "error": {"code": "UNKNOWN_FIXTURE",
                                       "message": str(cell.get("fixture"))}}
            continue
        reports[name] = judge_cell(cell, saved, fixture_path, skip_desktop,
                                   controls.get(cell.get("fixture")))
    return {
        "run": str(run),
        "browser": result.get("browserName"),
        "profile": result.get("artifact", {}).get("profile"),
        "wasmSha256": result.get("artifact", {}).get("wasmSha256"),
        "attributionConsistent": result.get("attribution", {}).get("consistent"),
        "complete": result.get("complete"),
        "cells": reports,
        "pass": bool(result.get("complete"))
                and bool(result.get("attribution", {}).get("consistent"))
                and all(report["pass"] for report in reports.values()),
    }


def judge_carried(directory: Path, skip_desktop: bool = False) -> dict:
    """`d3-list-contexts` and `d3-list-split`: the matrix words them as CARRYING
    the L cells, so the structural criteria are applied to the documents that
    round already saved rather than to a fresh round of the same thing."""
    out: dict = {"directory": str(directory), "cells": {}}
    for saved in sorted(directory.rglob("saved/*-after.odt")):
        label = saved.stem.removesuffix("-after")
        if label == "L7":
            fixture = "list-split"
        elif label.startswith("L"):
            fixture = "list-contexts"
        else:
            continue
        after = inspect_odt(saved)
        before = inspect_odt(FIXTURES[fixture])
        before_anchors = anchor_counts(before["text"], fixture)  # against the fixture
        after_anchors = anchor_counts(after["text"], fixture)
        control_path = saved.parent / "L6C-after.odt"
        structure_before = structure_counts(
            control_path if (fixture == "list-contexts" and control_path.is_file())
            else FIXTURES[fixture])
        structure_after = structure_counts(saved)
        moving = {"lists", "listItems", "paragraphs", "headings"}
        differences = {
            name: [structure_before.get(name), structure_after.get(name)]
            for name in structure_before
            if name not in moving
            and structure_before.get(name) != structure_after.get(name)
        }
        checks = {
            "zip": bool(after["zip"] and after["crc"]),
            "xml": bool(after["xml"]),
            "anchorsPreserved": bool(before_anchors)
                                and before_anchors == after_anchors,
            "structurePreserved": not differences,
            "noForbiddenContent": not FORBIDDEN.findall(after["text"]),
        }
        if not skip_desktop:
            with tempfile.TemporaryDirectory(prefix="d3-carried-") as tmp:
                desktop = desktop_pdf_roundtrip(saved, Path(tmp) / "out.pdf")
            checks["desktopReopen"] = bool(desktop.get("pass"))
        key = f"{saved.parent.parent.name}:{label}"
        out["cells"][key] = {"fixture": fixture, "checks": checks,
                             "structureDifferences": differences,
                             "anchors": {"before": before_anchors,
                                         "after": after_anchors},
                             "pass": all(checks.values())}
    out["pass"] = bool(out["cells"]) and all(c["pass"] for c in out["cells"].values())
    return out


def compare_browsers(runs: list[dict], directories: list[Path]) -> dict:
    """Same verdict per cell, and the same `<office:body>` bytes."""
    if len(runs) < 2:
        return {"compared": False,
                "why": "one browser only; SPEC E2-C requires both to agree"}
    names = sorted(set().union(*[set(run["cells"]) for run in runs]))
    per_cell = {}
    for name in names:
        verdicts = [run["cells"].get(name, {}).get("pass") for run in runs]
        bodies = []
        for directory in directories:
            saved = directory / "saved" / f"{name}-after.odt"
            bodies.append(body_bytes(saved) if saved.is_file() else None)
        # Reported, never used as the pass criterion.  P-C5 was registered as
        # "byte-identical" and that is how it is scored; this second number
        # exists so a failure says WHAT differed instead of only that something
        # did.  `c-l1-review` is the case: its two bodies differ only in
        # auto-generated tracked-change ids (`ct311...` vs `ct2888...`), are the
        # same length, and carry identical visible text.  Turning that into a
        # pass here would be deciding the criterion after seeing the result;
        # the narrower rule belongs in the second round's matrix, registered
        # before it runs.
        normalised = [re.sub(rb"ct\d+", b"ctN", b) if b is not None else None
                      for b in bodies]
        per_cell[name] = {
            "verdicts": verdicts,
            "verdictsAgree": len(set(verdicts)) == 1,
            "bodiesIdentical": len({b for b in bodies}) == 1 and bodies[0] is not None,
            "bodiesIdenticalAfterIdNormalisation":
                len({b for b in normalised}) == 1 and normalised[0] is not None,
        }
    return {
        "compared": True,
        "cells": per_cell,
        "pass": all(entry["verdictsAgree"] and entry["bodiesIdentical"]
                    for entry in per_cell.values()),
    }


def summarise(runs: list[dict], comparison: dict, carried: dict | None) -> dict:
    return {
        "schemaVersion": 1,
        "release": "spec-e2c-d3-corpus",
        "predictionFile":
            "findings/evidence/sdk-e2/e2-c-validation/d3-corpus/PREDICTION.md",
        "runs": runs,
        "browserComparison": comparison,
        "carried": carried,
        "pass": all(run["pass"] for run in runs)
                and bool(comparison.get("pass"))
                and (carried is None or bool(carried.get("pass"))),
    }


def self_test(run: Path) -> int:
    """Every predicate that can turn the verdict has to be shown to move it.

    The mutations run against COPIES in a temporary directory; nothing under
    findings/ is touched.  Desktop round trips are skipped here -- they take
    minutes per document and none of these mutations is about them.
    """
    failures: list[str] = []
    ran: list[str] = []
    baseline = judge_run(run, skip_desktop=True)

    def check(name: str, condition: bool, detail: str = "") -> None:
        ran.append(name)
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    check("the recorded run is judged at all", bool(baseline["cells"]))

    with tempfile.TemporaryDirectory(prefix="d3-corpus-self-") as directory:
        root = Path(directory)

        def copy_run() -> Path:
            import shutil
            target = root / f"case-{len(list(root.iterdir()))}"
            shutil.copytree(run, target)
            return target

        # 1. a cell that never dispatched cannot pass
        case = copy_run()
        result = json.loads((case / "result.json").read_text())
        first = next(name for name in result["cells"] if name != "d0-inventory")
        result["cells"][first]["error"] = {"code": "PROBE", "message": "probe"}
        (case / "result.json").write_text(json.dumps(result))
        mutated = judge_run(case, skip_desktop=True)
        check("a cell with an error stops passing",
              mutated["cells"][first]["pass"] is False)

        # 2. losing an anchor is caught -- the loss this phase exists for
        case = copy_run()
        saved = case / "saved" / f"{first}-after.odt"
        _rewrite_content(saved, lambda text: text.replace("頁面錨點", "XXX", 1)
                         .replace("長文件記憶體與效能測試", "XXX", 1)
                         .replace("Final line", "XXX", 1)
                         .replace("Lorem ipsum", "XXX", 1))
        mutated = judge_run(case, skip_desktop=True)
        check("a dropped anchor stops the cell passing",
              mutated["cells"][first]["pass"] is False,
              str(mutated["cells"][first]["checks"]))

        # 3. the edit itself has to be visible in the bytes
        case = copy_run()
        saved = case / "saved" / f"{first}-after.odt"
        _rewrite_content(saved, lambda text: text.replace("<text:list ", "<text:zz ")
                         .replace("</text:list>", "</text:zz>"))
        mutated = judge_run(case, skip_desktop=True)
        check("a save with no list in it stops the cell passing",
              mutated["cells"][first]["pass"] is False,
              str(mutated["cells"][first]["checks"]))

        # 4. a harness marker leaking into a corpus document
        case = copy_run()
        saved = case / "saved" / f"{first}-after.odt"
        _rewrite_content(saved, lambda text: text.replace(
            "</office:text>", "<text:p>E2C-LEAKED-MARKER</text:p></office:text>"))
        mutated = judge_run(case, skip_desktop=True)
        check("a leaked E2C- marker stops the cell passing",
              mutated["cells"][first]["pass"] is False,
              str(mutated["cells"][first]["checks"]))

        # 5. structure loss that keeps every anchor
        case = copy_run()
        saved = case / "saved" / f"{first}-after.odt"
        _rewrite_content(saved, lambda text: text.replace("<office:annotation",
                                                         "<office:zz", 1)
                         .replace("<draw:frame", "<draw:zz", 1)
                         .replace("<table:table ", "<table:zz ", 1))
        mutated = judge_run(case, skip_desktop=True)
        moved = (mutated["cells"][first]["pass"] is False
                 or not structure_counts(FIXTURES[
                     mutated["cells"][first]["fixture"]]).get("annotations"))
        check("structure loss is caught where the fixture has structure to lose",
              moved, str(mutated["cells"][first].get("structureDifferences")))

        # 6. the cross-browser comparison must be able to say no
        one = judge_run(run, skip_desktop=True)
        two = copy.deepcopy(one)
        cell = next(iter(two["cells"]))
        two["cells"][cell]["pass"] = not two["cells"][cell]["pass"]
        comparison = compare_browsers([one, two], [run, run])
        check("disagreeing browsers fail the comparison",
              comparison["pass"] is False)

        # 7. ... and must not pass by comparing a run with itself only
        single = compare_browsers([one], [run])
        check("a single browser is not a comparison",
              single.get("compared") is False)

    # Counted, not written down: a hardcoded denominator stops matching the
    # moment a case is added, and then it is reporting its own staleness.
    print(f"\nself-test: {len(ran) - len(failures)}/{len(ran)} "
          "checks moved the verdict")
    return 1 if failures else 0


def _rewrite_content(path: Path, transform) -> None:
    """Rewrite content.xml inside an ODT copy, preserving every other entry."""
    with zipfile.ZipFile(path) as archive:
        entries = [(item, archive.read(item.filename)) for item in archive.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for item, data in entries:
            if item.filename == "content.xml":
                data = transform(data.decode("utf-8")).encode("utf-8")
            archive.writestr(item, data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--carried", type=Path, default=None,
                        help="directory holding the L round's saved documents")
    parser.add_argument("--skip-desktop", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.self_test:
        return self_test(args.runs[0])

    runs = [judge_run(run, args.skip_desktop) for run in args.runs]
    comparison = compare_browsers(runs, args.runs)
    carried = (judge_carried(args.carried, args.skip_desktop)
               if args.carried else None)
    summary = summarise(runs, comparison, carried)
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
