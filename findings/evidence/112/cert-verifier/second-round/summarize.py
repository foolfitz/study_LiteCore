#!/usr/bin/env python3
"""Reads the round's reports (e*-NN.json in this directory) and prints the results table and the reading by the rule
in PREDICTION.md.  The reading is the printed SUMMARY lines; the exit code is always 0.

Per launch (P0, validity): >= 500 fetches ok; the control fetch recorded as net::ERR_CONNECTION_REFUSED; net log
parsed, complete, and reaching the end of the window; >= 1 HTTP/2 session to the origin.  A void launch is listed and
not counted; an arm with more than 25 % void launches is void.

Per launch (measures): resets = clusters of SOCKET_POOL_CLOSING_SOCKET "Cert verifier changed" (verifier resets);
"early" = t < 1.0 s, "mid" = 1.0 <= t < 6.0 s, "late" = t >= 6.0 s within the window; a hit = a
Network.loadingFailed net::ERR_CERT_VERIFIER_CHANGED between loop start and loop stop; afterFirstRequest = resets at
or after the first request (E3's quantity).
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ["e1", "e2", "e3", "e5", "e6"]
ORIGIN_HOST = "litecore.ddev.site:8443"
SEED = "clientservices.googleapis.com/chrome-variations/seed"
CHECKIN = "android.clients.google.com/checkin"
UPDATE_CHECK = "clients2.google.com/service/update2/crx"


def load() -> dict[str, list[dict]]:
    by_arm: dict[str, list[dict]] = {a: [] for a in ARMS}
    for p in sorted(HERE.glob("e*-*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        arm = r.get("arm")
        if arm in by_arm:
            by_arm[arm].append(r)
    return by_arm


def measure(r: dict) -> dict:
    nl = r.get("netlog") or {}
    ctl = r.get("control") or {}
    ok = (r.get("counters") or {}).get("ok") or 0
    control_ok = any(f.get("errorText") == "net::ERR_CONNECTION_REFUSED" for f in ctl.get("loadingFailed", []))
    window_end = r.get("loopStoppedT") or r.get("seconds")
    log_reaches_end = nl.get("lastEventT") is not None and nl["lastEventT"] >= (window_end or 0) - 1.0
    origin_sessions = [s for s in nl.get("h2Sessions", []) if s.get("host") == ORIGIN_HOST]
    void = []
    if ok < 500:
        void.append(f"fetches ok {ok} < 500")
    if not control_ok:
        void.append("control failure not recorded")
    if not nl.get("parsedOk"):
        void.append("net log not parsed")
    if not nl.get("complete"):
        void.append("net log not complete")
    if not log_reaches_end:
        void.append("net log ends before the window")
    if not origin_sessions:
        void.append("no HTTP/2 session to the origin")
    resets = [x for x in nl.get("resets", []) if "pool-closing:Cert verifier changed" in x.get("kinds", {})
              and x["t"] <= (window_end or 0)]
    db_resets = [x for x in nl.get("resets", []) if any("database" in k for k in x.get("kinds", {}))]
    first_req = r.get("firstRequestT") or 0
    hits = [f for f in r.get("loadingFailed", []) if f.get("errorText") == "net::ERR_CERT_VERIFIER_CHANGED"
            and (r.get("loopStartedT") or 0) <= f["t"] <= (r.get("loopStoppedT") or 1e9)]
    urls = [b["url"] for b in nl.get("browserRequests", [])]
    return {
        "label": r["label"], "arm": r["arm"], "void": void,
        "resetTimes": [x["t"] for x in resets],
        "early": [x["t"] for x in resets if x["t"] < 1.0],
        "mid": [x["t"] for x in resets if 1.0 <= x["t"] < 6.0],
        "late": [x["t"] for x in resets if x["t"] >= 6.0],
        "afterFirstRequest": [x["t"] for x in resets if x["t"] >= first_req],
        "midOriginWentAway": [x["t"] for x in resets if 1.0 <= x["t"] < 6.0 and x.get("originSessionWentAway")],
        "dbResets": [x["t"] for x in db_resets],
        "hits": [f["t"] for f in hits],
        "timeQuery": bool(nl.get("timeQuery")),
        "seed": any(SEED in u for u in urls),
        "checkin": any(CHECKIN in u for u in urls),
        "updateCheck": any(UPDATE_CHECK in u for u in urls),
        "firstRequestT": first_req, "loopStartedT": r.get("loopStartedT"), "fetchesOk": ok,
    }


def pct(k: int, n: int) -> str:
    return f"{k}/{n}" if n else "0/0"


def main() -> int:
    by_arm = load()
    rows = {a: [measure(r) for r in rs] for a, rs in by_arm.items()}
    print("| arm | n | valid | >=1 reset | early (<1 s) | mid (1-6 s) | late (>=6 s) | mid resets took the origin's"
          " session | mid t: min / median / max | resets after first request | hits (launches) | time query | seed |"
          " checkin | update check |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    arm_stats: dict[str, dict] = {}
    for a in ARMS:
        ms = rows[a]
        valid = [m for m in ms if not m["void"]]
        n, v = len(ms), len(valid)
        mids = [t for m in valid for t in m["mid"]]
        st = {
            "n": n, "valid": v, "voidFrac": (n - v) / n if n else 0.0,
            "anyReset": sum(1 for m in valid if m["resetTimes"]),
            "early": sum(1 for m in valid if m["early"]),
            "mid": sum(1 for m in valid if m["mid"]),
            "late": sum(1 for m in valid if m["late"]),
            "midOrigin": sum(1 for m in valid if m["midOriginWentAway"]),
            "afterFirst": sum(1 for m in valid if m["afterFirstRequest"]),
            "hits": sum(1 for m in valid if m["hits"]),
            "timeQuery": sum(1 for m in valid if m["timeQuery"]),
            "seed": sum(1 for m in valid if m["seed"]),
            "checkin": sum(1 for m in valid if m["checkin"]),
            "updateCheck": sum(1 for m in valid if m["updateCheck"]),
            "midTimes": sorted(mids),
        }
        arm_stats[a] = st
        mid_s = (f"{min(mids):.3f} / {statistics.median(mids):.3f} / {max(mids):.3f}" if mids else "—")
        print(f"| {a} | {n} | {v} | {pct(st['anyReset'], v)} | {pct(st['early'], v)} | {pct(st['mid'], v)} | "
              f"{pct(st['late'], v)} | {pct(st['midOrigin'], v)} | {mid_s} | {pct(st['afterFirst'], v)} | "
              f"{pct(st['hits'], v)} | {pct(st['timeQuery'], v)} | {pct(st['seed'], v)} | {pct(st['checkin'], v)} | "
              f"{pct(st['updateCheck'], v)} |")
    print()
    for a in ARMS:
        for m in rows[a]:
            if m["void"]:
                print(f"VOID {m['label']}: {'; '.join(m['void'])}")
    for a in ARMS:
        if arm_stats[a]["n"] and arm_stats[a]["voidFrac"] > 0.25:
            print(f"ARM VOID {a}: {arm_stats[a]['n'] - arm_stats[a]['valid']} of {arm_stats[a]['n']} launches void")
    print()
    # ---- the reading rule (PREDICTION.md, "Reading")
    e1, e2, e3, e5, e6 = (arm_stats[a] for a in ARMS)

    def frac(st, key):
        return st[key] / st["valid"] if st["valid"] else 0.0

    def armok(st):
        return st["valid"] >= 1 and st["voidFrac"] <= 0.25

    lines = []
    # V1 the phenomenon under the runners' flags
    v1 = armok(e1) and frac(e1, "mid") >= 0.9
    lines.append(f"V1 phenomenon (E1 mid reset in >= 90 %): {'HOLDS' if v1 else 'FAILS'} "
                 f"({pct(e1['mid'], e1['valid'])}; took the origin's session {pct(e1['midOrigin'], e1['valid'])}; "
                 f"late {pct(e1['late'], e1['valid'])}; hits {pct(e1['hits'], e1['valid'])})")
    # V2 component-update flag
    if armok(e2):
        v2 = frac(e2, "mid") >= 0.75
        lines.append(f"V2 --disable-component-update does NOT remove the mid reset: {'HOLDS' if v2 else 'FAILS'} "
                     f"({pct(e2['mid'], e2['valid'])})")
    # V3 the idle wait
    if armok(e3):
        v3a = frac(e3, "mid") >= 0.75
        v3b = e3["afterFirst"] == 0
        lines.append(f"V3a the mid reset is time-triggered (present in E3 without any request): "
                     f"{'HOLDS' if v3a else 'FAILS'} ({pct(e3['mid'], e3['valid'])})")
        lines.append(f"V3b no reset at or after the first request when it comes 5 s after launch: "
                     f"{'HOLDS' if v3b else 'FAILS'} ({pct(e3['afterFirst'], e3['valid'])}; hits "
                     f"{pct(e3['hits'], e3['valid'])})")
    # V4 the network-time push
    if armok(e5):
        v4a = e5["early"] == 0
        v4b = frac(e5, "mid") >= 0.75
        lines.append(f"V4a no early reset with CertVerificationNetworkTime disabled: {'HOLDS' if v4a else 'FAILS'} "
                     f"({pct(e5['early'], e5['valid'])})")
        lines.append(f"V4b the mid reset persists with CertVerificationNetworkTime disabled (prediction): "
                     f"{'HOLDS' if v4b else 'FAILS'} ({pct(e5['mid'], e5['valid'])})"
                     + ("" if v4b else " -> the mid reset IS a network-time push"))
    # V5 background networking
    if armok(e6):
        v5a = e6["timeQuery"] == 0 and e6["seed"] == 0 and e6["updateCheck"] == 0
        lines.append(f"V5a --disable-background-networking removes the time query, the seed and the update check: "
                     f"{'HOLDS' if v5a else 'FAILS'} (time query {pct(e6['timeQuery'], e6['valid'])}, seed "
                     f"{pct(e6['seed'], e6['valid'])}, update check {pct(e6['updateCheck'], e6['valid'])}, checkin "
                     f"{pct(e6['checkin'], e6['valid'])})")
        lines.append(f"V5b resets with --disable-background-networking: early {pct(e6['early'], e6['valid'])}, mid "
                     f"{pct(e6['mid'], e6['valid'])}, late {pct(e6['late'], e6['valid'])}")
    # Decision mapping
    decision = "D3 no recommendation: the shakedown red stays unexplained"
    flag_arms = [(a, f) for a, f in (("e5", "--disable-features=CertVerificationNetworkTime"),
                                     ("e6", "--disable-background-networking"))
                 if armok(arm_stats[a]) and arm_stats[a]["valid"] >= 12
                 and arm_stats[a]["anyReset"] == 0]
    all_mid = [t for a in ("e1", "e2", "e5", "e6") for t in arm_stats[a]["midTimes"]]
    no_late = all(arm_stats[a]["late"] == 0 for a in ("e1", "e2", "e5", "e6") if armok(arm_stats[a]))
    if v1 and flag_arms:
        decision = (f"D1 a flag removes every reset in its window: {', '.join(f for _, f in flag_arms)}"
                    f" -> recommend the first; chain prediction: 0 ERR_CERT_VERIFIER_CHANGED in the locks shakedown")
    elif v1 and no_late and all_mid and max(all_mid) <= 4.0 and armok(e3) and e3["afterFirst"] == 0:
        decision = (f"D2 no flag removes the mid reset; it is time-triggered, max observed {max(all_mid):.3f} s, "
                    f"none late -> recommend a 5 s wait after launch in ChromeSession; chain prediction the same")
    for line in lines:
        print("SUMMARY", line)
    print("SUMMARY", decision)
    (HERE / "summary.json").write_text(json.dumps({"arms": arm_stats, "launches": rows, "decision": decision,
                                                   "lines": lines}, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
