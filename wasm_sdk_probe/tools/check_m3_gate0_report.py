#!/usr/bin/env python3
"""The verdict of M3 gate 0, read from ONE report of probe_m3_gate0_coep.py.

Written to fable's ruling (handoff/m3-gate-0/RULING.md, CONDITIONS 3 a-h).  The
runner's own `provisionalGate` is not read: D1-D7 of the ruling showed it green on
false inputs.  Everything here is recomputed from raw fields -- a pass from the
editor's recorded steps, isolation from what the page read, C1/C3 through the
runner's scoring functions applied to the raw pages -- never from a boolean the
runner concluded.

  check_m3_gate0_report.py REPORT.json            -> one line, exit 0 iff a shape passes
  check_m3_gate0_report.py REPORT.json --json     -> the per-predicate detail
  check_m3_gate0_report.py BASE.json --red-cases DIR
      -> builds one mutated copy of BASE per case (gzipped, kept in DIR), checks
         that BASE itself is green and that every copy goes red on the predicate
         it names.  BASE is a shakedown report, so both run with --allow-shakedown.

--allow-shakedown relaxes only predicate (a)'s label and repeat count, so the rest
of the reader can be exercised on a shakedown before the counted run exists.
"""

from __future__ import annotations

import argparse
import copy
import functools
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_m3_gate0_coep as runner  # noqa: E402

BROWSERS = {"chrome", "firefox"}
ACTION = "set-paragraph-heading"
SHAPES = ("E1", "E1h", "E3")
HEADER_FIELDS = ("present", "elements", "idCount", "appMenu", "userMenu", "images",
                 "imagesLoaded", "buttons", "links")
STATIC_REQUIRED = {"e2-editor-app.js": "e2-editor-app.js",
                   "profiles/e2-editor-v8/sdk-worker.js": "profiles/e2-editor-v8/sdk-worker.js",
                   "profiles/e2-editor-v8/probe.wasm": "profiles/e2-editor-v8/probe.wasm"}
WIRE_REQUIRED = {"/r/php/profiles/e2-editor-v8/sdk-worker.js": "profiles/e2-editor-v8/sdk-worker.js",
                 "/r/php/profiles/e2-editor-v8/probe.js": "profiles/e2-editor-v8/probe.js"}


@functools.lru_cache(maxsize=None)
def sha256_file(path: Path) -> str:
    # Cached per process: --red-cases checks 24 copies against the same dist.
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------
# The editor sequence, re-judged from its recorded steps.


def run_passed(run: dict[str, Any]) -> bool:
    steps = {step.get("step"): step.get("state") or {} for step in run.get("steps") or []}
    boot, caret, acted = steps.get("boot") or {}, steps.get("place-caret") or {}, steps.get(ACTION) or {}
    if boot.get("state") != "ready":
        return False
    latency = caret.get("latency") or ""
    if "定位游標" not in latency or "失敗" in latency:
        return False
    before, after = caret.get("revision") or "", acted.get("revision") or ""
    return (before.isdigit() and after.isdigit() and int(after) == int(before) + 1
            and "失敗" not in (acted.get("latency") or ""))


def document_row(run: dict[str, Any]) -> dict[str, Any] | None:
    for row in (run.get("cdp") or {}).get("documents") or []:
        if row.get("url") == run.get("url"):
            return row
    return None


def as_page(run: dict[str, Any]) -> dict[str, Any]:
    """An editor run in the shape the runner's page scorers read."""
    return {"page": run.get("probe") or {}, "cdp": run.get("cdp")}


# --------------------------------------------------------------------------
# Predicates.  Each returns a list of failure strings; empty means it holds.


def p_a(report: dict[str, Any], allow_shakedown: bool) -> list[str]:
    bad = []
    if not allow_shakedown:
        if report.get("label") != "counted":
            bad.append(f"label is {report.get('label')!r}, not 'counted'")
        if report.get("repeats") != 3:
            bad.append(f"repeats is {report.get('repeats')!r}, not 3")
    if report.get("action") != ACTION:
        bad.append(f"action is {report.get('action')!r}")
    browsers = set((report.get("browsers") or {}).keys())
    if browsers != BROWSERS:
        bad.append(f"browsers are {sorted(browsers)}")
    for kind, result in (report.get("browsers") or {}).items():
        if "fatal" in result:
            bad.append(f"{kind}: fatal")
        for arm in ("E1", "E1h", "E3"):
            runs = (result.get("editor") or {}).get(arm) or []
            if len(runs) != report.get("repeats"):
                bad.append(f"{kind} {arm}: {len(runs)} runs, repeats {report.get('repeats')}")
    return bad


