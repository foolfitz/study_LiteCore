#!/usr/bin/env python3
"""SPEC-M3-K-0.2.44 append 1 on K 0.2.45 (derived from k-0.2.44/counted-paths/, not edited): witness and red cases for H1-H4, offline, before any counted run.

H1  check_m3_assets assumed a one-page package (K1/Z1 on the two ODS pages, K2-1 against the whole manifest).
H2  the counted runners required `make test-e2-c-static` to exit 0; the target is red on the spec's named set.
H3  production UI and host_entry asked the bound bundle tool's default manifest (v76), not generation 83.
H4  production UI's C keying refused a package with more than one probe.wasm.

Every clause says what it reads.  Each fix has its own red, so a green line here is not only "it returned green".
Reads the tree, dist/ and the installed host package.  Writes only --out.  No browser, no ddev.
"""
import copy
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent.parent
PROJECT = REPO / "wasm_sdk_probe"
sys.path.insert(0, str(PROJECT / "tools"))

import check_m3_assets as assets  # noqa: E402
import check_m3_host_entry as host_entry  # noqa: E402
import check_m3_production_ui as ui  # noqa: E402
import k_static_target as kst  # noqa: E402
from probe_m3_assets import closure  # noqa: E402

WITNESS = REPO / "findings/evidence/m3-assets/shakedown/2026-10-31T065458+0000.json"
# The witness is v28-era.  Its closure rows would compare two identities on this tree, so from there on they read 0.2.45's own shakedown.
LIVE = REPO / "findings/evidence/m3-assets/shakedown/2026-11-01T161343+0000.json"
LAST_COUNT = REPO / "findings/evidence/m3-assets/runs/2026-10-18T195011+0000.json"
ENGINE = Path.home() / "Projects/Nextcloud_Apps/litecore/engine"
OLD_ONE_WASM = PROJECT / "build/archive/host-0.2.25-engine-f5f0df762e1855f2"
BEFORE_C = PROJECT / "build/archive/host-0.2.12-engine-45cdcedfc0fe7e61"
rows = []


