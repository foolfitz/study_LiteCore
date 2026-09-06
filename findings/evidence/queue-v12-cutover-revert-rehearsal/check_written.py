import json, sys, pathlib
d = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
print("written:", d.get("written"), " bundleSha256:", (d.get("bundleSha256") or "")[:16])
print("problems after write:", d.get("problems"))
sys.exit(0 if d.get("written") else 1)
