#!/usr/bin/env python3
"""How far does finding 021 reach into the shipped e1-editor-v1 editor?

The page runs paired cases that differ only in whether the format cache was
primed by a click first.  This runner judges none of them from the engine's own
report: it opens each saved ODT and asks whether the target text really carries
the requested format.  A case whose control applied the format and whose
exposure did not, while reporting `documented-state-noop`, is a silent no-op in
a shipped artifact.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from e1_support import sha256, write_json
from r7_support import evaluate, wait_page
from run_browser_probe import ChromeSession, FirefoxSession, free_port

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
FO_NS = "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"

# Which control each exposure case is compared against.  The pair differs only
# in the priming click, so a divergence can only come from the cached value.
PAIRS = {
    "exposure-bold": "control-bold",
    "exposure-italic": "control-italic",
    "exposure-unbold": "control-unbold",
}


def styled_names(root: ElementTree.Element) -> dict[str, set[str]]:
    """Style names that resolve to bold / italic, following parent chains."""
    properties: dict[str, dict[str, str]] = {}
    parents: dict[str, str] = {}
    for style in root.iter(f"{{{STYLE_NS}}}style"):
        name = style.get(f"{{{STYLE_NS}}}name")
        if not name:
            continue
        parent = style.get(f"{{{STYLE_NS}}}parent-style-name")
        if parent:
            parents[name] = parent
        for node in style.iter(f"{{{STYLE_NS}}}text-properties"):
            entry = properties.setdefault(name, {})
            weight = node.get(f"{{{FO_NS}}}font-weight")
            posture = node.get(f"{{{FO_NS}}}font-style")
            if weight:
                entry["weight"] = weight
            if posture:
                entry["style"] = posture

    def resolve(name: str, key: str, wanted: str) -> bool:
        seen: set[str] = set()
        current: str | None = name
        while current and current not in seen:
            seen.add(current)
            value = properties.get(current, {}).get(key)
            if value is not None:
                return value == wanted
            current = parents.get(current)
        return False

    every = set(properties) | set(parents)
    return {
        "bold": {name for name in every if resolve(name, "weight", "bold")},
        "italic": {name for name in every if resolve(name, "style", "italic")},
    }


def inspect_target(path: Path, anchor: str) -> dict[str, Any]:
    """Report whether the anchor text carries bold / italic in the saved file."""
    result: dict[str, Any] = {"anchor": anchor, "found": False}
    if not path.is_file() or not zipfile.is_zipfile(path):
        result["error"] = "not-a-zip"
        return result
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            result["error"] = "crc-failed"
            return result
        names = archive.namelist()
        content = archive.read("content.xml")
        styles = archive.read("styles.xml") if "styles.xml" in names else b""
    root = ElementTree.fromstring(content)
    resolved = styled_names(root)
    if styles:
        extra = styled_names(ElementTree.fromstring(styles))
        for key in resolved:
            resolved[key] |= extra[key]

    for node in root.iter():
        if node.tag not in (f"{{{TEXT_NS}}}p", f"{{{TEXT_NS}}}h"):
            continue
        if anchor not in "".join(node.itertext()):
            continue
        result["found"] = True
        paragraph_style = node.get(f"{{{TEXT_NS}}}style-name")
        result["paragraphStyle"] = paragraph_style
        # Text sitting directly on the paragraph carries no span style, so it
        # can only be formatted through the paragraph style itself.
        carriers: list[tuple[str, str | None]] = []
        direct = (node.text or "").strip()
        if direct:
            carriers.append((direct, paragraph_style))
        for span in node.iter(f"{{{TEXT_NS}}}span"):
            text = "".join(span.itertext()).strip()
            if text:
                carriers.append((text, span.get(f"{{{TEXT_NS}}}style-name")))
        result["runs"] = [
            {
                "text": text,
                "style": name,
                "bold": name in resolved["bold"],
                "italic": name in resolved["italic"],
            }
            for text, name in carriers
        ]
        for key in ("bold", "italic"):
            result[key] = any(
                anchor in text and name in resolved[key] for text, name in carriers
            )
        break
    return result


def judge(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Every verdict is a comparison against that case's own control."""
    by_label = {case.get("label"): case for case in cases}

    def applied(case: dict[str, Any] | None) -> bool | None:
        """Did the saved file end up in the state the action requested?"""
        if not case:
            return None
        inspection = case.get("inspection") or {}
        if not inspection.get("found"):
            return None
        value = inspection.get(case.get("format"))
        if value is None:
            return None
        return value is bool(case.get("enabled"))

    results: dict[str, Any] = {}
    exposed: list[str] = []
    unreached: list[str] = []
    for exposure_label, control_label in PAIRS.items():
        exposure = by_label.get(exposure_label)
        control = by_label.get(control_label)
        if not exposure or not control:
            continue
        primed = (exposure.get("stateAfterPriming") or {}).get(exposure.get("format"))
        control_ok = applied(control)
        exposure_ok = applied(exposure)
        completion = (exposure.get("result") or {}).get("completion")
        entry = {
            "control": control_label,
            "controlApplied": control_ok,
            "cacheAfterPriming": primed,
            "cachePrimed": primed is not None,
            "exposureApplied": exposure_ok,
            "exposureCompletion": completion,
            "controlCompletion": (control.get("result") or {}).get("completion"),
        }
        entry["exposed"] = (
            control_ok is True
            and exposure_ok is False
            and completion == "documented-state-noop"
        )
        # A variant whose priming never populated the cache cannot reach the
        # shortcut at all.  That is "not reached", never "safe".
        entry["reachedShortcut"] = entry["cachePrimed"]
        if entry["exposed"]:
            exposed.append(exposure_label)
        elif not entry["cachePrimed"]:
            unreached.append(exposure_label)
        results[exposure_label] = entry

    controls_ok = all(
        applied(by_label.get(label)) is True for label in set(PAIRS.values())
        if by_label.get(label)
    )
    return {
        "pairs": results,
        "exposed": exposed,
        "notReached": unreached,
        "allControlsApplied": controls_ok,
        "conclusive": controls_ok and bool(results),
        "note": (
            "an exposed pair means the shipped editor reported "
            "documented-state-noop for text that was not in that state, and "
            "left the document unchanged"
        ),
    }


