"""Move every 0.2.24 pin to host 0.2.26 (engine v21, shell v74; finding 154's host rule): page 605cf24b..., session
f1509ff2..., buildId f5f0df76..., host 3c01876, version 0.2.26, shell bundle v74 27f33a13....
Each old text must occur exactly once in its file, or nothing is written.  Shape of ../host-0.2.24/repin_0224.py."""
import sys
from pathlib import Path

ROOT = Path("/home/jiajun/LibreOffice/study_LiteCore")
T = "wasm_sdk_probe/tools/"
PO = "901dd6a6dbff6ad6f5252814fb4dc09230446a11d75387fb447e8a6a398a68c2"
PN = "605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f"
SO = "f47c80ec955397c44d7638da63ed6837a3dea47125f6e279192298c20ed62ba9"
SN = "f1509ff22e6e2d8d945cfd803d293fd4cf102cece27618f54825571a2e1ef3a8"
BO, BN = "d3cd39bbc71ec311", "f5f0df762e1855f2"
CO, CN = "1479e56", "3c01876"
VO, VN = "0.2.24", "0.2.26"
SBO = "6ab20f684bb1b331c473e2cb7823b4d424c7818b68661133a5a4ec0ecfa346c2"
SBN = "27f33a13d604720232b02d5cb3a318e94278379923d3522a1de4c0689978673f"
WHY = "host 0.2.26 (engine v21, shell v74, finding 154's host rule), 2026-10-17"