def p_b(report: dict[str, Any]) -> list[str]:
    bad = []
    product_page = (report.get("product") or {}).get("e2-editor.html")
    for kind, result in (report.get("browsers") or {}).items():
        for arm in SHAPES:
            for index, run in enumerate((result.get("editor") or {}).get(arm) or []):
                if not run_passed(run):
                    continue
                where = f"{kind} {arm}#{index}"
                probe = run.get("probe") or {}
                isolation = probe.get("isolation") or {}
                if isolation.get("crossOriginIsolated") is not True:
                    bad.append(f"{where}: passed without crossOriginIsolated")
                if isolation.get("sharedArrayBuffer") is not True:
                    bad.append(f"{where}: passed without SharedArrayBuffer")
                if probe.get("href") != run.get("url"):
                    bad.append(f"{where}: page was {probe.get('href')!r}, not the arm URL")
                if (probe.get("editorImport") or {}).get("ok") is not True:
                    bad.append(f"{where}: product module import not ok")
                source = ((probe.get("config") or {}).get("editor") or {}).get("sourceSha256")
                if source is None or source != product_page:
                    bad.append(f"{where}: re-wrapped page is not the hashed e2-editor.html")
                if kind == "chrome":
                    row = document_row(run)
                    if not row or row.get("coop") != "same-origin" or row.get("coep") != "require-corp":
                        bad.append(f"{where}: document headers on the wire were {row}")
    return bad


def p_c(report: dict[str, Any]) -> list[str]:
    bad = []
    for kind, result in (report.get("browsers") or {}).items():
        runs = (result.get("editor") or {}).get("E0") or []
        if len(runs) != 1:
            bad.append(f"{kind} E0: {len(runs)} runs")
            continue
        run = runs[0]
        boot = ((run.get("steps") or [{}])[0].get("state") or {})
        probe = run.get("probe") or {}
        isolation = probe.get("isolation") or {}
        if run_passed(run) or run.get("failedAt") != "boot":
            bad.append(f"{kind} E0: did not fail at boot")
        if boot.get("state") != "stopped":
            bad.append(f"{kind} E0: boot state {boot.get('state')!r} (a read error or a login page is not a negative result)")
        if isolation.get("crossOriginIsolated") is not False or isolation.get("sharedArrayBuffer") is not False:
            bad.append(f"{kind} E0: isolation was {isolation}")
        if (probe.get("editorImport") or {}).get("ok") is not True:
            bad.append(f"{kind} E0: product module did not load, so its failure is not attributed")
        if kind == "chrome":
            logs = [entry.get("text") or "" for entry in (run.get("cdp") or {}).get("errorLogs") or []]
            if not any("requires self.crossOriginIsolated" in text for text in logs):
                bad.append("chrome E0: no 'requires self.crossOriginIsolated' error in the log")
    return bad


def p_d(report: dict[str, Any]) -> list[str]:
    bad = []
    product = report.get("product") or {}
    rows = {row["path"].split("/dist/", 1)[-1]: row for row in report.get("staticFiles") or []}
    for name in STATIC_REQUIRED:
        row = rows.get(name)
        if not row or row.get("servedTheFile") is not True or row.get("bodySha256") != product.get(name):
            bad.append(f"static {name}: not the product bytes")
    wire = {row["path"]: row for row in report.get("wire") or []}
    for suffix, name in WIRE_REQUIRED.items():
        row = next((r for p, r in wire.items() if p.endswith(suffix)), None)
        if not row or row.get("bodySha256") != product.get(name):
            bad.append(f"wire {suffix}: not the product bytes")
    for name in runner.PRODUCT_FILES:
        path = runner.DIST / name
        if not path.is_file() or sha256_file(path) != product.get(name):
            bad.append(f"dist/{name} on disk now differs from the report")
    # The container reads the bind mount's source; it must be the dist hashed here.
    compose = Path((report.get("instance") or {}).get("probeApp", {}).get("repo", "")) / ".ddev" / "docker-compose.litecore-dist.yaml"
    match = re.search(r"-\s*(\S+):/mnt/litecore-dist:ro", compose.read_text()) if compose.is_file() else None
    if not match or Path(match.group(1)).resolve() != runner.DIST.resolve():
        bad.append(f"the container's dist mount is not {runner.DIST}")
    return bad


