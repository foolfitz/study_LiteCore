# Task 2026-10-14m: the held-into-refusal judge and restore-window under C (§10.7), with 10-14l's reports as the witness

**Why.** `specs/SPEC-M3-link-batch.md` §10.7 (S-9) says the arms below need a new expectation under C before any count, and that their first v20 runs are the §34.4 witnesses. Task 10-14l (`09770d87`, `findings/evidence/link-batch/host-0.2.20/README.md`) made those runs on host 0.2.20 (page `53019168…`, engine v20, buildId `6cffc5960ebbbd98`), in both browsers.

The arms are `start-press`, `start-hold`, `end-hold`, `end-press-type`, `cell-start-hold` and `restore-window`.

- Under the unchanged judge, held reads `FAIL (30)` and table reads `FAIL (12)`.
- The red sits only on clauses that presuppose a refusal and a reopen: `one_reopen`, `scroll_end`'s "no restart-required sample", and `stage_is("nothing-selected")`.
- By the executor's reading, every C arm meets §10.7's five properties.

**Authority.** You rule this on the owner's behalf; the owner hands these rulings to fable. Give a plain-language reason for each choice in the evidence README and the commit.

## What to decide and deliver

- **The keying.** The judge must still read v19's expectation on a v19 report: the committed 0.2.18/0.2.19 reports under `findings/evidence/132/`, `134/` and `136/` must not change verdict. The C expectation applies only on a profile that ships C.
  - The precedent is task 10-14i (`7e6c9acd`, `run_merge_wasm_shakedown.py`'s `boundary_noop_declared`). It keys on the engine-emitted `verified-boundary-noop` fragment in the profile's wasm, because no manifest field declares C.
  - Reuse that rule or argue for another. Do not invent a second, different keying without saying why.
- **The C rules** for the five held/table arms, from §10.7:
  - 0 refusals;
  - generations `['1']`;
  - the document equals the original plus the marker;
  - the marker at the caret's place;
  - and, where the old rule had a scroll clause, the scroll rule that C implies.

  Keep every clause that still means the same thing under C (`document_kept`, the counts, the placement rules).
- **`restore-window` under C.** The window it measured, between a refusal's reopen and the restored caret, no longer exists. The probe now waits 20 s for a generation change that never comes. Decide what this arm asserts on v20:
  - the no-op itself, or a rewrite of the probe's wait;
  - or retiring the arm on C profiles as "nothing to guard", in AGENTS.md §3's sense, with the reason written down.

  Any change to the probe is a probe change and needs this same witness.
- **The held-key tail.** The executor saw the page stay `busy` 3.0–4.3 s after a hold was released, unverified as to cause. The main session's guess is one or two no-ops in flight at release, each about 2.25 s (the cost §10.5 names, together with 132's depth rule). Read the source and the reports, then rule one of three:
  - an instance of a named cost (cite it);
  - a new named limit (write it);
  - a candidate finding (describe it; the main session registers findings).
- **Re-judge.** Run the changed judge on:
  - (a) 10-14l's reports: the C arms must pass, and the four non-C table arms must still pass;
  - (b) every committed v19-era report the judge has read before: verdicts must be unchanged.

  Show both. Add a red case: a v20 report doctored into a refusal must fail under C, and a v19 report must not pass under C.

## Limits

- No browser run, no ddev, no make, no link, no host change.
- **Edit only:**
  - `findings/evidence/132/held-into-refusal/judge_held_into_refusal.py`;
  - `findings/evidence/134/restore-window/probe_restore_window.py`, only if you rule a probe change, and then without running it;
  - a new `findings/evidence/link-batch/host-0.2.20/re-expectation/` directory;
  - an appended section in `findings/evidence/link-batch/host-0.2.20/README.md`.
- If the right fix lies elsewhere, stop and report.
- §34.4: this is "repaired because of execution", one line per changed tool, with the witness `findings/evidence/link-batch/host-0.2.20/`. Write the line in the README.
- Commit only your own paths (`git commit -- <paths>`). If `.git/index.lock` exists, wait and retry. End messages with your model's `Co-Authored-By` line; never a `Claude-Session` line; no push.

## Output

- Final reply: a `## SUMMARY` of at most 20 lines with:
  - the keying;
  - the C rules per arm;
  - restore-window's ruling;
  - the held-tail ruling;
  - the re-judge table (changed and unchanged per report);
  - the red cases;
  - the §34.4 count.
