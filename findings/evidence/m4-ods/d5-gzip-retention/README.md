# D5-A: does Firefox keep a 48 MB gzip response in its HTTP cache?

Spec: `specs/SPEC-M4-ods-in-nextcloud.md` §6 (instrument, controls and judgement pinned in `d7ab2815`,
before this run). Tool: `wasm_sdk_probe/tools/probe_gzip_retention_firefox.py` (judge self-test 11/11
before the run). Report: `report-2026-10-20T114325Z.json`.

## Answer: yes. Kept up to 52,428,800 encoded bytes; 53,000,000 is not kept

Firefox 157.0.1 (snap), headless, a new profile per run under `wasm_sdk_probe/build/` (ext4, /home),
default cache prefs. Server: a local `127.0.0.1` server (no ddev) sending X1's headers
(`Cache-Control: max-age=15778463, immutable`, `Content-Type: application/wasm`, `Content-Encoding: gzip`
on the subject) plus ETag and Last-Modified; its own request log is the record.

| file | bytes on the wire | role | run 0 | run 1 |
| --- | ---: | --- | --- | --- |
| `ctrl-1k.wasm` | 1,000 | must be kept | kept | kept |
| `ctrl-5m.wasm` | 5,000,000 | must be kept | kept | kept |
| `rand-20m.wasm` | 20,000,000 | must be kept | kept | kept |
| `rand-45m.wasm` | 45,000,000 | must be kept (X1: kept) | kept | kept |
| **`enc-gzip-v14.wasm`** | **47,987,215** | **the subject** (decodes to 135,237,060) | **kept** | **kept** |
| `rand-48m.wasm` | 48,000,000 | locating | kept | kept |
| `rand-50m.wasm` | 50,000,000 | locating | kept | kept |
| `rand-52m.wasm` | 52,000,000 | locating | kept | kept |
| `rand-52.4m.wasm` | 52,428,800 (= 51,200 KiB) | locating | kept | kept |
| `rand-53m.wasm` | 53,000,000 | locating | **refetched** | **refetched** |
| `rand-60m.wasm` | 60,000,000 | must be refetched (X1: not kept) | refetched | refetched |

- Both runs valid (every control as required; the subject's first fetch decoded to 135,237,060 bytes;
  every first fetch served whole) and identical file by file; monotonic.
- **Judgement (§6.3): the gzip cap is 52,428,800**, the largest size kept in both runs.
- Every request carried `Accept-Encoding: gzip, deflate, br, zstd` (on `http://127.0.0.1`), and no
  second-round request was conditional: what reached the server again was a full 200.
- The subject is the v14 `probe.wasm` gzipped by Python's `gzip` at level 9 with `mtime=0`
  (47,987,215 bytes); `gzip -9` gives 47,987,197 (`specs/SPEC-M3-zstd.md` §1). Same core, same wasm sha
  `5847a140…`.

## Read

- The boundary sits between 52,428,800 and 53,000,000 encoded bytes. That is consistent with Firefox's
  documented default `browser.cache.disk.max_entry_size` = 51,200 KiB (52,428,800 bytes), and with an
  entry exactly at it being kept. **Consistent, not read:** the attempt to read the prefs in chrome
  context failed ("System access is required. Start Firefox with -remote-allow-system-access"); the
  error is in the report, unedited.
- The overlap with X1 (2026-09-28, Firefox 156, HTTPS through ddev) agrees: 45,000,000 kept, 60,000,000
  not. So the swap of server and scheme did not move the two points both runs share.

## Not measured

- Chrome: X1 measured Chrome keeping 100 MB even on a 14 GB tmpfs profile, so Firefox is the binding
  browser; not re-measured here.
- Firefox profiles with non-default cache prefs, private windows, other Firefox versions.
