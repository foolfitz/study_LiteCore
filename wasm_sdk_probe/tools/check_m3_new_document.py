#!/usr/bin/env python3
"""SPEC-M3-new-document section 4: "+ New -> New document" in Files, on the M3 host.

Two user settings (arms), both browsers, a fresh login each, against the
`litecore` dev instance.  The admin's own language and locale are switched per
arm (`occ user:setting`) and restored afterwards to what was read before.

  TW   core/lang zh_TW, no locale     -> en-US_zh-TW_A4.odt      (the owner's shape)
  EN   core/lang en, locale en_US     -> en-US_zh-TW_Letter.odt

Per arm and browser: Files -> "+ New" -> the litecore entry -> the name dialog
(typed) -> submit -> core opens the new file through the default action -> the
editor -> click the first line -> REAL KEYS type the marker -> toolbar save ->
back to Files, open the same row again -> read.  The server side is WebDAV and
OCS; the saved file's styles.xml is read with the generator's own reader.

  check_m3_new_document.py --label shakedown|counted [--arms TW,EN] [--browsers chrome,firefox]
  check_m3_new_document.py --control              N1's red case: the creator list on the installed app (run on 0.2.18)
  check_m3_new_document.py --red-corrupt          N7(b): hide blank/MANIFEST.json, create, expect 403 and no file; restore
  check_m3_new_document.py --score REPORT.json
  check_m3_new_document.py --red-cases REPORT.json

Never run two M3 runners at once.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import re
import signal
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_new_document_templates as gen  # noqa: E402
from check_m3_locks import HOST_DONE, LockChrome, login  # noqa: E402
from check_m3_production_ui import GEN, HOST, click, press, quiet, save_and_settle, state  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
from check_new_document_choice import LOCALES, nextcloud_languages, php_choose  # noqa: E402
from odt_paragraphs import paragraph_texts_from_xml  # noqa: E402
from probe_m3_gate0_coep import firefox_profile, sha256_file, utc_now, wait_until  # noqa: E402
from probe_m3_lock_semantics import Client  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "new-document"
SCRATCH = PROJECT / "build" / "scratch-m3-new-document"   # snap Firefox cannot see /tmp
ODT = "application/vnd.oasis.opendocument.text"
ROUTE = "/e2-editor.html"
MARK = "zqx"
OTHER = "lcprobe"
RO_FOLDER = "新文件 唯讀資料夾"
# The arms run in their own folder, not the root: the owner's root holds a
# Readme.md that the `text` app edits in place at the top of the list, and its
# conflict modal (「檔案已被覆寫。無法自動儲存…」) swallowed the name dialog's
# submit in the first full shakedown (TW/chrome, 2026-10-14 03:23Z).
FOLDER = "新文件 測試資料夾"
BOTH = ("chrome", "firefox")
ARMS = {
    "TW": {"lang": "zh_TW", "locale": None, "file": "en-US_zh-TW_A4.odt", "paper": "A4"},
    "EN": {"lang": "en", "locale": "en_US", "file": "en-US_zh-TW_Letter.odt", "paper": "Letter"},
}
# The first line of a blank page: 2 cm margins, 12 pt text, so its centre is about
# 23 mm from the top.  As a fraction of #paper (POINT_AT) that depends on the
# paper: 0.075 of a Letter page is 21 mm, inside the margin, and the engine
# refuses it (EDITOR_CARET_NOT_PLACED, first full shakedown).  x well inside.
FIRST_LINE_MM = 23.0
FIRST_LINE_X = "0.3"


def first_line(paper: str | None) -> tuple[str, str]:
    height = gen.PAPER_MM.get(paper or "A4", gen.PAPER_MM["A4"])[1]
    return (FIRST_LINE_X, f"{FIRST_LINE_MM / height:.4f}")

# Bindings for a counted run (spec section 4), written before it.  Bound
# 2026-10-15 (task 10-15c P3, spec 7.5's rule set) to host 0.2.23 for the
# batched count of 0.2.13-0.2.23; was 0.2.19 (afbaf3c), the host the committed
# reports under findings/evidence/new-document/ ran on.  The blank manifest is
# unchanged between the two hosts (git diff afbaf3c..2ccf1a9 touches only
# appinfo/info.xml and templates/editor.php).
# Re-bound 2026-10-15 to host 0.2.24 (finding 145): git diff 2ccf1a9..1479e56 touches only appinfo/info.xml, so
# the blank manifest is unchanged; the engine package and the page moved (shell v73).
# Re-bound 2026-10-17 to host 0.2.26: git diff 1479e56..3c01876 touches only appinfo/info.xml and
# templates/editor.php, so the blank manifest is unchanged; the engine package and the page moved (v21, shell v74).
HOST_COMMIT: str | None = "a97724f302ddc7eb7180a4d3fd6d4863bfd6952d"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was 3c01876; 0.2.26; was 1479e56 (0.2.24), 2ccf1a9 (0.2.23), afbaf3c (0.2.19)
HOST_VERSION: str | None = "0.2.44"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was 0.2.26; was 0.2.24, 0.2.23, 0.2.19
MANIFEST_SHA256: str | None = "e5cdb8e2f0311cc10ad543f918906144e73015352304385719b5f85bfd97eb04"
# The engine the count runs on: the host's engine/MANIFEST.json buildId and its
# declared e2-editor-app.js sha256.  None until the count binds them (review
# 2026-10-14, Q3): a strict run on any host but DELTA_HOST_VERSION then reads
# "binding not written" -- the count never inherits 0.2.19's engine clause.
# Written 2026-10-15: host 0.2.23's package (engine v20, shell v72); was None.
ENGINE_BUILD_ID: str | None = "dacdfa20fd4ff1ea"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was f5f0df762e1855f2; 0.2.26 (v21, shell v74); was d3cd39bb (0.2.24, finding 145), c3c22d92 (0.2.23)
PAGE_SHA256: str | None = "3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was 605cf24b3dff5a2d; 0.2.26; was 901dd6a6 (0.2.24), ccb67a52 (0.2.23)
# N9 as 0.2.19's acceptance: "0.2.19 changed only the host" -- the engine
# package and page are 0.2.18's (host 96a87d8) and the host diff since 96a87d8
# is within ALLOWED_CHANGED.  These three clauses are evaluated ONLY on a report
# whose host is DELTA_HOST_VERSION; they are frozen with it.  Do not move the
# CONTROL_* values to a later host: with CONTROL_HOST_COMMIT at HEAD the diff is
# empty by construction and "unchanged since 0.2.18" would silently become
# "equals whatever is installed" (both review seats, 2026-10-14).
DELTA_HOST_VERSION = "0.2.19"
CONTROL_BUILD_ID = "d6d04880f56e31da"
CONTROL_PAGE_SHA256 = "b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678"
CONTROL_HOST_COMMIT = "96a87d8"
ALLOWED_CHANGED = ("appinfo/info.xml", "lib/AppInfo/Application.php", "lib/Listener/", "lib/Template/", "blank/", "l10n/")

CREATORS_API = "/ocs/v2.php/apps/files/api/v1/templates"
CREATE_API = "/ocs/v2.php/apps/files/api/v1/templates/create"
NEW_ENTRY = '[data-cy-upload-picker-menu-entry^="template-new-litecore-"]'
NEW_BUTTON = "[data-cy-upload-picker] button"
DIALOG_INPUT = "[data-cy-files-new-node-dialog-input]"
DIALOG_SUBMIT = "[data-cy-files-new-node-dialog-submit]"

CLICK_ANY = """(() => { const e = document.querySelector(ARG); if (!e) return false;
  const b = e.matches('button') ? e : (e.querySelector('button') || e); b.click(); return true; })()"""
INPUT_OF = """(() => { const e = document.querySelector(ARG); if (!e) return null;
  const i = e.matches('input') ? e : e.querySelector('input'); if (!i) return null; i.focus(); i.select();
  return { value: i.value, id: i.id }; })()"""
READ_INPUT = """(() => { const e = document.querySelector(ARG); if (!e) return null;
  const i = e.matches('input') ? e : e.querySelector('input'); return i ? i.value : null; })()"""
A11Y = """(() => { const d = document.querySelector('#a11y-doc'), p = document.querySelector('#a11y-para');
  return { offers: d ? d.dataset.offers : null, text: p ? p.textContent : null,
           reason: p ? p.dataset.reason : null, deferred: p ? p.dataset.deferredToStructure : null }; })()"""
PICKER_TILES = """(() => { const f = document.querySelector('form.templates-picker__form'); if (!f) return null;
  const inputs = [...f.querySelectorAll('input[type=radio]')];
  return { tiles: inputs.length, checked: inputs.filter((i) => i.checked).map((i) => i.value),
           titles: [...f.querySelectorAll('.template-picker__title')].map((e) => e.textContent.trim()).slice(0, 20) }; })()"""
PICKER_SUBMIT = """(() => { const f = document.querySelector('form.templates-picker__form'); if (!f) return false;
  const b = f.querySelector('.templates-picker__buttons button, .templates-picker__buttons input[type=submit]');
  if (b) { b.click(); return 'clicked'; } f.requestSubmit(); return 'requestSubmit'; })()"""
UPLOAD_PICKER = """(() => { const w = document.querySelector('[data-cy-upload-picker]');
  if (!w) return { present: false }; const b = w.querySelector('button');
  return { present: true, buttons: w.querySelectorAll('button').length, disabled: b ? b.disabled : null,
           ariaDisabled: b ? b.getAttribute('aria-disabled') : null }; })()"""


# --------------------------------------------------------------------------
# occ and the server side


def occ(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["ddev", "occ", *args], cwd=root, capture_output=True, text=True, timeout=300)


class SettingReadError(RuntimeError):
    """occ could not read a user setting.  Never the same as 'not set'."""


# `occ user:setting <uid> core <key>` exits 1 both when the key is not set and
# when anything else fails (core/Command/User/Setting.php).  Read with a default
# so that "not set" is exit 0 with this text, and any non-zero exit is a failure
# that raises -- the old reader returned None for both, and a failed FIRST read
# made the restore delete the owner's core/lang and record ok: true (review
# 2026-10-14, Q6).
UNSET = "__litecore_unset__"


def user_setting(root: Path, uid: str, key: str) -> str | None:
    """The setting's value, or None when it is not set.  Raises when occ fails."""
    done = occ(root, "user:setting", uid, "core", key, "--default-value", UNSET)
    if done.returncode != 0:
        raise SettingReadError(f"occ user:setting {uid} core {key}: exit {done.returncode}: "
                               f"{(done.stderr or done.stdout).strip()[:300]}")
    value = done.stdout.strip()
    return None if value == UNSET else value


