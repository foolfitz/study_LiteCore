#!/usr/bin/env python3
"""The four ABI6 product arms: fixed table, observer mirror and per-browser driver.

Source: handoff/WORKORDER-2026-10-26-v23-product-four-arms.md (authoritative), the protocol's
"Product readiness and fixed inputs", and diagnostic/9.3-product-readiness-retained-keys-protocol.md.

  ARMS / table()      the four-member executable table: bound fixture bytes (pins verified against
                      the bytes), public setup, the consecutive trusted input and the exact result.
                      N=3 per browser, two browser families: 24 rows.  Read as truth by the reader.
  observer_mirror()   the declared served mirror: e2-editor.html's module tag only, plus the two
                      observer files; the app, shell, SDK and frozen worker stay byte-identical.
  run_block()         what the product runner calls once per browser, before its terminal 096 block:
                      one readiness document, then per arm three fresh OPEN_BYTES opens, setup,
                      measured trusted input through tools/v21_input.py (CDP / WebDriver, never a
                      synthetic KeyboardEvent), settle, product Save via capture_save, raw bytes kept.

No browser runs from this module on import.  Nothing here decides PASS/FAIL: that is
tools/judge_v23_product_four_arms.py, from the raw artifacts this writes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from pathlib import Path

import v21_input as inputs
from odt_paragraphs import paragraph_texts_from_xml
from r7_support import evaluate

PROJECT = Path(__file__).resolve().parent.parent
WORKSPACE = PROJECT.parent
FIXTURE_DIR = (WORKSPACE / "findings" / "evidence" / "link-batch-v23" / "native"
               / "ordered-commands" / "fixtures")
OBSERVER_ENTRY = "v23-product-four-arms-observer.js"
OBSERVER_CORE = "v23-product-four-arms-observer-core.js"
HTML = "e2-editor.html"
APP_MODULE = "e2-editor-app.js"
APP_TAG = b'<script type="module" src="./e2-editor-app.js"></script>'
OBSERVER_TAG = b'<script type="module" src="./v23-product-four-arms-observer.js"></script>'
PROFILE_ARTIFACTS = ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")
BROWSERS = ("chrome", "firefox")
ROUNDS = 3
EXTENSION = "move:move-character-right:true"

# The exact fixture bindings of 9.3-product-readiness-retained-keys-protocol.md ("Exact existing
# fixture bindings").  Never regenerated: a mismatch is a refusal, not a re-pin.
FIXTURE_PINS = {
    "abcd.fodt": "488c9cc00b5f07b83a4bf572194b427869739b31ea8c28338009bacb39cbd4d0",
    "plain3.fodt": "89c52deeca555ac60fb8dea7801a3bdcc81884cb06398701cf84d8ac934aa97d",
    "long200.fodt": "7e00a7a8da02576f94c232bb455964e06a1e7f9301f41f6e76d256ba1d078d35",
}

# The four-member executable table.  `check` is the literal id at the runner's call site.
ARMS = (
    {"id": "insert-then-shift", "check": "v23-product-insert-then-shift",
     "fixture": "abcd.fodt",
     "setup": {"kind": "select", "query": "abcd", "start": 1, "end": 2, "selectedText": "b"},
     "input": {"kind": "chain", "presses": [["x", []], ["ArrowRight", ["shift"]]]},
     "expect": {"kind": "sequence", "first": "text", "firstText": "x",
                "paragraphs": ["axcd"], "selectedText": "c"}},
    {"id": "merge-then-shift", "check": "v23-product-merge-then-shift",
     "fixture": "plain3.fodt",
     "setup": {"kind": "caret", "query": "Bravo second paragraph"},
     "input": {"kind": "chain", "presses": [["Backspace", []], ["ArrowRight", ["shift"]]]},
     "expect": {"kind": "sequence", "first": "delete", "firstAction": "delete-backward",
                "paragraphs": ["Alpha first paragraphBravo second paragraph",
                               "Charlie third paragraph"], "selectedText": "B"}},
    {"id": "held-shift-one-second", "check": "v23-product-held-shift-one-second",
     "fixture": "long200.fodt",
     "setup": {"kind": "caret", "query": "Paragraph 001."},
     "input": {"kind": "hold", "key": "ArrowRight", "mods": ["shift"], "holdMs": 1000},
     "expect": {"kind": "hold", "downs": 18, "releaseMs": 995, "releaseBound": False}},
    {"id": "held-shift-two-seconds", "check": "v23-product-held-shift-two-seconds",
     "fixture": "long200.fodt",
     "setup": {"kind": "caret", "query": "Paragraph 001."},
     "input": {"kind": "hold", "key": "ArrowRight", "mods": ["shift"], "holdMs": 2000},
     "expect": {"kind": "hold", "downs": 52, "releaseMs": 2015, "releaseBound": True}},
)
READINESS = {"fixture": "abcd.fodt", "setup": {"kind": "caret", "query": "abcd"},
             "key": "Z", "paragraphs": ["Zabcd"]}
REFERENCE_FIXTURE = "long200.fodt"
REFERENCE_SETUP = {"kind": "caret", "query": "Paragraph 001."}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def fixture_bytes(name: str) -> bytes:
    if name not in FIXTURE_PINS:
        raise ValueError(f"fixture {name!r} is not bound by the 9.3 table")
    raw = (FIXTURE_DIR / name).read_bytes()
    if digest(raw) != FIXTURE_PINS[name]:
        raise ValueError(f"fixture {name} differs from its 9.3 pin")
    return raw


def fixture_paragraphs(name: str) -> list[str]:
    return paragraph_texts_from_xml(fixture_bytes(name))


def schedule(hold_ms: int) -> dict:
    """The existing v21_input.hold schedule (500 ms delay, 30 ms repeats), as inputs."""
    times = inputs._times(hold_ms)                      # noqa: SLF001 -- the driver's own schedule
    return {"downsAtMs": times, "releaseMs": times[-1] + inputs.HOLD_INTERVAL_MS // 2}


def table() -> list[dict]:
    """The executable table, every derived input checked against the bytes and the driver."""
    rows, checks, ids = [], set(), set()
    for arm in ARMS:
        if arm["id"] in ids or arm["check"] in checks:
            raise ValueError("duplicate arm or check id")
        ids.add(arm["id"])
        checks.add(arm["check"])
        texts = fixture_paragraphs(arm["fixture"])
        row = json.loads(json.dumps(arm))
        row["fixtureSha256"] = FIXTURE_PINS[arm["fixture"]]
        row["fixtureParagraphs"] = texts
        query = arm["setup"]["query"]
        if sum(text.count(query) for text in texts) != 1:
            raise ValueError(f"{arm['id']}: setup query is not unique in the fixture")
        if arm["input"]["kind"] == "hold":
            planned = schedule(arm["input"]["holdMs"])
            if (len(planned["downsAtMs"]) != arm["expect"]["downs"]
                    or planned["releaseMs"] != arm["expect"]["releaseMs"]):
                raise ValueError(f"{arm['id']}: the driver schedule differs from the protocol's")
            row["schedule"] = planned
            # 9.3: no scheduled extension may reach the first paragraph's boundary.
            if not (texts[0].startswith(query) and len(texts[0]) > arm["expect"]["downs"]):
                raise ValueError(f"{arm['id']}: first paragraph too short for the schedule")
        rows.append(row)
    if len(rows) != 4:
        raise ValueError("the four-arm table changed size")
    return rows


def reference_steps() -> int:
    """Single public extended Right steps for the hold reference: every possible down."""
    return max(arm["expect"]["downs"] for arm in ARMS if arm["input"]["kind"] == "hold")


def expected_rows() -> list[tuple[str, str, int]]:
    return [(arm["id"], browser, rnd) for arm in ARMS for browser in BROWSERS
            for rnd in range(1, ROUNDS + 1)]


def cell_id(browser: str, arm: str, rnd: int) -> str:
    return f"{browser}-{arm}-r{rnd}"


def open_name(browser: str, arm: str, rnd: int | None) -> str:
    # The Writer SDK's .odt alias for the unchanged FODT bytes (9.3, fixture table note).
    suffix = f"-r{rnd}" if rnd is not None else ""
    return f"v23-four-arms-{arm}{suffix}-{browser}.odt"


# --------------------------------------------------------------- observer mirror

def transform_html(original: bytes) -> bytes:
    if original.count(APP_TAG) != 1:
        raise ValueError("the product HTML no longer has exactly one app module tag")
    return original.replace(APP_TAG, OBSERVER_TAG)


def served_module(path: str) -> str:
    """Where a bundle path is served (the entrypoint lives at web/ in source, at the root served)."""
    return path.removeprefix("web/")


def profile_files(directory: Path) -> list[str]:
    """Every file the profile's manifest names (loader, wasm, worker, packs), plus the four pins."""
    names = set(PROFILE_ARTIFACTS)
    manifest_path = directory / "sdk-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        names.update(str(v).removeprefix("./") for v in (manifest.get("artifactFiles") or {}).values())
        for pack in manifest.get("resourcePacks") or []:
            names.update(str(pack.get(k)).removeprefix("./") for k in ("data", "metadata") if pack.get(k))
    return sorted(names)


