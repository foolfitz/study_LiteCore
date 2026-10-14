#!/usr/bin/env python3
"""Judge a report of probe_held_into_refusal.py or probe_table_refusal.py against
finding 134's acceptance (SPEC-M3-held-key §14; ruling-1 condition 3) and
ruling-3 conditions 3 and 4 (finding 136, L-134-restore-flash; task 2026-10-13c).

Tool-closed over both probes: the probe is picked by report["probe"]; its arms
are read by `ast` from that probe's own ARMS (a tuple in the held probe; a dict
literal in the table probe, whose keys are the arms).  An arm the probe
declares with no rule here is a FAIL, and so is a required browser with fewer
rounds of an arm than the minimum, and a run of an arm the probe does not
declare.  Exit 0 only when every arm passes on every required browser and the
served and dist page are the one named.

Per round, every arm:
  one reopen     1 refusal, generations 1 -> 2, no limit notice;
  document kept  the server's paragraphs equal the original once the reader
                 has stripped the three marks (`zqx`, `kj`, `wvy`);
  mark counts    each mark exactly once where the arm types it, and absent
                 where it does not (`kjkjk` contains `kj`: a residue of it would
                 be stripped from the comparison, the count catches it).
Placement (booleans and indexes computed by the probe's reader, no text):
  start-press, start-hold   `wvy` in paragraph 0 only, at its start
  end-hold                  `wvy` in the last paragraph only, at its end, right
                            after `zqx` (`zqxwvy` closes the last paragraph)
  end-press-type            `kj` in the last paragraph only (S1); `zqx` in the last
                            paragraph only; `kjzqx` contiguous
  before-table-press-type   `kj` in paragraph 0 only (S1); `kjzqx` contiguous
  cell-press-type           `kj` in paragraph 1 (cell A1) only (S1); `kjzqx` contiguous
                            (with `kj` and `zqx` counted once each, contiguity puts
                            `zqx` in the same paragraph as `kj`)
  before-table-hold         `wvy` in paragraph 0 only, at its end
  cell-hold                 `wvy` in paragraph 1 (cell A1) only, at its end
  cell-start-hold           (ruling-3 addenda 4 and 6) positive control first:
                            the refusal stage the probe read from the page's
                            toast is `nothing-selected` (「這一下沒有取得可刪除的
                            內容…」; addendum 6 replaced addendum 4's
                            `anchor-mismatch`, measured 4/4 on aebef525) -- any
                            other stage FAILs as "measures that stage, not D";
                            then `wvy` in paragraph 1 only, at its start; `kjkjk`
                            fully gone (`kj` count 0, document otherwise original)
scrollTop (ruling-3 condition 4).  Samples: the probe's `stateBeforeKey`, then
every state entry of the log, in order.
  end-hold, end-press-type  every sample from the first `restart-required` to
                            the END of the log is >= 0.5 x the last sample
                            before that refusal (N1: until 2026-10-13 the
                            window stopped at the first 「已重新載入」 sample, and
                            an excursion after it went unjudged).  A sample
                            with 「已重新載入」 must still follow the refusal (a
                            reopen that never completes FAILs), and the last
                            sample before the refusal must be > 0: at 0 the
                            rule would hold for any page.
  start-press, start-hold   every sample is 0.
  table arms                exempt (the fixture fits one screen); the series is printed.
Rounds per required browser: 2 for start-hold, end-hold and cell-start-hold, 1 otherwise.

Review 1 (findings/evidence/136/review/review-1.md) S1 and N1, accepted in
ruling-3 addendum 4 (continued) and addendum 5; the witness per edit is in
findings/evidence/136/judge/README.md.

C (SPEC-M3-link-batch 10.5, 10.7; task 2026-10-14m, witness
findings/evidence/link-batch/host-0.2.20/).  On a profile that ships C, a
merge key whose barrier finds nothing selected completes
`verified-boundary-noop` instead of refusing and reopening: v19 refuses, v20
does not.  The five arms at a document or cell start/end (`start-press`,
`start-hold`, `end-hold`, `end-press-type`, `cell-start-hold`; the 10.7 list)
are then held to RULES_C instead of RULES:
  no reopen       0 refusals, generations ['1'], no limit notice, no reopen
                  toast (10.5: the page shows nothing and does not reopen);
  document kept, the mark counts and the placement rules: unchanged, they
                  mean the same thing under C;
  cell-start-hold the refusal stage read from the page is None and no reopen
                  toast was classified (a stage read = a refusal happened);
  scrollTop       start arms: every sample 0, as before.  End arms: no
                  refusal anchors a window, so from `stateBeforeKey` (> 0,
                  same guard) to the end of the log every sample is >= 0.5 x
                  the pre-key sample -- the same "never near the document
                  start" the v19 window asserted.
The other four table arms refuse on v20 as on v19 (`key-posted`,
`anchor-mismatch` are other exits) and keep RULES under both keyings.

THE KEYING is the one task 2026-10-14i set for the merge runner
(`run_merge_wasm_shakedown.boundary_noop_declared`): a profile declares C by
carrying, in its probe.wasm, the fragment the engine emits for that
completion (`probe_engine.cpp`, `finishSelectionBarrierBoundaryNoop`).  No
manifest field declares C, and a name is a convention.  These reports do not
record `wasmSha256`; they record the host engine's `buildId`
(`static.buildId`), which `package_m3_engine.py` defines as the first 16 hex
of the sha256 of the canonical JSON {path: sha256} of the packaged closure --
the page, the worker and the wasm.  So the judge resolves the buildId to the
engine package the host served (`wasm_sdk_probe/build/archive/
host-*-engine-<buildId>/`, or `--engine DIR`), recomputes the buildId from
that manifest, checks the manifest's page hash against the report's
`servedPage`, decompresses `files/<profile>/probe.wasm.gz`, checks its
sha256 against the manifest, and only then reads the fragment.  Fail-closed:
no package, or any mismatch, is a FAIL with nothing judged -- no bytes, no
expectation; a v19 profile judged under RULES_C is red (refusals 1 != 0), a
C profile judged under RULES is red (the witness), so a wrong keying in
either direction cannot pass.  The keying is printed (`engine ...`).

A field a report predates is a FAIL "... not recorded", never a pass.  One
exception, for the red case on table run-3 only: that run's reader put
`controlThenMark` under run["control"] (`control_read`, the same definition:
`kj` + `zqx` in one paragraph); it is read there when the server read lacks
it, and the printed source says so.

  judge_held_into_refusal.py REPORT --page SHA256 [--browsers chrome,firefox] [--engine DIR]
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PROBES = {
    "probe_held_into_refusal.py": HERE / "probe_held_into_refusal.py",
    "probe_table_refusal.py": HERE.parents[1] / "134" / "table" / "probe_table_refusal.py",
}
STATIC_KEYS = ("hostVersion", "hostCommit", "buildId", "servedPage", "distPage")
RELOADED = "已重新載入"
# Both reopen toasts (「…正在重新載入…」, 「…已重新載入…」) contain this; the table
# probe's `refusal_stage` classifies a toast as a reopen by the same substring.
REOPEN_TOAST = "重新載入"
MISSING = object()

# ------------------------------------------------------------------ keying (C)

# The byte fragment `finishSelectionBarrierBoundaryNoop` (probe_engine.cpp,
# behind OXSDK_E2_V20_LINK_BATCH) writes into its reply; the same constant as
# run_merge_wasm_shakedown.BOUNDARY_NOOP_FRAGMENT (task 2026-10-14i).  In
# v20's probe.wasm and in no earlier profile's; a string a binary emits cannot
# be a comment.
BOUNDARY_NOOP_FRAGMENT = b',"completion":"verified-boundary-noop"'
# Where package_m3_engine.py's output is archived, named by the buildId the
# reports record (ATTRIBUTION.md in each): the bytes the host served.
ARCHIVE = ROOT / "wasm_sdk_probe" / "build" / "archive"
ENGINE_SCHEMA = "litecore-engine/2"
PAGE_MODULE = "e2-editor-app.js"


def build_id(files: dict[str, dict[str, Any]]) -> str:
    """package_m3_engine.build_id, verbatim: the buildId is a function of the decoded files."""
    canonical = json.dumps({path: entry["sha256"] for path, entry in files.items()},
                           sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def engine_package(build: str | None, engine: Path | None) -> Path | dict[str, str]:
    if engine is not None:
        return engine
    if not build:
        return {"error": "static.buildId not recorded; the C expectation cannot be keyed"}
    hits = sorted(p for p in ARCHIVE.glob(f"host-*-engine-{build}") if (p / "MANIFEST.json").is_file())
    if len(hits) != 1:
        return {"error": f"buildId {build}: {len(hits)} engine packages under {ARCHIVE} "
                         f"({[h.name for h in hits]}); pass --engine DIR"}
    return hits[0]


def keying(report: dict[str, Any], engine: Path | None) -> dict[str, Any]:
    """Whether the engine the report ran through declares C, read from its own bytes.
    Returns {"error": ...} when that cannot be established -- the caller judges nothing then."""
    static = report.get("static") or {}
    build = static.get("buildId")
    package = engine_package(build, engine)
    if isinstance(package, dict):
        return package
    manifest_path = package / "MANIFEST.json"
    if not manifest_path.is_file():
        return {"error": f"{manifest_path} is not a file"}
    manifest = json.loads(manifest_path.read_text())
    files = manifest.get("files") or {}
    if manifest.get("schema") != ENGINE_SCHEMA:
        return {"error": f"{manifest_path}: schema {manifest.get('schema')!r} != {ENGINE_SCHEMA!r}"}
    if manifest.get("buildId") != build:
        return {"error": f"{manifest_path}: buildId {manifest.get('buildId')} != the report's {build}"}
    if build_id(files) != build:
        return {"error": f"{manifest_path}: its files hash to buildId {build_id(files)}, not {build}"}
    page = (files.get(PAGE_MODULE) or {}).get("sha256")
    if page != static.get("servedPage"):
        return {"error": f"{manifest_path}: page {page} != the report's servedPage {static.get('servedPage')}"}
    wasm_path = next((p for p in files if p.endswith("/probe.wasm")), None)
    if wasm_path is None:
        return {"error": f"{manifest_path}: no */probe.wasm among its files"}
    packed = package / "files" / (wasm_path + ".gz")
    if not packed.is_file():
        return {"error": f"{packed} is not a file; the declaration must be read from the bytes that ran"}
    raw = gzip.decompress(packed.read_bytes())
    sha = hashlib.sha256(raw).hexdigest()
    if sha != files[wasm_path]["sha256"]:
        return {"error": f"{packed}: sha256 {sha[:16]} != the manifest's {files[wasm_path]['sha256'][:16]}; "
                         "the declaration must be read from the bytes that ran"}
    declared = BOUNDARY_NOOP_FRAGMENT in raw
    return {"buildId": build, "package": str(package), "profile": (manifest.get("source") or {}).get("profile"),
            "wasm": wasm_path, "wasmSha256": sha, "declared": declared,
            "nothingSelectedExpects": "verified-boundary-noop" if declared else "refusal"}


def probe_arms(path: Path) -> tuple[str, ...]:
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "ARMS" for t in node.targets):
            value = ast.literal_eval(node.value)
            return tuple(value.keys()) if isinstance(value, dict) else tuple(value)
    raise SystemExit(f"ARMS not found in {path}")


def field(run: dict[str, Any], name: str) -> tuple[Any, str]:
    srv = run.get("server") or {}
    if name in srv:
        return srv[name], "server"
    if name == "controlThenMark" and name in (run.get("control") or {}):
        return run["control"][name], "run.control (table run-3 reader)"
    return MISSING, "not recorded"


def need(run: dict[str, Any], name: str, failed: list[str]) -> Any:
    value, _ = field(run, name)
    if value is MISSING:
        failed.append(f"{name} not recorded")
    return value


# ------------------------------------------------------------------ rules

def one_reopen(run: dict[str, Any]) -> list[str]:
    s = run["summary"]
    failed = []
    if s["refusals"] != 1:
        failed.append(f"refusals {s['refusals']} != 1")
    if s["generations"] != ["1", "2"]:
        failed.append(f"generations {s['generations']} != ['1', '2']")
    if s["limitSavedMs"] is not None or (run.get("limit") or {}).get("limit") is not None:
        failed.append(f"limit notice {(run.get('limit') or {}).get('limit')!r}")
    return failed


def document_kept(run: dict[str, Any]) -> list[str]:
    srv = run.get("server") or {}
    if srv.get("sameAsOriginal") is True:
        return []
    return [f"server differs after the reader stripped its marks: firstDiff {srv.get('firstDiffFromOriginal')} "
            f"charDelta {srv.get('charDelta')} paragraphs {srv.get('paragraphs')}/{srv.get('paragraphsOriginal')}"]


def counts(mark: int, control: int, after: int) -> Callable[[dict[str, Any]], list[str]]:
    def rule(run: dict[str, Any]) -> list[str]:
        failed: list[str] = []
        for name, want in (("marks", mark), ("controls", control), ("afters", after)):
            got = need(run, name, failed)
            if got is not MISSING and got != want:
                failed.append(f"{name} {got} != {want}")
        return failed
    return rule


def last_index(run: dict[str, Any]) -> int | None:
    paragraphs = (run.get("server") or {}).get("paragraphs")
    return paragraphs - 1 if isinstance(paragraphs, int) else None


def after_at(where: str, index: int | str) -> Callable[[dict[str, Any]], list[str]]:
    """`wvy` only in paragraph `index` ("last" = the last), at its start or end."""
    flag = {"start": "afterAtStart", "end": "afterAtEnd"}[where]

    def rule(run: dict[str, Any]) -> list[str]:
        failed: list[str] = []
        want = last_index(run) if index == "last" else index
        paragraphs, at = need(run, "afterParagraphs", failed), need(run, flag, failed)
        if paragraphs is not MISSING and paragraphs != [want]:
            failed.append(f"AFTER in paragraphs {paragraphs}, expected [{want}]")
        if at is not MISSING and at is not True:
            failed.append(f"AFTER not at the {where} of its paragraph ({flag} {at})")
        return failed
    return rule


def mark_then_after(run: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    value = need(run, "markThenAfter", failed)
    if value is not MISSING and value is not True:
        failed.append(f"MARK then AFTER not contiguous (markThenAfter {value})")
    return failed


def mark_at_end(run: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    paragraphs = need(run, "markParagraphs", failed)
    if paragraphs is not MISSING and paragraphs != [last_index(run)]:
        failed.append(f"mark in paragraphs {paragraphs}, last is {last_index(run)}")
    return failed


def control_at(index: int | str) -> Callable[[dict[str, Any]], list[str]]:
    """S1: `kj` only in paragraph `index` ("last" = the last), so contiguity is about that paragraph."""
    def rule(run: dict[str, Any]) -> list[str]:
        failed: list[str] = []
        want = last_index(run) if index == "last" else index
        paragraphs = need(run, "controlParagraphs", failed)
        if paragraphs is not MISSING and paragraphs != [want]:
            failed.append(f"CONTROL in paragraphs {paragraphs}, expected [{want}]")
        return failed
    return rule


def contiguous(run: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    value = need(run, "controlThenMark", failed)
    if value is not MISSING and value is not True:
        failed.append(f"CONTROL then MARK not contiguous (controlThenMark {value})")
    return failed


def samples(run: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    before = run.get("stateBeforeKey")
    if isinstance(before, dict):
        out.append({**before, "t": "beforeKey"})
    out += [e for e in run.get("log") or [] if e.get("what") == "state"]
    return out


def scroll_window(run: dict[str, Any]) -> dict[str, Any]:
    """From the first `restart-required` to the end of the log (N1); `close` is the first
    「已重新載入」 sample, required to exist but no longer the window's end."""
    ss = samples(run)
    first = next((k for k, e in enumerate(ss) if e.get("state") == "restart-required"), None)
    if first is None:
        return {"error": "no restart-required sample"}
    if first == 0:
        return {"error": "no sample before the refusal"}
    close = next((k for k in range(first, len(ss)) if RELOADED in (ss[k].get("toast") or "")), None)
    return {"pre": ss[first - 1].get("scroll"), "preAt": ss[first - 1].get("t"),
            "window": [e.get("scroll") for e in ss[first:]],
            "from": ss[first].get("t"), "reloadedAt": ss[close].get("t") if close is not None else None,
            "to": ss[-1].get("t"), "closed": close is not None}


