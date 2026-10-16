#!/usr/bin/env python3
"""Read round 2's out/<arm>/run*/summary.json (and round 1's P1 summaries for
the round-1 corpus) and write out/RESULTS.md and out/results.json.

Usage: aggregate2.py ROUND2_OUT ROUND1_OUT MD4C_SCAN_JSONL

Nothing is judged by hand: every column comes from the per-run summaries or
the md4c scan's JSON lines. "agree" compares the after-structure signatures
(md_structure.py) of the runs of one arm.
"""

import glob
import json
import os
import sys


def load(out_dir, prefix=""):
    arms = {}
    for path in sorted(glob.glob(os.path.join(out_dir, prefix + "*", "run*", "summary.json"))):
        with open(path) as handle:
            s = json.load(handle)
        arms.setdefault(s["arm"]["id"], []).append(s)
    for runs in arms.values():
        runs.sort(key=lambda r: r["run"])
    return arms


def span(values, fmt="%.1f"):
    values = [v for v in values if v is not None]
    if not values:
        return "-"
    lo, hi = min(values), max(values)
    return (fmt % lo) if lo == hi else (fmt + "-" + fmt) % (lo, hi)


def vals(runs, f):
    return ",".join(sorted({str(f(r)) for r in runs}))


def agree(runs):
    sigs = [r.get("afterSignatureSha256") for r in runs]
    if not sigs or any(s is None for s in sigs):
        return "n/a"
    return "%d/%d" % (len(sigs), len(sigs)) if len(set(sigs)) == 1 else "%d distinct of %d" % (len(set(sigs)), len(sigs))


def undo_delta(r):
    u = r.get("undo", {})
    return u.get("countAfter", 0) - u.get("countBefore", 0)


def new_actions(r):
    return "/".join(r.get("undo", {}).get("newActions", [])) or "-"


def readback_ok(runs):
    flags = [r.get("positionReadbackAsExpected") for r in runs]
    if all(f is None for f in flags):
        return "recorded"
    return "yes" if all(flags) else "NO"


def blocked(runs):
    return ",".join(r["blocked"]["step"] for r in runs if "blocked" in r) or "-"


def images_of(summary_after):
    """(linked, embedded) image counts in a summary's 'after' (round 1 or 2 shape)."""
    if not summary_after:
        return None
    imgs = summary_after.get("images")
    if isinstance(imgs, int):
        return None
    linked = sum(1 for i in imgs if i.get("href") and not i.get("embedded"))
    embedded = sum(1 for i in imgs if i.get("embedded"))
    return linked, embedded


def t1_rows(arms):
    lines = ["| arm | read-back (3 runs) | ok | returned | call ms | undo +n (action) | Undo to restore | agree | blocked |",
             "|---|---|---|---|---|---|---|---|---|"]
    import re
    order = lambda a: tuple(int(n) for n in re.findall(r"\d+", a))  # noqa: E731  P8 < P9 < P10 < P11
    for arm_id, runs in sorted(arms.items(), key=lambda kv: order(kv[0])):
        if not arm_id.startswith("T1-"):
            continue
        lines.append("| %s | %s | %s | %s | %s | %s (%s) | %s | %s | %s |" % (
            arm_id, " / ".join(sorted({repr(r.get("positionReadback")) for r in runs})), readback_ok(runs),
            vals(runs, lambda r: r.get("pasteReturned")), span([r.get("pasteCallMs") for r in runs]),
            vals(runs, undo_delta), vals(runs, new_actions), vals(runs, lambda r: r.get("undoStepsToRestore")),
            agree(runs), blocked(runs)))
    return lines