def shell_graph(root: Path) -> dict:
    """The served copy of every module of the current shell bundle, beside its declared hash."""
    import build_e2_c_shell_bundle as bundle
    relative = Path(bundle.MANIFEST)
    raw = (PROJECT / relative).read_bytes()
    manifest = json.loads(raw)
    included = {row["path"]: row["sha256"] for row in manifest.get("included") or []}
    return {"bundle": relative.as_posix(), "bundleFileSha256": digest(raw),
            "bundleSha256": manifest.get("bundleSha256"), "entrypoint": manifest.get("entrypoint"),
            "declared": included,
            "served": {served_module(p): digest((root / served_module(p)).read_bytes())
                       if (root / served_module(p)).is_file() else None for p in included}}


def observer_mirror(root: Path, profile: str, candidate_page_sha256: str | None = None) \
        -> tuple[dict[str, bytes], dict]:
    """Overrides for the runner's build_mirror, and the identity they bind.

    Absent pieces are recorded as None, never guessed: the reader then says NOT_ESTABLISHED, and
    the runner's other checks are not stopped by an instrument that cannot bind.
    """
    original = (root / HTML).read_bytes()
    served_html = transform_html(original)
    entry = (PROJECT / "web" / OBSERVER_ENTRY).read_bytes()
    core = (PROJECT / "web" / OBSERVER_CORE).read_bytes()
    directory = root / "profiles" / profile
    manifest_path = directory / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    identity = {
        "installed": True,
        "mirror": "v23-product-four-arms-observer",
        "evidenceClass": "instrument-observation",
        "transformation": "e2-editor.html: the one module tag ./e2-editor-app.js becomes "
                          "./v23-product-four-arms-observer.js, which imports the unchanged app",
        "originalHtmlSha256": digest(original),
        "servedHtmlSha256": digest(served_html),
        "observerEntrySha256": digest(entry),
        "observerCoreSha256": digest(core),
        "productModuleSha256": digest((root / APP_MODULE).read_bytes()),
        "candidatePageSha256": candidate_page_sha256,
        "shell": shell_graph(root),
        "profile": profile,
        "abiVersion": (manifest.get("editorContract") or {}).get("abiVersion"),
        "profileArtifacts": {name: digest((directory / name).read_bytes()) if (directory / name).is_file()
                             else None for name in profile_files(directory)},
        "diagnosticOverrides": [],
    }
    return {HTML: served_html, OBSERVER_ENTRY: entry, OBSERVER_CORE: core}, identity