def scroll_end(run: dict[str, Any]) -> list[str]:
    w = scroll_window(run)
    if "error" in w:
        return [f"scrollTop: {w['error']}"]
    pre, window = w["pre"], w["window"]
    if not w["closed"]:
        return [f"scrollTop: no sample with 「{RELOADED}」 after the refusal"]
    if not isinstance(pre, (int, float)) or pre <= 0:
        return [f"scrollTop: last sample before the refusal is {pre!r} (the rule needs the view away from the start)"]
    low = [s for s in window if not isinstance(s, (int, float)) or s < 0.5 * pre]
    if low:
        return [f"scrollTop: {len(low)} of {len(window)} samples from the refusal to the end of the log < 0.5 x {pre} "
                f"(lowest {min((s for s in low if isinstance(s, (int, float))), default=None)})"]
    return []


def scroll_start(run: dict[str, Any]) -> list[str]:
    ss = samples(run)
    if not ss:
        return ["scrollTop: no samples"]
    off = [e.get("scroll") for e in ss if e.get("scroll") != 0]
    return [f"scrollTop: {len(off)} of {len(ss)} samples not 0 ({sorted({str(s) for s in off})[:5]})"] if off else []


def stage_is(want: str) -> Callable[[dict[str, Any]], list[str]]:
    def rule(run: dict[str, Any]) -> list[str]:
        if "refusalStage" not in run:
            return ["refusalStage not recorded"]
        stage = (run["refusalStage"] or {}).get("stage")
        return [] if stage == want else [f"refusal stage {stage!r}: measures that stage, not D"]
    return rule


