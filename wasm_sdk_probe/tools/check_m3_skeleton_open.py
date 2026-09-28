#!/usr/bin/env python3
"""M3 skeleton -- open an ODT from Files in the `litecore` app.

Criteria: handoff/m3-skeleton/CRITERIA.md, written before the first run.  The
runner uploads a known ODT over WebDAV, then per browser and repeat (fresh
browser each time): logs in, opens Files, clicks the file's name, lets the app's
host script open it in the shipped editor, and runs gate 0's page-smoke step on
it.  It never changes the app, the product or dist/.

  check_m3_skeleton_open.py --label shakedown|counted     run, write a report
  check_m3_skeleton_open.py --score REPORT.json           re-score a report, one line
  check_m3_skeleton_open.py --red-cases REPORT.json       each mutation must fail

Scoring reads raw fields (where the browser landed, what the page read, the
sha256 of the bytes it fetched, the product's own state line), never a boolean
the host script concluded.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import re
import ssl
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_m3_gate0_coep import (  # noqa: E402
    DIST, MKCERT_CA, PRODUCT_FILES, EventChrome, browser_login, firefox_profile,
    sha256_file, summarize_cdp, utc_now, wait_until)
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import POINT_AT, PRESS, READ_STATE, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-skeleton"
DEFAULT_DDEV = Path.home() / "Projects" / "Nextcloud_Apps" / "litecore"
FIXTURE = DIST / "e1-fixtures" / "multi-paragraph.odt"
SAMPLE = DIST / "e1-fixtures" / "list-contexts.odt"   # what the product opens on its own
NAME = "M3 骨架 測試.odt"
# A suffix, not the whole path (SPEC-M3-asset-delivery K3): since the asset-delivery
# host the editor document is /index.php/apps/litecore/r/<buildId>/e2-editor.html, and
# every M3 runner only asks "did the browser land on the editor" through it.
ROUTE = "/e2-editor.html"
FILES = "/apps/files/files?dir=/"
ACTION = "set-paragraph-heading"
BROWSERS = {"chrome", "firefox"}
# SPEC-M3-install-elsewhere: any instance but the dev one has the app from the
# release archive, and is bound to it file by file through this record.
RELEASE_RECORD = REPO / "findings" / "evidence" / "m3-install" / "release.json"
HOST_FILES = ("js/litecore-editor.js", "lib/Controller/EditorController.php", "templates/editor.php")


def installed_app(root: Path) -> Path | None:
    """Where the app lives on the instance at `root`: None on the dev instance
    (the host repo itself, nc-linked in); elsewhere, the directory the release
    archive was unpacked into (SPEC-M3-install-elsewhere §3.2)."""
    if root.resolve() == DEFAULT_DDEV.resolve():
        return None
    return root / "nextcloud" / "apps-extra" / "litecore"


def tree_listing(app: Path) -> tuple[dict[str, str], list[str]]:
    """Every regular file under `app` with its sha256, and every symlink."""
    files, links = {}, []
    for path in sorted(app.rglob("*")):
        name = path.relative_to(app).as_posix()
        if path.is_symlink():
            links.append(name)
        elif path.is_file():
            files[name] = sha256_file(path)
    return files, links


def host_binding(root: Path) -> dict[str, Any]:
    """hostRepo / hostDirty / hostFiles as the counted runners record them.
    Dev instance: the host repo (git), as before.  Anywhere else: the installed
    tree against the release record in both directions; hostRepo is the
    record's commit only when nothing differs, and hostDirty names every
    difference -- so the runners' "dirty refuses a counted run" still holds."""
    app = installed_app(root)
    if app is None:
        git = lambda *a: subprocess.run(["git", *a], cwd=DEFAULT_DDEV, capture_output=True,  # noqa: E731
                                        text=True).stdout.strip()
        return {"hostRepo": git("log", "-1", "--format=%H %s"), "hostDirty": git("status", "--short"),
                "hostFiles": {n: sha256_file(DEFAULT_DDEV / n) for n in HOST_FILES},
                "appDir": str(DEFAULT_DDEV), "sourceRepo": str(DEFAULT_DDEV)}
    release = json.loads(RELEASE_RECORD.read_text())
    members = release["members"]
    files, links = tree_listing(app) if app.is_dir() else ({}, [])
    differ = ["the app directory itself is a symlink"] if app.is_symlink() else []
    differ += [f"symlink {n}" for n in links]
    differ += [f"missing {n}" for n in sorted(set(members) - set(files))]
    differ += [f"extra {n}" for n in sorted(set(files) - set(members))]
    differ += [f"changed {n}" for n in sorted(set(files) & set(members)) if files[n] != members[n]]
    return {"hostRepo": "" if differ else f"{release['commit']} {release['subject']}",
            "hostDirty": "\n".join(differ) if app.is_dir() else f"no app at {app}",
            "hostFiles": {n: files[n] for n in HOST_FILES if n in files},
            "appDir": str(app), "sourceRepo": release["sourceRepo"],
            "release": {"archiveSha256": release["archive"]["sha256"], "members": len(members)}}


