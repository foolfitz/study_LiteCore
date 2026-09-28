#!/usr/bin/env python3
"""M3 versions, step 0: what Nextcloud's file versions look like around our saves, over HTTP only.

Roadmap §5.5 asks for "versions correct" and nothing has measured them. The host
(`litecore` 49cc4ab) saves with a token lock held and every PUT conditional
(`If-Match`, plus `If: (<token>)`). This probe does the same over HTTP, next to a
plain client doing the same writes with the same timing, and records every
version Nextcloud keeps (revision, size, sha256 of its bytes, author, label):

  V1  host-like saves (LOCK, two conditional PUTs 2.5 s apart, UNLOCK) against a
      plain client (two unconditional PUTs, same spacing): same version history?
      Do LOCK / UNLOCK, which move the ETag, add a version or move the mtime?
  V2  two saves in the same second, both ways: Nextcloud names version files by
      mtime in seconds, so the first of the two is expected to be kept as no version.
  V3  the holder's own restore (what Files' Versions tab sends: MOVE to
      versions/<user>/restore/target, no lock token) while our token lock is held.
      Then the host's next save (old If-Match, token): refused? version added?
  V4  the same restore by a share recipient with write permission.
  V5  control for V3/V4: the recipient holds a *user* lock; the owner's restore.
      files_lock's storage wrapper refuses writes under user and app locks and
      never looks at token locks (LockWrapper::isFileLocked), so a refusal here
      and none in V3/V4 would put the difference on the lock type.
  V6  a conflict copy (PUT If-None-Match: *): its own history, and the original's.
  V7  (added after the first run's V2) someone else's same-size write in the same second
      as ours: does our later PUT with our If-Match get 412, or overwrite it?

A second user `lcprobe` is created for the run and deleted at the end, with every
file and the one share the probe made.

    python3 wasm_sdk_probe/tools/probe_m3_versions.py
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_skeleton_open import DEFAULT_DDEV, FIXTURE, Instance  # noqa: E402
from probe_m3_lock_semantics import LOCKINFO, ODT, PROBE_USER, Client  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-versions"
NS = {"d": "DAV:", "oc": "http://owncloud.org/ns", "nc": "http://nextcloud.org/ns"}
FILE_PROPS = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns" '
              b'xmlns:nc="http://nextcloud.org/ns"><d:prop><d:getetag/><d:getlastmodified/>'
              b"<d:getcontentlength/><oc:fileid/><oc:permissions/><nc:lock/><nc:lock-owner/>"
              b"<nc:lock-owner-type/><d:lockdiscovery/></d:prop></d:propfind>")
VERSION_PROPS = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns">'
                 b"<d:prop><d:getlastmodified/><d:getcontentlength/><d:getetag/>"
                 b"<nc:version-label/><nc:version-author/></d:prop></d:propfind>")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class VClient(Client):
    """Client that also hands back the whole body (the base class logs 1500 characters)."""

    def raw(self, step: str, method: str, path: str, body: bytes | None = None,
            headers: dict[str, str] | None = None) -> tuple[dict[str, Any], bytes]:
        sent = {"X-Requested-With": "XMLHttpRequest", **(headers or {})}
        request = urllib.request.Request(self.base + path, data=body, method=method, headers=sent)
        request.add_header("Authorization", self.auth)
        try:
            with urllib.request.urlopen(request, context=self.tls, timeout=60) as response:
                status, got, data = response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            status, got, data = error.code, error.headers, error.read()
        except (http.client.RemoteDisconnected, ConnectionError, urllib.error.URLError) as error:
            # A server-side crash can end the connection with no status (seen on a version GET).
            status, got, data = f"no response: {type(error).__name__}", {}, b""
        entry = {"step": step, "actor": self.user, "method": method, "path": urllib.parse.unquote(path),
                 "sent": {k: v for k, v in sent.items() if k != "X-Requested-With"}, "status": status,
                 "headers": {k.lower(): v for k, v in got.items()
                             if k.lower() in {"etag", "oc-etag", "lock-token", "content-type", "x-nc-ownerid"}},
                 "bodySha256": sha(data) if data else None, "bodyLength": len(data),
                 "body": data[:1500].decode("utf-8", "replace") if data and not data.startswith(b"PK") else None}
        self.log.append(entry)
        return entry, data

    def file(self, step: str, name: str) -> dict[str, Any]:
        entry, data = self.raw(step, "PROPFIND", self.dav_path(name), FILE_PROPS,
                               {"Depth": "0", "Content-Type": "application/xml"})
        if entry["status"] != 207:
            return {"status": entry["status"]}
        prop = ET.fromstring(data).find(".//d:propstat/d:prop", NS)
        text = lambda tag: (prop.findtext(tag, namespaces=NS) if prop is not None else None)  # noqa: E731
        tokens = [t.text for t in ET.fromstring(data).iterfind(".//d:lockdiscovery//d:locktoken/d:href", NS)]
        return {"etag": text("d:getetag"), "mtime": text("d:getlastmodified"), "size": text("d:getcontentlength"),
                "fileid": text("oc:fileid"), "permissions": text("oc:permissions"), "lock": text("nc:lock"),
                "lockOwner": text("nc:lock-owner"), "lockOwnerType": text("nc:lock-owner-type"),
                "tokens": tokens}

    def content(self, step: str, name: str) -> str | None:
        entry, data = self.raw(step, "GET", self.dav_path(name))
        return sha(data) if entry["status"] == 200 else None

    def versions(self, step: str, fileid: str) -> list[dict[str, Any]] | dict[str, Any]:
        """Every version Nextcloud lists for the file, oldest first, each with the sha256 of its bytes."""
        home = f"/remote.php/dav/versions/{self.user}/versions/{fileid}"
        entry, data = self.raw(step, "PROPFIND", home, VERSION_PROPS,
                               {"Depth": "1", "Content-Type": "application/xml"})
        if entry["status"] != 207:
            return {"status": entry["status"]}
        found = []
        for response in ET.fromstring(data).iterfind("d:response", NS):
            href = urllib.parse.unquote(response.findtext("d:href", namespaces=NS)).rstrip("/")
            if href.endswith(f"/versions/{fileid}"):
                continue
            prop = response.find("d:propstat/d:prop", NS)
            got, body = self.raw(step + " (version bytes)", "GET", href[href.index("/remote.php"):])
            found.append({"revision": href.rsplit("/", 1)[1], "mtime": prop.findtext("d:getlastmodified", namespaces=NS),
                          "size": prop.findtext("d:getcontentlength", namespaces=NS),
                          "author": prop.findtext("nc:version-author", namespaces=NS),
                          "label": prop.findtext("nc:version-label", namespaces=NS),
                          "sha256": sha(body) if got["status"] == 200 else f"GET {got['status']}"})
        return sorted(found, key=lambda v: int(v["revision"]) if v["revision"].isdigit() else 0)

    def restore(self, step: str, fileid: str, revision: str) -> dict[str, Any]:
        """What Files' Versions tab sends to restore a version."""
        entry, _ = self.raw(step, "MOVE", f"/remote.php/dav/versions/{self.user}/versions/{fileid}/{revision}", None,
                            {"Destination": f"{self.base}/remote.php/dav/versions/{self.user}/restore/target"})
        return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", nargs="*", default=None, help="sections to run (V1 … V6); default all")
    args = parser.parse_args()
    want = lambda section: args.only is None or section in args.only  # noqa: E731
    instance = Instance(DEFAULT_DDEV)
    log: list[dict[str, Any]] = []
    admin = VClient(instance.base, "admin", instance.password, log)
    password = secrets.token_urlsafe(24)
    admin.call("setup", "DELETE", f"/ocs/v2.php/cloud/users/{PROBE_USER}")
    made = admin.call("setup", "POST", "/ocs/v2.php/cloud/users", form={"userid": PROBE_USER, "password": password})
    if made["status"] != 200:
        print(json.dumps(made, ensure_ascii=False, indent=1))
        return 2
    other = VClient(instance.base, PROBE_USER, password, log)
    fixture = FIXTURE.read_bytes()
    body = lambda tag: fixture + f"\n{tag}\n".encode()  # noqa: E731  distinct bytes per save
    facts: dict[str, Any] = {"fixtureSha256": sha(fixture)}
    made_files: list[str] = []
    shares: list[str] = []
    stamp = time.strftime("%H%M%S")

    def upload(name: str) -> dict[str, Any]:
        made_files.append(name)
        admin.raw("setup", "PUT", admin.dav_path(name), fixture, {"Content-Type": ODT})
        return admin.file("setup", name)

    held: dict[str, str] = {}

    def lock(name: str) -> str:
        entry, _ = admin.raw("LOCK", "LOCK", admin.dav_path(name), LOCKINFO,
                             {"Content-Type": "application/xml", "Timeout": "Second-300"})
        held[name] = entry["headers"].get("lock-token", "").strip("<>")
        return held[name]

    def put(step: str, name: str, data: bytes, etag: str | None = None, token: str | None = None,
            client: VClient | None = None) -> dict[str, Any]:
        headers = {"Content-Type": ODT}
        if etag:
            headers["If-Match"] = etag
        if token:
            headers["If"] = f"(<{token}>)"
        entry, _ = (client or admin).raw(step, "PUT", (client or admin).dav_path(name), data, headers)
        return {"status": entry["status"], "etag": entry["headers"].get("etag"), "sha256": sha(data)}

    try:
        # V1: host-like against plain, same timing
        if want("V1"):
            for way in ("host", "plain"):
                name = f"V1 {way} {stamp}.odt"
                start = upload(name)
                fid = start["fileid"]
                row: dict[str, Any] = {"afterUpload": start, "versionsAfterUpload": admin.versions(f"V1 {way}", fid)}
                token = lock(name) if way == "host" else None
                if way == "host":
                    time.sleep(1.2)  # so a LOCK that moved the mtime would show a different second
                    row["afterLock"] = admin.file("V1 host after LOCK", name)
                    row["versionsAfterLock"] = admin.versions("V1 host after LOCK", fid)
                etag = row.get("afterLock", start)["etag"]
                saves = []
                for n in (1, 2):
                    time.sleep(2.5)
                    saves.append(put(f"V1 {way} save {n}", name, body(f"V1 {way} {n}"),
                                     etag if way == "host" else None, token))
                    etag = saves[-1]["etag"]
                row["saves"] = saves
                row["current"] = admin.file(f"V1 {way} after saves", name)
                row["currentSha256"] = admin.content(f"V1 {way} after saves", name)
                row["versionsAfterSaves"] = admin.versions(f"V1 {way} after saves", fid)
                if way == "host":
                    admin.raw("V1 host UNLOCK", "UNLOCK", admin.dav_path(name), None, {"Lock-Token": f"<{token}>"})
                    time.sleep(1.2)
                    row["afterUnlock"] = admin.file("V1 host after UNLOCK", name)
                    row["versionsAfterUnlock"] = admin.versions("V1 host after UNLOCK", fid)
                facts[f"V1-{way}"] = row

        # V2: two saves inside one second, both ways
        if want("V2"):
            for way in ("host", "plain"):
                name = f"V2 {way} {stamp}.odt"
                start = upload(name)
                fid = start["fileid"]
                token = lock(name) if way == "host" else None
                etag = admin.file(f"V2 {way}", name)["etag"]
                time.sleep(2.5)
                first = put(f"V2 {way} save 1", name, body(f"V2 {way} 1"), etag if way == "host" else None, token)
                second = put(f"V2 {way} save 2", name, body(f"V2 {way} 2"),
                             first["etag"] if way == "host" else None, token)
                row = {"saves": [first, second], "current": admin.file(f"V2 {way} after", name),
                       "currentSha256": admin.content(f"V2 {way} after", name),
                       "versions": admin.versions(f"V2 {way} after", fid)}
                time.sleep(2.5)
                third = put(f"V2 {way} save 3", name, body(f"V2 {way} 3"),
                            row["current"]["etag"] if way == "host" else None, token)
                row["thirdSave"] = third
                row["versionsAfterThird"] = admin.versions(f"V2 {way} after third", fid)
                if token:
                    admin.raw(f"V2 {way} UNLOCK", "UNLOCK", admin.dav_path(name), None, {"Lock-Token": f"<{token}>"})
                facts[f"V2-{way}"] = row

        # V3: the holder's own restore, without the token, while the token lock is held
        if want("V3"):
            name = f"V3 還原 持有者 {stamp}.odt"
            fid = upload(name)["fileid"]
            token = lock(name)
            etag = admin.file("V3", name)["etag"]
            time.sleep(2.5)
            saved = put("V3 host save", name, body("V3 1"), etag, token)
            before = admin.file("V3 before restore", name)
            history = admin.versions("V3 before restore", fid)
            oldest = history[0]["revision"] if isinstance(history, list) and history else None
            restored = admin.restore("V3 restore (holder, no token)", fid, oldest) if oldest else None
            after = admin.file("V3 after restore", name)
            row = {"save": saved, "before": before, "versionsBefore": history, "restoredRevision": oldest,
                   "restoreStatus": restored and restored["status"], "restoreBody": restored and restored["body"],
                   "after": after, "currentSha256AfterRestore": admin.content("V3 after restore", name),
                   "versionsAfterRestore": admin.versions("V3 after restore", fid)}
            time.sleep(1.2)
            row["hostNextSave"] = put("V3 host save after restore", name, body("V3 2"), before["etag"], token)
            row["afterHostSave"] = admin.file("V3 after host save", name)
            row["currentSha256AfterHostSave"] = admin.content("V3 after host save", name)
            row["versionsAfterHostSave"] = admin.versions("V3 after host save", fid)
            admin.raw("V3 UNLOCK", "UNLOCK", admin.dav_path(name), None, {"Lock-Token": f"<{token}>"})
            facts["V3"] = row

        # V4 and V5 share one file (Nextcloud limits share creation to 20 per 10 minutes)
        if want("V4") or want("V5"):
            name = f"V4 還原 收件人 {stamp}.odt"
            fid = upload(name)["fileid"]
            entry = admin.call("setup", "POST", "/ocs/v2.php/apps/files_sharing/api/v1/shares", form={
                "path": "/" + name, "shareType": 0, "shareWith": PROBE_USER, "permissions": 3})
            data = json.loads(entry["body"])["ocs"]["data"]
            shares.append(str(data["id"]))
            target = data["file_target"].lstrip("/")
            time.sleep(2.5)
            put("V4 setup save 1", name, body("V4 1"))
            time.sleep(2.5)
            put("V4 setup save 2", name, body("V4 2"))
            history = other.versions("V4 recipient's view", fid)
            facts["V4-setup"] = {"recipientSeesVersions": history, "ownerSeesVersions": admin.versions("V4 owner", fid),
                                 "recipientFile": other.file("V4 recipient's view", target)}
            oldest = history[0]["revision"] if isinstance(history, list) and history else None

            if want("V4"):
                token = lock(name)
                before = admin.file("V4 before restore", name)
                restored = other.restore("V4 restore (recipient)", fid, oldest) if oldest else None
                after = admin.file("V4 after restore", name)
                facts["V4"] = {"before": before, "restoredRevision": oldest,
                               "restoreStatus": restored and restored["status"],
                               "restoreBody": restored and restored["body"], "after": after,
                               "currentSha256AfterRestore": admin.content("V4 after restore", name),
                               "versionsAfterRestore": admin.versions("V4 after restore", fid)}
                admin.raw("V4 UNLOCK", "UNLOCK", admin.dav_path(name), None, {"Lock-Token": f"<{token}>"})

            if want("V5"):
                history = admin.versions("V5 before", fid)
                oldest = history[0]["revision"] if isinstance(history, list) and history else None
                user_lock, _ = other.raw("V5 recipient user lock", "LOCK", other.dav_path(target), None,
                                         {"X-User-Lock": "1"})
                before = admin.file("V5 before restore", name)
                before_sha = admin.content("V5 before restore", name)
                restored = admin.restore("V5 restore (owner, recipient holds a user lock)", fid, oldest) if oldest else None
                after = admin.file("V5 after restore", name)
                facts["V5"] = {"userLockStatus": user_lock["status"], "before": before, "restoredRevision": oldest,
                               "restoreStatus": restored and restored["status"],
                               "restoreBody": restored and restored["body"], "after": after,
                               "currentSha256Before": before_sha,
                               "currentSha256AfterRestore": admin.content("V5 after restore", name),
                               "versionsAfterRestore": admin.versions("V5 after restore", fid)}
                other.raw("V5 recipient unlock", "UNLOCK", other.dav_path(target), None, {"X-User-Lock": "1"})

        # V6: a conflict copy's own history, and the original's
        if want("V6"):
            name = f"V6 原檔 {stamp}.odt"
            fid = upload(name)["fileid"]
            time.sleep(2.5)
            put("V6 save", name, body("V6 1"))
            original_before = admin.versions("V6 original before copy", fid)
            copy = f"V6 原檔 {stamp}（衝突副本）.odt"
            made_files.append(copy)
            entry, _ = admin.raw("V6 copy", "PUT", admin.dav_path(copy), body("V6 copy"),
                                 {"Content-Type": ODT, "If-None-Match": "*"})
            copied = admin.file("V6 copy", copy)
            facts["V6"] = {"copyStatus": entry["status"], "copyVersions": admin.versions("V6 copy", copied["fileid"]),
                           "originalBefore": original_before, "originalAfter": admin.versions("V6 original after", fid)}
        # V7: does If-Match catch someone else's write that lands in the same second with the same size?
        # Local storage's ETag is md5(mtime . ino . dev . size) (Local::calculateEtag), and V2 saw two
        # different same-size bodies written in one second share an ETag. The server-side stat is read
        # so the ETag's inputs are measured, not inferred. Control: the other write one byte longer.
        if want("V7"):
            name = f"V7-ifmatch-{stamp}.odt"
            upload(name)
            entry = admin.call("setup", "POST", "/ocs/v2.php/apps/files_sharing/api/v1/shares", form={
                "path": "/" + name, "shareType": 0, "shareWith": PROBE_USER, "permissions": 3})
            data = json.loads(entry["body"])["ocs"]["data"]
            shares.append(str(data["id"]))
            target = data["file_target"].lstrip("/")

            def stat() -> str:
                done = subprocess.run(["ddev", "exec", "stat", "-c", "%i %Y %s", f"nextcloud/data/admin/files/{name}"],
                                      cwd=DEFAULT_DDEV, capture_output=True, text=True)
                return done.stdout.strip() or done.stderr.strip()

            trials = []
            for n in range(12):
                control = n >= 8
                mine = put(f"V7 {n} ours", name, body(f"V7 {n:02d} ours"))
                ours_stat = stat()
                theirs = put(f"V7 {n} theirs", target, body(f"V7 {n:02d} them") + (b"!" if control else b""),
                             client=other)
                their_stat = stat()
                again = put(f"V7 {n} ours again (If-Match from our first)", name, body(f"V7 {n:02d} late"),
                            mine["etag"])
                history = admin.versions(f"V7 {n} history", data["item_source"] and str(data["item_source"]))
                trials.append({"control": control, "ours": mine, "oursStat": ours_stat, "theirs": theirs,
                               "theirStat": their_stat, "sameEtag": mine["etag"] == theirs["etag"],
                               "conditional": again, "survivor": admin.content(f"V7 {n} survivor", name),
                               "theirsInHistory": isinstance(history, list)
                               and any(v["sha256"] == theirs["sha256"] for v in history)})
                time.sleep(0.3)
            # Is an overwritten body still in the history after one more save, in a later second?
            time.sleep(1.5)
            last = trials[-1]
            put("V7 one more save", name, body("V7 one more"))
            history = admin.versions("V7 history after one more save", str(data["item_source"]))
            facts["V7"] = trials
            facts["V7-after-one-more-save"] = {
                "lastTrialTheirsSha256": last["theirs"]["sha256"],
                "stillInHistory": isinstance(history, list)
                and any(v["sha256"] == last["theirs"]["sha256"] for v in history)}
    finally:
        for share_id in shares:
            admin.call("cleanup", "DELETE", f"/ocs/v2.php/apps/files_sharing/api/v1/shares/{share_id}")
        admin.call("cleanup", "DELETE", f"/ocs/v2.php/cloud/users/{PROBE_USER}")
        for name in made_files:
            if name in held:  # an exception can skip a section's UNLOCK; a locked file refuses DELETE
                admin.raw("cleanup", "UNLOCK", admin.dav_path(name), None, {"Lock-Token": f"<{held[name]}>"})
            admin.raw("cleanup", "DELETE", admin.dav_path(name))

    def setting(*argv: str) -> str:
        done = subprocess.run(["ddev", "occ", *argv], cwd=DEFAULT_DDEV, capture_output=True, text=True)
        return done.stdout.strip() if done.returncode == 0 else "unset"

    report = {
        "probe": "probe_m3_versions.py", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "instance": instance.base,
        "settings": {"versions_retention_obligation": setting("config:system:get", "versions_retention_obligation"),
                     "backgroundjobs_mode": setting("config:app:get", "core", "backgroundjobs_mode"),
                     "files_lock lock_timeout": setting("config:app:get", "files_lock", "lock_timeout")},
        "sections": args.only or "all", "facts": facts, "log": log,
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"versions-{report['at'].replace(':', '')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
