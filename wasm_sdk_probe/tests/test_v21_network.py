"""tools/v21_network.py (S-11) without a browser: the proxy forwards byte-for-byte and logs every attempt,
the target listeners log, and the two readers M5's judge uses say what they should.

Red cases: a log without the probe.wasm GET -> positive_control is None; a request to a target inside a
window -> outside_mirror reports it; a refused upstream (port 9) is still logged, with its error.
"""
import hashlib
import socket
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v21_network as net  # noqa: E402

BODY = bytes(range(256)) * 4096  # 1 MiB


class Upstream(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        self.wfile.write(BODY)


class Network(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        threading.Thread(target=cls.upstream.serve_forever, daemon=True).start()
        cls.mirror_port = cls.upstream.server_address[1]
        cls.proxy = net.LoggingProxy()
        cls.targets = net.TargetListeners()
        cls.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": f"http://127.0.0.1:{cls.proxy.port}"}))

    @classmethod
    def tearDownClass(cls):
        cls.proxy.close()
        cls.targets.close()
        cls.upstream.shutdown()

    def test_forward_is_byte_exact_and_logged(self):
        url = f"http://127.0.0.1:{self.mirror_port}/profiles/e2-editor-v21/probe.wasm"
        with self.opener.open(url, timeout=10) as response:
            body = response.read()
            coep = response.headers.get("Cross-Origin-Embedder-Policy")
        self.assertEqual(hashlib.sha256(body).hexdigest(), hashlib.sha256(BODY).hexdigest())
        self.assertEqual(coep, "require-corp")
        hit = net.positive_control(self.proxy.entries(), self.mirror_port)
        self.assertIsNotNone(hit)
        self.assertEqual((hit["status"], hit["bytes"]), (200, len(BODY)))

    def test_refused_upstream_is_still_logged(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.opener.open("http://127.0.0.1:9/x.png", timeout=10)
        self.assertEqual(caught.exception.code, 502)
        hits = [e for e in self.proxy.entries() if e.get("port") == 9]
        self.assertEqual(len(hits), 1)
        self.assertIn("error", hits[0])

    def test_connect_tunnel_reaches_the_closer_and_is_logged(self):
        sock = socket.create_connection(("127.0.0.1", self.proxy.port), timeout=5)
        sock.sendall(b"CONNECT 127.0.0.1:18768 HTTP/1.1\r\nHost: 127.0.0.1:18768\r\n\r\n")
        head = sock.recv(1024)
        self.assertTrue(head.startswith(b"HTTP/1.1 200"), head)
        sock.sendall(b"\x16\x03\x01hello")
        time.sleep(0.5)
        sock.close()
        self.assertTrue(any(e["method"] == "CONNECT" and e["port"] == 18768 for e in self.proxy.entries()))
        closer = [e for e in self.targets.entries() if e["target"] == "closer"]
        self.assertTrue(closer and closer[-1]["firstBytesHex"].startswith("160301"))

    def test_listener_logs_and_answers_404(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.opener.open("http://127.0.0.1:18765/h2.png", timeout=10)
        self.assertEqual(caught.exception.code, 404)
        self.assertTrue(any(e["target"] == "listener" and e["path"] == "/h2.png" for e in self.targets.entries()))

    def test_tarpit_accepts_and_is_logged(self):
        sock = socket.create_connection(("127.0.0.1", 18766), timeout=5)
        time.sleep(0.3)
        sock.close()
        self.assertTrue(any(e["target"] == "tarpit" for e in self.targets.entries()))

    def test_firefox_prefs_force_loopback(self):
        prefs = net.firefox_prefs(4321)
        self.assertIs(prefs["network.proxy.allow_hijacking_localhost"], True)
        self.assertEqual((prefs["network.proxy.type"], prefs["network.proxy.http_port"]), (1, 4321))
        self.assertEqual(prefs["network.proxy.no_proxies_on"], "")

    # ---- red cases ----
    def test_red_no_probe_wasm_means_no_positive_control(self):
        entries = [{"method": "GET", "host": "127.0.0.1", "port": 5555, "path": "/e2-editor.html", "t": 1.0}]
        self.assertIsNone(net.positive_control(entries, 5555))
        entries.append({"method": "GET", "host": "127.0.0.1", "port": 6666,
                        "path": "/profiles/e2-editor-v21/probe.wasm", "t": 2.0})
        self.assertIsNone(net.positive_control(entries, 5555), "probe.wasm from another origin is not the control")

    def test_red_target_request_inside_a_window_is_reported(self):
        entries = [{"method": "GET", "host": "127.0.0.1", "port": 5555, "path": "/x", "t": 10.0},
                   {"method": "CONNECT", "host": "127.0.0.1", "port": 9, "path": None, "t": 10.5},
                   {"target": "listener", "port": 18765, "method": "GET", "path": "/s01.png", "t": 11.0},
                   {"method": "GET", "host": "127.0.0.1", "port": 18765, "path": "/late.png", "t": 30.0}]
        flagged = net.outside_mirror(entries, 5555, 10.0, 12.0)
        self.assertEqual([e.get("port") for e in flagged], [9, 18765])


if __name__ == "__main__":
    unittest.main()
