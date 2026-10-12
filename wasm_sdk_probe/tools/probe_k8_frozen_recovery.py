#!/usr/bin/env python3
"""Diagnostic probe, not a counted runner: why did K8 (`check_m3_locks.py` arm
`frozen`) end in `recoverable-error` on 2026-10-12 (shakedown 113020Z, page
d761f1ce..., host 0.2.13 e028517) after 27 earlier runs ended `ready`?

It runs the locks runner's own `run_arm("frozen", "chrome", ...)` unchanged and
adds CDP logpoints -- conditional breakpoints whose condition is
`console.log(...), false`, so they never pause -- at the places the session can
enter `recoverable-error` and at what feeds them:

  * editor-session.js `_blockQueue` and `_enterRecovery` (with the error code,
    message and a stack), and state-machine.js `transition`;
  * document-sdk.js `_request` (operation, request id), `_handleMessage` (the
    response) and `failAndCancel` (timeout/abort, with the code);
  * tile-scheduler.js's render `.catch` (code, retry);
  * e2-editor-app.js `autosaveNow` (reason and conditions).

Every message carries Date.now(), so the order around the freeze (freezeAt /
thawAt in the record are host-relative, `data-litecore.started` + at) can be
read.  No product byte and no check is changed; the arm's own record and the
runner's own score_arm verdict are kept beside the log.

Run:  python3 tools/probe_k8_frozen_recovery.py --repeats 3
Writes findings/evidence/m3-locks/k8-recoverable-2026-10-12/probe-<UTC>.json.
Note: Debugger.enable and the logpoints are themselves a (small) timing change.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_m3_locks as locks  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance, binding_fields, host_binding  # noqa: E402
from probe_m3_gate0_coep import DIST, sha256_file, utc_now  # noqa: E402

OUT_DIR = locks.REPO / "findings" / "evidence" / "m3-locks" / "k8-recoverable-2026-10-12"

# (url regex, 1-based line, condition).  Lines are the served files' (equal to
# the sources, checked in main()).
LOGPOINTS = [
    (r"/editor-shell/editor-session\.js(\?.*)?$", 343,
     "console.log('LCDIAG blockQueue', Date.now(), state, reason, JSON.stringify({code: error && error.code,"
     " message: error && error.message, details: error && error.details}), new Error().stack), false"),
    (r"/editor-shell/editor-session\.js(\?.*)?$", 355,
     "console.log('LCDIAG enterRecovery', Date.now(), JSON.stringify({code: error && error.code,"
     " message: error && error.message}), new Error().stack), false"),
    (r"/editor-shell/state-machine\.js(\?.*)?$", 41,
     "console.log('LCDIAG transition', Date.now(), this._snapshot.state, next), false"),
    (r"/sdk/document-sdk\.js(\?.*)?$", 159,
     "console.log('LCDIAG req', Date.now(), operation, requestId), false"),
    (r"/sdk/document-sdk\.js(\?.*)?$", 236,
     "console.log('LCDIAG resp', Date.now(), entry.operation, message.requestId, message.ok), false"),
    (r"/sdk/document-sdk\.js(\?.*)?$", 171,
     "console.log('LCDIAG fail', Date.now(), entry.operation, requestId, error && error.code,"
     " error && error.message), false"),
    (r"/reader-shell/tile-scheduler\.js(\?.*)?$", 253,
     "console.log('LCDIAG tileError', Date.now(), JSON.stringify({code: error && error.code,"
     " message: error && error.message, retry: item && item.retry})), false"),
    (r"/e2-editor-app\.js(\?.*)?$", 2606,
     "console.log('LCDIAG autosaveNow', Date.now(), reason, JSON.stringify(autosaveConditions())), false"),
]
# What each logpoint line must read in the source, so a moved line is caught
# before a run instead of silently logging nothing.
EXPECT = {
    ("editor-shell/editor-session.js", 343): "this._invalidateDrain();",
    ("editor-shell/editor-session.js", 355): "if ([\"ready\", \"busy\"].includes(this.state.snapshot.state))",
    ("editor-shell/state-machine.js", 41): "const current = this._snapshot.state;",
    ("sdk/document-sdk.js", 159): "const timeoutMs = options.timeoutMs ?? this._defaultTimeoutMs;",
    ("sdk/document-sdk.js", 236): "this._pending.delete(message.requestId);",
    ("sdk/document-sdk.js", 171): "if (!this._pending.delete(requestId))",
    ("reader-shell/tile-scheduler.js", 253): "if (controller.signal.aborted || error?.code === \"ABORTED\") {",
    ("e2-editor-app.js", 2606): "autosave.timer = null;",
}

ALL_EVENTS: list[dict[str, Any]] = []
INSTALLED: list[dict[str, Any]] = []


class DiagChrome(locks.LockChrome):
    KEEP = locks.LockChrome.KEEP | {"Runtime.consoleAPICalled"}

    def drain(self) -> list[dict[str, Any]]:
        events = super().drain()
        ALL_EVENTS.extend(events)
        return events

    def close(self) -> None:
        # A run that died before run_arm's drain still leaves its log here.
        ALL_EVENTS.extend(self.events)
        self.events = []
        super().close()


def install(session) -> None:
    session.call("Debugger.enable")
    for regex, line, condition in LOGPOINTS:
        result = session.call("Debugger.setBreakpointByUrl",
                              {"urlRegex": regex, "lineNumber": line - 1, "columnNumber": 0,
                               "condition": condition})
        INSTALLED.append({"regex": regex, "line": line, "locations": result.get("locations", [])})


ORIGINAL_EDIT = locks.edit


def edit_with_logpoints(session, record: dict[str, Any], key: str = "smoke") -> None:
    if isinstance(session, DiagChrome):
        install(session)
    ORIGINAL_EDIT(session, record, key)


def diag_lines(events: list[dict[str, Any]]) -> list[list[Any]]:
    out = []
    for event in events:
        if event.get("method") != "Runtime.consoleAPICalled":
            continue
        args = event["params"].get("args", [])
        values = [a.get("value", a.get("description")) for a in args]
        if values and str(values[0]).startswith("LCDIAG"):
            out.append(values)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    args = parser.parse_args()

    for (rel, line), text in EXPECT.items():
        got = (DIST / rel).read_text(encoding="utf-8").split("\n")[line - 1].strip()
        if got != text:
            print(f"logpoint line moved: {rel}:{line} reads {got!r}, expected {text!r}")
            return 2

    locks.LockChrome = DiagChrome
    locks.edit = edit_with_logpoints
    binding = host_binding(args.ddev_root)
    instance = Instance(args.ddev_root)
    log: list[dict[str, Any]] = []
    server = locks.Server(instance, log)
    report: dict[str, Any] = {
        "probe": "probe_k8_frozen_recovery.py", "probeSha256": sha256_file(Path(__file__)),
        "locksRunnerSha256": sha256_file(Path(locks.__file__)),
        "startedAt": utc_now(), "static": {"page": {"dist": sha256_file(DIST / "e2-editor-app.js")}},
        **binding_fields(binding), "baseUrl": instance.base, "logpoints": LOGPOINTS, "runs": [],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"probe-{report['startedAt'].replace(':', '')}.json"
    try:
        report["setup"] = server.setup()
        with tempfile.TemporaryDirectory(prefix="k8-diag-", dir=locks.PROJECT / "build") as scratch:
            for index in range(args.repeats):
                ALL_EVENTS.clear()
                INSTALLED.clear()
                print(f"K8 frozen chrome #{index + 1}", flush=True)
                run = locks.run_arm("frozen", "chrome", server, Path(scratch))
                run["logpointsInstalled"] = list(INSTALLED)
                run["diag"] = diag_lines(ALL_EVENTS)
                try:
                    run["scoreProblems"] = locks.score_arm(run, report)
                except Exception as error:  # noqa: BLE001 -- recorded
                    run["scoreProblems"] = [f"score_arm raised {type(error).__name__}: {error}"]
                report["runs"].append(run)
                s1 = run.get("save1State") or {}
                stops = [row[:4] for row in run["diag"]
                         if row[0] in ("LCDIAG blockQueue", "LCDIAG enterRecovery", "LCDIAG fail", "LCDIAG tileError")]
                print(f"  state {s1.get('state')}  latency {s1.get('latency')}  problems {run['scoreProblems']}"
                      f"  diag lines {len(run['diag'])}  fatal {'fatal' in run}"
                      f"  unresolved logpoints {[i['line'] for i in INSTALLED if not i['locations']]}", flush=True)
                for row in stops:
                    print("   ", json.dumps(row, ensure_ascii=False)[:300], flush=True)
                out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    finally:
        server.teardown()
        report["completedAt"] = utc_now()
        report["httpLog"] = log
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(locks.REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
