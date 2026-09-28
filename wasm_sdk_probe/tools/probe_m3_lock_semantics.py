#!/usr/bin/env python3
"""M3 locks, step 0: what this Nextcloud answers, over HTTP only (no browser).

The lock-and-permission design for the `litecore` host rests on server behaviour
that was read from files_lock's source but never measured. This probe measures it
on the `litecore` ddev instance and keeps every raw status and header:

  L1  user lock, taken through OCS (lockType 0) and through DAV LOCK + X-User-Lock:
      does it change the file's ETag? does
      it block its own holder? what does another user's PUT get? does unlock
      change the ETag again?
  L3  token lock (RFC 4918 LOCK with a Timeout): PUT without the token, with it,
      refresh, expiry after the timeout, UNLOCK.
  L5  a token lock as another user sees it; the same user's second window; whether
      the file owner can remove it (Files' unlock) and what the holder's refresh gets then.
  L6  whether a token refresh or expiry moves the ETag; a PUT that carries an expired
      or removed token.
  L4  a user lock held by someone else: what our lock attempt and our PUT get,
      and whether the file's owner can remove it.
  L7  a share recipient's refused OCS unlock of our token lock: does it still move
      the ETag (K12 rests on this, read from LockService::unlockFile only)? the
      refusal's body carries the lock's token — can the recipient PUT with it?
  L8  finding 101's minimal repro: Timeout Second-20, refresh at 10 s with Second-20,
      token-less PUT at 22 s; beside it the host's fix (refresh with Second-30) as
      the control that the same PUT is refused while the lock is alive.
  P1  read-only share of a file, and of a folder: the recipient's PUT, and a new
      file next to it (where a conflict copy would go).
  P2  quota exceeded: the PUT status.

A second user `lcprobe` is created for the run and deleted at the end, with every
file and share the probe made.

    python3 wasm_sdk_probe/tools/probe_m3_lock_semantics.py
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import secrets
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_skeleton_open import DEFAULT_DDEV, FIXTURE, Instance  # noqa: E402
from probe_m3_gate0_coep import MKCERT_CA  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-locks"
ODT = "application/vnd.oasis.opendocument.text"
PROBE_USER = "lcprobe"
KEEP_HEADERS = {"etag", "oc-etag", "oc-fileid", "lock-token", "content-type", "www-authenticate", "dav"}
LOCKINFO = (b'<?xml version="1.0" encoding="utf-8"?><d:lockinfo xmlns:d="DAV:">'
            b"<d:lockscope><d:exclusive/></d:lockscope><d:locktype><d:write/></d:locktype>"
            b"<d:owner>litecore probe</d:owner></d:lockinfo>")
ETAG_PROPFIND = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns" '
                 b'xmlns:nc="http://nextcloud.org/ns"><d:prop><d:getetag/><oc:fileid/><oc:permissions/>'
                 b"<nc:lock/><nc:lock-owner/><nc:lock-owner-type/><nc:lock-time/><nc:lock-timeout/>"
                 b"<nc:share-permissions/></d:prop></d:propfind>")


class Client:
    def __init__(self, base: str, user: str, password: str, log: list[dict[str, Any]]):
        self.base, self.user, self.log = base, user, log
        self.auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        self.tls = ssl.create_default_context(cafile=str(MKCERT_CA))

    def dav_path(self, name: str) -> str:
        return f"/remote.php/dav/files/{self.user}/" + urllib.parse.quote(name)

    def call(self, step: str, method: str, path: str, body: bytes | None = None,
             headers: dict[str, str] | None = None, form: dict[str, Any] | None = None) -> dict[str, Any]:
        sent = {"X-Requested-With": "XMLHttpRequest", **(headers or {})}
        if path.startswith("/ocs/"):
            sent.update({"OCS-APIRequest": "true", "Accept": "application/json"})
        if form is not None:
            body = urllib.parse.urlencode(form).encode()
            sent["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(self.base + path, data=body, method=method, headers=sent)
        request.add_header("Authorization", self.auth)
        try:
            with urllib.request.urlopen(request, context=self.tls, timeout=60) as response:
                status, got, raw = response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            status, got, raw = error.code, error.headers, error.read()
        entry = {
            "step": step, "actor": self.user, "method": method, "path": urllib.parse.unquote(path),
            "sent": {k: v for k, v in sent.items() if k not in {"OCS-APIRequest", "Accept", "X-Requested-With"}},
            "status": status,
            "headers": {k.lower(): v for k, v in got.items() if k.lower() in KEEP_HEADERS},
            "body": raw[:1500].decode("utf-8", "replace") if raw and not raw.startswith(b"PK") else None,
        }
        self.log.append(entry)
        return entry

    def props(self, step: str, name: str) -> dict[str, Any]:
        entry = self.call(step, "PROPFIND", self.dav_path(name), ETAG_PROPFIND,
                          {"Depth": "0", "Content-Type": "application/xml"})
        body = entry["body"] or ""
        # XML-escaped in the body (&quot;); unescaped, it is what If-Match takes.
        grab = lambda tag: (html.unescape(body.split(f"<{tag}>", 1)[1].split(f"</{tag}>", 1)[0])  # noqa: E731
                            if f"<{tag}>" in body else None)
        return {"etag": grab("d:getetag"), "fileid": grab("oc:fileid"), "permissions": grab("oc:permissions"),
                "lock": grab("nc:lock"), "lockOwner": grab("nc:lock-owner"),
                "lockOwnerType": grab("nc:lock-owner-type"), "lockTimeout": grab("nc:lock-timeout"),
                "sharePermissions": grab("nc:share-permissions")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", nargs="*", default=None,
                        help="sections to run (L1 L3 L4 L5 L6 L7 L8 P1 P2); default all. "
                             "Nextcloud rate-limits share creation (429), and a full run makes 8.")
    args = parser.parse_args()
    want = lambda section: args.only is None or section in args.only  # noqa: E731
    instance = Instance(DEFAULT_DDEV)
    log: list[dict[str, Any]] = []
    admin = Client(instance.base, "admin", instance.password, log)
    password = secrets.token_urlsafe(24)
    admin.call("setup", "DELETE", f"/ocs/v2.php/cloud/users/{PROBE_USER}")
    made = admin.call("setup", "POST", "/ocs/v2.php/cloud/users", form={"userid": PROBE_USER, "password": password})
    if made["status"] != 200:
        print(json.dumps(made, ensure_ascii=False, indent=1))
        return 2
    other = Client(instance.base, PROBE_USER, password, log)
    fixture = FIXTURE.read_bytes()
    facts: dict[str, Any] = {}
    shares: list[str] = []
    stamp = time.strftime("%H%M%S")

    def upload(name: str) -> str:
        admin.call("setup", "PUT", admin.dav_path(name), fixture, {"Content-Type": ODT})
        return admin.props("setup", name)["fileid"]

    def share(path: str, permissions: int) -> str:
        entry = admin.call("setup", "POST", "/ocs/v2.php/apps/files_sharing/api/v1/shares", form={
            "path": path, "shareType": 0, "shareWith": PROBE_USER, "permissions": permissions})
        data = json.loads(entry["body"])["ocs"]["data"]
        shares.append(str(data["id"]))
        return data["file_target"].lstrip("/")

    def lock_url(fileid: str) -> str:
        return f"/ocs/v2.php/apps/files_lock/lock/{fileid}"

    try:
        # L1: user lock, taken through OCS and through DAV LOCK + X-User-Lock
        if want("L1"):
            for via in ("ocs", "dav"):
                name = f"L1 使用者鎖 {via} {stamp}.odt"
                fid = upload(name)
                target = share("/" + name, 3)

                def take(client: Client, step: str, path: str) -> dict[str, Any]:
                    if via == "ocs":
                        return client.call(step, "PUT", lock_url(fid), form={"lockType": 0})
                    return client.call(step, "LOCK", client.dav_path(path), None, {"X-User-Lock": "1"})

                e0 = admin.props(f"L1 {via}", name)["etag"]
                locked = take(admin, f"L1 {via} lock", name)
                after = admin.props(f"L1 {via} after lock", name)
                seen = other.props(f"L1 {via} seen by other", target)
                own = admin.call(f"L1 {via} holder PUT", "PUT", admin.dav_path(name), fixture,
                                 {"Content-Type": ODT, "If-Match": after["etag"]})
                e2 = admin.props(f"L1 {via}", name)["etag"]
                theirs = other.call(f"L1 {via} other PUT", "PUT", other.dav_path(target), fixture,
                                    {"Content-Type": ODT, "If-Match": e2})
                theirs_lock = take(other, f"L1 {via} other lock", target)
                again = take(admin, f"L1 {via} holder locks again", name)
                e3 = admin.props(f"L1 {via} after relock", name)["etag"]
                if via == "ocs":
                    unlocked = admin.call(f"L1 {via} unlock", "DELETE", lock_url(fid), form={"lockType": 0})
                else:
                    unlocked = admin.call(f"L1 {via} unlock", "UNLOCK", admin.dav_path(name), None, {"X-User-Lock": "1"})
                e4 = admin.props(f"L1 {via} after unlock", name)["etag"]
                facts[f"L1-{via}"] = {
                    "lockStatus": locked["status"], "lockChangesEtag": e0 != after["etag"],
                    "propfindAfterLock": after, "seenByOther": seen,
                    "holderPutStatus": own["status"], "otherPutStatus": theirs["status"],
                    "otherLockStatus": theirs_lock["status"], "relockStatus": again["status"],
                    "relockChangesEtag": e2 != e3, "unlockStatus": unlocked["status"],
                    "unlockChangesEtag": e3 != e4}

        # L3: token lock, with a short timeout
        if want("L3"):
            name = f"L3 token 鎖 {stamp}.odt"
            upload(name)
            target = share("/" + name, 3)
            e0 = admin.props("L3", name)["etag"]
            lock = admin.call("L3 LOCK", "LOCK", admin.dav_path(name), LOCKINFO,
                              {"Content-Type": "application/xml", "Timeout": "Second-8"})
            token = lock["headers"].get("lock-token", "")
            e1 = admin.props("L3 after LOCK", name)["etag"]
            bare = admin.call("L3 holder PUT without token", "PUT", admin.dav_path(name), fixture,
                              {"Content-Type": ODT, "If-Match": e1})
            tagged = admin.call("L3 holder PUT with token", "PUT", admin.dav_path(name), fixture,
                                {"Content-Type": ODT, "If-Match": e1, "If": f"({token})"})
            refresh = admin.call("L3 refresh", "LOCK", admin.dav_path(name), None,
                                 {"Timeout": "Second-8", "If": f"({token})"})
            theirs = other.call("L3 other PUT", "PUT", other.dav_path(target), fixture, {"Content-Type": ODT})
            time.sleep(12)
            expired = admin.call("L3 PUT after timeout, no token", "PUT", admin.dav_path(name), fixture,
                                 {"Content-Type": ODT})
            again = admin.call("L3 LOCK 2", "LOCK", admin.dav_path(name), LOCKINFO,
                               {"Content-Type": "application/xml", "Timeout": "Second-60"})
            released = admin.call("L3 UNLOCK", "UNLOCK", admin.dav_path(name), None,
                                  {"Lock-Token": again["headers"].get("lock-token", "")})
            free = admin.call("L3 PUT after UNLOCK, no token", "PUT", admin.dav_path(name), fixture,
                              {"Content-Type": ODT})
            facts["L3"] = {"lockStatus": lock["status"], "lockToken": bool(token), "lockChangesEtag": e0 != e1,
                           "holderPutWithoutToken": bare["status"], "holderPutWithToken": tagged["status"],
                           "refreshStatus": refresh["status"], "otherPutStatus": theirs["status"],
                           "putAfterTimeout": expired["status"], "unlockStatus": released["status"],
                           "putAfterUnlock": free["status"]}

        # L5: a token lock as others see it; a second window of the same user; the owner's unlock
        if want("L5"):
            name = f"L5 token 鎖 旁觀 {stamp}.odt"
            fid = upload(name)
            target = share("/" + name, 3)
            lock = admin.call("L5 LOCK", "LOCK", admin.dav_path(name), LOCKINFO,
                              {"Content-Type": "application/xml", "Timeout": "Second-300"})
            token = lock["headers"].get("lock-token", "")
            seen = other.props("L5 seen by other", target)
            mine = admin.props("L5 seen by holder", name)
            second = admin.call("L5 same user second LOCK", "LOCK", admin.dav_path(name), LOCKINFO,
                                {"Content-Type": "application/xml", "Timeout": "Second-300"})
            second_user = admin.call("L5 same user X-User-Lock", "LOCK", admin.dav_path(name), None, {"X-User-Lock": "1"})
            theirs = other.call("L5 other token LOCK", "LOCK", other.dav_path(target), LOCKINFO,
                                {"Content-Type": "application/xml", "Timeout": "Second-300"})
            by_other = other.call("L5 other (not owner) OCS unlock", "DELETE", lock_url(fid), form={"lockType": 0})
            by_owner = admin.call("L5 file owner OCS unlock (no token)", "DELETE", lock_url(fid), form={"lockType": 0})
            after = admin.call("L5 PUT after owner unlock, no token", "PUT", admin.dav_path(name), fixture,
                               {"Content-Type": ODT})
            stale = admin.call("L5 refresh with the removed token", "LOCK", admin.dav_path(name), None,
                               {"Timeout": "Second-300", "If": f"({token})"})
            facts["L5"] = {"seenByOther": seen, "seenByHolder": mine, "sameUserSecondLock": second["status"],
                           "sameUserUserLock": second_user["status"], "otherTokenLock": theirs["status"],
                           "nonOwnerUnlock": by_other["status"], "fileOwnerUnlock": by_owner["status"],
                           "putAfterOwnerUnlock": after["status"], "refreshWithRemovedToken": stale["status"]}

        # L6: what a heartbeat does to the version, and a save that still carries a dead token
        if want("L6"):
            name = f"L6 token 過期 {stamp}.odt"
            fid = upload(name)
            lock = admin.call("L6 LOCK", "LOCK", admin.dav_path(name), LOCKINFO,
                              {"Content-Type": "application/xml", "Timeout": "Second-6"})
            token = lock["headers"].get("lock-token", "")
            e1 = admin.props("L6 after LOCK", name)["etag"]
            refresh = admin.call("L6 refresh", "LOCK", admin.dav_path(name), None,
                                 {"Timeout": "Second-6", "If": f"({token})"})
            e2 = admin.props("L6 after refresh", name)["etag"]
            time.sleep(10)
            e3 = admin.props("L6 after expiry", name)["etag"]
            expired = admin.call("L6 PUT with the expired token", "PUT", admin.dav_path(name), fixture,
                                 {"Content-Type": ODT, "If-Match": e3, "If": f"({token})"})
            e4 = admin.props("L6", name)["etag"]
            lock = admin.call("L6 LOCK 2", "LOCK", admin.dav_path(name), LOCKINFO,
                              {"Content-Type": "application/xml", "Timeout": "Second-300"})
            token2 = lock["headers"].get("lock-token", "")
            e5 = admin.props("L6 after LOCK 2", name)["etag"]
            admin.call("L6 file owner unlock", "DELETE", lock_url(fid), form={"lockType": 0})
            e6 = admin.props("L6 after owner unlock", name)["etag"]
            removed = admin.call("L6 PUT with the removed token", "PUT", admin.dav_path(name), fixture,
                                 {"Content-Type": ODT, "If-Match": e6, "If": f"({token2})"})
            plain = admin.call("L6 PUT with If-Match only", "PUT", admin.dav_path(name), fixture,
                               {"Content-Type": ODT, "If-Match": e6})
            facts["L6"] = {"refreshStatus": refresh["status"], "refreshChangesEtag": e1 != e2,
                           "expiryChangesEtag": e2 != e3, "putWithExpiredToken": expired["status"],
                           "putWithExpiredTokenChangedEtag": e3 != e4,
                           "ownerUnlockChangesEtag": e5 != e6, "putWithRemovedToken": removed["status"],
                           "putWithIfMatchOnlyAfter": plain["status"]}

        # L4: a user lock held by someone else
        if want("L4"):
            name = f"L4 別人的鎖 {stamp}.odt"
            fid = upload(name)
            share("/" + name, 3)
            theirs = other.call("L4 other lock", "PUT", lock_url(fid), form={"lockType": 0})
            ours = admin.call("L4 our lock", "PUT", lock_url(fid), form={"lockType": 0})
            ours_dav = admin.call("L4 our X-User-Lock LOCK", "LOCK", admin.dav_path(name), None, {"X-User-Lock": "1"})
            ours_token = admin.call("L4 our token LOCK", "LOCK", admin.dav_path(name), LOCKINFO,
                                    {"Content-Type": "application/xml", "Timeout": "Second-60"})
            put = admin.call("L4 our PUT", "PUT", admin.dav_path(name), fixture, {"Content-Type": ODT})
            seen = admin.props("L4 seen by owner", name)
            broken = admin.call("L4 file owner unlocks", "DELETE", lock_url(fid), form={"lockType": 0})
            facts["L4"] = {"otherLockStatus": theirs["status"], "ourLockStatus": ours["status"], "ourDavUserLockStatus": ours_dav["status"],
                           "ourTokenLockStatus": ours_token["status"], "ourPutStatus": put["status"],
                           "seenByOwner": seen, "ownerUnlockStatus": broken["status"]}

        # L7: someone else's refused unlock of our token lock
        if want("L7"):
            name = f"L7 被拒絕的解鎖 {stamp}.odt"
            fid = upload(name)
            target = share("/" + name, 3)
            lock = admin.call("L7 LOCK", "LOCK", admin.dav_path(name), LOCKINFO,
                              {"Content-Type": "application/xml", "Timeout": "Second-300"})
            token = lock["headers"].get("lock-token", "").strip("<>")
            before = admin.props("L7 before", name)
            refused = other.call("L7 recipient OCS unlock", "DELETE", lock_url(fid), form={"lockType": 0})
            after = admin.props("L7 after refused unlock", name)
            stale = admin.call("L7 holder PUT, token + pre-refusal If-Match", "PUT", admin.dav_path(name), fixture,
                               {"Content-Type": ODT, "If-Match": before["etag"], "If": f"(<{token}>)"})
            discovery = other.call("L7 recipient PROPFIND lockdiscovery", "PROPFIND", other.dav_path(target),
                                   b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:lockdiscovery/>'
                                   b"</d:prop></d:propfind>", {"Depth": "0", "Content-Type": "application/xml"})
            # distinct from the fixture, so the readback tells whose bytes the file holds
            intruder = f"L7 recipient bytes {stamp}".encode()
            bare = other.call("L7 recipient PUT, no token", "PUT", other.dav_path(target), intruder, {"Content-Type": ODT})
            borrowed = other.call("L7 recipient PUT with the holder's token", "PUT", other.dav_path(target), intruder,
                                  {"Content-Type": ODT, "If": f"(<{token}>)"})
            readback = admin.call("L7 holder GET", "GET", admin.dav_path(name))
            end = admin.props("L7 end", name)
            admin.call("L7 UNLOCK", "UNLOCK", admin.dav_path(name), None, {"Lock-Token": f"<{token}>"})
            facts["L7"] = {"refusedUnlockStatus": refused["status"],
                           # the header's token is opaquelocktoken:<uuid>; the OCS body has the bare uuid
                           "refusalBodyCarriesToken": bool(token) and token.split(":", 1)[-1] in (refused["body"] or ""),
                           "refusedUnlockChangesEtag": before["etag"] != after["etag"],
                           "lockHeldAfterRefusal": after["lock"], "holderPutWithStaleEtag": stale["status"],
                           "recipientPutNoToken": bare["status"], "recipientPutWithHoldersToken": borrowed["status"],
                           "etagMovedByRecipientPuts": after["etag"] != end["etag"],
                           "fileHoldsRecipientBytes": readback["body"] == intruder.decode(),
                           "recipientLockdiscoveryStatus": discovery["status"],
                           "recipientLockdiscoveryCarriesToken": bool(token) and token.split(":", 1)[-1] in (discovery["body"] or "")}

        # L8: finding 101, minimal; B is the host's fix and the control for A's PUT
        if want("L8"):
            names = {arm: f"L8 續約 {arm} {stamp}.odt" for arm in ("A", "B")}
            for arm in names:
                upload(names[arm])
            start, tokens, timeline = time.monotonic(), {}, {}

            def at(second: float) -> float:
                time.sleep(max(0.0, start + second - time.monotonic()))
                return round(time.monotonic() - start, 2)

            for arm, name in names.items():
                lock = admin.call(f"L8 {arm} LOCK Second-20", "LOCK", admin.dav_path(name), LOCKINFO,
                                  {"Content-Type": "application/xml", "Timeout": "Second-20"})
                tokens[arm] = lock["headers"].get("lock-token", "").strip("<>")
                timeline[arm] = {"lock": [round(time.monotonic() - start, 2), lock["status"]]}
            at(10)
            for arm, name in names.items():
                asked = {"A": "Second-20", "B": f"Second-{int(time.monotonic() - start) + 20}"}[arm]
                refresh = admin.call(f"L8 {arm} refresh {asked}", "LOCK", admin.dav_path(name), None,
                                     {"Timeout": asked, "If": f"(<{tokens[arm]}>)"})
                timeline[arm]["refresh"] = [round(time.monotonic() - start, 2), asked, refresh["status"]]
            at(22)
            for arm, name in names.items():
                put = admin.call(f"L8 {arm} PUT at 22 s, no token", "PUT", admin.dav_path(name), fixture,
                                 {"Content-Type": ODT})
                timeline[arm]["put"] = [round(time.monotonic() - start, 2), put["status"]]
                timeline[arm]["lockAfter"] = admin.props(f"L8 {arm} after PUT", name)["lock"]
                admin.call(f"L8 {arm} UNLOCK", "UNLOCK", admin.dav_path(name), None, {"Lock-Token": f"<{tokens[arm]}>"})
            facts["L8"] = {"timeline": timeline,
                           "refreshDidNotExtend": timeline["A"]["put"][1] in (200, 201, 204),
                           "controlRefusedWhileAlive": timeline["B"]["put"][1] == 423}

        # P1: read-only share of a file, and of a folder
        if want("P1"):
            name = f"P1 唯讀 {stamp}.odt"
            upload(name)
            target = share("/" + name, 1)
            seen = other.props("P1 seen by recipient", target)
            put = other.call("P1 recipient PUT", "PUT", other.dav_path(target), fixture,
                             {"Content-Type": ODT, "If-Match": seen["etag"] or "*"})
            beside = other.call("P1 recipient new file beside", "PUT",
                                other.dav_path(f"P1 副本 {stamp}.odt"), fixture,
                                {"Content-Type": ODT, "If-None-Match": "*"})
            folder = f"P1 唯讀資料夾 {stamp}"
            admin.call("setup", "MKCOL", admin.dav_path(folder))
            upload(f"{folder}/inner.odt")
            ftarget = share("/" + folder, 1)
            inner_put = other.call("P1 recipient PUT in folder", "PUT", other.dav_path(f"{ftarget}/inner.odt"),
                                   fixture, {"Content-Type": ODT})
            inner_new = other.call("P1 recipient new file in folder", "PUT",
                                   other.dav_path(f"{ftarget}/copy.odt"), fixture,
                                   {"Content-Type": ODT, "If-None-Match": "*"})
            facts["P1"] = {"recipientProps": seen, "filePutStatus": put["status"], "besideStatus": beside["status"],
                           "folderFilePutStatus": inner_put["status"], "folderNewFileStatus": inner_new["status"]}

        # P2: quota
        if want("P2"):
            admin.call("setup", "PUT", f"/ocs/v2.php/cloud/users/{PROBE_USER}", form={"key": "quota", "value": "100 KB"})
            big = other.call("P2 PUT over quota", "PUT", other.dav_path(f"P2 {stamp}.bin"), secrets.token_bytes(300_000),
                             {"Content-Type": "application/octet-stream"})
            facts["P2"] = {"overQuotaStatus": big["status"]}
    finally:
        for share_id in shares:
            admin.call("cleanup", "DELETE", f"/ocs/v2.php/apps/files_sharing/api/v1/shares/{share_id}")
        admin.call("cleanup", "DELETE", f"/ocs/v2.php/cloud/users/{PROBE_USER}")
        for entry in [e for e in log if e["actor"] == "admin" and e["step"] == "setup"
                      and e["method"] in {"PUT", "MKCOL"} and e["path"].startswith("/remote.php/")]:
            top = entry["path"].split("/remote.php/dav/files/admin/", 1)[1].split("/", 1)[0]
            admin.call("cleanup", "DELETE", admin.dav_path(top))

    config = subprocess.run(["ddev", "occ", "config:app:get", "files_lock", "lock_timeout"], cwd=DEFAULT_DDEV,
                            capture_output=True, text=True)
    report = {
        "probe": "probe_m3_lock_semantics.py", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "instance": instance.base,
        "filesLockTimeoutSetting": config.stdout.strip() if config.returncode == 0 else "unset (app default -1)",
        "sections": args.only or "all", "facts": facts, "log": log,
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"semantics-{report['at'].replace(':', '')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(facts, ensure_ascii=False, indent=1))
    print(out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
