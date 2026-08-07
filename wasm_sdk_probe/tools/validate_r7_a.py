#!/usr/bin/env python3
"""Aggregate R7-A automatic/manual evidence and freeze R7-D thresholds."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree


THRESHOLDS = {
    browser: {
        "browser": browser,
        "sampleIntervalMs": 1000,
        "warmupCycles": 10,
        "blockSize": 10,
        "cycleCount": 50,
        "maxPostCloseGrowthBytes": 536_870_912,
        "maxPostCloseGrowthRatio": 0.35,
        "maxBlockMedianSlopeBytes": 67_108_864,
        "maxWasmHeapStepBytes": 268_435_456,
        "maxWorkersAfterClose": 0,
        "openTimeoutMs": 180_000,
        "closeTimeoutMs": 180_000,
    }
    for browser in ("chrome", "firefox")
}
EXPECTED_UNICODE = [
    "臺灣合成-R7", "臺灣文件測試", "「」，。！？；：", "𠀀", "😀",
    "👨‍👩‍👧‍👦", "e\u0301", "é", "換行前-R7", "換行後-R7",
    "連續一-R7", "連續二-R7", "R7-clipboard-臺灣😀",
]
MANUAL_ANCHORS = [
    "第一筆中文輸入",
    "第二筆中文輸入",
    "R7-manual-native-copy-臺灣😀",
    "R7-manual-clipboard-臺灣😀",
]
MANUAL_CLIPBOARD_TEXT = "R7-manual-clipboard-臺灣😀"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def odt_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("content.xml"))
    return "".join(root.itertext())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def desktop_roundtrip(odt: Path, output: Path) -> dict:
    soffice = shutil.which("soffice") or "soffice"
    with tempfile.TemporaryDirectory(prefix="r7-a-desktop-") as temporary:
        root = Path(temporary)
        profile = root / "profile"
        converted = root / f"{odt.stem}.pdf"
        command = [
            soffice, "--headless", "--nologo", "--nodefault",
            "--nofirststartwizard", "--norestore",
            f"-env:UserInstallation={profile.resolve().as_uri()}",
            "--convert-to", "pdf:writer_pdf_Export", "--outdir", str(root), str(odt),
        ]
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=180
        )
        if completed.returncode == 0 and converted.is_file():
            shutil.copyfile(converted, output)
    pdfinfo = subprocess.run(
        [shutil.which("pdfinfo") or "pdfinfo", str(output)],
        check=False, capture_output=True, text=True, timeout=30,
    ) if output.is_file() else None
    return {
        "command": command,
        "returnCode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "pdf": str(output),
        "pdfBytes": output.stat().st_size if output.is_file() else None,
        "pdfSha256": sha256(output) if output.is_file() else None,
        "pdfinfo": pdfinfo.stdout.strip() if pdfinfo else None,
        "pass": completed.returncode == 0
        and output.is_file()
        and output.stat().st_size > 0
        and pdfinfo is not None
        and pdfinfo.returncode == 0,
    }


def summarize_process_memory(samples: list[dict]) -> dict:
    rss = [item["rssBytes"] for item in samples if item.get("rssBytes") is not None]
    pss = [item["pssBytes"] for item in samples if item.get("pssBytes") is not None]
    counts = [item["processCount"] for item in samples if item.get("processCount") is not None]
    return {
        "sampleCount": len(samples),
        "firstRssBytes": rss[0] if rss else None,
        "lastRssBytes": rss[-1] if rss else None,
        "peakRssBytes": max(rss) if rss else None,
        "rssDeltaBytes": rss[-1] - rss[0] if rss else None,
        "firstPssBytes": pss[0] if pss else None,
        "lastPssBytes": pss[-1] if pss else None,
        "peakPssBytes": max(pss) if pss else None,
        "pssDeltaBytes": pss[-1] - pss[0] if pss else None,
        "peakProcessCount": max(counts) if counts else None,
    }


def validate_manual_evidence(discovery: Path, browser: str) -> dict:
    path = discovery / "input" / f"{browser}-manual-pass.json"
    if not path.is_file():
        return {
            "evidence": str(path),
            "status": "missing",
            "checks": {},
            "pass": False,
        }

    evidence = load(path)
    commits = evidence.get("commits", [])
    commit_texts = [item.get("text") for item in commits]
    searches = evidence.get("searches", [])
    searchable = [item for item in searches if item.get("searchable") is not False]
    ime = evidence.get("imeEvidence", {})
    cancel = evidence.get("cancelProbe", {})
    clipboard_read = evidence.get("clipboardRead", {})
    output = evidence.get("output", {})
    expected_browser_token = "Chrome/" if browser == "chrome" else "Firefox/"
    revisions_monotonic = bool(commits) and all(
        isinstance(item.get("beforeRevision"), int)
        and isinstance(item.get("revision"), int)
        and item["revision"] > item["beforeRevision"]
        and (index == 0 or item["beforeRevision"] == commits[index - 1]["revision"])
        for index, item in enumerate(commits)
    )
    output_sha = output.get("sha256")
    checks = {
        "schema": evidence.get("schemaVersion") == 1
        and evidence.get("release") == "R7-A-headed-manual",
        "browser": expected_browser_token in evidence.get("browser", ""),
        "inputMethod": evidence.get("operatorInputMethod")
        == "Fcitx5 Chewing (operator-confirmed)",
        "artifact": evidence.get("artifact", {}).get("profile") == "writer-review"
        and evidence.get("artifact", {}).get("sdkVersion") == "0.6.0-r6-worker",
        "reportedPass": evidence.get("pass") is True,
        "expectedCommits": all(anchor in commit_texts for anchor in MANUAL_ANCHORS),
        "revisionsMonotonic": revisions_monotonic,
        "trustedComposition": ime.get("trustedCompositionStart") is True
        and ime.get("trustedCompositionUpdate") is True
        and ime.get("trustedCompositionBeforeInput") is True,
        "cancelZeroMutation": cancel.get("status") == "checked"
        and cancel.get("requestDelta") == 0
        and cancel.get("trustedPreedit") is True
        and cancel.get("pass") is True
        and cancel.get("compositionEnd", {}).get("commitText") == "",
        "trustedNativePaste": evidence.get("trustedNativePasteCount", 0) >= 1,
        "clipboardWrite": evidence.get("clipboardWrite", {}).get("status") == "passed",
        "clipboardRead": clipboard_read.get("status") == "passed"
        and clipboard_read.get("commitDelta") == 1
        and clipboard_read.get("found") is True
        and clipboard_read.get("text") == MANUAL_CLIPBOARD_TEXT,
        "searches": bool(searchable)
        and all(item.get("found") is True for item in searchable)
        and all(any(item.get("text") == anchor for item in searchable) for anchor in MANUAL_ANCHORS),
        "output": isinstance(output.get("bytes"), int)
        and output["bytes"] > 0
        and isinstance(output_sha, str)
        and len(output_sha) == 64
        and all(character in "0123456789abcdef" for character in output_sha),
    }
    return {
        "evidence": str(path),
        "status": "passed" if all(checks.values()) else "failed",
        "browser": evidence.get("browser"),
        "operatorInputMethod": evidence.get("operatorInputMethod"),
        "commitCount": len(commits),
        "compositionEndTrustValues": ime.get("compositionEndTrustValues", []),
        "output": output,
        "verifiedAt": evidence.get("verifiedAt"),
        "checks": checks,
        "pass": all(checks.values()),
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    evidence = project.parent / "findings" / "evidence" / "sdk-r7"
    discovery = evidence / "discovery"
    corpus = load(evidence / "corpus" / "manifest-validation.json")
    preflight = load(evidence / "baseline" / "preflight-before.json")
    thresholds_path = discovery / "memory" / "thresholds.json"
    thresholds_path.parent.mkdir(parents=True, exist_ok=True)
    thresholds_path.write_text(json.dumps({
        "schemaVersion": 1,
        "release": "R7-D-preregistered-by-R7-A",
        "frozenDate": "2026-08-02",
        "thresholds": list(THRESHOLDS.values()),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    browsers = {}
    checks = {"preflight": preflight["pass"], "corpus": corpus["pass"]}
    decisions = []
    for browser in ("chrome", "firefox"):
        summary = load(discovery / f"{browser}-summary.json")
        input_result = load(discovery / "input" / f"{browser}.json")["input"]
        clipboard = load(discovery / "clipboard" / f"{browser}.json")["clipboard"]
        formats = load(discovery / "formats" / f"{browser}.json")["formats"]
        memory = load(discovery / "memory" / f"{browser}.json")
        output_odt = discovery / "input" / f"{browser}-unicode-out.odt"
        output_pdf = discovery / "input" / f"{browser}-unicode-out.pdf"
        text = odt_text(output_odt)
        missing = [value for value in EXPECTED_UNICODE if value not in text]
        desktop = desktop_roundtrip(output_odt, output_pdf)
        memory_summary = summarize_process_memory(memory.get("processSamples", []))
        browser_checks = {
            "page": summary["pass"],
            "syntheticInput": input_result.get("syntheticPass") is True,
            "unicodeOdtXml": not missing,
            "cancelZeroMutation": input_result.get("cancel", {}).get("requestDelta") == 0
            and input_result.get("cancel", {}).get("found") is False,
            "clipboardPlainText": clipboard.get("syntheticPass") is True
            and clipboard.get("mutationDeltaWithoutGesture") == 0,
            "formatSafety": formats.get("pass") is True,
            "lifecycle10": len(memory["lifecycle"]["cycles"]) == 10
            and all(item["pass"] for item in memory["lifecycle"]["cycles"]),
            "crashRestart3": len(memory["lifecycle"]["crashes"]) == 3
            and all(item["pass"] for item in memory["lifecycle"]["crashes"]),
            "processSamples": len(memory.get("processSamples", [])) > 0,
            "desktopRoundtrip": desktop["pass"],
        }
        checks[browser] = all(browser_checks.values())
        decisions.append(summary["decisionCandidate"])
        browsers[browser] = {
            "checks": browser_checks,
            "missingUnicodeInOdtXml": missing,
            "docxClassification": formats["docxClassification"],
            "processSampleCount": len(memory.get("processSamples", [])),
            "processMemory": memory_summary,
            "browserMemoryMethods": [item["method"] for item in memory["browserMemory"]],
            "browserMemory": memory["browserMemory"],
            "desktopRoundtrip": desktop,
            "pass": checks[browser],
        }
    automatic_pass = all(value is True for value in checks.values())
    decision = "STOP"
    if automatic_pass:
        decision = "PARTIAL_GO" if "PARTIAL_GO" in decisions else "GO"
    manual_browsers = {
        browser: validate_manual_evidence(discovery, browser)
        for browser in ("chrome", "firefox")
    }
    manual_missing = any(item["status"] == "missing" for item in manual_browsers.values())
    manual_pass = all(item["pass"] for item in manual_browsers.values())
    manual_status = "pending" if manual_missing else "passed" if manual_pass else "failed"
    final_decision = (
        "STOP" if not automatic_pass or manual_status == "failed"
        else "PENDING_MANUAL" if manual_status == "pending"
        else decision
    )
    checks["manual"] = manual_pass
    final_pass = automatic_pass and manual_pass
    result = {
        "schemaVersion": 1,
        "release": "R7-A",
        "automaticDecision": decision,
        "finalDecision": final_decision,
        "manual": {
            "required": True,
            "status": manual_status,
            "scope": "headed Chrome and Firefox Fcitx Chewing plus user-gesture plain-text clipboard",
            "browsers": manual_browsers,
        },
        "checks": checks,
        "browsers": browsers,
        "thresholds": str(thresholds_path),
        "pass": final_pass,
    }
    output = discovery / "summary.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not final_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
