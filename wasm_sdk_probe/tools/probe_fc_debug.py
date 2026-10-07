#!/usr/bin/env python3
"""What the WASM engine's fontconfig does with a substituted font name -- a diagnostic.

Written 2026-10-07 for finding 114 (findings/evidence/114/fc-debug/PREDICTION.md).
On v8 and v16, a zh-TW paragraph whose Asian font is a name the profile does not
have (思源黑體, PMingLiU, ...) gets a Latin line height; native LibreOffice with
the same font files and fonts.conf gets the CJK one.  The name reaches fontconfig
through LibreOffice's pre-match hook (`PrintFontManager::Substitute`), so this
asks fontconfig itself, inside the engine, what it was asked and what it answered.

Per profile, in a scratch mirror of dist/ (nothing in dist/ is written):
  - the profile's probe.js gets ENV.FC_DEBUG appended to the preRun line that
    already sets ENV.MAX_CONCURRENCY -- probe.wasm is the shipped one;
  - the product page is repointed to the profile (`pp.repointed_page`), creates
    its engine with `debug: true` (so the worker forwards stdout/stderr), and
    wraps `Worker` to keep every forwarded line;
  - finding 113's font-slot fixture is opened and its pitches read the same way
    `probe_cjk_font_slots.py` reads them.
It writes the raw log per profile and a parse of every `Match` block.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_cjk_font_slots as slots  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

# FC_DBG_MATCH 1 + FC_DBG_SCAN 128 + FC_DBG_CONFIG 1024 (fontconfig 2.18.2 src/fcint.h).
FC_DEBUG = "1153"
PRERUN = 'ENV.MAX_CONCURRENCY="4"'
IMPORT = 'import { createDocumentEngine } from "./sdk/document-sdk.js";\n'
CAPTURE = ('{const W=globalThis.Worker;globalThis.__fcLog=[];globalThis.Worker=class extends W{'
           'constructor(...a){super(...a);this.addEventListener("message",(e)=>{const m=e.data;'
           'if(m&&m.kind==="event"&&m.event==="diagnostic"&&(m.level==="stdout"||m.level==="stderr"))'
           'globalThis.__fcLog.push([m.level,String(m.message)]);});}};}\n')
LOG_LEN = "(() => (globalThis.__fcLog || []).length)()"
LOG_SLICE = "(() => (globalThis.__fcLog || []).slice(ARG_FROM, ARG_TO))()"
FIXTURE = "cjk-font-slots.odt"


def once(text: str, find: str, replace: str, where: str) -> str:
    if text.count(find) != 1:
        raise SystemExit(f"{where}: expected exactly one {find!r}, found {text.count(find)}")
    return text.replace(find, replace, 1)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_log(session, start: int = 0, step: int = 2000) -> list[list[str]]:
    total = pp.evaluate(session, LOG_LEN) or 0
    out: list[list[str]] = []
    for lo in range(start, total, step):
        out += pp.evaluate(session, LOG_SLICE.replace("ARG_FROM", str(lo))
                           .replace("ARG_TO", str(min(total, lo + step)))) or []
    return out


def values(line: str) -> list[str]:
    """Quoted strings, and the unquoted langset values (`lang: zh-tw(s) "en"(w)`)."""
    return [quoted or bare for quoted, bare in
            re.findall(r'(?:"([^"]*)"|([A-Za-z0-9|_-]+))\([sw]\)', line.split(":", 1)[-1])]


def in_pattern(line: str) -> bool:
    """FcPatternPrint's element lines start with a tab -- except the line that
    closes a charset dump, which is the bare binding `(s)` (measured on native
    fontconfig 2.17.1 output: without this the best match's `lang` was lost)."""
    return line.startswith("\t") or re.fullmatch(r"\([sw]\)", line) is not None


def element(block: list[str], name: str) -> str | None:
    for line in block:
        if line.startswith(f"\t{name}:"):
            return line
    return None


def match_blocks(lines: list[str]) -> list[dict]:
    """Every `Match` block: what was asked, the best score, what came back."""
    out, i = [], 0
    while i < len(lines):
        if not lines[i].startswith("Match Pattern has"):
            i += 1
            continue
        start, i = i, i + 1
        asked = []
        while i < len(lines) and in_pattern(lines[i]):
            asked.append(lines[i])
            i += 1
        while i < len(lines) and not lines[i].startswith(("Best score", "Match Pattern has")):
            i += 1
        score, best = None, []
        if i < len(lines) and lines[i].startswith("Best score"):
            score = lines[i][len("Best score"):].split()
            i += 1
            if i < len(lines) and lines[i].startswith("Pattern has"):
                i += 1
                while i < len(lines) and in_pattern(lines[i]):
                    best.append(lines[i])
                    i += 1
        lang_line = element(best, "lang") or ""
        out.append({
            "line": start,
            "askedFamily": values(element(asked, "family") or ""),
            "askedLang": values(element(asked, "lang") or ""),
            "bestScore": score,
            "bestFamily": values(element(best, "family") or ""),
            "bestFile": values(element(best, "file") or ""),
            "bestIndex": (element(best, "index") or "").strip(),
            "bestLangHasZhTw": "zh-tw" in lang_line,
        })
    return out


def measure(profile: str, out_dir: Path, fixture: bytes) -> dict:
    root = pp.PROJECT / "dist"
    loader_path = root / "profiles" / profile / "probe.js"
    loader_before = loader_path.read_bytes()
    page, pin_before, wasm = pp.repointed_page(
        (root / "e2-editor-app.js").read_text(encoding="utf-8"), profile,
        root / "profiles" / profile / "sdk-manifest.json")
    page = once(page, IMPORT, IMPORT + CAPTURE, "page")
    page = once(page, "createDocumentEngine({", "createDocumentEngine({ debug: true,", "page")
    loader = once(loader_before.decode("utf-8"), PRERUN,
                  f'{PRERUN};ENV.FC_DEBUG="{FC_DEBUG}"', str(loader_path))
    mirror = Path(tempfile.mkdtemp(prefix="fc-debug-")) / "root"
    served_loader = f"profiles/{profile}/probe.js"
    pp.build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8"),
                                   served_loader: loader.encode("utf-8")})
    # The override must be a real file in a real directory, or the run would
    # either measure the shipped loader or (worse) have written into dist/.
    if ((mirror / served_loader).is_symlink() or (mirror / served_loader).parent.is_symlink()
            or (mirror / served_loader).read_bytes() == loader_before):
        raise SystemExit(f"the loader override did not take in {mirror}")
    if (mirror / FIXTURE).exists() or mirror.is_symlink():
        raise SystemExit(f"refusing to write the fixture into {mirror}")
    (mirror / FIXTURE).write_bytes(fixture)
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(pp.PROJECT / "web" / "serve.py"),
                               "--port", str(port), "--root", str(mirror)],
                              cwd=pp.PROJECT, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    result = {"profile": profile, "pinBefore": pin_before, "wasm": wasm[:16],
              "servedLoaderSha256": sha256(loader.encode("utf-8")),
              "shippedLoaderSha256": sha256(loader_before), "fcDebug": FC_DEBUG}
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = pp.ChromeSession("cold")
        pp.navigate(session, base)
        result["boot"] = pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        result["shims"] = pp.evaluate(session, pp.INSTALL)
        result["logLinesAtReady"] = pp.evaluate(session, LOG_LEN)
        pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./" + FIXTURE)
                    .replace("ARG_NAME", FIXTURE))
        result["opened"] = pp.wait_for(session, lambda s: (s.get("doc") or "") == FIXTURE
                                       and s.get("state") == "ready", 120)
        scan = slots.settle(session)
        if scan and scan.get("png"):
            png = base64.b64decode(scan["png"].split(",", 1)[1])
            (out_dir / f"{profile}-fixture.png").write_bytes(png)
            result["pitches"] = slots.pitches(png)
        log = read_log(session)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        server.wait(timeout=10)
    if loader_path.read_bytes() != loader_before:
        raise SystemExit(f"{loader_path} changed during the run")
    (out_dir / f"{profile}-fc-log.txt").write_text(
        "".join(f"{level}\t{text}\n" for level, text in log), encoding="utf-8")
    lines = [text for level, text in log if level == "stdout"]
    at_ready = result["logLinesAtReady"] or 0
    blocks = match_blocks(lines)
    stdout_index = [n for n, (level, _) in enumerate(log) if level == "stdout"]
    for block in blocks:
        block["phase"] = "fixture" if stdout_index[block["line"]] >= at_ready else "boot"
    result.update({
        "logLines": len(log),
        "stderr": [text for level, text in log if level == "stderr"][:200],
        "configLines": [t for t in lines if "config file" in t or "config dir" in t],
        "scannedFiles": [t.strip() for t in lines if t.lstrip().startswith("Scanning file")],
        "matchBlocks": blocks,
        "siyuanBlocks": [b for b in blocks if "思源黑體" in b["askedFamily"]],
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", nargs="+", default=["e2-editor-v8", "e2-editor-v16"])
    parser.add_argument("--out", type=Path, required=True, help="a directory")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    fixture = slots.fixture_bytes()
    (args.out / FIXTURE).write_bytes(fixture)
    report = {"startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "browser": "chrome",
              "probeSha256": sha256(Path(__file__).read_bytes()),
              "fixtureSha256": sha256(fixture),
              "profiles": [measure(profile, args.out, fixture) for profile in args.profiles],
              "completedAt": None}
    report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (args.out / "fc-debug.json").write_text(json.dumps(report, indent=1, ensure_ascii=False),
                                            encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
