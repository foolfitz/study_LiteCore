# The count on host 0.2.26 (engine v21, item 1 only; shell v74; finding 154's host rule) — result (2026-10-19)

Reading table:
- ruling **J-a.2** (`handoff/RULING-2026-10-15-pre-binding.md`);
- C2 by **J-b.2**;
- the R arms by **SPEC-M3-link-batch §17.4**;
- the product-path verdict by its `SUMMARY` line (§34.7).

This is SPEC-M3-link-batch-v21's criterion **K** (§1, §11.1 K, §12.6). Chain and reader: `runs-0.2.26/` (`chain-0.2.26.sh`, `read-0.2.26.sh`, README). The count before this one, 0.2.24's, held (`RESULT-0.2.24.md`). The main session read this one in the session that prepared it, at the owner's request.

## What was counted

| What | Value |
|---|---|
| Host | `litecore` **0.2.26**, `3c01876`, clean (`dirty[]`), installed with `ddev occ upgrade` |
| Engine package | buildId `f5f0df762e1855f2` (engine v21, wasm `db3408f55316bf67`). It is 0.2.25's package byte for byte, archived read-only in `wasm_sdk_probe/build/archive/host-0.2.25-engine-f5f0df762e1855f2/` |
| Page | `605cf24b…` (v74 cutover). dist = web = archive = served, at `IDENTITY-START` and at `IDENTITY-END` |
| Shell | v74 `27f33a13…` (`4628c9d3`) |
| Tree at `START` | `9c8d83cc` |
| Runners (sha256[:16], from `START`) | production UI `8f664a2f8704658f`, autosave `ebeb0964da71e1aa`, new-document `bd28e29d2547c2ae`, product path `3e824c9710f5f21f`, merge `aaee0cda5be5ad84`, C2 view `1412e4c863de6fcb`, probe `dbad93c0dcf27fbf` |
| What the count carries | everything since 0.2.24, i.e. the v21 batch as shipped: item 1 (finding 142), the page fixes for findings 150 and 151 (part), item 2 withheld behind the shell, ABI 5, finding 154's host rule; plus page honesty §7.14 (the check) |

The production-UI, autosave and new-document runners differ from 0.2.24's by the 0.2.26 re-pin (`a643de39`). Page honesty also differs by §7.14 (`94b4913e`). The merge runner differs by `BINDING` v21 (`7ea8038f`). The product path differs by one mutation's `find` (`712f955a`).

## The chain (`runs-0.2.26/chain-20261018T160539Z.out`)

- **Started by the owner** at 2026-10-18T16:06:36Z (00:06:36 Asia/Taipei).
  - The agreed window was 「2026-10-19 00:10-09:30, owner 00:05; B3x withdrawn as 0.2.24」. The chain started four minutes before the window string's first time, and the owner wrote it at that moment.
  - The two expired runner locks (4882, 4886) had been deleted by the owner. P0–P6 read ok.
- **`DONE`** at 2026-10-18T23:55:16Z (07:55:16 Asia/Taipei): **7 h 48 m 40 s**.
- **`IDENTITY-END` equals `IDENTITY-START`** field for field: host `3c01876` `dirty[]` 0.2.26, buildId `f5f0df762e1855f2`, dist / web / archive / host-served page `605cf24b3dff5a2d`.
- **The desk:** 47 `DESK` lines, all recorded, none gated (J-a.3).
  - Load 0.12–2.51 (0.95 at `START`, 0.87 at `END`).
  - `ours` 0 and Chrome browsers 0 on every line.
  - The owner's snap Firefox: 1 process on some lines, 0 on others.
  - kwallet unlocked; host login `rc=0` on every line.
- **The eight shakedowns were clean** (16:06–17:23Z), so the STOP rule did not fire:
  - page honesty `clean` (with §7.14; without it, the first shakedown would have stopped the chain: `../m3-page-honesty/fix-7.14/`);
  - locks, versions, assets, same second `clean`;
  - host entry `LANDS`;
  - autosave `clean`;
  - new-document `WORKS`.

### J-a.2's row

`DONE`; every counted runner exit 0 with its green verdict line; red cases all red; identity equal → **"The count holds"**, subject to the hand readings below. The table also covers the exits of 1 the chain prints, as in 0.2.24:
- the six Firefox product-path reports exit 1 on the known red `an-inline-format-reaches-a-selection` (3 of 3 rounds, both arms); J-a.2's last row: the `SUMMARY` line decides;
- `merge pair-chrome` / `pair-firefox` exit 1, as in 0.2.23's and 0.2.24's chains. The merge judge reads the comparison: `control PASS, pairs 78, differ 0` in both browsers.

## The counted reports