def recomputed_c1_c3(result: dict[str, Any], canary_origin: str) -> dict[str, Any]:
    pages = result.get("pages") or {}
    a0, a0b, a1 = pages.get("A0", {}), pages.get("A0b", {}), pages.get("A1", {})
    c1 = (runner.isolated(a0) is False and runner.isolated(a1) is True
          and runner.canary_loaded(a0) is True and runner.canary_loaded(a1) is False
          and any(u.startswith(canary_origin) for u in runner.failed_loads(a1, canary_origin)["probe"]))
    f0, f1 = runner.failed_loads(a0, canary_origin), runner.failed_loads(a1, canary_origin)
    comparison = runner.compare(runner.fingerprint(a0), runner.fingerprint(a0b), runner.fingerprint(a1))
    return {"C1": c1, "A0failures": f0["nextcloud"],
            "newInA1": sorted(set(f1["nextcloud"]) - set(f0["nextcloud"])),
            "comparison": comparison,
            "menu": ((a0.get("page") or {}).get("appMenuOpened") or {}).get("entries") or 0}


def p_e(report: dict[str, Any]) -> list[str]:
    bad = []
    origin = (report.get("instance") or {}).get("canaryOrigin") or ""
    for kind, result in (report.get("browsers") or {}).items():
        c = recomputed_c1_c3(result, origin)
        if not c["C1"]:
            bad.append(f"{kind}: C1 does not hold")
        if c["A0failures"]:
            bad.append(f"{kind}: A0 has Nextcloud failures {c['A0failures']}")
        if c["comparison"]["noisy"]:
            bad.append(f"{kind}: noisy fields {c['comparison']['noisy']}")
        if c["newInA1"] or not c["comparison"]["equal"] or c["menu"] < 1:
            bad.append(f"{kind}: C3 does not hold (new {c['newInA1']}, differs {c['comparison']['differs']}, menu {c['menu']})")
        for arm, record in (result.get("pages") or {}).items():
            href = (record.get("page") or {}).get("href") or ""
            if not href.startswith(record.get("url") or "\0"):
                bad.append(f"{kind} {arm}: page was {href!r}, arm URL {record.get('url')!r}")
    return bad


def p_f(report: dict[str, Any]) -> list[str]:
    """E1h's own Nextcloud chrome, read on E1h, not inferred from A1."""
    bad = []
    origin = (report.get("instance") or {}).get("canaryOrigin") or ""
    for kind, result in (report.get("browsers") or {}).items():
        a0 = runner.fingerprint((result.get("pages") or {}).get("A0", {})) or {}
        for index, run in enumerate((result.get("editor") or {}).get("E1h") or []):
            where = f"{kind} E1h#{index}"
            failures = runner.failed_loads(as_page(run), origin)["nextcloud"]
            if failures:
                bad.append(f"{where}: Nextcloud failures {failures}")
            mine = runner.fingerprint(as_page(run)) or {}
            differs = [k for k in HEADER_FIELDS if mine.get(k) != a0.get(k)]
            if differs:
                bad.append(f"{where}: header differs from A0 on {differs}")
            if (mine.get("appMenuEntries") or 0) < 1:
                bad.append(f"{where}: app menu opened with no entries")
    return bad


def p_h(report: dict[str, Any]) -> list[str]:
    instance = report.get("instance") or {}
    bad = []
    if (instance.get("nextcloud") or {}).get("versionstring") != "34.0.2":
        bad.append(f"Nextcloud {(instance.get('nextcloud') or {}).get('versionstring')!r}")
    if (instance.get("system") or {}).get("debug") != "false":
        bad.append(f"debug {(instance.get('system') or {}).get('debug')!r}")
    if (instance.get("probeApp") or {}).get("dirty"):
        bad.append("probe app tree was dirty")
    if instance.get("webserver") != "apache-fpm":
        bad.append(f"web server {instance.get('webserver')!r}")
    return bad