def set_user_setting(root: Path, uid: str, key: str, value: str | None) -> dict[str, Any]:
    """Set (or delete, for None) and read back.  `ok` needs occ to have exited 0
    AND the readback to have succeeded AND to equal the value."""
    if value is None:
        done = occ(root, "user:setting", "--delete", uid, "core", key)
    else:
        done = occ(root, "user:setting", uid, "core", key, value)
    record: dict[str, Any] = {"key": key, "value": value, "exit": done.returncode}
    if done.returncode != 0:
        record["stderr"] = (done.stderr or done.stdout).strip()[:300]
    try:
        record["readback"] = user_setting(root, uid, key)
        record["ok"] = done.returncode == 0 and record["readback"] == value
    except SettingReadError as error:
        record["readback"] = None
        record["readError"] = str(error)
        record["ok"] = False
    return record


def read_settings(root: Path, uid: str = "admin") -> dict[str, str | None]:
    """The settings to restore to.  Raises SettingReadError: a run must not
    start on a value it could not read."""
    return {"lang": user_setting(root, uid, "lang"), "locale": user_setting(root, uid, "locale")}


def restore_settings(root: Path, original: dict[str, str | None], uid: str = "admin") -> dict[str, Any]:
    """Both keys are always attempted: a timeout or error on one must not skip
    the other.  `ok` is the conjunction of the per-key `ok`s."""
    restored: dict[str, Any] = {}
    for key in ("lang", "locale"):
        try:
            restored[key] = set_user_setting(root, uid, key, original[key])
        except Exception as error:  # noqa: BLE001 -- recorded as not restored
            restored[key] = {"key": key, "value": original[key], "exit": None, "readback": None, "ok": False,
                             "error": f"{type(error).__name__}: {error}"}
    restored["ok"] = all(restored[key].get("ok") is True for key in ("lang", "locale"))
    return restored


def dav_raw(client: Client, method: str, path: str, body: bytes | None = None,
            headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    request = urllib.request.Request(client.base + path, data=body, method=method,
                                     headers={"X-Requested-With": "XMLHttpRequest", **(headers or {})})
    request.add_header("Authorization", client.auth)
    try:
        with urllib.request.urlopen(request, context=client.tls, timeout=60) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def file_facts(client: Client, path: str) -> dict[str, Any]:
    """fileid, size and the bytes' sha256 of one of the user's files (404 -> absent)."""
    props = client.props("props", path)
    status, raw = dav_raw(client, "GET", client.dav_path(path))
    facts: dict[str, Any] = {"fileid": props.get("fileid"), "etag": props.get("etag"), "getStatus": status,
                             "bytes": len(raw) if status == 200 else 0,
                             "sha256": hashlib.sha256(raw).hexdigest() if status == 200 else None}
    if status == 200:
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                facts["entries"] = zf.namelist()
                content = zf.read("content.xml")
                facts["paragraphs"] = paragraph_texts_from_xml(content)
                facts["markCount"] = sum(p.count(MARK) for p in facts["paragraphs"])
                facts["stylesSha256"] = hashlib.sha256(zf.read("styles.xml")).hexdigest()
            facts["described"] = gen.describe(raw)
        except Exception as error:  # noqa: BLE001 -- a corrupt file is a finding, recorded
            facts["describeError"] = f"{type(error).__name__}: {error}"
    return facts


def creators(client: Client) -> dict[str, Any]:
    entry = client.call("creators", "GET", CREATORS_API)
    try:
        data = json.loads(entry["body"] or "")["ocs"]["data"]
    except (ValueError, KeyError, TypeError):
        # Client keeps 1500 characters; the listing can run past that.
        status, raw = dav_raw(client, "GET", CREATORS_API, headers={"OCS-APIRequest": "true", "Accept": "application/json"})
        try:
            data = json.loads(raw)["ocs"]["data"]
        except (ValueError, KeyError, TypeError):
            return {"status": status, "creators": None, "raw": raw[:500].decode("utf-8", "replace")}
        entry = {"status": status}
    rows = [{"app": c.get("app"), "label": c.get("label"), "extension": c.get("extension"),
             "mimetypes": c.get("mimetypes"), "templates": len(c.get("templates") or [])} for c in data]
    return {"status": entry["status"], "creators": rows, "litecore": [c for c in rows if c["app"] == "litecore"]}


def ocs_create(client: Client, file_path: str) -> dict[str, Any]:
    entry = client.call("create", "POST", CREATE_API, form={"filePath": file_path, "templatePath": "", "templateType": "user"})
    message = None
    try:
        message = json.loads(entry["body"] or "")["ocs"]["meta"].get("message")
    except (ValueError, KeyError, TypeError, AttributeError):
        pass
    return {"status": entry["status"], "message": message, "body": (entry["body"] or "")[:400]}


def host_static(root: Path) -> dict[str, Any]:
    git = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True).stdout.strip()  # noqa: E731
    manifest = json.loads((root / "engine" / "MANIFEST.json").read_text())
    info = (root / "appinfo" / "info.xml").read_text()
    changed = [line for line in git("diff", "--name-only", f"{CONTROL_HOST_COMMIT}..HEAD").splitlines() if line]
    blank = root / "blank" / "MANIFEST.json"
    return {"hostCommit": git("rev-parse", "--short", "HEAD"), "hostDirty": git("status", "--porcelain").splitlines(),
            "hostVersion": re.search(r"<version>([^<]+)</version>", info).group(1),
            "buildId": manifest.get("buildId"),
            "servedPage": ((manifest.get("files") or {}).get("e2-editor-app.js") or {}).get("sha256"),
            "engineFiles": {n: f.get("sha256") for n, f in (manifest.get("files") or {}).items()},
            "changedSinceControl": changed,
            "changedOutsideAllowed": [c for c in changed if not c.startswith(ALLOWED_CHANGED)],
            "blankManifestSha256": sha256_file(blank) if blank.is_file() else None,
            "blankGeneratorCheck": json.loads(subprocess.run(
                [sys.executable, str(PROJECT / "tools" / "make_new_document_templates.py"), "--check", str(root / "blank")],
                capture_output=True, text=True).stdout or "{}")}


