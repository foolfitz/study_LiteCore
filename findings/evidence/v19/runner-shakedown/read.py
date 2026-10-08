#!/usr/bin/env python3
"""Reader for PREDICTION.md R1-R4 (written before the run).  Exit 0 all HIT, 1 a MISS, 3 a report missing."""
import json
import re
import sys
import zipfile
import hashlib
from pathlib import Path

D = Path(__file__).resolve().parent
SAVED = re.compile(r"已存出 [0-9]+(?:\.[0-9]+)? KB")
KEYS = {"wasmSha256", "workerSha256", "sessionSha256", "shellSha256", "htmlSha256", "pageSha256",
        "pageSourceSha256", "eshapeSha256", "nativeSha256"}
STARTING, REOPENED = "，正在重新載入…", "，已重新載入"


def load(name):
    try:
        return json.loads((D / name).read_text())
    except (OSError, ValueError) as error:
        print(f"NOT MEASURED: {name}: {error}")
        return None


def content_sha(path):
    with zipfile.ZipFile(path) as z:
        return hashlib.sha256(z.read("content.xml")).hexdigest()[:16]


def pair_ok(toasts):
    if not isinstance(toasts, list) or len(toasts) != 2 or not toasts[0].endswith(STARTING):
        return False
    return toasts[1].startswith(toasts[0][: -len(STARTING)] + REOPENED)


hits, missing = {}, []
for b in ("chrome", "firefox"):
    cases, control, m24 = load(f"cases-{b}.json"), load(f"cases-control-{b}.json"), load(f"m2-4-{b}.json")
    pair = load(f"pair-{b}.stdout.txt")
    if None in (cases, control, m24, pair):
        missing.append(b)
        continue
    by = {c["case"]: c for c in cases["cases"]}
    r1 = set(by) == {"C01", "C15", "C29", "Y01"} and all(c.get("pass") is True for c in by.values())
    for name in ("C01", "Y01"):
        c = by.get(name, {})
        r1 &= (c.get("outcome") == "verified-key-undo" and isinstance(c.get("toastsAtEnd"), list)
               and len(c["toastsAtEnd"]) == 2 and all(SAVED.fullmatch(t) for t in c["toastsAtEnd"]))
    for name, stage, posted in (("C15", "key-deadline", True), ("C29", "nothing-selected", False)):
        c = by.get(name, {})
        g = c.get("generation") or [None, None]
        kept = D / "cases-{}.docs".format(b) / f"{name}-r1-reopened.odt"
        r1 &= (c.get("outcome") == "refused" and c.get("stage") == stage and c.get("keyPosted") is posted
               and pair_ok((c.get("toastWindow") or {}).get("toasts"))
               and g[1] == str(int(g[0]) + 1) and kept.is_file()
               and (c.get("reopenedDocument") or {}).get("sha") == content_sha(kept))
    r2 = (pair.get("pairs") == 4 and pair.get("sameOrder") is True and pair.get("differ") == []
          and (D / f"pair-{b}.exit").read_text().strip() == "0")
    h = m24["cases"][0]
    cl = h.get("clauses") or {}
    presses = h.get("presses") or []
    slow = sum(1 for p in presses if not (0 <= (p.get("keyToUndoMs") or -1) < 1000))
    r3 = (len(presses) == 105 and all(p.get("completion") == "verified-key-undo" for p in presses)
          and cl.get("latency") is False and all(cl.get(k) is True for k in
                                                 ("noToast", "noToastThroughSave", "finalBytes", "finalText"))
          and isinstance(h.get("toastsAtEnd"), list) and len(h["toastsAtEnd"]) == 1
          and SAVED.fullmatch(h["toastsAtEnd"][0]) is not None and h.get("pass") is False
          and [k for k, v in cl.items() if v is False] == ["latency"])
    r4 = True
    for name, rep in (("cases", cases), ("cases-control", control), ("m2-4", m24)):
        bound = rep.get("bound") or {}
        r4 &= (set(bound) == KEYS and all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v)
                                          for v in bound.values())
               and rep.get("counted") is False and not rep.get("teardownError")
               and "error" not in (rep.get("observerAtEnd") or {})
               and (D / f"{name}-{b}.stderr.txt").stat().st_size == 0
               # no test browser (CDP port / geckodriver / marionette) alive after the step
               and (D / f"{name}-{b}.ps-after.txt.test-browsers").read_text().strip() == "")
    hits[b] = {"R1": r1, "R2": r2, "R3": r3, "R4": r4}
    print(f"{b}: " + "  ".join(f"{k}:{'HIT' if v else 'MISS'}" for k, v in hits[b].items())
          + f"  (M2-4 slow presses {slow}; toastsAtEnd {h.get('toastsAtEnd')})")
log = (D / "chain.log").read_text() if (D / "chain.log").is_file() else ""
exits = re.findall(r"exit=(\d+)", log)
print(f"chain exits {exits}")
if missing:
    print(f"VERDICT NOT MEASURED: {missing}")
    sys.exit(3)
ok = all(all(v.values()) for v in hits.values()) and exits and set(exits) == {"0"}
print("VERDICT " + ("HIT" if ok else "MISS"))
sys.exit(0 if ok else 1)