def shape_passes(report: dict[str, Any], arm: str) -> bool:
    repeats = report.get("repeats")
    return all(
        len((result.get("editor") or {}).get(arm) or []) == repeats
        and all(run_passed(run) for run in (result.get("editor") or {}).get(arm) or [])
        for result in (report.get("browsers") or {}).values()) and bool(report.get("browsers"))


def check(report: dict[str, Any], allow_shakedown: bool = False) -> dict[str, Any]:
    predicates = {"a": p_a(report, allow_shakedown), "b": p_b(report), "c": p_c(report),
                  "d": p_d(report), "e": p_e(report), "f": p_f(report), "h": p_h(report)}
    passes = {arm: shape_passes(report, arm) for arm in SHAPES}
    blocking = [k for k in ("a", "b", "c", "d", "h") if predicates[k]]
    if blocking:
        verdict = "NOT_ESTABLISHED"
    elif passes["E1h"] and not predicates["e"] and not predicates["f"]:
        verdict = "E1h"
    elif passes["E3"]:
        verdict = "E3"
    else:
        verdict = "STOP"
    # (g) E1 is never recommended: static engine files are measured, not a shape.
    return {"verdict": verdict, "blocking": blocking, "shapes": passes, "predicates": predicates}


def one_line(result: dict[str, Any]) -> str:
    failing = {k: len(v) for k, v in result["predicates"].items() if v}
    return (f"VERDICT {result['verdict']} shapes={','.join(k for k, v in result['shapes'].items() if v) or '-'} "
            f"failing={failing or '{}'}")


# --------------------------------------------------------------------------
# Red cases: one mutation per predicate, each must go red where it says.


def _e(report: dict, kind: str, arm: str, index: int = 0) -> dict:
    return report["browsers"][kind]["editor"][arm][index]


def _p(report: dict, kind: str, arm: str) -> dict:
    return report["browsers"][kind]["pages"][arm]


def _step(run: dict, name: str) -> dict:
    return next(step for step in run["steps"] if step["step"] == name)["state"]


