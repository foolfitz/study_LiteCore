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

Since the 133 fix (fable's ruling §6, step 5): logpoints are placed by anchor
text, not line number (each anchor must match exactly one line of the served
file, or the probe refuses); `respIn` logs every reply before the pending check,
so a late reply to a cancelled request shows; `rearm` logs the fix's re-arm (a
deadline found late) -- a pre-fix SDK has no such line, so it needs --pre-fix.
The report carries `original`/`intruder` so score_arm runs.  A diagnostic tool,
not a counted check (spec §9.20; not in the §34.4 ledger).  133-B reads its
reports with findings/evidence/133/judge_133b.py.

Run (from wasm_sdk_probe/):  python3 tools/probe_k8_frozen_recovery.py --repeats 6 --out-dir ../findings/evidence/133/133-b
Default --out-dir: findings/evidence/m3-locks/k8-recoverable-2026-10-12/.
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

# (served path, anchor line text, offset, condition).  The logpoint goes on the
# line `offset` below the one line whose stripped text equals the anchor; main()
# refuses to run unless each anchor matches exactly one line of the served
# (dist) file, so an edited file cannot leave a logpoint silently logging
# nothing.  Anchors, not line numbers, since 2026-10-12 (the 133 fix moved the
# SDK's lines; fable's ruling §6 asked for `rearm` and an early `resp`).
LOGPOINTS = [
    ("editor-shell/editor-session.js", "_blockQueue(error, state, reason) {", 1,
     "console.log('LCDIAG blockQueue', Date.now(), state, reason, JSON.stringify({code: error && error.code,"
     " message: error && error.message, details: error && error.details}), new Error().stack), false"),
    ("editor-shell/editor-session.js", "if ([\"ready\", \"busy\"].includes(this.state.snapshot.state))", 0,
     "console.log('LCDIAG enterRecovery', Date.now(), JSON.stringify({code: error && error.code,"
     " message: error && error.message}), new Error().stack), false"),
    ("editor-shell/state-machine.js", "const current = this._snapshot.state;", 0,
     "console.log('LCDIAG transition', Date.now(), this._snapshot.state, next), false"),
    ("sdk/document-sdk.js", "const timeoutMs = options.timeoutMs ?? this._defaultTimeoutMs;", 0,
     "console.log('LCDIAG req', Date.now(), operation, requestId), false"),
    # Before `if (!entry) return;`: a reply to a request already failed and
    # cancelled is logged too (absent from the first report, ruling §4 item 3).
    ("sdk/document-sdk.js", "const entry = this._pending.get(message.requestId);", 0,
     "console.log('LCDIAG respIn', Date.now(), message.requestId, message.ok,"
     " this._pending.has(message.requestId)), false"),
    ("sdk/document-sdk.js", "this._pending.delete(message.requestId);", 0,
     "console.log('LCDIAG resp', Date.now(), entry.operation, message.requestId, message.ok), false"),
    ("sdk/document-sdk.js", "if (!this._pending.delete(requestId))", 0,
     "console.log('LCDIAG fail', Date.now(), entry.operation, requestId, error && error.code,"
     " error && error.message), false"),
    # The 133 fix's re-arm (a deadline found late): absent on a pre-fix SDK, so
    # the probe refuses a pre-fix package unless --pre-fix is given.
    ("sdk/document-sdk.js", "extensions += 1;", 0,
     "console.log('LCDIAG rearm', Date.now(), operation, requestId, Math.round(this._now() - dueAt)), false"),
    ("reader-shell/tile-scheduler.js", "if (controller.signal.aborted || error?.code === \"ABORTED\") {", 0,
     "console.log('LCDIAG tileError', Date.now(), JSON.stringify({code: error && error.code,"
     " message: error && error.message, retry: item && item.retry})), false"),
    ("e2-editor-app.js", "autosave.timer = null;", 0,
     "console.log('LCDIAG autosaveNow', Date.now(), reason, JSON.stringify(autosaveConditions())), false"),
]
RESOLVED: list[dict[str, Any]] = []


def resolve(pre_fix: bool) -> list[str]:
    """Find each anchor in the served file; return the problems."""
    problems = []
    RESOLVED.clear()
    for rel, anchor, offset, condition in LOGPOINTS:
        lines = (DIST / rel).read_text(encoding="utf-8").split("\n")
        hits = [i for i, line in enumerate(lines) if line.strip() == anchor]
        if pre_fix and anchor == "extensions += 1;" and not hits:
            continue
        if len(hits) != 1:
            problems.append(f"{rel}: anchor {anchor!r} matches {len(hits)} lines")
            continue
        regex = "/" + rel.replace(".", "\\.") + "(\\?.*)?$"
        RESOLVED.append({"rel": rel, "anchor": anchor, "line": hits[0] + offset + 1,
                         "regex": regex, "condition": condition})
    return problems


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
    for point in RESOLVED:
        result = session.call("Debugger.setBreakpointByUrl",
                              {"urlRegex": point["regex"], "lineNumber": point["line"] - 1, "columnNumber": 0,
                               "condition": point["condition"]})
        INSTALLED.append({"rel": point["rel"], "line": point["line"], "anchor": point["anchor"],
                          "locations": result.get("locations", [])})


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
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR,
                        help="where the report goes (133-B: findings/evidence/133/133-b)")
    parser.add_argument("--pre-fix", action="store_true",
                        help="the served SDK predates the 133 fix: no `rearm` logpoint")
    args = parser.parse_args()

    problems = resolve(args.pre_fix)
    if problems:
        print("refusing: " + "; ".join(problems))
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
        **binding_fields(binding), "baseUrl": instance.base, "logpoints": RESOLVED, "runs": [],
        # score_arm reads these (its KeyError 'original' in the first report).
        "original": {"source": str(locks.FIXTURE.relative_to(DIST)), "sha256": sha256_file(locks.FIXTURE)},
        "intruder": {"source": str(locks.SAMPLE.relative_to(DIST)), "sha256": sha256_file(locks.SAMPLE)},
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"probe-{report['startedAt'].replace(':', '')}.json"
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
                stops = [row[:5] for row in run["diag"]
                         if row[0] in ("LCDIAG blockQueue", "LCDIAG enterRecovery", "LCDIAG fail",
                                       "LCDIAG tileError", "LCDIAG rearm")]
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