class Instance:
    def __init__(self, root: Path):
        self.root = root
        described = json.loads(self._run(["ddev", "describe", "-j"]))["raw"]
        self.base = described["primary_url"].rstrip("/")
        self.webserver = described.get("webserver_type")
        text = (root / ".ddev" / "config.local.yaml").read_text()
        self.password = re.search(r"NEXTCLOUD_ADMIN_PASSWORD=(\S+)", text).group(1)
        self.tls = ssl.create_default_context(cafile=str(MKCERT_CA))

    def _run(self, argv: list[str]) -> str:
        return subprocess.run(argv, cwd=self.root, check=True, capture_output=True,
                              text=True, timeout=300).stdout

    def dav(self, method: str, name: str, body: bytes | None = None,
            headers: dict[str, str] | None = None) -> tuple[int, bytes]:
        url = f"{self.base}/remote.php/dav/files/admin/{urllib.parse.quote(name)}"
        request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        token = f"admin:{self.password}".encode()
        request.add_header("Authorization", "Basic " + base64.b64encode(token).decode())
        with urllib.request.urlopen(request, context=self.tls, timeout=60) as response:
            return response.status, response.read()

    def upload(self, source: Path, name: str) -> dict[str, Any]:
        status, _ = self.dav("PUT", name, source.read_bytes(),
                             {"Content-Type": "application/vnd.oasis.opendocument.text"})
        body = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">'
                b"<d:prop><oc:fileid/><d:getcontentlength/></d:prop></d:propfind>")
        _, answer = self.dav("PROPFIND", name, body, {"Depth": "0", "Content-Type": "application/xml"})
        fileid = re.search(rb"<oc:fileid>(\d+)</oc:fileid>", answer)
        return {"putStatus": status, "fileId": int(fileid.group(1)) if fileid else None,
                "name": name, "source": str(source.relative_to(DIST)),
                "sha256": sha256_file(source), "bytes": source.stat().st_size}

    def describe(self) -> dict[str, Any]:
        occ = lambda *a: self._run(["ddev", "occ", *a])  # noqa: E731
        described = {"baseUrl": self.base, "webserver": self.webserver,
                     "nextcloud": json.loads(occ("status", "--output=json")),
                     "debug": occ("config:system:get", "debug").strip()}
        if installed_app(self.root) is not None:
            binding = host_binding(self.root)
            return {**described, "app": {
                "repo": binding["appDir"], "commit": binding["hostRepo"].split(" ")[0],
                "dirty": binding["hostDirty"].splitlines(), "release": binding["release"],
                "files": tree_listing(Path(binding["appDir"]))[0] if Path(binding["appDir"]).is_dir() else {}}}
        files = {}
        for name in self._run(["git", "ls-files"]).split("\n"):
            path = self.root / name
            if name and path.is_file() and not path.is_symlink():
                files[name] = sha256_file(path)
        return {**described,
                "app": {"repo": str(self.root),
                        "commit": self._run(["git", "rev-parse", "HEAD"]).strip(),
                        "dirty": self._run(["git", "status", "--porcelain"]).strip().splitlines(),
                        "files": files}}


