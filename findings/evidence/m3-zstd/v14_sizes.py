import gzip, json
from compression import zstd
p = "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/dist/profiles/e2-editor-v14/probe.wasm"
raw = open(p, "rb").read()
g = gzip.compress(raw, compresslevel=9, mtime=0)
z = zstd.compress(raw, level=19)
print(json.dumps({"profile": "e2-editor-v14", "bytes": len(raw), "gz": len(g), "zst": len(z)}))
