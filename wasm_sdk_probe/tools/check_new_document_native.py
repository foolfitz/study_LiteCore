#!/usr/bin/env python3
"""SPEC-M3-new-document N11: native 26.8 LibreOfficeKit loads a blank-document
template and saves it; the saved styles.xml must keep the template's stated
defaults under BOTH `LANG=en_US.UTF-8` and `LANG=zh_TW.UTF-8` -- the template
must win over the environment.  Control: richdocuments' style-less template,
whose Asian language follows LANG (analysis 1, arms A and B), so the
instrument is shown to see the environment.

The probe binary is the analysis session's `lok_defaults_probe.cpp`
(findings/evidence/new-document/probe-1-native-defaults/tool/), compiled here
with the repo's native-harness recipe.  Each arm runs in its own process with
a fresh empty profile and LC_ALL/LANGUAGE/LC_CTYPE/LC_PAPER/PAPERSIZE unset.

  check_new_document_native.py --templates DIR --out EVIDENCE_DIR [--build BUILD_DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_new_document_templates as gen  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
INSTDIR = REPO / "native-lok-26-8" / "build" / "instdir"
LOK_INCLUDE = REPO / "libreoffice-26-8" / "include"
TOOL = REPO / "findings" / "evidence" / "new-document" / "probe-1-native-defaults" / "tool"
PROBE_SOURCE = TOOL / "lok_defaults_probe.cpp"
CONTROL = TOOL / "input-template.odt"
LANGS = ["en_US.UTF-8", "zh_TW.UTF-8"]
TEMPLATES = ["en-US_zh-TW_A4.odt", "en-US_zh-TW_Letter.odt", "en-US_ja-JP_A4.odt", "de-DE_zh-TW_Letter.odt"]
UNSET = ("LC_ALL", "LANGUAGE", "LC_CTYPE", "LC_PAPER", "PAPERSIZE", "LC_MESSAGES")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_probe(build: Path) -> Path:
    binary = build / "lok_defaults_probe"
    if binary.is_file() and binary.stat().st_mtime >= PROBE_SOURCE.stat().st_mtime:
        return binary
    build.mkdir(parents=True, exist_ok=True)
    subprocess.run(["g++", "-std=c++17", "-O2", "-I", str(LOK_INCLUDE), str(PROBE_SOURCE), "-ldl", "-o", str(binary)],
                   check=True, capture_output=True, text=True)
    return binary


def run_arm(binary: Path, lang: str, source: Path, work: Path) -> dict[str, Any]:
    profile = work / "profile"
    profile.mkdir()
    out = work / "saved.odt"
    env = {k: v for k, v in os.environ.items() if k not in UNSET}
    env.update({"LANG": lang, "SAL_USE_VCLPLUGIN": "svp"})
    done = subprocess.run([str(binary), str(INSTDIR / "program"), f"file://{profile}", f"file://{source}", str(out)],
                          env=env, capture_output=True, text=True, timeout=600, cwd=work)
    record: dict[str, Any] = {"lang": lang, "template": source.name, "exit": done.returncode,
                              "stdout": done.stdout.strip(), "stderrLines": len(done.stderr.splitlines())}
    if out.is_file():
        saved = out.read_bytes()
        record["savedBytes"] = len(saved)
        record["savedStylesSha256"] = None
        try:
            import zipfile
            with zipfile.ZipFile(out) as zf:
                record["savedStylesSha256"] = hashlib.sha256(zf.read("styles.xml")).hexdigest()
            record["described"] = gen.describe(saved)
        except Exception as error:  # noqa: BLE001 -- recorded
            record["describeError"] = f"{type(error).__name__}: {error}"
    else:
        record["savedBytes"] = 0
    registry = profile / "user" / "registrymodifications.xcu"
    if registry.is_file():
        import re
        text = registry.read_text(encoding="utf-8", errors="replace")
        record["registry"] = dict(re.findall(r'oor:name="(ooSetupSystemLocale|ooLocale)"[^>]*>\s*<value>([^<]*)</value>', text))
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", type=Path, required=True, help="the host's blank/ directory")
    parser.add_argument("--out", type=Path, required=True, help="evidence directory to write")
    parser.add_argument("--build", type=Path, default=PROJECT / "build" / "new-document-native")
    args = parser.parse_args()

    manifest = json.loads((args.templates / "MANIFEST.json").read_text(encoding="utf-8"))
    binary = compile_probe(args.build)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "styles").mkdir(exist_ok=True)
    report: dict[str, Any] = {
        "probe": "new-document-native-roundtrip", "spec": "specs/SPEC-M3-new-document.md N11",
        "engine": {"instdir": str(INSTDIR), "libsofficeapp": sha256_file(INSTDIR / "program" / "libsofficeapp.so")},
        "probeSource": {"path": str(PROBE_SOURCE.relative_to(REPO)), "sha256": sha256_file(PROBE_SOURCE)},
        "templatesManifestSha256": sha256_file(args.templates / "MANIFEST.json"),
        "arms": [], "control": [],
    }
    with tempfile.TemporaryDirectory(prefix="new-doc-native-", dir=args.build) as scratch:
        scratch_path = Path(scratch)
        for name in TEMPLATES:
            source = args.templates / name
            record = manifest["files"][name]
            for lang in LANGS:
                work = scratch_path / f"{name[:-4]}-{lang.split('.')[0]}"
                work.mkdir()
                arm = run_arm(binary, lang, source, work)
                arm["templateSha256"] = sha256_file(source)
                arm["expected"] = gen.expected(record)
                arm["departures"] = gen.compare(record, arm.get("described") or {}) if arm.get("described") else ["no saved file"]
                arm["passed"] = not arm["departures"]
                if (work / "saved.odt").is_file():
                    import zipfile
                    with zipfile.ZipFile(work / "saved.odt") as zf:
                        (args.out / "styles" / f"{name[:-4]}-{lang.split('.')[0]}-styles.xml").write_bytes(zf.read("styles.xml"))
                report["arms"].append(arm)
        for lang in LANGS:
            work = scratch_path / f"control-{lang.split('.')[0]}"
            work.mkdir()
            arm = run_arm(binary, lang, CONTROL, work)
            arm["templateSha256"] = sha256_file(CONTROL)
            if (work / "saved.odt").is_file():
                import zipfile
                with zipfile.ZipFile(work / "saved.odt") as zf:
                    (args.out / "styles" / f"control-{lang.split('.')[0]}-styles.xml").write_bytes(zf.read("styles.xml"))
            report["control"].append(arm)
    asian = [a.get("described", {}).get("asian") for a in report["control"]]
    report["controlSeesEnvironment"] = len(set(asian)) == 2 and None not in asian
    report["controlAsian"] = dict(zip([a["lang"] for a in report["control"]], asian))
    report["armsPassed"] = sum(1 for a in report["arms"] if a["passed"])
    report["armsOf"] = len(report["arms"])
    report["verdict"] = ("N11 PASS" if report["armsPassed"] == report["armsOf"] and report["controlSeesEnvironment"]
                         else "N11 FAIL")
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "armsPassed": f"{report['armsPassed']}/{report['armsOf']}",
                      "controlAsian": report["controlAsian"], "report": str(args.out / "report.json")}, ensure_ascii=False))
    return 0 if report["verdict"] == "N11 PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