PRODUCT_PATHS = ("wasm_sdk_probe/web/", "wasm_sdk_probe/editor-shell/", "wasm_sdk_probe/editor-shell-v2/",
                 "wasm_sdk_probe/sdk/", "wasm_sdk_probe/src/", "wasm_sdk_probe/Makefile", "wasm_sdk_probe/dist/")
# This round's own files in study_LiteCore: every commit that touches one of
# them is this round's commit, and none of those may touch a product path.
ROUND_PATHS = ("specs/SPEC-M3-new-document.md", "wasm_sdk_probe/tools/make_new_document_templates.py",
               "wasm_sdk_probe/tools/check_new_document_native.py", "wasm_sdk_probe/tools/check_new_document_choice.py",
               "wasm_sdk_probe/tools/check_m3_new_document.py", "wasm_sdk_probe/tests/test_new_document_templates.py",
               "findings/evidence/new-document/")


def repo_static() -> dict[str, Any]:
    """study_LiteCore: N9's repo half.  The commits that touch this round's
    files (ROUND_PATHS) must touch no product path; other sessions' commits in
    the same tree are recorded but are not this round's."""
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()  # noqa: E731
    commits = [c for c in git("log", "--format=%h", "0e7f7f64..HEAD", "--", *ROUND_PATHS).splitlines() if c]
    touched: dict[str, list[str]] = {}
    for commit in commits:
        files = git("show", "--format=", "--name-only", commit).splitlines()
        hits = [f for f in files if f.startswith(PRODUCT_PATHS)]
        if hits:
            touched[commit] = hits
    others = git("diff", "--name-only", "0e7f7f64..HEAD", "--", *[p.rstrip("/") for p in PRODUCT_PATHS]).splitlines()
    # A counted run needs the round's spec, tools and tests COMMITTED: with no
    # round commit the check above is vacuously green.  Evidence may be dirty
    # (this very report lands there).
    tools_dirty = [line[3:] for line in git("status", "--porcelain", "--", *[p for p in ROUND_PATHS if not p.endswith("/")]).splitlines() if line]
    return {"repoHead": git("rev-parse", "--short", "HEAD"), "roundCommits": commits,
            "roundToolsUncommitted": tools_dirty,
            "productPathsTouchedSinceStart": touched,
            "productPathsChangedByOthersSinceStart": [o for o in others if o]}


def validation_and_closure(host: Path) -> dict[str, Any]:
    validated = gen.validate_set(host / "blank")
    closure = subprocess.run([sys.executable, str(PROJECT / "tools" / "check_new_document_choice.py"),
                              "--host", str(host), "--json"], capture_output=True, text=True)
    try:
        closure_report = json.loads(closure.stdout)
    except json.JSONDecodeError:
        closure_report = {"unparsed": closure.stdout[-400:], "stderr": closure.stderr[-400:]}
    return {"N10": {k: v for k, v in validated.items() if k != "results"}, "N12": closure_report}


def other_runners(pgrep_lines: list[str], own_pids: tuple[int, ...]) -> list[str]:
    """Runner processes that are not this one.  A second instance of THIS tool
    counts (the old filter dropped every line naming it, so two instances ran
    at once and the later one read the earlier one's switched settings as the
    owner's -- review 2026-10-14, Q6).  Our own pid and parent (a `bash -c` or
    `timeout` whose command line names this script) are dropped by pid."""
    own = {str(p) for p in own_pids}
    return [line for line in pgrep_lines if line.split(" ", 1)[0] not in own and "pgrep" not in line]


def preflight() -> dict[str, Any]:
    wallet = subprocess.run(["busctl", "--user", "get-property", "org.freedesktop.secrets",
                             "/org/freedesktop/secrets/collection/kdewallet", "org.freedesktop.Secret.Collection", "Locked"],
                            capture_output=True, text=True)
    ours = subprocess.run(["pgrep", "-af", "probe_|check_m3|run_e2_c|run_merge"], capture_output=True, text=True).stdout
    ours = other_runners(ours.splitlines(), (os.getpid(), os.getppid()))
    chrome = subprocess.run(["pgrep", "-c", "chrome"], capture_output=True, text=True).stdout.strip()
    return {"kwalletLocked": wallet.stdout.strip(), "otherRunners": ours, "chromeProcesses": int(chrome or 0), "at": utc_now()}


def wait_for_runners(record: list[dict[str, Any]], **tag: Any) -> dict[str, Any]:
    flight = preflight()
    record.append({**tag, **flight})
    while flight["otherRunners"]:
        print(f"waiting: other runners {flight['otherRunners']}", file=sys.stderr)
        time.sleep(150)
        flight = preflight()
        record.append({**tag, **flight})
    return flight


# --------------------------------------------------------------------------
# The browser


def new_session(kind: str, scratch: Path):
    if kind == "chrome":
        session = LockChrome("cold")
        session.call("Network.disable")
        session.call("Emulation.setDeviceMetricsOverride", {"width": 1850, "height": 980, "deviceScaleFactor": 1, "mobile": False})
        return session
    scratch.mkdir(parents=True, exist_ok=True)
    session = FirefoxSession("cold", profile_dir=firefox_profile(scratch / f"ff-{time.monotonic_ns()}"))
    session.command("POST", "/window/rect", {"width": 1850, "height": 1080})
    return session


