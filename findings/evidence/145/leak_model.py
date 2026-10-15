"""Model of e2-editor-app.js's delete accounting (holdsDelete / dispatchDelete / settleDelete) with one assumption:
a refused delete's settle is lost (the refusal reopens the document, so `send.document !== session.document`).
Predicts each merge record's key outcome and the number of deletes that reach the engine; compares with the report."""
import json, sys
r = json.load(open(sys.argv[1]))
U, A, H = 0, None, 0           # deletesUnanswered, heldDeletes.action, heldDeletes.count
ok = bad = 0
for c in r["cases"]:
    k = "bwd" if c.get("backward") else "fwd"
    typed = c["decision"] == "typed-merge"
    rev = int((c.get("afterKey") or {}).get("revision") or 0)
    if U > 0 and A == k:
        H += 1; pred_out, pred_deletes = "no-response", 0
    else:
        A = k; U += 1; pred_deletes = 1
        if c["outcome"] == "refused":
            pred_out = "refused"                                  # settle lost: U stays up, nothing released
        elif c["outcome"] == "verified-boundary-noop":
            U -= 1; H = 0; pred_out = "boundary"; pred_deletes = 0  # dropHeldDeletes
            if U == 0: A = None
        else:
            U -= 1; pred_out = "answered"; pred_deletes += H; H = 0   # releaseHeldDelete replays every held press as k
    obs_out = {"no-response": "no-response", "refused": "refused", "verified-boundary-noop": "boundary"}.get(c["outcome"], "answered")
    obs_deletes = None if obs_out in ("refused", "boundary") else rev - (1 if typed else 0)
    match = pred_out == obs_out and (obs_deletes is None or obs_deletes == pred_deletes)
    ok += match; bad += not match
    print(f"r{c['round']} {c['case']} {k} {c['decision']:<18} observed {obs_out:<11} rev {rev}  predicted {pred_out:<11} deletes {pred_deletes}  "
          f"{'ok' if match else 'MISMATCH'}  [U={U} A={A} H={H}]")
print(f"{ok} match, {bad} mismatch")
