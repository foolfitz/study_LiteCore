#!/usr/bin/env python3
"""S-11: network capture for M5 (paste as Markdown must not reach the network).

Arms: findings/evidence/link-batch-v21/shakedown/ARMS.md S-11; ARMS-item2.md M5, DM-12 and §9 (ruling A,
plus: the positive control must cross the SAME capture -- the worker's `probe.wasm` GET must appear in
the PROXY's own log, with loopback forced through the proxy; without it the round is NOT_ESTABLISHED).

  LoggingProxy()             an HTTP proxy on 127.0.0.1:<free port>.  Absolute-form requests are
                             forwarded upstream (headers kept, hop-by-hop ones dropped, body streamed);
                             CONNECT is tunnelled (HTTPS, WebSocket).  EVERY request is logged before it
                             is forwarded -- also when the upstream refuses (port 9) or never answers --
                             so an attempt is visible whatever happens to it.  .entries(), .close()
  TargetListeners()          the corpus's targets: 127.0.0.1:18765 logs and answers 404 (501 for
                             OPTIONS/PROPFIND, as rounds 1-2), 18766 accepts and never answers (round 1's
                             tarpit), 18768 accepts, reads 64 bytes and closes (round 2's closer; also on
                             ::1 when it can bind, since `localhost` may resolve there).  Port 9 cannot be
                             listened on unprivileged: only the proxy sees an attempt there.  .entries()
  firefox_prefs(port)        the prefs that force every Firefox request through the proxy, loopback too
  ProxiedChrome(port)        ChromeSession started with --proxy-server and --proxy-bypass-list=<-loopback>;
                             it keeps CDP Network events (page and every auto-attached worker session)
                             as a supplementary record: `attach_workers()`, `drain_events()`
  positive_control(entries, mirror_port, profile)  the probe.wasm GET in the proxy log, or None
  outside_mirror(entries, mirror_port, t0, t1)     entries in [t0, t1] to any origin but the mirror

The mirror server's port must not be 9, 18765, 18766 or 18768 (the runner checks).
"""
from __future__ import annotations

import http.client
import json
import select
import socket
import socketserver
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_browser_probe as rbp  # noqa: E402

TARGET_PORTS = {"listener": 18765, "tarpit": 18766, "closer": 18768}
FORBIDDEN_MIRROR_PORTS = {9, 18765, 18766, 18768}
HOP = {"connection", "keep-alive", "proxy-connection", "proxy-authenticate", "proxy-authorization", "te",
       "trailers", "transfer-encoding", "upgrade"}


