#!/usr/bin/env python3
"""Deterministic R8-A delivery and fault-discovery HTTP server."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import threading
import time
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit


CANARY = b"R8-DELIVERY-CANARY-v1\n"
HASHED_PATH = re.compile(r"\.[0-9a-f]{12,64}\.(?:js|wasm|data|metadata|json)$")


class RequestJournal:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: list[dict[str, Any]] = []

    def append(self, item: dict[str, Any]) -> None:
        with self._lock:
            self._items.append(item)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class R8DeliveryServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler,
        *,
        role: str,
        allow_origin: str | None,
    ) -> None:
        super().__init__(server_address, handler)
        self.role = role
        self.allow_origin = allow_origin
        self.journal = RequestJournal()


class R8DeliveryHandler(SimpleHTTPRequestHandler):
    server: R8DeliveryServer

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".css": "text/css; charset=utf-8",
        ".data": "application/octet-stream",
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".metadata": "application/json; charset=utf-8",
        ".wasm": "application/wasm",
    }

    def log_message(self, format: str, *args: object) -> None:
        # The machine-readable journal is the canonical evidence.
        return

    def send_response(self, code: int, message: str | None = None) -> None:
        self._r8_status = code
        super().send_response(code, message)

    def _scenario(self) -> str:
        query = parse_qs(urlsplit(self.path).query)
        return query.get("scenario", ["ok"])[0]

    def _fault(self) -> str:
        query = parse_qs(urlsplit(self.path).query)
        return query.get("serverFault", query.get("fault", [self._scenario()]))[0]

    def _representation(self) -> str:
        query = parse_qs(urlsplit(self.path).query)
        return query.get("representation", ["auto"])[0]

    def _cors_enabled(self) -> bool:
        return self._fault() != "no-cors"

    def _corp_enabled(self) -> bool:
        return self._fault() != "no-corp"

    def end_headers(self) -> None:
        path = urlsplit(self.path).path
        self.send_header("X-Content-Type-Options", "nosniff")
        if self.server.role == "app":
            if self._fault() != "no-coop":
                self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            if self._fault() != "no-coep":
                self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        else:
            if self._corp_enabled():
                self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
            if self.server.allow_origin and self._cors_enabled():
                self.send_header("Access-Control-Allow-Origin", self.server.allow_origin)
                self.send_header(
                    "Access-Control-Expose-Headers",
                    "Cache-Control, Content-Encoding, Cross-Origin-Resource-Policy",
                )
                self.send_header("Vary", "Origin")
        if HASHED_PATH.search(path):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _write_json(self, value: Any, status: int = 200) -> None:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _write_canary(self, scenario: str) -> None:
        if scenario == "http-500":
            self._write_json({"code": "R8_INTENTIONAL_500", "scenario": scenario}, 500)
            return
        if scenario == "delay":
            time.sleep(0.25)
        payload = CANARY if scenario != "wrong-bytes" else b"R8-WRONG-BYTES\n"
        media_type = "text/plain; charset=utf-8" if scenario == "wrong-type" else "application/octet-stream"
        if scenario == "gzip":
            payload = gzip.compress(payload, compresslevel=9, mtime=0)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", media_type)
        if scenario == "gzip":
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            transmitted = payload[:-7] if scenario == "truncated" else payload
            self.wfile.write(transmitted)
            self.wfile.flush()
        if scenario == "truncated":
            self.close_connection = True

    def _static_source(self, path: Path, fault: str) -> Path:
        if fault != "stale-release":
            return path
        query = parse_qs(urlsplit(self.path).query)
        stale_release = query.get("staleReleaseId", [""])[0]
        if not re.fullmatch(r"writer-review-[0-9a-f]{16}", stale_release):
            return path.with_name("__invalid_stale_release__")
        parts = list(path.parts)
        try:
            index = next(i for i, part in enumerate(parts) if part == "releases")
        except StopIteration:
            return path.with_name("__invalid_stale_path__")
        if index + 1 >= len(parts):
            return path.with_name("__invalid_stale_path__")
        parts[index + 1] = stale_release
        return Path(*parts)

    @staticmethod
    def _mutate_manifest(payload: bytes, fault: str) -> bytes:
        value = json.loads(payload)
        artifacts = value.get("artifacts", [])
        if fault == "manifest-bad-schema":
            value["schemaVersion"] = 999
        elif fault == "manifest-bad-release":
            value["releaseId"] = "writer-review-0000000000000000"
        elif fault == "manifest-duplicate-role" and artifacts:
            artifacts[1]["role"] = artifacts[0]["role"]
        elif fault == "manifest-unknown-role" and artifacts:
            artifacts[0]["role"] = "unknown-role"
        elif fault == "manifest-path-traversal" and artifacts:
            artifacts[0]["url"] = "../escape.html"
        elif fault == "manifest-credential-url" and artifacts:
            artifacts[0]["url"] = "https://user:secret@127.0.0.1/escape"
        elif fault == "manifest-unknown-scheme" and artifacts:
            artifacts[0]["url"] = "data:text/plain,escape"
        elif fault == "manifest-missing-role" and artifacts:
            artifacts.pop()
        else:
            raise ValueError(f"unknown manifest mutation: {fault}")
        return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"

    def _write_static(self) -> None:
        path_text = urlsplit(self.path).path
        fault = self._fault()
        if fault in {"http-404", "http-500"}:
            status = HTTPStatus.NOT_FOUND if fault == "http-404" else HTTPStatus.INTERNAL_SERVER_ERROR
            self._write_json({"code": f"R8_INTENTIONAL_{status}", "fault": fault}, status)
            return
        if fault == "redirect-cross-origin":
            query = parse_qs(urlsplit(self.path).query)
            target = urlsplit(query.get("redirectTargetOrigin", [""])[0])
            if (target.scheme not in {"http", "https"}
                    or target.hostname not in {"127.0.0.1", "localhost"}
                    or target.username or target.password or target.path not in {"", "/"}
                    or target.query or target.fragment or target.port is None):
                self.send_error(HTTPStatus.BAD_REQUEST, "invalid redirect target origin")
                return
            remaining = [
                (key, value) for key, values in query.items() for value in values
                if key not in {"fault", "redirectTargetOrigin"}
            ]
            location = f"{target.scheme}://{target.netloc}{path_text}"
            if remaining:
                location += f"?{urlencode(remaining)}"
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if fault == "delay":
            time.sleep(0.25)
        original = Path(self.translate_path(path_text))
        source = self._static_source(original, fault)
        if not source.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        representation = self._representation()
        if representation not in {"auto", "identity", "gzip"}:
            self.send_error(HTTPStatus.BAD_REQUEST, "unknown representation")
            return
        accepts_gzip = "gzip" in self.headers.get("Accept-Encoding", "").lower()
        use_gzip = representation == "gzip" or (representation == "auto" and accepts_gzip)
        encoded_source = Path(f"{source}.gz") if use_gzip else source
        if use_gzip and not encoded_source.is_file():
            if representation == "gzip":
                self.send_error(HTTPStatus.NOT_ACCEPTABLE, "gzip representation unavailable")
                return
            use_gzip = False
            encoded_source = source
        decoded = source.read_bytes()
        payload = encoded_source.read_bytes()
        if fault.startswith("manifest-"):
            try:
                decoded = self._mutate_manifest(decoded, fault)
            except (ValueError, json.JSONDecodeError) as error:
                self.send_error(HTTPStatus.BAD_REQUEST, str(error))
                return
            payload = gzip.compress(decoded, compresslevel=9, mtime=0) if use_gzip else decoded
        if fault == "wrong-bytes":
            wrong = bytes([decoded[0] ^ 0x01]) + decoded[1:] if decoded else b"x"
            payload = gzip.compress(wrong, compresslevel=9, mtime=0) if use_gzip else wrong
        media_type = self.guess_type(str(original))
        if fault == "wrong-type":
            media_type = "text/plain; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", media_type)
        if use_gzip or fault == "wrong-encoding":
            self.send_header("Content-Encoding", "gzip")
        if use_gzip:
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            transmitted = payload[:-7] if fault == "truncated" and len(payload) > 7 else payload
            self.wfile.write(transmitted)
            self.wfile.flush()
        if fault == "truncated":
            self.close_connection = True

    def _dispatch(self) -> None:
        path = urlsplit(self.path).path
        if path == "/__r8__/health":
            self._write_json({
                "ok": True,
                "role": self.server.role,
                "allowOrigin": self.server.allow_origin,
            })
            return
        if path == "/__r8__/requests":
            self._write_json({"requests": self.server.journal.snapshot()})
            return
        if path == "/__r8__/canary":
            self._write_canary(self._scenario())
            return
        self._write_static()

    def _serve_and_record(self) -> None:
        started = time.monotonic()
        self._r8_status = 0
        scenario = self._fault()
        try:
            self._dispatch()
        finally:
            self.server.journal.append({
                "method": self.command,
                "path": urlsplit(self.path).path,
                "scenario": scenario,
                "representation": self._representation(),
                "status": self._r8_status,
                "durationMs": round((time.monotonic() - started) * 1000, 3),
            })

    def do_GET(self) -> None:
        self._serve_and_record()

    def do_HEAD(self) -> None:
        self._serve_and_record()

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path == "/__r8__/reset":
            self.server.journal.clear()
            self._write_json({"reset": True})
            return
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)


def create_server(
    root: Path,
    host: str,
    port: int,
    role: str,
    allow_origin: str | None = None,
) -> R8DeliveryServer:
    if role not in {"app", "artifact"}:
        raise ValueError(f"unknown R8 server role: {role}")
    handler = partial(R8DeliveryHandler, directory=str(root.resolve()))
    return R8DeliveryServer(
        (host, port),
        handler,
        role=role,
        allow_origin=allow_origin,
    )


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=project / "dist")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--role", choices=("app", "artifact"), default="app")
    parser.add_argument("--allow-origin")
    args = parser.parse_args()

    server = create_server(args.root, args.host, args.port, args.role, args.allow_origin)
    actual_port = server.server_address[1]
    print(json.dumps({
        "root": str(args.root.resolve()),
        "origin": f"http://{args.host}:{actual_port}",
        "role": args.role,
        "allowOrigin": args.allow_origin,
    }, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