# ------------------------------------------------------------------ rules under C (10.5, 10.7)

def no_reopen(run: dict[str, Any]) -> list[str]:
    """C: the key completed as a verified no-op -- nothing refused, nothing reopened,
    nothing shown.  The limit clause is one_reopen's, unchanged."""
    s = run["summary"]
    failed = []
    if s["refusals"] != 0:
        failed.append(f"refusals {s['refusals']} != 0 (C: a verified no-op, not a refusal)")
    if s["generations"] != ["1"]:
        failed.append(f"generations {s['generations']} != ['1'] (C: no reopen)")
    if s["limitSavedMs"] is not None or (run.get("limit") or {}).get("limit") is not None:
        failed.append(f"limit notice {(run.get('limit') or {}).get('limit')!r}")
    reopen = [t for t in s.get("toasts") or [] if REOPEN_TOAST in t]
    if reopen:
        failed.append(f"reopen toast shown under C: {reopen[0]!r}")
    return failed


def stage_none(run: dict[str, Any]) -> list[str]:
    """cell-start-hold under C: the positive control inverts.  v19 read the refusal
    stage from the toast to show the arm measured D (`nothing-selected`) and not
    `anchor-mismatch`; under C that exit is the no-op and the others still refuse,
    so the control is that NO stage was read: a stage read means a refusal."""
    if "refusalStage" not in run:
        return ["refusalStage not recorded"]
    stage = run["refusalStage"] or {}
    if stage.get("stage") is not None or stage.get("stages"):
        return [f"refusal stage {stage.get('stage')!r} read (stages {stage.get('stages')}): a refusal, not C's no-op"]
    return []


