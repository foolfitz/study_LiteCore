#!/usr/bin/env python3
"""Shared deterministic helpers for R7 browser evidence and desktop checks."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import psutil

from run_browser_probe import ChromeSession, FirefoxSession


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def process_snapshot(root_pid: int, page_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture only the browser process tree started by the current runner."""
    sample: dict[str, Any] = {
        "monotonicSeconds": time.monotonic(),
        "rootPid": root_pid,
        "processes": [],
    }
    if page_state:
        sample.update({
            "checkpoint": page_state.get("checkpoint"),
            "cycle": page_state.get("cycle"),
            "block": page_state.get("block"),
            "workersAfterClose": page_state.get("workersAfterClose"),
            "activeWorkers": page_state.get("activeWorkers"),
            "activeHandles": page_state.get("activeHandles"),
            "wasmHeapBytes": page_state.get("wasmHeapBytes"),
            "jsHeapBytes": page_state.get("jsHeapBytes"),
            "tileCacheBytes": page_state.get("tileCacheBytes"),
            "documentVersion": page_state.get("documentVersion"),
            "revision": page_state.get("revision"),
        })
    try:
        root = psutil.Process(root_pid)
        processes = [root, *root.children(recursive=True)]
    except (psutil.Error, ProcessLookupError) as error:
        sample["error"] = str(error)
        return sample
    for process in processes:
        try:
            memory = process.memory_info()
            try:
                pss = process.memory_full_info().pss
            except (AttributeError, psutil.Error, PermissionError):
                pss = None
            sample["processes"].append({
                "pid": process.pid,
                "ppid": process.ppid(),
                "name": process.name(),
                "rssBytes": memory.rss,
                "pssBytes": pss,
                "status": process.status(),
            })
        except (psutil.Error, ProcessLookupError):
            continue
    sample["processCount"] = len(sample["processes"])
    sample["rssBytes"] = sum(item["rssBytes"] for item in sample["processes"])
    pss_values = [item["pssBytes"] for item in sample["processes"]
                  if item["pssBytes"] is not None]
    sample["pssBytes"] = sum(pss_values) if pss_values else None
    return sample


def evaluate(session: ChromeSession | FirefoxSession, expression: str) -> Any:
    if isinstance(session, ChromeSession):
        return session.evaluate(expression)
    # .strip() is load-bearing, not tidiness.  WebDriver runs the body as a
    # function, so this becomes `return <expression>;` -- and if the expression
    # starts with a newline (every multi-line injected script does), JavaScript's
    # automatic semicolon insertion turns it into `return;` and the rest is dead
    # code that never runs.  Chrome is unaffected: CDP evaluates the raw
    # expression with no `return` wrapper, so the same script works there.
    # That asymmetry is exactly what made R8-D "hang" only on Firefox: the
    # injected batch script never executed, so the value the runner polled for
    # was never set, and it waited out the full 900 s timeout.
    # Measured 2026-08-08: `return \n (()=>{window.x='ran';return 'v'})()`
    # -> null and window.x stays unset; stripped -> 'v' and window.x === 'ran'.
    return session.execute(f"return {expression.strip()};")


def run_in_page(session: ChromeSession | FirefoxSession, script: str) -> None:
    """Execute `script` in the page's OWN global, not the driver's sandbox.

    Firefox's WebDriver evaluates injected scripts in a sandbox whose global is
    not the page window, and that breaks more than variable writes.  Product
    code that legitimately defaults to `globalThis.fetch?.bind(globalThis)`
    (delivery/verified-loader.js) then binds fetch to the sandbox, and every
    call throws "'fetch' called on an object that does not implement interface
    Window" -- surfacing as a RELEASE_MANIFEST_INVALID at stage manifest-fetch,
    i.e. the harness manufacturing a delivery error that no real page can hit.

    Appending a <script> element makes the browser run the text in the real page
    global, in both browsers.  Chrome's CDP path never had the problem; running
    both the same way is what makes the two browsers comparable at all.
    """
    evaluate(
        session,
        "(() => {"
        " const element = document.createElement('script');"
        f" element.textContent = {json.dumps(script)};"
        " document.head.appendChild(element);"
        " element.remove();"
        " return true; })()",
    )


def wait_page(url: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as error:  # noqa: BLE001 - evidence retains terminal error
            last_error = error
        time.sleep(0.2)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def odt_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("content.xml"))
    return "".join(root.itertext())


def validate_saved_odt(path: Path, commits: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256(path) if path.is_file() else None,
        "zip": False,
        "crc": False,
        "xml": False,
        "anchors": [],
        "pass": False,
    }
    if not path.is_file() or not zipfile.is_zipfile(path):
        return result
    result["zip"] = True
    try:
        with zipfile.ZipFile(path) as archive:
            result["crc"] = archive.testzip() is None
            for name in archive.namelist():
                if name.endswith(".xml"):
                    ElementTree.fromstring(archive.read(name))
            result["xml"] = True
        text = odt_text(path)
        unique = sorted({item["text"] for item in commits if item.get("text") != "\n"})
        for anchor in unique:
            expected = sum(item.get("text", "").count(anchor) for item in commits)
            actual = text.count(anchor)
            result["anchors"].append(
                {"text": anchor, "expectedCount": expected, "actualCount": actual,
                 "pass": actual == expected}
            )
    except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as error:
        result["error"] = {"name": type(error).__name__, "message": str(error)}
    result["pass"] = (
        result["zip"] and result["crc"] and result["xml"]
        and bool(result["anchors"])
        and all(item["pass"] for item in result["anchors"])
    )
    return result


def desktop_pdf_roundtrip(source: Path, output: Path, timeout: int = 180) -> dict[str, Any]:
    soffice = shutil.which("soffice") or "soffice"
    pdfinfo = shutil.which("pdfinfo") or "pdfinfo"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="r7-desktop-") as temporary:
        temporary_path = Path(temporary)
        profile = temporary_path / "profile"
        command = [
            soffice, "--headless", "--nologo", "--nodefault",
            "--nofirststartwizard", "--norestore",
            f"-env:UserInstallation={profile.resolve().as_uri()}",
            "--convert-to", "pdf:writer_pdf_Export",
            "--outdir", str(temporary_path), str(source.resolve()),
        ]
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=timeout
        )
        generated = temporary_path / f"{source.stem}.pdf"
        if completed.returncode == 0 and generated.is_file():
            shutil.copyfile(generated, output)
    info = subprocess.run(
        [pdfinfo, str(output)], check=False, capture_output=True, text=True, timeout=30
    ) if output.is_file() else None
    return {
        "command": command,
        "returnCode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "pdf": str(output),
        "pdfBytes": output.stat().st_size if output.is_file() else None,
        "pdfSha256": sha256(output) if output.is_file() else None,
        "pdfinfo": info.stdout.strip() if info else None,
        "pass": completed.returncode == 0
        and output.is_file()
        and output.stat().st_size > 0
        and info is not None
        and info.returncode == 0,
    }
