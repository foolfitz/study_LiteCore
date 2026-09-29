# Can the host's own saves land in one wall-clock second? (measured 2026-09-29)

Asked by fable's ruling (`ruling-2026-09-29-fable-d.md`, option D, **condition 1**: measure
before any host change for findings 103/104; every counted run so far had its two saves
≥ 1.18 s apart — the harness's path, not the user's). Tool:
`wasm_sdk_probe/tools/probe_m3_same_second_saves.py`. Dev instance, host `5e53362` (0.2.1)
unchanged, page `fbfb59a4…` unchanged, one editor session per browser, opened from Files.

- **pairs**: the save button, then Ctrl+S with no wait (one evaluation), 12 times, 1.5 s apart.
- **held**: Ctrl+S "held" ~1 s — 30 keydowns 33 ms apart, the first `repeat: false`, the rest
  `true` (the page does not filter `event.repeat`), 3 trials, each until the queue drains.

A same-second pair = two consecutive 2xx saves with the same ETag in the host's own record
(Nextcloud keeps the ETag for a second write in the same second — finding 103; after such a pair
any restore loses the later write — finding 104).

## Result: `2026-09-29T023742+0000.json`

| | Chrome 156 | Firefox 156 |
| --- | --- | --- |
| saves (all 204, each with different bytes) | 114 | 114 |
| button + Ctrl+S pairs with the same ETag | **5 of 12** | **6 of 12** |
| send-to-send gap inside a pair | 140–177 ms | 169–195 ms |
| versions added by the 24 pair saves | 19 (5 missing = the 5 same-ETag pairs) | 18 (6 missing) |
| PUTs per 1-s held Ctrl+S | 30, 30, 30 | 30, 30, 30 |
| how long each held burst kept writing | 3.80, 3.72, 3.80 s | 4.71, 5.17, 4.97 s |
| versions added by the 90 held saves | 15 | 18 |

**Condition 1 is met in both browsers** (≥ 1 equal-ETag pair each) — the ruling's work proceeds
(condition 2 next: criteria before code). These pairs are the fix's red case.

Also registered:

- **Held Ctrl+S sends one save per key repeat**: 30 PUTs for a 1-s hold, the burst running
  4–5 s. Condition 4's threshold (> 5 PUTs) is already exceeded on 0.2.1; after the host fix
  this is to be registered as a finding against the **page** (`event.repeat` unfiltered is
  page identity), not answered with a host mechanism.
- **Not explained**: with ~160 ms between the two PUTs, most pairs would be expected to share a
  second, yet about half did (5/12, 6/12). The history loss matches the ETag signal exactly
  (every same-ETag pair cost one version, no other pair did). Why the rate is ~½ was not
  looked into; the fix (≥ 1 s between the host's own PUTs) does not depend on it. *(Explained
  afterwards: it is phase, not chance -- see the addendum at the end.)*

Smoke run before it (`smoke/2026-09-29T023637+0000.json`, Chrome, 2 pairs, 1 held): both pairs
same-ETag, 30 PUTs for the hold; its first version of the probe stored the file's whole version
list (the file keeps its id across resets, ~500 revisions), which the full run replaced by the
revisions each phase added.

## Addendum (2026-09-29, before R2 was written): the "about half" is phase, not chance

Read from the same report, no new run. The host's own clock (`started` + `attempts[].at`) gives
where in the wall-clock second each PUT was sent:

| | pairs with different ETags | pairs with the same ETag |
| --- | --- | --- |
| Chrome | pair 0–6: first PUT at .856–.952 of a second, second at .033–.092 of the next | pair 7–11: first at .965–.018, second at .133–.166 |
| Firefox | pair 0–5: first at .840–.954, second at .013–.149 of the next | pair 6–11: first at .984–.143, second at .172–.329 |

The same-ETag pairs are not scattered: they are the **last** five (Chrome) and six (Firefox)
pairs, contiguous. The probe pressed a pair every ~3.01 s (drain + 1.5 s), so the phase in the
second drifted by ~13 ms per pair; it started late in a second (.84–.89), so the early pairs
straddled the boundary and the later ones, having drifted past it, did not. The split sits at a
first-PUT send phase of about .95–.97: the first write's server mtime is taken after the send
(a write starting at .965 already lands in the next second). For a pair pressed at a random phase
with a ~160 ms gap, the same-second rate would be about 1 − 0.16 ≈ 0.84, not ½.

Consequence for R2 (`specs/SPEC-M3-versions.md` §4): the runner controls the phase instead of
relying on chance -- ten pairs at phases .05, .15, …, .95, and the restore pair at .05.
