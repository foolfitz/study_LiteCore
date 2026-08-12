#!/usr/bin/env python3
"""Run E2-A A2-wasm state readback in Chrome or Firefox and retain evidence.

The page observes; this runner judges.  Every dispatch postcondition is read
out of the saved ODT, never out of the state callback that A2 is testing --
the same separation the native A2 run used.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from e1_support import sha256, write_json
from r7_support import evaluate, wait_page
from run_browser_probe import ChromeSession, FirefoxSession, free_port

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"

# What the document must look like after each dispatch.  These are the
# properties of the saved file, independent of anything the engine reported.
#
# The heading and body entries check the paragraph's style name, not the element
# type.  The first version of this table expected heading-on to produce a
# <text:h>; measuring showed .uno:StyleApply applies the "Heading 1" paragraph
# style to the existing <text:p> instead, which is correct ODF and the outcome
# the user sees.  The expectation was the guess, not the product -- corrected
# here to the measured form rather than relaxed.
EXPECTED_POSTCONDITIONS = {
    "bullet-on": {"insideList": True},
    "numbering-on": {"insideList": True},
    "list-off": {"insideList": False},
    "heading-on": {"resolvedParagraphStyle": "Heading_20_1"},
    "body-on": {"resolvedParagraphStyle": "Text_20_body"},
    # Repeats must land on the same state, not the opposite one.  A toggle
    # would show up here as insideList flipping back to False on repeat-1 and
    # True again on repeat-2 (finding 030).
    "bullet-on-repeat-1": {"insideList": True},
    "bullet-on-repeat-2": {"insideList": True},
    "heading-on-repeat-1": {"resolvedParagraphStyle": "Heading_20_1"},
    "heading-on-repeat-2": {"resolvedParagraphStyle": "Heading_20_1"},
    # A3: every step of the cycle is judged, not just where the cycle ends.
    "cycle-list-unordered": {"insideList": True, "listKind": "bullet"},
    "cycle-list-ordered": {"insideList": True, "listKind": "number"},
    "cycle-list-none": {"insideList": False},
    "roundtrip-heading": {"resolvedParagraphStyle": "Heading_20_1"},
    "roundtrip-body": {"resolvedParagraphStyle": "Text_20_body"},
    # A4: the set and both repeats share one expectation on purpose.  A repeat
    # that lands anywhere else is a toggle, and a toggle is the defect finding
    # 030 was about.
    "list-unordered-set": {'insideList': True, 'listKind': 'bullet'},
    "list-unordered-repeat-1": {'insideList': True, 'listKind': 'bullet'},
    "list-unordered-repeat-2": {'insideList': True, 'listKind': 'bullet'},
    "list-ordered-set": {'insideList': True, 'listKind': 'number'},
    "list-ordered-repeat-1": {'insideList': True, 'listKind': 'number'},
    "list-ordered-repeat-2": {'insideList': True, 'listKind': 'number'},
    "list-none-set": {'insideList': False},
    "list-none-repeat-1": {'insideList': False},
    "list-none-repeat-2": {'insideList': False},
    "paragraph-heading-set": {'resolvedParagraphStyle': 'Heading_20_1'},
    "paragraph-heading-repeat-1": {'resolvedParagraphStyle': 'Heading_20_1'},
    "paragraph-heading-repeat-2": {'resolvedParagraphStyle': 'Heading_20_1'},
    "paragraph-body-set": {'resolvedParagraphStyle': 'Text_20_body'},
    "paragraph-body-repeat-1": {'resolvedParagraphStyle': 'Text_20_body'},
    "paragraph-body-repeat-2": {'resolvedParagraphStyle': 'Text_20_body'},
}


def next_evidence_directory(base: Path) -> Path:
    """Keep every browser attempt instead of overwriting failed evidence."""
    if not (base / "result.json").exists():
        return base
    attempt = 2
    while (base / f"attempt-{attempt:02d}").exists():
        attempt += 1
    return base / f"attempt-{attempt:02d}"


def _ancestors(parents: dict, node: Any):
    current = parents.get(node)
    while current is not None:
        yield current
        current = parents.get(current)


# The A3 anchor per fixture, mirroring the app.  Two copies of one table is how
# a fixture gets added on one side and silently judged against the wrong
# paragraph on the other, so a test pins them equal.
A3_ANCHORS = {
    "styled-list": "E1-STYLED-END",
    "multi-paragraph": "E1-MULTI-END",
    "plain-grapheme": "E1-PLAIN-END",
}


def inspect_target_paragraph(path: Path, anchor: str) -> dict[str, Any]:
    """Report the structural facts about the paragraph carrying the anchor."""
    import zipfile

    result: dict[str, Any] = {
        "anchor": anchor,
        "found": False,
        "isHeading": None,
        "paragraphStyle": None,
        "resolvedParagraphStyle": None,
        "insideList": None,
        "listStyle": None,
        "listKind": None,
        "listLevel": None,
        "totalLists": None,
        "totalHeadings": None,
    }
    if not path.is_file() or not zipfile.is_zipfile(path):
        result["error"] = "not-a-zip"
        return result
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            result["error"] = "crc-failed"
            return result
        root = ElementTree.fromstring(archive.read("content.xml"))
    parents = {child: parent for parent in root.iter() for child in parent}
    # Joining a list gives the paragraph an automatic style (P1, P2, ...) that
    # inherits from the named one, so the raw style-name stops being the style
    # the moment a heading is also in a list.  Resolving to the named parent is
    # what makes "is this Heading 1" answerable in both shapes.  The same
    # mistake was fixed in analyze_e2_a_native_reissue.py earlier the same day
    # and not carried across to here, which is how a correct barrier ended up
    # judged as a failure.
    # unordered vs ordered is the promise; the generated list style name (L1,
    # L2, ...) is renumbered on every save and says nothing.  Resolve the kind
    # from the list style definition rather than from the command dispatched,
    # which would assume the answer the postcondition is supposed to check.
    #
    # Per level, not per style.  A list style defines every level it supports,
    # and LibreOffice writes mixed ones -- L1 in this fixture is a bullet at
    # level 1 and numbers at levels 2 and 3.  Asking "does this style contain a
    # numbered level" answers "yes" for a bullet list, which is how a correct
    # document first read as the wrong kind here.
    list_kinds: dict[tuple[str, str], str] = {}
    for node in root.iter(f"{{{TEXT_NS}}}list-style"):
        name = node.get(f"{{{STYLE_NS}}}name")
        if not name:
            continue
        for child in node:
            level = child.get(f"{{{TEXT_NS}}}level")
            if not level:
                continue
            if child.tag == f"{{{TEXT_NS}}}list-level-style-number":
                list_kinds[(name, level)] = "number"
            elif child.tag == f"{{{TEXT_NS}}}list-level-style-bullet":
                list_kinds[(name, level)] = "bullet"
    style_parents = {
        node.get(f"{{{STYLE_NS}}}name"): node.get(f"{{{STYLE_NS}}}parent-style-name")
        for node in root.iter(f"{{{STYLE_NS}}}style")
        if node.get(f"{{{STYLE_NS}}}family") == "paragraph"
        and node.get(f"{{{STYLE_NS}}}name")
        and node.get(f"{{{STYLE_NS}}}parent-style-name")
    }
    result["totalLists"] = sum(node.tag == f"{{{TEXT_NS}}}list" for node in root.iter())
    result["totalHeadings"] = sum(node.tag == f"{{{TEXT_NS}}}h" for node in root.iter())
    for node in root.iter():
        if node.tag not in (f"{{{TEXT_NS}}}p", f"{{{TEXT_NS}}}h"):
            continue
        if anchor not in "".join(node.itertext()):
            continue
        result["found"] = True
        result["isHeading"] = node.tag == f"{{{TEXT_NS}}}h"
        style_name = node.get(f"{{{TEXT_NS}}}style-name")
        result["paragraphStyle"] = style_name
        result["resolvedParagraphStyle"] = style_parents.get(style_name, style_name)
        ancestor = parents.get(node)
        inside = False
        # Nesting depth, so the kind is read at the level the paragraph is
        # actually on rather than at level 1 by assumption.
        depth = sum(1 for node_ in _ancestors(parents, node)
                    if node_.tag == f"{{{TEXT_NS}}}list")
        while ancestor is not None:
            if ancestor.tag == f"{{{TEXT_NS}}}list":
                inside = True
                result["listStyle"] = ancestor.get(f"{{{TEXT_NS}}}style-name")
                result["listKind"] = list_kinds.get((result["listStyle"], str(depth)))
                result["listLevel"] = depth
                break
            ancestor = parents.get(ancestor)
        result["insideList"] = inside
        break
    return result


def judge_postcondition(label: str, inspection: dict[str, Any]) -> dict[str, Any]:
    expected = EXPECTED_POSTCONDITIONS.get(label)
    if expected is None:
        return {"judged": False, "reason": "no registered postcondition"}
    if not inspection.get("found"):
        return {"judged": True, "met": False, "reason": "anchor paragraph not found in output"}
    mismatches = {
        key: {"expected": value, "actual": inspection.get(key)}
        for key, value in expected.items()
        if inspection.get(key) != value
    }
    return {"judged": True, "met": not mismatches, "expected": expected, "mismatches": mismatches}


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--fixture", default="styled-list")
    parser.add_argument(
        "--mode",
        choices=(
            "a2",
            "scheduler-attribution",
            # Finding 031: scheduler-attribution with a zh-TW UI language
            # compiled into the engine.  Same sequence, same drain, so the two
            # modes are directly comparable.
            "locale-attribution",
            # A3: the frozen positive matrix (SPEC E2-A section 5).
            "a3",
            # A4: repeat dispatch, the case route C created.
            "a4",
            # A5: negative and boundary cases.
            "a5",
            # The format barrier's wedge on an empty paragraph (finding 033's
            # open gap).  Its own tree, because it is the same measurement run
            # against two engines and both answers are evidence.
            "deadline",
            # Finding 034: the caret-offset discriminators.  Its own tree
            # because the same case list is run against two engines and both
            # answers are evidence -- the old build is what proves the gesture
            # reaches offset 0 at all.
            "discriminator",
            # Finding 037: the discriminator cases against the same artifact
            # through a worker copy that forwards the LOK callback stream.  Its
            # own mode rather than a flag on "discriminator" because the two
            # produce different records of the same run and mixing them into
            # one tree would make "which rows were traced" unanswerable.
            "wedge-trace",
            # Finding 037 stage two: the two LOK calls inside the barrier's
            # read step, driven one at a time without the barrier.
            "wedge-split",
            "mainloop-attribution",
            "mainloop-pei-attribution",
            "mainloop-move-attribution",
        ),
        default="a2",
    )
    parser.add_argument(
        "--cases",
        default="",
        help="comma-separated discriminator case ids to run (default: all)",
    )
    parser.add_argument(
        "--action",
        default="",
        help="wedge-trace only: dispatch this closed action instead of the "
             "one each case declares (finding 037 coverage)",
    )
    parser.add_argument(
        "--select-method",
        default="",
        help="wedge-split only: which way to select (finding 038 scope)",
    )
    parser.add_argument("--idle-after-select", type=int, default=0)
    parser.add_argument("--span", default="")
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="exact evidence directory, overriding the per-mode tree",
    )
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e2" / "discovery" / "state-readback" / "wasm",
    )
    args = parser.parse_args()

    server_port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(server_port)],
        cwd=project,
        # DEVNULL, not PIPE: nothing ever read these pipes, and the request
        # log fills 64 KiB after a workload-dependent number of navigations --
        # the handler thread then blocks before sending the response body and
        # every later fetch hangs (finding 023).
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    session = None
    result: dict[str, Any] = {}
    keyed_modes = ("a3", "a4", "a5", "deadline", "discriminator", "wedge-trace",
                   "wedge-split")
    if args.mode == "a2":
        root = args.evidence_root
    elif args.mode in keyed_modes:
        # SPEC E2-A section 6 gives A3 its own tree, keyed by fixture, because
        # the verdict has to be able to say which fixtures were covered rather
        # than average over whatever happened to run.
        root = args.evidence_root.parent.parent / {
            "a3": "browser", "a4": "repeat", "a5": "negative",
            "deadline": "barrier-deadline",
            "discriminator": "caret-offset-discriminator",
            "wedge-trace": "wedge-trace",
            "wedge-split": "wedge-split"}[args.mode]
        root = root / args.browser / args.fixture
    else:
        root = args.evidence_root.parent / args.mode
    if args.evidence_dir is not None:
        evidence = next_evidence_directory(args.evidence_dir)
    else:
        evidence = next_evidence_directory(
            root if args.mode in keyed_modes else root / args.browser)
    try:
        base_url = f"http://127.0.0.1:{server_port}/e2-format-discovery.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        query = f"?fixture={args.fixture}&mode={args.mode}"
        if args.cases:
            query += f"&cases={args.cases}"
        if args.action:
            query += f"&action={args.action}"
        if args.select_method:
            query += f"&select={args.select_method}"
        if args.idle_after_select:
            query += f"&idleAfterSelect={args.idle_after_select}"
        if args.span:
            query += f"&span={args.span}"
        session.navigate(f"{base_url}{query}")
        deadline = time.monotonic() + args.timeout
        metrics = None
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__e2_discovery || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.25)
        if not metrics or not metrics.get("complete"):
            metrics = {
                "schemaVersion": 1,
                "release": "E2-A-paragraph-format-discovery",
                "stage": "A2-wasm",
                "fixture": args.fixture,
                "complete": False,
                "pass": False,
                "error": {
                    "code": "RUNNER_TIMEOUT",
                    "message": f"page timed out after {args.timeout}s",
                },
            }
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "page.png").write_bytes(session.screenshot())
        log_text = str(evaluate(session, "document.querySelector('#log')?.textContent || ''"))
        (evidence / "page.log.txt").write_text(log_text, encoding="utf-8")

        outputs = []
        for entry in metrics.get("outputs") or []:
            label = entry.get("label")
            encoded = str(
                evaluate(
                    session,
                    f"globalThis.__e2_discovery_get_output_base64?.({json.dumps(label)}) || ''",
                )
            )
            if not encoded:
                outputs.append({"label": label, "retrieved": False})
                continue
            output_path = evidence / f"after-{label}.odt"
            output_path.write_bytes(base64.b64decode(encoded))
            inspection = inspect_target_paragraph(
                output_path, A3_ANCHORS.get(args.fixture, "E1-STYLED-END"))
            outputs.append({
                "label": label,
                "retrieved": True,
                "path": str(output_path),
                "bytes": output_path.stat().st_size,
                "sha256": sha256(output_path),
                "inspection": inspection,
                "postcondition": judge_postcondition(label, inspection),
            })
        metrics["outputs"] = outputs

        judged = [item for item in outputs if item.get("postcondition", {}).get("judged")]
        metrics["documentPostconditions"] = {
            "judged": len(judged),
            "met": sum(1 for item in judged if item["postcondition"].get("met")),
            "allMet": bool(judged) and all(item["postcondition"].get("met") for item in judged),
        }
        result = {
            **metrics,
            "browser": args.browser,
            "browserVersion": session.version,
            "evidenceDirectory": str(evidence),
        }
        write_json(evidence / "result.json", result)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)

    print(json.dumps({
        "browser": args.browser,
        "evidence": str(evidence / "result.json"),
        "pass": result.get("pass") is True,
        "mode": args.mode,
        "cases": args.cases or "all",
        "a2": result.get("a2"),
        "documentPostconditions": result.get("documentPostconditions"),
        "error": result.get("error"),
    }, ensure_ascii=False, indent=2))
    # wedge-trace is the one mode whose expected outcome is a failure: it runs a
    # case that stops answering on purpose, so a non-zero exit would report the
    # measurement working as if it had gone wrong.  Every other mode still fails
    # the process when the page does not pass.
    if args.mode not in ("wedge-trace", "wedge-split") \
            and result.get("pass") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
