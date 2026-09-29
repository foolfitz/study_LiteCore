#!/usr/bin/env python3
"""Does the host's read-back stay within one PUT as the document grows?  A measurement, not a gate.

Criteria (committed before this file): findings/evidence/m3-same-second/readback-size/CRITERIA.md.
Host 0.2.2 reads the file back (GET + sha256) before every PUT; ruling D condition 6 admitted that
on median read-back <= median PUT, measured on the 9.5 KB fixture only.  Here: the fixture, then
generated ODTs of about 1/5/20/50 MB (the fixture's text plus seeded-noise PNGs, stored), each
opened from Files once and saved SAVES times through Ctrl+S, 2.5 s after the previous one settled.

  probe_m3_readback_size.py [--browsers chrome,firefox] [--sizes 0,1,5,20,50] [--saves 6]
  probe_m3_readback_size.py --self-test
  probe_m3_readback_size.py --analyse REPORT.json

Size 0 is the fixture itself.  Writes findings/evidence/m3-same-second/readback-size/<startedAt>.json.
"""

from __future__ import annotations

import argparse
import io
import json
import random
import re
import statistics
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_host_entry import (  # noqa: E402
    CTRL_S, clear_lock, conflict_copies, host_record, leave_and_watch, open_from_files, server_lock)
from check_m3_skeleton_open import DEFAULT_DDEV, FIXTURE, NAME, Instance, binding_fields, host_binding  # noqa: E402
from probe_m3_gate0_coep import EventChrome, firefox_profile, sha256_file, utc_now, wait_until  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-same-second" / "readback-size"
MIB = 1 << 20
# pressAt first, then the press: one array expression (Firefox's evaluate is `return <expr>;`).
PRESS_AT = ("[Date.now() - JSON.parse(document.documentElement.getAttribute('data-litecore')).started, "
            + CTRL_S.strip() + "]")
SAVES = """(() => { const v = document.documentElement.getAttribute('data-litecore');
  const s = v && JSON.parse(v).saves; return s ? [s.length, s.every(x => x.settled === true)] : [0, true]; })()"""
# The page loaded well over the default 250 entries; clear them so the saves' requests are kept.
RESET_TIMING = ("(() => { performance.clearResourceTimings(); performance.setResourceTimingBufferSize(5000);"
                " return performance.timeOrigin; })()")
RESOURCES = """(() => JSON.stringify(performance.getEntriesByType('resource')
  .filter(e => e.name.includes('/remote.php/dav/files/'))
  .map(e => ({ start: performance.timeOrigin + e.startTime, duration: e.duration,
               encodedBodySize: e.encodedBodySize, transferSize: e.transferSize }))))()"""


