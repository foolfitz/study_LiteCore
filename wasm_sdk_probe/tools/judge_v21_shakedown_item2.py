#!/usr/bin/env python3
"""The judge of the v21 WASM shakedown, item 2 (paste as Markdown).

Arms: findings/evidence/link-batch-v21/shakedown/ARMS-item2.md (draft + rulings §9), spec §11.2, §12.2.
Population: findings/evidence/link-batch-v21/shakedown/item2/population.json.  Reads the reports of
run_v21_shakedown_item2.py and decides, per criterion and browser: PASS, FAIL or NOT_ESTABLISHED (NE).
A criterion passes only when every instance passes in every one of N = 3 rounds on both browsers
(§11.0); missing, NE or no reply is "not done".  Records (the task checkbox, DM-14's CORE_LOG) are
printed, never judged.  M11-autosave is a host arm: reported NOT RUN here, which is not a pass.

Refused outright (VERDICT NOT GIVEN): a smoke or development report (`"smoke": true`, `development`), a
served page other than --expect-page, an instrumented worker where the shipped one must be, a report
whose population or comparator is not the committed one, two reports for the same browser.

  judge_v21_shakedown_item2.py --dir DIR --expect-page SHA256     exit 0 only if every criterion PASSes
  judge_v21_shakedown_item2.py --self-test                         every red and non-vacuity case
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
POPULATION = REPO / "findings/evidence/link-batch-v21/shakedown/item2/population.json"
SHIPPED_WORKER = "0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350"
WASM = "db3408f55316bf67345258ce9f7cb58a1cb3777c9aabb9f7790bee69e1599f30"
EXPECT_PAGE = "3d5112161b23b060b2057a25bbbeb7cbc96628cde67e3e5c3c0dab92b435b5c5"
PASS, FAIL, NE = "PASS", "FAIL", "NOT_ESTABLISHED"
ROUNDS = 3
CRITERIA = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11")
NEEDS_CARET = "MARKDOWN_NEEDS_CARET"
UNKNOWN = "MUTATION_OUTCOME_UNKNOWN"
M9_CARET = [2004, 1694, 276]


class Cell:
    """One verdict being built: FAIL beats NE beats PASS; zero judged instances is NE."""

    def __init__(self):
        self.fails: list[str] = []
        self.nes: list[str] = []
        self.passed = 0

    def fail(self, why: str):
        self.fails.append(why)

    def ne(self, why: str):
        self.nes.append(why)

    def ok(self):
        self.passed += 1

    def verdict(self) -> str:
        if self.fails:
            return FAIL
        if self.nes or self.passed == 0:
            return NE
        return PASS

    def reasons(self) -> list[str]:
        if self.fails:
            return self.fails[:12]
        if self.nes:
            return self.nes[:12]
        return [] if self.passed else ["zero judged instances"]


def same(compare) -> bool | None:
    if not isinstance(compare, dict) or not compare.get("compared"):
        return None
    return bool(compare.get("same"))


def session_outcome(dialog: dict) -> dict:
    out = (dialog or {}).get("outcome") or {}
    return out.get("entry") or {} if out.get("kind") == "session" else {}


def dialog_error(dialog: dict) -> dict:
    entry = session_outcome(dialog)
    return entry.get("error") or {} if entry and not entry.get("ok") else {}


def requested(attempt: dict, op: str = "pasteMarkdown") -> bool:
    return any(r.get("op") == op for r in (attempt or {}).get("requests") or [])


def by_round(instances: list[dict], key) -> dict:
    out = {}
    for inst in instances or []:
        out.setdefault((inst.get("round"), key(inst)), []).append(inst)
    return out


# ------------------------------------------------------------------ criteria

def judge_m1(results: dict, pop: dict, rounds: int) -> tuple[Cell, Cell, Cell]:
    m1, m2, m10a = Cell(), Cell(), Cell()
    got = by_round((results.get("m1") or {}).get("instances"), lambda i: i.get("item"))
    if not got:
        for cell in (m1, m2, m10a):
            cell.ne("zero instances")
        return m1, m2, m10a
    for k in range(1, rounds + 1):
        for item in pop["M1"]:
            label = f"r{k} {item['path']}"
            found = got.get((k, item["path"]))
            if not found:
                m1.fail(f"{label}: missing")
                continue
            inst = found[-1]
            if inst.get("runnerError"):
                m1.ne(f"{label}: {inst['runnerError'][:120]}")
                continue
            dialog = inst.get("dialog") or {}
            if dialog.get("inputIntact") is not True:
                m1.ne(f"{label}: the clipboard did not carry the input intact (no SDK route for M1)")
                continue
            entry = session_outcome(dialog)
            if not entry.get("ok"):
                m1.fail(f"{label}: the paste did not complete: {(entry.get('error') or {}).get('code') or dialog.get('outcome')}")
                continue
            before, after = (inst.get("before") or {}).get("rev"), (inst.get("after") or {}).get("rev")
            if not (isinstance(before, int) and after == before + 1):
                m1.fail(f"{label}: engine revision {before} -> {after}")
                continue
            verdict = same(inst.get("compare"))
            if verdict is None:
                m1.ne(f"{label}: not compared: {(inst.get('compare') or {}).get('why')}")
            elif verdict:
                m1.ok()
            else:
                m1.fail(f"{label}: DIFFERENT {(inst.get('compare') or {}).get('firstDifference')}")
            if item["path"] == pop["M2"]["item"]:
                if "texts" not in inst:
                    m2.ne(f"r{k}: the M8 instance's texts were not recorded")
                elif inst.get("texts") == pop["M2"]["expectedTexts"]:
                    m2.ok()
                else:
                    m2.fail(f"r{k}: texts {inst.get('texts')} != {pop['M2']['expectedTexts']}")
            if inst.get("paperEventsBeforePaste"):
                m10a.ne(f"{label}: a paper event before the paste")
            else:
                m10a.ok()
    return m1, m2, m10a


def m3_instance(cell: Cell, label: str, inst: dict, item: dict, rnd_controls_ok: bool) -> None:
    attempt = inst.get("attempt") or {}
    route = inst.get("route")
    if inst.get("runnerError"):
        cell.ne(f"{label}: {inst['runnerError'][:120]}")
        return
    if not rnd_controls_ok:
        cell.ne(f"{label}: the round's positive control did not show the reader can see an undo action")
        return
    if route == "dialog":
        if attempt.get("inputIntact") is False and item["bytes"]:
            return                       # spec 12.2 (c): withdrawn; judged on R-sdk
        if (attempt.get("outcome") or {}).get("kind") != "session":
            cell.fail(f"{label}: no session outcome: {attempt.get('outcome')}")
            return
        error = dialog_error(attempt)
        if not error:
            cell.fail(f"{label}: the paste completed")
            return
        recovery = error.get("recovery")
    else:
        answer = attempt.get("answer") or {}
        if answer.get("ok") is True:
            cell.fail(f"{label}: the paste completed")
            return
        error = answer.get("error") or {}
        recovery = error.get("recoveryFor")
    if error.get("code") != item["expectedCode"]:
        cell.fail(f"{label}: code {error.get('code')} != {item['expectedCode']}")
        return
    if error.get("dispatched") is not False:
        cell.fail(f"{label}: dispatched {error.get('dispatched')}")
        return
    if recovery != "none":
        cell.fail(f"{label}: recovery {recovery}")
        return
    layer = item.get("layerOnDialogAndSdk")
    if layer == "sdk" and requested(attempt):
        cell.fail(f"{label}: the SDK should have refused, but a pasteMarkdown request reached the worker")
        return
    if layer == "engine" and not requested(attempt):
        cell.fail(f"{label}: the engine should have refused, but no pasteMarkdown request was posted")
        return
    if not (isinstance(inst.get("r0"), int) and inst.get("rMarker") == inst["r0"] + 1):
        cell.ne(f"{label}: the marker did not move the revision by one ({inst.get('r0')} -> {inst.get('rMarker')})")
        return
    if inst.get("rAfter") != inst.get("rMarker"):
        cell.fail(f"{label}: revision moved by the refusal ({inst.get('rMarker')} -> {inst.get('rAfter')})")
        return
    if same(inst.get("s1EqualsMarker")) is not True:
        cell.fail(f"{label}: content changed by the refusal: {(inst.get('s1EqualsMarker') or {}).get('firstDifference')}")
        return
    if same(inst.get("s2EqualsS0")) is not True:
        cell.fail(f"{label}: one Ctrl+Z did not take the marker away (an undo action was added?)")
        return
    cell.ok()


def judge_m3(results: dict, bytes_results: dict | None, pop: dict, rounds: int) -> Cell:
    cell = Cell()
    m3 = results.get("m3") or {}
    controls = {}
    for pc in m3.get("positiveControls") or []:
        ok = (not pc.get("runnerError") and same(pc.get("s2EqualsMarker")) is True
              and same(pc.get("s2EqualsS0")) is False)
        if pc.get("route") == "dialog":
            ok = ok and bool(session_outcome(pc.get("paste")).get("ok"))
        else:
            ok = ok and ((pc.get("paste") or {}).get("answer") or {}).get("ok") is True
        controls[(pc.get("round"), pc.get("route"))] = ok
    got = {(i.get("round"), i.get("route"), i.get("item")): i for i in m3.get("instances") or []}
    if not got and not (results.get("m3size") or {}).get("instances") and not (bytes_results or {}).get("instances"):
        cell.ne("zero instances")
        return cell
    for k in range(1, rounds + 1):
        for item in pop["M3"]["items"]:
            for route in item["routes"]:
                if route == "bytes":
                    continue
                inst = got.get((k, route, item["path"]))
                label = f"r{k} {route} {item['path']}"
                if inst is None:
                    cell.fail(f"{label}: missing")
                    continue
                m3_instance(cell, label, inst, item, controls.get((k, route), False))
    # Dialog cells withdrawn under 12.2 (c) must have their R-sdk cell judged.
    for (k, route, path), inst in got.items():
        if route == "dialog" and (inst.get("attempt") or {}).get("inputIntact") is False and (k, "sdk", path) not in got:
            cell.fail(f"r{k} {path}: dialog withdrawn but no R-sdk instance")
    # Size arms.
    sizes = {(i.get("round"), i.get("arm")): i for i in (results.get("m3size") or {}).get("instances") or []}
    limit = pop["M3"]["limitL"]
    for k in range(1, rounds + 1):
        for arm in pop["M3"]["sizeArms"]:
            inst = sizes.get((k, arm["arm"]))
            label = f"r{k} {arm['arm']}"
            if inst is None:
                cell.fail(f"{label}: missing")
                continue
            if inst.get("runnerError"):
                cell.ne(f"{label}: {inst['runnerError'][:120]}")
                continue
            attempt = inst.get("attempt") or {}
            if arm["route"] == "sdk":
                answer = attempt.get("answer") or {}
                error = answer.get("error") or {}
                if arm["refusingLayer"] is None:
                    ok = answer.get("ok") is True and requested(attempt)
                else:
                    details = error.get("details") or {}
                    ok = (answer.get("ok") is False and error.get("code") == "INVALID_ARGUMENT"
                          and details.get("limitBytes") == limit and details.get("utf8Bytes") == limit + 1
                          and error.get("dispatched") is False and not requested(attempt)
                          and inst.get("r1") == inst.get("r0"))
            else:
                response = attempt.get("response") or {}
                if arm["refusingLayer"] is None:
                    ok = response.get("ok") is True and attempt.get("posted") is True
                else:
                    ok = (response.get("ok") is False and response.get("code") == "INVALID_ARGUMENT"
                          and response.get("dispatched") is False and response.get("limitBytes") is None
                          and attempt.get("posted") is True and inst.get("r1") == inst.get("r0"))
            if ok:
                cell.ok()
            else:
                cell.fail(f"{label}: wrong layer or outcome: {json.dumps(attempt)[:200]}")
    # Raw-byte items (spec 12.2 (a)): only the engine's reply, from the carrier report.
    raw_items = [i for i in pop["M3"]["items"] if i["routes"] == ["bytes"]]
    if raw_items:
        if bytes_results is None:
            cell.ne("the raw-byte items: no carrier report")
        else:
            got_b = {(i.get("round"), i.get("item")): i for i in bytes_results.get("instances") or []}
            pcs = {p.get("round"): p for p in bytes_results.get("positiveControl") or []}
            for k in range(1, rounds + 1):
                pc = pcs.get(k) or {}
                pc_ok = ((pc.get("attempt") or {}).get("response") or {}).get("ok") is True
                for item in raw_items:
                    inst = got_b.get((k, item["path"]))
                    label = f"r{k} bytes {item['path']}"
                    if inst is None:
                        cell.fail(f"{label}: missing")
                        continue
                    if inst.get("runnerError") or not pc_ok:
                        cell.ne(f"{label}: {inst.get('runnerError') or 'the carrier positive control did not complete'}")
                        continue
                    response = (inst.get("attempt") or {}).get("response") or {}
                    if (response.get("ok") is False and response.get("code") == item["expectedCode"]
                            and response.get("dispatched") is False and inst.get("r1") == inst.get("r0")
                            and same(inst.get("s1EqualsS0")) is True):
                        cell.ok()
                    else:
                        cell.fail(f"{label}: {json.dumps(response)[:160]}, r {inst.get('r0')}->{inst.get('r1')}")
    return cell


def judge_m4(results: dict, pop: dict, rounds: int) -> Cell:
    cell = Cell()
    got = {(i.get("round"), i.get("id")): i for i in (results.get("m4") or {}).get("instances") or []}
    population_ids = {i["id"] for i in pop["M4"]["instances"]}
    corpus_sha = {i["path"]: i["sha256"] for i in pop["M1"]}
    if not got:
        cell.ne("zero instances")
        return cell
    for (k, ident) in got:
        if ident not in population_ids:
            cell.fail(f"r{k} {ident}: not in the population")
    for k in range(1, rounds + 1):
        for inst_spec in pop["M4"]["instances"]:
            label = f"r{k} {inst_spec['id']}"
            inst = got.get((k, inst_spec["id"]))
            if inst is None:
                cell.fail(f"{label}: missing")
                continue
            if inst.get("runnerError"):
                cell.ne(f"{label}: {inst['runnerError'][:120]}")
                continue
            if same(inst.get("loadEqualsNative")) is not True:
                cell.ne(f"{label}: the opened fixture does not equal the native round's (I-11 proof)")
                continue
            confirm = inst_spec["confirm"]
            if inst_spec["class"] == "range":
                if inst.get("selectionText") != confirm["selectionText"]:
                    cell.ne(f"{label}: selection {inst.get('selectionText')!r} != {confirm['selectionText']!r}")
                    continue
                dialog = inst.get("dialog") or {}
                if session_outcome(dialog).get("ok"):
                    cell.fail(f"{label}: a paste completed on a range")
                    continue
                if (dialog.get("outcome") or {}).get("kind") != "page-refusal" or requested(dialog):
                    cell.fail(f"{label}: the page did not refuse the range itself: {dialog.get('outcome')}")
                    continue
                if (dialog.get("readbackAfter") or {}).get("sha256") != corpus_sha.get(inst_spec["corpus"]):
                    cell.fail(f"{label}: the page's refusal did not keep the text (spec 12.2 (d))")
                    continue
                error = ((inst.get("sdk") or {}).get("answer") or {}).get("error") or {}
                if error.get("code") != NEEDS_CARET or error.get("dispatched") is not False:
                    cell.fail(f"{label}: R-sdk {error.get('code')} dispatched {error.get('dispatched')}")
                    continue
                if inst.get("r1") != inst.get("r0") or same(inst.get("s1EqualsR")) is not True:
                    cell.fail(f"{label}: the document changed on a refused range")
                    continue
                cell.ok()
                continue
            if "caret" in confirm:
                # Ruling S4 (shakedown README §1): a round-2 placement is confirmed by (i) the engine caret
                # equal to the native cursorAtPaste rectangle, or (ii) the after-paste document SAME as the
                # native after.fodt.gz of the arm (DM-11 A's rule; fonts move coordinates on WASM).  (ii)
                # needs an after-paste save, which only a collapsed instance has.
                caret = inst.get("caret") or {}
                got_caret = [caret.get("x"), caret.get("y"), caret.get("height")]
                want = [confirm["caret"][0], confirm["caret"][1], confirm["caret"][3]]
                by_document = inst_spec["class"] == "collapsed" and same(inst.get("afterEqualsNative")) is True
                if got_caret != want and not by_document:
                    second = ("is not SAME as native's" if same(inst.get("afterEqualsNative")) is False
                              else "was not compared with native's" if inst_spec["class"] == "collapsed"
                              else "cannot confirm a protected cell")
                    cell.ne(f"{label}: placement {got_caret} != native {want}, and the after-paste document {second}")
                    continue
            dialog = inst.get("dialog") or {}
            if inst_spec["class"] == "protected":
                error = dialog_error(dialog)
                if error.get("code") != UNKNOWN or error.get("recovery") != "rollback":
                    cell.fail(f"{label}: {error.get('code')} recovery {error.get('recovery')}")
                    continue
                if same(inst.get("sEqualsR")) is not True:
                    cell.fail(f"{label}: the document after the rollback differs from before")
                    continue
                cell.ok()
                continue
            if not session_outcome(dialog).get("ok"):
                cell.fail(f"{label}: the paste did not complete: {dialog_error(dialog).get('code')}")
                continue
            if "afterEqualsNative" in confirm and same(inst.get("afterEqualsNative")) is not True:
                cell.ne(f"{label}: placement not confirmed (after-paste differs from native)")
                continue
            if same(inst.get("s2EqualsR")) is not True:
                cell.fail(f"{label}: one Undo did not restore: {(inst.get('s2EqualsR') or {}).get('firstDifference')}")
                continue
            cell.ok()
    return cell


LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]"}
DEFAULT_PORT = {"http": 80, "https": 443, "ws": 80, "wss": 443}
LISTENERS = {"listener", "tarpit", "closer"}


def origin_key(origin: str) -> tuple:
    """"http://127.0.0.1:18765" -> ("loopback", 18765): the loopback names are one host, a missing port is
    the scheme's."""
    m = re.match(r"^(\w+)://(\[[^\]]+\]|[^/:?#]+)(?::(\d+))?", origin)
    if not m:
        raise ValueError(f"not an origin: {origin!r}")
    host = m.group(2).lower()
    return ("loopback" if host in LOOPBACK else host,
            int(m.group(3)) if m.group(3) else DEFAULT_PORT.get(m.group(1).lower()))