class _ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "v21-proxy"

    def log_message(self, *args):
        pass

    def _record(self, **entry) -> dict:
        entry.setdefault("t", time.time())
        with self.server.lock:
            self.server.log.append(entry)
        return entry

    def do_CONNECT(self):  # noqa: N802
        host, _, port = self.path.rpartition(":")
        entry = self._record(method="CONNECT", host=host.strip("[]"), port=int(port or 0), path=None)
        try:
            upstream = socket.create_connection((host.strip("[]"), int(port)), timeout=5)
        except OSError as error:
            entry["error"] = f"{type(error).__name__}: {error}"
            self.send_response(502)
            self.send_header("Content-Length", "0")
            self.end_headers()
            self.close_connection = True
            return
        entry["connected"] = True
        self.send_response(200, "Connection Established")
        self.end_headers()
        self.close_connection = True
        client = self.connection
        try:
            sockets = [client, upstream]
            while True:
                readable, _, broken = select.select(sockets, [], sockets, 30)
                if broken or not readable:
                    break
                done = False
                for sock in readable:
                    data = sock.recv(65536)
                    if not data:
                        done = True
                        break
                    (upstream if sock is client else client).sendall(data)
                if done:
                    break
        except OSError:
            pass
        finally:
            upstream.close()

    def _forward(self):
        url = urlsplit(self.path)
        host = url.hostname or ""
        port = url.port or (443 if url.scheme == "https" else 80)
        entry = self._record(method=self.command, host=host, port=port,
                             path=(url.path or "/") + (("?" + url.query) if url.query else ""))
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        headers["Connection"] = "close"
        try:
            upstream = http.client.HTTPConnection(host, port, timeout=30)
            upstream.request(self.command, entry["path"], body=body, headers=headers)
            response = upstream.getresponse()
        except OSError as error:
            entry["error"] = f"{type(error).__name__}: {error}"
            self.send_response(502)
            self.send_header("Content-Length", "0")
            self.end_headers()
            self.close_connection = True
            return
        entry["status"] = response.status
        self.send_response(response.status, response.reason)
        for key, value in response.getheaders():
            if key.lower() not in HOP and key.lower() != "content-length":
                self.send_header(key, value)
        declared = response.getheader("Content-Length")
        if declared is not None:
            self.send_header("Content-Length", declared)
        else:
            self.close_connection = True
        self.send_header("Connection", "close" if self.close_connection else "keep-alive")
        self.end_headers()
        sent = 0
        if self.command != "HEAD":
            while True:
                chunk = response.read(262144)
                if not chunk:
                    break
                self.wfile.write(chunk)
                sent += len(chunk)
        entry["bytes"] = sent
        upstream.close()

    do_GET = do_POST = do_HEAD = do_PUT = do_DELETE = do_OPTIONS = do_PATCH = do_PROPFIND = _forward  # noqa: N815


class LoggingProxy:
    def __init__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _ProxyHandler)
        self.server.daemon_threads = True
        self.server.log = []
        self.server.lock = threading.Lock()
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def entries(self) -> list[dict]:
        with self.server.lock:
            return [dict(e) for e in self.server.log]

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class _ListenerHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _record(self):
        with self.server.lock:
            self.server.log.append({"t": time.time(), "target": "listener", "port": TARGET_PORTS["listener"],
                                    "method": self.command, "path": self.path})

    def _404(self):
        self._record()
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _501(self):
        self._record()
        self.send_error(501, "Unsupported method (%r)" % self.command)

    do_GET = do_HEAD = _404  # noqa: N815
    do_OPTIONS = do_PROPFIND = do_POST = _501  # noqa: N815


