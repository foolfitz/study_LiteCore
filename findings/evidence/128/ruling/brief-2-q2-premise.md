# Brief 2 for fable: question 2 again — its premise did not hold (2026-10-12)

The owner chose 「交 fable 重新裁決」 after reading the measurements below. Work read-only. Every number here is in a committed file; re-derive what you rely on, and say where you could not.

## What was ruled

`fable-ruling.md` (this directory), question 2 = A: the 128-B rapid clause (max over the 4 rapid keys, all four arms, both browsers, ≤ 60 ms) is re-read on the 131-fixed page; if over 60 ms, register named limit **L-128-rapid**, worded "under keys 50 ms apart the deleted character may stay drawn up to about 100 ms after the caret moved (0.2.13 pre-fix: Chrome low 90.5, Firefox high 84.6, Firefox low 96.4; 0.2.12: 125–283 ms); single keys ≤ 40 ms hold"; default if never improved: the limit stands and is not a gate. The stated premise: "The fix in 1 does not change paint ordering, so no claim that it moves the rapid number." Spec text: `specs/SPEC-M3-autosave.md` §9.12; results and the named supersession of that premise: §9.14.

## What was measured since (page `d761f1ce…` = rule A; same host, same day)

1. **131-B holds** (`../../131/131-B/`): 12 bursts × 20 Backspaces, 0 refused, `persistent` 0 ×4. Red control (pre-fix package) refused 5/20 in each browser (`../../131/red-control/`). 121-B holds (`../../121/0.2.13-131fix-*`). 130-U holds. 129-B is running.
2. **128-B re-run** (`../final-0.2.13-131fix/README.md`, `cells.txt`): single keys all ≤ 40 ms; host segment PASS, its red control FAIL in both browsers; **rapid clause not met: low arm worst key Chrome 167.1, Firefox 220.5 ms** (the 131-B run of the same page read 213.9 / 223.8, `../../131/131-B/ghost-arms.txt`). Pre-fix: 90.5 / 96.4. So the premise above is false for the 4-key clause.
3. **Long hold, A/B over three pages** (`../../131/ghost-20/`, `../../131/ghost-20-ab/README.md`; instrument `probe_hand_test_0212.py --arms high,low --ghost-rapid-keys 20`, reader `../../131/read_ghost_long.py`): 20 Backspaces 50 ms apart.

   | Page | low: first deleted char drawn after the caret moved (Chrome / Firefox) | low: band repainted at (ms after key 1) | high: worst key | `persistent` high/low × C/F |
   |---|---|---|---|---|
   | 0.2.12 `8909564e…` | 1005.7 / 1114.8 ms | 1049.6 / 1160.5 | 562.9 / 465.2 | 21778 / 13843 / 22753 / 13843 |
   | 0.2.13 pre-fix `c7f904fa…` | 1030.0 / 1188.0 | 1072.7 / 1234.1 | 138.6 / 77.8 | 20606 / 47938 / 23122 / 13748 |
   | 0.2.13 fixed `d761f1ce…` | 1274.1 / 1296.2 | 1319.1 / 1341.9 | 281.0 / 286.3 | 0 / 0 / 0 / 0 |

   With the caret below the first band in view, the band under it is not repainted once during the burst on all three pages; every key's band turns fresh at the same instant after the keys stop. With rule A it is about 20 % longer. Without rule A a 20-key burst leaves characters in the document.
4. **132's prediction** (written before the run, §9.12): 20th-key delete time Chrome 150–250, Firefox 200–300. Measured Chrome 310–323 (missed high), Firefox 265–271 (`../../131/131-B/burst-times.txt`).

## Mechanism as read in code by the main session (a reading, not separately measured)

`web/e2-editor-app.js`: `run()` awaits `renderDocument()` before it returns (≈ line 1745); `editorAction` decrements `engineActionsOut` only after `run()` returns (≈ 1880), so an action counts as "out" through its own repaint; `renderDocument` gives up a BUSY repaint while `engineActionsOut > 0` (≈ 1264, remedy B of finding 128) and repaints only when the count reaches 0. Under rule A a burst keeps the count above 0 until the queue drains. Separately (finding 128 README H2), a pass paints the bands under the view in document order and a key ends the pass in flight, so the band below band 0 waits. Pre-fix, a refused key returned fast and opened a gap; that is the main session's explanation of the 4-key difference, not a measurement of it.

## Questions

- **Q2′.** Given 2–4, how is the rapid clause dispositioned for 0.2.13, and how is L-128-rapid worded? The main session's options: (A) apply ruling 1 with the wording corrected to the fixed page's numbers (4 keys: up to about 225 ms; a held key with the caret below the first band: the deleted characters stay drawn until the keys stop, about 1.3 s for a 1 s hold; 0.2.12 does the same, about 1.0–1.1 s, and also leaves characters behind) and move the repaint remedy into 132's post-release spec; (C) do not freeze 0.2.13 until the long-hold ghost is fixed (a new mechanism — e.g. caret band first, or letting one repaint through between queued deletes — so spec, A/B, review, and every page criterion re-run). Other options are welcome. **The main session leans A**: the long-hold ghost is older than rule A and is in what ships now; rule A removes characters left behind; the remedy is a new mechanism. Attack that lean.
- **Q2′b.** Is the 4-key clause still the right criterion form for 128's promise, given that the user-visible case (a held key) is the 20-key one? If you change the criterion, say so as a new criterion with its own "if never done", not as a reinterpretation.
- **Q4.** The main session changed one clause of the 121 witness itself (§9.13: "shape `collapsed` afterwards" read `#toolbar[data-selection-shape]`, the page's belief, which a keyboard delete never writes — unsatisfiable on any page; replaced by 121's existing 121-B instrument, which reads the saved paragraph). Was that substitution sound, or does it need something else before freezing?
- **Q5.** Anything in 132 (prediction missed for Chrome; per-key delete time 45→320 ms over 20 keys) that changes "not a blocker, post-release"?

Answer with a plain reason for the owner per question, and the exact text to append to the spec where a criterion or limit changes. Sources you read, by path and line.
