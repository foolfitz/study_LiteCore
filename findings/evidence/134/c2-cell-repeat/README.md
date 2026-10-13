# The C2 near-miss, repeated (Chrome, ratio 2 wide, owner gap 80 / 20 chars)

Measurement only. No product byte is touched, and no judge is edited: the cell's verdict stands as the guard chain printed it, PASS at 148.7 against < 150.

## Why

`../guard/c2/` (the guard chain on `6470dec0…`) gave this cell an on-screen max of 148.7 ms. The same cell read 41.1 ms on `abe93f45…` and 39.8 ms on `8909564e…`. Each of those three is a single run. The slow part was keys 9–12, with backlog 55.6 / 7.0 ms at keys 10 / 11. The cause is unknown. The open question is whether B (one sink keydown listener and two window capture listeners) costs typing latency, or whether 148.7 was a one-off.

## Run (`repeat.sh`)

- The guard chain's own command for this cell: `probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser chrome --document owner --gap 80 --chars 20`.
- **10 times**, one after another, on dist `6470dec0…`.
- Nothing else running. The script records `pgrep -c chrome` and the load average before each run.
- Read with `read_repeat.py`: per run, on-screen median and max, commit median and max, and the keys over 100 ms.

## Prediction (written before any run)

- **One-off.** Expect 8–10 of the 10 runs with an on-screen max under 60 ms and a median near the guard run's 30.5 ms. If so, 148.7 is a transient. No A/B against `abe93f45…` follows.
- **Would point at the page:**
  - (a) 4 or more of the 10 runs with an on-screen max of 100 ms or more, or
  - (b) every run's median clearly above about 35 ms.

  Then a paired A/B against `abe93f45…` is the next measurement. It needs dist swapped and restored, which waits for the owner. Nothing is changed in the page.
