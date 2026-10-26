"""The four ABI6 product arms' reader, table, mirror, driver and integration patch -- no browser.

A synthetic page builder reproduces the observer's record semantics (one shared sequence, sync
half-open instrument windows, admissions recorded during a trusted input's dispatch, release-set
snapshots taken at capture and after dispatch) for a clean run in both browser families.  The
positive baseline must read PASS for all 24 rows; every causal control of the work order's
"Finite source checks before execution" must be rejected with its own reason.

Controls that stand for PRODUCT behaviour are built self-consistent (the snapshots are recomputed,
as the observer would have recorded them), so the reader reaches its decision phase; controls
that stand for EVIDENCE tampering change the raw records the reader reconstructs from.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(ROOT / "tools"))

import judge_v23_product_four_arms as judge  # noqa: E402
import v23_product_four_arms as arms  # noqa: E402

PATCH = (WORKSPACE / "findings" / "evidence" / "link-batch-v23" / "feature-protocol"
         / "product-four-arms-source" / "integration-pending.patch")
UA = {"chrome": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "HeadlessChrome/139.0.0.0 Safari/537.36",
      "firefox": "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0"}
PROFILE = "e2-editor-v23"
SERVICE_MS = 45.0
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
# The runner's check population at HEAD 9309cdbc, in source order (`declared_check_ids`).
ORIGINAL_CHECKS = [
    "product-save-button-writes-a-real-odt", "every-ime-commit-reaches-the-document", "ctrl-c-asks-the-engine",
    "product-insert-button-inserts-what-the-field-holds", "product-undo-button-reverses-the-last-edit",
    "product-redo-button-restores-what-undo-removed", "bulleting-a-blank-line-does-not-demand-a-rollback",
    "notice-action-recovers-the-session", "backspace-and-arrows-reach-the-document",
    "the-keyboard-reaches-the-document", "ctrl-v-reaches-the-document", "the-caret-is-drawn-where-it-was-placed",
    "the-caret-lands-where-the-click-was", "bold-can-be-turned-off-again",
    "a-format-that-worked-is-not-reported-as-failed", "a-failed-format-does-not-block-the-session",
    "format-a-paragraph-changes-that-paragraph", "cut-removes-the-selected-text",
    "a-refused-action-is-reported-and-changes-nothing", "every-inline-format-reaches-the-document",
    "clear-format-removes-every-inline-format", "formatting-survives-the-next-paragraph-break",
    "the-toolbar-gives-the-keyboard-back", "the-edit-buttons-do-what-they-say",
    "the-open-button-opens-the-file-chooser", "an-aborted-gesture-stops-selecting",
    "caret-follows-the-text-you-type", "the-vertical-arrows-move-the-caret",
    "the-composition-you-are-typing-is-visible", "the-document-region-says-why-it-is-empty",
    "the-projection-is-placed-where-the-document-is", "an-inline-format-reaches-a-selection",
    "the-page-agrees-with-the-engine-about-the-selection", "the-canvas-follows-a-window-that-changed-size",
    "the-sample-picker-opens-a-second-document", "product-opens-a-document-the-user-chose",
    "the-enter-key-reaches-the-document", "a-long-document-is-drawn-or-the-product-says-it-is-not",
    "the-canvas-follows-a-document-that-grew", "editing-a-long-document-stays-responsive",
    "recovery-returns-what-the-product-promised", "a-boundary-arrow-press-does-not-cost-the-work"]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def b64(raw: bytes) -> dict:
    return {"encoding": "base64", "bytes": len(raw), "data": base64.b64encode(raw).decode("ascii")}


def odt(paragraphs: list[str], *, broken: bool = False) -> bytes:
    from xml.sax.saxutils import escape
    body = "".join(f"<text:p>{escape(p)}</text:p>" for p in paragraphs)
    content = (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content xmlns:office="{OFFICE_NS}" '
               f'xmlns:text="{TEXT_NS}"><office:body><office:text>{body}</office:text></office:body>'
               + ("" if broken else "</office:document-content>"))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        archive.writestr("content.xml", content)
    return out.getvalue()


def bundle() -> tuple[dict, dict]:
    import build_e2_c_shell_bundle as shell
    raw = (ROOT / shell.MANIFEST).read_bytes()
    manifest = json.loads(raw)
    declared = {row["path"]: row["sha256"] for row in manifest["included"]}
    return {"bundle": Path(shell.MANIFEST).as_posix(), "bundleFileSha256": sha(raw),
            "bundleSha256": manifest["bundleSha256"], "entrypoint": manifest["entrypoint"],
            "declared": declared, "served": {arms.served_module(p): h for p, h in declared.items()}}, manifest


def identity() -> dict:
    original = (ROOT / "web" / arms.HTML).read_bytes()
    shell, manifest = bundle()
    return {"installed": True, "mirror": "v23-product-four-arms-observer", "evidenceClass": "instrument-observation",
            "transformation": "test", "originalHtmlSha256": sha(original),
            "servedHtmlSha256": sha(arms.transform_html(original)),
            "observerEntrySha256": sha((ROOT / "web" / arms.OBSERVER_ENTRY).read_bytes()),
            "observerCoreSha256": sha((ROOT / "web" / arms.OBSERVER_CORE).read_bytes()),
            "productModuleSha256": shell["declared"][manifest["entrypoint"]], "candidatePageSha256": None,
            "shell": shell, "profile": PROFILE, "abiVersion": 6,
            "profileArtifacts": {n: sha(n.encode()) for n in arms.PROFILE_ARTIFACTS},
            "diagnosticOverrides": []}


def served(i: dict) -> dict:
    return {arms.HTML: i["servedHtmlSha256"], arms.OBSERVER_ENTRY: i["observerEntrySha256"],
            arms.OBSERVER_CORE: i["observerCoreSha256"], **i["shell"]["served"],
            **{f"profiles/{PROFILE}/{n}": h for n, h in i["profileArtifacts"].items()}}


def caret(paragraph: int, offset: int, shift: int = 0) -> dict:
    return {"x": 1000 + 100 * offset + shift, "y": 500 + 300 * paragraph, "height": 240}


def state(handle, revision, moving: dict, anchor: dict | None = None) -> dict:
    point = {"x": moving["x"], "y": moving["y"]}
    if anchor is None or (anchor["x"], anchor["y"]) == (moving["x"], moving["y"]):
        selection = {"observed": True, "collapsed": True, "start": point, "end": point, "rectangles": []}
    else:
        a = {"x": anchor["x"], "y": anchor["y"]}
        start, end = sorted([a, point], key=lambda p: (p["y"], p["x"]))
        selection = {"observed": True, "collapsed": False, "start": start, "end": end, "rectangles": []}
    return {"documentHandle": handle, "revision": revision, "sourceSequence": 1, "visible": True,
            "caret": dict(moving), "selection": selection}


class Builder:
    """One browser's raw artifacts, written as run_block would."""

    def __init__(self, browser: str, *, same_clock: bool = False):
        self.browser, self.same_clock = browser, same_clock
        self.seq, self.t, self.gen, self.handle = 0, 100.0, 0, 1
        self.ids: dict = {}
        self.cell = None
        self.saves: dict = {}
        self.identity = identity()
        self.p = {"schema": 1, "instrument": "v23-product-four-arms", "userAgent": UA[browser],
                  "recording": False, "seq": 0, "workers": [], "requests": [], "responses": [], "events": [],
                  "cancels": [], "workerErrors": [], "inputs": [], "admissions": [], "calls": [], "opens": [],
                  "cells": [], "snapshots": [], "failures": [], "orphanResponses": 0, "orphanCancels": 0}
        self.p["identity"] = {"profile": PROFILE, "served": served(self.identity),
                              "configured": {"profile": PROFILE}, "seq": self.next()}
        self.rows = {"schema": 1, "browser": browser, "rows": [], "readiness": None, "reference": None,
                     "failures": []}

    # ------------------------------------------------------------ primitives
    def next(self, dt: float = 0.5) -> int:
        self.seq += 1
        if not self.same_clock:
            self.t += dt
        return self.seq

    def post(self, op, payload, issuer="product", call=None, dt=0.5):
        rid = self.ids[self.gen] = self.ids.get(self.gen, 0) + 1
        item = {"seq": self.next(dt), "generation": self.gen, "at": self.t, "issuer": issuer,
                "callId": call["id"] if call else None,
                "message": {"protocolVersion": 1, "kind": "request", "requestId": rid, "operation": op,
                            "payload": payload}}
        self.p["requests"].append(item)
        return item

    def answer(self, request, result, ok=True, dt=0.5):
        item = {"seq": self.next(dt), "generation": request["generation"], "at": self.t,
                "message": {"protocolVersion": 1, "kind": "response", "requestId": request["message"]["requestId"],
                            "ok": ok, "result" if ok else "error": result}}
        self.p["responses"].append(item)
        return item

    def call(self, name, op, payload, result):
        entry = {"id": len(self.p["calls"]) + 1, "name": name, "seq": self.next(),
                 "cellId": self.cell["cellId"] if self.cell else None, "generation": self.gen,
                 "documentHandle": self.handle, "startedAt": self.t, "requestStart": len(self.p["requests"])}
        self.p["calls"].append(entry)
        request = self.post(op, {"documentHandle": self.handle, **payload}, "instrument", entry)
        entry["requestEnd"] = len(self.p["requests"])
        self.answer(request, result)
        entry.update(ok=True, result=copy.deepcopy(result), finishedAt=self.t, finishSeq=self.next())
        return result

    def input(self, type_, key, *, shift=False, repeat=False, prevented=False, input_type=None, data=None,
              during=None, trusted=True, dt=0.5):
        record = {"seq": self.next(dt), "type": type_, "at": self.t, "timeStamp": self.t, "isTrusted": trusted,
                  "key": key, "code": key, "repeat": repeat, "shiftKey": shift, "ctrlKey": False, "altKey": False,
                  "metaKey": False, "inputType": input_type, "data": data, "targetId": "sink",
                  "cellId": self.cell["cellId"] if self.cell else None, "sink": self.sink(), "admissions": []}
        self.p["inputs"].append(record)
        measuring = bool(self.cell and self.cell.get("measuring"))
        if measuring and trusted and type_ != "input":
            self.shot("capture", record)
        if during:
            during(record)
        record["afterSeq"] = self.next(0.1)
        record["defaultPrevented"] = prevented
        if measuring and trusted and type_ != "input":
            self.shot("after", record)
        return record

    def shot(self, phase, record):
        self.p["snapshots"].append({"seq": self.next(0.0), "phase": phase, "inputSeq": record["seq"],
                                    "cellId": self.cell["cellId"], "type": record["type"], "key": record["key"]})

    def admit(self, method, *, action=None, extend=False, text=None, input=None):
        record = {"id": len(self.p["admissions"]) + 1, "seq": self.next(0.1), "at": self.t, "method": method,
                  "issuer": "product", "inputSeq": input["seq"] if input else None, "generation": self.gen,
                  "documentHandle": self.handle, "cellId": self.cell["cellId"] if self.cell else None,
                  "requestIndex": len(self.p["requests"])}
        if method in ("action", "deleteKey"):
            record.update(action=action, extendSelection=extend)
        if method == "commitText":
            record["text"] = text
        self.p["admissions"].append(record)
        if input:
            input["admissions"].append(record["id"])
        return record

    def settle(self, record, ok=True):
        record.update(settledSeq=self.next(0.1), settledAt=self.t, ok=ok, result={"ok": ok})

    def sink(self):
        return {"id": "sink", "active": True, "disabled": False, "readOnly": False, "connected": True,
                "documentHandle": self.handle, "generation": self.gen}

    def close(self, cell):
        cell.update(generationAtClose=self.gen, pageStateAtClose="ready", endSeq=self.next())
        self.cell = None

    # ----------------------------------------------------------------- cells
    def open(self, name, fixture):
        raw = arms.fixture_bytes(fixture)
        record = {"serial": len(self.p["opens"]) + 1, "name": name, "seq": self.next(), "startedAt": self.t,
                  "fixtureSha256": sha(raw)}
        self.p["opens"].append(record)
        self.gen += 1
        self.p["workers"].append({"generation": self.gen, "url": f"./profiles/{PROFILE}/sdk-worker.js",
                                  "createdAt": self.t, "seq": self.next()})
        self.answer(self.post("init", {"requestedAbiVersion": 6, "debug": False}), {"abiVersion": 6})
        self.answer(self.post("open", {"buffer": b64(raw), "name": name}),
                    {"documentHandle": self.handle, "revision": 0, "widthTwips": 12240, "heightTwips": 15840})
        self.answer(self.post("editorGetStateV2", {"documentHandle": self.handle}),
                    state(self.handle, 0, caret(0, 0)))
        record.update(ok=True, finishedAt=self.t, finishSeq=self.next(), generation=self.gen,
                      documentHandle=self.handle)
        return record

    def prepare(self, cell_id, kind, arm, rnd, name, setup, paragraph):
        cell = {"cellId": cell_id, "kind": kind, "arm": arm, "round": rnd, "openName": name, "seq": self.next(),
                "openSerial": len(self.p["opens"]), "generation": self.gen, "documentHandle": self.handle,
                "setup": {}, "measuring": False}
        self.p["cells"].append(cell)
        self.cell = cell
        query = setup["query"]
        rect = [1000, 500 + 300 * paragraph, 100 * len(query), 240]
        self.call(f"{cell_id}-search", "search", {"query": query, "backward": False},
                  {"selections": [{"part": 0, "rectangles": ", ".join(map(str, rect))}], "revision": 0})
        self.call(f"{cell_id}-place", "editorPlaceCaretV2", {"xTwips": rect[0], "yTwips": rect[1] + rect[3] // 2},
                  {"revision": 0, "completion": "cursor-callback", "state": state(self.handle, 0, caret(paragraph, 0))})
        start = self.call(f"{cell_id}-start-state", "editorGetStateV2", {}, state(self.handle, 0, caret(paragraph, 0)))
        cell["setup"].update(rectangle=rect, start=start)
        if setup["kind"] == "select":
            states = [start]
            for i in range(setup["end"]):
                self.call(f"{cell_id}-right-{i}", "editorActionV2",
                          {"expectedRevision": 0, "action": "move-character-right", "extendSelection": False,
                           "enabled": False},
                          {"action": "move-character-right", "revision": 0, "changed": False,
                           "completion": "cursor-callback", "state": state(self.handle, 0, caret(paragraph, i + 1))})
                states.append(self.call(f"{cell_id}-right-{i}-state", "editorGetStateV2", {},
                                        state(self.handle, 0, caret(paragraph, i + 1))))
            a, b = states[setup["start"]]["caret"], states[setup["end"]]["caret"]
            self.call(f"{cell_id}-select", "editorSelectRangeV2",
                      {"startXTwips": a["x"], "startYTwips": a["y"] + 120, "endXTwips": b["x"], "endYTwips": b["y"] + 120},
                      {"revision": 0, "completion": "selection-callback", "state": state(self.handle, 0, b, a)})
            self.call(f"{cell_id}-selected-text", "getSelection", {},
                      {"text": setup["selectedText"], "revision": 0})
            cell["setup"].update(selectedText=setup["selectedText"], states=states)
            before = state(self.handle, 0, b, a)
        else:
            before = state(self.handle, 0, caret(paragraph, 0))
        cell["setup"]["before"] = self.call(f"{cell_id}-before-state", "editorGetStateV2", {}, before)
        return cell

    def arm(self, cell):
        cell.update(armSeq=self.next(), armedAt=self.t, inputStart=len(self.p["inputs"]),
                    requestStart=len(self.p["requests"]), sinkAtArm=self.sink(), dirtyAtArm=False,
                    pageStateAtArm="ready", generationAtArm=self.gen, measuring=True)

    def finish(self, cell, final_state, final_text):
        cell["measuring"] = False
        cell["measureEndSeq"] = self.next()
        cell["quietAtFinish"] = {"quiet": True, "reasons": []}
        cell["final"] = {"state": self.call(f"{cell['cellId']}-final-state", "editorGetStateV2", {}, final_state),
                         "selection": self.call(f"{cell['cellId']}-final-text", "getSelection", {},
                                                {"text": final_text, "revision": final_state["revision"]})}
        cell.update(pageStateAtFinish="ready", generationAtFinish=self.gen)

    def save(self, cell, paragraphs, revision, *, broken=False):
        raw = odt(paragraphs, broken=broken)
        admission = self.admit("save")
        request = self.post("save", {"documentHandle": self.handle, "format": "odt"})
        self.answer(request, {"buffer": b64(raw), "revision": revision})
        self.settle(admission)
        name = f"saves/{cell['cellId']}.odt"
        self.saves[name] = raw
        meta = {"index": len(self.saves) - 1, "captured": True, "file": name, "sha256": sha(raw), "bytes": len(raw)}
        cell["save"] = meta
        self.close(cell)
        return meta

    def row(self, cell, fixture, save=None):
        return {"cellId": cell["cellId"], "kind": cell["kind"], "arm": cell["arm"], "round": cell["round"],
                "browser": self.browser, "fixture": fixture, "fixtureSha256": arms.FIXTURE_PINS[fixture],
                "openName": cell["openName"], "failures": [], "save": save}

    # ------------------------------------------------------------- the arms
    def readiness(self, no_mutation=False, unsaved_mutation=False):
        name = arms.open_name(self.browser, "readiness", None)
        self.open(name, "abcd.fodt")
        cell = self.prepare(f"{self.browser}-readiness", "readiness", "readiness", None, name,
                            arms.READINESS["setup"], 0)
        self.arm(cell)
        self.input("keydown", "Z")

        def typed(record):
            if no_mutation:
                return
            admission = self.admit("commitText", text="Z", input=record)
            request = self.post("insertText", {"documentHandle": self.handle, "text": "Z"})
            self.answer(request, {"revision": 1, "changed": True})
            self.settle(admission)
        self.input("beforeinput", None, input_type="insertText", data="Z", during=typed)
        self.input("input", None, input_type="insertText", data="Z")
        self.input("keyup", "Z")
        revision = 0 if no_mutation else 1
        self.finish(cell, state(self.handle, revision, caret(0, revision)), "")
        meta = self.save(cell, ["abcd"] if (no_mutation or unsaved_mutation) else ["Zabcd"], revision)
        self.rows["readiness"] = self.row(cell, "abcd.fodt", meta)

    def reference(self, steps):
        name = arms.open_name(self.browser, "reference", None)
        self.open(name, arms.REFERENCE_FIXTURE)
        cell = self.prepare(f"{self.browser}-reference", "reference", "reference", None, name,
                            arms.REFERENCE_SETUP, 0)
        text = arms.fixture_paragraphs(arms.REFERENCE_FIXTURE)[0]
        start = caret(0, 0)
        cell["reference"] = []
        for i in range(1, steps + 1):
            self.call(f"{cell['cellId']}-step-{i}", "editorActionV2",
                      {"expectedRevision": 0, "action": "move-character-right", "extendSelection": True,
                       "enabled": False},
                      {"action": "move-character-right", "revision": 0, "changed": False,
                       "completion": "selection-callback", "state": state(self.handle, 0, caret(0, i), start)})
            self.call(f"{cell['cellId']}-text-{i}", "getSelection", {}, {"text": text[:i], "revision": 0})
            cell["reference"].append({"step": i, "revision": 0, "text": text[:i]})
        cell["save"] = None
        self.close(cell)
        self.rows["reference"] = self.row(cell, arms.REFERENCE_FIXTURE)

    def sequence(self, arm, rnd, *, swap=False, plain_move=False, wrong_content=False, no_shift=False,
                 untrusted=False, broken_save=False):
        name = arms.open_name(self.browser, arm["id"], rnd)
        self.open(name, arm["fixture"])
        cid = arms.cell_id(self.browser, arm["id"], rnd)
        merge = arm["id"] == "merge-then-shift"
        cell = self.prepare(cid, "measured", arm["id"], rnd, name, arm["setup"], 1 if merge else 0)
        self.arm(cell)
        first_key = arm["input"]["presses"][0][0]
        held: dict = {}
        self.input("keydown", first_key)

        def first(record):
            if merge:
                held["a1"] = self.admit("deleteKey", action="delete-backward", input=record)
            else:
                held["a1"] = self.admit("commitText", text="x", input=record)
        input_type = "deleteContentBackward" if merge else "insertText"
        self.input("beforeinput", None, input_type=input_type, data=None if merge else "x", during=first,
                   prevented=merge)
        if not merge:
            self.input("input", None, input_type="insertText", data="x")
        self.input("keyup", first_key)

        def extend(record):
            held["a2"] = self.admit("action", action="move-character-right", extend=True, input=record)
        self.input("keydown", "ArrowRight", shift=not no_shift, prevented=True, during=extend, trusted=not untrusted)
        if merge:
            self.answer(self.post("editorGetStateV2", {"documentHandle": self.handle}),
                        state(self.handle, 0, caret(1, 0)))
            edit = self.post("editorActionV2", {"documentHandle": self.handle, "expectedRevision": 0,
                                                "action": "delete-backward", "extendSelection": False,
                                                "enabled": False})
            edit_result = {"action": "delete-backward", "revision": 1, "changed": True,
                           "completion": "verified-delete", "state": state(self.handle, 1, caret(0, 21))}
        else:
            edit = self.post("insertText", {"documentHandle": self.handle, "text": "x"})
            edit_result = {"revision": 1, "changed": True}
        move_payload = {"documentHandle": self.handle, "expectedRevision": 1, "action": "move-character-right",
                        "extendSelection": not plain_move, "enabled": False}
        if swap:
            move = self.post("editorActionV2", move_payload)
            edit["message"], move["message"] = move["message"], edit["message"]
        self.answer(edit, edit_result)
        self.settle(held["a1"])
        checkpoint = self.post("save", {"documentHandle": self.handle, "format": "odt"})
        self.answer(checkpoint, {"buffer": b64(b"checkpoint"), "revision": 1})
        if not swap:
            move = self.post("editorActionV2", move_payload)
        anchor, moving = (caret(0, 21), caret(0, 22)) if merge else (caret(0, 2), caret(0, 3))
        self.answer(move, {"action": "move-character-right", "revision": 1, "changed": False,
                           "completion": "selection-callback", "state": state(self.handle, 1, moving, anchor)})
        self.settle(held["a2"])
        self.input("keyup", "ArrowRight", shift=True)
        self.finish(cell, state(self.handle, 1, moving, anchor), arm["expect"]["selectedText"])
        paragraphs = list(arm["expect"]["paragraphs"])
        if wrong_content:
            paragraphs[0] = paragraphs[0] + "!"
        meta = self.save(cell, paragraphs, 1, broken=broken_save)
        self.rows["rows"].append(self.row(cell, arm["fixture"], meta))
        return cell

    def hold(self, arm, rnd, *, extra_after_release=False, extra_before_release=False, no_repeats=False,
             final_anchor_moved=False, overshoot=False, settled_representation=False, double_admit=False,
             unposted_admission=False, refused=False, early_checkpoint=False):
        name = arms.open_name(self.browser, arm["id"], rnd)
        self.open(name, arm["fixture"])
        cid = arms.cell_id(self.browser, arm["id"], rnd)
        cell = self.prepare(cid, "measured", arm["id"], rnd, name, arm["setup"], 0)
        self.arm(cell)
        start = caret(0, 0)
        if early_checkpoint:
            self.answer(self.post("save", {"documentHandle": self.handle, "format": "odt"}),
                        {"buffer": b64(b"checkpoint"), "revision": 0})
        if self.browser == "firefox":
            self.input("keydown", "Shift", shift=True)
        t0 = self.t + 1.0
        times = arm["schedule"]["downsAtMs"]
        release_at = t0 + arm["schedule"]["releaseMs"]
        events = [(t0 + at, 0, ("down", i)) for i, at in enumerate(times)] + [(release_at, 1, ("up", None))]
        outstanding: list = []          # (admission, request, answer_at)
        sim = {"held": False, "active": True, "answered": 0, "busy": t0, "posted": 0}

        def post_extension(admission):
            request = self.post("editorActionV2", {"documentHandle": self.handle, "expectedRevision": 0,
                                                   "action": "move-character-right", "extendSelection": True,
                                                   "enabled": False}, dt=0.0)
            sim["posted"] += 1
            sim["busy"] = max(sim["busy"], self.t) + SERVICE_MS
            outstanding.append((admission, request, sim["busy"], refused and sim["posted"] == 2))

        def answer_due(until):
            while outstanding and outstanding[0][2] <= until:
                admission, request, at, refuse = outstanding.pop(0)
                self.t = max(self.t, at)
                if refuse:
                    self.answer(request, {"code": "EDITOR_ACTION_REFUSED"}, ok=False, dt=0.0)
                    self.settle(admission, ok=False)
                else:
                    sim["answered"] += 1
                    self.answer(request, {"action": "move-character-right", "revision": 0, "changed": False,
                                          "completion": "selection-callback",
                                          "state": state(self.handle, 0, caret(0, sim["answered"]), start)}, dt=0.0)
                    self.settle(admission)
                if sim["held"] and sim["active"]:
                    sim["held"] = False
                    post_extension(self.admit("action", action="move-character-right", extend=True))
        for at, _, (kind, index) in sorted(events):
            answer_due(at)
            self.t = max(self.t, at)
            if kind == "down":
                repeat = index > 0 and not no_repeats

                def dispatch(record, index=index):
                    if index == 0 or (not outstanding and not sim["held"]):
                        post_extension(self.admit("action", action="move-character-right", extend=True,
                                                  input=record))
                        if index == 0 and double_admit:
                            post_extension(self.admit("action", action="move-character-right", extend=True,
                                                      input=record))
                    elif len(outstanding) + (1 if sim["held"] else 0) < 2:
                        sim["held"] = True
                self.input("keydown", "ArrowRight", shift=True, repeat=repeat, prevented=True, during=dispatch,
                           dt=0.0)
            else:
                if extra_before_release:
                    post_extension(self.admit("action", action="move-character-right", extend=True))
                self.input("keyup", "ArrowRight", shift=True, dt=0.0)
                sim["active"], sim["held"] = False, False
                if self.browser == "firefox":
                    self.input("keyup", "Shift", dt=0.0)
                if extra_after_release:
                    post_extension(self.admit("action", action="move-character-right", extend=True))
                if unposted_admission:
                    self.settle(self.admit("action", action="move-character-right", extend=True), ok=False)
        answer_due(float("inf"))
        total = sim["answered"] + (1 if overshoot else 0)
        moving = caret(0, total, 7 if settled_representation else 0)
        final_anchor = caret(0, 1) if final_anchor_moved else start
        self.finish(cell, state(self.handle, 0, moving, final_anchor), arm["fixtureParagraphs"][0][:total])
        meta = self.save(cell, arm["fixtureParagraphs"], 0)
        self.rows["rows"].append(self.row(cell, arm["fixture"], meta))
        return cell

    # --------------------------------------------------------------- output
    def complete(self, special: dict | None = None, readiness: dict | None = None):
        options = special or {}
        plan = arms.table()
        self.readiness(**(readiness or {}))
        for arm in plan:
            if arm["input"]["kind"] == "hold" and self.rows["reference"] is None:
                self.reference(arms.reference_steps())
            for rnd in range(1, arms.ROUNDS + 1):
                extra = options.get((arm["id"], rnd), {})
                if arm["input"]["kind"] == "chain":
                    self.sequence(arm, rnd, **extra)
                else:
                    self.hold(arm, rnd, **extra)
        return self

    def resnapshot(self):
        cells = {c["cellId"]: c for c in self.p["cells"]}
        for shot in self.p["snapshots"]:
            shot.update(judge.release_sets(self.p, cells[shot["cellId"]], shot["seq"]))
        return self

    def write(self, directory: Path, *, snapshots=True) -> Path:
        if snapshots:
            self.resnapshot()
        directory.mkdir(parents=True)
        (directory / "identity.json").write_bytes(arms.encoded(self.identity))
        (directory / "table.json").write_bytes(arms.encoded(arms.table()))
        (directory / "rows.json").write_bytes(arms.encoded(self.rows))
        (directory / "page.json").write_text(json.dumps(self.p), encoding="utf-8")
        for name, raw in self.saves.items():
            (directory / name).parent.mkdir(parents=True, exist_ok=True)
            (directory / name).write_bytes(raw)
        return directory


def remove_request(b: Builder, victim: dict):
    """Drop one request and its terminal as if never recorded; later indices shift with it."""
    index = b.p["requests"].index(victim)
    del b.p["requests"][index]
    b.p["responses"] = [r for r in b.p["responses"] if judge.rkey(r) != judge.rkey(victim)]
    for call in b.p["calls"]:
        for key in ("requestStart", "requestEnd"):
            if call[key] > index:
                call[key] -= 1


def rewrite(directory: Path, name: str, mutate):
    value = json.loads((directory / name).read_text(encoding="utf-8"))
    mutate(value)
    (directory / name).write_text(json.dumps(value), encoding="utf-8")


def row(result: dict, arm: str, rnd: int = 1) -> dict:
    return next(r for r in result["rows"] if r["arm"] == arm and r["round"] == rnd)


def cell_of(b: Builder, arm: str, rnd: int) -> dict:
    return next(c for c in b.p["cells"] if c["cellId"] == arms.cell_id(b.browser, arm, rnd))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v23-four-arms-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_for(self, builder: Builder, name="run", snapshots=True) -> Path:
        return builder.write(self.tmp / name, snapshots=snapshots)

    def assert_row(self, result, arm, outcome, reason, rnd=1):
        entry = row(result, arm, rnd)
        self.assertEqual(entry["outcome"], outcome, entry)
        self.assertIn(reason, entry["why"] or "")
        return entry

    def chrome(self, special: dict | None = None, readiness: dict | None = None) -> Builder:
        return Builder("chrome").complete(special, readiness)


class TableAndMirror(Base):
    def test_the_table_is_four_arms_bound_to_the_93_pins(self):
        plan = arms.table()
        self.assertEqual([a["id"] for a in plan], ["insert-then-shift", "merge-then-shift",
                                                   "held-shift-one-second", "held-shift-two-seconds"])
        self.assertEqual(len(arms.expected_rows()), 24)
        hold1, hold2 = plan[2], plan[3]
        self.assertEqual((len(hold1["schedule"]["downsAtMs"]), hold1["schedule"]["releaseMs"]), (18, 995))
        self.assertEqual((len(hold2["schedule"]["downsAtMs"]), hold2["schedule"]["releaseMs"]), (52, 2015))
        self.assertEqual(hold2["schedule"]["downsAtMs"][:3], [0, 500, 530])
        self.assertEqual(plan[1]["fixtureParagraphs"][1], "Bravo second paragraph")

    def test_a_fixture_that_is_not_its_pin_is_refused(self):
        original = arms.FIXTURE_DIR
        fake = self.tmp / "fixtures"
        fake.mkdir()
        for name in arms.FIXTURE_PINS:
            (fake / name).write_bytes((original / name).read_bytes())
        (fake / "abcd.fodt").write_bytes((original / "abcd.fodt").read_bytes().replace(b"abcd", b"abce"))
        with mock.patch.object(arms, "FIXTURE_DIR", fake):
            with self.assertRaisesRegex(ValueError, "differs from its 9.3 pin"):
                arms.table()

    def test_a_member_added_or_removed_is_detected(self):
        saved = arms.ARMS
        with mock.patch.object(arms, "ARMS", saved + (dict(saved[0], id="extra", check="v23-product-extra"),)):
            with self.assertRaisesRegex(ValueError, "changed size"):
                arms.table()
        with mock.patch.object(arms, "ARMS", saved[:3]):
            with self.assertRaisesRegex(ValueError, "changed size"):
                arms.table()

    def root(self) -> Path:
        root = self.tmp / "root"
        (root / "profiles" / PROFILE).mkdir(parents=True)
        (root / arms.HTML).write_bytes((ROOT / "web" / arms.HTML).read_bytes())
        shell, _ = bundle()
        for path in shell["declared"]:
            target = root / arms.served_module(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / path).read_bytes())
        manifest = {"editorContract": {"abiVersion": 6}, "artifactFiles": {"wasm": "./probe.wasm", "data": "./probe.data"}}
        for name in (*arms.PROFILE_ARTIFACTS, "probe.data"):
            (root / "profiles" / PROFILE / name).write_bytes(
                json.dumps(manifest).encode() if name == "sdk-manifest.json" else name.encode())
        return root

    def test_the_mirror_changes_only_the_module_tag_and_binds_the_whole_served_graph(self):
        root = self.root()
        overrides, ident = arms.observer_mirror(root, PROFILE, candidate_page_sha256=None)
        self.assertEqual(sorted(overrides), sorted([arms.HTML, arms.OBSERVER_ENTRY, arms.OBSERVER_CORE]))
        original = (root / arms.HTML).read_bytes()
        self.assertEqual(overrides[arms.HTML].replace(arms.OBSERVER_TAG, arms.APP_TAG), original)
        self.assertEqual(ident["abiVersion"], 6)
        self.assertEqual(ident["evidenceClass"], "instrument-observation")
        self.assertIn("probe.data", ident["profileArtifacts"])
        shell, _ = bundle()
        self.assertEqual(ident["shell"]["declared"], shell["declared"])
        self.assertEqual(set(ident["shell"]["served"]), set(shell["served"]))
        paths = set(arms.served_paths(ident))
        self.assertTrue(set(shell["served"]) <= paths and f"profiles/{PROFILE}/probe.data" in paths)
        (root / arms.HTML).write_bytes(original.replace(arms.APP_TAG, b""))
        with self.assertRaisesRegex(ValueError, "exactly one app module tag"):
            arms.observer_mirror(root, PROFILE)