def type_name(session, kind: str, name: str) -> dict[str, Any]:
    """The file name, typed into the dialog (the user's path), replacing the default."""
    focused = evaluate(session, INPUT_OF.replace("ARG", json.dumps(DIALOG_INPUT)))
    if kind == "chrome":
        session.call("Input.insertText", {"text": name})
    else:
        element = session.command("POST", "/element", {"using": "css selector", "value": DIALOG_INPUT})
        key = next(iter(element.values()))
        session.command("POST", f"/element/{key}/clear", {})
        session.command("POST", f"/element/{key}/value", {"text": name})
    time.sleep(0.3)
    return {"default": (focused or {}).get("value"), "typed": evaluate(session, READ_INPUT.replace("ARG", json.dumps(DIALOG_INPUT)))}


def create_from_menu(session, kind: str, base: str, folder: str, name: str, record: dict[str, Any]) -> None:
    navigate(session, base + "/apps/files/files?dir=" + urllib.parse.quote("/" + folder), timeout=120)
    record["pickerSeen"] = wait_until(session, f"(() => document.querySelector({json.dumps(NEW_BUTTON)}) !== null)()", 60)
    record["picker"] = evaluate(session, UPLOAD_PICKER)
    evaluate(session, CLICK_ANY.replace("ARG", json.dumps(NEW_BUTTON)))
    record["entrySeen"] = wait_until(session, f"(() => document.querySelector({json.dumps(NEW_ENTRY)}) !== null)()", 20)
    record["entries"] = evaluate(session, "(() => [...document.querySelectorAll('[data-cy-upload-picker-menu-entry]')]"
                                          ".map((e) => ({ id: e.getAttribute('data-cy-upload-picker-menu-entry'), text: e.textContent.trim() })))()")
    record["entryClicked"] = evaluate(session, CLICK_ANY.replace("ARG", json.dumps(NEW_ENTRY)))
    record["dialogSeen"] = wait_until(session, f"(() => document.querySelector({json.dumps(DIALOG_INPUT)}) !== null)()", 20)
    record["name"] = type_name(session, kind, name)
    record["clickedFrom"] = evaluate(session, "(() => location.href)()")
    started = time.monotonic()
    record["submitClicked"] = evaluate(session, CLICK_ANY.replace("ARG", json.dumps(DIALOG_SUBMIT)))
    # With .odt files in the user's Templates folder, core shows its picker
    # ("Blank" preselected, plus those files); without any, it creates at once.
    picker_or_route = wait_until(session, "(() => (location.pathname.endsWith(" + json.dumps(ROUTE) + ") && 'route')"
                                          " || (document.querySelector('form.templates-picker__form') && 'picker') || false)()", 60)
    record["pickerShown"] = picker_or_route == "picker"
    if picker_or_route == "picker":
        record["pickerTiles"] = evaluate(session, PICKER_TILES)
        record["pickerSubmitted"] = evaluate(session, PICKER_SUBMIT)
    record["landed"] = wait_until(session, f"(() => location.pathname.endsWith({json.dumps(ROUTE)}) && location.href)()", 90)
    if not isinstance(record["landed"], str):
        record["landedInstead"] = evaluate(session, "(() => ({ href: location.href, modals: [...document.querySelectorAll('.modal-container')]"
                                                    ".map((m) => m.innerText.slice(0, 300)), text: (document.body.innerText || '').slice(0, 600) }))()")
        raise RuntimeError("the editor route was not reached after the dialog's submit")
    raw = wait_until(session, HOST_DONE, 400)
    record["host"] = json.loads(raw) if isinstance(raw, str) else {"notReported": raw}
    record["secondsToOpened"] = round(time.monotonic() - started, 2)
    record["opened"] = quiet(session, 60)


def reopen_from_files(session, base: str, folder: str, name: str, at: tuple[str, str], record: dict[str, Any]) -> None:
    navigate(session, base + "/apps/files/files?dir=" + urllib.parse.quote("/" + folder), timeout=120)
    selector = f'[data-cy-files-list-row-name={json.dumps(name, ensure_ascii=False)}] [data-cy-files-list-row-name-link]'
    record["filesRow"] = wait_until(session, f"(() => document.querySelector({json.dumps(selector)}) !== null)()", 60)
    started = time.monotonic()
    session.click(selector)
    record["landed"] = wait_until(session, f"(() => location.pathname.endsWith({json.dumps(ROUTE)}) && location.href)()", 60)
    raw = wait_until(session, HOST_DONE, 400)
    record["host"] = json.loads(raw) if isinstance(raw, str) else {"notReported": raw}
    record["secondsToOpened"] = round(time.monotonic() - started, 2)
    record["opened"] = quiet(session, 60)
    record["a11yBeforeClick"] = evaluate(session, A11Y)
    record["click"] = click(session, at)
    time.sleep(1.0)
    record["a11y"] = evaluate(session, A11Y)


def run_once(arm: str, kind: str, instance: Instance, admin: Client, scratch: Path) -> dict[str, Any]:
    spec = ARMS[arm]
    # One name per run: a file from a previous run is held by that session's
    # token lock for up to 300 s after the browser closed (the DELETE below got
    # 423 in the first counted run) and the name dialog then refuses the name.
    name = f"新文件 測試-{arm}-{kind}-{time.strftime('%H%M%SZ', time.gmtime())}.odt"
    record: dict[str, Any] = {"arm": arm, "browser": kind, "name": name, "expectedFile": spec["file"],
                              "settings": {"lang": spec["lang"], "locale": spec["locale"]}, "startedAt": utc_now()}
    path = f"{FOLDER}/{name}"
    record["folder"] = FOLDER
    record["mkcol"] = admin.call("mkcol", "MKCOL", admin.dav_path(FOLDER))["status"]   # 405 = already there
    record["removeOld"] = admin.call("remove old", "DELETE", admin.dav_path(path))["status"]
    record["creators"] = creators(admin)
    record["choice"] = php_choose(DEFAULT_DDEV, [(spec["lang"], spec["locale"])])[0]
    session = None
    try:
        session = new_session(kind, scratch)
        record["version"] = session.version
        record["navigatorLanguage"] = None
        record["login"] = login(session, instance.base, "admin", instance.password)
        record["navigatorLanguage"] = evaluate(session, "(() => navigator.language)()")
        create = record["create"] = {}
        create_from_menu(session, kind, instance.base, FOLDER, name, create)
        record["createdFile"] = file_facts(admin, path)
        # The user's path: a click in the first line, three real keys, the toolbar's save.
        at = first_line((record["createdFile"].get("described") or {}).get("paper") or ARMS[arm].get("paper"))
        record["clickAt"] = at
        record["click"] = click(session, at)
        keys = record["keys"] = []
        for letter in MARK:
            before = quiet(session, 30)
            generation = evaluate(session, GEN)
            press(session, kind, letter)
            time.sleep(0.5)
            after = quiet(session, 30)
            keys.append({"key": letter, "revBefore": before.get("revision"), "revAfter": after.get("revision"),
                         "genBefore": generation, "genAfter": evaluate(session, GEN), "latency": after.get("latency")})
        record["save"] = save_and_settle(session, 90)
        record["hostAfterSave"] = evaluate(session, HOST)
        record["savedFile"] = file_facts(admin, path)
        reopen = record["reopen"] = {}
        reopen_from_files(session, instance.base, FOLDER, name, at, reopen)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        if session is not None:
            session.close()
    record["completedAt"] = utc_now()
    return record


