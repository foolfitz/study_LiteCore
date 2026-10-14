#!/usr/bin/env python3
"""One-off reader over probe_10_14o.py host reports (burst-1s and page-number); prints the fields the README quotes."""
import json, sys
for p in sys.argv[1:]:
    r = json.load(open(p))
    print("=====", r["browser"], "doc", r["doc"], "folder", r["folder"], "deletedFolder", r.get("deletedFolder"), "mkcol", r.get("mkcol"), "upload", r.get("upload"), "started", r["startedAt"], "ended", r.get("endedAt"))
    print("static", {k: (v if k != "shellBundle" else {"exit": v["exit"], "manifest": v["manifest"], "problems": v["problems"]}) for k, v in r["static"].items()})
    print("deskRepeat", r.get("deskRepeat"))
    for run in r["runs"]:
        print("--", run["arm"], "round", run["round"], "version", run.get("version"), "fatal", bool(run.get("fatal")), "preflight", json.dumps(run["preflight"], ensure_ascii=False))
        print("   landed", run.get("landed", {}).get("url") if isinstance(run.get("landed"), dict) else run.get("landed"), "secondsToOpened", run.get("secondsToOpened"))
        print("   host.lock", json.dumps((run.get("host") or {}).get("lock", run.get("host")), ensure_ascii=False)[:300], "| bar", json.dumps(run.get("bar"), ensure_ascii=False))
        if run["arm"] == "burst-1s":
            s = run["summary"]
            print("   keydowns", s["keydowns"], "focus", s["keydownFocus"], "beforeinputs", s["beforeinputs"], "readyAgainMs", s["readyAgainMs"], "generations", s["generations"], "toasts", s["toasts"])
            print("   nonPaintRequests", [(x["op"], x["action"], x["t"]) for x in s["nonPaintRequests"]])
            print("   editorResponses", json.dumps(s["editorResponses"], ensure_ascii=False))
            print("   latencyLabels", s["latencyLabels"])
            print("   stateBeforeKey", json.dumps(run.get("stateBeforeKey"), ensure_ascii=False))
            print("   settle.last", json.dumps((run.get("settle") or {}).get("last"), ensure_ascii=False))
            print("   limit", json.dumps(run.get("limit"), ensure_ascii=False))
        else:
            g = run["geometryAtOpen"]
            print("   rect", g["rect"], "psTextRect", g["psTextRect"], "content", g["content"], "font", g["fontSize"], "color", g["color"], "bg", g["background"], "elementAtCentre", g["elementAtCentre"], "display", g["display"], "root", g["root"], "inner", g["inner"])
            steps = run["steps"]
            texts = [x["text"] for x in steps]
            print("   steps", len(steps), "distinct texts", len(set(texts)), "hidden any", any(x.get("hidden") for x in steps))
            print("   texts", texts)
            print("   geometryAtEnd", run.get("geometryAtEnd", {}).get("text"), run.get("geometryAtEnd", {}).get("rect"))
            ops = {}
            for e in run.get("scrollLog", []):
                if e.get("k") == "rq" and e.get("rq", 0) < 900000:
                    ops[e["op"]] = ops.get(e["op"], 0) + 1
            print("   scrollLog rq<900000 ops", ops, "| askAtOpen parts", (run.get("askAtOpen") or {}), "| askAfterScroll", (run.get("askAfterScroll") or {}))
        print("   screenshots", run.get("screenshots"))
