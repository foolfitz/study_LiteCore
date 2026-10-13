# Brief 2 — the C2 key-10 spike: A/B against 0.2.15 now, or leave it (owner-delegated, 2026-10-13 evening)

The owner is away and said 「我授權fable帶我裁決」 for this absence. Same return format as brief 1: `RULING` / `WHY (台灣正體中文白話, ≤10 lines)` / `FACT CHECK` / `CONDITIONS`. Write it to `findings/evidence/134/c2-cell-repeat/ruling/ruling-2.md`. Do not edit product bytes or `dist/`, do not run browsers, do not commit.

## Facts (reproduce from `../run-*.json` with `../read_repeat.py`, and `../../guard/c2/`)

- The cell: Chrome, ratio 2, window 1400×1000, owner document, gap 80 ms, 20 characters (`probe_typing_latency_view.py`, local serve of `dist/`, not the ddev host). Gate: on-screen max < 150 ms (`findings/evidence/c-prime/c2/judge_c2.py`, ON_SCREEN_MAX).
- Single runs before: `8909564e…` 39.8 ms; `abe93f45…` (0.2.15) 41.1 ms; `6470dec0…` (0.2.16, guard chain) **148.7** (keys 9–12).
- 10 repeats on `6470dec0…` (`../README.md`; prediction written first): on-screen max 44.7, 43.9, 41.5, 39.5, **179.4**, 46.0, **158.0**, **180.4**, 43.7, 40.4. Medians 24.4–29.6 in every run. Every spike is at **key 10** (run 7 also key 11), and the commit time (`revisionMs`) is high there too (143.0 / 151.3 / 147.4 ms) — not only the paint. So 4 of 11 runs on 0.2.16 spike near key 10, and **3 of the 10 exceed the gate** (the cell would read FAIL about 30 % of the time).
- My prediction: one-off = 8–10 of 10 under 60 ms → got 7 (missed); page-pointing = ≥ 4 of 10 at ≥ 100 ms or medians > ~35 → got 3, medians ~26 (not met). Neither branch holds cleanly.
- The page change from 0.2.15 to 0.2.16 (`git diff 32aaddb0 702c19ec -- wasm_sdk_probe/web/e2-editor-app.js`): B adds one sink `keydown` listener and window capture `keydown`/`keyup`/`blur` listeners that compare a few fields; the `beforeinput` handler's `.catch` sets a flag; D runs only on a reopen. My reading: none of this runs work proportional to anything at key 10. Unmeasured.
- A spike at a fixed key with the commit slow too suggests something document- or engine-positional (e.g. the typed run reaching a line wrap → relayout) that a single run on 0.2.15 had a ~60 % chance to miss at this rate. That is a hypothesis, nothing more.

## The options

- **A (my lean):** paired A/B now. Interleave 10 runs on `abe93f45…` and 10 on `6470dec0…` (alternate per run, so drift hits both). The 0.2.15 page bytes come from git (`git show 0e62a763:wasm_sdk_probe/web/e2-editor-app.js`, sha-checked). `dist/e2-editor-app.js` is copied in before each run, and `6470dec0…` is restored at the end. The restore is verified three ways: sha, `check_engine_decoded.py` (dist = web = packaged), and `make test-e2-c-static` exit 0. The host is not touched, since its engine package is separate. Prediction written before: if the 0.2.15 runs spike at key 10 at a similar rate, it is not 134's, and it becomes a finding about the C2 gate / the engine. If they do not spike (0 of 10 against about 3 of 10), the page is implicated, and the next step is the owner's.
- **B:** do nothing more now. Register the spike rate (4/11 on 0.2.16, gate exceeded in 3/10) for the owner. The A/B is left to them.
- **C:** a cheaper discriminator without swapping. Run the ratio-1 owner-gap-80 cell (P2, `probe_typing_latency.py`) 10 times on 0.2.16. If it spikes at key 10 too, the cause is not ratio-specific — but that still says nothing about page versus engine.

## Questions

1. A, B or C (or other)? If A, any condition on the swap or its verification?
2. Does the guard chain's G4 "PASS" stand as the verdict of record for condition 4, given that the same cell exceeds its gate in 3 of 10 repeats? (My reading: the chain ran once as specified and printed PASS. The repeats are a separate measurement and do not re-judge it. But the release text must not say the cell is safely under its gate.)
3. Anything in my facts that is wrong.