def target_hits(entries: list[dict], origins: list[str]) -> tuple[list[dict], list[dict]]:
    """Ruling S3: split one item window's non-mirror entries into requests or connection attempts to the item's
    targets (every scheme://host:port in its bytes, plus the target-port listeners) and everything else."""
    if not origins:
        return [], list(entries)       # no URL, no target: the cell is the refusal
    keys = {origin_key(o) for o in origins}
    hits, other = [], []
    for e in entries:
        host = str(e.get("host") or "").lower()
        if e.get("target") in LISTENERS or ("loopback" if host in LOOPBACK else host, e.get("port")) in keys:
            hits.append(e)
        else:
            other.append(e)
    return hits, other


def m5_control_crossed(rnd: dict) -> bool:
    second = rnd.get("secondControl") or {}
    return (any(e.get("port") == 18765 and str(e.get("path") or "").startswith("/m5-control") for e in second.get("proxy") or [])
            and any(str(e.get("path") or "").startswith("/m5-control") for e in second.get("listener") or []))


def judge_m5(results: dict | None, pop: dict, rounds: int) -> Cell:
    cell = Cell()
    cell.info = []
    if not results:
        cell.ne("no M5 report")
        return cell
    rounds_got = {r.get("round"): r for r in results.get("rounds") or []}
    for k in range(1, rounds + 1):
        rnd = rounds_got.get(k)
        if rnd is None:
            cell.fail(f"r{k}: missing")
            continue
        if not rnd.get("positiveControl"):
            cell.ne(f"r{k}: no probe.wasm GET in the proxy's log")
            continue
        if not m5_control_crossed(rnd):
            cell.ne(f"r{k}: the /m5-control request is not in both the proxy's log and the listener's")
            continue
        got = {(i.get("item"), i.get("route")): i for i in rnd.get("items") or []}
        for item in pop["M5"]:
            m3 = next(i for i in pop["M3"]["items"] if i["path"] == item["path"])
            for route in ("dialog", "sdk"):
                label = f"r{k} {route} {item['path']}"
                inst = got.get((item["path"], route))
                if inst is None:
                    cell.fail(f"{label}: missing")
                    continue
                if inst.get("runnerError"):
                    cell.ne(f"{label}: {inst['runnerError'][:120]}")
                    continue
                attempt = inst.get("attempt") or {}
                if route == "dialog" and attempt.get("inputIntact") is False:
                    continue
                hits, other = target_hits(inst.get("outsideMirror") or [], item.get("originsNamed") or [])
                cell.info += [{"round": k, "item": item["path"], "route": route, "window": inst.get("window"),
                               **{f: e.get(f) for f in ("host", "port", "method", "t")}} for e in other]
                if hits:
                    cell.fail(f"{label}: requests to the item's targets: {json.dumps(hits)[:200]}")
                    continue
                code = (dialog_error(attempt) if route == "dialog"
                        else ((attempt.get("answer") or {}).get("error") or {})).get("code")
                if code != m3["expectedCode"]:
                    cell.fail(f"{label}: not refused as M3 says ({code})")
                    continue
                cell.ok()
    return cell


