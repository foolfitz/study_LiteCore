#!/usr/bin/env python3
"""A7's round-trip slice: are the ODTs this engine writes sound documents?

A3/A4/A5 all ask the same kind of question -- "is the paragraph in the state
the action asked for" -- and they answer it by reading the file back.  None of
them asks whether the *package* is sound, or whether another LibreOffice can
open it.  SPEC E2-A section 5 puts that in A7, and section 8 makes A7 part of
`GO_TO_E2_B`; SPEC E2-A 2.8 narrowing 3 says in as many words that pinning the
serialiser's output is A7's job and is not validated anywhere yet.  E2-000
section 10 lists "list switching causes silent structure loss in the ODT" as a
STOP-clause risk, which is exactly what a structural check is for.

Two rules this tool follows because the project has been burned by their
absence:

  * It counts only runs bound to the artifact currently in dist/ (finding 027).
    Evidence from a superseded build is reported as skipped, never as coverage.
  * Every check is written so a broken document fails it.  `--self-test`
    breaks a good document five different ways and requires five failures;
    a checker that cannot fail is the shape of validate_e1_corpus.py, which
    never ran at all.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
import zipfile
import zlib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_e2_discovery import A3_ANCHORS  # noqa: E402

ANCHORS = dict(A3_ANCHORS, **{
    "table-boundary": "E1-CELL-A1",
    "paragraph-content": "PC-PLAIN",
    "image-variants": "IV-PLAIN",
})

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}
ODT_MIMETYPE = b"application/vnd.oasis.opendocument.text"

# Attributes that name a style, and the element that declares one.  Kept
# explicit rather than "any attribute ending in style-name": a silent typo in
# this list would weaken the check without failing anything, so it is pinned by
# the self-test instead of trusted.
STYLE_REFERENCES = (
    f"{{{NS['text']}}}style-name",
    f"{{{NS['table']}}}style-name",
    f"{{{NS['draw']}}}style-name",
    f"{{{NS['style']}}}parent-style-name",
    f"{{{NS['style']}}}list-style-name",
    f"{{{NS['text']}}}list-style-name",
)
STYLE_DECLARATIONS = (
    f"{{{NS['style']}}}style",
    f"{{{NS['text']}}}list-style",
    f"{{{NS['style']}}}page-layout",
    f"{{{NS['text']}}}outline-style",
)
NAME_ATTRIBUTE = f"{{{NS['style']}}}name"


def declared_styles(archive: zipfile.ZipFile) -> set[str]:
    """Every style name this package declares, from both style documents."""
    names: set[str] = set()
    for member in ("content.xml", "styles.xml"):
        if member not in archive.namelist():
            continue
        root = ElementTree.fromstring(archive.read(member))
        for element in root.iter():
            if element.tag in STYLE_DECLARATIONS:
                name = element.get(NAME_ATTRIBUTE)
                if name:
                    names.add(name)
    return names


def check_package(path: Path) -> list[str]:
    """ODF packaging: the parts are all there, intact, and declared."""
    problems: list[str] = []
    if not zipfile.is_zipfile(path):
        return ["not-a-zip"]
    with zipfile.ZipFile(path) as archive:
        # testzip() raises rather than returns on a corrupted deflate stream,
        # and an exception here would abort the whole sweep instead of failing
        # one document -- a validator that crashes produces no verdict at all,
        # which is the failure mode this project keeps legislating against.
        try:
            if archive.testzip() is not None:
                problems.append("crc-failed")
        except (zipfile.BadZipFile, OSError, EOFError, zlib.error) as error:
            return [f"crc-failed:{type(error).__name__}"]
        names = archive.namelist()
        # ODF 1.3 3.3: mimetype first, stored, no extra field.  A reader that
        # sniffs the type from the first 30 bytes -- which desktop LibreOffice
        # does -- misidentifies the document when this is wrong.
        if not names or names[0] != "mimetype":
            problems.append("mimetype-not-first")
        elif archive.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            problems.append("mimetype-deflated")
        elif archive.read("mimetype") != ODT_MIMETYPE:
            problems.append("mimetype-wrong")
        for member in names:
            if not member.endswith(".xml"):
                continue
            try:
                ElementTree.fromstring(archive.read(member))
            except ElementTree.ParseError as error:
                problems.append(f"xml-malformed:{member}:{error}")
        if "META-INF/manifest.xml" in names:
            try:
                manifest = ElementTree.fromstring(archive.read("META-INF/manifest.xml"))
            except ElementTree.ParseError:
                manifest = None
            if manifest is not None:
                listed = {
                    entry.get(f"{{{NS['manifest']}}}full-path")
                    for entry in manifest.iter(f"{{{NS['manifest']}}}file-entry")
                }
                # A part present in the zip but absent from the manifest is the
                # signature of content that survived the write and will not
                # survive the read.
                for member in names:
                    if member in ("mimetype", "META-INF/manifest.xml"):
                        continue
                    if member.endswith("/"):
                        continue
                    if member not in listed:
                        problems.append(f"manifest-missing-entry:{member}")
                for entry in listed:
                    if not entry or entry == "/" or entry.endswith("/"):
                        continue
                    if entry not in names:
                        problems.append(f"manifest-lists-absent-part:{entry}")
        else:
            problems.append("manifest-absent")
    return problems


def check_structure(path: Path, anchor: str | None) -> list[str]:
    """Content structure: styles resolve, lists nest, headings are levelled."""
    problems: list[str] = []
    if not zipfile.is_zipfile(path):
        return ["not-a-zip"]
    with zipfile.ZipFile(path) as archive:
        if "content.xml" not in archive.namelist():
            return ["content-absent"]
        try:
            root = ElementTree.fromstring(archive.read("content.xml"))
            declared = declared_styles(archive)
        except ElementTree.ParseError as error:
            return [f"xml-malformed:content.xml:{error}"]
        except (zipfile.BadZipFile, OSError, EOFError, zlib.error) as error:
            # Same reason as check_package: one unreadable document must be a
            # reported failure, not the end of the run.
            return [f"unreadable:{type(error).__name__}"]

    if anchor is not None and anchor not in "".join(root.itertext()):
        problems.append(f"anchor-missing:{anchor}")

    for element in root.iter():
        for attribute in STYLE_REFERENCES:
            value = element.get(attribute)
            # The empty string is a legitimate "no style" in ODF and is not a
            # dangling reference.
            if value and value not in declared:
                problems.append(f"unresolved-style:{value}")

    parents = {child: parent for parent in root.iter() for child in parent}
    list_tag = f"{{{NS['text']}}}list"
    item_tag = f"{{{NS['text']}}}list-item"
    for element in root.iter(item_tag):
        parent = parents.get(element)
        if parent is None or parent.tag != list_tag:
            problems.append("orphan-list-item")
    for element in root.iter(list_tag):
        if next(element.iter(item_tag), None) is None:
            problems.append("empty-list")
    for element in root.iter(f"{{{NS['text']}}}h"):
        level = element.get(f"{{{NS['text']}}}outline-level")
        if level is None or not level.isdigit() or int(level) < 1:
            problems.append(f"heading-without-outline-level:{level}")
    return sorted(set(problems))


def reopen_with_desktop(paths: list[Path], soffice: str,
                        batch: int = 40) -> dict[str, Any]:
    """Open each document in desktop LibreOffice and export it to PDF.

    A structural check says the bytes are shaped like ODF.  This says another
    LibreOffice -- a different version from the one compiled into the engine --
    agrees, which is the half of SPEC E2-A 2.8 narrowing 3 that no other check
    covers.
    """
    results: dict[str, Any] = {"converted": [], "failed": [], "version": None}
    version = subprocess.run([soffice, "--version"], capture_output=True,
                             text=True, check=False)
    results["version"] = version.stdout.strip() or version.stderr.strip()
    with tempfile.TemporaryDirectory() as workspace:
        staging = Path(workspace) / "in"
        output = Path(workspace) / "out"
        staging.mkdir()
        output.mkdir()
        # Unique names: the evidence tree repeats `after-cycle-list-none.odt`
        # in every attempt directory, and a shared output directory would let
        # one conversion stand in for a hundred.
        staged: list[tuple[Path, Path]] = []
        for index, path in enumerate(paths):
            target = staging / f"{index:04d}-{path.name}"
            shutil.copy2(path, target)
            staged.append((path, target))
        for start in range(0, len(staged), batch):
            chunk = staged[start:start + batch]
            subprocess.run(
                [soffice, "--headless", "--norestore", "--convert-to", "pdf",
                 "--outdir", str(output)] + [str(target) for _, target in chunk],
                capture_output=True, text=True, check=False, timeout=1800)
        for source, target in staged:
            pdf = output / (target.stem + ".pdf")
            # Existence is not enough: a failed export can leave a stub.
            if pdf.is_file() and pdf.stat().st_size > 1024 \
                    and pdf.read_bytes()[:5] == b"%PDF-":
                results["converted"].append(str(source))
            else:
                results["failed"].append({
                    "path": str(source),
                    "bytes": pdf.stat().st_size if pdf.is_file() else 0,
                })
    return results


def current_wasm(profile: Path) -> str:
    manifest = json.loads((profile / "sdk-manifest.json").read_text(encoding="utf-8"))
    return manifest["diagnostic"]["wasmSha256"]


def collect(evidence: Path, wanted_sha: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Every ODT written by a run bound to the current artifact."""
    documents: list[dict[str, Any]] = []
    skipped: dict[str, int] = {}
    for result_path in sorted(evidence.rglob("result.json")):
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            skipped["unreadable-result"] = skipped.get("unreadable-result", 0) + 1
            continue
        sha = ((result.get("manifest") or {}).get("diagnostic") or {}).get("wasmSha256")
        odts = sorted(result_path.parent.glob("*.odt"))
        if sha != wanted_sha:
            if odts:
                key = f"other-artifact:{(sha or 'none')[:8]}"
                skipped[key] = skipped.get(key, 0) + len(odts)
            continue
        for odt in odts:
            documents.append({
                "path": odt,
                "browser": result.get("browser"),
                "fixture": result.get("fixture"),
                "tree": result_path.relative_to(evidence).parts[0],
            })
    return documents, skipped


