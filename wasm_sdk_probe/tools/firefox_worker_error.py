"""One Firefox RDP operation: schedule a real uncaught document-worker error.

Instrument only. No product messages, fake ErrorEvents, thread attachment, or
generic browser adapter. The caller owns the disposable Firefox server and
supplies the exact served page/worker URLs. Scheduling is not recovery proof.
"""
from __future__ import annotations

import json
import socket
import time

EXPRESSION = "setTimeout(() => { throw new Error('induced worker failure'); }, 0); true"


def launch_options(port: int) -> tuple[list[str], dict]:
    """Only for a new, owned Firefox profile; default sessions never opt in."""
    if type(port) is not int or not 0 < port < 65536:
        raise ValueError("invalid owned DevTools port")
    return (["--start-debugger-server", str(port)], {
        "devtools.debugger.remote-enabled": True,
        "devtools.chrome.enabled": True,
        "devtools.debugger.prompt-connection": False,
        "devtools.debugger.force-local": True,
    })


class _Packets:
    """Length-prefixed JSON for the single sequential actor traversal below."""
    def __init__(self, sock, deadline, transcript):
        self.sock, self.deadline, self.transcript = sock, deadline, transcript
        self.buffer = bytearray()
        self.pending = []

    def _receive(self):
        while True:
            left = self.deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError("worker-error transport deadline")
            colon = self.buffer.find(b":")
            if colon >= 0:
                header = self.buffer[:colon]
                if not header or not header.isdigit() or len(header) > 9:
                    raise ValueError("invalid RDP packet length")
                length = int(header)
                if length > 1024 * 1024:
                    raise ValueError("oversized RDP instrument packet")
                if len(self.buffer) >= colon + 1 + length:
                    raw = self.buffer[colon + 1:colon + 1 + length]
                    del self.buffer[:colon + 1 + length]
                    packet = json.loads(raw)
                    if not isinstance(packet, dict):
                        raise ValueError("RDP packet is not an object")
                    self.transcript.append({"direction": "receive", "packet": packet})
                    return packet
            elif len(self.buffer) > 10:
                raise ValueError("unterminated RDP length")
            self.sock.settimeout(left)
            data = self.sock.recv(65536)
            if not data:
                raise EOFError("Firefox closed the worker-error transport")
            self.buffer.extend(data)

    def take(self, predicate):
        for i, packet in enumerate(self.pending):
            if predicate(packet):
                return self.pending.pop(i)
        while True:
            packet = self._receive()
            if predicate(packet):
                return packet
            self.pending.append(packet)

    def request(self, actor, operation, fields, result_key):
        packet = {"to": actor, "type": operation, **fields}
        raw = json.dumps(packet, separators=(",", ":")).encode()
        self.sock.sendall(str(len(raw)).encode() + b":" + raw)
        self.transcript.append({"direction": "send", "packet": packet})
        reply = self.take(lambda p: p.get("from") == actor and
                          ("error" in p or (result_key in p and
                           p.get("type") != "evaluationResult")))
        if "error" in reply:
            raise ValueError("RDP command refused: " + json.dumps(reply))
        return reply


def _unique(rows, url, description):
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("invalid " + description + " enumeration: " + json.dumps(rows))
    matches = [row for row in rows if row.get("url") == url]
    if len(matches) != 1 or not matches[0].get("actor"):
        raise ValueError("no unique " + description + ": " + json.dumps(rows))
    return matches[0]


def _inject(sock, deadline, page_url, worker_url, evidence):
    wire = _Packets(sock, deadline, evidence["packets"])
    greeting = wire.take(lambda p: p.get("from") == "root")
    if greeting.get("applicationType") != "browser":
        raise ValueError("not a Firefox browser RDP greeting")
    tabs = wire.request("root", "listTabs", {}, "tabs")["tabs"]
    tab = _unique(tabs, page_url, "owned product tab")
    target = wire.request(tab["actor"], "getTarget", {}, "frame")["frame"]
    if not isinstance(target, dict) or target.get("url") != page_url or not target.get("actor"):
        raise ValueError("tab target differs from the owned product page: " + json.dumps(target))
    workers = wire.request(target["actor"], "listWorkers", {}, "workers")["workers"]
    worker = _unique(workers, worker_url, "bound document worker")
    connected = wire.request(worker["actor"], "getTarget", {}, "type")
    console = connected.get("consoleActor")
    if connected.get("type") != "connected" or not isinstance(console, str) or not console:
        raise ValueError("worker supplied no console actor: " + json.dumps(connected))
    if connected.get("url", worker_url) != worker_url:
        raise ValueError("connected worker URL differs")
    evidence["target"] = {"tab": tab, "frame": target, "worker": worker,
                          "connected": connected}
    acknowledged = wire.request(console, "evaluateJSAsync", {"text": EXPRESSION}, "resultID")
    result_id = acknowledged["resultID"]
    if not isinstance(result_id, str) or not result_id:
        raise ValueError("evaluation acknowledgement has no resultID")
    result = wire.take(lambda p: p.get("from") == console and
                       p.get("type") == "evaluationResult" and p.get("resultID") == result_id)
    evidence["evaluation"] = result
    if result.get("error") or result.get("hasException") or result.get("exception") is not None or result.get("result") is not True:
        raise ValueError("worker did not confirm error scheduling: " + json.dumps(result))
    evidence["fired"] = True


def induce_worker_error(port, page_url, worker_url, settle=4.0, *, connector=socket.create_connection):
    """Use the existing inducer's transport budget; callers still judge B4."""
    evidence = {"name": "INDUCE_WORKER_FAILURE", "transport": "firefox-rdp",
                "fired": False, "pageUrl": page_url, "workerUrl": worker_url,
                "packets": []}
    sock = None
    try:
        launch_options(port)  # validate before contacting a socket
        if not page_url or not worker_url or settle <= 0:
            raise ValueError("missing owned page/worker or transport budget")
        deadline = time.monotonic() + settle
        sock = connector(("127.0.0.1", port), timeout=settle)
        _inject(sock, deadline, page_url, worker_url, evidence)
    except (OSError, ValueError, KeyError, TypeError, EOFError) as error:
        evidence["why"] = f"{type(error).__name__}: {error}"
    finally:
        if sock is not None:
            sock.close()
    return evidence
