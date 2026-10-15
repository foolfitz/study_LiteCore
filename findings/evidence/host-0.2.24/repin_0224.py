"""Move every 0.2.23 pin to host 0.2.24 (finding 145): page 901dd6a6..., buildId d3cd39bb..., host 1479e56, shell v73.
Each old text must occur exactly once in its file, or nothing is written."""
import sys
from pathlib import Path

ROOT = Path("/home/jiajun/LibreOffice/study_LiteCore")
PO = "ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e"
PN = "901dd6a6dbff6ad6f5252814fb4dc09230446a11d75387fb447e8a6a398a68c2"
T = "wasm_sdk_probe/tools/"

EDITS = {
    "findings/evidence/c-prime/c2/judge_c2.py": [
        ("# Every committed C2 report ran on an earlier page",
         "# Re-pinned 2026-10-15 to host 0.2.24's page (finding 145; shell v73, engine v20).  The previous pin, host 0.2.23's page, was\n"
         f"# {PO} (findings/evidence/release-0.2.23/c2/ ran on it; the 136 page b24d754a… before that).\n"
         "# Every committed C2 report ran on an earlier page"),
        (f'PAGE = "{PO}"', f'PAGE = "{PN}"'),
    ],
    "findings/evidence/typing-latency/judge_p2.py": [
        ("# Every committed P2 report ran on an earlier page",
         "# Re-pinned 2026-10-15 to host 0.2.24's page (finding 145; shell v73, engine v20).  The previous pin, host 0.2.23's page, was\n"
         f"# {PO} (findings/evidence/release-0.2.23/c2/r*/ratio-1/ ran on it; the 136 page b24d754a… before that).\n"
         "# Every committed P2 report ran on an earlier page"),
        (f'PAGE = "{PO}"', f'PAGE = "{PN}"'),
    ],
    T + "probe_129_m4_wasm.py": [
        (f'FINAL_PAGE_SHA256 = "{PO}"',
         "# Re-pinned 2026-10-15 to host 0.2.24's page (finding 145; shell v73).  The previous pin, host 0.2.23's page, was\n"
         f"# {PO} (no round of this probe ran on it; the last, round-20261014T085633Z, ran on 7815e16c…).\n"
         f'FINAL_PAGE_SHA256 = "{PN}"'),
    ],
    T + "check_m3_assets.py": [
        (f'PAGE_SHA256 = "{PO}"   # host 0.2.23 (v72), 2026-10-15; was d761f1ce',
         f'PAGE_SHA256 = "{PN}"   # host 0.2.24 (v73, finding 145), 2026-10-15; was ccb67a52 (host 0.2.23, v72), d761f1ce'),
        ('BUILD_ID = "c3c22d9294de068a"   # host 0.2.23\'s engine package (v20, page ccb67a52, shell v72), link-batch §17; was eb3f9408',
         'BUILD_ID = "d3cd39bbc71ec311"   # host 0.2.24\'s engine package (v20, page 901dd6a6, shell v73; finding 145); was c3c22d92 (0.2.23, link-batch §17), eb3f9408'),
    ],
    T + "check_m3_autosave.py": [
        (f'PAGE_SHA256: str | None = "{PO}"      # web/e2-editor-app.js, dist copy and the copy the host serves; was d761f1ce',
         f'PAGE_SHA256: str | None = "{PN}"      # web/e2-editor-app.js, dist copy and the copy the host serves; was ccb67a52 (0.2.23), d761f1ce'),
        ('HOST_VERSION: str | None = "0.2.23"     # appinfo/info.xml <version>; link-batch §17; was 0.2.14',
         'HOST_VERSION: str | None = "0.2.24"     # appinfo/info.xml <version>; finding 145; was 0.2.23 (link-batch §17), 0.2.14'),
        ('HOST_COMMIT: str | None = "2ccf1a9"      # the host repo\'s HEAD, a prefix is enough; link-batch §17; was 237f2cb',
         'HOST_COMMIT: str | None = "1479e56"      # the host repo\'s HEAD, a prefix is enough; finding 145; was 2ccf1a9 (link-batch §17), 237f2cb'),
    ],
    T + "check_m3_locks.py": [
        (f'PAGE_SHA256 = "{PO}"   # host 0.2.23 (v72), 2026-10-15; was d761f1ce',
         f'PAGE_SHA256 = "{PN}"   # host 0.2.24 (v73, finding 145), 2026-10-15; was ccb67a52 (host 0.2.23, v72), d761f1ce'),
    ],
    T + "check_m3_new_document.py": [
        ('HOST_COMMIT: str | None = "2ccf1a9"      # was afbaf3c (0.2.19)',
         "# Re-bound 2026-10-15 to host 0.2.24 (finding 145): git diff 2ccf1a9..1479e56 touches only appinfo/info.xml, so\n"
         "# the blank manifest is unchanged; the engine package and the page moved (shell v73).\n"
         'HOST_COMMIT: str | None = "1479e56"      # 0.2.24; was 2ccf1a9 (0.2.23), afbaf3c (0.2.19)'),
        ('HOST_VERSION: str | None = "0.2.23"      # was 0.2.19',
         'HOST_VERSION: str | None = "0.2.24"      # was 0.2.23, 0.2.19'),
        ('ENGINE_BUILD_ID: str | None = "c3c22d9294de068a"',
         'ENGINE_BUILD_ID: str | None = "d3cd39bbc71ec311"   # 0.2.24 (finding 145, shell v73); was c3c22d92 (0.2.23)'),
        (f'PAGE_SHA256: str | None = "{PO}"',
         f'PAGE_SHA256: str | None = "{PN}"   # 0.2.24; was ccb67a52 (0.2.23)'),
    ],
    T + "check_m3_page_honesty.py": [
        (f'PAGE_SHA256: str | None = "{PO}"   # host 0.2.23 (v72), 2026-10-15; was d761f1ce',
         f'PAGE_SHA256: str | None = "{PN}"   # host 0.2.24 (v73, finding 145), 2026-10-15; was ccb67a52 (0.2.23, v72), d761f1ce'),
        ('HOST_VERSION = "0.2.23"   # link-batch §17; was 0.2.14',
         'HOST_VERSION = "0.2.24"   # finding 145; was 0.2.23 (link-batch §17), 0.2.14'),
        ('HOST_COMMIT: str | None = "2ccf1a9"   # link-batch §17; was 237f2cb',
         'HOST_COMMIT: str | None = "1479e56"   # finding 145; was 2ccf1a9 (link-batch §17), 237f2cb'),
    ],
    T + "check_m3_production_ui.py": [
        (f'PAGE_SHA256: str | None = "{PO}"   # host 0.2.23 (v72), 2026-10-15; was d761f1ce',
         f'PAGE_SHA256: str | None = "{PN}"   # host 0.2.24 (v73, finding 145), 2026-10-15; was ccb67a52 (0.2.23, v72), d761f1ce'),
        ('HOST_VERSION: str | None = "0.2.23"   # link-batch §17; was 0.2.14',
         'HOST_VERSION: str | None = "0.2.24"   # finding 145; was 0.2.23 (link-batch §17), 0.2.14'),
        ('HOST_COMMIT: str | None = "2ccf1a9"   # link-batch §17; was 237f2cb',
         'HOST_COMMIT: str | None = "1479e56"   # finding 145; was 2ccf1a9 (link-batch §17), 237f2cb'),
        ('SHELL_BUNDLE_SHA256: str | None = "4dc10507565992d51527c12c8a738b7f857ff3e67fc2bc98db00c0e4e2252731"   # v72; was v63',
         'SHELL_BUNDLE_SHA256: str | None = "6ab20f684bb1b331c473e2cb7823b4d424c7818b68661133a5a4ec0ecfa346c2"   # v73; was v72 4dc10507, v63'),
    ],
    T + "check_m3_same_second.py": [
        ('HOST_VERSION = "0.2.23"   # SPEC-M3-link-batch §17 (0.2.23, v72), 2026-10-15; was 0.2.14',
         'HOST_VERSION = "0.2.24"   # finding 145 (0.2.24, v73), 2026-10-15; was 0.2.23 (SPEC-M3-link-batch §17), 0.2.14'),
    ],
    T + "check_m3_versions.py": [
        ('HOST_COMMIT = "2ccf1a9"   # SPEC-M3-link-batch §17 (0.2.23, v72), 2026-10-15 (host 0.2.23); was 237f2cb',
         'HOST_COMMIT = "1479e56"   # finding 145 (0.2.24, v73), 2026-10-15 (host 0.2.24); was 2ccf1a9 (SPEC-M3-link-batch §17, host 0.2.23), 237f2cb'),
    ],
    T + "run_merge_wasm_shakedown.py": [
        ("# Spec 34.1: from this commit until the v20 count's verdict is read, this file is not edited.\n",
         "# Spec 34.1: from this commit until the v20 count's verdict is read, this file is not edited.\n"
         "# Re-bound 2026-10-15 to host 0.2.24's page 901dd6a6… (finding 145).  The v20 count's verdict was read first: merge\n"
         "# FAIL, explained by finding 145 (findings/evidence/145/).  Only pageSha256 and pageSourceSha256 moved, as N1's recorded\n"
         "# `bound` shows (findings/evidence/145/n1/); both were ccb67a52….  Spec 34.1 again: from this re-binding until the\n"
         "# 0.2.24 count's verdict is read, this file is not edited.\n"),
        (f'"pageSha256": "{PO}",', f'"pageSha256": "{PN}",'),
        (f'"pageSourceSha256": "{PO}",', f'"pageSourceSha256": "{PN}",'),
    ],
}

staged, bad = {}, []
for rel, pairs in EDITS.items():
    text = (ROOT / rel).read_text(encoding="utf-8")
    for old, new in pairs:
        n = text.count(old)
        if n != 1:
            bad.append(f"{rel}: {n} occurrences of {old[:70]!r}")
            continue
        text = text.replace(old, new, 1)
    staged[rel] = text
if bad:
    print("NOTHING WRITTEN:", *bad, sep="\n  ")
    sys.exit(1)
for rel, text in staged.items():
    (ROOT / rel).write_text(text, encoding="utf-8")
    print("written", rel)
