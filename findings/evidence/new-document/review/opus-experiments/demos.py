"""Report mutations: each writes report/<name>.json, to be scored by the tool's own CLI."""
import copy, json
from pathlib import Path
S = Path(__file__).resolve().parent.parent
BASE = json.loads((S / "report" / "base.json").read_text())

def run(r, arm, browser):
    return next(x for x in r["runs"] if x["arm"] == arm and x["browser"] == browser)

def save(name, r):
    (S / "report" / f"{name}.json").write_text(json.dumps(r, ensure_ascii=False))

# Q1/N4+N5: the save replaced the file (temp + MOVE): new fileid at the same path,
# reopened through the new id.  Every cell.
r = copy.deepcopy(BASE)
for x in r["runs"]:
    new = str(int(x["createdFile"]["fileid"]) + 50000)
    x["savedFile"]["fileid"] = new
    x["reopen"]["landed"] = x["reopen"]["landed"].split("fileId=")[0] + "fileId=" + new
    x["reopen"]["host"]["file"]["id"] = int(new)
save("q1-fileid-replaced", r)

# Q1/N9: the engine package's manifest still says buildId d6d04880 and page b24d754a,
# but declares a different worker (and the served bytes are never hashed at all).
r = copy.deepcopy(BASE)
r["hostStatic"]["engineFiles"]["profiles/e2-editor-v19/sdk-worker.js"] = "f" * 64
r["hostStatic"]["engineFiles"]["editor-shell-v2/narrow-editor-v2-session.js"] = "e" * 64
save("q1-engine-files-changed", r)

# Q4: the live region is gone from the page (or the read failed): every cell.
r = copy.deepcopy(BASE)
for x in r["runs"]:
    del x["reopen"]["a11y"]
save("q4-no-a11y", r)
r = copy.deepcopy(BASE)
for x in r["runs"]:
    x["reopen"]["a11y"] = {"offers": None, "text": None, "reason": None, "deferred": None}
save("q4-a11y-offers-null", r)

# Q4: #s-generation unreadable (both reads None) on every key of every cell.
r = copy.deepcopy(BASE)
for x in r["runs"]:
    for k in x["keys"]:
        k["genBefore"] = None; k["genAfter"] = None
save("q4-generation-unread", r)

# Q4: a non-counted label with zero runs (what --score does with it).
r = copy.deepcopy(BASE); r["label"] = "shakedown"; r["runs"] = []
save("q4-shakedown-no-runs", r)

# Q4 controls (should be red): keys empty, N10 validated 0, readOnly absent.
r = copy.deepcopy(BASE); run(r, "TW", "chrome")["keys"] = []; save("q4-ctl-keys-empty", r)
r = copy.deepcopy(BASE); r["checks"]["N10"].update(validated=0, passed=0); save("q4-ctl-n10-zero", r)
r = copy.deepcopy(BASE); del r["readOnly"]; save("q4-ctl-readonly-absent", r)

# Q6: the first occ read failed (None == "not set"), the restore deleted the
# owner's language, and the readback agrees with the failed read.
r = copy.deepcopy(BASE)
r["adminSettingsBefore"] = {"lang": None, "locale": None}
r["settingsRestored"]["lang"] = {"key": "lang", "value": None, "exit": 0, "readback": None}
save("q6-lang-deleted", r)

# Q3: 0.2.20 as the next count would see it, with HOST_* bindings updated and
# nothing else: engine v20 package, page moved, host diff includes js/ and engine-less files.
r = copy.deepcopy(BASE)
r["hostStatic"].update(hostCommit="1234567", hostVersion="0.2.20", buildId="aaaaaaaaaaaaaaaa", servedPage="9" * 64,
                       changedOutsideAllowed=["js/litecore-editor.js"])
save("q3-next-host", r)

# Q2 (latent): a profile that offers caret paragraph text AND has the structure
# projection -- the page empties #a11y-para by design (deferredToStructure "1").
r = copy.deepcopy(BASE)
for x in r["runs"]:
    x["reopen"]["a11y"] = {"offers": "1", "text": "", "reason": "ok", "deferred": "1"}
save("q2-a11y-deferred-to-structure", r)
print("written")
