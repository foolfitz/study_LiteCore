# Read-back cost vs document size — criteria (written before the probe and before any run)

## Question

Ruling D condition 6 admitted half B (host 0.2.2 reads the file back before every PUT) on
"extra latency <= one PUT", operationalized in `../README.md` as **median read-back <= median
PUT, from the host's own record**. That was measured on the 9.5 KB fixture only, and the
read-back downloads the whole document. Does the admission hold at realistic sizes?

This is a measurement, not a gate. It moves no verdict and changes no product byte.

## Arms

- Host `litecore` `695d9ad` (0.2.2), clean; page `fbfb59a4…`; dev instance; Chrome and Firefox.
- Sizes: the existing fixture (anchor, links to the admitted number), then generated ODTs of
  about 1, 5, 20 and 50 MB: the fixture's text plus N stored, incompressible (seeded-noise) PNGs,
  each as-char inside a `text:p`. Fixture sha256 recorded per arm.
- Per (browser, size): open from Files once, then 6 saves through Ctrl+S, each pressed >= 2.5 s
  after the previous one settled, so the host's spacing wait is 0.

## Metrics, per save, from the host's own record (`data-litecore`)

- `readback` = `attempt.check.ms` (GET + body + sha256).
- `put` = `attempt.respondedAt - attempt.at`.
- `getBytes` = the read-back's `encodedBodySize` from Resource Timing; `putBytes` = `record.bytes`.
- `engine` = `record.at - pressAt`; `endToEnd` = `attempt.respondedAt - pressAt`
  (`pressAt` read as `Date.now() - out.started` in the same evaluation that presses).

## Criterion (the only one)

**R-a**, per (browser, size): median `readback` <= median `put` over the counted saves.
Unchanged from condition 6; only the size range is new.

A save counts only if: its first attempt has `check.status` 200 and a `check.sha256`, its PUT is
2xx, and `waited` <= 50 ms. A (browser, size) with fewer than 5 counted saves, or whose document
did not open, is **not measured** (reason recorded) — it neither passes nor fails.

## What each outcome means (fixed now)

- R-a holds at every measured size in both browsers: the admission extends to the largest
  measured size; `../README.md`'s "only on the 9.5 KB fixture" line gets an appended correction.
  The next page round (C + I) carries no host change for the read-back.
- R-a fails at some size: the admission holds only below the smallest failing size. That limit is
  registered in finding 103, and the next page round must include a host change for it. No
  mechanism is designed in this step (a candidate has to be measured before it is admitted).
- The largest size measured in both browsers is under 5 MB: inconclusive for the realistic
  range; say so, do not extrapolate.
- **If this is never run**: the admission stays "9.5 KB only", as registered.

## Descriptive only (no threshold)

`getBytes` vs the server's size (whether the read-back is a full, uncompressed download);
`engine`, `endToEnd`, and `readback / endToEnd`.

## Named limits, up front

- **Localhost.** ddev runs on the same machine; transfer is nearly free, so this measures server
  and browser processing, not a link. On a real link the read-back adds about
  `getBytes / downlink`. Inference, not measured: where downlink >= uplink, the transfer part
  favours the read-back over the PUT at least as much as here.
- The failure path of the read-back is still exercised by no net; this does not change that.

## Self-checks before counting

- The analyser has a `--self-test` with synthetic rows that must come out: read-back > PUT at one
  size -> FAIL; a save with no `check` -> not counted; `waited` 1100 -> not counted; 4 counted
  saves -> not measured. Each must fail the way named, or the analyser is not used.