def served_paths(identity: dict) -> list[str]:
    """The whole served graph the page hashes at begin(): page, observer, shell bundle, profile."""
    profile = identity["profile"]
    return sorted({HTML, OBSERVER_ENTRY, OBSERVER_CORE, APP_MODULE,
                   *((identity.get("shell") or {}).get("served") or {}),
                   *(f"profiles/{profile}/{name}" for name in identity.get("profileArtifacts") or {})})


# ---------------------------------------------------------------------- driver

REFERENCE_CHUNK = 8
RESTORE_FIXTURE = "./e1-fixtures/list-contexts.odt"


class CellAbort(Exception):
    """A cell could not be completed; its raw record is kept and the reader says NE."""


def _control(session, expression: str):
    return evaluate(session, "window.__fourArmsControl." + expression)


def _bounded(session, predicate, limit_s: float, poll_s: float = 0.25):
    """Containment bound for an observation, never a product completion policy."""
    until = time.monotonic() + limit_s
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(poll_s)
    return None


def _open(session, hooks: dict, name: str, raw: bytes) -> dict:
    serial = evaluate(session, "window.__fourArms.opens.length") or 0
    dispatched = evaluate(session, hooks["open_bytes"]
                          .replace("ARG_B64", base64.b64encode(raw).decode("ascii"))
                          .replace("ARG_NAME", name))
    if dispatched != "dispatched":
        raise CellAbort(f"the product file input was not reachable: {dispatched!r}")
    status = _bounded(session, lambda: (lambda s: s if s.get("found") and s.get("done") else None)(
        _control(session, f"openStatus({json.dumps(name)}, {int(serial)})") or {}), 180)
    if not status or not status.get("ok"):
        raise CellAbort(f"the fresh open of {name} did not succeed: {status!r}")
    return status


