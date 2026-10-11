# Second round — the early verifier reset: when, and what makes it miss the page (2026-10-11)

Prediction and reading rule: `PREDICTION.md`, committed before any counted launch (`5ea259af`; the schedule-flag
fix `3f7fc9ce`, see note at the end). Instrument `probe_early_reset.py`, schedule `run_round.py`, reader+rule
`summarize.py` (its `SUMMARY` lines are the reading). Reports `e{1,2,3,5,6}-NN.json`, log `runs.log`,
machine summary `summary.json`, detector control `control-70s.json`. Chrome 151.0.7922.169, 64 launches one at a
time, 2026-10-11T13:14:56Z → 13:35:19Z, nothing else running.

## What a "reset" is here

Read directly from each launch's `--log-net-log`: a reset = a cluster of `SOCKET_POOL_CLOSING_SOCKET` events with
reason **`"Cert verifier changed"`** within 50 ms (the socket-pool side of a verifier-change notification; source
path in `PREDICTION.md`). For each one the report records which HTTP/2 sessions went away within 1 s (by host, so
"took the origin's session" is read, not inferred) and what the browser had just fetched. A request-level **hit** =
a `Network.loadingFailed net::ERR_CERT_VERIFIER_CHANGED` on one of the page's own fetches between loop start and stop
(the first round's detector; the two cross-check). The 70 s control (`control-70s.json`) catches the component-install
reset at 61.87 s — the net-log detector sees the reset the first round could only infer; the CDP detector's control
is the deliberate failing fetch logged in every launch (all 64 recorded `net::ERR_CONNECTION_REFUSED`).

## Results

All 64 launches valid (P0: ≥ 500 fetches ok — min 1,659; control failure recorded; net log complete; ≥ 1 origin
HTTP/2 session). There are **two** reset events per launch, not one:

- **R_a**, early, t ≈ 0.17–0.56 s (right after the network-time query completes).
- **R_b**, mid, t ≈ 2.3 s (min 2.293, max 2.421 across all arms; it is **this** one that takes the origin's HTTP/2
  session in a burst — the Files-burst shape). In one E1 launch R_b landed at 0.63 s, so the two are not cleanly
  separated by time; they are separated by cause (below).

| arm | n | launch | ≥1 reset | early (<1 s) | mid (1–6 s) | late (≥6 s) | mid took origin session | resets at/after first request | page-fetch hits | time query | seed | update check |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 20 | runner flags | 20/20 | 19/20 | 20/20 | 0/20 | 19/20 | 20/20 | 0/20 | 20/20 | 20/20 | 20/20 |
| E2 | 8 | + `--disable-component-update` | 8/8 | 8/8 | 8/8 | 0/8 | 8/8 | 8/8 | 0/8 | 8/8 | 8/8 | 8/8 |
| E3 | 12 | first request only at 5 s | 12/12 | 12/12 | 11/12 | 0/12 | — | **0/12** | **0/12** | 12/12 | 12/12 | 12/12 |
| E5 | 12 | + `--disable-features=CertVerificationNetworkTime` | 12/12 | **0/12** | 12/12 | 0/12 | 12/12 | 12/12 | 1/12 | 12/12 | 12/12 | 12/12 |
| E6 | 12 | + `--disable-background-networking` | 12/12 | 12/12 | **0/12** | 0/12 | — | 4/12 | 0/12 | 12/12 | **0/12** | **0/12** |

Across all resets: E1 **59/59 took the origin session**; E2 22/23; **E3 0/34** (the page has no origin session yet
when the resets fire); E5 12/12; E6 2/12.

## Reading by PREDICTION.md (the `SUMMARY` lines of `summarize.py`)

- **V1 holds**: E1 has the mid reset in 19/20 and it takes the origin's HTTP/2 session in 19/20 (the 20th's R_b
  landed early, at 0.63 s, and also took it); no late reset. The phenomenon is established under the runner's flags.
- **V2 holds**: E2 keeps the mid reset 8/8 — `--disable-component-update` is not a fix (as the first round already
  showed for the install, now shown for R_b too).
- **V3a holds / V3b holds**: E3 still has both resets (time-triggered, not request-triggered), but **0 of 12 occur at
  or after the first request** when that request is delayed to 5 s, and **0 hits** — because the resets fire before
  the origin session exists (0/34 took it).
- **V4a holds / V4b holds**: with `CertVerificationNetworkTime` disabled there is **no early reset** (0/12) — so
  **R_a is the network-time push** to the verifier (`CertVerifierServiceTimeUpdater`, enabled by default). **R_b
  persists** (12/12) and is therefore **not** a network-time push; it even produced the round's one page-fetch hit
  (e5-01, a `Fetch` at 2.305 s).
- **V5**: `--disable-background-networking` removes the variations seed and the update check (0/12 each) but **not**
  the time query (12/12) or the GCM check-in. With it, **R_b is gone** (0/12 mid) — so R_b rides on the
  background-networking family, not component update and not network time. R_a remains (12/12) and still took the
  origin session in 2/12 (e6-10, e6-11).

**Verdict (D2):** no single launch flag removes the reset that endangers the page. Each flag removes one of the two
and neither reliably spares the origin's session (E5 keeps R_b, which hit a page fetch 1/12; E6 keeps R_a, which took
the origin 2/12). All resets are **early and time-triggered** (max 2.421 s, none late); **delaying the page's first
request past them avoids every one** — E3 is the clean arm (0/12 at/after the first request, 0 hits). So the fix is a
**warm-up wait**, not a flag.