def run_readonly(instance: Instance, admin: Client, scratch: Path, with_browser: bool) -> dict[str, Any]:
    """N8: a read-only share, and the other user's attempt to create in it."""
    import secrets
    record: dict[str, Any] = {}
    password = secrets.token_urlsafe(24)
    admin.call("setup", "DELETE", f"/ocs/v2.php/cloud/users/{OTHER}")
    made = admin.call("setup", "POST", "/ocs/v2.php/cloud/users", form={"userid": OTHER, "password": password})
    record["userCreated"] = made["status"]
    other = Client(instance.base, OTHER, password, admin.log)
    admin.call("setup", "DELETE", admin.dav_path(RO_FOLDER))
    record["mkcol"] = admin.call("setup", "MKCOL", admin.dav_path(RO_FOLDER))["status"]
    share = admin.call("share", "POST", "/ocs/v2.php/apps/files_sharing/api/v1/shares",
                       form={"path": "/" + RO_FOLDER, "shareType": 0, "shareWith": OTHER, "permissions": 1})
    record["shareStatus"] = share["status"]
    try:
        data = json.loads(share["body"])["ocs"]["data"]
        target = data["file_target"].lstrip("/")
        record["sharePermissions"] = data.get("permissions")
    except (ValueError, KeyError, TypeError):
        target = RO_FOLDER
    record["target"] = target
    record["otherSees"] = other.props("props", target).get("permissions")
    attempt = f"/{target}/新文件 唯讀測試.odt"
    record["create"] = ocs_create(other, attempt)
    record["adminAfter"] = admin.props("props", f"{RO_FOLDER}/新文件 唯讀測試.odt")
    record["otherAfter"] = other.props("props", f"{target}/新文件 唯讀測試.odt")
    if with_browser:
        session = None
        try:
            session = new_session("chrome", scratch)
            login(session, instance.base, OTHER, password)
            navigate(session, instance.base + "/apps/files/files?dir=" + urllib.parse.quote("/" + target), timeout=120)
            wait_until(session, "(() => document.querySelector('[data-cy-files-list]') !== null)()", 60)
            time.sleep(2)
            record["pickerInSharedFolder"] = evaluate(session, UPLOAD_PICKER)
            record["entriesInSharedFolder"] = evaluate(session, "(() => [...document.querySelectorAll('[data-cy-upload-picker-menu-entry]')]"
                                                               ".map((e) => e.getAttribute('data-cy-upload-picker-menu-entry')))()")
        except Exception:  # noqa: BLE001
            record["browserFatal"] = traceback.format_exc()
        finally:
            if session is not None:
                session.close()
    admin.call("teardown", "DELETE", f"/ocs/v2.php/cloud/users/{OTHER}")
    admin.call("teardown", "DELETE", admin.dav_path(RO_FOLDER))
    return record


# --------------------------------------------------------------------------
# Scoring -- raw fields only.

def digits(*values: Any) -> bool:
    return all(isinstance(v, str) and v.isdigit() for v in values)


def score_run(run: dict[str, Any], manifest: dict[str, Any]) -> dict[str, list[str]]:
    bad: dict[str, list[str]] = {k: [] for k in ("N1", "N2", "N3", "N4", "N5", "N6")}
    if "fatal" in run:
        return {k: ["run died"] for k in bad}
    expected_file = run.get("expectedFile")
    record = (manifest.get("files") or {}).get(expected_file) or {}
    # N1
    lite = (run.get("creators") or {}).get("litecore")
    if not lite or len(lite) != 1 or lite[0].get("extension") != ".odt" or lite[0].get("mimetypes") != [ODT]:
        bad["N1"].append(f"creator listing {lite}")
    if (run.get("create") or {}).get("entrySeen") is not True:
        bad["N1"].append(f"menu entry not seen: {(run.get('create') or {}).get('entrySeen')}")
    # N2
    created = run.get("createdFile") or {}
    if (run.get("choice") or {}).get("file") != expected_file:
        bad["N2"].append(f"PHP chose {(run.get('choice') or {}).get('file')!r}, the arm expects {expected_file!r}")
    if created.get("sha256") != record.get("sha256") or created.get("bytes") != record.get("bytes"):
        bad["N2"].append(f"created file sha {created.get('sha256')} bytes {created.get('bytes')}, template {record.get('sha256')} {record.get('bytes')}")
    if not created.get("fileid"):
        bad["N2"].append("no fileid after creation")
    # N3
    create = run.get("create") or {}
    landed = create.get("landed")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(landed).query) if isinstance(landed, str) else {}
    if not isinstance(landed, str) or query.get("fileId") != [str(created.get("fileid"))]:
        bad["N3"].append(f"landed {landed!r}, want fileId {created.get('fileid')}")
    if not (isinstance(create.get("clickedFrom"), str) and "/apps/files/" in create["clickedFrom"]):
        bad["N3"].append(f"not from Files: {create.get('clickedFrom')!r}")
    fetched = (create.get("host") or {}).get("fetched") or {}
    if fetched.get("sha256") != created.get("sha256") or fetched.get("status") != 200:
        bad["N3"].append(f"page fetched {fetched}")
    opened = create.get("opened") or {}
    if opened.get("state") != "ready" or opened.get("doc") != run.get("name"):
        bad["N3"].append(f"opened state {opened.get('state')!r} doc {opened.get('doc')!r}")
    # N4
    clicked = run.get("click") or {}
    if clicked.get("timedOut") is not False or "定位游標" not in (clicked.get("latency") or "") or "失敗" in (clicked.get("latency") or ""):
        bad["N4"].append(f"click into the first line {clicked.get('latency')!r} timedOut={clicked.get('timedOut')}")
    keys = run.get("keys") or []
    if len(keys) != len(MARK):
        bad["N4"].append(f"{len(keys)} keys recorded")
    for k in keys:
        # "generation unchanged" needs the generation to have been READ: two
        # unread values (None == None) are not "unchanged" (review, Q4).
        if not (digits(k.get("revBefore"), k.get("revAfter"), k.get("genBefore"), k.get("genAfter"))
                and int(k["revAfter"]) == int(k["revBefore"]) + 1 and k["genBefore"] == k["genAfter"]):
            bad["N4"].append(f"key {k}")
    save = run.get("save") or {}
    if save.get("outcome") != "saved":
        bad["N4"].append(f"save {save.get('outcome')!r} timedOut={save.get('timedOut')}")
    saved = run.get("savedFile") or {}
    # The saved document is the blank one plus the three keys: its paragraph
    # sequence is exactly [MARK].  "contains the marker once" also passed a
    # document that was never blank (`zqxOLD`) or gained a paragraph (review, Q1).
    if (saved.get("getStatus") != 200 or not saved.get("bytes") or saved.get("markCount") != 1
            or saved.get("paragraphs") != [MARK] or "describeError" in saved):
        bad["N4"].append(f"server file status {saved.get('getStatus')} bytes {saved.get('bytes')} marks {saved.get('markCount')}"
                         f" paragraphs {saved.get('paragraphs')!r} {saved.get('describeError', '')}")
    # N5
    reopen = run.get("reopen") or {}
    re_fetched = (reopen.get("host") or {}).get("fetched") or {}
    re_landed = reopen.get("landed")
    re_query = urllib.parse.parse_qs(urllib.parse.urlsplit(re_landed).query) if isinstance(re_landed, str) else {}
    # The same row is the same file: the reopen lands on N2's fileid, as N3
    # does.  A save that replaced the file under a new id passed before (review, Q1).
    if (not isinstance(re_landed, str) or re_query.get("fileId") != [str(created.get("fileid"))]
            or re_fetched.get("sha256") != saved.get("sha256")):
        bad["N5"].append(f"reopen landed {re_landed!r} (want fileId {created.get('fileid')}), fetched {re_fetched.get('sha256')} vs saved {saved.get('sha256')}")
    re_opened = reopen.get("opened") or {}
    if re_opened.get("state") != "ready" or re_opened.get("doc") != run.get("name"):
        bad["N5"].append(f"reopened state {re_opened.get('state')!r} doc {re_opened.get('doc')!r}")
    a11y = reopen.get("a11y") or {}
    offers = a11y.get("offers")
    # The offer is "0" or "1" -- anything else is the live region not read
    # (renamed, or the evaluate failed), which is neither NOT_OFFERED nor OFFERED
    # (CLAUDE.md section 3; review, Q4).
    if offers not in ("0", "1"):
        bad["N5"].append(f"the live region's offer was not read: {offers!r}")
    elif offers == "1" and MARK not in (a11y.get("text") or ""):
        bad["N5"].append(f"the live region offers text but says {a11y.get('text')!r}")
    # N6
    described = saved.get("described") or {}
    if not record:
        bad["N6"].append(f"no manifest record for {expected_file}")
    else:
        bad["N6"] += [f"saved styles.xml {d}" for d in gen.compare(record, described)]
    return bad