def referenced_styles(archive: zipfile.ZipFile) -> set[str]:
    """Style names content.xml actually points at."""
    root = ElementTree.fromstring(archive.read("content.xml"))
    return {value for element in root.iter()
            for attribute in STYLE_REFERENCES
            if (value := element.get(attribute))}


def break_document(source: Path, kind: str, target: Path) -> None:
    """Produce a document that must fail exactly one named check."""
    with zipfile.ZipFile(source) as archive:
        members = [(info, archive.read(info.filename)) for info in archive.infolist()]
        # Rename a style the document REALLY USES.  The first version renamed
        # whichever declaration came first in content.xml, and the sample it
        # ran on declared none at all -- so the mutation changed nothing and
        # the check "passed" without being exercised.
        wanted = sorted(referenced_styles(archive) & declared_styles(archive))
    victim = wanted[0] if wanted else None
    with zipfile.ZipFile(target, "w") as out:
        for info, data in members:
            name = info.filename
            if kind == "mimetype-last" and name == "mimetype":
                continue
            if kind == "malformed-xml" and name == "content.xml":
                data = data.replace(b"</office:body>", b"</office:bodyy>")
            if kind == "dangling-style" and victim is not None \
                    and name in ("content.xml", "styles.xml"):
                # Leave every reference to `victim` pointing at nothing.  This
                # is the shape "silent structure loss" takes in the file.
                root = ElementTree.fromstring(data)
                for element in root.iter():
                    if element.tag in STYLE_DECLARATIONS \
                            and element.get(NAME_ATTRIBUTE) == victim:
                        element.set(NAME_ATTRIBUTE, victim + "-RENAMED")
                data = ElementTree.tostring(root, encoding="utf-8")
            if kind == "unlisted-part" and name == "META-INF/manifest.xml":
                root = ElementTree.fromstring(data)
                for entry in list(root):
                    if entry.get(f"{{{NS['manifest']}}}full-path") == "content.xml":
                        root.remove(entry)
                data = ElementTree.tostring(root, encoding="utf-8")
            if kind == "orphan-list-item" and name == "content.xml":
                root = ElementTree.fromstring(data)
                parents = {c: p for p in root.iter() for c in p}
                item = next(root.iter(f"{{{NS['text']}}}list-item"), None)
                if item is None:
                    body = next(root.iter(f"{{{NS['office']}}}text"))
                    body.append(ElementTree.Element(f"{{{NS['text']}}}list-item"))
                else:
                    parents[item].remove(item)
                    next(root.iter(f"{{{NS['office']}}}text")).append(item)
                data = ElementTree.tostring(root, encoding="utf-8")
            out.writestr(info, data)
        if kind == "mimetype-last":
            out.writestr("mimetype", ODT_MIMETYPE)