def judge_m6(results: dict, rounds: int) -> Cell:
    cell = Cell()
    got = {i.get("round"): i for i in (results.get("m6") or {}).get("instances") or []}
    for k in range(1, rounds + 1):
        inst = got.get(k)
        if inst is None:
            cell.fail(f"r{k}: missing")
            continue
        if inst.get("runnerError"):
            cell.ne(f"r{k}: {inst['runnerError'][:120]}")
            continue
        if (inst.get("foreignCpu") or {}).get("ok") is False:
            cell.ne(f"r{k}: foreign CPU load")
            continue
        span = inst.get("busySpanMs")
        if isinstance(span, (int, float)) and span > 10000:
            # Busy longer than the bound, whatever ended it (smoke J1: the SDK gave up after 30 s busy, which
            # is no fast refusal).
            cell.fail(f"r{k}: busy for {span} ms (ended in {inst.get('busyEndState')}) > 10,000")
            continue
        if not session_outcome(inst.get("dialog")).get("ok"):
            cell.ne(f"r{k}: the paste did not complete ({dialog_error(inst.get('dialog')).get('code')}): a refusal is fast")
            continue
        busy = inst.get("busyToReadyMs")
        if busy is None:
            cell.ne(f"r{k}: no busy -> ready transition logged")
            continue
        if busy > 10000:
            cell.fail(f"r{k}: busy -> ready {busy} ms > 10,000")
            continue
        if same(inst.get("s2EqualsR")) is not True:
            cell.fail(f"r{k}: one Undo did not restore")
            continue
        cell.ok()
    return cell


def judge_m7(results: dict, rounds: int) -> Cell:
    cell = Cell()
    a = {i.get("round"): i for i in (results.get("m7a") or {}).get("instances") or []}
    b = {i.get("round"): i for i in (results.get("m7b") or {}).get("instances") or []}
    for k in range(1, rounds + 1):
        inst = a.get(k)
        if inst is None:
            cell.fail(f"r{k} m7a: missing")
        elif inst.get("runnerError") or not inst.get("payloadSurvived"):
            cell.ne(f"r{k} m7a: {inst.get('runnerError') or 'the paste payload did not survive'}")
        elif (inst.get("markOccurrences") == 1 and inst.get("isAnOdt") is True
              and isinstance(inst.get("revisionBefore"), int) and (inst.get("revisionAfter") or -1) > inst["revisionBefore"]):
            cell.ok()
        else:
            cell.fail(f"r{k} m7a: marker {inst.get('markOccurrences')} odt {inst.get('isAnOdt')}")
        inst = b.get(k)
        if inst is None:
            cell.fail(f"r{k} m7b: missing")
        elif inst.get("runnerError") or not inst.get("pasteEvents"):
            cell.ne(f"r{k} m7b: {inst.get('runnerError') or 'the trusted Ctrl+V produced no insertText'}")
        elif same(inst.get("compare")) is True:
            cell.ok()
        else:
            cell.fail(f"r{k} m7b: DIFFERENT from native text/plain: {(inst.get('compare') or {}).get('firstDifference')}")
    return cell


def judge_m8(v20: dict | None, v21: dict | None, rounds: int) -> Cell:
    cell = Cell()
    v20i = {i.get("round"): i for i in (v20 or {}).get("instances") or []}
    v21i = {i.get("round"): i for i in (v21 or {}).get("instances") or []}
    for k in range(1, rounds + 1):
        control = v21i.get(k) or {}
        control_ok = (not control.get("runnerError") and (control.get("button") or {}).get("hidden") is False
                      and ((control.get("worker") or {}).get("response") or {}).get("ok") is True)
        inst = v20i.get(k)
        if inst is None:
            cell.fail(f"r{k}: v20 missing")
            continue
        if not control_ok or inst.get("runnerError"):
            cell.ne(f"r{k}: {inst.get('runnerError') or 'the v21 positive control did not show the entry and a paste'}")
            continue
        sdk_error = ((inst.get("sdk") or {}).get("answer") or {}).get("error") or {}
        if (inst.get("button") or {}).get("hidden") is not True:
            cell.fail(f"r{k}: the entry is visible on v20")
        elif sdk_error.get("code") != "UNSUPPORTED_OPERATION" or any(r.get("op") == "pasteMarkdown" for r in inst.get("requestsAfterSdk") or []):
            cell.fail(f"r{k}: the SDK on v20 answered {sdk_error.get('code')}")
        elif ((inst.get("worker") or {}).get("response") or {}).get("ok") is not False:
            cell.fail(f"r{k}: v20's worker accepted pasteMarkdown")
        else:
            cell.ok()
    return cell