def check(name, ok, detail=""):
    rows.append({"check": name, "ok": bool(ok), "detail": detail})
    print(f"{'ok  ' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""), flush=True)


def h1():
    report = json.loads(WITNESS.read_text())
    ctx = assets.run_context(report)
    manifest = ctx["manifest"]
    check("H1 witness: red as the chain saw it", assets.score(report, strict=False)["verdict"] == "red")
    # The new reading of K1/Z1 alone already clears the two pages.
    check("H1 K1/Z1 clean on the witness wire record", not assets.score_wire(report["wire"], manifest, True),
          f"pages {sorted(assets.pages_of(manifest))}")
    check("H1 the pages read from the table, three of them", len(assets.pages_of(manifest)) == 3)
    check("H1 a manifest without a table keeps one page", assets.pages_of({"files": {}}) == {assets.DOC})
    # Fails closed: the witness has no pageFiles, so K2-1 stays red rather than being skipped.
    closed = [p for r in report["runs"] for p in assets.score_run(r, ctx) if p.startswith("K2-1")]
    check("H1 no pageFiles record on a three-page manifest stays red", len(closed) == len(report["runs"]), f"{len(closed)} K2-1")
    # 0.2.45's own shakedown, which carries the record the runner now writes, and closure(DIST) must be that record.
    report = json.loads(LIVE.read_text())
    ctx, manifest = assets.run_context(report), assets.run_context(report)["manifest"]
    derived = closure(assets.DIST)
    check("H1 closure(DIST) is the record 0.2.45's shakedown carries",
          report["package"]["pageFiles"] == {html: page["files"] for html, page in derived["pages"].items()})
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "witness-with-pageFiles.json"
        path.write_text(json.dumps(report))
        result = assets.score(report, strict=False)
        check("H1 the witness scores clean with the record", result["verdict"] == "clean", assets.one_line(result)[:150])
        listed = set(report["package"]["pageFiles"][assets.DOC])
        check("H1 the Writer page's closure is a proper part of the manifest",
              listed < set(manifest["files"]), f"{len(listed)} of {len(manifest['files'])}")
        for run in report["runs"]:
            under = {assets.strip_front(r["path"])[len(assets.asset_prefix(ctx["address"])):]
                     for r in run["first"]["log"] if assets.strip_front(r["path"]).startswith(assets.asset_prefix(ctx["address"]))}
            check(f"H1 {run['browser']} first open requested exactly the closure", under == listed, f"{len(under)} files")
        failures = assets.red_cases(path)
        check("H1 --red-cases on the witness: every mutation red, none missing", failures == 0, f"{failures} failures")
    # An older report is scored as it was: the last count's wire and runs do not change verdict.
    last = json.loads(LAST_COUNT.read_text())
    lctx = assets.run_context(last)
    check("H1 the 0.2.26 count's wire record stays clean", not assets.score_wire(last["wire"], lctx["manifest"], True))
    check("H1 the 0.2.26 count's runs stay clean", not any(assets.score_run(r, lctx) for r in last["runs"]))


def h2():
    plain = subprocess.run(["make", "test-e2-c-static"], cwd=PROJECT, capture_output=True, text=True).returncode
    check("H2 witness: the plain target is not exit 0", plain != 0, f"exit {plain}")
    named = kst.NAMED.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        original = scratch / "t.txt"
        with original.open("w") as transcript:
            make = subprocess.run(["make", "-i", "test-e2-c-static"], cwd=PROJECT, stdout=transcript, stderr=subprocess.STDOUT)
        text = original.read_text(encoding="utf-8")
        check("H2 the tree's red set is exactly the named one",
              kst.judge(make.returncode, kst.read_reds(original), named)["testStatic"] == 0)
        more = scratch / "more.txt"
        more.write_text(text + "\n✖ a red the spec never named (1ms)\n", encoding="utf-8")
        check("H2 red: one red more", kst.judge(0, kst.read_reds(more), named)["testStatic"] != 0)
        fewer = scratch / "fewer.txt"
        fewer.write_text("\n".join(line for line in text.splitlines() if "FAIL: test_the_inducing_arms_hold_the_guard_off" not in line),
                         encoding="utf-8")
        check("H2 red: one red fewer", kst.judge(0, kst.read_reds(fewer), named)["testStatic"] != 0)
        ignored = scratch / "ignored.txt"
        ignored.write_text(text + "\nmake: [Makefile:1: test-e2-c-static] Error 1 (ignored)\n", encoding="utf-8")
        check("H2 red: one more ignored make error", kst.judge(0, kst.read_reds(ignored), named)["testStatic"] != 0)
        check("H2 red: make itself failed", kst.judge(2, kst.read_reds(original), named)["testStatic"] == 2)
    live = kst.static_target(PROJECT)
    check("H2 what a counted runner now records", live["testStatic"] == 0, json.dumps(live, ensure_ascii=False)[:170])


def h3():
    default = subprocess.run([sys.executable, str(PROJECT / "tools/build_e2_c_shell_bundle.py")], capture_output=True, text=True)
    check("H3 witness: the bound tool's default manifest exits 1 on this tree", default.returncode == 1,
          json.loads(default.stdout).get("manifest"))
    shell = ui.shell_bundle()
    check("H3 production UI asks generation 83: exit 0, the pinned digest",
          shell["exit"] == 0 and shell["sha256"] == ui.SHELL_BUNDLE_SHA256, f"{shell['manifest']} {str(shell['sha256'])[:12]}")
    kept = ui.SHELL_MANIFEST
    ui.SHELL_MANIFEST = "e2/editor-shell-v2-bundle-v82.json"
    red = ui.shell_bundle()
    ui.SHELL_MANIFEST = kept
    check("H3 red: asked generation 82, the same check is not exit 0", red["exit"] != 0, f"exit {red['exit']}")
    served = host_entry.served_shell()
    check("H3 host_entry: dist/ is generation 83", served["differsFromManifest"] == [], served["manifest"])
    kept = host_entry.SHELL_MANIFEST
    host_entry.SHELL_MANIFEST = Path("e2/editor-shell-v2-bundle-v76.json")
    old = host_entry.served_shell()
    host_entry.SHELL_MANIFEST = kept
    check("H3 witness/red: against v76 dist/ differs, the refusal the chain would have hit", old["differsFromManifest"] != [],
          str(old["differsFromManifest"]))


def tampered(engine_dir: Path, mutate) -> Path:
    """A package directory with a mutated MANIFEST.json; files/ is a symlink, nothing is copied or written to the host."""
    manifest = json.loads((ENGINE / "MANIFEST.json").read_text())
    mutate(manifest)
    (engine_dir / "MANIFEST.json").write_text(json.dumps(manifest))
    os.symlink(ENGINE / "files", engine_dir / "files")
    return engine_dir


def h4():
    key = ui.boundary_noop_keying(ENGINE)
    check("H4 the served package keys on the editor's wasm",
          key.get("wasm") == "profiles/e2-editor-v29/probe.wasm" and key.get("wasmSha256", "").startswith("e61e5890"),
          str({k: v for k, v in key.items() if k in ("declared", "wasm", "error")}))
    check("H4 v29 carries C by its ABI, not by the fragment (the ordered spec's premise is false, its prescription stands)",
          key.get("declared") is True and key.get("abiVersion") == 6 and key.get("fragmentInWasm") is False,
          str({k: key.get(k) for k in ("declared", "abiVersion", "fragmentInWasm")}))
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        for name, mutate, want in (
                ("witness/red: without the page table three wasm entries refuse, as the chain would have",
                 lambda m: m["source"].pop("pages"), lambda k: k["declared"] is None and "3 probe.wasm" in k["error"]),
                ("red: the page table's sha256 is not the bytes",
                 lambda m: m["source"]["pages"]["e2-editor.html"].update(wasmSha256="0" * 64),
                 lambda k: k["declared"] is None and "page table" in k["error"]),
                ("red: the editor row names a profile that is not packaged",
                 lambda m: m["source"]["pages"]["e2-editor.html"].update(profile="e2-editor-v0"),
                 lambda k: k["declared"] is None),
                ("the viewer's wasm carries no C: declared False, not True",
                 lambda m: m["source"]["pages"]["e2-editor.html"].update(
                     profile="ods-viewer-v3", wasmSha256=m["source"]["pages"]["ods-viewer.html"]["wasmSha256"]),
                 lambda k: k["declared"] is False)):
            directory = scratch / hashlib.sha256(name.encode()).hexdigest()[:8]
            directory.mkdir()
            result = ui.boundary_noop_keying(tampered(directory, mutate))
            check(f"H4 {name}", want(result), str(result.get("error") or result.get("declared"))[:110])
    old = ui.boundary_noop_keying(OLD_ONE_WASM)
    check("H4 an archived one-wasm package keys as before: v21 carries C by the fragment, ABI 5",
          old.get("declared") is True and old.get("fragmentInWasm") is True and old.get("abiVersion") == 5,
          str({k: old.get(k) for k in ("wasm", "abiVersion", "fragmentInWasm", "error")}))
    before_c = ui.boundary_noop_keying(BEFORE_C)
    check("H4 red: an engine before C stays declared False", before_c.get("declared") is False,
          str({k: before_c.get(k) for k in ("wasm", "abiVersion", "fragmentInWasm", "error")}))


def main():
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    for part in (h1, h2, h3, h4):
        part()
    bad = [r for r in rows if not r["ok"]]
    print(f"\n{len(rows) - len(bad)}/{len(rows)} hold")
    if out:
        out.write_text(json.dumps({"tool": Path(__file__).name, "rows": rows, "held": len(rows) - len(bad), "of": len(rows)},
                                  indent=1, ensure_ascii=False) + "\n")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