SELF_TEST = {
    "mimetype-last": "mimetype-not-first",
    "malformed-xml": "xml-malformed:content.xml",
    "dangling-style": "unresolved-style:",
    "unlisted-part": "manifest-missing-entry:content.xml",
    "orphan-list-item": "orphan-list-item",
}


def expressiveness(path: Path) -> dict[str, int]:
    """How much of the structure under test a document actually contains.

    A mutation test on a document that cannot express the defect is not a
    weaker test, it is no test: the first version of this file renamed a style
    in a document that declared none and reported the check as exercised.
    """
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("content.xml"))
        shared = referenced_styles(archive) & declared_styles(archive)
    return {
        "resolvableStyleReferences": len(shared),
        "listItems": sum(1 for _ in root.iter(f"{{{NS['text']}}}list-item")),
        "lists": sum(1 for _ in root.iter(f"{{{NS['text']}}}list")),
        "headings": sum(1 for _ in root.iter(f"{{{NS['text']}}}h")),
    }


def choose_sample(paths: list[Path]) -> Path:
    """The document that exercises the most of what the checks look at."""
    return max(paths, key=lambda path: (
        min(expressiveness(path)["resolvableStyleReferences"], 1),
        min(expressiveness(path)["listItems"], 1),
        sum(expressiveness(path).values()),
    ))


