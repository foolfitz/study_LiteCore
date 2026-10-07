#!/usr/bin/env python3
"""What the engine's fontconfig is asked, and answers, while the red document is laid out (PREDICTION.md).

Four cold Chrome sessions, one at a time, each opening ONE document as its first: {A the fixture, D the variant} x
{e2-editor-v17, e2-editor-v17-cjk-r5-ab}.  Per session: the cutover page repointed to the profile (as
compare_layout_corpus.measure does), with probe_fc_debug's two page edits (a Worker wrapper keeping the forwarded
stdout/stderr; `debug: true`) and its loader edit (ENV.FC_DEBUG), served from a scratch mirror (dist/ is not
written; the shipped loader's bytes are checked before and after); bands read with the corpus tool's own
settle/runs; Match blocks parsed with probe_fc_debug's own parser.  Composed from existing functions only; no tool
file is edited.  Writes fc-request.json, <profile>-<variant>-fc-log.txt and summary.txt beside this file.  It prints
facts; the readings are applied in RESULT.md against PREDICTION.md.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE.parents[4] / "wasm_sdk_probe"
sys.path.insert(0, str(PROBE / "tools"))
import compare_layout_corpus as clc  # noqa: E402
import probe_fc_debug as fcd  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

PROFILES = ("e2-editor-v17", "e2-editor-v17-cjk-r5-ab")
DOCS = {"A": PROBE / "test-docs/e1/paragraph-content.odt",
        "D": PROBE / "build/fc-request/D-western-liberation-mono.odt"}
EXPECTED = {"A": "920ca5d51ef5e52605af16e8aa98178daee87ec3ab309bcc6ea94ccfd248d28b",
            "D": "42faf12445ecaa68350c9c3dec554fa1e6761f337deb8d66a13bc670a5dd1fe2"}
NAME = "c000.odt"
CONFD = re.compile(r"Loading config file from \S*/conf\.d/(\S+?) done")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def one_session(profile: str, variant: str) -> dict:
    root = PROBE / "dist"
    lagging = pp.shell_lagging_source(root)
    if lagging:
        raise SystemExit(f"served from dist/ but not their source: {lagging}")
    document = DOCS[variant].read_bytes()
    if sha256(document) != EXPECTED[variant]:
        raise SystemExit(f"{DOCS[variant]} is not the document PREDICTION.md names")
    loader_path = root / "profiles" / profile / "probe.js"
    loader_before = loader_path.read_bytes()
    page, pin_before, wasm = pp.repointed_page(pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8"), profile,
                                               root / "profiles" / profile / "sdk-manifest.json")
    page_measured = page
    page = fcd.once(page, fcd.IMPORT, fcd.IMPORT + fcd.CAPTURE, "page")
    page = fcd.once(page, "createDocumentEngine({", "createDocumentEngine({ debug: true,", "page")
    loader = fcd.once(loader_before.decode("utf-8"), fcd.PRERUN,
                      f'{fcd.PRERUN};ENV.FC_DEBUG="{fcd.FC_DEBUG}"', str(loader_path))
    mirror = Path(tempfile.mkdtemp(prefix="fc-request-")) / "root"
    served_loader = f"profiles/{profile}/probe.js"
    pp.build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8"),
                                   served_loader: loader.encode("utf-8")})
    if ((mirror / served_loader).is_symlink() or (mirror / served_loader).parent.is_symlink()
            or (mirror / served_loader).read_bytes() == loader_before):
        raise SystemExit(f"the loader override did not take in {mirror}")
    folder = mirror / "layout-corpus"           # new, under the mirror ROOT: a real directory
    folder.mkdir()
    (folder / NAME).write_bytes(document)
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(PROBE / "web" / "serve.py"), "--port", str(port),
                               "--root", str(mirror)], cwd=PROBE,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = {"profile": profile, "variant": variant, "document": str(DOCS[variant].relative_to(PROBE)),
           "documentSha256": sha256(document), "pinBefore": pin_before, "wasm": wasm[:16],
           "repointedPageSha256": sha256(page_measured.encode("utf-8")),
           "servedPageSha256": sha256(page.encode("utf-8")),
           "shippedLoaderSha256": sha256(loader_before), "servedLoaderSha256": sha256(loader.encode("utf-8")),
           "fcDebug": fcd.FC_DEBUG, "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = pp.ChromeSession("cold")
        pp.navigate(session, base)
        out["boot"] = (pp.wait_for(session, lambda s: s.get("state") == "ready", 300) or {}).get("state")
        out["navigatorLanguages"] = pp.evaluate(session, fcd.LANGUAGES)
        out["logLinesAtReady"] = pp.evaluate(session, fcd.LOG_LEN)
        pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", f"./layout-corpus/{NAME}").replace("ARG_NAME", NAME))
        opened = pp.wait_for(session, lambda s: (s.get("doc") or "") == NAME and s.get("state") in (
            "ready", "stopped", "expired", "recoverable-error", "restart-required"), 120)
        out["state"] = (opened or {}).get("state")
        if out["state"] == "ready":
            scan = clc.settle(session)
            out.update({"canvas": [scan.get("width"), scan.get("height")], "page": scan.get("page"),
                        "unsettled": scan.get("unsettled", False), "runs": clc.runs(scan.get("counts") or [])})
        log = fcd.read_log(session)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        server.wait(timeout=10)
    if loader_path.read_bytes() != loader_before:
        raise SystemExit(f"{loader_path} changed during the run")
    (HERE / f"{profile}-{variant}-fc-log.txt").write_text(
        "".join(f"{level}\t{text}\n" for level, text in log), encoding="utf-8")
    lines = [text for level, text in log if level == "stdout"]
    stdout_index = [n for n, (level, _) in enumerate(log) if level == "stdout"]
    blocks = fcd.match_blocks(lines)
    for block in blocks:
        block["phase"] = "fixture" if stdout_index[block["line"]] >= (out["logLinesAtReady"] or 0) else "boot"
    out.update({"completedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "logLines": len(log),
                "stderr": [text for level, text in log if level == "stderr"][:200],
                "confdLoaded": sorted({m.group(1) for t in lines if (m := CONFD.search(t))}),
                "matchBlocks": blocks})
    return out


def key(block: dict) -> tuple:
    return (tuple(block["askedFamily"]), tuple(block["askedLang"]), block["askedCharset"])


def answer(block: dict) -> tuple:
    return (block["bestFamily"][0] if block["bestFamily"] else None,
            Path(block["bestFile"][0]).name if block["bestFile"] else None, block["bestIndex"])


def census(result: dict) -> dict:
    """Fixture-phase blocks: key -> list of answers (a list, so a key asked twice shows twice)."""
    out = defaultdict(list)
    for block in result["matchBlocks"]:
        if block["phase"] == "fixture":
            out[key(block)].append(answer(block))
    return dict(out)


def show(k: tuple) -> str:
    family, lang, charset = k
    return f"family {list(family)[:6]}{' ...' if len(family) > 6 else ''} lang {list(lang)} charset {charset}"


def summarize(results: dict) -> list[str]:
    lines = []
    for (profile, variant), r in results.items():
        runs = r.get("runs") or []
        fixture = sum(1 for b in r["matchBlocks"] if b["phase"] == "fixture")
        lines.append(f"{profile} {variant}: boot {r['boot']} state {r['state']} languages {r['navigatorLanguages']} "
                     f"confd {len(r['confdLoaded'])} logLines {r['logLines']} matchBlocks {len(r['matchBlocks'])} "
                     f"(fixture {fixture}) bands {len(runs)} unsettled {r.get('unsettled')} "
                     f"band10 {runs[10] if len(runs) > 10 else None}")
    for variant in DOCS:
        ra, rb = (results[(p, variant)].get("runs") or [] for p in PROFILES)
        tops = [b[0] - a[0] for a, b in zip(ra, rb)]
        lines.append(f"{variant}: bands {len(ra)} vs {len(rb)}; control-minus-v17 top per band {tops}; "
                     f"max |diff| {max((abs(t) for t in tops), default=None) if len(ra) == len(rb) else None}")
    c = {k: census(r) for k, r in results.items()}
    for profile in PROFILES:
        a, d = c[(profile, "A")], c[(profile, "D")]
        lines.append(f"{profile}: keys only in A (fixture phase) {len(set(a) - set(d))}, only in D {len(set(d) - set(a))}")
        for k in sorted(set(a) - set(d)):
            lines.append(f"  A-only {show(k)} -> {a[k]}")
        for k in sorted(set(d) - set(a)):
            lines.append(f"  D-only {show(k)} -> {d[k]}")
    for variant in DOCS:
        x, y = (c[(p, variant)] for p in PROFILES)
        lines.append(f"{variant} across arms: keys only in v17 {len(set(x) - set(y))}, only in control "
                     f"{len(set(y) - set(x))}, shared {len(set(x) & set(y))}")
        for k in sorted(set(x) - set(y)):
            lines.append(f"  v17-only {show(k)} -> {x[k]}")
        for k in sorted(set(y) - set(x)):
            lines.append(f"  control-only {show(k)} -> {y[k]}")
        for k in sorted(set(x) & set(y)):
            fx, fy = sorted({v[0] for v in x[k]}), sorted({v[0] for v in y[k]})
            if fx != fy:
                lines.append(f"  answer differs {show(k)}: v17 {x[k]} control {y[k]}")
    return lines


def main() -> int:
    report = {"startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "browser": "chrome",
              "runSha256": sha256(Path(__file__).read_bytes()),
              "tools": {name: sha256((PROBE / "tools" / name).read_bytes()) for name in
                        ("probe_fc_debug.py", "compare_layout_corpus.py", "run_e2_c_product_path.py")}}
    results = {}
    for variant in DOCS:
        for profile in PROFILES:
            results[(profile, variant)] = one_session(profile, variant)
    report["sessions"] = list(results.values())
    report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (HERE / "fc-request.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = summarize(results)
    (HERE / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
