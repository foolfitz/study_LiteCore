# Where text typed during the caret-restore window lands (L-134-restore-flash, unmeasured half)

Measurement only, not a counted runner and not an acceptance arm: no product byte is touched, and the acceptance judge's arm list (`probe_held_into_refusal.py` `ARMS`) is not extended. Host 0.2.16 (`f5b34f0`), page `6470dec0…`.

## Why

Spec §15 / acceptance README: after a refusal at the document end, the new generation is `ready` for about 1 ms, then `busy` for 0.71–0.78 s while D puts the caret back. The toast reads 「正在重新載入…」 throughout. Two readings of where text typed inside that window lands:

- ruling-1 F6: "a key typed between the sink focus and the placeCaret ack lands at the start".
- review 1 (from code): it lands at the restored caret. `placeCaret` is queued in the same task as the focus, and the refusal had already emptied the typing queue.

## Arm (`probe_restore_window.py`)

Each round loads a fresh page (generation 1) and uses the owner-document copy.

1. Click the last line, press End, then press Delete **once**.
2. Poll `#s-generation` every ~20 ms until it reads `2`.
3. **Immediately** type `zqx` (three key presses about 50 ms apart, no waiting for the session to go quiet).
4. Settle, save, and read the server file back.

Recorded per round:
- the instrument log: keydowns, state, `scrollTop`;
- each typed key's time relative to the generation change and to the scroll returning (= caret restored);
- server read-back: `marks`, `markParagraphs`, sequence with marks removed against the original.

Rounds: 3 per browser.

## Prediction (written before any run)

- **Primary (review 1's reading):** all three letters land in the last paragraph (index 210), `marks == 1`, the sequence with the mark removed equals the original. The keys are typed before the scroll returns (that is the point of the arm), so the text is drawn only after the restore.
- **Would contradict it:**
  - (a) the mark in paragraph 0 — F6's reading;
  - (b) the letters split between paragraph 0 and 210 — `marks == 0` with stray letters, or the sequence differs;
  - (c) letters lost — fewer than three in the document.

  Any of these is a defect of D, registered as a finding; the page is not changed while the owner is away.
- Refusals 1, generations `['1','2']` in every round.