def judge_m9(results: dict, rounds: int) -> Cell:
    cell = Cell()
    m9 = results.get("m9") or {}
    for sub in ("clean", "dirty", "inject"):
        got = {i.get("round"): i for i in m9.get(sub) or []}
        pcs = {i.get("round"): i for i in m9.get("positiveControl") or []}
        for k in range(1, rounds + 1):
            label = f"r{k} {sub}"
            inst = got.get(k)
            if inst is None:
                cell.fail(f"{label}: missing")
                continue
            if inst.get("runnerError"):
                cell.ne(f"{label}: {inst['runnerError'][:120]}")
                continue
            if not session_outcome((pcs.get(k) or {}).get("dialog")).get("ok"):
                cell.ne(f"{label}: the positive control (a paste outside the section) did not complete")
                continue
            caret = inst.get("caret") or {}
            if [caret.get("x"), caret.get("y"), caret.get("height")] != M9_CARET:
                cell.ne(f"{label}: placement {caret} is not the section's native caret")
                continue
            error = dialog_error(inst.get("dialog"))
            if sub == "inject":
                responses = inst.get("saveResponses") or []
                if not responses or any(r.get("ok") for r in responses) or not any(r.get("rewritten") for r in inst.get("requests") or []):
                    cell.ne(f"{label}: the injection did not fire ({responses})")
                    continue
                if any(r.get("op") == "pasteMarkdown" for r in inst.get("requests") or []):
                    cell.fail(f"{label}: a pasteMarkdown request was sent over a failed checkpoint")
                    continue
                if (error.get("code") != "MARKDOWN_CHECKPOINT_FAILED" or error.get("dispatched") is not False
                        or error.get("recovery") != "none"):
                    cell.fail(f"{label}: {error.get('code')} dispatched {error.get('dispatched')} recovery {error.get('recovery')}")
                    continue
                if not isinstance(inst.get("r0"), int) or inst.get("rev") != inst["r0"]:
                    cell.fail(f"{label}: the engine revision moved ({inst.get('r0')} -> {inst.get('rev')})")
                    continue
                cell.ok()
                continue
            if error.get("code") != UNKNOWN or error.get("recovery") != "rollback" or error.get("dispatched") is not True:
                cell.fail(f"{label}: {error.get('code')} recovery {error.get('recovery')} dispatched {error.get('dispatched')}")
                continue
            if sub == "clean":
                if same(inst.get("sEqualsR")) is True:
                    cell.ok()
                else:
                    cell.fail(f"{label}: the document after the rollback differs")
                continue
            ops = [r.get("op") for r in inst.get("requestsToPaste") or []]
            if "save" not in ops or "pasteMarkdown" not in ops or ops.index("save") > ops.index("pasteMarkdown"):
                cell.fail(f"{label}: the work was not banked before the paste ({ops})")
                continue
            if inst.get("markerCount") != 1 or inst.get("m2Present"):
                cell.fail(f"{label}: marker {inst.get('markerCount')} M2 present {inst.get('m2Present')}")
                continue
            cell.ok()
    return cell


def judge_m10(results: dict, trace: dict | None, m10a: Cell, rounds: int, pop: dict) -> Cell:
    cell = Cell()
    cell.fails += m10a.fails
    cell.nes += m10a.nes
    cell.passed += m10a.passed
    m10 = results.get("m10") or {}
    pre = {(i.get("round"), i.get("target")): i for i in (trace or {}).get("m10Precondition") or []}
    for sub, target in (("b", "image"), ("c", "frame"), ("d", None)):
        got = {i.get("round"): i for i in m10.get(sub) or []}
        for k in range(1, rounds + 1):
            label = f"r{k} M10{sub}"
            inst = got.get(k)
            if inst is None:
                cell.fail(f"{label}: missing")
                continue
            if inst.get("runnerError"):
                cell.ne(f"{label}: {inst['runnerError'][:120]}")
                continue
            dialog = inst.get("dialog") or {}
            if target:
                p = pre.get((k, target)) or {}
                if not p.get("graphicSelection"):
                    cell.ne(f"{label}: the selection precondition is not established (no GRAPHIC_SELECTION)")
                    continue
                if session_outcome(dialog).get("ok"):
                    cell.fail(f"{label}: a paste completed with the {target} selected")
                    continue
                error = dialog_error(dialog)
                if error.get("code") != NEEDS_CARET or error.get("dispatched") is not False:
                    cell.fail(f"{label}: {error.get('code')} dispatched {error.get('dispatched')}")
                    continue
            else:
                if inst.get("selectionText") != "A1 text\tB1 text\n":
                    cell.ne(f"{label}: not the two-cell selection ({inst.get('selectionText')!r})")
                    continue
                if requested(dialog) or (dialog.get("outcome") or {}).get("kind") != "page-refusal":
                    cell.fail(f"{label}: the dialog sent the paste on a range")
                    continue
                if (dialog.get("readbackAfter") or {}).get("sha256") != pop["M3"]["positiveControl"]["sha256"]:
                    cell.fail(f"{label}: the page's refusal did not keep the text (spec 12.2 (d))")
                    continue
                error = ((inst.get("sdk") or {}).get("answer") or {}).get("error") or {}
                if error.get("code") != NEEDS_CARET or error.get("dispatched") is not False:
                    cell.fail(f"{label}: R-sdk {error.get('code')}")
                    continue
            if inst.get("r1") != inst.get("r0") or same(inst.get("sEqualsR")) is not True:
                cell.fail(f"{label}: the document changed")
                continue
            cell.ok()
    return cell


def judge_m11(results: dict, rounds: int) -> Cell:
    cell = Cell()
    m11 = results.get("m11") or {}
    dirty = {i.get("round"): i for i in m11.get("dirty") or []}
    cancel = {i.get("round"): i for i in m11.get("cancel") or []}
    for k in range(1, rounds + 1):
        inst = dirty.get(k)
        if inst is None:
            cell.fail(f"r{k} dirty: missing")
        elif inst.get("runnerError") or not session_outcome(inst.get("dialog")).get("ok"):
            cell.ne(f"r{k} dirty: {inst.get('runnerError') or 'the paste did not complete'}")
        elif (inst.get("before") or {}).get("dirty") is False and (inst.get("after") or {}).get("dirty") is True:
            cell.ok()
        else:
            cell.fail(f"r{k} dirty: {inst.get('before')} -> {inst.get('after')}")
        inst = cancel.get(k)
        if inst is None:
            cell.fail(f"r{k} cancel: missing")
            continue
        if inst.get("runnerError"):
            cell.ne(f"r{k} cancel: {inst['runnerError'][:120]}")
            continue
        control = [r.get("op") for r in inst.get("controlRequests") or []]
        if "insertText" not in control or inst.get("r2") != (inst.get("r1") or 0) + 1:
            cell.ne(f"r{k} cancel: the positive control (typing into the document) did not reach the engine")
            continue
        bad = []
        for ep in inst.get("episodes") or []:
            ops = [r.get("op") for r in ep.get("requests") or []]
            if (ep.get("dialogOpen") is not True or ep.get("dialogOpenAfter") is not False
                    or (ep.get("textareaAfter") or {}).get("utf16") != 0 or (ep.get("textareaBefore") or {}).get("utf16", 0) == 0
                    or any(op in ("insertText", "pasteMarkdown") or str(op).startswith("editorAction") for op in ops)
                    or ep.get("enqueueCount") != inst.get("e0")):
                bad.append(ep.get("how"))
        if len(inst.get("episodes") or []) != 2 or bad:
            cell.fail(f"r{k} cancel: {bad or 'episodes missing'}")
        elif inst.get("r1") != inst.get("r0") or same(inst.get("s1EqualsS0")) is not True:
            cell.fail(f"r{k} cancel: the document changed")
        else:
            cell.ok()
    return cell


# ------------------------------------------------------------------ reports

