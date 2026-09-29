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

## The fix and its counted verdict: `SAME-SECOND SAVES KEPT` (2026-09-29)

Criteria: `specs/SPEC-M3-versions.md` §4 R2 `same-second` and R3 `same-second-foreign`, written
before the runner and the host change (R2 in `b498d213`; R3 and the rest -- see that spec's §6 for
what git can and cannot show about the order). Runner: `wasm_sdk_probe/tools/check_m3_same_second.py`
(a separate runner; the R1 runner stays bound to `VERSIONS CORRECT`).

**Host 0.2.2** (`~/Projects/Nextcloud_Apps/litecore` `695d9ad`; only `js/litecore-editor.js` and
`appinfo/info.xml` changed, page `fbfb59a4…`, no shell, no relink -- ruling conditions 3, 5, 6):

- a PUT to the file waits until 1.1 s after the host's previous PUT was answered (monotonic
  clock; the 0.1 s is for coarsened timers, review item 8); a save that does not follow another
  that closely waits 0 ms;
- before each PUT, after the wait, the host reads the file back (`no-store`) and compares it
  with the bytes its ETag belongs to; the same version with other bytes (someone else's write
  in that second, finding 103) goes to a conflict copy, not over the file. A read that breaks
  off decides nothing -- the PUT does, as on 0.2.1 (review item 1; **no net exercises that
  path**).

| Report | Host | Result |
| --- | --- | --- |
| `shakedown/2026-09-29T031241+0000.json` | 0.2.1 | first runner; Chrome and Firefox run 1 died on finding 104's off-by-one `Content-Length` (after the restore); runs 2 red in (a)(b)(c) and the 104 cell |
| `shakedown/2026-09-29T031828+0000.json` | 0.2.1 | **the red run before the fix**: R2 4/4 red in (a), (b), (c) and (c) 104 (S23 gone after the restore); R3 4/4 red in kept, copy, page (premise held: X landed in S1's second; S2 then overwrote it with a 204) |
| `shakedown/2026-09-29T032619+0000.json` | 0.2.2 draft (1.0 s) | 8/8 clean; R3's entry condition measured here |
| `shakedown/2026-09-29T035413+0000.json` | 0.2.2 final (uncommitted) | 4/4 clean |
| **`runs/2026-09-29T035833+0000.json`** | **0.2.2 `695d9ad`, clean** | **`SAME-SECOND SAVES KEPT`**: R2 Chrome 3/3, Firefox 3/3; R3 Chrome 3/3, Firefox 3/3; page `fbfb59a4…` in `dist/` and `web/`; `make test-e2-c-static` 0; runner `a4356968…` (= commit `28ba8f45`); 03:58:33–04:09:35Z, no ddev container created in that window |

Red cases (`--red-cases`): 70, every one red on the counted report and on both clean 0.2.2
shakedowns; a no-op mutation reports GREEN; switching off any single sub-clause of the scorer
turns at least one case GREEN (review item 3, re-run by the main session). On the 0.2.1 report the
product-level red is the runs themselves; synthetic cases on an already-red base can "add a line"
by changing a message's text, so they are cited on the clean reports (review item 11).

Registered, not gated (R2, counted report):

- **Wait**: every second-in-a-row save waited 982–1091 ms; every first save 0 ms.
- **Latency the user sees** (the page's own line, "存回 N ms"): the second save of a pair went
  from 38–58 ms (0.2.1, `031828Z`) to 1048–1161 ms; a save that does not follow another went
  from 50–57 ms to 67–71 ms (the read-back GET, ~24 ms).
- **R3 entry condition** (median read-back GET <= median PUT, host's own record): Chrome 24 vs
  46 ms, Firefox 24 vs 46 ms over 69 saves each (also held per single run in the shakedowns).
  Only on the 9.5 KB fixture; the read-back downloads the whole document before every save.
- **0.2.1 same-second pairs per run** (phase-controlled): 8, 9, 9, 8, 9, 8 of 10 -- more than the
  ~7 predicted before running; the restore pair shared a second in all six. The misclassified
  pairs under a send-phase rule are all PUTs sent at >= .965 of a second whose write landed in the
  next one (the server stamps the mtime ~30 ms after the send).

## Condition 7: the four earlier counted runners, re-run on 0.2.2 (2026-09-29)

Dev instance, host `695d9ad` (0.2.2) clean, page `fbfb59a4…`; each runner unchanged except the
one binding written down before the run (`check_m3_versions.HOST_COMMIT` 5e53362 -> 695d9ad,
commit `b1b46ef7`; spec §3). Run one after another by a script (each runner clears the whole lock
table), each followed by its own `--red-cases` on the counted report. No ddev container was
created from 03:58Z to 05:07Z (newest: 2026-09-28 14:33Z).

| runner | report | verdict | red cases |
| --- | --- | --- | --- |
| locks | `../m3-locks/runs/2026-09-29T040942+0000.json` (04:09–04:55Z) | `LOCKS LAND`, all 22 cells, 52/52 | 87, all red (same count as before) |
| versions R1 | `../m3-versions/runs/2026-09-29T045548+0000.json` (04:55–04:59Z) | `VERSIONS CORRECT` 3/3 + 3/3 | 68, all red (same) |
| assets | `../m3-assets/runs/2026-09-29T045936+0000.json` (04:59–05:02Z) | `ASSETS DELIVERED` 3/3 + 3/3 | 84, all red (same) |
| host entry | `../m3-host-entry/runs/2026-09-29T050202Z.json` (05:02–05:07Z) | `HOST_ENTRY LANDS` (open-save 3/3 + 3/3, conflict 3/3 + 3/3, broken 1/1, broken-no-save 1/1) | 23, all red (its "GREEN base" line is the unmutated report landing) |

**No expectation was amended.** Fable's F2 caveat (a wait or an extra GET might break shapes such
as one attempt per save, or the second save chaining on the first's version) did not bite: the
read-back is recorded inside the attempt, the nets count only PUTs, and a pair of saves in these
nets is never within 1.1 s of each other's answer except on the retry paths (expired /
broken-then-written), which kept their shapes with about a second more of waiting. The one
place 0.2.2 behaves differently from 0.2.1 by design -- the read-back finding the same version
with other bytes -- is reached by none of them (R3 is the only net that reaches it).

## Condition 4: held Ctrl+S after the fix (2026-09-29)

The condition-1 probe, unchanged (`probe_m3_same_second_saves.py`), on the committed 0.2.2
(`695d9ad`, tree clean): `2026-09-29T050705+0000.json`.

| | 0.2.1 (`023742Z`) | 0.2.2 (`050705Z`) |
| --- | --- | --- |
| button + Ctrl+S pairs with the same ETag | Chrome 5/12, Firefox 6/12 | **0/12 and 0/12** (0 of 99 consecutive pairs in each browser) |
| versions added by the 24 pair saves | 19, 18 | **24, 24** |
| PUTs per 1-s held Ctrl+S | 30 ×3, 30 ×3 | 30 ×3, 30 ×3 |
| first to last PUT of a hold | 3.72–3.80 s, 4.71–5.17 s | 34.64–34.71 s, 34.93–35.20 s |
| versions added by the 90 held saves | 15, 18 | **90, 90** |

A 1-s hold still sends 30 PUTs (> 5): registered as **finding 106** against the page
(`event.repeat` unfiltered is page identity); nothing was added to the host (condition 4).
`2026-09-29T033411+0000.json` is the same probe on the pre-review draft host (1.0 s spacing,
uncommitted): 0/99 same-ETag, tails 31.5–32.3 s.
