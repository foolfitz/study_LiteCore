"""Checker-mutation census: neutralize one clause of score_run/score at a time
and ask whether any RED_CASE turns GREEN (i.e. the self-test would notice)."""
import copy, importlib.util, io, json, sys, contextlib
from pathlib import Path

S = Path(__file__).resolve().parent.parent
TOOLS = S / "tools"
SRC = (TOOLS / "check_m3_new_document.py").read_text()
BASE = json.loads((S / "report" / "base.json").read_text())
sys.path.insert(0, str(TOOLS))

def load(src, tag):
    path = S / "harness" / f"mut_{tag}.py"
    path.write_text(src)
    spec = importlib.util.spec_from_file_location(f"mut_{tag}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# (id, old, new): each replaces exactly one occurrence in the source.
M = [
 ("C1 fatal", 'if "fatal" in run:', 'if False:'),
 ("C2a N1 no lite", 'if not lite or len(lite) != 1', 'if False or len(lite) != 1'),
 ("C2b N1 len!=1", 'len(lite) != 1 or lite[0]', 'False or lite[0]'),
 ("C2c N1 extension", 'lite[0].get("extension") != ".odt" or', 'False or'),
 ("C2d N1 mimetypes", 'or lite[0].get("mimetypes") != [ODT]:', 'or False:'),
 ("C3 N1 entrySeen", 'if (run.get("create") or {}).get("entrySeen") is not True:', 'if False:'),
 ("C4 N2 choice", 'if (run.get("choice") or {}).get("file") != expected_file:', 'if False:'),
 ("C5a N2 sha", 'if created.get("sha256") != record.get("sha256") or', 'if False or'),
 ("C5b N2 bytes", 'or created.get("bytes") != record.get("bytes"):', 'or False:'),
 ("C6 N2 fileid", 'if not created.get("fileid"):', 'if False:'),
 ("C7 N3 landed fileId", 'if not isinstance(landed, str) or query.get("fileId") != [str(created.get("fileid"))]:', 'if False:'),
 ("C8 N3 clickedFrom", 'if not (isinstance(create.get("clickedFrom"), str) and "/apps/files/" in create["clickedFrom"]):', 'if False:'),
 ("C9a N3 fetched sha", 'if fetched.get("sha256") != created.get("sha256") or', 'if False or'),
 ("C9b N3 fetched status", 'or fetched.get("status") != 200:', 'or False:'),
 ("C10 N3 opened", 'if opened.get("state") != "ready" or opened.get("doc") != run.get("name"):', 'if False:'),
 ("C11 N4 click", 'if clicked.get("timedOut") is not False or "定位游標" not in (clicked.get("latency") or "") or "失敗" in (clicked.get("latency") or ""):', 'if False:'),
 ("C11c N4 click 失敗", 'or "失敗" in (clicked.get("latency") or ""):', 'or False:'),
 ("C12 N4 len keys", 'if len(keys) != len(MARK):', 'if False:'),
 ("C13a N4 rev", 'and int(k["revAfter"]) == int(k["revBefore"]) + 1', 'and True'),
 ("C13b N4 gen", 'and k.get("genBefore") == k.get("genAfter")):', 'and True):'),
 ("C14 N4 save", 'if save.get("outcome") != "saved":', 'if False:'),
 ("C15a N4 getStatus", 'if saved.get("getStatus") != 200 or not saved.get("bytes")', 'if False or not saved.get("bytes")'),
 ("C15b N4 bytes", 'or not saved.get("bytes") or', 'or False or'),
 ("C15c N4 markCount", 'saved.get("markCount") != 1', 'False'),
 ("C15d N4 describeError", 'or "describeError" in saved:', 'or False:'),
 ("C16 N5 fetched", 'if not isinstance(reopen.get("landed"), str) or re_fetched.get("sha256") != saved.get("sha256"):', 'if False:'),
 ("C17 N5 reopened", 'if re_opened.get("state") != "ready" or re_opened.get("doc") != run.get("name"):', 'if False:'),
 ("C18 N5 a11y", 'if a11y.get("offers") == "1" and MARK not in (a11y.get("text") or ""):', 'if False:'),
 ("C19 N6 no record", 'if not record:\n        bad["N6"]', 'if False:\n        bad["N6"]'),
 ("C20 N6 compare", 'bad["N6"] += [f"saved styles.xml {d}" for d in gen.compare(record, described)]', 'pass'),
 ("S1 arms x browsers", 'if strict and seen != wanted:', 'if False:'),
 ("S2a N9 buildId", 'if static.get("buildId") != CONTROL_BUILD_ID or', 'if False or'),
 ("S2b N9 page", 'or static.get("servedPage") != CONTROL_PAGE_SHA256:', 'or False:'),
 ("S3 N9 changedOutsideAllowed", 'if static.get("changedOutsideAllowed"):', 'if False:'),
 ("S4 N9 product touched", 'if (report.get("repoStatic") or {}).get("productPathsTouchedSinceStart"):', 'if False:'),
 ("S5 generator check", 'if not (static.get("blankGeneratorCheck") or {}).get("identical"):', 'if False:'),
 ("S6a N10 passed", 'if n10.get("passed") != n10.get("validated") or', 'if False or'),
 ("S6b N10 hashes", 'or not n10.get("hashesMatch") or', 'or False or'),
 ("S6c N10 validated>0", 'or not n10.get("validated"):', 'or False:'),
 ("S7 N12", 'if not (checks.get("N12") or {}).get("passed"):', 'if False:'),
 ("S8a N8 403", 'if ro.get("create", {}).get("status") != 403 or', 'if False or'),
 ("S8b N8 adminAfter", 'or ro.get("adminAfter", {}).get("fileid") or', 'or False or'),
 ("S8c N8 otherSees", 'or ro.get("otherSees") in (None, ""):', 'or False:'),
 ("S9 label", 'if report.get("label") != "counted":', 'if False:'),
 ("S10 hostDirty", 'if static.get("hostDirty"):', 'if False:'),
 ("S11a tools uncommitted", 'if repo.get("roundToolsUncommitted") or not repo.get("roundCommits"):', 'if False or not repo.get("roundCommits"):'),
 ("S11b roundCommits", 'if repo.get("roundToolsUncommitted") or not repo.get("roundCommits"):', 'if repo.get("roundToolsUncommitted") or False:'),
 ("S12 bindings", 'elif have != want:', 'elif False:'),
 ("S13 control red", 'if not (report.get("controlReport") or {}).get("red"):', 'if False:'),
 ("S14 redCorrupt red", 'if not (report.get("redCorruptReport") or {}).get("red"):', 'if False:'),
 ("S15 settings", 'if not settings.get("ok"):', 'if False:'),
]

def selftest(mod):
    """(baseline works, list of red cases that stayed red, list that went green, skipped)"""
    base = mod.score(copy.deepcopy(BASE), strict=True)
    stayed, green, skipped = [], [], []
    for name, mutate in mod.RED_CASES:
        r = copy.deepcopy(BASE)
        try:
            mutate(r)
        except Exception as e:
            skipped.append(name); continue
        (green if mod.score(r, strict=True)["works"] else stayed).append(name)
    return base["works"], stayed, green, skipped

print("checker-mutant census (a clause is GUARDED if neutralizing it turns >=1 red case GREEN, with the baseline still GREEN)")
unguarded = []
for cid, old, new in M:
    n = SRC.count(old)
    if n != 1:
        print(f"!! {cid}: pattern occurs {n} times"); continue
    mod = load(SRC.replace(old, new), cid.split()[0])
    works, stayed, green, skipped = selftest(mod)
    status = "GUARDED by " + ",".join(green) if green else "UNGUARDED"
    if not green: unguarded.append(cid)
    print(f"{cid:30} baseline={'GREEN' if works else 'RED'} {status}")
print("\nUNGUARDED:", len(unguarded), "of", len(M))
for u in unguarded: print("  ", u)

print("\nper red case: which rules fired (name prefix vs fired)")
import re
mod = load(SRC, "orig")
for name, mutate in mod.RED_CASES:
    r = copy.deepcopy(BASE); mutate(r)
    res = mod.score(r, strict=True)
    fired = set()
    for v in res["runs"].values():
        if v != "PASS": fired |= set(v)
    for pr in res["problems"]:
        m = re.match(r"(N\d+)", pr)
        if m: fired.add(m.group(1))
        elif pr.startswith("arms x"): fired.add("arms")
        elif "admin settings" in pr: fired.add("settings")
        elif "red case" in pr: fired.add("redcase")
    print(f"  {name:26} fired={sorted(fired)}")
