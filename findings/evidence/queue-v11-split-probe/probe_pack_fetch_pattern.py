#!/usr/bin/env python3
"""B-2 criteria 3'-i and 3'-ii — what the client actually fetches, and the fonts it ends up with.

3'-i  The startup fetch pattern, read from the SERVER'S OWN ACCESS LOG.

      Deliberately not read from the worker's `resource-pack-loaded` events:
      those are the loader reporting on itself, and the question is what
      crossed the wire.  `web/serve.py` is a `SimpleHTTPRequestHandler`, which
      logs every request to stderr, so the oracle is a process that shares no
      code with the thing under test.

3'-ii Font parity between profiles.  DERIVED, and the derivation is named: the
      mounted filesystem is the union of the packs the client fetched, and each
      pack's file list comes from its own metadata.  The worker verifies that a
      pack's ranges cover its blob exactly before writing any of it
      (`sdk-worker.js:600`), and criterion 1 established that the metadata
      partitions the image; so the derivation is sound, but it is a derivation
      and not a reading of `Module.FS`.  All three profiles are derived THE
      SAME WAY, which is what makes the parity comparison itself sound
      regardless.

Run from `wasm_sdk_probe/`:
  python3 ../findings/evidence/queue-v11-split-probe/probe_pack_fetch_pattern.py \
      --profile e2-editor-v12 [--out FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3] / "wasm_sdk_probe"
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from run_e2_c_product_path import build_mirror, repointed_page  # noqa: E402

FONT_PREFIX = "/instdir/share/fonts/"
REQUEST = re.compile(r'"(?:GET|HEAD) (/[^ "]*) HTTP/[0-9.]+"')


def font_inventory(root: Path, metadata_references: list[str]) -> dict[str, int]:
    inventory: dict[str, int] = {}
    for reference in metadata_references:
        metadata = json.loads((root / reference).read_text(encoding="utf-8"))
        for entry in metadata["files"]:
            if entry["filename"].startswith(FONT_PREFIX):
                inventory[entry["filename"]] = entry["end"] - entry["start"]
    return inventory



# The worker cannot be found by asking for it: `Target.getTargets` reports the
# pthread targets with empty urls and `Target.attachToTarget` returns a session
# nothing ever answers (measured 2026-08-27, recorded in
# `run_e2_c_product_path.induce_worker_failure`).  `Target.setAutoAttach` is the
# route that works, and it must be sent on the raw socket because Chrome emits
# `Target.attachedToTarget` BEFORE it answers, and `ChromeSession.call` discards
# every message whose id does not match while it waits for its own.
WALK_FONTS = """
(() => {
  if (typeof moduleInstance === "undefined" || !moduleInstance || !moduleInstance.FS)
    return JSON.stringify({error: "no module instance in this worker"});
  const FS = moduleInstance.FS;
  const files = [];
  const walk = (dir) => {
    let names;
    try { names = FS.readdir(dir); } catch (e) { return; }
    for (const name of names) {
      if (name === "." || name === "..") continue;
      const path = dir + "/" + name;
      const stat = FS.stat(path);
      if (FS.isDir(stat.mode)) walk(path);
      else files.push([path, stat.size]);
    }
  };
  walk("ARG_ROOT");
  return JSON.stringify({files});
})()
"""


def mounted_font_inventory(session, root: str, settle: float = 6.0) -> dict:
    """Read the font directory out of the RUNNING worker's Emscripten FS.

    B-2 criterion 3'-ii as written.  A derivation from pack metadata is
    corroboration, not this: the tree's current handoff is titled `instruments
    that hid what they were built to find`, and three of its five instrument
    failures were readers that derived where they could have looked.
    """
    call = getattr(session, "call", None)
    websocket = getattr(session, "websocket", None)
    if call is None or websocket is None:
        return {"error": "this session has no CDP websocket"}

    attached = []
    session.next_id += 1
    message_id = session.next_id
    websocket.send(json.dumps(
        {"id": message_id, "method": "Target.setAutoAttach",
         "params": {"autoAttach": True, "flatten": True,
                    "waitForDebuggerOnStart": False}}))
    deadline = time.monotonic() + settle
    while time.monotonic() < deadline:
        try:
            message = json.loads(websocket.recv(timeout=0.5))
        except Exception:                             # noqa: BLE001 -- a quiet
            continue                                  # socket is not an error
        if message.get("method") == "Target.attachedToTarget":
            attached.append(message["params"])

    workers = [a for a in attached
               if a["targetInfo"].get("type") == "worker"
               and a["targetInfo"].get("url", "").endswith("sdk-worker.js")]
    if not workers:
        return {"error": "auto-attach delivered no document-worker session",
                "attachedTypes": sorted({a["targetInfo"].get("type")
                                         for a in attached})}

    answer = call("Runtime.evaluate",
                  {"expression": WALK_FONTS.replace("ARG_ROOT", root),
                   "returnByValue": True},
                  session_id=workers[-1]["sessionId"])
    # `ChromeSession.call` already unwraps the CDP envelope, so the shape is
    # {"result": {"type": "string", "value": ...}} -- one level, not two.
    value = ((answer or {}).get("result") or {}).get("value")
    if not isinstance(value, str):
        return {"error": f"the worker did not answer with a string: {answer!r}"}
    payload = json.loads(value)
    if "error" in payload:
        return {"error": payload["error"]}
    return {"files": {name: size for name, size in payload["files"]}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--out")
    args = parser.parse_args()

    profile_root = PROJECT / "dist" / "profiles" / args.profile
    manifest_path = profile_root / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # The page as it would ship for this profile -- `repointed_page()`, the same
    # function the cutover tool and the runner use.  Not a fourth construction.
    source = (PROJECT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
    page, _, _ = repointed_page(source, args.profile, manifest_path)

    mounted: dict = {"error": "not attempted"}
    scratch = Path(tempfile.mkdtemp(prefix="pack-fetch-"))
    mirror = scratch / "dist"
    build_mirror(PROJECT / "dist", mirror, {"e2-editor-app.js": page.encode()})

    log_path = scratch / "server.log"
    port = free_port()
    with log_path.open("wb") as log:
        server = subprocess.Popen(
            [sys.executable, str(PROJECT / "web" / "serve.py"),
             "--port", str(port), "--root", str(mirror)],
            cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=log)
        session = None
        try:
            base = f"http://127.0.0.1:{port}/e2-editor.html"
            wait_page(base)
            session = ChromeSession("cold")
            navigate(session, base)
            deadline = time.monotonic() + args.timeout
            state = None
            while time.monotonic() < deadline:
                state = evaluate(session, READ_STATE)
                if state and state.get("state") in ("ready", "stopped", "expired"):
                    break
                time.sleep(0.5)
            assert state and state.get("state") == "ready", \
                f"{args.profile}: the editor did not reach ready: {state}"
            # A settling window: a pack fetched late would otherwise be missed
            # by a log read taken the instant the editor said ready.
            time.sleep(5.0)
            mounted = mounted_font_inventory(session, FONT_PREFIX.rstrip("/"))
        finally:
            if session is not None:
                session.close()
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

    requested = [m.group(1) for m in REQUEST.finditer(
        log_path.read_text(encoding="utf-8", errors="replace"))]
    assert requested, "the server logged no requests -- the oracle read nothing"

    packs = manifest.get("resourcePacks", [])
    def basename(reference: str) -> str:
        return reference.rsplit("/", 1)[-1]

    fetched_packs, unfetched_packs = [], []
    for pack in packs:
        name = basename(pack["data"])
        hit = any(path.endswith("/" + name) for path in requested)
        (fetched_packs if hit else unfetched_packs).append(
            {"id": pack["id"], "file": name,
             "loadAtStartup": pack.get("loadAtStartup"), "fetched": hit})

    data_requests = sorted({p for p in requested if p.endswith(".data")})

    mounted_metadata = [manifest["artifactFiles"]["soffice.data.js.metadata"]]
    mounted_metadata += [p["metadata"] for p in packs
                         if any(f["id"] == p["id"] and f["fetched"]
                                for f in fetched_packs)]
    fonts = font_inventory(profile_root, mounted_metadata)

    result = {
        "profile": args.profile,
        "criterion": "B-2 3'-i (server access log) and 3'-ii (derived font inventory)",
        "requestsLogged": len(requested),
        "dataRequests": data_requests,
        "packs": fetched_packs + unfetched_packs,
        "startupPacksAllFetched": all(
            p["fetched"] for p in fetched_packs + unfetched_packs
            if p["loadAtStartup"] is True),
        "nonStartupPacksNeverFetched": all(
            not p["fetched"] for p in fetched_packs + unfetched_packs
            if p["loadAtStartup"] is not True),
        "fontFiles": len(fonts),
        "fontBytes": sum(fonts.values()),
        "fontInventorySha": __import__("hashlib").sha256(
            json.dumps(sorted(fonts.items())).encode()).hexdigest()[:16],
        "fontInventory": fonts,
        "mountedFontInventory": mounted.get("files"),
        "mountedReadError": mounted.get("error"),
    }
    if mounted.get("files") is not None:
        result["mountedFontFiles"] = len(mounted["files"])
        result["mountedFontBytes"] = sum(mounted["files"].values())
        result["mountedInventorySha"] = hashlib.sha256(
            json.dumps(sorted(mounted["files"].items())).encode()).hexdigest()[:16]
        # THE POINT OF READING IT: derivation and reading must agree.  A
        # mismatch is not a probe blemish -- a loader that fetches bytes it does
        # not mount, or mounts bytes it did not fetch, is a discovery about
        # every profile.
        result["derivationMatchesTheMount"] = (mounted["files"] == fonts)
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "fontInventory"},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