def make_fixture(mib: int, path: Path) -> Path:
    """The fixture plus ceil(mib/3) noise PNGs of ~3 MiB total each, stored, as-char in one text:p."""
    with zipfile.ZipFile(FIXTURE) as source:
        parts = {name: source.read(name) for name in source.namelist()}
    count = max(1, -(-mib // 3))
    side = int((mib * MIB / count / 3) ** 0.5)
    rng = random.Random(mib)
    frames, entries, pictures = [], [], {}
    from PIL import Image
    for i in range(count):
        buffer = io.BytesIO()
        Image.frombytes("RGB", (side, side), rng.randbytes(side * side * 3)).save(buffer, "PNG", compress_level=0)
        pictures[f"Pictures/noise{i}.png"] = buffer.getvalue()
        frames.append(f'<draw:frame draw:name="noise{i}" text:anchor-type="as-char" svg:width="3cm" svg:height="3cm">'
                      f'<draw:image xlink:href="Pictures/noise{i}.png" xlink:type="simple" xlink:show="embed"'
                      ' xlink:actuate="onLoad"/></draw:frame>')
        entries.append(f' <manifest:file-entry manifest:full-path="Pictures/noise{i}.png" manifest:media-type="image/png"/>\n')
    content = parts["content.xml"].decode().replace(
        "xmlns:office=", 'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
        'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:office=', 1)
    parts["content.xml"] = content.replace("</office:text>", "<text:p>" + "".join(frames) + "</text:p>\n</office:text>", 1).encode()
    parts["META-INF/manifest.xml"] = parts["META-INF/manifest.xml"].decode().replace(
        "</manifest:manifest>", "".join(entries) + "</manifest:manifest>").encode()
    with zipfile.ZipFile(path, "w") as out:
        out.writestr(zipfile.ZipInfo("mimetype"), parts.pop("mimetype"), zipfile.ZIP_STORED)
        for name, data in parts.items():
            out.writestr(name, data, zipfile.ZIP_DEFLATED)
        for name, data in pictures.items():
            out.writestr(name, data, zipfile.ZIP_STORED)
    return path


def upload(instance: Instance, source: Path) -> dict[str, Any]:
    status, _ = instance.dav("PUT", NAME, source.read_bytes(), {"Content-Type": "application/vnd.oasis.opendocument.text"})
    body = b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns"><d:prop><oc:fileid/></d:prop></d:propfind>'
    _, answer = instance.dav("PROPFIND", NAME, body, {"Depth": "0", "Content-Type": "application/xml"})
    fileid = re.search(rb"<oc:fileid>(\d+)</oc:fileid>", answer)
    return {"putStatus": status, "fileId": int(fileid.group(1)) if fileid else None,
            "sha256": sha256_file(source), "bytes": source.stat().st_size}


def run_arm(kind: str, instance: Instance, scratch: Path, fixture: Path, saves: int) -> dict[str, Any]:
    record: dict[str, Any] = {"browser": kind, "lockAtReset": server_lock(instance)}
    if record["lockAtReset"]["lock"] == "1" and record["lockAtReset"]["fileId"]:
        record["staleLockCleared"] = clear_lock(instance, record["lockAtReset"]["fileId"])
    record["reset"] = upload(instance, fixture)
    record["copiesBefore"] = conflict_copies(instance, remove=True)
    session = (EventChrome("cold") if kind == "chrome" else FirefoxSession("cold", profile_dir=firefox_profile(scratch / f"arm-{fixture.stem}")))
    record["version"] = session.version
    try:
        open_from_files(session, instance, record)
        wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                            " return v && JSON.parse(v).done; })()", 600)
        steps = host_record(session).get("steps") or []
        opened = next((s.get("state") or {} for s in steps if s.get("step") == "opened"), {})
        record["opened"] = opened.get("state") == "ready" and opened.get("doc") == NAME
        record["openedState"] = opened
        if not record["opened"]:
            return record
        if isinstance(session, EventChrome):
            # Network.requestWillBeSent carries the PUT's body: 12.8 MB for the 5 MiB document,
            # over the CDP client's 1 MiB frame limit (shakedown 2026-09-29T055204). The bytes
            # come from Resource Timing instead, so the events are not needed after the open.
            session.call("Network.disable")
            record["chromeNetworkEvents"] = "disabled after open"
        record["timeOrigin"] = evaluate(session, RESET_TIMING)
        record["presses"] = []
        for index in range(saves):
            record["presses"].append(evaluate(session, PRESS_AT))
            record.setdefault("settled", []).append(wait_until(
                session, f"(() => {{ const s = {SAVES.strip()}; return s[0] >= {index + 1} && s[1] && s; }})()", 300))
            time.sleep(2.5)
        record["host"] = host_record(session)
        record["resources"] = json.loads(evaluate(session, RESOURCES))
        _, body = instance.dav("GET", NAME)
        with zipfile.ZipFile(io.BytesIO(body)) as saved:
            record["serverAfter"] = {"bytes": len(body), "pictures": sum(n.startswith("Pictures/") for n in saved.namelist())}
        record["copiesAfter"] = conflict_copies(instance, remove=True)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            record["leave"] = leave_and_watch(session, instance)
        except Exception as error:  # noqa: BLE001
            record["leave"] = f"{type(error).__name__}: {error}"
        session.close()
    return record


def rows_of(record: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per save, from the host's record; the read-back's bytes from Resource Timing
    (the entry that started within 50 ms of the check, on the epoch clock)."""
    host = record.get("host") or {}
    started, resources = host.get("started"), record.get("resources") or []
    rows = []
    for i, save in enumerate(host.get("saves") or []):
        attempt = (save.get("attempts") or [{}])[0]
        check = attempt.get("check") or {}
        press = (record.get("presses") or [])[i] if i < len(record.get("presses") or []) else None
        press_at = press[0] if isinstance(press, list) else None
        match = [r for r in resources if started is not None and "at" in check
                 and abs(r["start"] - (started + check["at"])) <= 50 and r["encodedBodySize"] > 0]
        row = {"i": i, "checkStatus": check.get("status"), "hashed": bool(check.get("sha256")),
               "status": attempt.get("status"), "waited": attempt.get("waited"),
               "readback": check.get("ms"), "put": (attempt["respondedAt"] - attempt["at"])
               if "respondedAt" in attempt and "at" in attempt else None,
               "getBytes": match[0]["encodedBodySize"] if match else None, "putBytes": save.get("bytes"),
               "engine": save["at"] - press_at if press_at is not None and "at" in save else None,
               "endToEnd": attempt["respondedAt"] - press_at if press_at is not None and "respondedAt" in attempt else None}
        row["counted"] = (row["checkStatus"] == 200 and row["hashed"] and isinstance(row["status"], int)
                          and 200 <= row["status"] < 300 and row["waited"] is not None and row["waited"] <= 50
                          and row["readback"] is not None and row["put"] is not None)
        rows.append(row)
    return rows


def verdict(record: dict[str, Any]) -> dict[str, Any]:
    if not record.get("opened"):
        return {"outcome": "not measured", "why": f"did not open: {record.get('openedState')}"}
    rows = rows_of(record)
    counted = [r for r in rows if r["counted"]]
    if len(counted) < 5:
        return {"outcome": "not measured", "why": f"{len(counted)} counted saves", "rows": rows}
    median = lambda key: statistics.median(r[key] for r in counted if r[key] is not None)  # noqa: E731
    out = {k: median(k) for k in ("readback", "put", "getBytes", "putBytes", "engine", "endToEnd")
           if any(r[k] is not None for r in counted)}
    out["outcome"] = "PASS" if out["readback"] <= out["put"] else "FAIL"
    return {**out, "counted": len(counted), "rows": rows}


def self_test() -> int:
    def fake(readback: int, put: int, n: int = 6, **over: Any) -> dict[str, Any]:
        saves = [{"at": 1000 * i + 500, "bytes": 10, "settled": True, "attempts": [
            {"waited": 0, "check": {"at": 1000 * i + 500, "status": 200, "sha256": "x", "ms": readback},
             "at": 1000 * i + 500 + readback, "respondedAt": 1000 * i + 500 + readback + put, "status": 204, **over}]}
                 for i in range(n)]
        return {"opened": True, "host": {"started": 0, "saves": saves}, "presses": [[1000 * i, True] for i in range(n)],
                "resources": [{"start": 1000 * i + 500, "encodedBodySize": 10} for i in range(n)]}
    no_check = fake(10, 20)
    for save in no_check["host"]["saves"]:
        del save["attempts"][0]["check"]
    cases = {"pass": (fake(10, 20), "PASS"), "read-back > PUT": (fake(30, 20), "FAIL"),
             "no check": (no_check, "not measured"), "waited 1100": (fake(10, 20, waited=1100), "not measured"),
             "4 counted": (fake(10, 20, n=4), "not measured"), "did not open": ({"opened": False}, "not measured")}
    bad = [f"{name}: {verdict(record)['outcome']} != {want}" for name, (record, want) in cases.items()
           if verdict(record)["outcome"] != want]
    print("\n".join(bad) or f"self-test: {len(cases)} cases as named")
    return 1 if bad else 0


def summary(report: dict[str, Any]) -> None:
    for key, arm in report["arms"].items():
        v = arm.get("verdict") or verdict(arm)
        print(f"  {key:>12}  {v['outcome']:<13} " + (
            f"readback {v['readback']} ms  put {v['put']} ms  get {v.get('getBytes')} B  put {v.get('putBytes')} B"
            f"  engine {v.get('engine')} ms  end-to-end {v.get('endToEnd')} ms  counted {v['counted']}"
            if "readback" in v else v.get("why", "")) + (" FATAL" if arm.get("fatal") else ""), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--sizes", default="0,1,5,20,50")
    parser.add_argument("--saves", type=int, default=6)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--analyse")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.analyse:
        summary(json.loads(Path(args.analyse).read_text()))
        return 0
    if self_test():
        return 1
    instance = Instance(DEFAULT_DDEV)
    report: dict[str, Any] = {"probe": Path(__file__).name, "probeSha256": sha256_file(Path(__file__)),
                              "criteria": "findings/evidence/m3-same-second/readback-size/CRITERIA.md",
                              "startedAt": utc_now(), **binding_fields(host_binding(DEFAULT_DDEV)),
                              "instance": instance.base, "saves": args.saves, "arms": {}}
    out = EVIDENCE / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m3-readback-size-", dir=PROJECT / "build") as scratch:
        for mib in (int(s) for s in args.sizes.split(",")):
            fixture = FIXTURE if mib == 0 else make_fixture(mib, Path(scratch) / f"noise-{mib}mib.odt")
            for kind in args.browsers.split(","):
                print(f"{kind} {mib} MiB …", flush=True)
                arm = run_arm(kind, instance, Path(scratch), fixture, args.saves)
                arm["mib"] = mib
                arm["verdict"] = verdict(arm)
                report["arms"][f"{kind}-{mib}"] = arm
                out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
                summary({"arms": {f"{kind}-{mib}": arm}})
    report["completedAt"] = utc_now()
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