def t2_rows(arms):
    lines = ["| arm | read-back | ok | .uno:Paste state before | returned | doc changed (reader / fingerprint) | "
             "undo count before->after | undo payload changed | restore | agree | blocked |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm_id, runs in arms.items():
        if not arm_id.startswith("T2-"):
            continue
        lines.append("| %s | %s | %s | %s | %s | %s / %s | %s | %s | %s | %s | %s |" % (
            arm_id, " / ".join(sorted({repr(r.get("positionReadback")) for r in runs})), readback_ok(runs),
            vals(runs, lambda r: (r.get("pasteStateBefore") or "").replace(".uno:Paste=", "")),
            vals(runs, lambda r: r.get("pasteReturned")),
            vals(runs, lambda r: None if "afterSameAsBefore" not in r else not r["afterSameAsBefore"]),
            vals(runs, lambda r: None if "afterSameFingerprintAsBefore" not in r else not r["afterSameFingerprintAsBefore"]),
            vals(runs, lambda r: "%s->%s" % (r.get("undo", {}).get("countBefore"), r.get("undo", {}).get("countAfter"))),
            vals(runs, lambda r: r.get("undo", {}).get("payloadChanged")),
            vals(runs, lambda r: r.get("undoStepsToRestore")), agree(runs), blocked(runs)))
    return lines


def md4c_decision(scan):
    if scan["imagesNonData"]:
        return "REMOTE_IMAGE"
    if scan["textNonBlank"] == 0:
        return "NO_TEXT"
    return "pass"


def native_of(runs):
    """What Writer did natively at P1, over the runs of one arm."""
    out = {"runs": len(runs)}
    imgs = []
    for r in runs:
        if "afterImages" in r:      # round 2
            imgs.append((sum(1 for i in r["afterImages"] if i["href"] and not i["embedded"]),
                         sum(1 for i in r["afterImages"] if i["embedded"])))
        else:                       # round 1 keeps the whole after summary
            imgs.append(images_of(r.get("after")))
    out["images"] = ",".join(sorted({("%d linked/%d embedded" % i) if i else "n/a (large)" for i in imgs}))
    # Round 2: listener (18765) requests + closer (18768) connections; round 1:
    # listener requests (M11b) + tarpit (18766) accepts (M11c). Round 1's M11
    # (port 9, refused) has no listener: its connect() is only in its strace.
    out["requests"] = ",".join(sorted({str(len(r.get("listenerRequests", [])) + len(r.get("closerEvents", [])) +
                                           sum(1 for e in r.get("tarpit", []) if e.get("event") == "accept"))
                                       for r in runs}))
    out["requestPaths"] = sorted({"%s %s" % (q.get("method", "GET"), q["path"]) for r in runs
                                  for q in r.get("listenerRequests", [])} |
                                 {"connect:18768" for r in runs if r.get("closerEvents")} |
                                 {"connect:18766" for r in runs if r.get("tarpit")})
    out["changed"] = ",".join(sorted({str(not r.get("afterSameAsBefore")) for r in runs}))
    out["undo"] = ",".join(sorted({str(undo_delta(r)) for r in runs}))
    return out


def t3_rows(scans, r2_arms, r1_arms):
    lines = ["| item | md4c images non-data / data | text outside images (ASCII-blank / Unicode-ws) | "
             "HTML blocks / HTML text | spec 9.3 rule says | native at P1: images | native: requests to the "
             "local listeners per run | native: document changed | native: undo +n | runs |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for scan in scans:
        item = scan["file"][:-3]
        runs = r2_arms.get("T3-P1-" + item) or r1_arms.get("P1-" + item)
        native = native_of(runs) if runs else None
        lines.append("| %s | %d / %d | %d / %d | %d / %d | %s | %s | %s | %s | %s | %s |" % (
            item, scan["imagesNonData"], scan["imagesData"], scan["textNonBlank"], scan["textNonUnicodeWs"],
            scan["htmlBlocks"], scan["htmlText"], md4c_decision(scan),
            native["images"] if native else "not pasted",
            ("%s %s" % (native["requests"], native["requestPaths"])) if native else "-",
            native["changed"] if native else "-", native["undo"] if native else "-",
            ("%d (%s)" % (native["runs"], "round 2" if ("T3-P1-" + item) in r2_arms else "round 1"))
            if native else "-"))
    return lines


def main(argv):
    out2, out1, scan_path = argv[1:4]
    r2 = load(out2, "T")
    r1 = load(out1, "P1-")
    with open(scan_path) as handle:
        scans = [json.loads(line) for line in handle if line.strip()]
    lines = ["# Round 2 results (generated by tool/aggregate2.py from out/*/run*/summary.json and "
             "out/T3-md4c/scan.jsonl)", "",
             "## T1: positions round 1 did not measure", ""] + t1_rows(r2) + [
             "", "## T2: pastes that might add no undo action", ""] + t2_rows(r2) + [
             "", "## T3: md4c classification against native pastes", "",
             "Round-1 corpus items take their native columns from round 1's `out/P1-<item>/` (3 runs each); "
             "C1 and M8-utf16le were not markdown pastes and are not scanned.", ""] + t3_rows(scans, r2, r1)
    lines += ["", "## Structure after the paste (run 1 of each arm; tool/md_structure.py)", ""]
    for arm_id, runs in r2.items():
        first = runs[0]
        lines += ["### " + arm_id, "",
                  "before: " + (first.get("beforeHuman", "").splitlines() or [""])[0], "", "```",
                  first.get("afterHuman", ""), "```", ""]
        reqs = [len(r.get("listenerRequests", [])) for r in runs]
        if any(reqs):
            lines += ["listener requests per run: %s; paths: %s" % (
                reqs, sorted({q["method"] + " " + q["path"] for r in runs for q in r["listenerRequests"]})), ""]
        closes = [len(r.get("closerEvents", [])) for r in runs]
        if any(closes):
            lines += ["connections to the closing socket (18768) per run: %s" % closes, ""]
    rows = {}
    for arm_id, runs in r2.items():
        rows[arm_id] = [{k: r.get(k) for k in (
            "run", "returncode", "positionReadback", "positionReadbackAsExpected", "pasteReturned", "pasteCallMs",
            "undo", "undoStepsToRestore", "afterSameAsBefore", "afterSameFingerprintAsBefore",
            "afterSignatureSha256", "readOnlyAtOpen", "pasteStateBefore", "pasteStateAfter",
            "listenerRequests", "closerEvents", "waitedForOtherLokSeconds", "processSeconds", "blocked")}
            for r in runs]
    with open(os.path.join(out2, "results.json"), "w") as handle:
        json.dump({"arms": rows, "md4c": scans}, handle, ensure_ascii=False, indent=1)
    with open(os.path.join(out2, "RESULTS.md"), "w") as handle:
        handle.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