class TargetListeners:
    """Every socket a corpus URL names, except port 9."""

    def __init__(self):
        self.lock = threading.Lock()
        self.log: list[dict] = []
        self.closed = False
        self.http = ThreadingHTTPServer(("127.0.0.1", TARGET_PORTS["listener"]), _ListenerHandler)
        self.http.daemon_threads = True
        self.http.log = self.log
        self.http.lock = self.lock
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.raw = []
        for name in ("tarpit", "closer"):
            for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
                try:
                    sock = socket.socket(family, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind((address, TARGET_PORTS[name]))
                    sock.listen(16)
                except OSError:
                    if family == socket.AF_INET:
                        raise
                    continue
                self.raw.append(sock)
                threading.Thread(target=self._serve, args=(sock, name, address), daemon=True).start()
        self.held: list[socket.socket] = []

    def _serve(self, sock, name, address):
        while not self.closed:
            try:
                conn, peer = sock.accept()
            except OSError:
                return
            entry = {"t": time.time(), "target": name, "port": TARGET_PORTS[name], "address": address}
            if name == "tarpit":
                self.held.append(conn)          # accepted, never answered (closed at the end)
            else:
                conn.settimeout(1.0)
                try:
                    entry["firstBytesHex"] = conn.recv(64)[:8].hex()
                except OSError:
                    entry["firstBytesHex"] = ""
                conn.close()
            with self.lock:
                self.log.append(entry)

    def entries(self) -> list[dict]:
        with self.lock:
            return [dict(e) for e in self.log]

    def close(self) -> None:
        self.closed = True
        self.http.shutdown()
        self.http.server_close()
        for sock in self.raw + self.held:
            try:
                sock.close()
            except OSError:
                pass


# The browser's own background traffic (updaters, safe browsing, push, prefetch) goes through the proxy too
# and lands in M5's item windows as "an origin other than the mirror's": the item-2 smoke saw Chrome's
# component updater, GCM and safe browsing in 8 of 38 windows (smoke/item2/ R5).  These switch it off; a
# page's own requests are not affected.  The Firefox set was not exercised before the Firefox evidence run.
QUIET_CHROME = ("--disable-background-networking", "--disable-component-update", "--disable-sync",
                "--disable-default-apps", "--disable-domain-reliability", "--disable-client-side-phishing-detection",
                "--no-pings", "--metrics-recording-only",
                "--disable-features=OptimizationHints,OptimizationGuideModelDownloading,OptimizationHintsFetching,"
                "OptimizationTargetPrediction,MediaRouter,Translate,AutofillServerCommunication,"
                "CertificateTransparencyComponentUpdater")
QUIET_FIREFOX: dict[str, Any] = {
    "network.captive-portal-service.enabled": False, "network.connectivity-service.enabled": False,
    "browser.safebrowsing.malware.enabled": False, "browser.safebrowsing.phishing.enabled": False,
    "browser.safebrowsing.downloads.enabled": False, "browser.safebrowsing.blockedURIs.enabled": False,
    "app.update.disabledForTesting": True, "datareporting.policy.dataSubmissionEnabled": False,
    "datareporting.healthreport.uploadEnabled": False, "toolkit.telemetry.enabled": False,
    "dom.push.connection.enabled": False, "network.dns.disablePrefetch": True, "network.prefetch-next": False,
    "network.http.speculative-parallel-limit": 0, "browser.newtabpage.enabled": False,
    "extensions.update.enabled": False, "extensions.getAddons.cache.enabled": False,
    "media.gmp-manager.updateEnabled": False, "browser.region.network.url": "", "browser.search.update": False,
}


def firefox_prefs(port: int) -> dict[str, Any]:
    return {**QUIET_FIREFOX,
            "network.proxy.type": 1, "network.proxy.http": "127.0.0.1", "network.proxy.http_port": port,
            "network.proxy.ssl": "127.0.0.1", "network.proxy.ssl_port": port,
            "network.proxy.no_proxies_on": "", "network.proxy.allow_hijacking_localhost": True,
            "network.proxy.share_proxy_settings": True}


class ProxiedChrome(rbp.ChromeSession):
    """run_browser_probe.ChromeSession's start-up with two more flags, and CDP events kept."""

    KEEP = {"Network.requestWillBeSent", "Network.webSocketCreated", "Network.loadingFailed",
            "Target.attachedToTarget"}

    def __init__(self, proxy_port: int, cache_mode: str = "cold"):  # noqa: D401 -- mirrors the base
        import shutil
        import subprocess
        import tempfile
        self.events: list[dict] = []
        self.proxy_port = proxy_port
        chrome = shutil.which("google-chrome") or shutil.which("chromium")
        if not chrome:
            raise RuntimeError("Chrome/Chromium is unavailable")
        self.profile = tempfile.TemporaryDirectory(prefix="wasm-sdk-probe-chrome-")
        self.profile_dir = Path(self.profile.name)
        self.port = rbp.free_port()
        self.process = subprocess.Popen(
            [chrome, "--headless=new", f"--remote-debugging-port={self.port}", "--remote-allow-origins=*",
             f"--user-data-dir={self.profile_dir}", "--no-first-run", "--no-default-browser-check",
             f"--proxy-server=http://127.0.0.1:{proxy_port}", "--proxy-bypass-list=<-loopback>",
             "--password-store=basic", *QUIET_CHROME, "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        self.base_url = f"http://127.0.0.1:{self.port}"
        version = rbp.wait_http(f"{self.base_url}/json/version")
        self.version = version.get("Browser", "unknown")
        targets = rbp.wait_http(f"{self.base_url}/json/list")
        page = next(target for target in targets if target["type"] == "page")
        self.websocket = rbp.websocket_connect(page["webSocketDebuggerUrl"], origin="http://127.0.0.1")
        self.next_id = 0
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Network.enable")
        self.call("Network.setCacheDisabled", {"cacheDisabled": cache_mode == "cold"})
        time.sleep(5)    # finding 112's warm-up, as the base class

    def call(self, method: str, params: dict | None = None, timeout: float = 180,
             session_id: str | None = None) -> dict:
        self.next_id += 1
        message_id = self.next_id
        message = {"id": message_id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        self.websocket.send(json.dumps(message))
        while True:
            response = json.loads(self.websocket.recv(timeout=timeout))
            if "id" not in response:
                if response.get("method") in self.KEEP:
                    self.events.append(response)
                    if response["method"] == "Target.attachedToTarget":
                        self._enable_attached(response["params"])
                continue
            if response.get("id") != message_id:
                continue
            if "error" in response:
                raise RuntimeError(f"CDP {method}: {response['error']}")
            return response.get("result", {})

    def _enable_attached(self, params: dict) -> None:
        sid = params.get("sessionId")
        if not sid:
            return
        for method, args in (("Network.enable", {}),
                             ("Target.setAutoAttach", {"autoAttach": True, "flatten": True,
                                                       "waitForDebuggerOnStart": False}),
                             ("Runtime.runIfWaitingForDebugger", {})):
            self.next_id += 1
            self.websocket.send(json.dumps({"id": self.next_id, "method": method, "params": args,
                                            "sessionId": sid}))

    def attach_workers(self) -> None:
        self.call("Target.setAutoAttach", {"autoAttach": True, "flatten": True, "waitForDebuggerOnStart": False})

    def drain_events(self) -> list[dict]:
        self.call("Runtime.evaluate", {"expression": "1"})
        events, self.events = self.events, []
        return events


def cdp_requests(events: list[dict]) -> list[dict]:
    out = []
    for event in events:
        params = event.get("params", {})
        if event.get("method") == "Network.requestWillBeSent":
            out.append({"kind": "request", "url": params.get("request", {}).get("url"),
                        "session": event.get("sessionId"), "wallTime": params.get("wallTime")})
        elif event.get("method") == "Network.webSocketCreated":
            out.append({"kind": "websocket", "url": params.get("url"), "session": event.get("sessionId")})
        elif event.get("method") == "Target.attachedToTarget":
            info = params.get("targetInfo", {})
            out.append({"kind": "attached", "type": info.get("type"), "url": (info.get("url") or "")[-80:],
                        "session": params.get("sessionId")})
    return out


def positive_control(entries: list[dict], mirror_port: int, profile: str) -> dict | None:
    """The worker's probe.wasm GET, in the proxy's log, to the mirror server.  `profile` has no default: it is
    the profile the mirror was built with (ruling 6, v22: a v21 default voided M5 when the mirror moved)."""
    for e in entries:
        if (e.get("method") == "GET" and e.get("port") == mirror_port
                and e.get("host") in ("127.0.0.1", "localhost")
                and (e.get("path") or "").split("?")[0].endswith(f"profiles/{profile}/probe.wasm")):
            return e
    return None


def outside_mirror(entries: list[dict], mirror_port: int, t0: float, t1: float) -> list[dict]:
    """Every proxy or listener entry in [t0, t1] that is not a request to the mirror server."""
    out = []
    for e in entries:
        if not (t0 <= e.get("t", 0) <= t1):
            continue
        if e.get("port") == mirror_port and e.get("host") in ("127.0.0.1", "localhost") and e.get("method") != "CONNECT":
            continue
        out.append(e)
    return out