def _settle(session, cell: str) -> dict:
    quiet_twice = {"last": None}

    def poll():
        value = _control(session, f"quiet({json.dumps(cell)})") or {}
        if not value.get("quiet"):
            quiet_twice["last"] = None
            return None
        if quiet_twice["last"] is None:
            quiet_twice["last"] = time.monotonic()
            return None
        return value if time.monotonic() - quiet_twice["last"] >= 0.3 else None
    return _bounded(session, poll, 60) or {"quiet": False, "reasons": ["containment bound"]}


def _save(session, hooks: dict, out: Path, cell: str) -> dict:
    index = evaluate(session, hooks["save_count"]) or 0
    if index < 0:
        return {"index": index, "captured": False, "why": "the save shim is not installed"}
    report = hooks["capture_save"](session, index)
    raw = evaluate(session, hooks["read_save"].replace("ARG_INDEX", str(index))) if report else None
    if not raw or not raw.get("b64"):
        return {"index": index, "captured": False}
    data = base64.b64decode(raw["b64"], validate=True)
    path = out / "saves" / f"{cell}.odt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"index": index, "captured": True, "file": path.relative_to(out).as_posix(),
            "sha256": digest(data), "bytes": len(data)}


def _measure(session, browser: str, row: dict, inputs_spec: dict) -> dict:
    driver = {"method": inputs_spec["kind"], "startedMonotonic": time.monotonic()}
    if inputs_spec["kind"] == "chain":
        presses = [(name, tuple(mods)) for name, mods in inputs_spec["presses"]]
        inputs.chain(session, browser, presses)
        driver["presses"] = inputs_spec["presses"]
    elif inputs_spec["kind"] == "hold":
        driver["scheduled"] = row["schedule"]
        driver["returned"] = inputs.hold(session, browser, inputs_spec["key"], tuple(inputs_spec["mods"]),
                                         inputs_spec["holdMs"], flagged=True)
    elif inputs_spec["kind"] == "key":
        inputs.key(session, browser, inputs_spec["key"])
        driver["presses"] = [[inputs_spec["key"], []]]
    driver["finishedMonotonic"] = time.monotonic()
    return driver


def _reference(session, cell: str, steps: int) -> None:
    """The single-step reference in bounded chunks, each its own short awaited execute."""
    for first in range(1, steps + 1, REFERENCE_CHUNK):
        last = min(first + REFERENCE_CHUNK - 1, steps)
        done = _control(session, f"reference({json.dumps(cell)}, {first}, {last})") or {}
        if not done.get("ok"):
            raise CellAbort(f"reference refused at steps {first}-{last}: {done!r}")