def refuse(report: dict, pop_sha: str, expect_page: str) -> list[str]:
    why = []
    if report.get("smoke"):
        why.append("a smoke report is never judged")
    if report.get("development"):
        why.append("a development report (--limit/--only) is never judged")
    if report.get("populationSha256") != pop_sha:
        why.append("the report's population is not the committed one")
    for page, ident in (report.get("identity") or {}).items():
        hashes = ident.get("profileHashes") or {}
        if page in ("main", "m6", "proxy", "bytes", "trace"):
            if ident.get("pageServedSha256") != expect_page:
                why.append(f"{page}: served page {str(ident.get('pageServedSha256'))[:16]} != {expect_page[:16]}")
            if hashes.get("probe.wasm") != WASM:
                why.append(f"{page}: wasm {str(hashes.get('probe.wasm'))[:16]}")
        if page in ("main", "m6", "proxy") and ident.get("instrumentedWorker"):
            why.append(f"{page}: an instrumented worker where the shipped one must be")
        if page in ("bytes", "trace") and not ident.get("instrumentedWorker"):
            why.append(f"{page}: the diagnostic page does not say instrumentedWorker")
    m5 = (report.get("results") or {}).get("m5")
    if m5 and m5.get("identity"):
        if m5["identity"].get("pageServedSha256") != expect_page or m5["identity"].get("instrumentedWorker"):
            why.append("m5: not the round's page and shipped worker")
    return why


def judge_report(report: dict, pop: dict, rounds: int = ROUNDS) -> dict:
    """Judged over the rounds the report says it ran, capped at N; fewer than N is never a PASS."""
    results = report.get("results") or {}
    ran = int(report.get("rounds") or 0)
    short = f"{ran} rounds < {rounds}" if ran < rounds else None
    rounds = min(ran, rounds)
    m1, m2, m10a = judge_m1(results, pop, rounds)
    cells = {
        "M1": m1, "M2": m2,
        "M3": judge_m3(results, results.get("m3bytes"), pop, rounds),
        "M4": judge_m4(results, pop, rounds),
        "M5": judge_m5(results.get("m5"), pop, rounds),
        "M6": judge_m6(results, rounds),
        "M7": judge_m7(results, rounds),
        "M8": judge_m8(results.get("m8-v20"), results.get("m8-main"), rounds),
        "M9": judge_m9(results, rounds),
        "M10": judge_m10(results, results.get("trace"), m10a, rounds, pop),
        "M11": judge_m11(results, rounds),
    }
    out = {}
    for name, cell in cells.items():
        verdict = cell.verdict()
        reasons = cell.reasons()
        if short and verdict == PASS:
            verdict, reasons = NE, [short]
        out[name] = {"verdict": verdict, "passed": cell.passed, "reasons": reasons}
        if getattr(cell, "info", None) is not None:
            out[name]["info"] = cell.info     # recorded, never a verdict (ruling S3)
    out["M11"]["autosave"] = "NOT RUN (host arm)"
    trace = results.get("trace") or {}
    out["records"] = {"coreLog": [i.get("coreLog") for i in trace.get("m6CoreLog") or []],
                      "taskCheckbox": [{k: i.get(k) for k in ("S1Checked", "S2Checked", "rBefore", "rAfter", "afterClick")}
                                       for i in (results.get("record") or {}).get("instances") or []]}
    return out


def judge_dir(directory: Path, expect_page: str, pop: dict, pop_sha: str) -> tuple[int, list[str]]:
    lines = []
    reports = sorted(p for p in directory.glob("report-*.json"))
    by_browser: dict[str, list] = {}
    for path in reports:
        report = json.loads(path.read_text(encoding="utf-8"))
        by_browser.setdefault(report.get("browser"), []).append((path, report))
    verdicts = {}
    for browser in ("chrome", "firefox"):
        found = by_browser.get(browser) or []
        if len(found) != 1:
            lines.append(f"{browser}: {len(found)} reports (exactly one required)")
            verdicts[browser] = None
            continue
        path, report = found[0]
        refused = refuse(report, pop_sha, expect_page)
        if refused:
            lines.append(f"{browser}: VERDICT NOT GIVEN: {refused}")
            verdicts[browser] = None
            continue
        verdicts[browser] = judge_report(report, pop)
        for name in CRITERIA:
            v = verdicts[browser][name]
            lines.append(f"{browser} {name}: {v['verdict']} ({v['passed']} passed){'' if v['verdict'] == PASS else ' ' + '; '.join(v['reasons'][:3])}")
        info = verdicts[browser]["M5"].get("info") or []
        hosts: dict[str, int] = {}
        for e in info:
            hosts[f"{e.get('host')}:{e.get('port')}"] = hosts.get(f"{e.get('host')}:{e.get('port')}", 0) + 1
        lines.append(f"{browser} M5 info (recorded, not judged; ruling S3): {len(info)} non-target requests in item "
                     f"windows{': ' + ', '.join(f'{h} x{n}' for h, n in sorted(hosts.items())) if hosts else ''}")
    ok = all(verdicts.get(b) and all(verdicts[b][n]["verdict"] == PASS for n in CRITERIA) for b in ("chrome", "firefox"))
    lines.append("VERDICT " + ("PASS" if ok else "NOT PASS"))
    return (0 if ok else 1), lines


# ------------------------------------------------------------------ self-test