class PositiveBaseline(Base):
    def test_both_families_read_pass_for_all_24_rows(self):
        chrome = self.run_for(Builder("chrome").complete(), "chrome")
        firefox = self.run_for(Builder("firefox").complete(), "firefox")
        result = judge.aggregate([chrome, firefox])
        self.assertEqual(result["problems"], [])
        self.assertEqual(result["rows"], 24)
        for arm, value in result["arms"].items():
            self.assertEqual(value["outcome"], judge.PASS, (arm, value, [
                (r["arm"], r["round"], r["browser"], r["why"]) for run in result["runs"] for r in run["rows"]
                if r["outcome"] != judge.PASS]))
        hold = row(result["runs"][0], "held-shift-two-seconds")
        self.assertGreater(hold["observed"]["repeats"], 0)
        self.assertLessEqual(hold["observed"]["growthAfterRelease"], len(hold["observed"]["release"]["wirePending"]))
        self.assertEqual(hold["observed"]["admitted"], hold["observed"]["finalPrefix"])

    def test_adjacent_same_clock_instrument_requests_still_pass(self):
        result = judge.judge_run(self.run_for(Builder("chrome", same_clock=True).complete()))
        self.assertEqual({v["outcome"] for v in result["arms"].values()}, {judge.PASS})

    def test_a_settled_state_representation_differing_from_the_terminal_still_passes(self):
        result = judge.judge_run(self.run_for(self.chrome(
            {("held-shift-two-seconds", 2): {"settled_representation": True}})))
        self.assertEqual(row(result, "held-shift-two-seconds", 2)["outcome"], judge.PASS)

    def test_a_candidate_entrypoint_is_bound_to_its_own_page_hash(self):
        b = self.chrome()
        b.identity["candidatePageSha256"] = "d" * 64
        b.identity["productModuleSha256"] = "d" * 64
        b.p["identity"]["served"][arms.APP_MODULE] = "d" * 64
        self.assertEqual({v["outcome"] for v in judge.judge_run(self.run_for(b))["arms"].values()}, {judge.PASS})