def product_state(session) -> dict[str, Any]:
    try:
        return evaluate(session, READ_STATE)
    except Exception as error:  # noqa: BLE001 -- recorded
        return {"readError": f"{type(error).__name__}: {error}"}


def state_until(session, predicate, limit: float) -> dict[str, Any]:
    deadline = time.monotonic() + limit
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = product_state(session)
        if state and predicate(state):
            return state
        time.sleep(0.5)
    return {**state, "timedOut": True}


def dav_requests(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every request the page made for the user's document (Chrome only)."""
    return [{"method": e["params"]["request"]["method"], "url": e["params"]["request"]["url"],
             "initiator": (e["params"].get("initiator") or {}).get("type")}
            for e in events if e["method"] == "Network.requestWillBeSent"
            and "/remote.php/dav/files/" in e["params"]["request"]["url"]]


def run_once(kind: str, instance: Instance, scratch: Path, uploaded: dict[str, Any]) -> dict[str, Any]:
    session = (EventChrome("cold") if kind == "chrome"
               else FirefoxSession("cold", profile_dir=firefox_profile(scratch)))
    record: dict[str, Any] = {"browser": kind, "version": session.version}
    try:
        record["login"] = browser_login(session, instance.base, instance.password)
        navigate(session, instance.base + FILES, timeout=120)
        # ensure_ascii=False: CSS does not read JSON's \\uXXXX escapes, so an
        # escaped CJK name is a selector that can never match (shakedown 1).
        selector = (f'[data-cy-files-list-row-name={json.dumps(NAME, ensure_ascii=False)}]'
                    ' [data-cy-files-list-row-name-link]')
        record["filesRow"] = wait_until(
            session, f"(() => document.querySelector({json.dumps(selector)}) !== null)()", 60)
        if record["filesRow"] is not True:
            record["filesRowsSeen"] = evaluate(
                session, "(() => [...document.querySelectorAll('[data-cy-files-list-row-name]')]"
                         ".map((e) => e.getAttribute('data-cy-files-list-row-name')))()")
        record["clickedFrom"] = evaluate(session, "(() => location.href)()")
        if isinstance(session, EventChrome):
            session.drain()
        started = time.monotonic()
        session.click(selector)
        record["landed"] = wait_until(
            session, f"(() => location.pathname.endsWith({json.dumps(ROUTE)}) && location.href)()", 60)
        raw = wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                                  " return v && JSON.parse(v).done && v; })()", 400)
        record["host"] = json.loads(raw) if isinstance(raw, str) else {"notReported": raw}
        record["secondsToOpened"] = round(time.monotonic() - started, 2)
        # Gate 0's page-smoke step, on the document the host script opened.
        caret_before = product_state(session)
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        caret = state_until(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        evaluate(session, PRESS.replace("ARG_ACTION", ACTION))
        acted = state_until(session, lambda s: s.get("revision") != caret.get("revision")
                            or "失敗" in (s.get("latency") or ""), 120)
        record["smoke"] = {"before": caret_before, "caret": caret, "acted": acted}
        if isinstance(session, EventChrome):
            events = session.drain()
            record["cdp"] = summarize_cdp(events)
            record["davRequests"] = dav_requests(events)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        session.close()
    return record


# --------------------------------------------------------------------------
# Scoring -- raw fields only.


def score_run(run: dict[str, Any], uploaded: dict[str, Any]) -> dict[str, list[str]]:
    bad: dict[str, list[str]] = {k: [] for k in ("S1", "S2", "S3", "S4", "S5")}
    if "fatal" in run:
        return {k: ["run died"] for k in bad}
    landed = run.get("landed")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(landed).query) if isinstance(landed, str) else {}
    if not (isinstance(run.get("clickedFrom"), str) and "/apps/files/" in run["clickedFrom"]):
        bad["S1"].append(f"not clicked from Files: {run.get('clickedFrom')!r}")
    if not isinstance(landed, str) or query.get("fileId") != [str(uploaded["fileId"])]:
        bad["S1"].append(f"landed {landed!r}, want fileId {uploaded['fileId']}")
    host = run.get("host") or {}
    isolation = host.get("isolation") or {}
    if isolation.get("crossOriginIsolated") is not True or isolation.get("sharedArrayBuffer") is not True:
        bad["S2"].append(f"isolation {isolation}")
    if run.get("browser") == "chrome":
        rows = [d for d in (run.get("cdp") or {}).get("documents") or [] if d.get("url") == landed]
        if not rows or rows[0].get("coop") != "same-origin" or rows[0].get("coep") != "require-corp":
            bad["S2"].append(f"document headers on the wire {rows}")
    fetched = host.get("fetched") or {}
    if fetched.get("status") != 200 or fetched.get("sha256") != uploaded["sha256"] \
            or fetched.get("bytes") != uploaded["bytes"]:
        bad["S3"].append(f"fetched {fetched}")
    opened = next((s.get("state") or {} for s in host.get("steps") or [] if s.get("step") == "opened"), {})
    if opened.get("state") != "ready" or opened.get("doc") != uploaded["name"]:
        bad["S4"].append(f"product state after open {opened}")
    smoke = run.get("smoke") or {}
    caret, acted = smoke.get("caret") or {}, smoke.get("acted") or {}
    before, after = caret.get("revision") or "", acted.get("revision") or ""
    if "定位游標" not in (caret.get("latency") or "") or "失敗" in (caret.get("latency") or ""):
        bad["S5"].append(f"caret {caret.get('latency')!r}")
    elif not (before.isdigit() and after.isdigit() and int(after) == int(before) + 1
              and "失敗" not in (acted.get("latency") or "")):
        bad["S5"].append(f"revision {before!r} -> {after!r}, latency {acted.get('latency')!r}")
    if acted.get("doc") != uploaded["name"]:
        bad["S5"].append(f"action ran on {acted.get('doc')!r}")
    return bad