| Report | Result |
|---|---|
| production UI `runs-0.2.26/counted-KR-x3.json` | **Kdel, Kbs, Rbs, Rdel 3/3 each in both browsers (24/24)** |
| production UI `runs-0.2.26/counted-ctl-S-P.json` | Bctl, S, P 1/1 each, both browsers (6/6) |
| production UI B3x | **not run**: withdrawn since the 0.2.23 count (SPEC-M3-link-batch §17.3); engine v21 also carries C |
| production UI, pooled mutations | **`red cases: 28/28`**, 13 `no passing B3x run` notes (all A1-5), exit 1 by the runner's every-mutation rule, as expected (`runs-0.2.26/red-cases-on-counted-pooled.txt`). The reader now reads 13, not 14 |
| page honesty `m3-page-honesty/runs/2026-10-18T175135+0000.json` | **PAGE HONEST**, every cell 3/3; red cases **158** (154 + §7.14's two cases × 2 browsers), `0 not red or missing` |
| locks `m3-locks/runs/2026-10-18T185619+0000.json` | **LOCKS LAND**, every cell full; red cases 101 |
| versions `m3-versions/runs/2026-10-18T194537+0000.json` | **VERSIONS CORRECT** 3/3, 3/3; red cases 68 |
| assets `m3-assets/runs/2026-10-18T195011+0000.json` | **ASSETS DELIVERED** chrome / firefox / firefox-nozstd 3/3; red cases 156 |
| host entry `m3-host-entry/runs/2026-10-18T195440Z.json` | **HOST_ENTRY LANDS**, `problems=[]`; red cases 27 |
| same second `m3-same-second/runs/2026-10-18T200053+0000.json` | **SAME-SECOND SAVES KEPT** 3/3 × 4, `red-clauses-per-run=[]`; red cases 70 |
| autosave `m3-autosave/runs/2026-10-18T201302+0000.json` | **AUTOSAVE HOLDS**; red cases 78, `0 not red or missing` |
| new-document `new-document/runs/2026-10-18T213054Z.json` | **NEW-DOCUMENT WORKS**, EN/TW × chrome/firefox PASS; red cases 39 RED, plus the baseline green |

The red-case counts were re-read from each runner's full `--red-cases` output; every one exited 0. Apart from page honesty's +4, they equal 0.2.24's.

## §17.4: the R arms' positive control, by hand (`runs-0.2.26/r-arm-spans.txt`)

The spans were printed by `runs-0.2.24/r_arm_spans.py`, unchanged (`7b3ae95d…`).

| arm | browser | round 1 | round 2 | round 3 |
|---|---|---|---|---|
| Rbs | chrome | 2,262 ms, rev 3→3 | 2,260, 3→3 | 2,260, 3→3 |
| Rdel | chrome | 2,262, 3→3 | 2,262, 3→3 | 2,263, 3→3 |
| Rbs | firefox | 2,259, 3→3 | 2,259, 3→3 | 2,258, 3→3 |
| Rdel | firefox | 2,258, 3→3 | 2,260, 3→3 | 2,258, 3→3 |

- **12 of 12 runs carry the span**: 2,258–2,263 ms, `rev` equal, `gen 1→1`, ending in `ready`, one span per run. Rbs and Rdel read **PASS**.
- **Contrast:** the 12 K-arm runs in the same report have no busy span of at least 1 s.
- **Control:** the same script on the §17.4 witness reproduces its 2,257–2,261 ms on the four R runs.
- **Recorded:** the round-2 Firefox Rbs span starts at 39.5 s, against about 9.1–9.3 s in the other Rbs runs. 0.2.24 recorded the same offset once (its round 3). The span itself is as in every other run.

## Merge (`release-0.2.26/merge-m2/judge-output.txt`)

`judge_counted_m2.py --profile e2-editor-v21`: **`VERDICT PASS`**. Keyed on the v21 wasm: C declared, so nothing-selected expects `verified-boundary-noop`.

Per clause, in both browsers:
- M2-1 60/60, M2-3 15/15, barrier 3/3.
- M2-2: 60 completions. Runner median 124.35 ms (chrome) / 128.2 ms (firefox); engine median 30 ms; every value under 1000 ms.
- Control: 78 pairs, differ 0.
- M2-1b: 20/20.
- M2-4: 105 presses, slow 0.
- Red: C01–C03 on v8, each placed, refused and reopened.
- M2-0: PASS.

Identity: every report has runner `aaee0cda5be5ad84` and page `605cf24b…` (the red arm `ea3b6bad…`), with wasm `db3408f55316bf67`. **This is the merge runner's first count on v21.** Its first-contact shakedown (`../link-batch-v21/first-contact/`) had predicted it.

## C2 by J-b.2 (`release-0.2.26/c2/r1–r3/`)

| run | `judge_c2.py` | `judge_p2.py` | Chrome gap-80 on-screen max / median | Firefox gap-80 on-screen max / median |
|---|---|---|---|---|
| r1 | PASS: both browsers, every cell | PASS | 42.3 / 26.3 | 51.8 / 27.0 |
| r2 | PASS | PASS | 46.1 / 28.1 | 48.4 / 27.6 |
| r3 | PASS | PASS | 42.0 / 26.4 | 50.5 / 28.9 |

**J-b.2's table, row 1: 3 × PASS → C2 reads PASS.** The rate (J-b.2 item 5): 0 of 3 runs over the gate, none at 135's shape.

**Recorded, not attributed:** 0.2.24 recorded slower early keys in the Firefox gap-80 cell (first-five median commit 36.8 / 43.7 / 52.6 ms; one key at 106.9 ms on screen). Here they read **25.7 / 22.2 / 25.6** (last five 20.1 / 19.9 / 20.0), and the on-screen max is 51.8. That is back inside the pre-v20 record (21.3–27.4). No measurement here separates the engine, the page and the desk, so the change is not attributed.

## Product-path net (`release-0.2.26/product-path/`)

The net ran twelve reports, interleaved, 3 rounds × Chrome/Firefox, 21:33–22:51Z:
- v8, the page repointed (`ea3b6bad…`);
- v21, dist as served (`605cf24b…`).

**The reader was made red once on scratch copies** before its verdict was read (`judge-red-offline.txt`):

| Case | Edit on the scratch copy | Result |
|---|---|---|
| unchanged copy | none | reproduces the committed `SUMMARY` |
| red 1 | chrome v21 r2 `product-save-button-writes-a-real-odt` flipped to FAIL | **P3: MISS** (`RED: ('chrome', 'product-save-button-writes-a-real-odt', '3 PASS', '2 PASS, 1 FAIL')`) |
| red 2 | firefox v21 r1 entrypoint set to 0.2.24's page `901dd6a6…` | **P2: MISS** |

**The watch item (carried):** Chrome `clear-format-removes-every-inline-format` read NE in 0 of the 6 Chrome runs (threshold 2), so the verdict is read.

`judge-output.txt`: **`SUMMARY  P1: HIT  P2: HIT  P3: HIT (red cells 0)  P4: descriptive (differing cells 0)`**. Row 1′'s window at read time: chrome 0 of 39 v8 records NE, firefox 4 of 39. PREDICTION.md's P1–P4 all hold.

**The descriptive comparison against 0.2.24's v20 reports** (`v21-vs-0.2.24-v20.txt`, by `v21_vs_0224_v20.py`, 0.2.24's script with the arms moved):
- Chrome: 42 cells, 0 differ.
- Firefox: 42 cells, 1 differs. It went the other way: `recovery-returns-what-the-product-promised`, v20 2 PASS + 1 NE (0.2.24's inducer NE) against v21 3 PASS.
- **Cells where 0.2.24's v20 passed every round and v21 did not: 0.**

## Verdict

**The count holds on host 0.2.26.** Every row J-a.2 names for "the count holds" is met:
- `DONE`;
- every counted runner exit 0 with a green verdict;
- every red-case set all red;
- identity equal;
- the product-path reader made red once, then `SUMMARY` P1–P3 HIT;
- C2 PASS by J-b.2;
- §17.4's spans present on all 12 R runs.

By SPEC-M3-link-batch-v21 §11.1 K and the criteria above:
- **0.2.26 becomes the nominal shipped version**, replacing 0.2.24. v21 (item 1) is counted, with findings 150 and 151 (part) in the page and finding 154's host rule.
- **Not measured, carried:**
  - **the user path:** the owner's hand test of 0.2.26 (Ctrl/Cmd+Home/End on a real document, and that no Markdown box appears) has not been done;
  - item 2 stays withheld (finding 153), with L-md-sdk-callable.
- **B3x / A1-5 stay unguarded on v20+**, as registered in §17.3.

**Limits carried:**
- the C branch's positive control is the hand reading above (§17.4), not code;
- L-142-readback-overtaken, -steps, -sdk-callable;
- L-md-sdk-callable;
- L-154-diag-second-click;
- the Firefox early-key change above is recorded and not attributed.

## Static

The chain ran its P6 before `IDENTITY-START`: 134 unit tests OK and `make test-e2-c-static` exit 0 (`wasm_sdk_probe/build/m3-count-20261018T160539Z/preflight-p6-*.txt`). Since then the tree has changed only by this reading's evidence files and two reading aids. No tool, page or judge changed, so the static gate was not run again.

## §34.4

This reading repaired nothing:
- **because of execution: 0**;
- **because of review: 0**.

Running total since 10-14b: **execution 29, review 18**, unchanged. `r_arm_spans.py` (0.2.24's, unchanged) and `v21_vs_0224_v20.py` print facts for a hand reading and judge nothing.