def self_test(sample: Path) -> dict[str, Any]:
    """Break a good document five ways; every break must be caught."""
    outcomes = []
    with tempfile.TemporaryDirectory() as workspace:
        for kind, expected in SELF_TEST.items():
            broken = Path(workspace) / f"{kind}.odt"
            break_document(sample, kind, broken)
            found = check_package(broken) + check_structure(broken, None)
            outcomes.append({
                "mutation": kind,
                "expects": expected,
                "caught": any(problem.startswith(expected) for problem in found),
                "reported": found[:4],
            })
    baseline = check_package(sample) + check_structure(sample, None)
    carries = expressiveness(sample)
    # Every mutation needs something in the sample to damage.  Without this the
    # suite reports five greens against a document that could only ever fail
    # three of them.
    usable = carries["resolvableStyleReferences"] > 0 and carries["listItems"] > 0
    return {
        "sample": str(sample),
        "sampleCarries": carries,
        "sampleCanExpressEveryMutation": usable,
        "cleanSampleProblems": baseline,
        "mutations": outcomes,
        "pass": usable and not baseline
        and all(entry["caught"] for entry in outcomes),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path,
                        default=Path("../findings/evidence/sdk-e2/discovery"))
    parser.add_argument("--profile", type=Path,
                        default=Path("dist/profiles/e2-format-discovery"))
    parser.add_argument("--soffice", default=shutil.which("soffice"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-per-browser", type=int, default=3)
    parser.add_argument("--skip-reopen", action="store_true",
                        help="structural checks only; the report says so")
    arguments = parser.parse_args()

    wanted = current_wasm(arguments.profile)
    documents, skipped = collect(arguments.evidence, wanted)
    if not documents:
        print("no ODT is bound to the current artifact", file=sys.stderr)
        return 2

    checks = []
    for entry in documents:
        anchor = ANCHORS.get(entry["fixture"])
        problems = check_package(entry["path"]) + check_structure(entry["path"], anchor)
        checks.append({
            "path": str(entry["path"]),
            "browser": entry["browser"],
            "fixture": entry["fixture"],
            "tree": entry["tree"],
            "anchor": anchor,
            "problems": problems,
            "pass": not problems,
        })

    by_browser: dict[str, dict[str, int]] = {}
    for check in checks:
        bucket = by_browser.setdefault(check["browser"] or "unknown",
                                       {"documents": 0, "passed": 0})
        bucket["documents"] += 1
        bucket["passed"] += 1 if check["pass"] else 0

    control = self_test(choose_sample([Path(check["path"]) for check in checks]))

    # What the corpus lets these checks see.  "406 documents clean" would read
    # as full structural coverage even if none of them carried a list; this
    # says how many did.
    seen = {"withList": 0, "withHeading": 0, "withResolvableStyles": 0}
    for check in checks:
        if not check["pass"]:
            continue   # an unreadable document is counted as a failure, not as coverage
        carries = expressiveness(Path(check["path"]))
        seen["withList"] += 1 if carries["lists"] else 0
        seen["withHeading"] += 1 if carries["headings"] else 0
        seen["withResolvableStyles"] += 1 if carries["resolvableStyleReferences"] else 0

    reopen: dict[str, Any] = {"ran": False,
                              "why": "asked to skip" if arguments.skip_reopen
                              else "no soffice on PATH"}
    refusal: dict[str, Any] = {"ran": False}
    if not arguments.skip_reopen and arguments.soffice:
        reopen = reopen_with_desktop([Path(check["path"]) for check in checks],
                                     arguments.soffice)
        reopen["ran"] = True
        # "406 documents converted" means nothing until a document that should
        # NOT convert is shown not to.  Without this the desktop half would
        # pass against a soffice that writes a PDF for anything it is handed.
        with tempfile.TemporaryDirectory() as workspace:
            broken = Path(workspace) / "malformed.odt"
            break_document(Path(control["sample"]), "malformed-xml", broken)
            outcome = reopen_with_desktop([broken], arguments.soffice)
            refusal = {"ran": True, "refused": not outcome["converted"],
                       "mutation": "malformed-xml"}

    structural_pass = all(check["pass"] for check in checks)
    coverage_pass = all(
        counts["documents"] >= arguments.minimum_per_browser
        for counts in by_browser.values()) and len(by_browser) >= 2
    reopen_pass = (reopen.get("ran") and not reopen.get("failed")
                   and refusal.get("refused") is True)
    decision = ("A7_ROUNDTRIP_PASS"
                if structural_pass and coverage_pass and control["pass"] and reopen_pass
                else "A7_ROUNDTRIP_FAIL")

    report = {
        "schemaVersion": 1,
        "release": "E2-A-paragraph-format-discovery",
        "phase": "A7-roundtrip-slice",
        "decision": decision,
        "artifactBinding": {
            "currentProfileWasmSha256": wanted,
            "documentsBoundToIt": len(documents),
            "documentsSkippedByArtifact": skipped,
        },
        "coverage": by_browser,
        "structureSeen": seen,
        "minimumPerBrowser": arguments.minimum_per_browser,
        "structuralPass": structural_pass,
        "selfTest": control,
        "desktopReopen": {
            "ran": reopen.get("ran", False),
            "version": reopen.get("version"),
            "converted": len(reopen.get("converted", [])),
            "failed": reopen.get("failed", []),
            "why": reopen.get("why"),
            "refusesABrokenDocument": refusal,
        },
        "failures": [check for check in checks if not check["pass"]],
        "notValidated": [
            "The regression half of A7 (R6-R8, E1-A/B/C, workspace preflight)"
            " is not run here; this covers the round-trip half only.",
            "The desktop reopen uses whichever LibreOffice is installed, which"
            " is a cross-version check.  A same-version (26.8) desktop control"
            " is not available on this machine.",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
    print(f"{decision}: {len(documents)} documents, "
          f"{sum(1 for c in checks if c['pass'])} structurally clean, "
          f"reopened {len(reopen.get('converted', []))}")
    for browser, counts in sorted(by_browser.items()):
        print(f"  {browser}: {counts['passed']}/{counts['documents']}")
    return 0 if decision == "A7_ROUNDTRIP_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