## Recommendation

**Change `wasm_sdk_probe/tools/run_browser_probe.py` (`ChromeSession.__init__`): add a warm-up wait of ~5 s after the
browser is up and CDP is ready, before control returns (i.e. before the first navigation).** 5 s is ~2.6 s of margin
over the 2.421 s maximum observed here. Do **not** use the flags as the fix: each removes only one of the two resets,
and the residual one still swept the origin session in this round. (Both flags together would plausibly zero
everything, but the combined arm was not measured and cannot be recommended without a confirming run — and it is a
heavier behaviour change to a launcher shared by many runners than a wait, which changes only timing.)

- **Chain prediction for the re-run**: with the wait, the locks shakedown's 12 Chrome arms show **0
  `net::ERR_CERT_VERIFIER_CHANGED`** and the Files list renders every time (the K9′ arm included). The locks runner
  opens a fresh Chrome per arm, logs in, then opens Files right away (`check_m3_locks.py` `run_arm`), so today the
  login/Files burst at ~0.2–3 s overlaps R_a/R_b; the wait moves it past both.
- **Residual risk to state when applying it**: R_b's time depends on the latency of Chrome's background fetches to
  Google; a materially slower network could push it past 5 s. It was ≤ 2.421 s on this machine/network. If a red
  recurs despite the wait, widen it or add `--disable-background-networking` as well (it removes R_b causally).
- **Anything smarter than a fixed wait** (e.g. poll until the origin's HTTP/2 session has been stable for N ms) is a
  **new mechanism**; per CLAUDE.md §4 that should go to the owner, not be built in this diagnosis.

### §34 (`specs/SPEC-M3-paragraph-merge.md`) framing

This is a check-machinery change. **Witness** = the locks shakedown report
(`../../../m3-locks/shakedown/2026-10-11T110140+0000.json`, the honest run whose K9′ Chrome red stopped the count and
was attributable to this reset) plus this round's reports. **Ledger: 因執行而修 6 → 7, 因審核而修 stays 5.** Note the
collision flagged in `handoff/HANDOFF-2026-10-11e…md` Open 1: §17.21 already reserves "6 → 7 一次" for a future runner
opening; whichever lands second is 8. Settling the notation belongs in the spec append, which is outside this
diagnosis's scope.

### What pins `run_browser_probe.py`'s bytes (read-only census)

- **No absolute pin and no static test** names it. `wasm_sdk_probe/tests/` has nothing referencing `run_browser_probe`
  or `ChromeSession`; the six M3 runners pin themselves and the page/host/shell, not this helper.
- Its sha256 `663b2ffab8174afc070401a15afac18c9ba12950b6a39f146b331ceeab7d8e3e` (last changed `c4627426`, 2026-08-27) is
  recorded as a `moduleSha256` entry in `findings/evidence/m3-install/equivalence.json` and in the m3-install / 089
  evidence. `check_m3_install_elsewhere.py` compares those module hashes **between its equivalence check and its
  window** (I3-8, `module_shas()`/`tree_binding()`) — a within-window consistency check, not an absolute pin, and the
  tree binding checks `wasm_sdk_probe/` is clean and unchanged across the run. So editing this file changes that hash;
  the install-elsewhere check would need its equivalence recomputed on the new tree (true of any edit, wait or flag).
- `specs/SPEC-M3-production-ui.md` §17.3 is the precedent for shared-helper edits: `ChromeSession` is subclassed by
  `EventChrome` (`probe_m3_gate0_coep.py:179`) and `LockChrome(EventChrome)` (`check_m3_locks.py:98`), and ~80 tools
  import `run_browser_probe`; a change there is counted once (因執行而修) but every importer's pin is blind to it, so a
  0-difference reproduction across importers is the precedent if the owner wants that rigor. The six M3 counting
  runners all route their Chrome through `ChromeSession`, so the wait reaches all of them (which is the intent).

## Not established

- The exact caller of R_b (the net log shows a verifier-change notification and that it rides on the
  background-networking family — it vanishes when the variations seed and update check are suppressed — but not which
  API call issued the `UpdateVerifierServices`). The recommendation does not depend on it.
- Whether the two flags together zero all resets (not measured as a combined arm).
- The locks arm's own failures' time since launch (its report has no timestamps on `loadingFailed`), so the match to
  R_b remains a match in cause and shape, timed here, not timed there.
- Rates on another machine/network: all of this is one host, one evening; R_b's ≤ 2.421 s is this environment's.

## Notes on the run

- The first start of `run_round.py` aborted at `e2-01`: argparse rejects an `--extra-flag` value beginning with `--`
  unless written `--extra-flag=…`; the scheduler was fixed (`3f7fc9ce`) and the whole round restarted from the top.
  The aborted start produced only `e1-01`/`e3-01` with no flag arm; those and that `runs.log` were moved to the
  session scratch directory and are **not** counted here. The counted round is the 64 launches logged in this
  directory's `runs.log`.
- Smoke runs of the instrument (two 16 s, one 70 s) were done before the committed launches, as `PREDICTION.md`
  states; the 70 s one is kept as `control-70s.json` (the detector's positive control); the raw net logs (60–95 MB
  each) stay in the session scratch directory, not in evidence. Each per-launch JSON carries the parsed net-log
  summary the rule reads.
