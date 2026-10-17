#!/usr/bin/env python3
"""Host 0.2.25: what the installed host serves over HTTP, as a second source beside the package manifest.

The shape of findings/evidence/host-0.2.24/http-served-page.txt (the entry's 303 and its address; the page under
gzip and zstd, decoded), plus the v21 profile's wasm and worker.  Logs in as admin, uploads one fixture to a name of
its own, reads, deletes the fixture.  Writes nothing else.

  python3 findings/evidence/host-0.2.25/http_served_page.py [MANIFEST]

MANIFEST (default: the installed host's engine/MANIFEST.json) is what the served bytes are compared with; giving
0.2.24's archived manifest is the red case.
"""
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[3] / "wasm_sdk_probe" / "tools"
sys.path.insert(0, str(TOOLS))
from check_m3_assets import ENTRY, asset_prefix, fetch  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, FIXTURE, Instance  # noqa: E402
from probe_m3_gate0_coep import Wire  # noqa: E402

PATHS = ("e2-editor-app.js", "profiles/e2-editor-v21/sdk-worker.js", "profiles/e2-editor-v21/probe.wasm")
NAME = "host-0225-http-check.odt"

instance = Instance(DEFAULT_DDEV)
manifest = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DDEV / "engine" / "MANIFEST.json").read_text())
upload = instance.upload(FIXTURE, NAME)
try:
    wire = Wire(instance)
    wire.login()
    entry = fetch(wire, f"{instance.base}{ENTRY}?fileId={upload['fileId']}", "gzip")
    location = entry["headers"].get("location") or ""
    address = location.split("/r/", 1)[1].split("/", 1)[0] if "/r/" in location else "?"
    print(f"entry {entry['status']} address {address}  (manifest buildId {manifest['buildId']})")
    base = instance.base + "/index.php" + asset_prefix(address)
    bad = []
    for path in PATHS:
        want = (manifest["files"].get(path) or {}).get("sha256", "not in the manifest")
        for coding in ("gzip", "zstd"):
            got = fetch(wire, base + path, coding)
            ce = got["headers"].get("content-encoding")
            decoded = got.get("decodedSha256", "")
            print(f"{path} {coding} {got['status']} {ce} decoded {decoded[:16]} {got['bodyBytes']} bytes")
            if got["status"] != 200 or ce != coding or decoded != want:
                bad.append(f"{path} {coding}: status {got['status']}, coding {ce}, decoded {decoded[:16]} != {want[:16]}")
    if not address.startswith(manifest["buildId"] + "-"):
        bad.append(f"address {address} does not start with the manifest's buildId")
    print("\n".join(bad) if bad else "every path decodes to the manifest's sha256 under gzip and zstd")
finally:
    print(f"fixture {NAME} fileId {upload['fileId']} PUT {upload['putStatus']} DELETE {instance.dav('DELETE', NAME)[0]}")
