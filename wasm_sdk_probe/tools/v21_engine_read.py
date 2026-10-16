#!/usr/bin/env python3
"""S-8: the engine read (`editorGetStateV2` through the observer's ask channel) and save capture.

Arms: ARMS.md S-8; ARMS-item1.md §2.8; ARMS-item2.md I-5, I-6.  Works on a page served with v20's
OBSERVER (`run_v20_shakedown.OBSERVER`, injected by S-1) and after `run_e2_c_product_path.INSTALL`.

  Trace(session)              accumulates v20's trace node (`#v20-trace`) across drains, so nothing a
                              helper drains is lost to the runner: `.drain()` -> new entries, `.all`
  ask_state(trace, handle)    one editorGetStateV2 ask; {answered, ok, result{sel, selectionType,
                              selectionText, caret, rev}, askedAt, answeredAt}
  current_worker(session)     the observer's worker count (one per opened document)
  document_handle(session)    the current document handle the observer saw
  save(session)               the product's save (toolbar action), bytes from the INSTALL shim
  install(session)            the INSTALL shim (saves and toasts); call after every navigation
"""
from __future__ import annotations

import base64
import json
import time

import r7_support
import run_e2_c_product_path as pp
import run_merge_wasm_shakedown as mws
import run_v20_shakedown as v20

ASK_BASE = v20.ASK_BASE


class Trace:
    """v20's drained log, kept whole for the run."""

    def __init__(self, session):
        self.session = session
        self.all: list[dict] = []

    def reset(self) -> None:
        """After a navigation: the page's sequence restarts."""
        v20.TRACE["last"] = -1

    def drain(self) -> list[dict]:
        entries = v20.drain(self.session)
        self.all += entries
        return entries

    def wait(self, predicate, limit: float = 20.0, poll: float = 0.1) -> dict | None:
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            for entry in self.drain():
                if predicate(entry):
                    return entry
            time.sleep(poll)
        return None


_ASKS = {"n": 0}


def ask_state(trace: Trace, handle, timeout: float = 8.0, selection_text_cap: int = 400) -> dict:
    """One `editorGetStateV2` ask on the product's own worker (v20's ask channel).  The worker answers
    with `selectionType` and `selectionText` read fresh by the engine and the editor-state cache."""
    _ASKS["n"] += 1
    rq = ASK_BASE + (int(time.time() * 10) % 0x00FFFFF0) + _ASKS["n"] % 16
    r7_support.run_in_page(trace.session, v20.ASK.replace("ARG_JSON", json.dumps(json.dumps(
        {"requestId": rq, "operation": "editorGetStateV2", "payload": {"documentHandle": handle}}))))
    asked = time.monotonic()
    entry = trace.wait(lambda e: e.get("k") == "rs" and e.get("rq") == rq, timeout)
    if entry is None:
        return {"asked": rq, "answered": False}
    return {"asked": rq, "answered": True, "ok": entry.get("ok"), "result": entry.get("result"),
            "askT": None, "answerT": entry.get("t"), "roundTripMs": round((time.monotonic() - asked) * 1000)}


def current_worker(session) -> int | None:
    return (mws.obs(session) or {}).get("workers")


def document_handle(session):
    return (mws.obs(session) or {}).get("documentHandle")


def install(session) -> str:
    return pp.evaluate(session, pp.INSTALL)


def save(session, timeout: float = 60) -> bytes | None:
    """The product's own save (toolbar `save`), bytes caught by INSTALL's createObjectURL hook."""
    index = pp.evaluate(session, pp.SAVE_COUNT) or 0
    if index < 0:
        raise RuntimeError("INSTALL shim missing: call install() after the navigation")
    pp.evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
    if not pp.wait_saves(session, index + 1, timeout):
        return None
    saved = pp.evaluate(session, pp.READ_SAVE.replace("ARG_INDEX", str(index)))
    return base64.b64decode(saved["b64"]) if saved else None
