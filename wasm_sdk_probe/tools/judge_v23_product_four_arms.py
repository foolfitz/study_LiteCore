#!/usr/bin/env python3
"""Independent raw-artifact reader for the four ABI6 product arms.

Reads only what `v23_product_four_arms.run_block` wrote per browser -- identity.json, table.json,
rows.json, page.json (the observer's raw record) and saves/*.odt -- and never the runner's own
verdicts.  Per row and in aggregate:

  PASS             every witness present and bound, and the exact result holds;
  FAIL             every witness present and bound, and the product contradicts the result
                   (wrong text, order, selection, anchor, admission, revision or the S-12 bound);
  NOT_ESTABLISHED  a witness is missing, ambiguous, malformed, unbound or duplicated.

Each row is judged in two phases: `establish` may only raise NotEstablished, `decide` may only
raise ProductFailure, so a FAIL can never stand on an unfulfilled prerequisite.  Any other
exception anywhere is NOT_ESTABLISHED with its text recorded: the runner must always reach 096.

Aggregate: the four-member table x both real browser families x N=3 distinct fresh cells = 24
rows; a missing, extra or duplicated row, or one family twice, is NOT_ESTABLISHED.  A FAIL row
makes its arm FAIL.  The runner's literal check sites are compared with the table, read from the
runner's source by its own `declared_check_ids`.

Usage:
  judge_v23_product_four_arms.py RUN_DIR [RUN_DIR ...] [--runner PATH] [--out FILE]
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odt_paragraphs import paragraph_texts_from_xml  # noqa: E402
import v23_product_four_arms as arms  # noqa: E402

PASS, FAIL, NE = "PASS", "FAIL", "NOT_ESTABLISHED"
DEAD_STATES = ("recoverable-error", "restart-required", "expired")
MODIFIER_KEYS = ("Shift", "Control", "Alt", "Meta")
RUNNER = Path(__file__).resolve().parent / "run_e2_c_product_path.py"
CHECK_PREFIX = "v23-product-"


class NotEstablished(ValueError):
    pass


class ProductFailure(ValueError):
    pass


def need(value, message):
    if not value:
        raise NotEstablished(message)


def contradict(value, message):
    if not value:
        raise ProductFailure(message)


def binary(value) -> bytes:
    need(isinstance(value, dict) and value.get("encoding") == "base64", "binary wire evidence absent")
    raw = base64.b64decode(value["data"], validate=True)
    need(len(raw) == value["bytes"], "binary length mismatch")
    return raw


def odt_paragraphs(raw: bytes) -> list[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return paragraph_texts_from_xml(archive.read("content.xml"))
    except Exception as error:                        # noqa: BLE001 -- zip, zlib, XML: all unreadable
        raise NotEstablished(f"saved bytes are not a readable ODT: {type(error).__name__}: {error}") from error


# ------------------------------------------------- categories and release sets
# Same rules as `admissionCategory` / `requestCategory` / `releaseSets` in
# web/v23-product-four-arms-observer-core.js.  The tests run both on one record.

DELETE_ACTIONS = ("delete-backward", "delete-forward", "delete-selection")


def admission_category(a: dict):
    if a.get("method") == "commitText":
        return "text"
    if a.get("method") == "deleteKey":
        return "delete"
    if a.get("method") == "action":
        if a.get("action") in DELETE_ACTIONS:
            return "delete"
        if str(a.get("action")).startswith("move-"):
            return f"move:{a.get('action')}:{'true' if a.get('extendSelection') is True else 'false'}"
        return f"action:{a.get('action')}"
    return None


def request_category(r: dict):
    message = r.get("message") or {}
    if message.get("operation") not in ("editorActionV2", "insertText"):
        return None
    if message["operation"] == "insertText":
        return "text"
    payload = message.get("payload") or {}
    if payload.get("action") in DELETE_ACTIONS:
        return "delete"
    if str(payload.get("action")).startswith("move-"):
        return f"move:{payload.get('action')}:{'true' if payload.get('extendSelection') is True else 'false'}"
    return f"action:{payload.get('action')}"


def rkey(item: dict) -> tuple:
    return (item["generation"], item["message"]["requestId"])


def release_sets(page: dict, cell: dict, boundary: int) -> dict:
    generation = cell["generation"]

    def in_cell(item):
        return cell["armSeq"] <= item["seq"] < boundary
    admissions = [a for a in page["admissions"] if a.get("issuer") == "product"
                  and a.get("generation") == generation and in_cell(a)]
    requests = [r for r in page["requests"] if r.get("issuer") == "product"
                and r["generation"] == generation and in_cell(r)]
    terminals = {rkey(t) for t in page["responses"] + page["cancels"]
                 if t["generation"] == generation and t["seq"] < boundary}
    by_category: dict = {}
    for request in requests:
        category = request_category(request)
        if category is not None:
            by_category.setdefault(category, []).append(request)
    used: dict = {}
    unposted = []
    for admission in admissions:
        category = admission_category(admission)
        if category is None or category == "save":
            continue
        index = used.get(category, 0)
        used[category] = index + 1
        posted = index < len(by_category.get(category, []))
        settled = type(admission.get("settledSeq")) is int and admission["settledSeq"] < boundary
        if not posted and not settled:
            unposted.append(admission["id"])
    last = max((a["seq"] for a in admissions), default=-1)
    retained = [i["seq"] for i in page["inputs"] if i.get("type") == "keydown" and i.get("isTrusted") is True
                and in_cell(i) and i["seq"] > last and type(i.get("afterSeq")) is int and i["afterSeq"] < boundary
                and i.get("defaultPrevented") is True and i.get("admissions") == []]
    pending = [[r["generation"], r["message"]["requestId"], r["message"]["operation"], request_category(r)]
               for r in page["requests"] if r.get("issuer") == "product" and r["generation"] == generation
               and r["seq"] < boundary and rkey(r) not in terminals]
    extension_keys = {rkey(r) for r in requests if request_category(r) == arms.EXTENSION}
    latest = None
    for response in page["responses"]:
        if response["generation"] != generation or response["seq"] >= boundary:
            continue
        if rkey(response) in extension_keys and (latest is None or response["seq"] > latest["seq"]):
            latest = response
    return {"admitted": [a["id"] for a in admissions], "unposted": unposted, "pageRetained": retained,
            "wirePending": pending,
            "latestExtensionTerminal": list(rkey(latest)) if latest else None}


# ------------------------------------------------------------------ the record

def ua_family(ua: str):
    if re.search(r"Firefox/[0-9]", ua or ""):
        return "firefox"
    if re.search(r"(?:Headless)?Chrome/[0-9]", ua or ""):
        return "chrome"
    return None


class Record:
    """One browser's raw page record, its stream invariants checked once."""

    def __init__(self, page: dict, browser: str, identity: dict, repo: Path = arms.PROJECT):
        self.page, self.browser, self.identity = page, browser, identity
        need(isinstance(page, dict) and page.get("schema") == 1
             and page.get("instrument") == "v23-product-four-arms", "not a four-arms observer record")
        need(ua_family(page.get("userAgent")) == browser, "actual UA family differs from the run's browser")
        self._identity(repo)
        self._stream()
        self.cells = {}
        for cell in page["cells"]:
            need(cell.get("cellId") not in self.cells, "duplicate cell record")
            self.cells[cell["cellId"]] = cell

    def _identity(self, repo: Path):
        i = self.identity
        page_identity = self.page.get("identity") or {}
        served = page_identity.get("served") or {}
        need(i.get("installed") is True and i.get("evidenceClass") == "instrument-observation",
             "identity is not the declared observer mirror")
        need(not i.get("diagnosticOverrides"), "a diagnostic mirror/profile override is not product acceptance")
        need(i.get("abiVersion") == 6, "the served profile is not ABI6")
        profile = i.get("profile")
        need(isinstance(profile, str) and profile, "profile unbound")
        need(page_identity.get("profile") == profile, "page ran a different profile")
        need(i.get("observerEntrySha256") == arms.digest((repo / "web" / arms.OBSERVER_ENTRY).read_bytes())
             and i.get("observerCoreSha256") == arms.digest((repo / "web" / arms.OBSERVER_CORE).read_bytes()),
             "observer bytes differ from this reader's instrument source")
        original = (repo / "web" / arms.HTML).read_bytes()
        need(i.get("originalHtmlSha256") == arms.digest(original)
             and i.get("servedHtmlSha256") == arms.digest(arms.transform_html(original)),
             "served HTML is not the declared one-tag transformation")
        # The whole served import graph against the shell generation the runner reported.
        shell = i.get("shell") or {}
        manifest_path = repo / str(shell.get("bundle"))
        need(manifest_path.is_file(), "the reported shell bundle manifest is absent from this tree")
        raw = manifest_path.read_bytes()
        need(arms.digest(raw) == shell.get("bundleFileSha256"), "the shell bundle manifest differs from the reported one")
        manifest = json.loads(raw)
        declared = {row["path"]: row["sha256"] for row in manifest.get("included") or []}
        need(declared and declared == shell.get("declared"), "reported shell members differ from the manifest")
        entry = manifest.get("entrypoint")
        candidate = i.get("candidatePageSha256")
        for path, sha in declared.items():
            got = served.get(arms.served_module(path))
            allowed = {sha} | ({candidate} if path == entry and candidate else set())
            need(got in allowed, f"served {path} is not the reported shell generation (lagging or unstamped mirror)")
        need(served.get(arms.APP_MODULE) == i.get("productModuleSha256"), "product module identity differs")
        artifacts = i.get("profileArtifacts") or {}
        need(set(arms.PROFILE_ARTIFACTS) <= set(artifacts) and all(artifacts.values()),
             "profile artifacts unbound")
        need(set(served) == set(arms.served_paths(i)), "the page fetched a different served graph")
        want = {arms.HTML: i["servedHtmlSha256"], arms.OBSERVER_ENTRY: i["observerEntrySha256"],
                arms.OBSERVER_CORE: i["observerCoreSha256"],
                **{f"profiles/{profile}/{n}": h for n, h in artifacts.items()}}
        need(all(served.get(k) == v for k, v in want.items()),
             "browser-fetched page/profile identity differs from the declared mirror")
        self.profile = profile

    def _stream(self):
        p = self.page
        for name in ("workers", "requests", "responses", "events", "cancels", "inputs", "admissions",
                     "calls", "opens", "cells", "snapshots", "workerErrors"):
            need(isinstance(p.get(name), list), f"record lacks {name}")
        seqs = []
        for name in ("requests", "responses", "events", "cancels", "inputs", "admissions", "calls", "snapshots"):
            values = [x.get("seq") for x in p[name]]
            need(all(type(v) is int for v in values) and values == sorted(values), f"{name} sequence invalid")
            seqs += values
        need(len(seqs) == len(set(seqs)), "sequence numbers reused across records")
        self.requests, self.replies, self.cancels = {}, {}, {}
        for item in p["requests"]:
            need(item.get("issuer") in ("product", "instrument"), "request issuer unrecorded")
            need(rkey(item) not in self.requests, "duplicate request identity")
            self.requests[rkey(item)] = item
        for item in p["responses"]:
            need(rkey(item) not in self.replies, "duplicate terminal")
            need(rkey(item) in self.requests and self.requests[rkey(item)]["seq"] < item["seq"],
                 "terminal has no earlier posted request")
            self.replies[rkey(item)] = item
        for item in p["cancels"]:
            need(rkey(item) in self.requests and self.requests[rkey(item)]["seq"] < item["seq"],
                 "cancel has no earlier posted request")
            self.cancels[rkey(item)] = item
        previous = 0
        self.calls = {}
        for call in p["calls"]:
            start, end = call.get("requestStart"), call.get("requestEnd")
            # Corrected half-open ownership: integer, nonempty, in bounds, ordered, nonoverlapping.
            need(type(start) is int and type(end) is int and 0 <= start < end <= len(p["requests"]),
                 "invalid instrument call request range")
            need(start >= previous, "overlapping or unordered instrument call request ranges")
            previous = end
            need(call.get("name") not in self.calls, "reused instrument call name")
            self.calls[call["name"]] = call
        owned = {i for c in p["calls"] for i in range(c["requestStart"], c["requestEnd"])}
        for index, item in enumerate(p["requests"]):
            need((item["issuer"] == "instrument") == (index in owned), "request ownership differs from its issuer")

    # ---------------------------------------------------------------- calls
    def call(self, name: str, operation: str, cell: dict):
        """An instrument call bound to the wire, to this cell's document AND its Worker generation."""
        handle, generation = cell["documentHandle"], cell["generation"]
        call = self.calls.get(name)
        need(call is not None and call.get("ok") is True, f"missing/refused instrument call {name}")
        window = self.page["requests"][call["requestStart"]:call["requestEnd"]]
        need(len(window) == 1, f"instrument call {name} owns {len(window)} requests")
        request = window[0]
        need(request["message"].get("operation") == operation and request.get("callId") == call["id"],
             f"wire call {name} differs")
        need(request["generation"] == call.get("generation") == generation,
             f"instrument call {name} ran on another Worker generation")
        need(call["startedAt"] <= request["at"] <= call["finishedAt"], f"request outside call {name}")
        terminal = self.replies.get(rkey(request))
        need(terminal is not None and terminal["message"].get("ok") is True, f"missing/refused terminal {name}")
        need(request["at"] <= terminal["at"] <= call["finishedAt"], f"terminal outside call {name}")
        need((request["message"].get("payload") or {}).get("documentHandle") == handle, f"wrong document {name}")
        need(call.get("result") == terminal["message"].get("result"), f"public result of {name} differs from wire")
        return call, request, terminal

    def state(self, name, cell):
        _, request, terminal = self.call(name, "editorGetStateV2", cell)
        result = terminal["message"]["result"]
        need(result.get("documentHandle") == cell["documentHandle"], f"state {name} belongs to another document")
        return result, request, terminal

    def text(self, name, cell):
        _, _, terminal = self.call(name, "getSelection", cell)
        value = (terminal["message"].get("result") or {}).get("text")
        need(isinstance(value, str), f"selection text {name} absent")
        return value

    # -------------------------------------------------------------- the open
    def opened(self, row: dict, cell: dict) -> tuple:
        opens = [o for o in self.page["opens"] if o.get("name") == row["openName"]]
        need(len(opens) == 1 and opens[0].get("ok") is True and type(opens[0].get("finishSeq")) is int,
             "actual fresh open absent/nonunique")
        o = opens[0]
        need(o.get("fixtureSha256") == arms.FIXTURE_PINS[row["fixture"]] == row.get("fixtureSha256"),
             "opened fixture differs from its pin")
        need(cell.get("openSerial") == o["serial"] and cell.get("generation") == o.get("generation")
             and cell.get("documentHandle") == o.get("documentHandle"), "cell is not bound to its open")
        wire = [r for r in self.page["requests"] if r["generation"] == o["generation"]
                and r["message"].get("operation") == "open"]
        need(len(wire) == 1 and wire[0]["issuer"] == "product", "wire open absent/nonunique")
        request = wire[0]
        need(o["seq"] < request["seq"] < o["finishSeq"], "wire open outside the observed open")
        terminal = self.replies.get(rkey(request))
        need(terminal is not None and terminal["message"].get("ok") is True, "open terminal absent/refused")
        need((terminal["message"].get("result") or {}).get("documentHandle") == o["documentHandle"],
             "open terminal handle differs")
        payload = request["message"].get("payload") or {}
        need(arms.digest(binary(payload.get("buffer"))) == arms.FIXTURE_PINS[row["fixture"]],
             "wire open bytes differ from the pinned fixture")
        need(payload.get("name") == row["openName"], "wire open name differs")
        workers = [w for w in self.page["workers"] if w.get("generation") == o["generation"]]
        need(len(workers) == 1 and workers[0]["url"].endswith(f"/profiles/{self.profile}/sdk-worker.js"),
             "actual worker differs from the bound profile")
        return rkey(request)

    def no_recovery(self, cell: dict, start: int, generation_after) -> None:
        need(generation_after == cell["generation"], "the Worker generation changed during the cell")
        need(not [w for w in self.page["workers"] if start <= w["seq"] < cell["endSeq"]]
             and not [e for e in self.page["workerErrors"] if start <= e["seq"] < cell["endSeq"]],
             "a Worker was replaced or failed during the cell (recovery)")

    def setup(self, cell: dict, plan: dict) -> dict:
        cid = cell["cellId"]
        need(cell.get("setup", {}).get("start") is not None, "setup record absent")
        _, request, terminal = self.call(f"{cid}-search", "search", cell)
        need(request["message"]["payload"].get("query") == plan["query"], "setup query differs")
        rows = (terminal["message"].get("result") or {}).get("selections")
        need(isinstance(rows, list) and len(rows) == 1 and rows[0].get("part") in (0, "0")
             and isinstance(rows[0].get("rectangles"), str), "setup search match not unique")
        boxes = rows[0]["rectangles"].split(";")
        need(len(boxes) == 1 and re.fullmatch(r"\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*", boxes[0]),
             "setup search match not one line")
        r = [int(x) for x in boxes[0].split(",")]
        need(r[2] > 0 and r[3] > 0, "invalid setup rectangle")
        _, request, _ = self.call(f"{cid}-place", "editorPlaceCaretV2", cell)
        payload = request["message"]["payload"]
        need((payload.get("xTwips"), payload.get("yTwips")) == (r[0], r[1] + r[3] // 2),
             "setup click not derived from the actual search")
        start, _, _ = self.state(f"{cid}-start-state", cell)
        caret = start.get("caret") or {}
        need((caret.get("x"), caret.get("y")) == (r[0], r[1]) and (start.get("selection") or {}).get("collapsed") is True,
             "actual text-start caret differs")
        need(cell["setup"]["start"] == start, "page setup record differs from the wire state")
        out = {"rectangle": r, "start": start, "anchor": (r[0], r[1])}
        if plan["kind"] == "select":
            states = [start]
            for i in range(plan["end"]):
                _, request, _ = self.call(f"{cid}-right-{i}", "editorActionV2", cell)
                payload = request["message"]["payload"]
                need(payload.get("action") == "move-character-right" and payload.get("extendSelection") is False,
                     "setup move differs")
                states.append(self.state(f"{cid}-right-{i}-state", cell)[0])

            def point(c):
                return c["x"], c["y"] + int(c["height"] // 2)
            _, request, _ = self.call(f"{cid}-select", "editorSelectRangeV2", cell)
            payload = request["message"]["payload"]
            a, b = point(states[plan["start"]]["caret"]), point(states[plan["end"]]["caret"])
            need((payload.get("startXTwips"), payload.get("startYTwips"), payload.get("endXTwips"),
                  payload.get("endYTwips")) == (*a, *b), "public selection coordinates differ")
            need(self.text(f"{cid}-selected-text", cell) == plan["selectedText"], "public selection text differs")
            out["anchor"] = (states[plan["start"]]["caret"]["x"], states[plan["start"]]["caret"]["y"])
        before, _, _ = self.state(f"{cid}-before-state", cell)
        out["before"] = before
        if plan["kind"] == "select":
            sel = before.get("selection") or {}
            need(sel.get("observed") is True and sel.get("collapsed") is False, "planned range not selected")
        else:
            need((before.get("caret") or {}) == caret and (before.get("selection") or {}).get("collapsed") is True,
                 "caret moved before the measured input")
        setup_calls = [c for n, c in self.calls.items() if n.startswith(f"{cid}-")
                       and not n.startswith((f"{cid}-final", f"{cid}-step", f"{cid}-text"))]
        armed = cell.get("armSeq")
        need(all(c["seq"] > cell["seq"] and (armed is None or c["finishSeq"] < armed) for c in setup_calls),
             "setup calls are not between the cell's open and its measured input")
        return out

    def saved(self, run_dir: Path, row: dict, cell: dict) -> list[str]:
        save = row.get("save") or {}
        need(save.get("captured") is True and isinstance(save.get("file"), str), "product save not captured")
        raw = (run_dir / save["file"]).read_bytes()
        need(arms.digest(raw) == save.get("sha256") and len(raw) == save.get("bytes"),
             "raw save bytes differ from their recorded hash")
        need(cell.get("save") == save, "page cell does not bind this save artifact")
        lo, hi = cell["measureEndSeq"], cell["endSeq"]
        wire = [r for r in self.page["requests"] if r["issuer"] == "product" and lo < r["seq"] < hi
                and r["message"].get("operation") == "save" and r["generation"] == cell["generation"]]
        need(len(wire) == 1, "product save wire request absent/nonunique")
        terminal = self.replies.get(rkey(wire[0]))
        need(terminal is not None and terminal["message"].get("ok") is True and terminal["seq"] < hi,
             "product save terminal absent/refused")
        need(binary((terminal["message"].get("result") or {}).get("buffer")) == raw,
             "captured product save differs from the wire save")
        admitted = [a for a in self.page["admissions"] if a.get("method") == "save" and a.get("issuer") == "product"
                    and lo < a["seq"] < wire[0]["seq"]]
        need(len(admitted) == 1, "the save was not the product Save button's admission")
        return odt_paragraphs(raw)

    def window(self, cell: dict) -> dict:
        """The measured window and its generic witnesses."""
        lo, hi = cell.get("armSeq"), cell.get("measureEndSeq")
        need(type(lo) is int and type(hi) is int and lo < hi < cell.get("endSeq", -1), "measured window unbound")
        need(not [c for c in self.page["calls"] if lo <= c["seq"] < hi]
             and not [r for r in self.page["requests"] if r["issuer"] == "instrument" and lo <= r["seq"] < hi],
             "an instrument wait/read was inserted into the measured sequence")
        sink = cell.get("sinkAtArm") or {}
        need(sink.get("active") is True and sink.get("connected") is True and sink.get("disabled") is False
             and sink.get("readOnly") is False and sink.get("documentHandle") == cell["documentHandle"],
             "the product sink was not the focused, enabled sink of this document")
        need(cell.get("generationAtArm") == cell["generation"], "the Worker generation changed during the cell")
        self.no_recovery(cell, lo, cell.get("generationAtFinish"))
        need(cell.get("pageStateAtFinish") not in DEAD_STATES and cell.get("pageStateAtFinish") is not None,
             "the session ended dead")
        measured = [i for i in self.page["inputs"] if lo <= i["seq"] < hi and i["type"] != "input"]
        need(all(i.get("isTrusted") is True for i in measured), "a measured input is synthetic (isTrusted false)")
        for item in measured:
            for phase in ("capture", "after"):
                shots = [s for s in self.page["snapshots"] if s["inputSeq"] == item["seq"] and s["phase"] == phase]
                need(len(shots) == 1, f"release-set record missing at a measured {item['type']}")
                shot = shots[0]
                want = release_sets(self.page, cell, shot["seq"])
                need({k: shot.get(k) for k in want} == want,
                     f"recorded release sets differ from the raw reconstruction at {item['type']} {item['seq']}")
        keys = [i for i in measured if i["type"] == "keydown" and i.get("key") not in MODIFIER_KEYS]
        need(all(k.get("targetId") == "sink" and (k.get("sink") or {}).get("active") is True
                 and (k.get("sink") or {}).get("documentHandle") == cell["documentHandle"] for k in keys),
             "a measured key did not reach the focused product sink of this document")
        return {"lo": lo, "hi": hi, "inputs": measured, "keydowns": keys}

    def product_requests(self, cell, lo, hi):
        return [r for r in self.page["requests"] if r["issuer"] == "product" and r["generation"] == cell["generation"]
                and lo <= r["seq"] < hi]

    def product_admissions(self, cell, lo, hi):
        return [a for a in self.page["admissions"] if a.get("issuer") == "product"
                and a.get("generation") == cell["generation"] and lo <= a["seq"] < hi]


# ---------------------------------------------------------------- endpoints

def xy(point):
    need(isinstance(point, dict) and all(type(point.get(k)) in (int, float) for k in ("x", "y")),
         "endpoint coordinate missing")
    return point["x"], point["y"]


def observed(state: dict) -> dict:
    """Establish only that a state has a caret and an observed selection; geometry is decided later."""
    need(isinstance(state, dict), "engine state missing")
    sel = state.get("selection") or {}
    need(sel.get("observed") is True and type(sel.get("collapsed")) is bool, "selection unobserved")
    xy(state.get("caret"))
    if sel["collapsed"] is False:
        xy(sel.get("start"))
        xy(sel.get("end"))
    return state


def geometry(state: dict):
    """(collapsed, anchor, moving) by pairing with the caret; anchor None when the caret is not an end."""
    sel = state["selection"]
    caret = (state["caret"]["x"], state["caret"]["y"])
    if sel["collapsed"]:
        return True, caret, caret
    ends = [(sel["start"]["x"], sel["start"]["y"]), (sel["end"]["x"], sel["end"]["y"])]
    if ends.count(caret) != 1:
        return False, None, caret
    return False, ends[1] if ends[0] == caret else ends[0], caret


def pair_key(state: dict):
    """A terminal state's endpoint key, for matching against the reference's terminal states."""
    collapsed, anchor, moving = geometry(observed(state))
    need(anchor is not None, "anchor/moving endpoints not uniquely paired")
    return (moving, True) if collapsed else ((anchor, moving), False)


class Reference:
    """The fresh same-browser single public extended-Right reference: step i -> prefix i."""

    def __init__(self, record: Record, row: dict, paragraph: str, steps: int):
        cell = record.cells.get(row["cellId"])
        need(cell is not None and row.get("kind") == "reference", "hold reference cell absent")
        record.opened(row, cell)
        self.setup = record.setup(cell, arms.REFERENCE_SETUP)
        need(type(cell.get("endSeq")) is int, "reference cell not closed")
        record.no_recovery(cell, cell["seq"], cell.get("generationAtClose"))
        need(cell.get("pageStateAtClose") not in DEAD_STATES and cell.get("pageStateAtClose") is not None,
             "the reference session ended dead")
        self.map: dict = {}
        self.texts = [""]
        self.add(pair_key(self.setup["start"]), 0)
        anchors = set()
        for i in range(1, steps + 1):
            _, request, terminal = record.call(f"{row['cellId']}-step-{i}", "editorActionV2", cell)
            payload = request["message"]["payload"]
            need(payload.get("action") == "move-character-right" and payload.get("extendSelection") is True,
                 "reference step is not a public extended Right")
            text = record.text(f"{row['cellId']}-text-{i}", cell)
            need(text == paragraph[:i], "reference active selection is not the step's prefix")
            key = pair_key((terminal["message"].get("result") or {}).get("state"))
            need(key[1] is False, "reference step left a collapsed selection")
            anchors.add(key[0][0])
            self.add(key, i)
            self.texts.append(text)
        need(len(anchors) == 1, "reference anchor moved")
        # The anchor as the TERMINAL representation reports it; hold terminals are compared with
        # this, never with a getState representation of the same position.
        self.terminal_anchor = anchors.pop()
        self.anchor, self.steps, self.serial = self.setup["anchor"], steps, cell["openSerial"]

    def add(self, key, prefix):
        self.map.setdefault(key, set()).add(prefix)

    def prefix(self, state) -> int:
        found = self.map.get(pair_key(state), set())
        need(len(found) == 1, "endpoint does not match the reference unambiguously")
        return next(iter(found))


# -------------------------------------------------------------------- arms

def judge_readiness(record: Record, run_dir: Path, row: dict) -> dict:
    cell = record.cells.get(row.get("cellId"))
    need(cell is not None and row.get("kind") == "readiness", "readiness document absent")
    need(row.get("openName") == arms.open_name(record.browser, "readiness", None)
         and row.get("fixture") == arms.READINESS["fixture"], "readiness document is not the declared copy")
    record.opened(row, cell)
    setup = record.setup(cell, arms.READINESS["setup"])
    w = record.window(cell)
    keys = w["keydowns"]
    need(len(keys) == 1 and keys[0].get("key") == arms.READINESS["key"], "actual readiness key absent")
    typed = [i for i in w["inputs"] if i["type"] == "beforeinput" and i.get("inputType") == "insertText"
             and i.get("data") == arms.READINESS["key"]]
    need(len(typed) == 1 and typed[0]["seq"] > keys[0]["seq"], "actual readiness beforeinput absent")
    mutations = [r for r in record.product_requests(cell, w["lo"], w["hi"])
                 if r["message"].get("operation") == "insertText"]
    need(len(mutations) == 1 and mutations[0]["seq"] > typed[0]["seq"], "readiness wire mutation absent/extra")
    payload = mutations[0]["message"].get("payload") or {}
    need(payload.get("documentHandle") == cell["documentHandle"] and payload.get("text") == arms.READINESS["key"],
         "readiness wire mutation differs")
    terminal = record.replies.get(rkey(mutations[0]))
    need(terminal is not None and terminal["message"].get("ok") is True, "readiness mutation refused")
    admitted = [a for a in record.product_admissions(cell, w["lo"], w["hi"])
                if a.get("method") == "commitText" and a.get("text") == arms.READINESS["key"]]
    need(len(admitted) == 1, "readiness input was not admitted through the product")
    final, _, _ = record.state(f"{cell['cellId']}-final-state", cell)
    need(type(final.get("revision")) is int and type(setup["before"].get("revision")) is int
         and final["revision"] > setup["before"]["revision"], "readiness revision did not progress")
    need(record.saved(run_dir, row, cell) == arms.READINESS["paragraphs"], "readiness save lacks the known mutation")
    return {"cellSeq": cell["seq"], "generation": cell["generation"]}


def link(admissions: list, requests: list) -> None:
    """Every admission has its own posted request (FIFO), and every request its own admission."""
    need(len(requests) <= len(admissions), "a wire request no admission owns")
    for admission, request in zip(admissions, requests):
        need(request["seq"] >= admission["seq"], "a request was posted before its admission")
    # Rejected before posting, or never settled: the admitted work has no wire witness.
    need(len(requests) == len(admissions), "an admitted extension or edit has no wire request")


def judge_sequence(record: Record, run_dir: Path, row: dict, arm: dict) -> dict:
    cell = record.cells.get(row["cellId"])
    need(cell is not None, "measured cell record absent")
    open_key = record.opened(row, cell)
    setup = record.setup(cell, arm["setup"])
    w = record.window(cell)
    expect = arm["expect"]
    first_key, second = arm["input"]["presses"][0][0], arm["input"]["presses"][1]
    keys = w["keydowns"]
    need([k.get("key") for k in keys] == [first_key, second[0]], "the two consecutive trusted keys are absent")
    need(keys[1].get("shiftKey") is True and keys[0].get("shiftKey") is False
         and not any(k.get(m) for k in keys for m in ("ctrlKey", "altKey", "metaKey", "repeat")),
         "trusted Shift+Right absent or wrong modifiers")
    input_type = "insertText" if expect["first"] == "text" else "deleteContentBackward"
    edits = [i for i in w["inputs"] if i["type"] == "beforeinput" and i.get("inputType") == input_type
             and i["seq"] > keys[0]["seq"]]
    need(len(edits) == 1, "the first key's trusted beforeinput is absent")
    admissions = record.product_admissions(cell, w["lo"], w["hi"])
    first_admissions = [a for a in admissions if admission_category(a) == expect["first"]]
    move_admissions = [a for a in admissions if str(a.get("action")).startswith("move-")]
    need(len(first_admissions) + len(move_admissions) == len(admissions), "foreign admissions in the sequence")
    need(first_admissions, "the first key was not admitted")
    need(move_admissions and move_admissions[0].get("inputSeq") == keys[1]["seq"],
         "the page did not admit the move during the trusted Shift+Right")
    requests = record.product_requests(cell, w["lo"], cell["endSeq"])
    firsts = [r for r in requests if request_category(r) == expect["first"]]
    moves = [r for r in requests if r["message"].get("operation") == "editorActionV2"
             and str((r["message"].get("payload") or {}).get("action")).startswith("move-")]
    link(first_admissions, firsts)
    link(move_admissions, moves)
    for request in firsts + moves:
        need((request["message"].get("payload") or {}).get("documentHandle") == cell["documentHandle"],
             "a measured request belongs to another document")
        terminal = record.replies.get(rkey(request)) or record.cancels.get(rkey(request))
        need(terminal is not None and terminal["seq"] < w["hi"], "a required terminal is absent")
    final, _, _ = record.state(f"{cell['cellId']}-final-state", cell)
    observed(final)
    final_text = record.text(f"{cell['cellId']}-final-text", cell)
    paragraphs = record.saved(run_dir, row, cell)
    return {"setupAnchor": setup["anchor"], "openRequest": list(open_key), "firsts": firsts, "moves": moves,
            "firstAdmissions": first_admissions, "moveAdmissions": move_admissions, "final": final,
            "finalText": final_text, "paragraphs": paragraphs,
            "terminals": [record.replies.get(rkey(r)) or record.cancels.get(rkey(r)) for r in firsts + moves]}


def decide_sequence(witness: dict, arm: dict) -> dict:
    expect = arm["expect"]
    contradict(len(witness["firstAdmissions"]) == 1 and len(witness["moveAdmissions"]) == 1,
               "a trusted key was admitted more than once")
    first, move = witness["firsts"][0], witness["moves"][0]
    payload = first["message"]["payload"]
    if expect["first"] == "text":
        contradict(payload.get("text") == expect["firstText"], "the inserted text differs")
    else:
        contradict(payload.get("action") == expect["firstAction"], "the delete action differs")
    mp = move["message"]["payload"]
    contradict(mp.get("action") == "move-character-right", "Shift+Right posted another move")
    contradict(mp.get("extendSelection") is True and witness["moveAdmissions"][0].get("extendSelection") is True,
               "public extension flag absent on the measured Shift+Right")
    contradict(first["seq"] < move["seq"], "wire order: the extension was posted before the first edit")
    contradict(all(t["message"].get("kind") == "response" and t["message"].get("ok") is True
                   for t in witness["terminals"]), "a measured request was refused or cancelled")
    contradict(witness["paragraphs"] == expect["paragraphs"], "saved content differs from the exact result")
    contradict(witness["finalText"] == expect["selectedText"], "final selection text differs")
    collapsed, anchor, moving = geometry(witness["final"])
    contradict(not collapsed, "final selection collapsed")
    contradict(anchor is not None, "the final caret is not an end of the selection")
    contradict(moving[1] == anchor[1] and moving[0] > anchor[0],
               "selection is not anchored before the extended character")
    first_terminal = witness["terminals"][0]
    return {"insertBeforeExtendTerminal": first_terminal["seq"] < move["seq"],
            "selectedText": witness["finalText"], "paragraphs": witness["paragraphs"]}


def attribute(admissions: list, downs: list) -> dict:
    """Each admission to its own trusted press: during that press's dispatch, or released later
    from an earlier press the page took without admitting (its retained repeat)."""
    by_seq = {d["seq"]: d for d in downs}
    direct: dict = {}
    retained = []
    unattributed = []
    for admission in admissions:
        if admission.get("inputSeq") is not None:
            if admission["inputSeq"] in by_seq:
                direct.setdefault(admission["inputSeq"], []).append(admission["id"])
            else:
                unattributed.append(admission["id"])
            continue
        candidates = [d for d in downs if d["seq"] < admission["seq"] and d.get("defaultPrevented") is True
                      and d.get("admissions") == [] and d["seq"] not in retained]
        if candidates:
            retained.append(candidates[0]["seq"])
        else:
            unattributed.append(admission["id"])
    return {"direct": direct, "released": retained, "unattributed": unattributed,
            "multiple": [seq for seq, ids in direct.items() if len(ids) > 1]}


def release_accounting(record: Record, cell: dict, w: dict, downs: list, moves: list, admissions: list,
                       reference: Reference) -> dict:
    """The S-12 release witness.  Raises NotEstablished; the one-second arm only records it."""
    ups = [i for i in w["inputs"] if i["type"] == "keyup" and i["seq"] > downs[-1]["seq"]
           and i.get("key") in ("ArrowRight", "Shift")]
    need(ups, "final physical-key release absent")
    release = ups[0]
    need(cell.get("dirtyAtArm") is False, "hold setup was not clean")
    early = [r for r in record.product_requests(cell, w["lo"], release["seq"])
             if r["message"].get("operation") in ("insertText", "save") or request_category(r) == "delete"]
    need(not early, "a dirty checkpoint or text/delete queue precedes the hold")
    first = [a for a in admissions if a.get("inputSeq") == downs[0]["seq"]]
    need(first and moves and moves[0]["seq"] < release["seq"], "initial nonrepeat was not posted before release")

    def ended_before(request):
        ends = [t for t in (record.replies.get(rkey(request)), record.cancels.get(rkey(request))) if t]
        return any(t["seq"] < release["seq"] for t in ends)
    # S-12's right-hand side: posted extension requests with no terminal/cancel at release, from the
    # raw Worker records only -- never a page counter, never held/queued admissions.
    pending = [r for r in moves if r["seq"] < release["seq"] and not ended_before(r)
               and request_category(r) == arms.EXTENSION]
    answered = [record.replies[rkey(r)] for r in moves if rkey(r) in record.replies
                and record.replies[rkey(r)]["seq"] < release["seq"]
                and record.replies[rkey(r)]["message"].get("ok") is True]
    answered.sort(key=lambda t: t["seq"])
    if answered:
        state = (answered[-1]["message"].get("result") or {}).get("state")
        release_prefix = reference.prefix(state)
    else:
        release_prefix = 0
    # A state cannot be ahead of the extensions answered by then: a post-release state moved into
    # the release slot is not attributable.  Behind (a stale terminal) is reported, not absorbed.
    need(release_prefix <= len(answered), "release state is ahead of the extensions answered by release")
    shots = [s for s in record.page["snapshots"] if s["inputSeq"] == release["seq"] and s["phase"] == "capture"]
    need(len(shots) == 1, "release-set record missing at the physical release")
    shot = shots[0]
    need(shot.get("latestExtensionTerminal") == (list(rkey(answered[-1])) if answered else None),
         "the recorded release state is not the latest at release")
    return {"release": release, "releasePrefix": release_prefix, "answeredAtRelease": len(answered),
            "releaseOrdinalMismatch": release_prefix != len(answered),
            "wirePending": [list(rkey(r)) for r in pending],
            "heldOrQueued": {"unposted": shot.get("unposted"), "pageRetained": shot.get("pageRetained")}}


def judge_hold(record: Record, run_dir: Path, row: dict, arm: dict, reference: Reference | None) -> dict:
    cell = record.cells.get(row["cellId"])
    need(cell is not None, "measured cell record absent")
    open_key = record.opened(row, cell)
    setup = record.setup(cell, arm["setup"])
    need(reference is not None, "same-browser single-step reference absent")
    need(reference.serial != cell["openSerial"], "a candidate cannot supply its own reference")
    need(reference.anchor == setup["anchor"], "reference layout/anchor differs from the cell's")
    w = record.window(cell)
    lo, hi = w["lo"], w["hi"]
    downs = w["keydowns"]
    need(downs and all(k.get("key") == "ArrowRight" for k in downs), "foreign or missing measured keys")
    need(len(downs) <= arm["expect"]["downs"], "more measured keydowns than the schedule sent")
    need(downs[0].get("repeat") is False, "initial nonrepeat press absent")
    need(any(k.get("repeat") is True for k in downs), "no actual repeat input")
    need(all(k.get("shiftKey") is True for k in downs), "trusted Shift absent on a measured press")
    admissions = record.product_admissions(cell, lo, hi)
    need(all(a.get("method") == "action" and a.get("action") == "move-character-right" for a in admissions),
         "foreign admissions in the hold")
    requests = record.product_requests(cell, lo, cell["endSeq"])
    moves = [r for r in requests if r["message"].get("operation") == "editorActionV2"]
    need(all(str((r["message"].get("payload") or {}).get("action")).startswith("move-") for r in moves),
         "foreign wire actions in the hold")
    link(admissions, moves)
    terminals = []
    for request in moves:
        terminal = record.replies.get(rkey(request)) or record.cancels.get(rkey(request))
        need(terminal is not None and terminal["seq"] < hi, "a required terminal is absent")
        terminals.append(terminal)
    for terminal in terminals:
        if terminal["message"].get("kind") == "response" and terminal["message"].get("ok") is True:
            observed((terminal["message"].get("result") or {}).get("state"))
    final, _, _ = record.state(f"{cell['cellId']}-final-state", cell)
    observed(final)
    final_text = record.text(f"{cell['cellId']}-final-text", cell)
    paragraphs = record.saved(run_dir, row, cell)
    need(len(admissions) <= reference.steps, "more admitted extensions than the reference covers")
    if arm["expect"]["releaseBound"]:
        release = release_accounting(record, cell, w, downs, moves, admissions, reference)
    else:
        # Recorded, not a gate: the one-second arm's own endpoint rule is judged regardless.
        try:
            release = release_accounting(record, cell, w, downs, moves, admissions, reference)
        except NotEstablished as error:
            release = {"notEstablished": str(error)}
    return {"setup": setup, "openRequest": list(open_key), "downs": downs, "moves": moves,
            "terminals": terminals, "admissions": admissions, "attribution": attribute(admissions, downs),
            "final": final, "finalText": final_text, "paragraphs": paragraphs, "release": release,
            "reference": reference, "cell": cell}


def paragraph_prefix(arm: dict, length: int) -> str:
    return arm["fixtureParagraphs"][0][:length]


def decide_hold(witness: dict, arm: dict) -> dict:
    for request in witness["moves"]:
        payload = request["message"]["payload"]
        contradict(payload.get("action") == "move-character-right" and payload.get("extendSelection") is True,
                   "public extension flag absent on a measured move")
    contradict(all(a.get("extendSelection") is True for a in witness["admissions"]),
               "the page admitted a plain move for Shift+Right")
    attribution = witness["attribution"]
    contradict(not attribution["unattributed"], "an extension was admitted without a trusted press of its own")
    contradict(not attribution["multiple"], "one trusted press was admitted more than once")
    ok = [t for t in witness["terminals"] if t["message"].get("kind") == "response" and t["message"].get("ok") is True]
    contradict(len(ok) == len(witness["terminals"]), "an admitted extension was refused or cancelled")
    reference = witness["reference"]
    for terminal in ok:
        _, anchor, _ = geometry(terminal["message"]["result"]["state"])
        contradict(anchor == reference.terminal_anchor, "the selection anchor moved")
    admitted = len(witness["admissions"])
    text = witness["finalText"]
    contradict(text == paragraph_prefix(arm, len(text)), "final selection is not a first-paragraph prefix")
    # The logical prefix, from the active selection text -- never a getState geometry compared
    # with a terminal geometry of the same position.
    final_prefix = len(text)
    collapsed, anchor, _ = geometry(witness["final"])
    contradict(not collapsed or final_prefix == 0, "final selection collapsed")
    contradict(anchor is not None, "the final caret is not an end of the selection")
    contradict(anchor == witness["setup"]["anchor"], "final selection anchor moved")
    # 9.3: each admitted Right extend advances the moving endpoint by one reference step.
    contradict(text == reference.texts[admitted],
               "endpoint differs from the single-step reference after the admitted extensions")
    contradict(witness["paragraphs"] == arm["fixtureParagraphs"], "the held Shift changed the document")
    before = witness["setup"]["before"].get("revision")
    contradict(witness["final"].get("revision") == before, "the held Shift changed the revision")
    release = witness["release"]
    growth = None
    if "notEstablished" not in release:
        growth = final_prefix - release["releasePrefix"]
    if arm["expect"]["releaseBound"]:
        bound = len(release["wirePending"])
        contradict(growth >= 0, "the selection shrank after release")
        contradict(growth <= bound, f"S-12: growth after release {growth} exceeds wire-pending extensions {bound}")
    downs = witness["downs"]
    first = downs[0]["at"]
    stale = sum(1 for n, t in enumerate(ok, 1)
                if reference.map.get(pair_key(t["message"]["result"]["state"])) != {n})
    return {"downs": len(downs), "repeats": sum(1 for d in downs if d.get("repeat") is True),
            "deliveredMs": [round(d["at"] - first, 1) for d in downs],
            "scheduledMs": arm["schedule"]["downsAtMs"], "scheduledReleaseMs": arm["schedule"]["releaseMs"],
            "admitted": admitted, "posted": len(witness["moves"]), "answeredOk": len(ok),
            "admittedVersusAnsweredMismatch": admitted != len(ok),
            "releasedRetained": len(attribution["released"]), "finalPrefix": final_prefix,
            "growthAfterRelease": growth, "releaseBoundApplies": arm["expect"]["releaseBound"],
            "release": {k: v for k, v in release.items() if k != "release"},
            "releaseDeliveredMs": (round(release["release"]["at"] - first, 1) if "release" in release else None),
            "completions": sorted({str(t["message"]["result"].get("completion")) for t in ok}),
            "terminalStatesNotAtTheirOrdinal": stale}


# -------------------------------------------------------------------- runs

def load_run(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    files = {}
    for name in ("identity.json", "table.json", "rows.json", "page.json"):
        need((run_dir / name).is_file(), f"run artifact {name} absent")
        files[name] = (run_dir / name).read_bytes()
    return {"dir": run_dir, "raw": files, "identity": json.loads(files["identity.json"]),
            "table": json.loads(files["table.json"]), "rows": json.loads(files["rows.json"]),
            "page": json.loads(files["page.json"]), "pageSha256": arms.digest(files["page.json"])}


def outcome(fn):
    try:
        return PASS, None, fn()
    except NotEstablished as error:
        return NE, str(error), None
    except ProductFailure as error:
        return FAIL, str(error), None
    except Exception as error:                        # noqa: BLE001 -- any other shape is a missing witness
        return NE, f"malformed evidence: {type(error).__name__}: {error}", None


def judge_run(run_dir, repo: Path = arms.PROJECT) -> dict:
    """One browser's twelve rows (and its readiness and reference).  Never raises."""
    try:
        return _judge_run(run_dir, repo)
    except Exception as error:                        # noqa: BLE001 -- recorded, the runner continues
        result = arms.not_established(f"reader exception: {type(error).__name__}: {error}")
        result.update(dir=str(run_dir), browser=None, readiness=None, reference=None)
        return result


def _judge_run(run_dir, repo: Path) -> dict:
    plan = arms.table()
    result = {"dir": str(run_dir), "browser": None, "rows": [], "readiness": None, "reference": None}

    def all_rows(why):
        result["rows"] = [{"arm": a["id"], "browser": result["browser"], "round": n, "outcome": NE, "why": why}
                          for a in plan for n in range(1, arms.ROUNDS + 1)]
        result["arms"] = summarize(result["rows"], plan)
        return result
    try:
        run = load_run(Path(run_dir))
        browser = run["rows"].get("browser")
        need(browser in arms.BROWSERS, "run browser undeclared")
        result["browser"] = browser
        result["pageSha256"] = run["pageSha256"]
        need(run["table"] == plan, "the run's four-arm table differs from the source table")
        record = Record(run["page"], browser, run["identity"], repo)
    except Exception as error:                        # noqa: BLE001
        return all_rows(f"run not readable as evidence: {type(error).__name__}: {error}")
    status, why, value = outcome(lambda: judge_readiness(record, run["dir"], run["rows"].get("readiness") or {}))
    result["readiness"] = {"outcome": status, "why": why}
    ready = value if status == PASS else None
    reference = None
    ref_row = run["rows"].get("reference")
    if ref_row:
        hold = next(a for a in plan if a["input"]["kind"] == "hold")
        status, why, reference = outcome(lambda: Reference(record, ref_row, hold["fixtureParagraphs"][0],
                                                          arms.reference_steps()))
        result["reference"] = {"outcome": status, "why": why}
    rows = run["rows"].get("rows") or []
    seen, opens, saves = set(), {}, set()
    for arm in plan:
        for rnd in range(1, arms.ROUNDS + 1):
            ident = arms.cell_id(browser, arm["id"], rnd)
            matches = [r for r in rows if r.get("cellId") == ident]
            entry = {"arm": arm["id"], "browser": browser, "round": rnd, "cellId": ident}
            result["rows"].append(entry)
            if len(matches) != 1:
                entry.update(outcome=NE, why="row absent or duplicated")
                continue
            row = matches[0]
            seen.add(ident)
            if (row.get("arm"), row.get("round"), row.get("browser"), row.get("kind")) != (arm["id"], rnd, browser, "measured") \
                    or row.get("openName") != arms.open_name(browser, arm["id"], rnd) \
                    or row.get("fixture") != arm["fixture"]:
                entry.update(outcome=NE, why="row is not the declared fresh cell")
                continue
            if ready is None:
                entry.update(outcome=NE, why="readiness not established on this worker/browser path")
                continue
            cell = record.cells.get(ident)
            if cell is None:
                entry.update(outcome=NE, why="measured cell record absent")
                continue
            if cell.get("seq", -1) <= ready["cellSeq"]:
                entry.update(outcome=NE, why="measured cell does not follow the readiness document")
                continue
            identity_key = (cell.get("openSerial"), cell.get("generation"), cell.get("documentHandle"))
            save_file = (row.get("save") or {}).get("file")
            if identity_key in opens.values() or (save_file is not None and save_file in saves):
                entry.update(outcome=NE, why="duplicate cell: a copied round is not a fresh cell")
                continue
            opens[ident] = identity_key
            saves.add(save_file)
            if arm["input"]["kind"] == "chain":
                status, why, value = outcome(lambda: decide_sequence(
                    judge_sequence(record, run["dir"], row, arm), arm))
            else:
                ref = reference if result["reference"] and result["reference"]["outcome"] == PASS else None
                status, why, value = outcome(lambda: decide_hold(
                    judge_hold(record, run["dir"], row, arm, ref), arm))
            entry.update(outcome=status, why=why, observed=value)
    extra = [r.get("cellId") for r in rows if r.get("cellId") not in seen]
    if extra:
        result["extraRows"] = extra
        for entry in result["rows"]:
            if entry["outcome"] == PASS:
                entry.update(outcome=NE, why=f"undeclared extra rows {extra}")
    result["arms"] = summarize(result["rows"], plan)
    return result


def summarize(rows: list[dict], plan: list[dict]) -> dict:
    out = {}
    for arm in plan:
        mine = [r for r in rows if r["arm"] == arm["id"]]
        outcomes = [r["outcome"] for r in mine]
        if FAIL in outcomes:
            verdict = FAIL
        elif outcomes and all(o == PASS for o in outcomes):
            verdict = PASS
        else:
            verdict = NE
        out[arm["id"]] = {"check": arm["check"], "outcome": verdict, "ok": verdict == PASS, "rows": len(mine),
                          "outcomes": outcomes}
    return out


def declared_population(runner_text: str) -> list[str]:
    """The runner's literal four-arm check ids, by the runner's own `declared_check_ids`."""
    from run_e2_c_product_path import declared_check_ids   # lazy: the runner imports this module
    return [cid for cid in declared_check_ids(runner_text) if cid.startswith(CHECK_PREFIX)]


def aggregate(run_dirs, runner_text: str | None = None, repo: Path = arms.PROJECT) -> dict:
    plan = arms.table()
    runs = [judge_run(d, repo) for d in run_dirs]
    problems = []
    if runner_text is not None:
        declared = declared_population(runner_text)
        if sorted(declared) != sorted(a["check"] for a in plan) or len(declared) != len(set(declared)):
            problems.append(f"runner literal check sites {declared} differ from the table")
    families = [r["browser"] for r in runs]
    if sorted(f for f in families if f) != sorted(arms.BROWSERS):
        problems.append(f"browser families {families}, both real families required once each")
    shas = [r.get("pageSha256") for r in runs if r.get("pageSha256")]
    if len(shas) != len(set(shas)):
        problems.append("duplicate page artifact across runs")
    rows = [row for r in runs for row in r["rows"]]
    keys = [(row["arm"], row["browser"], row["round"]) for row in rows]
    expected = set(arms.expected_rows())
    if len(keys) != len(set(keys)) or set(keys) != expected or len(keys) != 24:
        problems.append(f"row population differs: {len(keys)} rows, {len(set(keys))} distinct, 24 declared")
    verdict = summarize(rows, plan)
    if problems:
        for value in verdict.values():
            if value["outcome"] == PASS:
                value.update(outcome=NE, ok=False)
    return {"schema": 1, "rows": len(rows), "problems": problems, "arms": verdict,
            "runs": [{k: v for k, v in r.items()} for r in runs]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--runner", type=Path, default=RUNNER)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = aggregate(args.runs, args.runner.read_text(encoding="utf-8"))
    text = json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(json.dumps({k: v["outcome"] for k, v in result["arms"].items()} | {"problems": result["problems"]},
                     indent=2, ensure_ascii=False))
    return 0 if all(v["outcome"] == PASS for v in result["arms"].values()) and not result["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