def kept_window(run: dict[str, Any]) -> dict[str, Any]:
    """C's scroll window for the end arms: no refusal anchors it, so it is the whole
    log after `stateBeforeKey` (required: the probe's one sample before the key)."""
    ss = samples(run)
    if not ss or ss[0].get("t") != "beforeKey":
        return {"error": "no stateBeforeKey sample"}
    return {"pre": ss[0].get("scroll"), "window": [e.get("scroll") for e in ss[1:]],
            "from": ss[1].get("t") if len(ss) > 1 else None, "to": ss[-1].get("t")}


def scroll_kept(run: dict[str, Any]) -> list[str]:
    w = kept_window(run)
    if "error" in w:
        return [f"scrollTop: {w['error']}"]
    pre, window = w["pre"], w["window"]
    if not isinstance(pre, (int, float)) or pre <= 0:
        return [f"scrollTop: sample before the key is {pre!r} (the rule needs the view away from the start)"]
    if not window:
        return ["scrollTop: no sample after the key"]
    low = [s for s in window if not isinstance(s, (int, float)) or s < 0.5 * pre]
    if low:
        return [f"scrollTop: {len(low)} of {len(window)} samples from the key to the end of the log < 0.5 x {pre} "
                f"(lowest {min((s for s in low if isinstance(s, (int, float))), default=None)})"]
    return []