def next_evidence_directory(base: Path) -> Path:
    if not (base / "result.json").exists():
        return base
    attempt = 2
    while (base / f"attempt-{attempt:02d}").exists():
        attempt += 1
    return base / f"attempt-{attempt:02d}"


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument(
        "--profile",
        default="e1-editor-v1",
        help="profile under test; the default is the frozen shipped artifact",
    )
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "022",
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
    root = args.evidence_root if args.profile == "e1-editor-v1" else (
        args.evidence_root / args.profile)
    evidence = next_evidence_directory(root / args.browser)
    try:
        base_url = f"http://127.0.0.1:{server_port}/e1-bold-noop-check.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(f"{base_url}?profile={args.profile}")
        deadline = time.monotonic() + args.timeout
        metrics = None
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__e1_bold_noop || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.25)
        if not metrics or not metrics.get("complete"):
            metrics = {
                "schemaVersion": 2,
                "release": "finding-022-e1-exposure",
                "complete": False,
                "error": {
                    "code": "RUNNER_TIMEOUT",
                    "message": f"page timed out after {args.timeout}s",
                },
            }
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "page.png").write_bytes(session.screenshot())
        log_text = str(evaluate(session, "document.querySelector('#log')?.textContent || ''"))
        (evidence / "page.log.txt").write_text(log_text, encoding="utf-8")

        for case in metrics.get("cases") or []:
            label = case.get("label")
            encoded = str(
                evaluate(
                    session,
                    f"globalThis.__e1_bold_noop_get_output_base64?.({json.dumps(label)}) || ''",
                )
            )
            if not encoded:
                case["retrieved"] = False
                continue
            output_path = evidence / f"after-{label}.odt"
            output_path.write_bytes(base64.b64decode(encoded))
            case["retrieved"] = True
            case["sha256"] = sha256(output_path)
            case["inspection"] = inspect_target(output_path, case.get("target"))

        metrics["verdict"] = judge(metrics.get("cases") or [])
        result = {
            **metrics,
            "browser": args.browser,
            "browserVersion": session.version,
            "profileUnderTest": args.profile,
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
        "profile": args.profile,
        "evidence": str(evidence / "result.json"),
        "verdict": result.get("verdict"),
        "error": result.get("error"),
    }, ensure_ascii=False, indent=2))
    verdict = result.get("verdict") or {}
    if not verdict.get("conclusive"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