def score(report: dict[str, Any], strict: bool) -> dict[str, Any]:
    manifest = report.get("blankManifest") or {}
    problems: list[str] = []
    runs = report.get("runs") or []
    seen = {(r.get("arm"), r.get("browser")) for r in runs}
    wanted = {(a, b) for a in ARMS for b in BOTH}
    if strict and seen != wanted:
        problems.append(f"arms x browsers {sorted(seen)}")
    # A run that stopped before its cells (kwallet locked) or recorded none is
    # not WORKS in any mode (review, Q4: `NEW-DOCUMENT WORKS -` was printed).
    if not runs or report.get("stopped"):
        problems.append(f"no complete run: {len(runs)} runs, stopped {report.get('stopped')!r}")
    static = report.get("hostStatic") or {}
    delta_host = static.get("hostVersion") == DELTA_HOST_VERSION
    if delta_host:
        # 0.2.19's acceptance only (spec N9: "only the host changed").
        if static.get("buildId") != CONTROL_BUILD_ID or static.get("servedPage") != CONTROL_PAGE_SHA256:
            problems.append(f"N9 engine package buildId {static.get('buildId')} page {static.get('servedPage')} is not 0.2.18's")
        if static.get("changedOutsideAllowed"):
            problems.append(f"N9 host changed outside the allowed paths: {static['changedOutsideAllowed']}")
    if (report.get("repoStatic") or {}).get("productPathsTouchedSinceStart"):
        problems.append(f"N9 product paths touched: {report['repoStatic']['productPathsTouchedSinceStart']}")
    if not (static.get("blankGeneratorCheck") or {}).get("identical"):
        problems.append("N9/N10 blank/ is not what the generator makes")
    checks = report.get("checks") or {}
    n10 = checks.get("N10") or {}
    if n10.get("passed") != n10.get("validated") or not n10.get("hashesMatch") or not n10.get("validated"):
        problems.append(f"N10 {n10}")
    if not (checks.get("N12") or {}).get("passed"):
        problems.append(f"N12 {checks.get('N12')}")
    ro = report.get("readOnly") or {}
    # The other user's view of the share must carry no create permission (CK):
    # a 403 from a share that allows creating is not Nextcloud's refusal (review, Q1).
    if (ro.get("create", {}).get("status") != 403 or ro.get("adminAfter", {}).get("fileid") or ro.get("otherSees") in (None, "")
            or "CK" in (ro.get("otherSees") or "")):
        problems.append(f"N8 create {ro.get('create', {}).get('status')} admin sees {ro.get('adminAfter', {}).get('fileid')} other perms {ro.get('otherSees')!r}")
    if strict:
        if report.get("label") != "counted":
            problems.append(f"label {report.get('label')!r}")
        if static.get("hostDirty"):
            problems.append("host tree dirty")
        repo = report.get("repoStatic") or {}
        if repo.get("roundToolsUncommitted") or not repo.get("roundCommits"):
            problems.append(f"N9 the round's spec/tools/tests are not committed: {repo.get('roundToolsUncommitted')} commits {repo.get('roundCommits')}")
        bound = [("hostCommit", HOST_COMMIT, static.get("hostCommit")), ("hostVersion", HOST_VERSION, static.get("hostVersion")),
                 ("blankManifestSha256", MANIFEST_SHA256, static.get("blankManifestSha256"))]
        if not delta_host:
            # The count's engine identity (N9's recurring half): the bound
            # candidate, never "unchanged since the previous host".
            bound += [("engineBuildId", ENGINE_BUILD_ID, static.get("buildId")), ("pageSha256", PAGE_SHA256, static.get("servedPage"))]
        for name, want, have in bound:
            tag = "N9 binding" if name in ("engineBuildId", "pageSha256") else "binding"
            if want is None:
                problems.append(f"{tag} {name} not written")
            elif have != want:
                problems.append(f"{tag} {name} {have} != {want}")
        if not (report.get("controlReport") or {}).get("red"):
            problems.append("N1's red case (the 0.2.18 control) is not recorded as red")
        if not (report.get("redCorruptReport") or {}).get("red"):
            problems.append("N7(b)'s red case is not recorded as red")
        settings = report.get("settingsRestored") or {}
        if not settings.get("ok") or any((settings.get(k) or {}).get("exit") != 0 for k in ("lang", "locale")):
            problems.append(f"admin settings not restored: {settings}")
    per: dict[str, Any] = {}
    a11y_half: dict[str, str] = {}
    for run in runs:
        scored = score_run(run, manifest)
        failing = {k: v for k, v in scored.items() if v}
        cell = f"{run.get('arm')}/{run.get('browser')}"
        per[cell] = failing or "PASS"
        if failing:
            problems.append(f"{cell} {sorted(failing)}")
        # N5's conditional half, named as what it is (CLAUDE.md section 3): on a
        # profile that offers no caret paragraph text there is nothing to guard.
        offers = ((run.get("reopen") or {}).get("a11y") or {}).get("offers")
        a11y_half[cell] = "OFFERED" if offers == "1" else ("NOT_OFFERED" if offers == "0" else f"unknown ({offers!r})")
    return {"works": not problems, "problems": problems, "runs": per, "n5ParagraphTextHalf": a11y_half}


def one_line(result: dict[str, Any]) -> str:
    cells = ",".join(f"{k}={'PASS' if v == 'PASS' else '+'.join(sorted(v))}" for k, v in sorted(result["runs"].items()))
    return f"NEW-DOCUMENT {'WORKS' if result['works'] else 'NOT_ESTABLISHED'} {cells or '-'} problems={result['problems']}"


def _run(report: dict, arm: str, browser: str = "chrome") -> dict:
    return next(r for r in report["runs"] if r["arm"] == arm and r["browser"] == browser)