def _cell(session, browser, hooks, out, *, cell, kind, arm, rnd, fixture, setup, measure=None,
          reference=None) -> dict:
    record = {"cellId": cell, "kind": kind, "arm": arm, "round": rnd, "browser": browser,
              "fixture": fixture, "fixtureSha256": FIXTURE_PINS[fixture],
              "openName": open_name(browser, arm, rnd), "failures": []}
    try:
        record["open"] = _open(session, hooks, record["openName"], fixture_bytes(fixture))
        spec = {"cellId": cell, "kind": kind, "arm": arm, "round": rnd, "openName": record["openName"],
                "setup": setup}
        prepared = _control(session, f"prepare({json.dumps(spec)})") or {}
        if not prepared.get("ok"):
            raise CellAbort(f"setup refused: {prepared!r}")
        if reference is not None:
            _reference(session, cell, reference)
        else:
            armed = _control(session, f"arm({json.dumps(cell)})") or {}
            if not armed.get("ok"):
                raise CellAbort(f"arm refused: {armed!r}")
            record["driver"] = measure()
            record["settle"] = _settle(session, cell)
            finished = _control(session, f"finish({json.dumps(cell)})") or {}
            if not finished.get("ok"):
                raise CellAbort(f"final reads refused: {finished!r}")
            record["save"] = _save(session, hooks, out, cell)
    except Exception as error:                        # noqa: BLE001 -- kept, reader says NE
        record["failures"].append(f"{type(error).__name__}: {error}")
    finally:
        try:
            _control(session, f"closeCell({json.dumps(cell)}, {json.dumps(record.get('save'))})")
        except Exception as error:                    # noqa: BLE001
            record["failures"].append(f"closeCell: {type(error).__name__}: {error}")
    return record


def export_record(session) -> tuple[bytes, dict]:
    meta = evaluate(session, "window.__fourArmsControl.exportBegin()")
    parts = []
    for start in range(0, meta["length"], 65536):
        end = min(start + 65536, meta["length"])
        part = base64.b64decode(_control(session, f"exportChunk({start}, {end})"), validate=True)
        if len(part) != end - start:
            raise ValueError("observer export chunk truncated")
        parts.append(part)
    raw = b"".join(parts)
    if len(raw) != meta["length"] or digest(raw) != meta["sha256"]:
        raise ValueError("observer export hash/length mismatch")
    _control(session, "exportDone()")
    return raw, meta


def _write(out: Path, name: str, raw: bytes, summary: dict) -> None:
    try:
        (out / name).write_bytes(raw)
    except OSError as error:
        summary["failures"].append(f"write {name}: {type(error).__name__}: {error}")


