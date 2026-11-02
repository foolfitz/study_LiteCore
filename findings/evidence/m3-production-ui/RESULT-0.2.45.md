# The count on host 0.2.45 (engine v29, shell generation 83) — result (2026-11-02)

**K holds.** `findings/evidence/k-0.2.45/read_k.py` reads K1-K8 from the chain's products: `K_HOLDS` (`release-0.2.45/k-verdict.json`), its 20 mutations all red (`release-0.2.45/k-verdict-self-test.json`). The nominal shipped host moves from 0.2.26 to **0.2.45**.

Spec `specs/SPEC-M3-K-0.2.45.md`, on the protocol of `SPEC-M3-K-0.2.44`. This is that protocol's first real run: K 0.2.44 never got past its shakedowns. Chain and reader: `runs-0.2.45/`.

## What was counted

| What | Value |
|---|---|
| Host | `litecore` **0.2.45**, `eeac22c`, clean (`dirty[]`), on the own stack (`SPEC-M3-own-stack`) |
| Engine package | buildId `623f51d295ff6030`, archive `build/archive/host-0.2.45-engine-623f51d295ff6030` |
| Writer engine | `e2-editor-v29`, wasm `e61e5890…` |
| Page, HTML | `022d0cd0…`, `ca58f40f…`; dist = web = archive = served at `IDENTITY-START` and `IDENTITY-END` |
| Shell | generation 83, `607b280d…` |
| Tree at `START` | `fe6c3cc7d` |
| What the count carries | everything since 0.2.26: engines v22-v29, shell generations 75-83, hosts 0.2.27-0.2.45, the spreadsheet viewer and cell editor |

## The chain (`runs-0.2.45/chain-20261101T173658Z.out`)

- **Started** 2026-11-01T17:38:05Z (01:38 Asia/Taipei) on the owner's word, quoted in `--owner-window`: 「手測完成，都符合預期／請繼續跑」. P0-P6 ok.
- **`DONE`** 2026-11-02T00:58:17Z (08:58 Asia/Taipei): **7 h 20 m**.
- **`IDENTITY-END` equals `IDENTITY-START`** field for field.
- **The desk:** 39 `DESK` lines. Load 0.32-4.03. `ours` 0 and Chrome browsers 0 on every line; kwallet unlocked and host login `rc=0` on every line.
- **The eight shakedowns were clean**, so the STOP rule did not fire.
- **C2's desk gate** read clean before all three rounds, so no round was refused.

## K1-K8

| Item | Reading | Result |
|---|---|---|
| K1 | `DONE`, identity equal, P0-P6 | holds |
| K2 | production UI, both counted reports all pass, documents clean; red cases 28/28, 13 `no passing B3x run` notes | holds |
| K3 | `PAGE HONEST` 90 of 90 runs; `LOCKS LAND` 52; `VERSIONS CORRECT` 6; `ASSETS DELIVERED` 9; `SAME-SECOND SAVES KEPT` 12; `HOST_ENTRY LANDS`; each `--red-cases` exit 0 | holds |
| K4 | `AUTOSAVE HOLDS`, every cell full, `as5` included; `NEW-DOCUMENT WORKS`; red cases exit 0 | holds |
| K5 | `K_MERGE_COUNTED`; `judge_k_0245_merge.py --uncounted` exit 4, `VERDICT PASS`, red PASS on both browsers, one runner, keying `ordered-abi6` | holds |
| K6 | C2 three rounds: `judge_c2` and `judge_p2` PASS, both browsers, every cell | holds |
| K7 | `K_PATH_HOLDS`, 6 reports, special cells by their rows | holds |
| K8 | page gate `LEGACY_V8_CONTROL_REFUSED`, Enter `V24_ENTER_HOLDS` | holds |

## Numbers worth keeping

C2, median ms, three rounds:

| | Chrome | Firefox | gate |
|---|---|---|---|
| `boundaries` commit | 11.0, 9.2, **14.3** | 10.4, 9.5, 8.9 | <= 16 |
| owner document, gap 80, on screen | 17.5, 16.1, 18.2 | 11.6, 11.8, 10.8 | < 70 / < 90 |

**The `boundaries` commit gate decided K6.** Set at 10 on v20, re-set to 16 by the owner on 2026-11-02 before this run, from T1's 8.7-12.3 (spec v29 append 8). Under 10, rounds 1 and 3 on Chrome would read FAIL. 14.3 is 2 ms under the new gate: this is the cell to watch.

## Two exit codes that are not reds

- **Product path exit 1, all six.** The runner's own verdict. K reads its own table (SPEC-M3-K-0.2.44 section 3), which holds.
- **`pair-chrome`, `pair-firefox` exit 1.** One pair each, C03, one key, `toastsAtEnd`: 「已存出 14.3 KB」 against 「已存出 14.2 KB」. The judge reads pairs equal up to the KB figure by fable's ruling of 2026-10-08 (spec paragraph-merge 34.1 (b)): `pairs 78, differ 0`, both browsers. Checked by hand, the figures are as stated.

## Named limits, carried

- **L-K-0244-no-engine-refusal-exercised**: no cell reached a v29 engine refusal, `reopened` documents 0 of 0.
- **L-v29-small-client-contention**: C2 measures a 12-core desktop.
- Merge's red arm is read from the 0.2.26 count, not re-run (K ruling item 1).
- `report.v23-four-arms/` of the six product-path runs (about 31 MB, mostly `.odt`) is on this disk, not in git; the reader does not read it.
