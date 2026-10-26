"""Causal packet controls; these do not establish an actual Firefox crash."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import firefox_worker_error as worker

PAGE = "http://127.0.0.1:8765/e2-editor.html"
WORKER = "http://127.0.0.1:8765/profiles/e2-editor-v23/sdk-worker.js"


def packets():
    return [
        {"from": "root", "applicationType": "browser"},
        {"from": "root", "tabs": [{"actor": "tab", "url": PAGE}]},
        {"from": "tab", "frame": {"actor": "frame", "url": PAGE}},
        {"from": "frame", "workers": [{"actor": "worker", "url": WORKER},
                                        {"actor": "pthread", "url": WORKER + ".pthread"}]},
        {"from": "worker", "type": "connected", "consoleActor": "console", "url": WORKER},
        # Real protocols may deliver the event before the acknowledgement.
        {"from": "console", "type": "evaluationResult", "resultID": "result-1", "result": True},
        {"from": "console", "resultID": "result-1"},
    ]


class Socket:
    def __init__(self, rows):
        self.remaining = bytearray()
        for row in rows:
            raw = json.dumps(row).encode()
            self.remaining.extend(str(len(raw)).encode() + b":" + raw)
        self.sent, self.closed = [], False

    def settimeout(self, timeout):
        assert timeout > 0

    def recv(self, size):
        if not self.remaining:
            raise TimeoutError("fake transport exhausted")
        # Fragment both header and payload, and retain adjacent packet bytes.
        data = bytes(self.remaining[:17])
        del self.remaining[:17]
        return data

    def sendall(self, raw):
        length, data = raw.split(b":", 1)
        assert int(length) == len(data)
        self.sent.append(json.loads(data))

    def close(self):
        self.closed = True


class WorkerErrorTests(unittest.TestCase):
    def run_rows(self, rows):
        sock = Socket(rows)
        def connect(address, timeout):
            self.assertEqual(address, ("127.0.0.1", 8766))
            self.assertEqual(timeout, 4.0)
            return sock
        result = worker.induce_worker_error(8766, PAGE, WORKER, connector=connect)
        self.assertTrue(sock.closed)
        return result, sock

    def test_actual_actor_chain_and_event_before_ack(self):
        result, sock = self.run_rows(packets())
        self.assertTrue(result["fired"], result)
        self.assertEqual([(p["to"], p["type"]) for p in sock.sent], [
            ("root", "listTabs"), ("tab", "getTarget"), ("frame", "listWorkers"),
            ("worker", "getTarget"), ("console", "evaluateJSAsync")])
        self.assertEqual(sock.sent[-1]["text"], worker.EXPRESSION)
        self.assertEqual(len(result["packets"]), 12)

    def test_ack_before_event(self):
        rows = packets()
        rows[-2:] = reversed(rows[-2:])
        self.assertTrue(self.run_rows(rows)[0]["fired"])

    def test_causal_rejections(self):
        mutations = {
            "wrong-tab": lambda r: r[1]["tabs"][0].update(url=PAGE + "wrong"),
            "duplicate-tab": lambda r: r[1]["tabs"].append(copy.deepcopy(r[1]["tabs"][0])),
            "wrong-tab-target": lambda r: r[2]["frame"].update(url=PAGE + "wrong"),
            "wrong-worker": lambda r: r[3]["workers"][0].update(url=WORKER + "wrong"),
            "duplicate-worker": lambda r: r[3]["workers"].append(copy.deepcopy(r[3]["workers"][0])),
            "missing-console": lambda r: r[4].pop("consoleActor"),
            "wrong-connected-url": lambda r: r[4].update(url=WORKER + "wrong"),
            "evaluation-error": lambda r: r[5].update(hasException=True),
            "evaluation-false": lambda r: r[5].update(result=False),
            "wrong-result-id": lambda r: r[5].update(resultID="other"),
            "wrong-result-actor": lambda r: r[5].update(**{"from": "pthread-console"}),
            "missing-result": lambda r: r.pop(5),
            "missing-ack": lambda r: r.pop(6),
            "missing-result-id": lambda r: r[6].update(resultID=""),
            "command-error": lambda r: r[4].update(error="noSuchActor"),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                rows = packets()
                mutation(rows)
                result, _ = self.run_rows(rows)
                self.assertFalse(result["fired"], result)
                self.assertTrue(result["why"])
                self.assertTrue(result["packets"])

    def test_only_owned_loopback_server_options(self):
        args, prefs = worker.launch_options(8766)
        self.assertEqual(args, ["--start-debugger-server", "8766"])
        self.assertTrue(prefs["devtools.debugger.force-local"])
        for bad in (True, 0, 65536, "8766"):
            with self.assertRaises(ValueError):
                worker.launch_options(bad)


class IntegrationSeams(unittest.TestCase):
    """integration-pending.patch: opt-in launch only; Firefox 096 reaches the RDP helper."""
    def launch(self, **kwargs):
        from unittest.mock import patch
        import run_browser_probe as probe
        sent = {}
        def request(self_, method, path, payload=None, timeout=180):
            sent["payload"] = payload
            return {"value": {"sessionId": "s", "capabilities": {"browserVersion": "150.0"}}}
        with patch.object(probe.shutil, "which", return_value="/bin/true"), \
                patch.object(probe.subprocess, "Popen"), patch.object(probe, "wait_http"), \
                patch.object(probe.FirefoxSession, "request", request):
            session = probe.FirefoxSession("cold", **kwargs)
        return session, sent["payload"]["capabilities"]["alwaysMatch"]["moz:firefoxOptions"]

    def test_default_session_is_unchanged_and_opt_in_is_owned_loopback(self):
        session, options = self.launch()
        self.assertEqual(options["args"], ["-headless"])
        self.assertFalse(any(name.startswith("devtools.") for name in options["prefs"]))
        self.assertIsNone(session.worker_error_port)
        session, options = self.launch(worker_error_server=True)
        port = session.worker_error_port
        self.assertEqual(options["args"], ["-headless", "--start-debugger-server", str(port)])
        self.assertIs(options["prefs"]["devtools.debugger.force-local"], True)
        self.assertEqual(session.worker_error_configuration["args"], options["args"][1:])

    def test_firefox_inducer_uses_the_owned_target_and_keeps_its_result(self):
        from unittest.mock import patch
        import run_e2_c_product_path as runner

        class Session:
            worker_error_port = 7
            worker_error_target = {"pageUrl": "http://127.0.0.1:1/e2-editor.html",
                                   "workerUrl": "http://127.0.0.1:1/profiles/p/sdk-worker.js"}
            version = "150.0"
            worker_error_configuration = {"args": ["--start-debugger-server", "7"]}

        refused = {"name": "INDUCE_WORKER_FAILURE", "fired": False, "why": "no unique worker"}
        with patch.object(worker, "induce_worker_error", return_value=dict(refused)) as induce:
            result = runner.induce_worker_failure(Session(), settle=2.5)
        induce.assert_called_once_with(7, Session.worker_error_target["pageUrl"],
                                       Session.worker_error_target["workerUrl"], 2.5)
        self.assertIs(result["fired"], False)
        self.assertEqual(result["why"], "no unique worker")
        self.assertEqual(result["browserVersion"], "150.0")
        self.assertEqual(result["launchConfiguration"], Session.worker_error_configuration)


if __name__ == "__main__":
    unittest.main()