RED_CASES = [
    ("N1-no-creator", lambda r: _run(r, "TW")["creators"].update(litecore=[])),
    ("N1-ott-offered", lambda r: _run(r, "EN", "firefox")["creators"]["litecore"][0]["mimetypes"].append(ODT + "-template")),
    ("N2-other-bytes", lambda r: _run(r, "TW")["createdFile"].update(sha256="0" * 64)),
    ("N2-php-chose-other", lambda r: _run(r, "EN")["choice"].update(file="en-US_zh-TW_A4.odt")),
    ("N3-wrong-file", lambda r: _run(r, "TW", "firefox")["create"].update(landed=_run(r, "TW", "firefox")["create"]["landed"].replace("fileId=", "fileId=9"))),
    ("N3-page-fetched-other", lambda r: _run(r, "EN")["create"]["host"]["fetched"].update(sha256="1" * 64)),
    ("N4-no-revision", lambda r: _run(r, "TW")["keys"][0].update(revAfter=_run(r, "TW")["keys"][0]["revBefore"])),
    ("N4-generation-unread", lambda r: [k.update(genBefore=None, genAfter=None) for k in _run(r, "EN", "firefox")["keys"]]),
    ("N4-click-refused", lambda r: _run(r, "EN")["click"].update(latency="定位游標 失敗")),
    ("N4-save-not-saved", lambda r: _run(r, "EN", "firefox")["save"].update(outcome="copied")),
    ("N4-marker-missing", lambda r: _run(r, "TW")["savedFile"].update(markCount=0)),
    ("N4-extra-paragraph", lambda r: _run(r, "TW", "firefox")["savedFile"].update(paragraphs=[MARK, "UNEXPECTED"], markCount=1)),
    ("N4-zero-bytes", lambda r: _run(r, "EN")["savedFile"].update(bytes=0, getStatus=200)),
    ("N5-reopened-other-bytes", lambda r: _run(r, "TW", "firefox")["reopen"]["host"]["fetched"].update(sha256="2" * 64)),
    ("N5-reopened-other-file", lambda r: _run(r, "EN")["reopen"].update(landed=_run(r, "EN")["reopen"]["landed"].replace("fileId=", "fileId=9"))),
    ("N5-live-region-lies", lambda r: _run(r, "EN")["reopen"]["a11y"].update(offers="1", text="something else")),
    ("N5-offer-not-read", lambda r: _run(r, "TW")["reopen"]["a11y"].update(offers=None, text=None)),
    ("N6-asian-zh-CN", lambda r: _run(r, "TW")["savedFile"]["described"].update(asian="zh-CN")),
    ("N6-paper-letter-in-TW", lambda r: _run(r, "TW", "firefox")["savedFile"]["described"].update(paper="Letter")),
    ("N6-paper-a4-in-EN", lambda r: _run(r, "EN")["savedFile"]["described"].update(paper="A4")),
    ("N6-font-KR", lambda r: _run(r, "EN", "firefox")["savedFile"]["described"]["fonts"].update(asian="Noto Sans CJK KR")),
    ("N6-western-en-GB", lambda r: _run(r, "TW")["savedFile"]["described"].update(western="en-GB")),
    ("N8-created-anyway", lambda r: r["readOnly"]["create"].update(status=200)),
    ("N8-file-appeared", lambda r: r["readOnly"]["adminAfter"].update(fileid="123")),
    ("N8-share-allows-create", lambda r: r["readOnly"].update(otherSees="SRGDNVCK")),
    ("N9-other-engine", lambda r: r["hostStatic"].update(buildId="0000000000000000")),
    ("N9-page-moved", lambda r: r["hostStatic"].update(servedPage="3" * 64)),
    ("N9-product-touched", lambda r: r["repoStatic"].update(productPathsTouchedSinceStart={"deadbeef": ["wasm_sdk_probe/web/e2-editor-app.js"]})),
    ("N9-tools-uncommitted", lambda r: r["repoStatic"].update(roundToolsUncommitted=["wasm_sdk_probe/tools/check_m3_new_document.py"])),
    ("N10-validator-red", lambda r: r["checks"]["N10"].update(passed=r["checks"]["N10"]["validated"] - 1)),
    ("N12-closure-red", lambda r: r["checks"]["N12"].update(passed=False)),
    ("one-browser", lambda r: r.update(runs=[x for x in r["runs"] if x["browser"] != "firefox"])),
    ("one-arm", lambda r: r.update(runs=[x for x in r["runs"] if x["arm"] != "EN"])),
    ("stopped-before-the-cells", lambda r: r.update(stopped="kwallet locked")),
    ("binding-host-moved", lambda r: r["hostStatic"].update(hostCommit="0000000")),
    ("control-not-red", lambda r: r["controlReport"].update(red=False)),
    ("red-corrupt-not-red", lambda r: r["redCorruptReport"].update(red=False)),
    ("settings-not-restored", lambda r: r["settingsRestored"].update(ok=False)),
    ("settings-restore-failed", lambda r: r["settingsRestored"]["lang"].update(exit=1)),
]


def rules_fired(result: dict[str, Any]) -> set[str]:
    """The rule ids a verdict names: per-cell failing keys plus the leading
    `N<n>` of each static problem."""
    fired: set[str] = set()
    for cell in result["runs"].values():
        if cell != "PASS":
            fired |= set(cell)
    for problem in result["problems"]:
        found = re.match(r"(N\d+)\b", problem)
        if found:
            fired.add(found.group(1))
    return fired


def red_cases(path: Path) -> int:
    """Every case must go red ON THE RULE ITS NAME STARTS WITH (`N<n>-…`); a
    case with no rule prefix only has to go red.  Before the review a case was
    satisfied by whatever rule fired first, so deleting a clause whose case
    also tripped a neighbour left the self-test green (review 2026-10-14, Q5)."""
    base = json.loads(path.read_text())
    baseline = score(base, strict=True)
    print(("GREEN" if baseline["works"] else "RED  ") + " base " + one_line(baseline))
    ok = baseline["works"]
    for name, mutate in RED_CASES:
        mutated = copy.deepcopy(base)
        try:
            mutate(mutated)
        except (KeyError, StopIteration, IndexError, TypeError) as error:
            print(f"SKIP  {name:26} mutation not applicable: {error!r}")
            ok = False
            continue
        result = score(mutated, strict=True)
        rule = name.split("-", 1)[0]
        targeted = rule not in rules_fired(result) if re.fullmatch(r"N\d+", rule) else False
        red = not result["works"] and not targeted
        ok = ok and red
        print(("RED  " if red else ("MISS " if targeted else "GREEN")) + f" {name:26} " + one_line(result))
    return 0 if ok else 1


# --------------------------------------------------------------------------
# Modes


def control(instance: Instance, admin: Client, out_dir: Path) -> dict[str, Any]:
    """N1's red case: what the installed app lists.  Meant for 0.2.18."""
    listing = creators(admin)
    installed = occ(instance.root, "config:app:get", "litecore", "installed_version").stdout.strip()
    git = lambda *a: subprocess.run(["git", *a], cwd=instance.root, capture_output=True, text=True).stdout.strip()  # noqa: E731
    report = {"probe": "m3-new-document-control", "at": utc_now(), "installedVersion": installed,
              "hostCommit": git("rev-parse", "--short", "HEAD"), "hostDirty": git("status", "--porcelain").splitlines(),
              "creators": listing, "red": listing.get("creators") is not None and not listing.get("litecore")}
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report['at'].replace(':', '').replace('+0000', 'Z')}.json"
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    report["path"] = str(path)
    return report


