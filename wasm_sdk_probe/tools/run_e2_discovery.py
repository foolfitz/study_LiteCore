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
}


def next_evidence_directory(base: Path) -> Path:
    """Keep every browser attempt instead of overwriting failed evidence."""
    if not (base / "result.json").exists():
        return base
    attempt = 2
    while (base / f"attempt-{attempt:02d}").exists():
        attempt += 1
    return base / f"attempt-{attempt:02d}"


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
        while ancestor is not None:
            if ancestor.tag == f"{{{TEXT_NS}}}list":
                inside = True
                result["listStyle"] = ancestor.get(f"{{{TEXT_NS}}}style-name")
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
            "mainloop-attribution",
            "mainloop-pei-attribution",
            "mainloop-move-attribution",
        ),
        default="a2",
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
    root = args.evidence_root if args.mode == "a2" else (
        args.evidence_root.parent / args.mode)
    evidence = next_evidence_directory(root / args.browser)
    try:
        base_url = f"http://127.0.0.1:{server_port}/e2-format-discovery.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(f"{base_url}?fixture={args.fixture}&mode={args.mode}")
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
            inspection = inspect_target_paragraph(output_path, "E1-STYLED-END")
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
        "a2": result.get("a2"),
        "documentPostconditions": result.get("documentPostconditions"),
        "error": result.get("error"),
    }, ensure_ascii=False, indent=2))
    if result.get("pass") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
