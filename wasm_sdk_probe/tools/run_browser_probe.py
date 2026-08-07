#!/usr/bin/env python3
"""Run the R1 browser harness through Chrome CDP or Firefox WebDriver."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from websockets.sync.client import connect as websocket_connect


WEBDRIVER_ELEMENT_KEY = "element-6066-11e4-a52e-4f735466cecf"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(method: str, url: str, payload: object | None = None,
              timeout: float = 10) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        raw = error.read()
        raise RuntimeError(
            f"HTTP {error.code} for {method} {url}: {raw.decode(errors='replace')}"
        ) from error
    return json.loads(raw) if raw else None


def wait_http(url: str, timeout: float = 20) -> Any:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return http_json("GET", url)
        except Exception as error:
            last_error = error
            time.sleep(0.2)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def _browser_stderr_path(prefix: str) -> Path | None:
    """Opt-in destination for browser/driver chatter, or None to drop it.

    Set OXSDK_BROWSER_STDERR_DIR to a directory to keep it.  Each session gets
    its own file (the pid keeps concurrent or batched sessions apart), so a
    campaign that starts one browser per batch can be accounted for per batch.
    """
    root = os.environ.get("OXSDK_BROWSER_STDERR_DIR")
    if not root:
        return None
    directory = Path(root)
    directory.mkdir(parents=True, exist_ok=True)
    index = 1
    while (directory / f"{prefix}-{index:03d}.log").exists():
        index += 1
    return directory / f"{prefix}-{index:03d}.log"


class FirefoxSession:
    def __init__(self, cache_mode: str, profile_dir: Path | None = None,
                 extra_prefs: dict[str, object] | None = None):
        geckodriver = shutil.which("geckodriver") or "/snap/bin/geckodriver"
        if not Path(geckodriver).exists():
            raise RuntimeError("geckodriver is unavailable")
        self.port = free_port()
        # DEVNULL, not PIPE: nothing ever read these pipes, and geckodriver
        # forwards the browser's chatter -- a filled 64 KiB pipe wedges the
        # whole browser at a deterministic depth (finding 023).
        #
        # OXSDK_BROWSER_STDERR_DIR opts into keeping that chatter instead of
        # dropping it, for runs that need to *measure* it (finding 014 left the
        # driver pipe as an unexcluded explanation for R8-D's 900 s stalls).
        # It writes to a real file, never a pipe, so enabling it cannot
        # reintroduce finding 023.  Default stays DEVNULL.
        self.stderr_path = _browser_stderr_path("geckodriver")
        self.stderr_file = (
            open(self.stderr_path, "wb") if self.stderr_path else None
        )
        self.process = subprocess.Popen(
            [geckodriver, "--port", str(self.port), "--log", "error"],
            stdout=self.stderr_file or subprocess.DEVNULL,
            stderr=subprocess.STDOUT if self.stderr_file else subprocess.DEVNULL,
        )
        self.base_url = f"http://127.0.0.1:{self.port}"
        wait_http(f"{self.base_url}/status")

        prefs: dict[str, object] = {
            "browser.shell.checkDefaultBrowser": False,
            "browser.startup.page": 0,
        }
        if cache_mode == "cold":
            prefs.update({
                "browser.cache.disk.enable": False,
                "browser.cache.memory.enable": False,
                "network.http.use-cache": False,
            })
        if extra_prefs:
            prefs.update(extra_prefs)
        firefox_args = ["-headless"]
        if profile_dir is not None:
            profile_dir = profile_dir.resolve()
            profile_dir.mkdir(parents=True, exist_ok=True)
            firefox_args.extend(["-profile", str(profile_dir)])
        self.profile_dir = profile_dir
        response = self.request(
            "POST",
            "/session",
            {
                "capabilities": {
                    "alwaysMatch": {
                        "browserName": "firefox",
                        "moz:firefoxOptions": {
                            "args": firefox_args,
                            "prefs": prefs,
                        },
                    }
                }
            },
        )["value"]
        self.session_id = response["sessionId"]
        self.version = response["capabilities"].get("browserVersion", "unknown")

    def request(self, method: str, path: str,
                payload: object | None = None, timeout: float = 180) -> Any:
        return http_json(method, self.base_url + path, payload, timeout)

    def command(self, method: str, suffix: str,
                payload: object | None = None) -> Any:
        return self.request(
            method, f"/session/{self.session_id}{suffix}", payload
        )["value"]

    def navigate(self, url: str) -> None:
        self.command("POST", "/url", {"url": url})

    def execute(self, script: str, arguments: list[Any] | None = None) -> Any:
        return self.command(
            "POST", "/execute/sync", {"script": script, "args": arguments or []}
        )

    def set_file(self, selector: str, path: Path) -> None:
        element = self.command(
            "POST", "/element", {"using": "css selector", "value": selector}
        )[WEBDRIVER_ELEMENT_KEY]
        value = str(path.resolve())
        self.command(
            "POST", f"/element/{element}/value",
            {"text": value, "value": list(value)},
        )

    def click(self, selector: str) -> None:
        element = self.command(
            "POST", "/element", {"using": "css selector", "value": selector}
        )[WEBDRIVER_ELEMENT_KEY]
        self.command("POST", f"/element/{element}/click", {})

    def screenshot(self) -> bytes:
        return base64.b64decode(self.command("GET", "/screenshot"))

    def close(self) -> None:
        if hasattr(self, "session_id"):
            try:
                self.request("DELETE", f"/session/{self.session_id}")
            except Exception:
                pass
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)
        if getattr(self, "stderr_file", None) is not None:
            self.stderr_file.close()


class ChromeSession:
    def __init__(self, cache_mode: str, profile_dir: Path | None = None):
        chrome = shutil.which("google-chrome") or shutil.which("chromium")
        if not chrome:
            raise RuntimeError("Chrome/Chromium is unavailable")
        self.profile = (
            tempfile.TemporaryDirectory(prefix="wasm-sdk-probe-chrome-")
            if profile_dir is None else None
        )
        self.profile_dir = (
            Path(self.profile.name) if self.profile is not None else profile_dir.resolve()
        )
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.port = free_port()
        self.process = subprocess.Popen(
            [
                chrome,
                "--headless=new",
                f"--remote-debugging-port={self.port}",
                "--remote-allow-origins=*",
                f"--user-data-dir={self.profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "about:blank",
            ],
            # DEVNULL, not PIPE: nothing ever read these pipes, and a filled
            # 64 KiB pipe wedges the whole browser at a deterministic depth
            # (finding 023).
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.base_url = f"http://127.0.0.1:{self.port}"
        version = wait_http(f"{self.base_url}/json/version")
        self.version = version.get("Browser", "unknown")
        targets = wait_http(f"{self.base_url}/json/list")
        page = next(target for target in targets if target["type"] == "page")
        self.websocket = websocket_connect(
            page["webSocketDebuggerUrl"], origin="http://127.0.0.1"
        )
        self.next_id = 0
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Network.enable")
        self.call("Network.setCacheDisabled", {"cacheDisabled": cache_mode == "cold"})

    def call(self, method: str, params: dict[str, Any] | None = None,
             timeout: float = 180) -> dict[str, Any]:
        self.next_id += 1
        message_id = self.next_id
        self.websocket.send(json.dumps({
            "id": message_id,
            "method": method,
            "params": params or {},
        }))
        while True:
            response = json.loads(self.websocket.recv(timeout=timeout))
            if response.get("id") != message_id:
                continue
            if "error" in response:
                raise RuntimeError(f"CDP {method}: {response['error']}")
            return response.get("result", {})

    def evaluate(self, expression: str) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        ).get("result", {})
        if result.get("subtype") == "error" or "exceptionDetails" in result:
            raise RuntimeError(f"CDP evaluation failed: {result}")
        return result.get("value")

    def navigate(self, url: str) -> None:
        self.call("Page.navigate", {"url": url})
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            try:
                if self.evaluate(
                    "document.readyState === 'complete' && "
                    "typeof globalThis.__probe_metrics === 'object'"
                ):
                    return
            except Exception:
                pass
            time.sleep(0.2)
        raise RuntimeError("Chrome page did not finish loading")

    def set_file(self, selector: str, path: Path) -> None:
        root = self.call("DOM.getDocument")["root"]["nodeId"]
        node = self.call(
            "DOM.querySelector", {"nodeId": root, "selector": selector}
        )["nodeId"]
        self.call("DOM.setFileInputFiles", {"nodeId": node, "files": [str(path.resolve())]})

    def click(self, selector: str) -> None:
        self.evaluate(f"document.querySelector({json.dumps(selector)}).click(); true")

    def screenshot(self) -> bytes:
        result = self.call("Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(result["data"])

    def close(self) -> None:
        try:
            self.call("Browser.close", timeout=10)
        except Exception:
            pass
        try:
            self.websocket.close()
        except Exception:
            pass
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)
        if self.profile is not None:
            self.profile.cleanup()


def browser_state(session) -> dict[str, Any]:
    script = """
        return JSON.stringify({
          status: document.querySelector('#status')?.textContent || '',
          log: document.querySelector('#log')?.textContent || '',
          metrics: globalThis.__probe_metrics || null
        });
    """
    if isinstance(session, ChromeSession):
        raw = session.evaluate(f"(() => {{{script}}})()")
    else:
        raw = session.execute(script)
    return json.loads(raw)


def wait_for_run(session, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_state = browser_state(session)
        runs = (last_state.get("metrics") or {}).get("runs") or []
        if runs and runs[-1].get("pass"):
            return last_state
        status = last_state.get("status", "")
        if status.startswith("error:") or status in {
            "action failed", "event handling error", "module initialization failed"
        }:
            raise RuntimeError(f"browser probe failed ({status}):\n{last_state.get('log', '')}")
        time.sleep(0.5)
    raise RuntimeError(
        f"browser probe timed out with status {last_state.get('status')}:\n"
        f"{last_state.get('log', '')}"
    )


def wait_for_ready(session, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_state = browser_state(session)
        status = last_state.get("status", "")
        if status == "ready":
            return last_state
        if status.startswith("error:") or status in {
            "action failed", "event handling error", "module initialization failed"
        }:
            raise RuntimeError(f"browser warmup failed ({status}):\n{last_state.get('log', '')}")
        time.sleep(0.5)
    raise RuntimeError(
        f"browser warmup timed out with status {last_state.get('status')}:\n"
        f"{last_state.get('log', '')}"
    )


def get_output_base64(session) -> str:
    expression = "globalThis.__probe_get_output_base64()"
    if isinstance(session, ChromeSession):
        return str(session.evaluate(expression))
    return str(session.execute(f"return {expression};"))


def run_sample(session, url: str, document: Path, timeout: float) -> dict[str, Any]:
    session.navigate(url)
    session.set_file("#file", document)
    session.click("#run-all")
    state = wait_for_run(session, timeout)
    state["output_base64"] = get_output_base64(session)
    state["screenshot"] = session.screenshot()
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--doc", type=Path, required=True)
    parser.add_argument("--cache", choices=("cold", "hot"), required=True)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--url", default="http://127.0.0.1:8765/index.html")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.doc.is_file():
        raise SystemExit(f"missing document: {args.doc}")
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
    session = session_class(args.cache)
    summary: dict[str, Any] = {
        "browser": args.browser,
        "browser_version": session.version,
        "cache": args.cache,
        "doc": args.doc.name,
        "samples": [],
    }
    try:
        if args.cache == "hot":
            warmup_separator = "&" if "?" in args.url else "?"
            session.navigate(f"{args.url}{warmup_separator}cache=warmup")
            wait_for_ready(session, args.timeout)

        for sample_index in range(args.samples):
            separator = "&" if "?" in args.url else "?"
            url = (
                f"{args.url}{separator}cache={args.cache}"
                f"&sample={sample_index + 1}"
            )
            state = run_sample(session, url, args.doc, args.timeout)
            prefix = f"{args.browser}-{args.doc.stem}-{args.cache}-{sample_index + 1}"
            (args.evidence_dir / f"{prefix}.log.txt").write_text(
                state["log"], encoding="utf-8"
            )
            (args.evidence_dir / f"{prefix}.png").write_bytes(state["screenshot"])
            output = base64.b64decode(state["output_base64"])
            (args.evidence_dir / f"{prefix}-out.odt").write_bytes(output)
            run_metrics = state["metrics"]["runs"][-1]
            summary["samples"].append({
                "run": run_metrics,
                "memory": state["metrics"].get("memory", []),
                "output_bytes": len(output),
            })
            print(json.dumps({"sample": sample_index + 1, "run": run_metrics}, ensure_ascii=False))
    finally:
        session.close()

    output_path = args.evidence_dir / (
        f"{args.browser}-{args.doc.stem}-{args.cache}-summary.json"
    )
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(output_path)


if __name__ == "__main__":
    main()
