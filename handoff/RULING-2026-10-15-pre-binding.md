# Ruling 2026-10-15 (pre-binding, part J): the count chain's abort rule; finding 135's C2 repeat semantics; the release text

Ruled by fable on the owner's behalf. Authority: the owner chose **A** on 2026-10-15 for task `handoff/tasks/TASK-2026-10-15c-pre-binding-v20-prep-and-rulings.md` (commit `91de8867`): part J's three judgment calls are ruled here, and the release-text draft (`handoff/RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md`, zh-TW) is shown to the owner before it is used.

Read in full before ruling: `AGENTS.md` (criteria form §1–§11), `specs/SPEC-M3-paragraph-merge.md` §34, `handoff/HANDOFF-2026-10-14b-…` with its Addendum, `handoff/HANDOFF-2026-10-13f-…` (line 50, the origin of the obligations), `handoff/RUNBOOK-relink-v20.md` §4, findings 135, 137, 138, 140, 141, 142, 143, 144, `specs/SPEC-M3-link-batch.md` §7, §10.5, §13.5, §15.1, §16, `specs/SPEC-M3-held-key.md` §3.2, §4, §8, §15, §17, `specs/SPEC-M3-production-ui.md` §17.4 (the C2 row), `specs/SPEC-M3-autosave.md` §9.4, §9.21, the chain scripts and logs `findings/evidence/m3-production-ui/runs-0.2.13/chain-2026-10-12.{sh,out}`, `runs-0.2.12/chain-2026-10-11b.{sh,out}`, `runs-0.2.12/stop-1/README.md`, `findings/evidence/m3-production-ui/RESULT-0.2.12.md`, every committed C2 report directory (`findings/evidence/c-prime/c2/`, `132/guard/c2/`, `134/guard/c2/`, `134/c2-cell-repeat/` with `ab/` and `ruling/ruling-2.md`, `136/guard-r2/c2/`, `c2-aborted-load-1.58/`, `c2-extra/`), `judge_c2.py`, `read_ab.py`, and the desk records of 10-14k, 10-14l and 10-14p (`findings/evidence/link-batch/v68-witness-2/README.md`, `link-batch/host-0.2.20/README.md`, `host-0.2.21/k3/README.md`). The numbers below were re-read from those files, not copied from the brief. No browser, no ddev, no make; no code, test, spec or finding was edited.

---

## J-a. The count chain's abort rule

### Ruling

**Never abort a started chain. Every abort moves to before `START`, where it is a mechanical preflight with named, deterministic conditions. Load is recorded at every step and is never a gate.**

The two shapes the task offered were "abort only if load ≥ X at start" and "never abort a started chain". The ruling is the second, with a preflight in front of it. "Load ≥ X" is rejected for the reasons in §J-a.3.

### J-a.1 The rule