def red_corrupt(instance: Instance, admin: Client, out_dir: Path) -> dict[str, Any]:
    """N7(b): with the manifest hidden, creating a blank document must be refused
    and leave no file.  The manifest is restored whatever happens."""
    manifest = instance.root / "blank" / "MANIFEST.json"
    hidden = instance.root / "blank" / "MANIFEST.json.red-case"
    name = "新文件 紅案-壞範本.odt"
    report: dict[str, Any] = {"probe": "m3-new-document-red-corrupt", "at": utc_now(), "name": name}
    admin.call("remove old", "DELETE", admin.dav_path(name))
    report["before"] = admin.props("before", name)
    try:
        manifest.rename(hidden)
        report["manifestHidden"] = not manifest.exists()
        time.sleep(1.0)
        report["create"] = ocs_create(admin, "/" + name)
        report["after"] = admin.props("after", name)
        report["listingAfter"] = [n for n in folder_names(admin, "") if n.startswith("新文件 紅案")]
    finally:
        if hidden.exists():
            hidden.rename(manifest)
        report["manifestRestored"] = manifest.exists() and sha256_file(manifest) == MANIFEST_SHA256
    report["hostDirty"] = subprocess.run(["git", "status", "--porcelain"], cwd=instance.root, capture_output=True, text=True).stdout.splitlines()
    # Which host this red case was measured on (review 2026-10-14, Q3): the
    # count inherits it while lib/Listener/, lib/Template/ and blank/ are
    # unchanged since this commit; a change there re-runs --red-corrupt.
    report["hostCommit"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=instance.root, capture_output=True, text=True).stdout.strip()
    report["red"] = (report.get("create", {}).get("status") == 403 and not report.get("after", {}).get("fileid")
                     and not report.get("listingAfter") and report["manifestRestored"])
    # And the positive control, right after the restore: the same request now creates the file.
    report["controlCreate"] = ocs_create(admin, "/" + name)
    report["controlAfter"] = file_facts(admin, name)
    admin.call("cleanup", "DELETE", admin.dav_path(name))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report['at'].replace(':', '').replace('+0000', 'Z')}.json"
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    report["path"] = str(path)
    return report


def folder_names(client: Client, folder: str) -> list[str]:
    status, raw = dav_raw(client, "PROPFIND", client.dav_path(folder),
                          b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:displayname/></d:prop></d:propfind>',
                          {"Depth": "1", "Content-Type": "application/xml"})
    text = raw.decode("utf-8", "replace")
    hrefs = [chunk.split("</d:href>", 1)[0] for chunk in text.split("<d:href>")[1:]]
    return [urllib.parse.unquote(h.rstrip("/").rsplit("/", 1)[-1]) for h in hrefs]


def latest(out_dir: Path) -> dict[str, Any] | None:
    files = sorted(out_dir.glob("*.json")) if out_dir.is_dir() else []
    return json.loads(files[-1].read_text()) if files else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--arms", default="TW,EN")
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--skip-readonly", action="store_true")
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--red-corrupt", action="store_true")
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

    instance = Instance(args.ddev_root)
    log: list[dict[str, Any]] = []
    admin = Client(instance.base, "admin", instance.password, log)
    if args.control:
        report = control(instance, admin, EVIDENCE / "control-0.2.18")
        print(("RED  " if report["red"] else "GREEN") + f" control installed {report['installedVersion']} host {report['hostCommit']}"
              f" litecore creators {report['creators'].get('litecore')} -> {report['path']}")
        return 0 if report["red"] else 1
    if args.red_corrupt:
        report = red_corrupt(instance, admin, EVIDENCE / "red-corrupt")
        print(("RED  " if report["red"] else "GREEN") + f" red-corrupt create {report.get('create')} after {report.get('after', {}).get('fileid')}"
              f" restored {report['manifestRestored']} control {report['controlCreate'].get('status')} -> {report['path']}")
        return 0 if report["red"] else 1
    if not args.label:
        parser.error("--label is required for a run")

    # The owner's settings are read AFTER any other runner has finished (a
    # second instance of this tool would otherwise read the first's switched
    # values as the owner's) and a value that cannot be read stops the run
    # before anything is switched: it could not be restored.
    early_preflight: list[dict[str, Any]] = []
    wait_for_runners(early_preflight, phase="before-reading-settings")
    try:
        original = read_settings(args.ddev_root)
    except SettingReadError as error:
        print(f"refusing to run: the admin's setting could not be read, so it could not be restored: {error}", file=sys.stderr)
        return 2
    report: dict[str, Any] = {
        "probe": "m3-new-document", "label": args.label, "startedAt": utc_now(), "spec": "specs/SPEC-M3-new-document.md",
        "runner": {"path": str(Path(__file__).relative_to(REPO)), "sha256": sha256_file(Path(__file__))},
        "bindings": {"hostCommit": HOST_COMMIT, "hostVersion": HOST_VERSION, "blankManifestSha256": MANIFEST_SHA256,
                     "engineBuildId": ENGINE_BUILD_ID, "pageSha256": PAGE_SHA256,
                     "deltaHostVersion": DELTA_HOST_VERSION, "controlBuildId": CONTROL_BUILD_ID, "controlPageSha256": CONTROL_PAGE_SHA256},
        "instance": instance.describe(), "hostStatic": host_static(args.ddev_root), "repoStatic": repo_static(),
        "blankManifest": json.loads((args.ddev_root / "blank" / "MANIFEST.json").read_text()),
        "checks": validation_and_closure(args.ddev_root),
        "controlReport": latest(EVIDENCE / "control-0.2.18"), "redCorruptReport": latest(EVIDENCE / "red-corrupt"),
        "adminSettingsBefore": original, "preflight": early_preflight, "settingsChanges": [], "runs": [],
    }
    if args.label == "counted" and report["hostStatic"]["hostDirty"]:
        print("refusing a counted run on a dirty host tree", file=sys.stderr)
        return 2
    SCRATCH.mkdir(parents=True, exist_ok=True)
    # A SIGTERM (a chain's abort or timeout of a detached run) must reach the
    # `finally` below: as SystemExit it does; as the default action it skips it
    # and leaves the owner in the arm's language.
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(128 + signum))
    try:
        for arm in args.arms.split(","):
            spec = ARMS[arm]
            report["settingsChanges"].append({"arm": arm, "lang": set_user_setting(args.ddev_root, "admin", "lang", spec["lang"]),
                                              "locale": set_user_setting(args.ddev_root, "admin", "locale", spec["locale"])})
            for kind in args.browsers.split(","):
                flight = wait_for_runners(report["preflight"], arm=arm, browser=kind)
                if flight["kwalletLocked"] == "b true":
                    report["stopped"] = "kwallet locked"
                    break
                report["runs"].append(run_once(arm, kind, instance, admin, SCRATCH / f"{arm}-{kind}"))
                report["log"] = log
    finally:
        report["settingsRestored"] = restore_settings(args.ddev_root, original)
    if not args.skip_readonly:
        report["readOnly"] = run_readonly(instance, admin, SCRATCH / "readonly", with_browser="chrome" in args.browsers)
    # Tidy up what the runs made; a file still under its session's lock answers
    # 423 and lapses within 300 s -- recorded, not retried.
    report["cleanup"] = {run["name"]: admin.call("cleanup", "DELETE", admin.dav_path(f"{FOLDER}/{run['name']}"))["status"]
                         for run in report["runs"] if run.get("name")}
    report["log"] = log
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