class CausalControls(Base):
    """Each control of the work order's finite list, with its own reason."""

    def test_removed_readiness_mutation_or_save(self):
        result = judge.judge_run(self.run_for(self.chrome(readiness={"no_mutation": True}), "nomutation"))
        self.assertEqual(result["readiness"]["outcome"], judge.NE)
        self.assertIn("readiness wire mutation absent", result["readiness"]["why"])
        self.assert_row(result, "insert-then-shift", judge.NE, "readiness not established")
        result = judge.judge_run(self.run_for(self.chrome(readiness={"unsaved_mutation": True}), "nosave"))
        self.assertIn("readiness save lacks the known mutation", result["readiness"]["why"])
        self.assert_row(result, "held-shift-one-second", judge.NE, "readiness not established")

    def test_synthetic_input_instead_of_trusted(self):
        result = judge.judge_run(self.run_for(self.chrome({("insert-then-shift", 1): {"untrusted": True}})))
        self.assert_row(result, "insert-then-shift", judge.NE, "synthetic (isTrusted false)")

    def test_shift_removed_from_the_trusted_input(self):
        result = judge.judge_run(self.run_for(self.chrome({("merge-then-shift", 1): {"no_shift": True}})))
        self.assert_row(result, "merge-then-shift", judge.NE, "trusted Shift+Right absent")

    def test_public_extension_flag_absent_on_the_wire(self):
        result = judge.judge_run(self.run_for(self.chrome({("insert-then-shift", 2): {"plain_move": True}})))
        self.assert_row(result, "insert-then-shift", judge.FAIL, "public extension flag absent", rnd=2)

    def test_swapped_immediate_request_order(self):
        result = judge.judge_run(self.run_for(self.chrome({("insert-then-shift", 1): {"swap": True}})))
        self.assert_row(result, "insert-then-shift", judge.FAIL, "wire order")

    def test_wrong_fixture(self):
        b = self.chrome()
        opened = next(o for o in b.p["opens"] if o["name"] == arms.open_name("chrome", "merge-then-shift", 1))
        opened["fixtureSha256"] = arms.FIXTURE_PINS["abcd.fodt"]
        self.assert_row(judge.judge_run(self.run_for(b)), "merge-then-shift", judge.NE,
                        "opened fixture differs from its pin")

    def test_wrong_profile(self):
        b = self.chrome()
        b.p["identity"]["profile"] = "e2-editor-v22"
        result = judge.judge_run(self.run_for(b))
        self.assertTrue(all(r["outcome"] == judge.NE and "different profile" in r["why"] for r in result["rows"]))

    def test_wrong_browser(self):
        directory = self.run_for(self.chrome())
        rewrite(directory, "rows.json", lambda v: v.update(browser="firefox"))
        result = judge.judge_run(directory)
        self.assertTrue(all(r["outcome"] == judge.NE and "UA family" in r["why"] for r in result["rows"]))

    def test_wrong_page(self):
        b = self.chrome()
        b.p["identity"]["served"][arms.HTML] = "0" * 64
        result = judge.judge_run(self.run_for(b))
        self.assertTrue(all("browser-fetched page/profile identity differs" in r["why"] for r in result["rows"]))

    def test_a_lagging_or_unstamped_shell_member_is_not_established(self):
        b = self.chrome()
        b.p["identity"]["served"]["sdk/document-sdk.js"] = "1" * 64
        result = judge.judge_run(self.run_for(b))
        self.assertTrue(all("served sdk/document-sdk.js is not the reported shell generation" in r["why"]
                            for r in result["rows"]))

    def test_an_unreported_shell_manifest_is_not_established(self):
        b = self.chrome()
        b.identity["shell"]["bundleFileSha256"] = "2" * 64
        result = judge.judge_run(self.run_for(b))
        self.assertTrue(all("differs from the reported one" in r["why"] for r in result["rows"]))

    def test_diagnostic_override_is_not_acceptance(self):
        b = self.chrome()
        b.identity["diagnosticOverrides"] = ["profileDiagnostic"]
        result = judge.judge_run(self.run_for(b))
        self.assertTrue(all("not product acceptance" in r["why"] for r in result["rows"]))

    def test_corrupt_raw_save(self):
        directory = self.run_for(self.chrome())
        path = directory / "saves" / "chrome-merge-then-shift-r3.odt"
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 0xFF
        path.write_bytes(bytes(raw))
        self.assert_row(judge.judge_run(directory), "merge-then-shift", judge.NE,
                        "raw save bytes differ from their recorded hash", rnd=3)

    def test_wrong_saved_content(self):
        result = judge.judge_run(self.run_for(self.chrome({("merge-then-shift", 2): {"wrong_content": True}})))
        self.assert_row(result, "merge-then-shift", judge.FAIL, "saved content differs", rnd=2)

    def test_erased_required_terminal(self):
        b = self.chrome()
        cell = cell_of(b, "insert-then-shift", 1)
        move = next(r for r in b.p["requests"] if r["generation"] == cell["generation"]
                    and r["message"]["operation"] == "editorActionV2" and r["issuer"] == "product")
        b.p["responses"] = [r for r in b.p["responses"] if judge.rkey(r) != judge.rkey(move)]
        self.assert_row(judge.judge_run(self.run_for(b)), "insert-then-shift", judge.NE,
                        "a required terminal is absent")

    def test_stolen_adjacent_same_clock_request(self):
        b = Builder("chrome", same_clock=True).complete()
        calls = [c for c in b.p["calls"] if c["name"].startswith("chrome-insert-then-shift-r1-")]
        first, second = calls[0], calls[1]
        self.assertEqual(b.p["requests"][first["requestStart"]]["at"], b.p["requests"][second["requestStart"]]["at"])
        first["requestEnd"] = second["requestEnd"]
        result = judge.judge_run(self.run_for(b))
        self.assertTrue(all("overlapping or unordered instrument call request ranges" in r["why"]
                            for r in result["rows"]))

    def test_page_snapshot_substituted_for_engine_state(self):
        b = self.chrome()
        call = next(c for c in b.p["calls"] if c["name"] == "chrome-held-shift-two-seconds-r1-final-state")
        call["result"] = {"state": "ready", "editorState": call["result"], "source": "page-snapshot"}
        self.assert_row(judge.judge_run(self.run_for(b)), "held-shift-two-seconds", judge.NE, "differs from wire")

    def test_post_release_state_moved_into_the_release_slot(self):
        """Raw tamper: the latest pre-release terminal carries a post-release state."""
        b = self.chrome({("held-shift-two-seconds", 1): {"extra_after_release": True}})
        untampered = judge.judge_run(self.run_for(copy.deepcopy(b), "untampered"))
        self.assert_row(untampered, "held-shift-two-seconds", judge.FAIL, "S-12")
        cell = cell_of(b, "held-shift-two-seconds", 1)
        release = next(i for i in b.p["inputs"] if i["cellId"] == cell["cellId"] and i["type"] == "keyup")
        pre = [r for r in b.p["responses"] if r["generation"] == cell["generation"] and r["seq"] < release["seq"]
               and (r["message"].get("result") or {}).get("action") == "move-character-right"]
        pre[-1]["message"]["result"]["state"] = copy.deepcopy(cell["final"]["state"])
        tampered = judge.judge_run(self.run_for(b, "tampered"))
        self.assert_row(tampered, "held-shift-two-seconds", judge.NE,
                        "release state is ahead of the extensions answered by release")

    def test_held_work_misclassified_as_wire_pending(self):
        """Raw records decide the S-12 set: held work released after the keyup is not wire-pending."""
        after = self.chrome({("held-shift-two-seconds", 1): {"extra_after_release": True}})
        result = judge.judge_run(self.run_for(after, "after"))
        self.assert_row(result, "held-shift-two-seconds", judge.FAIL,
                        "S-12: growth after release 2 exceeds wire-pending extensions 1")
        cell = cell_of(after, "held-shift-two-seconds", 1)
        release = next(i for i in after.p["inputs"] if i["cellId"] == cell["cellId"] and i["type"] == "keyup")
        shot = next(s for s in after.p["snapshots"] if s["inputSeq"] == release["seq"] and s["phase"] == "capture")
        self.assertTrue(shot["pageRetained"], "the held repeat is recorded as held at release")
        self.assertEqual(len([p for p in shot["wirePending"] if p[3] == arms.EXTENSION]), 1)
        before = self.chrome({("held-shift-two-seconds", 1): {"extra_before_release": True}})
        entry = self.assert_row(judge.judge_run(self.run_for(before, "before")), "held-shift-two-seconds",
                                judge.PASS, "")
        self.assertEqual(len(entry["observed"]["release"]["wirePending"]), 2)

    def test_omitted_pending_request(self):
        b = self.chrome()
        cell = cell_of(b, "held-shift-two-seconds", 2)
        moves = [r for r in b.p["requests"] if r["generation"] == cell["generation"] and r["issuer"] == "product"
                 and r["message"]["operation"] == "editorActionV2"]
        remove_request(b, moves[-1])
        self.assert_row(judge.judge_run(self.run_for(b)), "held-shift-two-seconds", judge.NE,
                        "an admitted extension or edit has no wire request", rnd=2)

    def test_all_repeats_removed(self):
        result = judge.judge_run(self.run_for(self.chrome({("held-shift-two-seconds", 3): {"no_repeats": True}})))
        self.assert_row(result, "held-shift-two-seconds", judge.NE, "no actual repeat input", rnd=3)

    def test_release_bound_violated(self):
        result = judge.judge_run(self.run_for(self.chrome(
            {("held-shift-two-seconds", 1): {"extra_after_release": True}})))
        self.assert_row(result, "held-shift-two-seconds", judge.FAIL, "S-12")

    def test_copied_round(self):
        b = self.chrome()
        one, two = cell_of(b, "insert-then-shift", 1), cell_of(b, "insert-then-shift", 2)
        for key in ("openSerial", "generation", "documentHandle"):
            two[key] = one[key]
        self.assert_row(judge.judge_run(self.run_for(b)), "insert-then-shift", judge.NE,
                        "duplicate cell: a copied round", rnd=2)