def score(report: dict[str, Any], strict: bool) -> dict[str, Any]:
    uploaded = report.get("uploaded") or {}
    problems: list[str] = []
    if uploaded.get("sha256") == report.get("sampleSha256"):
        problems.append("the uploaded file is the bundled sample; S3/S4 cannot tell them apart")
    if set(report.get("browsers") or {}) != BROWSERS:
        problems.append(f"browsers {sorted(report.get('browsers') or {})}")
    if strict and (report.get("label") != "counted" or report.get("repeats") != 3):
        problems.append(f"label {report.get('label')!r} repeats {report.get('repeats')!r}")
    if (report.get("instance") or {}).get("app", {}).get("dirty"):
        problems.append("app tree dirty")
    per: dict[str, Any] = {}
    for kind, runs in (report.get("browsers") or {}).items():
        scored = [score_run(run, uploaded) for run in runs]
        passed = sum(1 for s in scored if not any(s.values()))
        per[kind] = {"passed": passed, "of": len(runs),
                     "failing": [{k: v for k, v in s.items() if v} for s in scored if any(s.values())]}
        if len(runs) != report.get("repeats") or passed != len(runs):
            problems.append(f"{kind} {passed}/{len(runs)}")
    return {"works": not problems, "problems": problems, "browsers": per}


def one_line(result: dict[str, Any]) -> str:
    counts = ",".join(f"{k}={v['passed']}/{v['of']}" for k, v in sorted(result["browsers"].items()))
    return f"SKELETON {'WORKS' if result['works'] else 'NOT_ESTABLISHED'} {counts or '-'} problems={result['problems']}"