RED_CASES: list[tuple[str, str, Callable[[dict], None]]] = [
    ("a-one-browser", "a", lambda r: r["browsers"].pop("firefox")),
    ("a-other-action", "a", lambda r: r.update(action="set-bold")),
    ("b-pass-without-isolation", "b", lambda r: _e(r, "firefox", "E1h")["probe"]["isolation"].update(crossOriginIsolated=False)),
    ("b-page-not-hashed", "b", lambda r: _e(r, "chrome", "E3")["probe"]["config"]["editor"].update(sourceSha256="0" * 64)),
    ("b-wire-without-coep", "b", lambda r: [d.update(coep=None) for d in _e(r, "chrome", "E1h")["cdp"]["documents"]]),
    ("b-wrong-page", "b", lambda r: _e(r, "firefox", "E3")["probe"].update(href="https://elsewhere.invalid/")),
    ("c-e0-read-error", "c", lambda r: _e(r, "firefox", "E0")["steps"][0].update(state={"readError": "login page"})),
    ("c-e0-isolated", "c", lambda r: _e(r, "chrome", "E0")["probe"]["isolation"].update(crossOriginIsolated=True, sharedArrayBuffer=True)),
    ("c-e0-no-attribution", "c", lambda r: _e(r, "chrome", "E0")["cdp"].update(errorLogs=[])),
    ("d-static-not-served", "d", lambda r: [row.update(servedTheFile=False) for row in r["staticFiles"] if row["path"].endswith("sdk-worker.js")]),
    ("d-product-hash-drift", "d", lambda r: r["product"].update({"profiles/e2-editor-v8/probe.wasm": "1" * 64})),
    ("d-wire-bytes-differ", "d", lambda r: [row.update(bodySha256="2" * 64) for row in r["wire"] if row["path"].endswith("/r/php/profiles/e2-editor-v8/probe.js")]),
    ("e-canary-not-caught", "e", lambda r: _p(r, "firefox", "A1")["page"]["canary"].update(event="load", naturalWidth=16)),
    ("e-noisy-field", "e", lambda r: _p(r, "chrome", "A0b")["page"]["header"].update(elements=_p(r, "chrome", "A0b")["page"]["header"]["elements"] + 3)),
    ("e-a0-failure", "e", lambda r: _p(r, "chrome", "A0")["page"]["images"].append({"src": "https://litecoreprobe.ddev.site:8443/core/img/x.png", "complete": True, "naturalWidth": 0, "broken": True})),
    ("e-a6-wrong-page", "e", lambda r: _p(r, "firefox", "A6")["page"].update(href="https://litecoreprobe.ddev.site:8443/apps/files/files")),
    ("f-header-differs", "f", lambda r: _e(r, "chrome", "E1h")["probe"]["header"].update(buttons=_e(r, "chrome", "E1h")["probe"]["header"]["buttons"] - 1)),
    ("f-menu-empty", "f", lambda r: _e(r, "firefox", "E1h")["probe"]["appMenuOpened"].update(entries=0)),
    ("f-nextcloud-blocked", "f", lambda r: _e(r, "chrome", "E1h")["cdp"]["loadingFailed"].append({"url": "https://litecoreprobe.ddev.site:8443/core/css/server.css", "blockedReason": "coep-frame-resource-needs-coep-header", "errorText": "net::ERR_BLOCKED_BY_RESPONSE"})),
    ("g-e1h-fails-so-e3", "verdict:E3", lambda r: _step(_e(r, "chrome", "E1h"), ACTION).update(revision="0")),
    ("g-both-fail-so-stop", "verdict:STOP", lambda r: (_step(_e(r, "chrome", "E1h"), ACTION).update(revision="0"),
                                                         _step(_e(r, "firefox", "E3"), "boot").update(state="stopped"))),
    ("h-dirty", "h", lambda r: r["instance"]["probeApp"].update(dirty=["M lib/Probe.php"])),
    ("h-version", "h", lambda r: r["instance"]["nextcloud"].update(versionstring="34.0.1")),
    ("h-nginx", "h", lambda r: r["instance"].update(webserver="nginx-fpm")),
]


def red_cases(base_path: Path, out_dir: Path) -> int:
    base = json.loads(base_path.read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    baseline = check(base, allow_shakedown=True)
    strict = check(base, allow_shakedown=False)
    summary = {"base": str(base_path), "baseline": one_line(baseline),
               "baselineGreen": baseline["verdict"] == "E1h",
               "strictOnShakedown": one_line(strict),
               "strictRedOnA": strict["verdict"] == "NOT_ESTABLISHED" and "a" in strict["blocking"],
               "cases": []}
    for name, expect, mutate in RED_CASES:
        mutated = copy.deepcopy(base)
        mutate(mutated)
        (out_dir / f"{name}.json.gz").write_bytes(gzip.compress(json.dumps(mutated).encode(), mtime=0))
        result = check(mutated, allow_shakedown=True)
        if expect.startswith("verdict:"):
            red = result["verdict"] == expect.split(":", 1)[1]
        else:
            red = bool(result["predicates"][expect]) and result["verdict"] != "E1h"
        summary["cases"].append({"case": name, "expects": expect, "red": red, "got": one_line(result)})
    summary["allRed"] = all(case["red"] for case in summary["cases"])
    (out_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "cases"}, ensure_ascii=False))
    for case in summary["cases"]:
        print(("RED  " if case["red"] else "GREEN") + f" {case['case']:28} {case['got']}")
    return 0 if summary["baselineGreen"] and summary["strictRedOnA"] and summary["allRed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-shakedown", action="store_true")
    parser.add_argument("--red-cases", type=Path, default=None)
    args = parser.parse_args()
    if args.red_cases:
        return red_cases(args.report, args.red_cases)
    result = check(json.loads(args.report.read_text()), args.allow_shakedown)
    print(json.dumps(result, indent=1, ensure_ascii=False) if args.json else one_line(result))
    return 0 if result["verdict"] in ("E1h", "E3") else 1


if __name__ == "__main__":
    sys.exit(main())