def synthetic(pop: dict, rounds: int = ROUNDS, browser: str = "chrome") -> dict:
    """A report in which every instance passes: the base every red case mutates."""
    ident = {"pageServedSha256": EXPECT_PAGE, "profileHashes": {"probe.wasm": WASM, "sdk-worker.js": SHIPPED_WORKER},
             "instrumentedWorker": False}
    same_ = {"compared": True, "same": True, "signatureSame": True, "fingerprintSame": True, "firstDifference": None}
    diff_ = {"compared": True, "same": False, "signatureSame": False, "fingerprintSame": False, "firstDifference": "/x"}
    ok_dialog = lambda: {"inputIntact": True, "outcome": {"kind": "session", "entry": {"k": "paste", "ok": True, "revision": 1}},  # noqa: E731
                         "requests": [{"op": "pasteMarkdown"}]}

    def refused_dialog(code, recovery="none", dispatched=False, request=True):
        return {"inputIntact": True, "outcome": {"kind": "session", "entry": {"k": "paste", "ok": False, "error": {
            "code": code, "recovery": recovery, "dispatched": dispatched}}},
            "requests": [{"op": "pasteMarkdown"}] if request else []}
    page_refusal = {"inputIntact": True, "outcome": {"kind": "page-refusal", "message": {"hidden": False, "text": "請先取消選取"}},
                    "requests": []}
    res: dict = {}
    res["m1"] = {"instances": []}
    for k in range(1, rounds + 1):
        for item in pop["M1"]:
            inst = {"round": k, "item": item["path"], "dialog": ok_dialog(), "before": {"rev": 0}, "after": {"rev": 1},
                    "compare": dict(same_), "paperEventsBeforePaste": []}
            if item["path"] == pop["M2"]["item"]:
                inst["texts"] = list(pop["M2"]["expectedTexts"])
            res["m1"]["instances"].append(inst)
    res["m3"] = {"instances": [], "positiveControls": []}
    for k in range(1, rounds + 1):
        for route in ("dialog", "sdk"):
            paste = ok_dialog() if route == "dialog" else {"answer": {"ok": True}}
            res["m3"]["positiveControls"].append({"round": k, "route": route, "paste": paste,
                                                  "s2EqualsMarker": dict(same_), "s2EqualsS0": dict(diff_)})
            for item in pop["M3"]["items"]:
                if route not in item["routes"]:
                    continue
                layer_request = item["layerOnDialogAndSdk"] == "engine"
                if route == "dialog":
                    attempt = refused_dialog(item["expectedCode"], request=layer_request)
                else:
                    attempt = {"answer": {"ok": False, "error": {"code": item["expectedCode"], "dispatched": False,
                                                                  "recoveryFor": "none", "details": {}}},
                               "requests": [{"op": "pasteMarkdown"}] if layer_request else []}
                res["m3"]["instances"].append({"round": k, "route": route, "item": item["path"], "attempt": attempt,
                                               "r0": 0, "rMarker": 1, "rAfter": 1, "s1EqualsMarker": dict(same_),
                                               "s2EqualsS0": dict(same_)})
    limit = pop["M3"]["limitL"]
    res["m3size"] = {"instances": []}
    for k in range(1, rounds + 1):
        for arm in pop["M3"]["sizeArms"]:
            if arm["route"] == "sdk":
                attempt = ({"answer": {"ok": True}, "requests": [{"op": "pasteMarkdown"}]} if arm["refusingLayer"] is None else
                           {"answer": {"ok": False, "error": {"code": "INVALID_ARGUMENT", "dispatched": False,
                                                              "details": {"limitBytes": limit, "utf8Bytes": limit + 1}}},
                            "requests": []})
            else:
                attempt = ({"posted": True, "response": {"ok": True}} if arm["refusingLayer"] is None else
                           {"posted": True, "response": {"ok": False, "code": "INVALID_ARGUMENT", "dispatched": False,
                                                         "limitBytes": None}})
            res["m3size"]["instances"].append({"round": k, "arm": arm["arm"], "attempt": attempt, "r0": 0, "r1": 0})
    res["m3bytes"] = {"instances": [], "positiveControl": []}
    for k in range(1, rounds + 1):
        res["m3bytes"]["positiveControl"].append({"round": k, "attempt": {"response": {"ok": True}}})
        for item in pop["M3"]["items"]:
            if item["routes"] == ["bytes"]:
                res["m3bytes"]["instances"].append({"round": k, "item": item["path"], "r0": 0, "r1": 0,
                                                    "s1EqualsS0": dict(same_), "attempt": {"response": {
                                                        "ok": False, "code": item["expectedCode"], "dispatched": False}}})
    res["m4"] = {"instances": []}
    sha_of = {i["path"]: i["sha256"] for i in pop["M1"]}
    for k in range(1, rounds + 1):
        for spec in pop["M4"]["instances"]:
            inst = {"round": k, "id": spec["id"], "class": spec["class"], "loadEqualsNative": dict(same_)}
            confirm = spec["confirm"]
            if "caret" in confirm:
                inst["caret"] = {"x": confirm["caret"][0], "y": confirm["caret"][1], "height": confirm["caret"][3]}
            if spec["class"] == "range":
                kept = dict(copy.deepcopy(page_refusal), readbackAfter={"sha256": sha_of[spec["corpus"]]})
                inst.update({"selectionText": confirm["selectionText"], "dialog": kept,
                             "sdk": {"answer": {"ok": False, "error": {"code": NEEDS_CARET, "dispatched": False}}},
                             "r0": 0, "r1": 0, "s1EqualsR": dict(same_)})
            elif spec["class"] == "protected":
                inst.update({"dialog": refused_dialog(UNKNOWN, recovery="rollback", dispatched=True), "sEqualsR": dict(same_)})
            else:
                inst.update({"dialog": ok_dialog(), "s2EqualsR": dict(same_), "afterEqualsNative": dict(same_)})
            res["m4"]["instances"].append(inst)
    res["m5"] = {"identity": dict(ident), "rounds": []}
    for k in range(1, rounds + 1):
        items = []
        for item in pop["M5"]:
            m3 = next(i for i in pop["M3"]["items"] if i["path"] == item["path"])
            items.append({"item": item["path"], "route": "dialog", "outsideMirror": [], "window": [0.0, 2.0],
                          "attempt": refused_dialog(m3["expectedCode"])})
            items.append({"item": item["path"], "route": "sdk", "outsideMirror": [], "window": [0.0, 2.0],
                          "attempt": {"answer": {"ok": False, "error": {"code": m3["expectedCode"]}}}})
        res["m5"]["rounds"].append({"round": k, "positiveControl": {"method": "GET"}, "items": items, "secondControl": {
            "proxy": [{"method": "GET", "host": "127.0.0.1", "port": 18765, "path": "/m5-control"}],
            "listener": [{"target": "listener", "port": 18765, "method": "GET", "path": "/m5-control"}]}})
    res["m6"] = {"instances": [{"round": k, "foreignCpu": {"ok": True}, "dialog": ok_dialog(), "busyToReadyMs": 3000.0,
                                "busySpanMs": 3000.0, "busyEndState": "ready",
                                "s2EqualsR": dict(same_)} for k in range(1, rounds + 1)]}
    res["m7a"] = {"instances": [{"round": k, "payloadSurvived": True, "markOccurrences": 1, "isAnOdt": True,
                                 "revisionBefore": 0, "revisionAfter": 1} for k in range(1, rounds + 1)]}
    res["m7b"] = {"instances": [{"round": k, "pasteEvents": 1, "compare": dict(same_)} for k in range(1, rounds + 1)]}
    res["m8-main"] = {"instances": [{"round": k, "button": {"hidden": False}, "worker": {"response": {"ok": True}}}
                                    for k in range(1, rounds + 1)]}
    res["m8-v20"] = {"instances": [{"round": k, "button": {"hidden": True}, "requestsAfterSdk": [],
                                    "sdk": {"answer": {"ok": False, "error": {"code": "UNSUPPORTED_OPERATION"}}},
                                    "worker": {"response": {"ok": False, "code": "UNKNOWN_OPERATION"}}}
                                   for k in range(1, rounds + 1)]}
    caret = {"x": M9_CARET[0], "y": M9_CARET[1], "height": M9_CARET[2]}
    res["m9"] = {
        "positiveControl": [{"round": k, "dialog": ok_dialog()} for k in range(1, rounds + 1)],
        "clean": [{"round": k, "caret": dict(caret), "dialog": refused_dialog(UNKNOWN, "rollback", True),
                   "sEqualsR": dict(same_)} for k in range(1, rounds + 1)],
        "dirty": [{"round": k, "caret": dict(caret), "dialog": refused_dialog(UNKNOWN, "rollback", True),
                   "requestsToPaste": [{"op": "save"}, {"op": "pasteMarkdown"}], "markerCount": 1, "m2Present": False}
                  for k in range(1, rounds + 1)],
        "inject": [{"round": k, "caret": dict(caret), "r0": 9, "rev": 9,
                    "dialog": refused_dialog("MARKDOWN_CHECKPOINT_FAILED", "none", False, False),
                    "requests": [{"op": "save", "rewritten": True}], "saveResponses": [{"ok": False, "code": "INVALID_ARGUMENT"}]}
                   for k in range(1, rounds + 1)]}
    res["m10"] = {
        "b": [{"round": k, "dialog": refused_dialog(NEEDS_CARET), "r0": 0, "r1": 0, "sEqualsR": dict(same_)} for k in range(1, rounds + 1)],
        "c": [{"round": k, "dialog": refused_dialog(NEEDS_CARET), "r0": 0, "r1": 0, "sEqualsR": dict(same_)} for k in range(1, rounds + 1)],
        "d": [{"round": k, "selectionText": "A1 text\tB1 text\n",
               "dialog": dict(copy.deepcopy(page_refusal), readbackAfter={"sha256": pop["M3"]["positiveControl"]["sha256"]}),
               "sdk": {"answer": {"ok": False, "error": {"code": NEEDS_CARET, "dispatched": False}}},
               "r0": 0, "r1": 0, "sEqualsR": dict(same_)} for k in range(1, rounds + 1)]}
    res["trace"] = {"m10Precondition": [{"round": k, "target": t, "graphicSelection": 1}
                                        for k in range(1, rounds + 1) for t in ("image", "frame")],
                    "m6CoreLog": [{"round": k, "coreLog": 10000} for k in range(1, rounds + 1)]}
    ep = lambda how: {"how": how, "dialogOpen": True, "dialogOpenAfter": False, "textareaBefore": {"utf16": 8},  # noqa: E731
                      "textareaAfter": {"utf16": 0}, "requests": [], "enqueueCount": 3}
    res["m11"] = {"dirty": [{"round": k, "dialog": ok_dialog(), "before": {"dirty": False}, "after": {"dirty": True}}
                            for k in range(1, rounds + 1)],
                  "cancel": [{"round": k, "e0": 3, "r0": 0, "r1": 0, "r2": 1, "s1EqualsS0": dict(same_),
                              "controlRequests": [{"op": "insertText"}], "episodes": [ep("cancel"), ep("escape")]}
                             for k in range(1, rounds + 1)]}
    identity = {"main": dict(ident), "m6": dict(ident), "v20": {"pageServedSha256": "v20", "profileHashes": {}, "instrumentedWorker": False},
                "bytes": {**ident, "instrumentedWorker": True}, "trace": {**ident, "instrumentedWorker": True}}
    return {"browser": browser, "smoke": False, "development": None, "rounds": rounds, "counted": False,
            "populationSha256": hashlib.sha256(POPULATION.read_bytes()).hexdigest(), "identity": identity,
            "results": res}