**Preflight (before the chain's `IDENTITY-START` line; a refusal prints the failed item and exits without writing a `START` line).** Each item is a failure mode that has already cost a run, with the precedent named:

| # | Condition | Precedent | If it fails |
|---|---|---|---|
| P1 | KWallet `kdewallet` `Locked` reads `b false` (`busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`) | 10-13d run 1: every Chrome half died at its first `Page.navigate` (180 s each, about 1.5 h, nothing measured); memory `reboot-locks-kwallet-headless-chrome-hangs` | REFUSED; the owner unlocks the wallet on the VNC desktop; start again |
| P2 | A default-flag headless Chrome reaches the host: `timeout 30 google-chrome --headless=new --user-data-dir="$(mktemp -d)" --dump-dom https://litecore.ddev.site:8443/login` exits 0 and the output contains `Nextcloud` (the positive control the 10-14p queue wrapper used, `host-0.2.21/k3/README.md` "Desk") | 10-13d (wallet), 0.2.12 stop-1 (`ERR_CERT_VERIFIER_CHANGED` after launch), memory `nextcloud-work-uses-owner-ddev-scaffold` (another project's `ddev start` makes the router 404 briefly) | REFUSED; the printed reason says which (rc, byte count, grep count) |
| P3 | Nothing of ours is running: `pgrep -af 'probe_|judge_|check_m3|run_e2_c|run_merge|run_v20'` prints 0 lines (excluding `pgrep` itself) | every C2 chain's `desk-at-start.txt`; the 10-14l/10-14p wrappers | REFUSED |
| P4 | Identity: `dist/e2-editor-app.js`, `web/e2-editor-app.js` and the archived host package's page decode to the same sha256, and the host tree is clean (`dirty[]` empty) | the chain's `ident` line already prints these; 10-12f Next 1 compares START with END | REFUSED (today the chain prints and a reader compares afterwards; comparing before START costs nothing and saves five hours) |
| P5 | The owner has been told the window and has agreed not to open `litecore.ddev.site` during it; `oc_files_lock` is empty at start | 10-12f "Host while the chain runs" (the owner closed tabs; the lock table was empty; every M3 runner clears the whole lock table, so the owner's own session would be clobbered and the owner's activity would perturb arms) | not mechanical for the agreement; the lock-table read is. Record both. If the owner cannot be asked, the chain is not started |

**Recorded, never gated**, at `START`, before each step, and at `END`: `/proc/loadavg`, `pgrep -c chrome`, `pgrep -fc '/opt/google/chrome/chrome( |$)'` (browser processes), `pgrep -c firefox`, swap used (`free -m`), and the three P1–P3 readings. The owner's desktop browsers are never touched.

**Once `START` is written:**

- No human and no agent kills the chain or any step of it. The one stop is the script's own shakedown gate (`STOP: shakedown X not clean; no counted run started`, exit 1), exactly as `chain-2026-10-12.sh` is written. Counted steps never stop the chain; they write their exit code and verdict line and the chain goes on.
- A step that runs long is not stopped (0.2.12's `locks` shakedown took 35 min, its counted `page_honesty` 64 min). The runners have their own timeouts; a hang is read afterwards.
- A reboot or power loss ends the chain without `DONE`. That is "no count", not an abort: the partial log stays as evidence, and the whole chain runs again as a new file (the `chain-2026-10-11b.sh` precedent: a new log directory, the old one kept).

### J-a.2 What the reader of the chain's output does on each outcome

The reader is the main session, reading `chain.txt` / `chain-<date>.out` after `DONE` (10-12f Next 1–3), never while the chain runs.

| Outcome (what the log shows) | Reading | What follows |
|---|---|---|
| No `START` line; a preflight `REFUSED <item>` line | Nothing ran. Not a count, not an abort | Fix the named item; run the same script again |
| `STOP: shakedown X not clean` (exit 1, no counted run) | Read `shakedown-X.log` and the shakedown report. Classify once: **(a)** an honest execution accident (traceback, no report, a browser or navigation fatal such as `Page.navigate` timeout, `net::ERR_*`, the browser exiting) → §34.1(a); **(b)** a product red → a finding; **(c)** a judge error → needs a witness, §34.1(b) | (a): fix the environment or launcher, run the whole chain again as a new file (0.2.12 stop-1 → `chain-2026-10-11b.sh`); (b): the count does not proceed on these bytes (0.2.13 stop → finding 133 → 0.2.13 retired); (c): re-judge with the shakedown report as the witness, no re-run |
| `DONE`; every counted step exit 0; every `VERDICT` line green; red cases all red; `IDENTITY-END` equals `IDENTITY-START` | The count holds | Product-path reader made red once on scratch copies, then its verdict read from its `SUMMARY` line (§34.7, not its exit code); RESULT written in the shape of `RESULT-0.2.12.md`; C2 read by §J-b |
| `DONE`; a counted step red | The criterion is red. Attribute first against the uncounted list (SPEC-M3-link-batch §7: 127–136, 138, 140, 141, 143, 144, 132's page fix, v20) | No re-run of that step on the spot. The only re-runs are §34.1(a) (an honest accident in that step: re-run that one step once after `DONE`, appended to the same log with a `RERUN` line, both reports kept; if it recurs, it is an instrument finding and the criterion reads NOT_ESTABLISHED) and §34.1(b) (a committed witness that the judge misjudged) |
| `DONE` but `IDENTITY-END` differs from `IDENTITY-START` | The bytes moved under the chain: the count is void | Whole chain again |
| No `DONE` (reboot, power, a step still running the next morning) | Not a count | Whole chain again as a new file; the partial log is kept |
| A product-path report exits 1 | Not a verdict by itself: the Firefox reports exited 1 in 0.2.12 on the known red `an-inline-format-reaches-a-selection` and the count held | The reader's `SUMMARY` line decides (§34.7) |

### J-a.3 Why not "abort only if load ≥ X at start"

- **No committed measurement ties load to a verdict on this machine** (12 cores, 30 GB, `nproc`/`free` at drafting). The committed record: 134's guard C2 spiked at load **0.68** on a clean desk (`134/guard/c2/chain.txt`); the repeat chain spiked 3/10 at load 0.9–1.8; the A/B on the same bytes spiked 0/10 at 0.7–1.0 (`ab/README.md`: "load is not the trigger"); 129-B on 10-14k ran at load 1.5–2.7 with the owner's Chrome at 32–34 processes and swap active in 41 of 54 arms, and read **54/54, 0 cells different from four reference rounds** (`v68-witness-2/README.md`); 10-14l's §10.7 host arms and 10-14p's K3 ran at 1.5–2.7 and 1.7–2.5 with no clause red that was not a product defect (`host-0.2.20/README.md`, `host-0.2.21/k3/README.md`; K3c's red was 27–29 extra deletes against a limit of 2, finding 144, not a latency number). Any X inside [0.4, 2.7] contradicts a green run; any X above 2.7 has never been observed, so it would be a number nobody measured — AGENTS.md §2: a criterion decided by whoever is present.
- **The one off-script abort selected against the signal.** 10-13d's G4 was killed at load 1.58 after its gap-80 cell had written 158.3 ms with finding 135's signature; the restart read 43.1 and became the record (`c2-aborted-load-1.58/ABORTED.txt`, SPEC-M3-held-key §17 condition 6). A load gate re-runs exactly the runs that carry 135's stall, which is a filter on the thing 135 measures. AGENTS.md §4: do not build machinery to keep a claim true.
- **The failures that actually cost whole runs were deterministic, not load**: the wallet (1.5 h of Chrome halves measuring nothing), the certificate-verifier reset (stop-1), the lock table shared with the owner. Each has a cheap, exact preflight; none is a load number.
- **Time of day is not a condition.** The chain runs overnight because the owner asked for the five hours to be batched and detached (`release-count-batched`), not because the desk is cleaner at night; the owner's browsers may be open and are recorded, not removed.

### J-a.4 Defaults and form

- **If never decided**: the chain as written already encodes "never abort" (its only exit is the shakedown gate), and an agent's hand abort is a deviation to be recorded as 10-13d did. This ruling makes that explicit and adds the preflight.
- **If the preflight is never implemented**: the chain is still started only after P1–P5 are checked by hand and their readings pasted into the task's README; the chain itself is unchanged.
- **Form (AGENTS.md §1)**: P1–P4 are per-instance checks on one start; the reading table is closed over the chain's own `say` lines. Nothing here is a judgment made during the run.
- **Adding a load gate later (AGENTS.md §9)** needs its witness: a committed report in which a clause went red and the step's recorded load lay outside the band of every green run of that clause. Until such a report exists, load stays a recorded covariate.

### J-a.5 Work items (no code here; not repairs)

- **W-a1.** The next chain script (`runs-<release>/chain-<date>.sh`, the shape of `chain-2026-10-12.sh`) gains the preflight block before `IDENTITY-START` and the recorded desk line before each `say "… begin"`. This is a new chain file, as every count has been; it is not a check and has no §34.4 witness requirement. The script's `STOP` rule, step order and identity lines are unchanged.
- **W-a2.** The task that launches the chain states the owner's agreement (P5) and the window.

---

## J-b. Finding 135's C2 repeat semantics

### J-b.1 The committed record (every complete run of the Chrome ratio-2-wide owner gap-80 cell)

Read from `judge-output.txt`, `read_repeat-output.txt`, `read_ab-output.txt` and `ABORTED.txt`:

| page | source | runs | on-screen max per run (ms) | ≥ 150 | 135 spikes (≥ 100 at keys 9–13, 1-based) |
|---|---|---|---|---|---|
| `8909564e…` 0.2.12 | `c-prime/c2/` (verdict run) | 1 | 39.8 | 0 | 0 |
| `abe93f45…` 0.2.15 | `132/guard/c2/` (verdict run) | 1 | 41.1 | 0 | 0 |
| `abe93f45…` | `134/c2-cell-repeat/ab/` odd runs (diagnostic) | 10 | 43.8 45.7 44.1 45.9 **147.9** 46.9 45.8 46.1 42.7 44.7 | 0 | 1 |
| `6470dec0…` 0.2.16 | `134/guard/c2/` (verdict run) | 1 | **148.7** | 0 | 1 |
| `6470dec0…` | `134/c2-cell-repeat/` (diagnostic) | 10 | 44.7 43.9 41.5 39.5 **179.4** 46.0 **158.0** **180.4** 43.7 40.4 | 3 | 3 |
| `6470dec0…` | `ab/` even runs (diagnostic) | 10 | 49.9 40.4 42.0 45.9 44.6 46.5 41.9 42.0 42.9 48.7 | 0 | 0 |
| `b24d754a…` 0.2.18 | `136/guard-r2/c2/` (verdict run) | 1 | 43.1 | 0 | 0 |
| `b24d754a…` | `136/guard-r2/c2-extra/` (G6) | 2 | 43.8 50.8 | 0 | 0 |
| `b24d754a…` | `c2-aborted-load-1.58/` (not judged, not of record) | 1 | **158.3** | 1 | 1 |

Totals over 37 complete runs on four pages: **6 spikes (16 %)**, **4 over the gate (11 %)**; on 0.2.16 alone 4/21 and 3/21. Every spike sits at key 10 (sometimes key 11 too: 114.0, 105.5, 103.1), commit max 140.3–151.3, a paint gap of 196.6–210 ms right after key 9's commit; every spiking run's on-screen median stayed 25.4–30.5 where a median was printed (the A/B reader prints none), and clause (a) (every commit < 160) never failed. Non-spiking runs of this cell max at 39.5–50.8. The rate moves between sessions on the same bytes (3/10 then 0/10). **No other C2 cell has ever read ≥ 100 ms** (Firefox gap 80: 44.5–55.2; Chrome gap 200: 42.1–44.3; Firefox gap 200: 42.8–47.9, over the four verdict runs).

So the judge's single-run `on-screen max < 150` clause on this one cell passes or fails by luck at roughly one run in nine, as finding 135 says; the judge is otherwise untouched by 135.

### J-b.2 Ruling

**A repeat count is needed for this cell. The C2 chain runs three times; the judge is run unchanged on each; the count reads the three verdict lines by the rule below. The single-run rule is not kept as the verdict, and "N runs all under the gate" is rejected.**

1. **Run.** On the bound page (`ccb67a52…`, host 0.2.23), on the counted desk (J-a's preflight), `findings/evidence/136/guard-r2/c2/chain-c2.sh`'s shape (both browsers, both gaps, ratio 1.5 recorded, ratio 1 for P2) is run **three times back to back**, one directory per run under this count's release evidence directory (the `release-0.2.12/`, `release-0.2.13/` precedent): `…/c2/r1/`, `r2/`, `r3/` (about 4 min each by the committed chains' timestamps: 03:40:13–03:44:06, 07:00:39–07:05:00). The whole chain, not only the Chrome cell, so that `judge_c2.py` runs on a complete directory exactly as it is written.
2. **Per run.** `python3 -I findings/evidence/c-prime/c2/judge_c2.py --dir …/rK` and `judge_p2.py --dir …/rK/ratio-1`, unchanged, pinned to `ccb67a52…` (W-b1). Each prints its own verdict; those lines are the record.
3. **The count's reading of C2** (fixed here, before any run; a FAIL run is "attributable to 135" when its **only** FAIL line is `chrome owner-gap80 on-screen max` and the printed max is **< 200 ms**; 200 is above every committed spike, 147.9–180.4, and below nothing ever measured on this cell; a FAIL on any other line, or a max ≥ 200, is not 135's recorded shape):

| three judge verdicts | C2 reads |
|---|---|
| 3 × PASS | **PASS** |
| 2 × PASS, 1 × FAIL attributable to 135 | **PASS**, with the rate written beside it in RESULT and in the release text (the default's "ratio beside") |
| 1 × PASS, 2 × FAIL both attributable | **one extension**, once: three more runs (`r4`–`r6`), the same way. Six verdicts: ≤ 2 FAIL (all attributable) → **PASS** with the rate; ≥ 3 FAIL → **FAIL** |
| 3 × FAIL, or any FAIL not attributable to 135 (another line, another cell, max ≥ 200), or `judge_p2.py` FAIL | **FAIL** |
| any run `REFUSED` (report missing, unreadable, bound to another page) or fewer than three complete runs | **NOT_ESTABLISHED** (not a verdict on the product): fix the binding or the accident (§34.1(a)), run the missing run once; if still short, it stays NOT_ESTABLISHED and the count is not read |

4. **What a FAIL means.** It is not "run again until green". ≥ 3 of 6 attributable FAILs is a stall rate of 50 % against a committed band of 11–16 %, i.e. 135's rate has moved on this page, which is itself a measurement: finding 135 gets the numbers, the C2 criterion is red for this count, and the count is red. A non-attributable FAIL is a typing-latency regression and reads as any other red.
5. **The rate is always reported**, PASS or FAIL: "k of N runs over the gate, all at 135's shape", with the three (or six) maxima. The release text says this cell is not safely under its gate (SPEC-M3-held-key §15 追記).

### J-b.3 Why this shape

- **Single run (the default)** gives about 11 % chance of a red count on a page with no regression, and says nothing about what follows a FAIL; that is the form defect 135 registered.
- **"N runs all under the gate"** compounds it: at 11 % per run, three runs all pass 70 % of the time; five, 56 %. A criterion that fails a healthy product one time in three is not a criterion.
- **This rule**: at the worst committed rate (0.14), a healthy page reads FAIL about 2 % of the time (≥ 2 of 3 then ≥ 1 of the next 3, plus 3 of 3); at 0.11, about 1.3 %. One extension, once, is the precedent of ruling 2 condition 5 (`134/c2-cell-repeat/ruling/ruling-2.md`), not a new shape.
- **It changes no judge.** `judge_c2.py` keeps its single-run clause and prints what it prints; the reading is over its output lines. §34.1's freeze is not touched, §34.3's one review for `judge_c2.py` (codex, 2026-10-11) is not re-spent, and the §34.4 counts stay 0/0 for this ruling.
- **The attribution needs no new reader**: "only FAIL line" and "max < 200" are read off the judge's own output. `read_ab.py`'s per-key reading is diagnostic and optional; its spike definition (≥ 100 at keys 9–13) is the one the table above uses, kept for continuity, not for the verdict.
- **Form (AGENTS.md §1)**: per-instance over a tool-closed set (the three or six judge outputs the chain wrote). **§9's four conditions**: written before any run that counts; forced by finding 135 (named); form checked; deadline = this count's RESULT (after it, the rule stays for later counts unless a later ruling replaces it, and the rate band is re-read from the then-committed record).

### J-b.4 Defaults

- **If the three runs are never made**: the default stands — the single verdict run is the verdict, and the committed rate (4 of 37 over the gate, 6 of 37 spiking, as of 2026-10-15) is written beside it.
- **If a judge pin is not moved (W-b1)**: every run reads `REFUSED` → NOT_ESTABLISHED; the count is not read on C2 until the pin moves.
- **Time-vs-position (gap 200 × 10) and the worker-side shim** stay the owner's follow-ups (finding 135 「之後」); nothing here depends on them.

### J-b.5 Work items

- **W-b1 (binding update, not a repair).** Before the C2 runs, the `PAGE` line of `findings/evidence/c-prime/c2/judge_c2.py` (`:53`, now `b24d754a…`) and of `findings/evidence/typing-latency/judge_p2.py` (`:41`, same value) moves to `ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e`, old value kept in the comment above, one commit per pin line, the precedent being `1fa91903` / `c0d507cc` / the 136 re-pin. These two judges are not among part P's nine runners (P4 names the six M3 runners, production UI, autosave and the product-path net), so this is the main session's. §34.4: 0/0.
- **W-b2 (optional, later; a new tool).** A reader that takes the three (or six) run directories and prints this section's verdict line. It is a judging tool, so before its first counted use it needs its red cases first and its one §34.3 review; its red cases are already committed: the ten reports in `134/c2-cell-repeat/` (any window of runs 05–08 must read "extension" or FAIL, any window of 01–04 PASS) and `ab/` (the 0.2.16 arm must read PASS). It is not needed for this count; the rule is applied by reading the judge's lines.
- **W-b3 (release text).** The sentence the owner sees is in `RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md` §4 (finding 135): the cell is not safely under its gate; about one run in nine shows one ~0.15–0.18 s pause near the tenth key; on the record the pause appears on pages with and without 134's change, and its cause is unlocated.

---

## J-c. The release text

Written as `handoff/RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md`, zh-TW by the task's instruction (owner-facing; this is the stated exception to `AGENTS.md`'s English rule for `handoff/**`). Every claim in it cites its finding or spec section; everything not measured is marked 「未量」 with what would measure it. The task's twelve required items are all present (its §3–§6), plus the per-release table and the "what the count will and will not claim" section. The draft is **shown to the owner before use**; nothing in it is a ruling.

Points the owner must confirm are listed in the draft's §7.

---

## §34.4 for part J

- Repaired because of execution: **0**. Repaired because of review: **0**.
- No tool, test, spec or finding was edited. The pin moves in W-b1 are binding updates (as P3/P4 are), not repairs.

## Revision

| date | what |
|---|---|
| 2026-10-15 | First version (fable, task 10-15c part J). |