def all_of(*rules: Callable[[dict[str, Any]], list[str]]) -> Callable[[dict[str, Any]], list[str]]:
    return lambda run: [f for rule in rules for f in rule(run)]


RULES: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    # held probe
    "start-press": all_of(one_reopen, document_kept, counts(1, 0, 1), after_at("start", 0), scroll_start),
    "start-hold": all_of(one_reopen, document_kept, counts(1, 0, 1), after_at("start", 0), scroll_start),
    "end-hold": all_of(one_reopen, document_kept, counts(1, 0, 1), after_at("end", "last"), mark_then_after,
                       scroll_end),
    "end-press-type": all_of(one_reopen, document_kept, counts(1, 1, 0), control_at("last"), mark_at_end, contiguous,
                             scroll_end),
    # table probe (scrollTop exempt)
    "before-table-press-type": all_of(one_reopen, document_kept, counts(1, 1, 0), control_at(0), contiguous),
    "before-table-hold": all_of(one_reopen, document_kept, counts(0, 0, 1), after_at("end", 0)),
    "cell-press-type": all_of(one_reopen, document_kept, counts(1, 1, 0), control_at(1), contiguous),
    "cell-hold": all_of(one_reopen, document_kept, counts(0, 0, 1), after_at("end", 1)),
    "cell-start-hold": all_of(one_reopen, stage_is("nothing-selected"), document_kept, counts(0, 0, 1),
                              after_at("start", 1)),
}
MIN_ROUNDS = {"start-press": 1, "start-hold": 2, "end-hold": 2, "end-press-type": 1,
              "before-table-press-type": 1, "before-table-hold": 1, "cell-press-type": 1, "cell-hold": 1,
              "cell-start-hold": 2}