class HoldContradictions(Base):
    """Fix 2/3/7: geometric and admission contradictions reach FAIL; S-12 gates stay on S-12."""

    def test_final_anchor_moved_is_a_failure(self):
        result = judge.judge_run(self.run_for(self.chrome({("held-shift-one-second", 1): {"final_anchor_moved": True}})))
        self.assert_row(result, "held-shift-one-second", judge.FAIL, "final selection anchor moved")

    def test_overshoot_beyond_the_admitted_extensions_is_a_failure(self):
        result = judge.judge_run(self.run_for(self.chrome({("held-shift-two-seconds", 2): {"overshoot": True}})))
        self.assert_row(result, "held-shift-two-seconds", judge.FAIL,
                        "endpoint differs from the single-step reference after the admitted extensions", rnd=2)

    def test_one_press_admitted_twice_is_a_failure(self):
        result = judge.judge_run(self.run_for(self.chrome({("held-shift-one-second", 2): {"double_admit": True}})))
        self.assert_row(result, "held-shift-one-second", judge.FAIL, "one trusted press was admitted more than once",
                        rnd=2)

    def test_an_admission_never_posted_is_not_established(self):
        result = judge.judge_run(self.run_for(self.chrome({("held-shift-one-second", 3): {"unposted_admission": True}})))
        self.assert_row(result, "held-shift-one-second", judge.NE,
                        "an admitted extension or edit has no wire request", rnd=3)

    def test_a_refused_extension_terminal_is_a_failure(self):
        result = judge.judge_run(self.run_for(self.chrome({("held-shift-two-seconds", 3): {"refused": True}})))
        self.assert_row(result, "held-shift-two-seconds", judge.FAIL, "an admitted extension was refused or cancelled",
                        rnd=3)

    def test_s12_gates_bind_the_two_second_arm_only(self):
        special = {("held-shift-one-second", 1): {"early_checkpoint": True},
                   ("held-shift-two-seconds", 1): {"early_checkpoint": True}}
        result = judge.judge_run(self.run_for(self.chrome(special)))
        one = self.assert_row(result, "held-shift-one-second", judge.PASS, "")
        self.assertIn("dirty checkpoint", one["observed"]["release"]["notEstablished"])
        self.assert_row(result, "held-shift-two-seconds", judge.NE, "a dirty checkpoint or text/delete queue")

    def test_a_reference_call_on_another_generation_is_not_established(self):
        b = self.chrome()
        call = next(c for c in b.p["calls"] if c["name"] == "chrome-reference-step-7")
        call["generation"] = 999
        result = judge.judge_run(self.run_for(b))
        self.assertEqual(result["reference"]["outcome"], judge.NE)
        self.assertIn("ran on another Worker generation", result["reference"]["why"])
        self.assert_row(result, "held-shift-one-second", judge.NE, "same-browser single-step reference absent")


