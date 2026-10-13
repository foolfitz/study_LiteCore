# C2 key-10 spike: paired A/B, 0.2.15 vs 0.2.16 (ruling-2, fable on the owner's behalf)

DIAGNOSTIC. `dist/` and `web/` are never written. The 0.2.15 page (`abe93f45…`, `git show 0e62a763:…`) is served through the probe's own mirror override by `ab_wrapper.py`, and so is the 0.2.16 page (`6470dec0…`): one code path for both arms.

Each report's `page` is the sha256 of the bytes the mirror held, and `servedFromMirror` records that the file was real (not a symlink into `dist/`). `ab.sh` checks `dist/` and `web/` against `6470dec0…` before and after every run, and aborts on a mismatch.

**Cell:** exactly the guard's: Chrome, `--dpr 2 --window 1400x1000 --document owner --gap 80 --chars 20`. 20 runs interleaved: odd = 0.2.15, even = 0.2.16. One at a time, fresh browser each.

**Reader:** `read_ab.py`. Spike := on-screen ≥ 100 ms at any of keys 9–13. The stall signature is the longest `raw.paints` gap in [key 8, key 13 + 100 ms].

## Decision rule (ruling-2 condition 5; fixed before the run)

| spikes per 10 | reading |
|---|---|
| 0.2.16 < 2 | A/B VOID; stop and report; no `dist/` swap |
| 0.2.15 ≥ 2 and 0.2.16 ≥ 2 | not 134's; finding 135 is the engine's / the gate's |
| 0.2.15 = 0 and 0.2.16 ≥ 3 | page implicated; nothing changed; the same 10 + 10 once more before the owner acts |
| otherwise | one extension of 10 + 10, once; then report as is |

**fable's prediction (ruling-2 §4):** both arms spike at comparable rates.
