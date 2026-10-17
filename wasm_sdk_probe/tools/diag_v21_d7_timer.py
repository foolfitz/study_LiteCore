#!/usr/bin/env python3
"""A0 of fable ruling 2 (spec SPEC-M3-link-batch-v21 §12.4 (b), (c)): a DIAGNOSTIC, NOT EVIDENCE.

D7's +500 ms read posted late in Firefox (2/192, then 6/192 outside 500±50; all carets equal).  Option A aims the
observer earlier; its premise -- that the lateness is additive, i.e. an earlier timer escapes the busy stretch -- was
not measured.  A0 measures it per press, with the unchanged runner on the unchanged mirror:

  run   imports run_v21_shakedown_item1 (its file is not edited), replaces `v21_item1_observer.SNIPPET` in memory with a
        copy that adds exactly what ruling 2 Q1 condition 3 names, and calls the runner's own main().  The copy:
          - on the same successful move-document-* reply, three silent sentinel timers at +440, +455, +470 that only
            record now() into a local object;
          - the page time of every paint / pageRectangles RESPONSE after that reply, into a local array (with the op
            and the request's own time, already in the observer's map);
          - both emitted inside the real `ask7` entry (`sentinels`, `paints`); no extra put(), no extra worker request;
          - the real ask stays at +500.
        A sidecar `a0-identity.json` names the patched snippet's sha256, this file's sha256 and the label.
  read  reads the A0 report and applies §12.4 (c) as pinned: informative iff >= 3 presses have the +500 read later
        than +520; then 470 iff max(sentinel470 - reply) <= 540, else 455 iff max(sentinel455 - reply) <= 540, else
        none; uninformative -> 455 ("premise unmeasured, maximum slack chosen").  It also prints the differential
        (a press whose +500 read is late and whose +470 sentinel is not) and each late press's paint replies.
  --self-test   synthetic records through `read`'s rule, red cases first (each outcome, and the refusals).

Usage (from wasm_sdk_probe/):
  python3 tools/diag_v21_d7_timer.py run --out DIR [--rounds 3] [--wait-lock S]
  python3 tools/diag_v21_d7_timer.py read REPORT.json
  python3 tools/diag_v21_d7_timer.py --self-test
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LABEL = "diagnostic, not evidence (fable ruling 2, A0; spec §12.4 (b))"
T_ARMS = [f"t-{k}-{c}-n{n}" for k in ("home", "end") for c in ("A1", "B2") for n in (1, 2, 3)]
SENTINELS = (440, 455, 470)

# (anchor in the committed SNIPPET, replacement); each anchor must occur exactly once.
PATCHES = [
    ("    const requests = new Map();\n",
     "    const requests = new Map();\n"
     "    const a0open = new Map();               // A0: forRq -> { sentinels, paints }\n"),
    ('      if (rq.op === "paint" || rq.op === "pageRectangles") return;\n',
     '      if (rq.op === "paint" || rq.op === "pageRectangles") {\n'
     '        if (a0open.size) { const tp = now(); for (const w of a0open.values()) w.paints.push({ op: rq.op, tRq: rq.t, t: tp }); }\n'
     '        return;\n'
     '      }\n'),
    ("              rev: r.revision ?? null });\n        return;\n",
     "              rev: r.revision ?? null,\n"
     "              sentinels: rq.ask7 ? (a0open.get(rq.forRq)?.sentinels ?? null) : undefined,\n"
     "              paints: rq.ask7 ? (a0open.get(rq.forRq)?.paints ?? null) : undefined });\n"
     "        if (rq.ask7) a0open.delete(rq.forRq);\n"
     "        return;\n"),
    ("        const forRq = d.requestId;\n        setTimeout(() => {\n",
     "        const forRq = d.requestId;\n"
     "        const a0w = { sentinels: {}, paints: [] };\n"
     "        a0open.set(forRq, a0w);\n"
     "        for (const ms of [440, 455, 470]) setTimeout(() => { a0w.sentinels[ms] = now(); }, ms);\n"
     "        setTimeout(() => {\n"),
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patched_snippet(snippet: str) -> str:
    out = snippet
    for anchor, repl in PATCHES:
        if out.count(anchor) != 1:
            raise SystemExit(f"the observer changed: anchor found {out.count(anchor)} times: {anchor!r}")
        out = out.replace(anchor, repl)
    if out.count("}, 500);") != 1:
        raise SystemExit("the real ask is not at +500 exactly once")
    return out


def cmd_run(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="diag_v21_d7_timer.py run")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--wait-lock", type=float, default=0.0)
    args = ap.parse_args(argv)
    import v21_item1_observer as obs1
    import run_v21_shakedown_item1 as runner
    original = obs1.SNIPPET
    obs1.SNIPPET = patched_snippet(original)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "a0-identity.json").write_text(json.dumps({
        "label": LABEL,
        "tool": "diag_v21_d7_timer.py", "toolSha256": sha256(Path(__file__).read_bytes()),
        "runner": "run_v21_shakedown_item1.py", "runnerSha256": sha256((HERE / "run_v21_shakedown_item1.py").read_bytes()),
        "observerFileSha256": sha256((HERE / "v21_item1_observer.py").read_bytes()),
        "committedSnippetSha256": sha256(original.encode("utf-8")),
        "patchedSnippetSha256": sha256(obs1.SNIPPET.encode("utf-8")),
        "arms": T_ARMS, "rounds": args.rounds, "sentinelsMs": list(SENTINELS),
    }, indent=1) + "\n")
    sys.argv = ["run_v21_shakedown_item1.py", "--browser", "firefox", "--arms", "d1", "--rounds", str(args.rounds),
                "--only", ",".join(T_ARMS), "--smoke", "--out", str(args.out), "--wait-lock", str(args.wait_lock)]
    return runner.main()


def presses_of(report: dict) -> list[dict]:
    rows = []
    for rec in (report.get("results", {}).get("d1", {}) or {}).get("rounds", []):
        if not rec.get("arm", "").startswith("t-"):
            continue
        for i, p in enumerate(rec.get("presses") or []):
            a, s = p.get("ask7") or {}, p.get("response") or {}
            if a.get("tPosted") is None or s.get("t") is None:
                rows.append({"arm": rec["arm"], "round": rec.get("round"), "i": i, "missing": True})
                continue
            sent = a.get("sentinels")
            rows.append({"arm": rec["arm"], "round": rec.get("round"), "i": i, "label": p.get("label"),
                         "d500": a["tPosted"] - s["t"],
                         "s": None if sent is None else {int(k): v - s["t"] for k, v in sent.items()},
                         "paints": [(q.get("op"), round(q["tRq"] - s["t"], 1), round(q["t"] - s["t"], 1))
                                    for q in (a.get("paints") or [])],
                         "caretEqual": a.get("caret") == s.get("caret"),
                         "foreignOk": (rec.get("foreign") or {}).get("ok")})
    return rows


def decide(rows: list[dict]) -> dict:
    """§12.4 (c), as pinned.  Refuses (raises) when the record cannot carry the rule."""
    if not rows:
        raise ValueError("no t-* presses in the report")
    missing = [r for r in rows if r.get("missing")]
    if missing:
        raise ValueError(f"{len(missing)} press(es) without a +500 read")
    blind = [r for r in rows if r["s"] is None or any(ms not in r["s"] for ms in SENTINELS)]
    if blind:
        raise ValueError(f"{len(blind)} press(es) without all three sentinels: the patch did not reach the page")
    late = [r for r in rows if r["d500"] > 520]
    max470 = max(r["s"][470] for r in rows)
    max455 = max(r["s"][455] for r in rows)
    differential = [r for r in late if r["s"][470] <= 540]
    out = {"presses": len(rows), "late500": len(late), "max470": round(max470, 1), "max455": round(max455, 1),
           "max440": round(max(r["s"][440] for r in rows), 1), "differential": len(differential)}
    if len(late) < 3:
        out.update(informative=False, constant=455, note="premise unmeasured, maximum slack chosen")
    elif max470 <= 540:
        out.update(informative=True, constant=470)
    elif max455 <= 540:
        out.update(informative=True, constant=455)
    else:
        out.update(informative=True, constant=None, note="no constant: the default stands, no evidence re-run")
    return out


def cmd_read(argv: list[str]) -> int:
    path = Path(argv[0])
    report = json.loads(path.read_text())
    rows = presses_of(report)
    print(f"A0 read of {path.name} -- {LABEL}")
    print(f"browser {report.get('browser')} {report.get('browserVersion')}; smoke {report.get('smoke')}; "
          f"snippetSha256 {[(x or '')[:16] for x in report.get('pages', {}).get('v21', {}).get('snippetSha256', [])]}")
    rounds = (report.get("results", {}).get("d1", {}) or {}).get("rounds", [])
    print(f"rounds {len(rounds)}; outcomes {sorted({str(r.get('outcome')) for r in rounds})}; "
          f"foreign over the limit: {sum(1 for r in rounds if (r.get('foreign') or {}).get('ok') is False)}")
    print("arm            r  i label  +500   +440   +455   +470  caret  paint replies after the move reply (op, tRq, t)")
    for r in rows:
        if r.get("missing"):
            print(f"{r['arm']:14} {r['round']} {r['i']} MISSING")
            continue
        s = r["s"] or {}
        f = lambda ms: f"{s[ms]:6.1f}" if ms in s else "   n/a"  # noqa: E731
        paints = "" if r["d500"] <= 505 else " ".join(f"({op[0]},{a},{b})" for op, a, b in r["paints"])
        print(f"{r['arm']:14} {r['round']} {r['i']} {r['label'] or '':5} {r['d500']:6.1f} {f(440)} {f(455)} {f(470)}  "
              f"{'eq' if r['caretEqual'] else 'NE!'}  {paints}")
    late = [r for r in rows if not r.get("missing") and r["d500"] > 505]
    if late:
        pre = [q for r in late for (op, a, b) in r["paints"] if b <= r["d500"]]
        print(f"paint replies before the +500 post, over {len(late)} presses later than +505: {len(pre)}"
              f"{'' if not pre else '; their t: ' + str(sorted(pre)[:20])}")
    try:
        verdict = decide(rows)
    except ValueError as error:
        print(f"REFUSED: {error}")
        return 2
    print("DECISION " + json.dumps(verdict, ensure_ascii=False))
    return 0


def self_test() -> int:
    def row(d500, s440, s455, s470):
        return {"arm": "t-x", "round": 1, "i": 0, "label": "x", "d500": d500,
                "s": {440: s440, 455: s455, 470: s470}, "paints": [], "caretEqual": True}
    base = [row(500.3, 440.2, 455.2, 470.2) for _ in range(20)]
    cases = [
        ("additive: late +500, early sentinels on time -> 470", base + [row(556, 440.5, 455.4, 470.3)] * 3, 470),
        ("470 held to 545, 455 not -> 455", base + [row(556, 440.5, 455.4, 545.0)] * 3, 455),
        ("all held to the same end -> none", base + [row(556, 556.0, 556.0, 556.0)] * 3, None),
        ("only two late -> uninformative, 455", base + [row(556, 556.0, 556.0, 556.0)] * 2, 455),
        ("470 exactly at 540 -> 470 (inclusive)", base + [row(556, 440.5, 455.4, 540.0)] * 3, 470),
    ]
    bad = 0
    for name, rows, want in cases:
        got = decide(rows)["constant"]
        ok = got == want
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {name}: {got}")
    refusals = [
        ("empty", []),
        ("a press without its read", base + [{"arm": "t-x", "round": 1, "i": 1, "missing": True}]),
        ("sentinels absent (patch did not reach the page)", base + [{**row(556, 0, 0, 0), "s": None}]),
        ("one sentinel absent", base + [{**row(556, 0, 0, 0), "s": {440: 440.1, 455: 455.1}}]),
    ]
    for name, rows in refusals:
        try:
            decide(rows)
            print(f"BAD {name}: not refused")
            bad += 1
        except ValueError as error:
            print(f"ok  {name}: refused ({error})")
    patched = patched_snippet(__import__("v21_item1_observer").SNIPPET)
    for needle in ("a0open", "[440, 455, 470]", "sentinels:", "paints:"):
        if needle not in patched:
            print(f"BAD patched snippet lacks {needle!r}")
            bad += 1
    print(f"self-test: {len(cases) + len(refusals) - bad}/{len(cases) + len(refusals)} ok" + (" -- FAILED" if bad else ""))
    return 1 if bad else 0


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--self-test":
        return self_test()
    if len(sys.argv) >= 2 and sys.argv[1] == "run":
        return cmd_run(sys.argv[2:])
    if len(sys.argv) == 3 and sys.argv[1] == "read":
        return cmd_read(sys.argv[2:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
