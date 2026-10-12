# SPEC-M3-autosave §4 M1 — typing during a save, on host 0.2.12 (2026-10-12)

`wasm_sdk_probe/tools/probe_autosave_m1.py` (hash in `probe.sha256`; the shakedown ran an earlier version with three arms). Host 0.2.12, served page `8909564e…`; the owner's document uploaded as `probe-autosave-m1.odt`; real keys (CDP in Chrome 151, WebDriver in Firefox 157). One session per round; arms in fixed order C, A50, A100, A150, H, each behind its own marker; the server's file is read after a final manual save, and each arm's received run of letters is compared with what was sent.

| | Chrome (3 rounds) | Firefox (3 rounds) |
|---|---|---|
| C — no save, 20 keys 50 ms apart | lost 0, 0, 0 | 0, 0, 0 |
| A50 — save, then 20 keys 50 ms apart (the first save after open) | lost **3, 3, 4**; engine save 591, 597, 640 ms | lost **5, 4, 5**; 702, 670, 717 ms |
| A100 — save, then 20 keys 100 ms apart | 0, 0, 0; save 174, 164, 167 ms | 0, 0, 0; 284, 290, 309 ms |
| A150 — 150 ms apart | 0, 0, 0; 161, 170, 179 ms | 0, 0, 0; 275, 278, 288 ms |
| H — save, then one key held, 40 repeats 33 ms apart | 0, 0, 0; 168, 168, 169 ms | 0, 0, 0; 284, 268, 279 ms |

Shakedown (Chrome, one round, three arms): A at 50 ms lost 4 (`ijkl`: the 9th to 12th keys) during a 609 ms save; H lost 0 during a 173 ms save.

**What this shows**: characters typed while the engine is busy are silently lost once more than about 9 arrive (8 queued + 1 in flight) — finding 130's mechanism, observed in both browsers on the product path, with nothing shown to the user.

**The confound, stated before any reading of the other arms**: the first save after open took 591–717 ms; every later save 161–309 ms. A50 always ran first, so it is the only arm that met a long save. A100, A150 and H losing nothing says only that they met short saves; by the same arithmetic (keys arriving during the save ≥ 10), H at 33 ms would lose characters against a ~600 ms save, and A100 would not (6 keys). Not measured: the arms against a save of equal length (a warm-up save before the arms, or the arm order rotated); why the first save is slower.

Prediction record: before the shakedown, "A loses nothing; H loses characters" — both missed. Before this run, "a loss happens when saveMs / gap > 9" — consistent with all 30 arms here (A50: at least 591/50 ≈ 12 keys during the save → lost; the most any other arm met is H in Firefox, 284/33 ≈ 8.6 → lost 0).
