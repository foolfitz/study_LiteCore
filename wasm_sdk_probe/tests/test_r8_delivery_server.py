from __future__ import annotations

import gzip
import http.client
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from r8_delivery_server import CANARY, create_server  # noqa: E402


class R8DeliveryServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="r8-delivery-server-")
        self.root = Path(self.temporary.name)
        (self.root / "entry.js").write_text("export const ok = true;\n", encoding="utf-8")
        (self.root / "probe.0123456789abcdef.wasm").write_bytes(b"wasm-fixture")
        (self.root / "probe.0123456789abcdef.wasm.gz").write_bytes(
            gzip.compress(b"wasm-fixture", compresslevel=9, mtime=0)
        )
        self.server = create_server(
            self.root,
            "127.0.0.1",
            0,
            "artifact",
            "http://127.0.0.1:9000",
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temporary.cleanup()

    def open(self, path: str):
        return urllib.request.urlopen(self.origin + path, timeout=5)

    def test_cross_origin_static_headers_and_cache_policy(self) -> None:
        with self.open("/probe.0123456789abcdef.wasm") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Content-Type"], "application/wasm")
            self.assertEqual(response.headers["Cross-Origin-Resource-Policy"], "cross-origin")
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://127.0.0.1:9000")
            self.assertIn("immutable", response.headers["Cache-Control"])
        with self.open("/entry.js") as response:
            self.assertEqual(response.headers["Cache-Control"], "no-cache")

    def test_gzip_canary_is_deterministic(self) -> None:
        with self.open("/__r8__/canary?scenario=gzip") as response:
            payload = response.read()
            self.assertEqual(response.headers["Content-Encoding"], "gzip")
            self.assertEqual(gzip.decompress(payload), CANARY)

    def test_precompressed_static_negotiation_and_identity_override(self) -> None:
        request = urllib.request.Request(
            self.origin + "/probe.0123456789abcdef.wasm?representation=gzip",
            headers={"Accept-Encoding": "gzip"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = response.read()
            self.assertEqual(response.headers["Content-Encoding"], "gzip")
            self.assertEqual(int(response.headers["Content-Length"]), len(payload))
            self.assertEqual(gzip.decompress(payload), b"wasm-fixture")
        request = urllib.request.Request(
            self.origin + "/probe.0123456789abcdef.wasm?representation=identity",
            headers={"Accept-Encoding": "gzip"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertIsNone(response.headers["Content-Encoding"])
            self.assertEqual(response.read(), b"wasm-fixture")

    def test_cors_and_corp_can_be_removed_independently(self) -> None:
        with self.open("/__r8__/canary?scenario=no-cors") as response:
            self.assertIsNone(response.headers["Access-Control-Allow-Origin"])
            self.assertEqual(response.headers["Cross-Origin-Resource-Policy"], "cross-origin")
        with self.open("/__r8__/canary?scenario=no-corp") as response:
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://127.0.0.1:9000")
            self.assertIsNone(response.headers["Cross-Origin-Resource-Policy"])

    def test_http_500_and_truncated_scenarios_are_observable(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.open("/__r8__/canary?scenario=http-500")
        self.assertEqual(raised.exception.code, 500)
        raised.exception.close()
        with self.assertRaises(http.client.IncompleteRead) as truncated:
            with self.open("/__r8__/canary?scenario=truncated") as response:
                response.read()
        self.assertGreater(len(truncated.exception.partial), 0)
        self.assertLess(len(truncated.exception.partial), len(CANARY))

    def test_static_faults_preserve_status_and_change_only_requested_contract(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as missing:
            self.open("/entry.js?fault=http-404")
        self.assertEqual(missing.exception.code, 404)
        missing.exception.close()
        with self.open("/entry.js?fault=wrong-type&representation=identity") as response:
            self.assertTrue(response.headers["Content-Type"].startswith("text/plain"))
            self.assertEqual(response.read(), b"export const ok = true;\n")
        with self.open("/entry.js?fault=wrong-bytes&representation=identity") as response:
            self.assertNotEqual(response.read(), b"export const ok = true;\n")

    def test_request_journal_is_machine_readable(self) -> None:
        with self.open("/__r8__/canary?scenario=delay") as response:
            self.assertEqual(response.read(), CANARY)
        with self.open("/__r8__/requests") as response:
            journal = json.load(response)["requests"]
        self.assertTrue(any(
            item["path"] == "/__r8__/canary"
            and item["scenario"] == "delay"
            and item["durationMs"] >= 200
            for item in journal
        ))

    def test_manifest_mutation_and_redirect_faults_are_deterministic(self) -> None:
        release = self.root / "releases" / "writer-review-0123456789abcdef"
        release.mkdir(parents=True)
        manifest = {
            "schemaVersion": 1,
            "releaseId": "writer-review-0123456789abcdef",
            "artifacts": [{"role": "entry-html", "url": "entry.js"}],
        }
        (release / "release-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        with self.open(
            "/releases/writer-review-0123456789abcdef/release-manifest.json"
            "?fault=manifest-path-traversal&representation=identity"
        ) as response:
            mutated = json.load(response)
        self.assertEqual(mutated["artifacts"][0]["url"], "../escape.html")

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, file_pointer, code, message, headers, new_url):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        target = f"http://127.0.0.1:{self.server.server_address[1] + 1}"
        with self.assertRaises(urllib.error.HTTPError) as redirected:
            opener.open(
                self.origin + "/entry.js?fault=redirect-cross-origin&redirectTargetOrigin="
                + urllib.parse.quote(target, safe=""),
                timeout=5,
            )
        self.assertEqual(redirected.exception.code, 302)
        self.assertTrue(redirected.exception.headers["Location"].startswith(target))
        redirected.exception.close()


if __name__ == "__main__":
    unittest.main()
