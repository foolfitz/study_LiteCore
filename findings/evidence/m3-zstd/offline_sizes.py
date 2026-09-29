import json, sys, time, hashlib
from pathlib import Path
from compression import zstd
app = Path.home() / "Projects/Nextcloud_Apps/litecore"
dist = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/dist")
m = json.loads((app / "engine/MANIFEST.json").read_text())
print("libzstd", zstd.zstd_version_info, file=sys.stderr)
out = {}
for path, e in m["files"].items():
    raw = (dist / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == e["sha256"], path
    t = time.monotonic()
    z = zstd.compress(raw, level=19)
    dt = time.monotonic() - t
    fp = zstd.get_frame_info(z)
    # window from frame header
    fhd = z[4]; single = (fhd >> 5) & 1
    if single:
        win = None
    else:
        wd = z[5]; exp = wd >> 3; mant = wd & 7
        base = 1 << (10 + exp); win = base + (base // 8) * mant
    assert zstd.decompress(z) == raw
    out[path] = {"bytes": e["bytes"], "gz": e["gzBytes"], "zst": len(z), "single": single, "window": win,
                 "contentSize": fp.decompressed_size, "sec": round(dt, 1)}
    print(path, out[path], file=sys.stderr, flush=True)
tot = {k: sum(v[k] for v in out.values()) for k in ("bytes", "gz", "zst")}
print(json.dumps({"files": out, "totals": tot}, indent=1))
