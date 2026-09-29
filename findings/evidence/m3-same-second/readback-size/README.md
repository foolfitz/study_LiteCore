# Read-back cost vs document size (2026-09-29)

Criteria: `CRITERIA.md` (commit `3f76f82d`, before the probe and before any run). Probe:
`wasm_sdk_probe/tools/probe_m3_readback_size.py` (`84119cb6…` = commit `24eb14d9`).
A measurement, not a gate: no verdict moves, no product byte changed.

## Result: `2026-09-29T060123+0000.json` — R-a holds at every size, both browsers

Host `litecore` `695d9ad` (0.2.2) clean; dev instance; 06:01:23–06:07:28Z. Six saves per arm,
all six counted in every arm (read-back 200 + sha256, PUT 204, host wait 0 ms).

| Arm | Read-back GET (bytes) | Read-back ms | PUT ms | Ratio | Engine ms | End-to-end ms | Read-back share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Chrome, fixture | 9,760 | 24.0 | 75.0 | 0.32 | 91.0 | 185.5 | 0.13 |
| Firefox, fixture | 9,747 | 27.5 | 80.5 | 0.34 | 113.0 | 222.0 | 0.12 |
| Chrome, 1 MiB | 1,062,651 | 28.5 | 87.0 | 0.33 | 113.5 | 233.5 | 0.12 |
| Firefox, 1 MiB | 1,062,654 | 30.0 | 84.5 | 0.36 | 137.0 | 255.5 | 0.12 |
| Chrome, 5 MiB | 5,253,206 | 40.5 | 117.5 | 0.34 | 189.5 | 355.0 | 0.11 |
| Firefox, 5 MiB | 5,253,202 | 43.0 | 104.0 | 0.41 | 217.0 | 370.5 | 0.12 |
| Chrome, 20 MiB | 20,997,818 | 91.5 | 241.0 | 0.38 | 481.0 | 834.0 | 0.11 |
| Firefox, 20 MiB | 20,997,836 | 97.5 | 173.5 | 0.56 | 538.5 | 844.0 | 0.12 |
| Chrome, 50 MiB | 52,414,426 | 185.5 | 475.0 | 0.39 | 1122.5 | 1827.5 | 0.10 |
| Firefox, 50 MiB | 52,414,477 | 189.0 | 311.0 | 0.61 | 1201.5 | 1754.0 | 0.11 |

Medians over the six saves. Ratio = read-back / PUT (R-a: <= 1). Share = read-back / end-to-end.
Stronger than the medians: in every arm the slowest read-back was faster than the fastest PUT
(e.g. Firefox 50 MiB: read-back 176–195 ms, PUT 301–346 ms).

**Reading, per `CRITERIA.md`**: R-a holds at every measured size in both browsers, so the
condition-6 admission extends from 9.5 KB to about 50 MiB (52.4 MB). The next page round
(C + I) carries no host change for the read-back.

Descriptive:

- **The read-back is a full, uncompressed download.** Its `encodedBodySize` equals the bytes
  the previous save put, to the byte, in every row (the first save reads the uploaded fixture).
  So every save moves the document twice over the wire: once down, once up.
- **The documents were real.** The pictures survived every save (1, 2, 7, 17 in the saved file
  for 1/5/20/50 MiB); no conflict copy was made; each arm's leave released the lock.
- **Firefox's ratio grows with size** (0.34 → 0.61) because its PUT is faster than Chrome's at
  20 and 50 MiB, not because its read-back is slower (the read-backs match within 6%). Not
  extrapolated past 50 MiB.
- **The PUT here is slower than R2's** at the same 9.5 KB (75–80 ms vs 46 ms in
  `../runs/2026-09-29T035833+0000.json`); the read-back matches (24–27 vs 24 ms). Not explained;
  not needed for R-a, which compares within one run.
- The engine's serialization is the largest part of a save at every size (61% Chrome,
  68% Firefox of end-to-end at 50 MiB); the read-back is 10–13%.

## Named limits

- **Localhost.** ddev runs on this machine, so transfer is nearly free; this measures server and
  browser processing. On a real link the read-back adds about `size / downlink` (a 50 MiB
  document on a 100 Mbit/s downlink: ~4.2 s, arithmetic, not measured). Inference, not measured:
  where downlink >= uplink the transfer part favours the read-back over the PUT.
- **Page identity was not bound by the probe.** Read after the run: the page the host serves,
  `~/Projects/Nextcloud_Apps/litecore/engine/files/e2-editor-app.js.gz`, decompresses to
  `fbfb59a4…`, file time 2026-09-29 01:19 +0800, before the run; `wasm_sdk_probe/web/` and
  `dist/` have the same bytes.
- The read-back's failure path is still exercised by no net.
- One run, six saves per arm. Sizes above 50 MiB were not tried.

## Other files

- `shakedown/2026-09-29T055204+0000.json`: died on the first save; Chrome's
  `Network.requestWillBeSent` carried the 5 MiB PUT body as a 12.8 MB CDP frame, over the client's
  1 MiB limit. The probe now disables Chrome's Network events after the open (Resource Timing gives
  the bytes). The shared `probe_m3_gate0_coep.py` was not touched.
- `shakedown/2026-09-29T055805+0000.json`: 5 MiB, two saves per browser, both counted (so "not
  measured" by design, < 5 saves).
- `aborted/2026-09-29T055923+0000.json`: the first full run; died opening the second Firefox arm
  (every Firefox arm made `firefox-profile` in one scratch directory). Its three finished arms
  passed; it is not counted, and the full run above was started from scratch.