SCROLL = {"start-press": "start", "start-hold": "start", "end-hold": "end", "end-press-type": "end"}
# 10.7's list: the arms whose key meets a document or cell start/end with
# nothing selected.  Under C they are judged by these rules; every other arm
# keeps RULES.  The list is a mirror of 10.7, but it cannot pass wrongly: an
# arm listed here that still refuses is red on `no_reopen`, and an arm left
# out that completes as a no-op is red on `one_reopen` (both measured on
# host 0.2.20: the four other table arms still refuse).
RULES_C: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "start-press": all_of(no_reopen, document_kept, counts(1, 0, 1), after_at("start", 0), scroll_start),
    "start-hold": all_of(no_reopen, document_kept, counts(1, 0, 1), after_at("start", 0), scroll_start),
    "end-hold": all_of(no_reopen, document_kept, counts(1, 0, 1), after_at("end", "last"), mark_then_after,
                       scroll_kept),
    "end-press-type": all_of(no_reopen, document_kept, counts(1, 1, 0), control_at("last"), mark_at_end, contiguous,
                             scroll_kept),
    "cell-start-hold": all_of(no_reopen, stage_none, document_kept, counts(0, 0, 1), after_at("start", 1)),
}
assert set(RULES_C) <= set(RULES), "RULES_C names an arm RULES does not"


# ------------------------------------------------------------------ printing

