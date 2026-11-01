#!/usr/bin/env python3
"""ST1 of SPEC-M3-own-stack: what the instance holds, read the same way on either stack.  Which stack answers is decided by PATH
(`ddev` the tool, or host-stack/bin/ddev).  Writes no secret.   snapshot.py OUT.json"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.error

REPO = Path(__file__).resolve().parents[4]
HOST = Path.home() / "Projects/Nextcloud_Apps/litecore"
sys.path.insert(0, str(REPO / "wasm_sdk_probe/tools"))
from check_m3_skeleton_open import Instance  # noqa: E402


def sh(argv):
    return subprocess.check_output(argv, cwd=HOST, text=True, stderr=subprocess.STDOUT, timeout=300).strip()


def query(sql):
    return sh(["ddev", "mysql", "-B", "-e", sql])


def main():
    instance = Instance(HOST)
    reference = json.loads((REPO / "findings/evidence/host-0.2.38/protected-documents-before.json").read_bytes())
    docs = []
    for item in reference:
        try:
            status, body = instance.dav("GET", item["path"])
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        docs.append({"fileId": item["fileId"], "path": item["path"], "status": status, "bytes": len(body),
                     "sha256": hashlib.sha256(body).hexdigest()})
    status = json.loads(sh(["ddev", "occ", "status", "--output=json"]))
    out = {"protectedDocuments": docs, "lockRows": query("SELECT * FROM oc_files_lock ORDER BY file_id;"),
           "counts": {t: query(f"SELECT COUNT(*) FROM {t};").splitlines()[-1] for t in
                      ("oc_filecache", "oc_users", "oc_appconfig", "oc_files_versions")},
           "installedVersion": sh(["ddev", "occ", "config:app:get", "litecore", "installed_version"]),
           "ncVersion": status.get("versionstring"), "maintenance": status.get("maintenance"), "needsDbUpgrade": status.get("needsDbUpgrade")}
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"docs": len(docs), "lockRows": len(out["lockRows"].splitlines()), **out["counts"], "version": out["installedVersion"],
                      "url": instance.base}, ensure_ascii=False))


if __name__ == "__main__":
    main()