class NeverStopsTheRunner(Base):
    """Fix 1: nothing in the block or the reader may raise into the runner."""

    def test_unreadable_saved_xml_is_not_established(self):
        result = judge.judge_run(self.run_for(self.chrome({("insert-then-shift", 3): {"broken_save": True}})))
        self.assert_row(result, "insert-then-shift", judge.NE, "saved bytes are not a readable ODT: ParseError", rnd=3)

    def test_any_reader_exception_is_not_established(self):
        directory = self.run_for(self.chrome())
        with mock.patch.object(arms, "table", side_effect=RuntimeError("boom")):
            result = judge.judge_run(directory)
        self.assertTrue(all(v["outcome"] == judge.NE and "reader exception: RuntimeError: boom" in v["why"]
                            for v in result["arms"].values()))

    def test_run_block_never_raises(self):
        hooks = {"open_bytes": "", "capture_save": None, "read_save": "", "save_count": ""}
        ident = identity()
        with mock.patch.object(arms, "evaluate", side_effect=OSError("browser gone")):
            summary = arms.run_block(object(), "chrome", hooks, self.tmp / "a", ident)
        self.assertTrue(any("browser gone" in f for f in summary["failures"]))
        with mock.patch.object(arms, "table", side_effect=ValueError("table drift")), \
                mock.patch.object(arms, "evaluate", return_value=None):
            summary = arms.run_block(object(), "chrome", hooks, self.tmp / "b", ident)
        self.assertTrue(any("table drift" in f for f in summary["failures"]))
        blocker = self.tmp / "file"
        blocker.write_text("x")
        summary = arms.run_block(object(), "chrome", hooks, blocker / "c", ident)
        self.assertIn("artifact directory unusable", summary["refused"])
        summary = arms.run_block(object(), "chrome", hooks, self.tmp / "b", ident)
        self.assertEqual(summary["refused"], "the artifact directory already exists")

    def test_the_neutral_restore_requires_a_ready_page(self):
        hooks = {"open_file": "OPEN ARG_URL ARG_NAME", "read_state": "STATE"}
        opened = {}

        def ready(session, expression):
            if expression.startswith("OPEN"):
                opened["name"] = expression.split()[-1]
                return "dispatched"
            return {"state": "ready", "doc": opened.get("name")}
        with mock.patch.object(arms, "evaluate", side_effect=ready):
            self.assertTrue(arms.restore_neutral(object(), hooks, limit_s=1)["ok"])
        with mock.patch.object(arms, "evaluate", side_effect=lambda s, e: "dispatched" if e.startswith("OPEN")
                               else {"state": "recoverable-error", "doc": "x"}):
            failed = arms.restore_neutral(object(), hooks, limit_s=0.3)
        self.assertFalse(failed["ok"])
        self.assertEqual(len(failed["attempts"]), 2)
        verdict = arms.with_restore({"arms": {"a": {"outcome": "PASS", "ok": True}}}, failed)
        self.assertEqual(verdict["arms"]["a"]["outcome"], "NOT_ESTABLISHED")