def red_cases() -> list[tuple[str, str, str, callable]]:
    """(name, criterion, expected verdict, mutation): each must turn the criterion to that verdict."""
    def first(lst, pred=lambda i: True):
        return next(i for i in lst if pred(i))
    r = lambda rep: rep["results"]  # noqa: E731
    return [
        ("M1 signature changed", "M1", FAIL, lambda rep: first(r(rep)["m1"]["instances"]).update(
            compare={"compared": True, "same": False, "firstDifference": "/paragraphs[0]"})),
        ("M1 item missing", "M1", FAIL, lambda rep: r(rep)["m1"]["instances"].pop()),
        ("M1 encoding refusal", "M1", FAIL, lambda rep: first(r(rep)["m1"]["instances"]).update(
            dialog={"inputIntact": True, "outcome": {"kind": "session", "entry": {"ok": False, "error": {"code": "MARKDOWN_ENCODING_UNSUPPORTED"}}}})),
        ("M1 input mismatch everywhere", "M1", NE, lambda rep: [i["dialog"].update(inputIntact=False) for i in r(rep)["m1"]["instances"]]),
        ("M1 zero instances", "M1", NE, lambda rep: r(rep)["m1"].update(instances=[])),
        ("M2 mojibake", "M2", FAIL, lambda rep: first(r(rep)["m1"]["instances"], lambda i: "texts" in i).update(
            texts=["æ¨\x99é¡\x8c", "", "", "", "", ""])),
        ("M2 trailing paragraph missing", "M2", FAIL, lambda rep: first(r(rep)["m1"]["instances"], lambda i: "texts" in i)["texts"].pop()),
        ("M2 no M8 instance", "M2", NE, lambda rep: [i.pop("texts", None) for i in r(rep)["m1"]["instances"]]),
        ("M3 wrong code", "M3", FAIL, lambda rep: first(r(rep)["m3"]["instances"], lambda i: i["item"] == "round-2/S01-inline-http.md" and i["route"] == "sdk")["attempt"]["answer"]["error"].update(code="MARKDOWN_HTML_UNSUPPORTED")),
        ("M3 dispatched true", "M3", FAIL, lambda rep: first(r(rep)["m3"]["instances"], lambda i: i["route"] == "sdk")["attempt"]["answer"]["error"].update(dispatched=True)),
        ("M3 recovery rollback", "M3", FAIL, lambda rep: first(r(rep)["m3"]["instances"], lambda i: i["route"] == "dialog")["attempt"]["outcome"]["entry"]["error"].update(recovery="rollback")),
        ("M3 revision moved", "M3", FAIL, lambda rep: first(r(rep)["m3"]["instances"]).update(rAfter=2)),
        ("M3 content changed", "M3", FAIL, lambda rep: first(r(rep)["m3"]["instances"]).update(s1EqualsMarker={"compared": True, "same": False})),
        ("M3 undo action added (marker survives Ctrl+Z)", "M3", FAIL, lambda rep: first(r(rep)["m3"]["instances"]).update(s2EqualsS0={"compared": True, "same": False})),
        ("M3 SDK-L+1 reached the worker", "M3", FAIL, lambda rep: first(r(rep)["m3size"]["instances"], lambda i: i["arm"] == "SDK-L+1")["attempt"].update(requests=[{"op": "pasteMarkdown"}])),
        ("M3 ENG-65537 with limitBytes", "M3", FAIL, lambda rep: first(r(rep)["m3size"]["instances"], lambda i: i["arm"] == "ENG-65537")["attempt"]["response"].update(limitBytes=65536)),
        ("M3 ENG-65536 refused", "M3", FAIL, lambda rep: first(r(rep)["m3size"]["instances"], lambda i: i["arm"] == "ENG-65536")["attempt"].update(response={"ok": False, "code": "INVALID_ARGUMENT"})),
        ("M3 positive control did not complete", "M3", NE, lambda rep: first(r(rep)["m3"]["positiveControls"]).update(s2EqualsS0={"compared": True, "same": True})),
        ("M3 zero instances", "M3", NE, lambda rep: [r(rep)["m3"].update(instances=[]), r(rep)["m3size"].update(instances=[]), r(rep)["m3bytes"].update(instances=[])]),
        ("M3 raw-byte item completed", "M3", FAIL, lambda rep: first(r(rep)["m3bytes"]["instances"]).update(attempt={"response": {"ok": True}})),
        ("M4 bold dropped after Undo", "M4", FAIL, lambda rep: first(r(rep)["m4"]["instances"], lambda i: i["class"] == "collapsed").update(s2EqualsR={"compared": True, "same": False, "firstDifference": "flags"})),
        ("M4 placement not confirmed (caret off, after-paste DIFFERENT)", "M4", NE, lambda rep: first(r(rep)["m4"]["instances"], lambda i: "caret" in i and i["class"] == "collapsed").update(caret={"x": 1, "y": 1, "height": 1}, afterEqualsNative={"compared": True, "same": False})),
        ("M4 S4: round-2 caret 17 twips off, after-paste SAME as native (smoke ccplain)", "M4", PASS, lambda rep: first(r(rep)["m4"]["instances"], lambda i: i["id"] == "M4-T2-ccplain-M2").update(caret={"x": 2157, "y": 1694, "height": 276})),
        ("M4 S4: round-2 caret off and no after-paste comparison", "M4", NE, lambda rep: [i.pop("afterEqualsNative") for i in r(rep)["m4"]["instances"] if i["id"] == "M4-T2-ccplain-M2"] and first(r(rep)["m4"]["instances"], lambda i: i["id"] == "M4-T2-ccplain-M2").update(caret={"x": 2157, "y": 1694, "height": 276})),
        ("M4 S4: a protected cell's caret off is not rescued", "M4", NE, lambda rep: first(r(rep)["m4"]["instances"], lambda i: i["class"] == "protected").update(caret={"x": 1, "y": 1, "height": 1}, afterEqualsNative={"compared": True, "same": True})),
        ("M4 range selection differs", "M4", NE, lambda rep: first(r(rep)["m4"]["instances"], lambda i: i["class"] == "range").update(selectionText="Bet")),
        ("M4 range: the page's refusal lost the text", "M4", FAIL, lambda rep: first(r(rep)["m4"]["instances"], lambda i: i["class"] == "range")["dialog"].update(readbackAfter={"sha256": "0" * 64})),
        ("M4 range pasted", "M4", FAIL, lambda rep: first(r(rep)["m4"]["instances"], lambda i: i["class"] == "range").update(dialog={"outcome": {"kind": "session", "entry": {"ok": True}}})),
        ("M4 instance outside the population", "M4", FAIL, lambda rep: r(rep)["m4"]["instances"].append({"round": 1, "id": "M4-T2-input-M2", "class": "collapsed"})),
        ("M4 zero instances", "M4", NE, lambda rep: r(rep)["m4"].update(instances=[])),
        ("M5 GET to the target", "M5", FAIL, lambda rep: first(r(rep)["m5"]["rounds"][0]["items"], lambda i: i["item"] == "round-2/H4-inline-img-then-block.md").update(outsideMirror=[{"method": "GET", "host": "127.0.0.1", "port": 18765, "path": "/h4.png"}])),
        ("M5 WebSocket to port 9", "M5", FAIL, lambda rep: first(r(rep)["m5"]["rounds"][0]["items"], lambda i: i["item"] == "round-1/M11.md").update(outsideMirror=[{"method": "CONNECT", "host": "127.0.0.1", "port": 9}])),
        ("M5 a listener connection in a target item's window", "M5", FAIL, lambda rep: first(r(rep)["m5"]["rounds"][0]["items"], lambda i: i["item"] == "round-2/H4-inline-img-then-block.md").update(outsideMirror=[{"target": "listener", "port": 18765, "method": "GET", "path": "/h4.png"}])),
        ("M5 the target by its loopback alias (localhost:18768 asked as 127.0.0.1)", "M5", FAIL, lambda rep: first(r(rep)["m5"]["rounds"][0]["items"], lambda i: i["item"] == "round-2/S02-https-hostname.md").update(outsideMirror=[{"method": "CONNECT", "host": "127.0.0.1", "port": 18768}])),
        ("M5 S3: Chrome's own GCM in a target item's window (smoke)", "M5", PASS, lambda rep: first(r(rep)["m5"]["rounds"][0]["items"], lambda i: i["item"] == "round-2/H3-inline-html-img.md").update(outsideMirror=[{"method": "CONNECT", "host": "mtalk.google.com", "port": 5228}])),
        ("M5 S3: a no-URL item's cell is its refusal", "M5", PASS, lambda rep: first(r(rep)["m5"]["rounds"][0]["items"], lambda i: i["item"] == "m0/X08-angle-generic.md").update(outsideMirror=[{"method": "GET", "host": "127.0.0.1", "port": 18765, "path": "/x"}])),
        ("M5 S3: /m5-control not in the proxy's log", "M5", NE, lambda rep: r(rep)["m5"]["rounds"][0]["secondControl"].update(proxy=[])),
        ("M5 no probe.wasm in the proxy log", "M5", NE, lambda rep: r(rep)["m5"]["rounds"][0].update(positiveControl=None)),
        ("M5 empty log", "M5", NE, lambda rep: r(rep).pop("m5")),
        ("M5 item not refused", "M5", FAIL, lambda rep: first(r(rep)["m5"]["rounds"][0]["items"], lambda i: i["route"] == "sdk").update(attempt={"answer": {"ok": True}})),
        ("M6 10,001 ms", "M6", FAIL, lambda rep: first(r(rep)["m6"]["instances"]).update(busyToReadyMs=10001)),
        ("M6 the SDK gave up after 30 s busy", "M6", FAIL, lambda rep: first(r(rep)["m6"]["instances"]).update(
            busyToReadyMs=None, busySpanMs=30001.6, busyEndState="recoverable-error",
            dialog={"outcome": {"kind": "session", "entry": {"ok": False, "error": {"code": "TIMEOUT", "recovery": "rollback"}}}})),
        ("M6 Undo did not restore", "M6", FAIL, lambda rep: first(r(rep)["m6"]["instances"]).update(s2EqualsR={"compared": True, "same": False})),
        ("M6 refused by the SDK", "M6", NE, lambda rep: first(r(rep)["m6"]["instances"]).update(dialog={"outcome": {"kind": "session", "entry": {"ok": False, "error": {"code": "INVALID_ARGUMENT"}}}})),
        ("M6 no busy logged", "M6", NE, lambda rep: first(r(rep)["m6"]["instances"]).update(busyToReadyMs=None)),
        ("M6 foreign load", "M6", NE, lambda rep: first(r(rep)["m6"]["instances"]).update(foreignCpu={"ok": False})),
        ("M7 two markers", "M7", FAIL, lambda rep: first(r(rep)["m7a"]["instances"]).update(markOccurrences=2)),
        ("M7 C1 converted to a heading", "M7", FAIL, lambda rep: first(r(rep)["m7b"]["instances"]).update(compare={"compared": True, "same": False, "firstDifference": "Heading_20_1"})),
        ("M7 no paste event", "M7", NE, lambda rep: first(r(rep)["m7b"]["instances"]).update(pasteEvents=0)),
        ("M7 payload did not survive", "M7", NE, lambda rep: first(r(rep)["m7a"]["instances"]).update(payloadSurvived=False)),
        ("M8 entry visible on v20", "M8", FAIL, lambda rep: first(r(rep)["m8-v20"]["instances"]).update(button={"hidden": False})),
        ("M8 v20 worker accepted", "M8", FAIL, lambda rep: first(r(rep)["m8-v20"]["instances"]).update(worker={"response": {"ok": True}})),
        ("M8 no v21 positive control", "M8", NE, lambda rep: r(rep).pop("m8-main")),
        ("M9 clean document changed", "M9", FAIL, lambda rep: r(rep)["m9"]["clean"][0].update(sEqualsR={"compared": True, "same": False})),
        ("M9 clean outcome unknown but not dispatched", "M9", FAIL, lambda rep: r(rep)["m9"]["clean"][0]["dialog"]["outcome"]["entry"]["error"].update(dispatched=False)),
        ("M9 inject moved the revision", "M9", FAIL, lambda rep: r(rep)["m9"]["inject"][0].update(rev=10)),
        ("M9 dirty marker lost", "M9", FAIL, lambda rep: r(rep)["m9"]["dirty"][0].update(markerCount=0)),
        ("M9 dirty not banked", "M9", FAIL, lambda rep: r(rep)["m9"]["dirty"][0].update(requestsToPaste=[{"op": "pasteMarkdown"}])),
        ("M9 inject sent the paste", "M9", FAIL, lambda rep: r(rep)["m9"]["inject"][0]["requests"].append({"op": "pasteMarkdown"})),
        ("M9 inject did not fire", "M9", NE, lambda rep: r(rep)["m9"]["inject"][0].update(saveResponses=[{"ok": True}])),
        ("M9 placement mismatch", "M9", NE, lambda rep: [i.update(caret={"x": 1418, "y": 1418, "height": 276}) for s in ("clean", "dirty", "inject") for i in r(rep)["m9"][s]]),
        ("M10b pasted on an image", "M10", FAIL, lambda rep: r(rep)["m10"]["b"][0].update(dialog={"outcome": {"kind": "session", "entry": {"ok": True}}})),
        ("M10b precondition missing", "M10", NE, lambda rep: r(rep)["trace"].update(m10Precondition=[])),
        ("M10d dialog sent the paste", "M10", FAIL, lambda rep: r(rep)["m10"]["d"][0]["dialog"].update(requests=[{"op": "pasteMarkdown"}])),
        ("M10d: the page's refusal lost the text", "M10", FAIL, lambda rep: r(rep)["m10"]["d"][0]["dialog"].pop("readbackAfter")),
        ("M10a click before the paste", "M10", NE, lambda rep: first(r(rep)["m1"]["instances"]).update(paperEventsBeforePaste=[{"op": "editorPlaceCaretV2"}])),
        ("M11 dirty stayed false", "M11", FAIL, lambda rep: r(rep)["m11"]["dirty"][0].update(after={"dirty": False})),
        ("M11 insertText while the dialog was open", "M11", FAIL, lambda rep: r(rep)["m11"]["cancel"][0]["episodes"][0]["requests"].append({"op": "insertText"})),
        ("M11 positive control without a request", "M11", NE, lambda rep: r(rep)["m11"]["cancel"][0].update(controlRequests=[])),
    ]