EDITS = {
    "findings/evidence/c-prime/c2/judge_c2.py": [
        (f'PAGE = "{PO}"',
         f"# Re-pinned 2026-10-17 to {WHY}.  The previous pin, host 0.2.24's page, was\n"
         f"# {PO} (the 0.2.24 count's C2 ran on it).\n"
         f'PAGE = "{PN}"'),
    ],
    "findings/evidence/typing-latency/judge_p2.py": [
        (f'PAGE = "{PO}"',
         f"# Re-pinned 2026-10-17 to {WHY}.  The previous pin, host 0.2.24's page, was\n"
         f"# {PO} (the 0.2.24 count's P2 ran on it).\n"
         f'PAGE = "{PN}"'),
    ],
    T + "probe_129_m4_wasm.py": [
        (f'FINAL_PAGE_SHA256 = "{PO}"',
         f"# Re-pinned 2026-10-17 to {WHY}.  The previous pin, host 0.2.24's page, was\n"
         f"# {PO} (no round of this probe ran on it).\n"
         f'FINAL_PAGE_SHA256 = "{PN}"'),
    ],
    T + "check_m3_assets.py": [
        (f'PAGE_SHA256 = "{PO}"   # host 0.2.24 (v73, finding 145), 2026-10-15; was ccb67a52',
         f'PAGE_SHA256 = "{PN}"   # {WHY}; was 901dd6a6 (host 0.2.24, v73, finding 145), ccb67a52'),
        (f'BUILD_ID = "{BO}"   # host 0.2.24\'s engine package (v20, page 901dd6a6, shell v73; finding 145); was c3c22d92',
         f'BUILD_ID = "{BN}"   # host 0.2.26\'s engine package (v21, page 605cf24b, shell v74; the same package as 0.2.25); was d3cd39bb (0.2.24, finding 145), c3c22d92'),
    ],
    T + "check_m3_autosave.py": [
        (f'PAGE_SHA256: str | None = "{PO}"      # web/e2-editor-app.js, dist copy and the copy the host serves; was ccb67a52',
         f'PAGE_SHA256: str | None = "{PN}"      # web/e2-editor-app.js, dist copy and the copy the host serves; was 901dd6a6 (0.2.24), ccb67a52'),
        (f'SESSION_SHA256: str | None = "{SO}"   # editor-shell-v2/narrow-editor-v2-session.js, same three places; link-batch §17',
         f'SESSION_SHA256: str | None = "{SN}"   # editor-shell-v2/narrow-editor-v2-session.js, same three places; shell v74 (0.2.26); was f47c80ec (link-batch §17)'),
        (f'HOST_VERSION: str | None = "{VO}"     # appinfo/info.xml <version>; finding 145; was 0.2.23',
         f'HOST_VERSION: str | None = "{VN}"     # appinfo/info.xml <version>; engine v21 + finding 154; was 0.2.24 (finding 145), 0.2.23'),
        (f'HOST_COMMIT: str | None = "{CO}"      # the host repo\'s HEAD, a prefix is enough; finding 145; was 2ccf1a9',
         f'HOST_COMMIT: str | None = "{CN}"      # the host repo\'s HEAD, a prefix is enough; 0.2.26; was 1479e56 (finding 145), 2ccf1a9'),
    ],
    T + "check_m3_locks.py": [
        (f'PAGE_SHA256 = "{PO}"   # host 0.2.24 (v73, finding 145), 2026-10-15; was ccb67a52',
         f'PAGE_SHA256 = "{PN}"   # {WHY}; was 901dd6a6 (host 0.2.24, v73, finding 145), ccb67a52'),
    ],
    T + "check_m3_new_document.py": [
        (f'HOST_COMMIT: str | None = "{CO}"      # 0.2.24; was 2ccf1a9 (0.2.23), afbaf3c (0.2.19)',
         "# Re-bound 2026-10-17 to host 0.2.26: git diff 1479e56..3c01876 touches only appinfo/info.xml and\n"
         "# templates/editor.php, so the blank manifest is unchanged; the engine package and the page moved (v21, shell v74).\n"
         f'HOST_COMMIT: str | None = "{CN}"      # 0.2.26; was 1479e56 (0.2.24), 2ccf1a9 (0.2.23), afbaf3c (0.2.19)'),
        (f'HOST_VERSION: str | None = "{VO}"      # was 0.2.23, 0.2.19',
         f'HOST_VERSION: str | None = "{VN}"      # was 0.2.24, 0.2.23, 0.2.19'),
        (f'ENGINE_BUILD_ID: str | None = "{BO}"   # 0.2.24 (finding 145, shell v73); was c3c22d92 (0.2.23)',
         f'ENGINE_BUILD_ID: str | None = "{BN}"   # 0.2.26 (v21, shell v74); was d3cd39bb (0.2.24, finding 145), c3c22d92 (0.2.23)'),
        (f'PAGE_SHA256: str | None = "{PO}"   # 0.2.24; was ccb67a52 (0.2.23)',
         f'PAGE_SHA256: str | None = "{PN}"   # 0.2.26; was 901dd6a6 (0.2.24), ccb67a52 (0.2.23)'),
    ],
    T + "check_m3_page_honesty.py": [
        (f'PAGE_SHA256: str | None = "{PO}"   # host 0.2.24 (v73, finding 145), 2026-10-15; was ccb67a52',
         f'PAGE_SHA256: str | None = "{PN}"   # {WHY}; was 901dd6a6 (0.2.24, v73, finding 145), ccb67a52'),
        (f'SESSION_SHA256: str | None = "{SO}"   # link-batch §17 (0.2.23); was 62a2a20e',
         f'SESSION_SHA256: str | None = "{SN}"   # shell v74 (0.2.26); was f47c80ec (link-batch §17, 0.2.23), 62a2a20e'),
        (f'HOST_VERSION = "{VO}"   # finding 145; was 0.2.23',
         f'HOST_VERSION = "{VN}"   # engine v21 + finding 154; was 0.2.24 (finding 145), 0.2.23'),
        (f'HOST_COMMIT: str | None = "{CO}"   # finding 145; was 2ccf1a9',
         f'HOST_COMMIT: str | None = "{CN}"   # 0.2.26; was 1479e56 (finding 145), 2ccf1a9'),
    ],
    T + "check_m3_production_ui.py": [
        (f'PAGE_SHA256: str | None = "{PO}"   # host 0.2.24 (v73, finding 145), 2026-10-15; was ccb67a52',
         f'PAGE_SHA256: str | None = "{PN}"   # {WHY}; was 901dd6a6 (0.2.24, v73, finding 145), ccb67a52'),
        (f'SESSION_SHA256: str | None = "{SO}"   # link-batch §17 (0.2.23); was 62a2a20e',
         f'SESSION_SHA256: str | None = "{SN}"   # shell v74 (0.2.26); was f47c80ec (link-batch §17, 0.2.23), 62a2a20e'),
        (f'HOST_VERSION: str | None = "{VO}"   # finding 145; was 0.2.23',
         f'HOST_VERSION: str | None = "{VN}"   # engine v21 + finding 154; was 0.2.24 (finding 145), 0.2.23'),
        (f'HOST_COMMIT: str | None = "{CO}"   # finding 145; was 2ccf1a9',
         f'HOST_COMMIT: str | None = "{CN}"   # 0.2.26; was 1479e56 (finding 145), 2ccf1a9'),
        (f'SHELL_BUNDLE_SHA256: str | None = "{SBO}"   # v73; was v72 4dc10507',
         f'SHELL_BUNDLE_SHA256: str | None = "{SBN}"   # v74; was v73 6ab20f68, v72 4dc10507'),
    ],
    T + "check_m3_same_second.py": [
        (f'HOST_VERSION = "{VO}"   # finding 145 (0.2.24, v73), 2026-10-15; was 0.2.23',
         f'HOST_VERSION = "{VN}"   # {WHY}; was 0.2.24 (finding 145, v73), 0.2.23'),
    ],
    T + "check_m3_versions.py": [
        (f'HOST_COMMIT = "{CO}"   # finding 145 (0.2.24, v73), 2026-10-15 (host 0.2.24); was 2ccf1a9',
         f'HOST_COMMIT = "{CN}"   # {WHY} (host 0.2.26); was 1479e56 (finding 145, host 0.2.24), 2ccf1a9'),
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