class Aggregate(Base):
    def test_the_same_family_twice_or_a_duplicate_artifact_is_not_24_rows(self):
        chrome = self.run_for(Builder("chrome").complete(), "chrome")
        result = judge.aggregate([chrome, chrome])
        self.assertTrue(any("browser families" in p for p in result["problems"]))
        self.assertTrue(any("duplicate page artifact" in p for p in result["problems"]))
        self.assertTrue(all(v["outcome"] != judge.PASS for v in result["arms"].values()))

    def test_one_family_alone_is_not_established(self):
        result = judge.aggregate([self.run_for(Builder("firefox").complete(), "firefox")])
        self.assertTrue(any("row population differs" in p for p in result["problems"]))
        self.assertTrue(all(v["outcome"] == judge.NE for v in result["arms"].values()))

    def test_a_fail_row_makes_its_arm_fail(self):
        chrome = self.run_for(Builder("chrome").complete({("insert-then-shift", 3): {"swap": True}}), "c")
        firefox = self.run_for(Builder("firefox").complete(), "f")
        result = judge.aggregate([chrome, firefox])
        self.assertEqual(result["arms"]["insert-then-shift"]["outcome"], judge.FAIL)
        self.assertEqual(result["arms"]["merge-then-shift"]["outcome"], judge.PASS)