RED_CASES = [
    ("S1-wrong-file", lambda r: r["browsers"]["chrome"][0].update(landed=r["browsers"]["chrome"][0]["landed"].replace("fileId=", "fileId=9"))),
    ("S1-typed-url", lambda r: r["browsers"]["firefox"][0].update(clickedFrom="about:blank")),
    ("S2-not-isolated", lambda r: r["browsers"]["firefox"][0]["host"]["isolation"].update(crossOriginIsolated=False)),
    ("S2-no-coep-on-wire", lambda r: [d.update(coep=None) for d in r["browsers"]["chrome"][0]["cdp"]["documents"]]),
    ("S3-other-bytes", lambda r: r["browsers"]["chrome"][0]["host"]["fetched"].update(sha256="0" * 64)),
    ("S4-still-the-sample", lambda r: next(s for s in r["browsers"]["firefox"][0]["host"]["steps"] if s["step"] == "opened")["state"].update(doc="list-contexts.odt")),
    ("S5-no-revision", lambda r: r["browsers"]["chrome"][0]["smoke"]["acted"].update(revision=r["browsers"]["chrome"][0]["smoke"]["caret"]["revision"])),
    ("S5-acted-on-sample", lambda r: r["browsers"]["firefox"][0]["smoke"]["acted"].update(doc="list-contexts.odt")),
    ("one-browser", lambda r: r["browsers"].pop("firefox")),
    ("sample-uploaded", lambda r: r.update(sampleSha256=r["uploaded"]["sha256"])),
]


def red_cases(path: Path) -> int:
    base = json.loads(path.read_text())
    baseline = score(base, strict=False)
    print(("GREEN" if baseline["works"] else "RED  ") + " base " + one_line(baseline))
    ok = baseline["works"]
    for name, mutate in RED_CASES:
        mutated = copy.deepcopy(base)
        mutate(mutated)
        result = score(mutated, strict=False)
        ok = ok and not result["works"]
        print(("RED  " if not result["works"] else "GREEN") + f" {name:20} " + one_line(result))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--score", type=Path)
    parser.add_argument("--red-cases", type=Path)
    args = parser.parse_args()
    if args.red_cases:
        return red_cases(args.red_cases)
    if args.score:
        report = json.loads(args.score.read_text())
        result = score(report, strict=report.get("label") == "counted")
        print(one_line(result))
        return 0 if result["works"] else 1
    if not args.label:
        parser.error("--label is required for a run")

    instance = Instance(args.ddev_root)
    report: dict[str, Any] = {
        "probe": "m3-skeleton-open", "label": args.label, "startedAt": utc_now(),
        "criteria": "handoff/m3-skeleton/CRITERIA.md", "repeats": args.repeats,
        "runner": {"path": str(Path(__file__).relative_to(REPO)), "sha256": sha256_file(Path(__file__))},
        "instance": instance.describe(),
        "product": {name: sha256_file(DIST / name) for name in PRODUCT_FILES},
        "sampleSha256": sha256_file(SAMPLE),
        "uploaded": instance.upload(FIXTURE, NAME),
        "browsers": {},
    }
    if args.label == "counted" and report["instance"]["app"]["dirty"]:
        print("refusing a counted run on a dirty app tree", file=sys.stderr)
        return 2
    (PROJECT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m3-skeleton-", dir=PROJECT / "build") as scratch:
        for kind in args.browsers.split(","):
            report["browsers"][kind] = [
                run_once(kind, instance, Path(scratch) / f"{kind}-{attempt}", report["uploaded"])
                for attempt in range(args.repeats)]
    report["completedAt"] = utc_now()
    result = score(report, strict=args.label == "counted")
    report["score"] = result
    out = EVIDENCE / ("runs" if args.label == "counted" else "shakedown") / \
        f"{report['startedAt'].replace(':', '').replace('+0000', 'Z')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"report": str(out)}, ensure_ascii=False))
    print(one_line(result))
    return 0 if result["works"] else 1


if __name__ == "__main__":
    sys.exit(main())
