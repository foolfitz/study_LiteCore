# The batched count on host 0.2.24 (0.2.13–0.2.24, engine v20, finding 145's page fix) — result (2026-10-16)

Reading table: ruling **J-a.2** (`handoff/RULING-2026-10-15-pre-binding.md`); C2 by **J-b.2**; the R arms by **SPEC-M3-link-batch §17.4**; the product-path verdict by its `SUMMARY` line (§34.7). Chain and reader: `runs-0.2.24/` (`chain-0.2.24.sh`, `read-0.2.24.sh`, README). The count before this one, 0.2.23's, ran to `DONE` and did not hold (merge `VERDICT FAIL`, finding 145; `runs-0.2.23/`, handoff 10-15c). The last count that held is 0.2.12's (`RESULT-0.2.12.md`).

## What was counted

| What | Value |
|---|---|
| Host | `litecore` **0.2.24**, `1479e56`, clean (`dirty[]`), installed with `ddev occ upgrade` |
| Engine package | buildId `d3cd39bbc71ec311` (engine v20, wasm `313b08d5cb085897`); archived read-only in `wasm_sdk_probe/build/archive/host-0.2.24-engine-d3cd39bbc71ec311/` |
| Page | `901dd6a6…` (`f7887ced`, finding 145's fix); dist = web = archive = served, at `IDENTITY-START` and at `IDENTITY-END` |
| Shell | v73 `6ab20f68…` (`2c3c6ed5`) |
| Tree at `START` | `db2f8001` |
| Runners (sha256[:16], from `START`) | production UI `24be3053ff7ddfba`, autosave `b07e35de3bce81fd`, new-document `c82c3ad895e16901`, product path `9d1f44c6be8a45a3`, merge `f900820773990725`, C2 view `1412e4c863de6fcb`, probe `dbad93c0dcf27fbf` |
| What the count carries | the uncounted list of SPEC-M3-link-batch §7 (127–136, 138, 140, 141, 143, 144, 132's page fix, v20) plus finding 145's fix |

## The chain (`runs-0.2.24/chain-20261015T164456Z.out`)

- **Started by the owner** at 2026-10-15T16:45:38Z (00:45:38 Asia/Taipei), inside the agreed window 00:45–11:00, after the two expired runner locks were deleted by id (`runs-0.2.24/lock-cleanup-2026-10-16.txt`) and preflight read 0 refusals (`preflight-only-2026-10-16.txt`).
- **`DONE`** at 2026-10-16T00:44:49Z (08:44:49 Asia/Taipei): **7 h 59 m 11 s** (0.2.23's re-run: 10:59 → 19:17 local).
- **`IDENTITY-END` equals `IDENTITY-START`** field for field: host `1479e56` `dirty[]` 0.2.24, buildId `d3cd39bbc71ec311`, dist / web / archive / host-served page `901dd6a6dbff6ad6`.
- **The desk** had 47 `DESK` lines. Load ranged 1.08–3.37, with 2.97 at `START` and 2.18 at `END`. `ours` was 0 on every line. The owner's Chrome (19 browser processes) was open at the start and gone by the end. kwallet stayed unlocked, and the host login read `rc=0` on every line. Load is recorded, never gated (J-a.3).
- **The eight shakedowns were clean** (16:45–18:04Z, 79 min), so the STOP rule did not fire.
  - Page honesty: `clean`.
  - Locks, versions, assets, same second: `clean`.
  - Host entry: `LANDS`.
  - Autosave: `clean`.
  - New-document: `WORKS`.

### J-a.2's row

`DONE`; every counted runner exit 0 with its green verdict line; red cases all red; identity equal → **"The count holds"**, subject to the hand readings below. The table also covers the two exits of 1 the chain prints:

- the six Firefox product-path reports exit 1 on the known red `an-inline-format-reaches-a-selection` (3 of 3 rounds, both arms, as in 0.2.12 and 0.2.23); J-a.2's last row: the `SUMMARY` line decides;
- `merge pair-chrome` / `pair-firefox` exit 1 (as in 0.2.23's chain); the pair step writes its comparison and the merge judge reads it: `control PASS, pairs 78, differ 0` in both browsers.

## The counted reports

| Report | Result |
|---|---|
| production UI `runs-0.2.24/counted-KR-x3.json` | **Kdel, Kbs, Rbs, Rdel 3/3 each in both browsers (24/24)** |
| production UI `runs-0.2.24/counted-ctl-S-P.json` | Bctl, S, P 1/1 each, both browsers (6/6) |
| production UI B3x | **not run**: withdrawn since the 0.2.23 count (SPEC-M3-link-batch §17.3, same engine v20) |
| production UI, pooled mutations | **`red cases: 28/28`**, 13 `no passing B3x run` notes (all A1-5), exit 1 by the runner's every-mutation rule, as expected (`runs-0.2.24/red-cases-on-counted-pooled.txt`) |
| page honesty `m3-page-honesty/runs/2026-10-15T183256+0000.json` | **PAGE HONEST**, all 30 cells 3/3; red cases 154 |
| locks `m3-locks/runs/2026-10-15T193833+0000.json` | **LOCKS LAND**, all 22 cells full, `problems=[]`; red cases 101 |
| versions `m3-versions/runs/2026-10-15T202826+0000.json` | **VERSIONS CORRECT** 3/3, 3/3; red cases 68 |
| assets `m3-assets/runs/2026-10-15T203305+0000.json` | **ASSETS DELIVERED** chrome / firefox / firefox-nozstd 3/3; red cases 156 (K1-6 repaired in `74489aa0`) |
| host entry `m3-host-entry/runs/2026-10-15T203752Z.json` | **HOST_ENTRY LANDS**, `problems=[]`; red cases 27, plus the baseline green |
| same second `m3-same-second/runs/2026-10-15T204406+0000.json` | **SAME-SECOND SAVES KEPT** 3/3 × 4, `red-clauses-per-run=[]`; red cases 70 |
| autosave `m3-autosave/runs/2026-10-15T205624+0000.json` | **AUTOSAVE HOLDS** (its second counted run; the first was 0.2.23's); red cases 78, `0 not red or missing` |
| new-document `new-document/runs/2026-10-15T221539Z.json` | **NEW-DOCUMENT WORKS**, EN/TW × chrome/firefox PASS; red cases 39 RED, plus the baseline green |

**About the red-case counts:**
- They were re-read from each runner's full `--red-cases` output. The reader script saves only the last five lines.
- Every `--red-cases` exited 0.
- Against 0.2.12, locks has 2 more and host entry 4 more. Both runners gained them in `65e90f62` (SPEC-M3-autosave §9.4). The other counts equal 0.2.12's.

**About the 14:** the reader prints `no-passing-run notes: 14 (13 expected, all B3x)`. The 14th match is the reader's own `expected:` header line in the same file, which contains the string it counts. The notes are 13, all B3x. 0.2.23's file counts the same way: 21 = 7 P + 13 B3x + 1 header. This is a counting artifact of `read-0.2.24.sh`, not a deviation. The script is not repaired here.

## §17.4: the R arms' positive control, by hand (`runs-0.2.24/r-arm-spans.txt`)

On v20 the C branch (`score_noop`) has no positive control. §17.4 therefore asks the reader to confirm, for every counted Rbs/Rdel run, one busy span of at least 2,000 ms whose `rev` is equal at its start and end.

The spans were printed from the raw timelines by `runs-0.2.24/r_arm_spans.py`. Its span function is `witness-c-0.2.23/read_witness.py`'s, copied unchanged.

| arm | browser | round 1 | round 2 | round 3 |
|---|---|---|---|---|
| Rbs | chrome | 2,261 ms, rev 3→3 | 2,260, 3→3 | 2,261, 3→3 |
| Rdel | chrome | 2,262, 3→3 | 2,262, 3→3 | 2,261, 3→3 |
| Rbs | firefox | 2,258, 3→3 | 2,257, 3→3 | 2,257, 3→3 |
| Rdel | firefox | 2,258, 3→3 | 2,258, 3→3 | 2,257, 3→3 |

- **12 of 12 runs carry the span**: 2,257–2,262 ms, `rev` equal, `gen 1→1`, ending in `ready`, one span per run. Rbs and Rdel read **PASS**, not NOT_ESTABLISHED.
- **Contrast**: the 12 K-arm runs in the same report have no busy span of at least 1 s.
- **Control**: the same script on the §17.4 witness reproduces its 2,257–2,261 ms on the four R runs. The script can print both a span and the absence of one.
- **Recorded**: the round-3 Firefox Rbs span starts at 39.5 s, against about 9.4 s in the other Rbs runs. The witness's Firefox B3x run shows the same offset (39.4 s). It is not read further here; the span itself is as in every other run.

## Merge (`release-0.2.24/merge-m2/judge-output.txt`)

`judge_counted_m2.py --profile e2-editor-v20`: **`VERDICT PASS`**. Per clause, in both browsers:

- M2-1: 60/60.
- M2-3: 15/15.
- Barrier: 3/3.
- M2-2: 60 completions.
  - Runner median 123.1 ms (chrome) and 127.45 ms (firefox).
  - Engine median 30 ms.
  - Max under 1000 ms.
- Control: 78 pairs, differ 0.
- M2-1b: 20/20.
- M2-4: 105 presses, slow 0.
- Red: C01–C03 on v8, each placed, refused and reopened.
- M2-0: PASS.

Identity: every report has runner `f900820773990725`, the page `901dd6a6…` (the red arm `daa868d3…`), and wasm `313b08d5cb085897`.

This is the clause set that read `FAIL` on 0.2.23 (finding 145), and that the N1 run on dist read PASS before the chain (`findings/evidence/145/n1/`). It now reads PASS on the counted desk, served by the host, in both browsers.

## C2 by J-b.2 (`release-0.2.24/c2/r1–r3/`)

| run | `judge_c2.py` | `judge_p2.py` | Chrome gap-80 on-screen max / median | Firefox gap-80 on-screen max / median |
|---|---|---|---|---|
| r1 | PASS: both browsers, every cell | PASS | 50.0 / 33.8 | 57.9 / 30.0 |
| r2 | PASS | PASS | 66.0 / 35.4 | 89.3 / 30.1 |
| r3 | PASS | PASS | 44.4 / 30.6 | **106.9** / 36.9 |

**J-b.2's table, row 1: 3 × PASS → C2 reads PASS.**

- **The rate (J-b.2 item 5): 0 of 3 runs over the gate, and none at 135's shape.**
  - No Chrome gap-80 key reached 100 ms.
  - The three Chrome maxima are 50.0, 66.0 and 44.4 ms.
- **Recorded, not a verdict:** the Firefox gap-80 cell read a key of at least 100 ms, which J-b.1's record says no non-Chrome cell had done.
  - **The keys.** r3 key 3 read 106.9 ms on screen (commit 44.8). r3 key 4 read 91.5 (commit 63.4), and r2 key 4 read 89.3 (commit 59.1). These are early keys, not key 10.
  - **The first-five / last-five median commit** (the judge's `RECORD` line):
    - 0.2.24's three runs: 36.8 / 19.9, 43.7 / 20.8 and 52.6 / 23.3.
    - 0.2.23's three runs: 41.1 / 25.7, 23.9 / 20.8 and 33.0 / 20.9.
    - The eight `RECORD` lines before v20 (in `c-prime/c2/`, `132/guard/c2/`, `134/guard/c2/` and `136/guard-r2/c2/`): 21.3–27.4 for the first five keys.
  - **What it shows.** On engine v20 pages, Firefox's first keys commit slower than on the pre-v20 record, in 5 of 6 runs. One run's early key crossed 100 ms on screen.
  - **The gate is unchanged:** every value is under 150 ms. J-b.1's sentence "no other C2 cell has ever read ≥ 100 ms" was true when written. After this count it is no longer true of the Firefox gap-80 cell.
  - **The cause is not located.** No measurement here separates the engine, the page and the desk.

## Product-path net (`release-0.2.24/product-path/`)

The net ran twelve reports: v8 (the page repointed, `daa868d3…`) and v20 (dist as served, `901dd6a6…`), interleaved, 3 rounds × Chrome/Firefox, 22:18–23:39Z.

**The reader was made red once on scratch copies** before its verdict was read (`judge-red-offline.txt`):

| Case | Edit on the scratch copy | Result |
|---|---|---|
| unchanged copy | none | reproduces the committed `SUMMARY` |
| red 1 | chrome v20 r2 `product-save-button-writes-a-real-odt` flipped to FAIL | **P3: MISS** (`RED: ('chrome', 'product-save-button-writes-a-real-odt', '3 PASS', '2 PASS, 1 FAIL')`) |
| red 2 | firefox v20 r1 entrypoint set to 0.2.23's page `ccb67a52…` | **P2: MISS** |

**The watch item (carried):** Chrome `clear-format-removes-every-inline-format` read NE in 1 of the 6 Chrome runs (v8 r1). The threshold is at least 2, so the verdict is read.

`judge-output.txt`: **`SUMMARY  P1: HIT  P2: HIT  P3: HIT (red cells 0)  P4: descriptive (differing cells 1)`**. This covers 84 cells, 0 of them red under §23 and row 1′. Row 1′'s window at read time is chrome 0 of 36 v8 records NE, firefox 3 of 36.

P4 found one differing cell: Chrome `clear-format-removes-every-inline-format`, v8 2 PASS + 1 NE against v20 3 PASS. It is NE-only, the kind PREDICTION.md's P4 names.

**The descriptive comparison against 0.2.12's v19 reports** (`v20-vs-0.2.12-v19.txt`, by `v20_vs_0212_v19.py`, the shape of `../release-0.2.12/product-path/old-vs-new-v19.txt`):

- Chrome: 42 cells, 0 differ.
- Firefox: 42 cells, 1 differs. In it, 0.2.12's v19 passed every round and this v20 did not: `recovery-returns-what-the-product-promised`, v19 3 PASS against v20 2 PASS + 1 NE.

**0.2.23's PREDICTION predicted no such cell, and this count misses that prediction by one NE cell.** What the cell shows:

- The NE is round 3 in **both arms**, v8 and v20, with `finding038Reproduced: false` on both. The reason the check gives is "NEITHER inducer put the session into a state where the product offers its recovery button".
- So the inducer did not reproduce finding 038 in that round, on either engine. 0.2.23's v8 arm had the same NE once (r1).
- It is row 1′'s NE kind, not a FAIL. It is on the control engine too, so nothing in it points at v20 or the page.
- The same comparison on 0.2.23's committed v20 reports reads 0 such cells. Its one differing cell is Firefox clear-format, NE-only.

## Verdict

**The count holds on host 0.2.24.** Every row J-a.2 names for "the count holds" is met:

- `DONE`;
- every counted runner exit 0 with a green verdict;
- every red-case set all red;
- identity equal;
- the product-path reader made red once, then `SUMMARY` P1–P3 HIT;
- C2 PASS by J-b.2;
- §17.4's spans present on all 12 R runs.

By their own criteria:

- **0.2.24 becomes the nominal shipped version**, replacing 0.2.12. The batch 0.2.13–0.2.24 is counted as SPEC-M3-link-batch §7 lists it, plus finding 145.
- **Finding 145's fix is counted.** U1/U2 and N1 were done before the chain. The merge clause set that went red on 0.2.23 is now PASS in both browsers, served by the host.
  - Still not measured: **the user path.** The owner's hand test (handoff 10-15c "For the owner" 3) has not been done.
- **B3x / A1-5 stay unguarded on v20+**, as registered in §17.3. No counted arm induces a refusal.

**Limits carried:**

- the C branch's positive control is the hand reading above (§17.4), not code;
- the Firefox early-key latency above is recorded and not attributed;
- the descriptive miss above is an inducer NE;
- 135's rate is unchanged as a measurement: 0 of 3 here.

## Static

The chain ran its P6 before `IDENTITY-START`: 134 unit tests OK and `make test-e2-c-static` exit 0 (`wasm_sdk_probe/build/m3-count-20261015T164456Z/preflight-p6-*.txt`). Since then the tree has changed only by the 10-15c addendum, and now by this reading's evidence files. No tool, page or judge changed, so the static gate was not run again.

## §34.4

This reading repaired nothing:

- **because of execution: 0**;
- **because of review: 0**.

Running total since 10-14b: **execution 9, review 18**, unchanged. `r_arm_spans.py` and `v20_vs_0212_v19.py` print facts for a hand reading and judge nothing. They are reading aids in the shape of `witness-c-0.2.23/read_witness.py` and 0.2.12's ad-hoc comparison, not checks.
