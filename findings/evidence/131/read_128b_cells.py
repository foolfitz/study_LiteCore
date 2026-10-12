import json, sys
r = json.load(open(sys.argv[1]))
for run in r["runs"]:
    for arm in ("high", "low"):
        a = run.get(arm)
        if not a: continue
        s = [k.get("staleAfterCaretMs") for k in a.get("single", [])]
        q = [k.get("staleAfterCaretMs") for k in a.get("rapid", [])]
        print(run["browser"], arm, "single", s, "rapid", q, "persistent", (a.get("persistent") or {}).get("differing"))