class ObserverSemantics(Base):
    """The observer's own Worker wrapper and release sets, driven by Node with its actual source."""

    def test_node_drives_the_actual_observer_source(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        script = ROOT / "tests" / "v23-product-four-arms-observer.test.mjs"
        done = subprocess.run([node, "--test", str(script)], capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_js_and_python_release_sets_agree_including_queued_work(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        script = ROOT / "tests" / "v23-product-four-arms-observer.test.mjs"
        done = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=120,
                              env={"V23_FOUR_ARMS_EMIT": "1", "PATH": ""})
        self.assertEqual(done.returncode, 0, done.stderr)
        record = json.loads(done.stdout)
        cells = {c["cellId"]: c for c in record["cells"]}
        self.assertTrue(any(s["unposted"] for s in record["snapshots"]), "a queued-work snapshot is present")
        self.assertTrue(any(s["pageRetained"] for s in record["snapshots"]), "a retained-candidate snapshot is present")
        for shot in record["snapshots"]:
            want = judge.release_sets(record, cells[shot["cellId"]], shot["seq"])
            self.assertEqual({k: shot[k] for k in want}, want, shot)


class IntegrationPatch(Base):
    """The runner change exists only as a patch; it must apply to HEAD and declare the four sites."""

    def patched_runner(self) -> str:
        work = self.tmp / "tree"
        (work / "wasm_sdk_probe" / "tools").mkdir(parents=True)
        target = work / "wasm_sdk_probe" / "tools" / "run_e2_c_product_path.py"
        target.write_bytes((ROOT / "tools" / "run_e2_c_product_path.py").read_bytes())
        done = subprocess.run(["git", "apply", "--check", str(PATCH)], capture_output=True, text=True, cwd=work)
        self.assertEqual(done.returncode, 0, done.stderr)
        subprocess.run(["git", "apply", str(PATCH)], check=True, capture_output=True, cwd=work)
        return target.read_text(encoding="utf-8")

    def test_the_patch_applies_keeps_the_42_and_declares_exactly_the_table_sites(self):
        if not PATCH.is_file():
            self.skipTest("integration patch not written")
        from run_e2_c_product_path import declared_check_ids
        original = (ROOT / "tools" / "run_e2_c_product_path.py").read_text(encoding="utf-8")
        self.assertEqual(declared_check_ids(original), ORIGINAL_CHECKS)
        text = self.patched_runner()
        patched = declared_check_ids(text)
        new = [a["check"] for a in arms.table()]
        self.assertEqual([c for c in patched if c not in new], ORIGINAL_CHECKS)
        self.assertEqual(patched[patched.index(new[0]):patched.index(new[-1]) + 1], new)
        self.assertEqual(patched[patched.index(new[-1]) + 1:], ["a-boundary-arrow-press-does-not-cost-the-work"])
        self.assertEqual(sorted(judge.declared_population(text)), sorted(new))
        removed = text.replace('check("v23-product-merge-then-shift"', 'check_("v23-product-merge-then-shift"')
        result = judge.aggregate([], removed)
        self.assertTrue(any("literal check sites" in p for p in result["problems"]))
        compile(text, "run_e2_c_product_path.py", "exec")


if __name__ == "__main__":
    unittest.main()