def run_block(session, browser: str, hooks: dict, out: Path, identity: dict) -> dict:
    """One runner execution's four arms in one browser; raw artifacts under `out` (new).

    Never raises: every failure, including the table, the directory and the first writes, is
    kept in `failures` (or `refused`), and the reader then says NOT_ESTABLISHED.  The runner
    must reach its 096 block whatever happens here.
    """
    summary = {"schema": 1, "browser": browser, "artifactDir": str(out), "rows": [],
               "readiness": None, "reference": None, "failures": []}
    try:
        if out.exists():
            # Never overwrite, and never let the reader judge an earlier run's files as this one's.
            summary["refused"] = "the artifact directory already exists"
            return summary
        out.mkdir(parents=True)
    except Exception as error:                        # noqa: BLE001
        summary["refused"] = f"artifact directory unusable: {type(error).__name__}: {error}"
        return summary
    try:
        plan = table()
        (out / "identity.json").write_bytes(encoded(identity))
        (out / "table.json").write_bytes(encoded(plan))
        if evaluate(session, "Boolean(window.__fourArmsControl && window.__fourArms)") is not True:
            raise CellAbort("the declared observer is not installed on this page")
        config = {"profile": identity["profile"], "served": served_paths(identity)}
        begun = _control(session, f"begin({json.dumps(config)})") or {}
        if not begun.get("ok"):
            raise CellAbort(f"observer begin refused: {begun!r}")
        summary["readiness"] = _cell(
            session, browser, hooks, out, cell=f"{browser}-readiness", kind="readiness", arm="readiness",
            rnd=None, fixture=READINESS["fixture"], setup=READINESS["setup"],
            measure=lambda: _measure(session, browser, {}, {"kind": "key", "key": READINESS["key"]}))
        for row in plan:
            if row["input"]["kind"] == "hold" and summary["reference"] is None:
                summary["reference"] = _cell(
                    session, browser, hooks, out, cell=f"{browser}-reference", kind="reference",
                    arm="reference", rnd=None, fixture=REFERENCE_FIXTURE, setup=REFERENCE_SETUP,
                    reference=reference_steps())
            for rnd in range(1, ROUNDS + 1):
                summary["rows"].append(_cell(
                    session, browser, hooks, out, cell=cell_id(browser, row["id"], rnd), kind="measured",
                    arm=row["id"], rnd=rnd, fixture=row["fixture"], setup=row["setup"],
                    measure=lambda row=row: _measure(session, browser, row, row["input"])))
    except Exception as error:                        # noqa: BLE001 -- kept, reader says NE
        summary["failures"].append(f"{type(error).__name__}: {error}")
    finally:
        try:
            _control(session, "end()")
            raw, meta = export_record(session)
            _write(out, "page.json", raw, summary)
            summary["pageTransfer"] = meta
        except Exception as error:                    # noqa: BLE001
            summary["failures"].append(f"export: {type(error).__name__}: {error}")
        try:
            _write(out, "rows.json", encoded(summary), summary)
            summary["files"] = {path.relative_to(out).as_posix(): digest(path.read_bytes())
                                for path in sorted(out.rglob("*")) if path.is_file()}
        except Exception as error:                    # noqa: BLE001
            summary["failures"].append(f"listing: {type(error).__name__}: {error}")
    return summary


def restore_neutral(session, hooks: dict, attempts: int = 2, limit_s: float = 120) -> dict:
    """After the block: the product's own file input opens the neutral fixture and must be ready.

    The 096 block and every later check then start from a live document whatever the last cell
    left behind; a page that cannot get there is recorded, and the block's checks say NE.
    """
    tries = []
    for attempt in range(1, attempts + 1):
        name = f"v23-four-arms-restore-{attempt}.odt"
        entry = {"name": name}
        try:
            entry["dispatched"] = evaluate(session, hooks["open_file"].replace("ARG_URL", RESTORE_FIXTURE)
                                           .replace("ARG_NAME", name))
            state = _bounded(session, lambda: (lambda s: s if (s.get("doc") or "") == name
                                               and s.get("state") == "ready" else None)(
                evaluate(session, hooks["read_state"]) or {}), limit_s)
            entry["ready"] = state is not None
        except Exception as error:                    # noqa: BLE001
            entry["ready"] = False
            entry["error"] = f"{type(error).__name__}: {error}"
        tries.append(entry)
        if entry["ready"]:
            return {"ok": True, "attempts": tries}
    return {"ok": False, "attempts": tries}


def artifact_dir_for(out_report: str | None) -> Path | None:
    """`<report>.v23-four-arms/` beside the runner's report; None when the run writes no report."""
    if out_report:
        return Path(re.sub(r"\.json$", "", out_report) + ".v23-four-arms")
    return None


def not_established(why: str) -> dict:
    """The four arms' verdict when the block could not run or be read, in the reader's shape."""
    return {"rows": [], "arms": {arm["id"]: {"check": arm["check"], "outcome": "NOT_ESTABLISHED", "ok": False,
                                             "rows": 0, "outcomes": [], "why": why} for arm in ARMS}}


def with_restore(verdict: dict, restore: dict) -> dict:
    """A page that could not be brought back to a live neutral document makes the block NE."""
    if restore.get("ok"):
        return verdict
    why = "the page could not be restored to a live neutral document after the block"
    for value in verdict["arms"].values():
        if value["outcome"] == "PASS":
            value.update(outcome="NOT_ESTABLISHED", ok=False, why=why)
    return verdict


if __name__ == "__main__":
    print(json.dumps({"arms": [row["id"] for row in table()], "rows": len(expected_rows()),
                      "referenceSteps": reference_steps()}, indent=2))
