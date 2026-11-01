import gzip, json, sys
from pathlib import Path
ROOT = Path('/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe')
PACKAGE = ROOT / 'build/archive' / sys.argv[5]
OUT = Path(sys.argv[1])
manifest = json.loads((PACKAGE / 'MANIFEST.json').read_text())
for path in manifest['files']:
    target = OUT / path
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gzip.decompress((PACKAGE / 'files' / (path + '.gz')).read_bytes()))
sys.path.insert(0, str(ROOT / 'tools'))
import probe_typing_latency as p
p.DIST = OUT
sys.argv = ['probe_typing_latency.py', '--browser', sys.argv[2], '--document', sys.argv[3], '--gap', '200', '--chars', '10', '--out', sys.argv[4]]
raise SystemExit(p.main())
