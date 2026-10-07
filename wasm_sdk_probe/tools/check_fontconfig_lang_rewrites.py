#!/usr/bin/env python3
"""How many language tags a profile's OWN fontconfig rules rewrite (spec 26.3 V2).

Finding 114.  Reads the fontconfig configuration out of the profile's shipped
base pack (metadata + data named by its sdk-manifest, not the build tree),
includes its conf.d by ABSOLUTE path -- a relative `<include>conf.d</include>`
resolves against fontconfig's default directory and silently loads the
machine's /etc/fonts/conf.d instead, which is how the first native rerun of
114 measured the wrong rules -- and runs the review's census
(findings/evidence/114/review/census.py: every FcGetLangs() tag added as a
string FC_LANG, then FcConfigSubstitute) with LibreOffice's bundled fontconfig.

The rule files fontconfig reports loading are part of the result: any file
outside the extracted directory, or a conf.d file not loaded, fails the run,
so "0 rewritten" cannot come from rules that were never read.

  check_fontconfig_lang_rewrites.py --profile e2-editor-v17 --expect 0
  check_fontconfig_lang_rewrites.py --profile e2-editor-v16 --expect 66   # red case
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CENSUS = HERE.parent / "findings/evidence/114/review/census.py"
LIBFONTCONFIG = HERE.parent / "native-lok-26-8/build/instdir/program/libfontconfig-lo.so.1.16.1"
PREFIX = "/instdir/share/fontconfig/"
INCLUDE = '<include ignore_missing="yes">conf.d</include>'


def extract(profile: str, out: Path) -> list[str]:
    root = HERE / "dist/profiles" / profile
    files = json.loads((root / "sdk-manifest.json").read_text(encoding="utf-8"))["artifactFiles"]
    data = (root / files["soffice.data"]).resolve()
    metadata = json.loads((root / files["soffice.data.js.metadata"]).resolve().read_text(encoding="utf-8"))
    written = []
    with data.open("rb") as stream:
        for entry in metadata["files"]:
            name = entry["filename"]
            if not name.startswith(PREFIX):
                continue
            target = out / name[len(PREFIX):]
            target.parent.mkdir(parents=True, exist_ok=True)
            stream.seek(entry["start"])
            target.write_bytes(stream.read(entry["end"] - entry["start"]))
            written.append(name[len(PREFIX):])
    return sorted(written)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--expect", type=int, default=None)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--keep-relative-include", action="store_true",
                    help="red case: leave fonts.conf's relative include (the mistake of 114's "
                         "first native rerun); the run must report rules loaded from outside")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="fc-census-") as tmp:
        base = Path(tmp)
        conf = base / "fontconfig"
        files = extract(a.profile, conf)
        confd = sorted(f for f in files if f.startswith("conf.d/") and f.endswith(".conf"))
        text = (conf / "fonts.conf").read_text(encoding="utf-8")
        if text.count(INCLUDE) != 1:
            raise SystemExit(f"fonts.conf has {text.count(INCLUDE)} copies of {INCLUDE!r}, expected 1")
        if not a.keep_relative_include:
            text = text.replace(INCLUDE, f'<include ignore_missing="yes">{conf}/conf.d</include>')
        text = re.sub(r"<cachedir[^>]*>[^<]*</cachedir>", f"<cachedir>{base}/cache</cachedir>", text)
        (conf / "fonts.conf").write_text(text, encoding="utf-8")
        (base / "xdg").mkdir()
        env = {**os.environ, "FONTCONFIG_FILE": str(conf / "fonts.conf"),
               "XDG_CONFIG_HOME": str(base / "xdg"), "LANG": "C", "LC_ALL": "C"}
        env.pop("FONTCONFIG_PATH", None)
        env.pop("FC_DEBUG", None)
        command = [sys.executable, "-I", str(CENSUS), str(LIBFONTCONFIG)]
        # Two runs: fontconfig's FC_DEBUG lines (C stdio) and the census's own
        # lines (Python, flushed at exit) share one pipe and interleave mid-line
        # (measured twice: the summary line, then a `done` line, were cut), so
        # the rule files are read from a run that only calls FcInit -- the same
        # FONTCONFIG_FILE, the same library, and nothing else printing.
        init = [sys.executable, "-I", "-c",
                "import ctypes, sys; sys.exit(0 if ctypes.CDLL(sys.argv[1]).FcInit() else 3)",
                str(LIBFONTCONFIG)]
        traced = subprocess.run(init, env={**env, "FC_DEBUG": "1024"}, capture_output=True,
                                text=True, cwd=tmp, check=False)
        done = subprocess.run(command, env=env, capture_output=True, text=True, cwd=tmp, check=False)
        lines = (done.stdout + done.stderr).splitlines()
        loaded = sorted(set(re.findall(r"Loading config file from (\S+?) done",
                                       traced.stdout + traced.stderr)))
        outside = [p for p in loaded if not p.startswith(str(conf))]
        loaded_confd = sorted(p[len(str(conf)) + 1:] for p in loaded
                              if p.startswith(str(conf / "conf.d")))
        summary = next((line for line in lines if line.startswith("FcGetLangs:")), None)
        found = re.search(r"rewritten: (\d+)$", summary or "")
        rewritten = int(found.group(1)) if found else None
        result = {"profile": a.profile, "census": str(CENSUS.relative_to(HERE.parent)),
                  "libfontconfig": str(LIBFONTCONFIG.relative_to(HERE.parent)),
                  "fontconfigFilesInPack": files, "confdInPack": confd,
                  "confdLoaded": loaded_confd, "loadedOutsidePack": outside,
                  "summary": summary, "rewritten": rewritten,
                  "rewrites": [line.strip() for line in lines if " -> " in line]}
    problems = []
    if done.returncode != 0 or traced.returncode != 0 or rewritten is None:
        problems.append(f"census did not complete (exit {done.returncode})")
    if outside:
        problems.append(f"rules loaded from outside the pack: {outside}")
    if loaded_confd != confd:
        problems.append(f"conf.d files in the pack but not loaded: {sorted(set(confd) - set(loaded_confd))}")
    if a.expect is not None and rewritten != a.expect:
        problems.append(f"rewritten {rewritten}, expected {a.expect}")
    result["problems"] = problems
    if a.json:
        a.json.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{a.profile}: {summary}; conf.d in pack {len(confd)}, loaded {len(loaded_confd)}, "
          f"outside {len(outside)}")
    for p in problems:
        print("FAIL " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