def scroll_series(run: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    for e in samples(run):
        if "scroll" in e and (not out or out[-1] != e["scroll"]):
            out.append(e["scroll"])
    return out


def raw_lines(arm: str, run: dict[str, Any], declared: bool = False) -> list[str]:
    s, srv = run["summary"], run.get("server") or {}
    show = lambda name: (lambda v: "-" if v[0] is MISSING else f"{v[0]}" + (  # noqa: E731
        "" if v[1] == "server" else f" [{v[1]}]"))(field(run, name))
    lines = [
        f"    reopen   refusals {s['refusals']} gens {s['generations']} limit {(run.get('limit') or {}).get('limit')}",
        f"    server   same {srv.get('sameAsOriginal')} firstDiff {srv.get('firstDiffFromOriginal')} "
        f"charDelta {srv.get('charDelta')} paragraphs {srv.get('paragraphs')}/{srv.get('paragraphsOriginal')}",
        f"    counts   marks {show('marks')} controls {show('controls')} afters {show('afters')}",
        f"    where    mark {show('markParagraphs')} control {show('controlParagraphs')} after {show('afterParagraphs')}",
        f"    bools    controlThenMark {show('controlThenMark')} markThenAfter {show('markThenAfter')} "
        f"afterAtStart {show('afterAtStart')} afterAtEnd {show('afterAtEnd')}",
    ]
    if arm == "cell-start-hold":
        lines.append(f"    cell     refusalStage {run.get('refusalStage', '-')} cellStart {run.get('cellStart', '-')}")
    kind = SCROLL.get(arm)
    if kind == "end":
        w = kept_window(run) if declared else scroll_window(run)
        lines.append(f"    scroll   series {scroll_series(run)} | window {w}")
    else:
        lines.append(f"    scroll   series {scroll_series(run)}" + ("" if kind else " (exempt)"))
    return lines


def judge_report(report: dict[str, Any], page: str, browsers: str, declared: bool,
                 out: Callable[[str], None] = print) -> list[str]:
    """Every failure line of the report under one keying (`declared`: the engine
    carries C, so 10.7's arms take RULES_C).  main() reads the keying from the
    engine's bytes; a re-judge may pass it to show a red case.  Returns the
    failures; the verdict is printed and is `PASS` iff the list is empty."""
    failures: list[str] = []
    path = PROBES.get(report.get("probe"))
    if path is None:
        out(f"FAIL report['probe'] {report.get('probe')!r} is none of {sorted(PROBES)}")
        out("verdict FAIL (1)")
        return ["report['probe'] unknown"]
    arms = probe_arms(path)
    out(f"probe {report['probe']} arms {list(arms)}")
    out(f"expectation {'C (RULES_C on ' + str(sorted(RULES_C)) + ')' if declared else 'v19 (RULES, refusal and reopen)'}")

    static, after = report.get("static") or {}, report.get("staticAfter") or {}
    out(f"static {({k: static.get(k) for k in STATIC_KEYS})}")
    for key in ("servedPage", "distPage"):
        if static.get(key) != page:
            failures.append(f"static: {key} {static.get(key)} != {page}")
    if any(static.get(k) != after.get(k) for k in STATIC_KEYS):
        failures.append(f"static: staticAfter differs {[k for k in STATIC_KEYS if static.get(k) != after.get(k)]}")

    for run in report["runs"]:
        if run["arm"] not in arms:
            failures.append(f"{run['browser']} {run['arm']} r{run.get('round', 0)}: arm not in the probe's ARMS")
    for arm in arms:
        rule = (RULES_C if declared else {}).get(arm) or RULES.get(arm)
        if rule is None or arm not in MIN_ROUNDS:
            failures.append(f"{arm}: no rule for an arm the probe declares")
            continue
        for browser in browsers.split(","):
            runs = [r for r in report["runs"] if r["arm"] == arm and r["browser"] == browser]
            if len(runs) < MIN_ROUNDS[arm]:
                failures.append(f"{browser} {arm}: {len(runs)} rounds < {MIN_ROUNDS[arm]}")
            for run in runs:
                head = f"{browser} {arm} r{run.get('round', 0)}"
                if run.get("fatal"):
                    failures.append(f"{head}: fatal {run['fatal'].strip().splitlines()[-1]}")
                    out(f"{head} FAIL fatal")
                    continue
                failed = rule(run)
                out(f"{head} {'FAIL' if failed else 'PASS'}")
                for line in raw_lines(arm, run, declared and arm in RULES_C):
                    out(line)
                for f in failed:
                    out(f"    - {f}")
                failures.extend(f"{head}: {f}" for f in failed)
    for f in failures:
        out(f"FAIL {f}")
    out(f"verdict {'PASS' if not failures else f'FAIL ({len(failures)})'}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--page", required=True, help="sha256 the served and dist page must both be")
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--engine", type=Path, default=None,
                        help="the engine package (package_m3_engine.py's <app>/engine: MANIFEST.json + files/) the "
                             "report ran through; default: the archive entry named by the report's buildId")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())

    key = keying(report, args.engine)
    if "error" in key:
        print(f"FAIL engine: {key['error']}")
        print("verdict FAIL (1)")
        return 1
    print(f"engine buildId {key['buildId']} package {key['package']} profile {key['profile']} "
          f"wasm {key['wasm']} sha256 {key['wasmSha256'][:16]} declares C: {key['declared']} "
          f"(nothing-selected expects {key['nothingSelectedExpects']})")
    failures = judge_report(report, args.page, args.browsers, key["declared"])
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
