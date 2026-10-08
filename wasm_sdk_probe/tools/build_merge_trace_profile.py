#!/usr/bin/env python3
"""Finding 117's diagnostic profile: v18 with a worker that forwards every engine event.

Written 2026-10-08 (fable's ruling on 117, section 1, "D1-D4").  NEVER SHIPPED.

The engine already emits every LOK callback as a {"type":"lok"} event before it
handles it (`probe_engine.cpp` `onLokCallback`); the shared worker turns ids 0
and 1 into `document-invalidated`, six more into diagnostics under `debug`, and
drops the rest.  So "which callbacks reached the engine after the key, and
when" is answerable with no link: this profile is v18 byte for byte except
`sdk-worker.js`, whose one added statement posts a `merge-trace` event for
EVERY engine event (lok or not), stamped with the worker's clock as an absolute
time (`performance.timeOrigin + performance.now()`), so the page can put it on
its own clock.  Additive: every existing path is unchanged, the page and the
session ignore an event name they do not know (`e2-editor-app.js` onEvent,
`editor-session.js` `_handleEngineEvent`).  Precedent: finding 083 (worker-only
change, no link) and `build_e2_discovery_profile.py --lok-trace` (finding 037).

What it writes, refusing to overwrite either:
  dist/profiles/e2-editor-v18-trace117/     probe.js, probe.wasm, sdk-manifest.json copied
                                            (verified against v18's archive), the patched worker
  build/archive/e2-editor-v18-trace117-worker-<sha8>/   the patched worker, SHA256SUMS, TRACE.json

The manifest is v18's, unchanged (its `profile` still says e2-editor-v18: the
worker reads it only for error messages).  `--check` only verifies an existing
profile against the archive and the patch, and writes nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / "dist/profiles/e2-editor-v18"
ARCHIVE = HERE / "build/archive/e2-editor-v18-ad3f68bb-worker-00882139-cjk-e10-06976180"
NAME = "e2-editor-v18-trace117"
TARGET = HERE / "dist/profiles" / NAME
COPIED = ("probe.js", "probe.wasm", "sdk-manifest.json")

ANCHOR = """  const requestId = Number(event.requestId || 0);
  switch (event.type) {
    case "ready": {"""
PATCH = """  // FINDING 117 DIAGNOSTIC (build_merge_trace_profile.py): every engine event, timestamped.
  postEvent("merge-trace", {
    tw: performance.timeOrigin + performance.now(),
    type: event.type, id: event.id ?? null, requestId: event.requestId ?? null,
    completion: event.completion ?? null, code: event.code ?? null,
    keyToUndoMs: event.keyUndo?.keyToUndoMs ?? null,
    len: typeof event.payload === "string" ? event.payload.length : null,
    head: typeof event.payload === "string" ? event.payload.slice(0, 96) : null,
  });
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def archived() -> dict[str, str]:
    rows = (line.split() for line in (ARCHIVE / "SHA256SUMS").read_text().splitlines() if line.strip())
    return {name: digest for digest, name in rows}


def patched_worker(text: str) -> str:
    """Exactly once, or not at all: a silent no-op would produce a profile that traces nothing,
    and "no callback after the key" would then be the instrument's absence, not a measurement."""
    if text.count(ANCHOR) != 1:
        raise SystemExit("the worker's handleCEvent anchor is not there exactly once")
    return text.replace(ANCHOR, ANCHOR.replace("  switch (event.type) {",
                                               PATCH + "  switch (event.type) {"), 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the existing profile; write nothing")
    args = ap.parse_args()
    expected = archived()
    for name in (*COPIED, "sdk-worker.js"):
        if sha256(SOURCE / name) != expected[name]:
            raise SystemExit(f"{SOURCE / name} is not v18's archived {name}")
    worker = patched_worker((SOURCE / "sdk-worker.js").read_text(encoding="utf-8"))
    worker_sha = hashlib.sha256(worker.encode("utf-8")).hexdigest()
    store = HERE / "build/archive" / f"{NAME}-worker-{worker_sha[:8]}"
    if args.check:
        bad = [n for n in COPIED if sha256(TARGET / n) != expected[n]]
        if sha256(TARGET / "sdk-worker.js") != worker_sha:
            bad.append("sdk-worker.js")
        if sha256(store / "sdk-worker.js") != worker_sha:
            bad.append(f"{store.name}/sdk-worker.js")
        print(json.dumps({"ok": not bad, "bad": bad, "workerSha256": worker_sha}))
        return 1 if bad else 0
    for path in (TARGET, store):
        if path.exists():
            raise SystemExit(f"refusing to overwrite {path}")
    store.mkdir(parents=True)
    (store / "sdk-worker.js").write_text(worker, encoding="utf-8")
    TARGET.mkdir()
    for name in COPIED:
        shutil.copy2(SOURCE / name, TARGET / name)
        if sha256(TARGET / name) != expected[name]:
            raise SystemExit(f"copy of {name} does not hash to the archive")
    (TARGET / "sdk-worker.js").write_text(worker, encoding="utf-8")
    sums = {name: expected[name] for name in COPIED}
    sums["sdk-worker.js"] = worker_sha
    (store / "SHA256SUMS").write_text("".join(f"{d}  {n}\n" for n, d in sums.items()))
    (store / "TRACE.json").write_text(json.dumps({
        "profile": NAME, "shipped": False, "finding": 117,
        "source": {"profile": "e2-editor-v18", "archive": ARCHIVE.name,
                   "workerSha256": expected["sdk-worker.js"]},
        "sha256": sums, "anchor": ANCHOR, "patch": PATCH}, indent=1) + "\n")
    print(json.dumps({"profile": str(TARGET.relative_to(HERE)), "archive": str(store.relative_to(HERE)),
                      "sha256": sums}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
