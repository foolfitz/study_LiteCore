# SPEC-M3-autosave §8.1 Q6 — M1 rerun without run-1's confound (`--mode m1b`), host 0.2.12 (2026-10-12)

`wasm_sdk_probe/tools/probe_autosave_m1.py --mode m1b` (hash in `probe.sha256`; the default `m1` mode that produced `../m1/run-1.json` is unchanged). Host 0.2.12 `b245ae7`, served page `8909564e…`, engine v19; the owner's document uploaded as `probe-autosave-m1.odt`; real keys (CDP in Chrome 151, WebDriver actions in Firefox 157). `run-1/report.json` 03:11:57–03:35:29 UTC; `shakedown/` is one Chrome round before it (same picture: cold Hpre lost 11, everything else 0).

## Design (from the probe's docstring, written before the first m1b run)

Per round and browser, four sessions, each a fresh browser and a fresh upload:
- **warm**: a warm-up save first (one letter, save, settle), then C, A50, A100, A125, Hpre, each after its own marker, so every arm meets a later (short) save; then **I30**: 30 s with no input, then A50's shape again.
- **cold-A100**, **cold-A125**, **cold-Hpre**: that one arm only; its save is the first after open (the long one — as autosave's first will be).

A*n*: press save, then 20 letters *n* ms apart. Hpre: one letter held (repeats every 33 ms requested; measured median gap 35 ms in Chrome, 37–38 ms in Firefox, where each press is a WebDriver call) for 1.0 s **before** save is pressed and 1.5 s after.

## Result — letters lost (engine save ms in brackets)

| | Chrome r1 | Chrome r2 | Chrome r3 | Firefox r1 | Firefox r2 | Firefox r3 |
|---|---|---|---|---|---|---|
| warm-up save (first after open) | [625] | [678] | [655] | [753] | [663] | [696] |
| warm C (no save) | 0 | 0 | 0 | 0 | 0 | 0 |
| warm A50 | 0 [213] | 0 [265] | 0 [181] | 0 [292] | 0 [294] | 0 [280] |
| warm A100 | 0 [160] | 0 [185] | 0 [164] | 0 [282] | 0 [276] | 0 [270] |
| warm A125 | 0 [176] | 0 [171] | 0 [162] | 0 [291] | 0 [292] | 0 [260] |
| warm Hpre | 0 [180] | 0 [165] | 0 [193] | **1** [284] | **1** [277] | **1** [273] |
| warm I30 (after 30 s idle) | 0 [159] | 0 [157] | 0 [160] | 0 [307] | 0 [288] | 0 [367] |
| cold A100 | 0 [642] | 0 [628] | 0 [577] | 0 [701] | 0 [676] | 0 [646] |
| cold A125 | 0 [690] | 0 [603] | 0 [591] | 0 [744] | 0 [676] | 0 [887] |
| cold Hpre | **12** [632] | **11** [612] | **10** [584] | **12** [694] | **12** [690] | **20** [1032] |

Held-key arms, keys whose send time falls inside [save pressed, save pressed + engine save ms] against letters lost (from `sendMs`, `savePressedMs`, `saveMs`): Chrome cold 19→12, 18→11, 17→10; Firefox cold 19→12, 19→12, 28→20; Firefox warm 8→1 (×3); Chrome warm 5–6→0. Loss = keys during the save − 7 or 8, in every held arm.

Firefox r3's last two cold sessions ran while the native measurements of task 2026-10-12c were using the CPU (load average 2.18 at 03:35 UTC, against 0.75 at the start); their saves (887, 1032 ms) are the two longest here. Their outcome follows the same rule.

## Prediction record (written before the first m1b run)

- cold-A100 and cold-A125 lose nothing — **held** (12/12 sessions).
- cold-Hpre loses about 9–12 — **held** in 5 of 6 (10, 11, 12, 12, 12); Firefox r3 lost 20 against a 1032 ms save (the rule held; the range did not).
- nothing loses in the warm session, Hpre included ("at most 9 keys") — **missed in Firefox**: warm Hpre lost 1 in all three rounds (8 keys arrived in a 273–284 ms save; the queue takes 8 including the one in flight — `input/input-adapter.js` `queuedDepth >= this._maxQueueDepth` counts `_processing` — so the 9th of the burst is the first refused). The prediction's threshold was one too high.
- I30's save is short — **held** (157–367 ms): the first save's extra ~400 ms is paid once per open, not again after an idle stretch.

## What this settles for the spec

- Real typing speeds (8–10 keys/s) lose nothing even against the long first save after open — the save autosave will meet first. Q6's condition for raising the queue limit ("if real typing speed is also rejected") is **not met**.
- A held key (25–30 repeats/s) loses characters against any save longer than about 250 ms, silently on 0.2.12 — finding 130's toast is the remedy in scope; the limit stays at 8.
- Open item 3 of the handoff (why the first save is slower) is narrowed, not explained: it is per open, not per idle.
