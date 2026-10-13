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

## Result (2026-10-13 01:06–01:12Z; 20/20 exit 0; dist/ and web/ = `6470dec0…` before and after every run; every report's `servedFromMirror` is a real file with the arm's sha)

`read_ab.py` (`read_ab-output.txt`):

- 0.2.15 (`abe93f45…`) **1/10** spikes. Run 09: key 10 at 147.9 ms, key 11 at 105.5 ms; commit max 140.4; stall gap 196.6 ms.
- 0.2.16 (`6470dec0…`) **0/10** spikes. Screen max 40.4–49.9; stall gaps 84.3–101.9 ms.

**Decision by the rule fixed before the run: A/B VOID.** The 0.2.16 arm does not reproduce the counted cell (fewer than 2 of 10). No `dist/` swap follows in the owner's absence.

**Observation, not a verdict:** the one spike in this A/B is on the **0.2.15** page. It carries the same signature as the 0.2.16 spikes: key 10, commit about 140 ms, a paint gap of about 200 ms right after key 9. Elsewhere the longest gap is 87–106 ms. So the stall occurs on a page without B + D. That bears on "is it 134's"; under the rule, it does not settle it. Rates so far:

| page | spiking runs | sources |
|---|---|---|
| 0.2.16 | **4/21** | guard 1/1, repeat 3/10, A/B 0/10 |
| 0.2.15 | **1/11** | guard 0/1, A/B 1/10 |

The repeat chain's 3/10 against this A/B's 0/10 on the same page shows the rate itself moves between sessions. Load was 0.9–1.8 for the repeat chain and 0.7–1.0 here; that is a correlation, not a cause.