def self_test(verbose: bool = True) -> int:
    pop = json.loads(POPULATION.read_text(encoding="utf-8"))
    pop_sha = hashlib.sha256(POPULATION.read_bytes()).hexdigest()
    problems = []
    base = judge_report(synthetic(pop), pop)
    for name in CRITERIA:
        if base[name]["verdict"] != PASS:
            problems.append(f"control: {name} is {base[name]['verdict']} on the all-pass report: {base[name]['reasons'][:2]}")
    for name, criterion, want, mutate in red_cases():
        report = synthetic(pop)
        mutate(report)
        got = judge_report(report, pop)
        if got[criterion]["verdict"] != want:
            problems.append(f"{name}: {criterion} is {got[criterion]['verdict']}, wanted {want}")
        others = [c for c in CRITERIA if c != criterion and got[c]["verdict"] != base[c]["verdict"]
                  and not (name.startswith("M10a") or name.startswith("M2") or name.startswith("M1"))]
        if others:
            problems.append(f"{name}: also moved {others}")
        if verbose:
            print(f"  red {'ok ' if got[criterion]['verdict'] == want else 'BAD'} {name}: {criterion} {got[criterion]['verdict']}")
    # Ruling S3: a non-target request is recorded in M5's info list, with its host and window.
    gcm = next(c for c in red_cases() if c[0].startswith("M5 S3: Chrome's own GCM"))
    report = synthetic(pop)
    gcm[3](report)
    info = judge_report(report, pop)["M5"].get("info") or []
    if [(e.get("host"), e.get("port"), e.get("window")) for e in info] != [("mtalk.google.com", 5228, [0.0, 2.0])]:
        problems.append(f"M5 info list: {info}")
    elif verbose:
        print("  info ok M5 non-target request recorded:", info)
    # Short reports and refusals.
    two = synthetic(pop, rounds=2)
    if judge_report(two, pop)["M1"]["verdict"] != NE:
        problems.append("two rounds judged as more than NE")
    refusal_cases = (("smoke", lambda rep: rep.update(smoke=True)),
                          ("development", lambda rep: rep.update(development={"limit": 2})),
                          ("page", lambda rep: rep["identity"]["main"].update(pageServedSha256="0" * 64)),
                          ("instrumented main", lambda rep: rep["identity"]["main"].update(instrumentedWorker=True)),
                          ("instrumented m6", lambda rep: rep["identity"]["m6"].update(instrumentedWorker=True)),
                          ("m6 page", lambda rep: rep["identity"]["m6"].update(pageServedSha256="0" * 64)),
                          ("trace not instrumented", lambda rep: rep["identity"]["trace"].update(instrumentedWorker=False)),
                          ("population", lambda rep: rep.update(populationSha256="0" * 64)))
    for label, mutate in refusal_cases:
        report = synthetic(pop)
        mutate(report)
        if not refuse(report, pop_sha, EXPECT_PAGE):
            problems.append(f"refusal {label}: not refused")
        elif verbose:
            print(f"  refused ok {label}")
    if refuse(synthetic(pop), pop_sha, EXPECT_PAGE):
        problems.append(f"the all-pass report is refused: {refuse(synthetic(pop), pop_sha, EXPECT_PAGE)}")
    for line in problems:
        print("PROBLEM", line)
    print(f"self-test: {len(red_cases())} red cases, {len(refusal_cases)} refusals, 1 short report, {len(problems)} problem(s)")
    return 0 if not problems else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path)
    ap.add_argument("--expect-page")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.dir or not args.expect_page:
        print("VERDICT NOT GIVEN: --dir and --expect-page are required")
        return 1
    pop = json.loads(POPULATION.read_text(encoding="utf-8"))
    code, lines = judge_dir(args.dir, args.expect_page, pop, hashlib.sha256(POPULATION.read_bytes()).hexdigest())
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
