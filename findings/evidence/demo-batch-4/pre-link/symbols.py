#!/usr/bin/env python3
"""What writer_caret_bridge.o will ask the link for, read before the link: the undefined C++ symbols the bridge's source names from outside UNO's
inline headers must be defined in an archive of the Writer core.  llvm-nm only, compiles nothing.  `sfx2` is the one library the Writer engine has
not called into directly until now; the Calc bridge calls the same two, on another core."""
import json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
CORE = ROOT / 'wasm-lite/build-headless-probe'
NM = ROOT / 'wasm-lite/tools/emsdk/upstream/bin/llvm-nm'
WANT = ['SfxLokHelper::getViewOfId', 'SfxViewShell::GetCurrentDocument', 'comphelper::SolarMutex', 'Application::GetSolarMutex']
found = {w: [] for w in WANT}
archives = sorted(CORE.glob('instdir/program/*.a')) + sorted(CORE.glob('workdir/LinkTarget/StaticLibrary/*.a')) + sorted(CORE.glob('workdir/LinkTarget/Library/*.a'))
for a in archives:
    r = subprocess.run([str(NM), '--defined-only', '--demangle', '--no-weak', str(a)], capture_output=True, text=True, errors='replace')
    for line in r.stdout.splitlines():
        for w in WANT:
            if w in line and ' T ' in line and len(found[w]) < 3:
                found[w].append(a.name + ': ' + line.split(' T ', 1)[1][:80])
held = all(found[w] for w in WANT[:2])
report = {'archives': len(archives), 'found': found, 'verdict': 'SYMBOLS_HOLD' if held and archives else 'SYMBOLS_RED'}
(Path(__file__).parent / 'symbols.json').write_text(json.dumps(report, indent=1) + '\n')
print(json.dumps(report, indent=0)[:900])
