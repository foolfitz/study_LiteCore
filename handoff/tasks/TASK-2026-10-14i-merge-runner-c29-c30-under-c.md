# Task 2026-10-14i: the merge runner's expectation for C29/C30 under C (before v20 is bound)

**Why now.** Handoff 10-14, Next 2: before v20 is bound, `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py`'s `expectation()` must stop mapping R0c's `nothing-selected` to a refusal on a profile that ships C. On v20, C29 (Backspace at the document start) and C30 (Delete at the document end) complete `verified-boundary-noop`; the runner records `pass: false` on exactly those 4 records per report. The change moves the runner's sha256, so it lands before `BINDING`. You decide the design on the owner's behalf (the owner authorized fable for this round's decisions); write the reasons into the commit and the evidence README.

**Read first.**
- `specs/SPEC-M3-link-batch.md` §10.5 (C) and §10.7 (S-9: the re-expectation and its §34.4 witness);
- `specs/SPEC-M3-paragraph-merge.md` §34 (the stop rule: witness, "repaired because of execution", no new guards) and the M2-3 row (line ~145) plus the list rule (line ~727);
- `findings/evidence/link-batch/v20-shakedown/merge/README.md` (the witness: what C29/C30 recorded, which clauses are false, why each step took ~14 min);
- the runner: `expectation()` (line ~173), the refusal branch (`refusal = spec["expected"][0] == "refused"`, `toast_window(..., limit=90)`), `bound_values`, `BINDING`, `RED_PROFILE`.

## What to decide and deliver

- **The keying.** v19 (shipped) still refuses C29/C30; v20 does not. The expectation therefore depends on the profile under test. Key it on something the profile declares (its manifest or ABI), not on a profile name, unless you find a reason the name is right; say which and why. The R0c-generated list stays tool-closed (spec line ~727): a decision the runner does not know still stops it.
- **The new expectation under C**, from §10.7 and the witness: no refusal, generation unchanged, no toast, document = original + marker, caret unchanged. The control's clauses (it keeps only caret and size) need the same treatment; the witness lists which clauses failed there.
- **The refusal branch's 90 s toast wait** must not run for a no-op.
- **Evidence the change is right without a browser.** If the runner's per-record judgement can be recomputed from the recorded fields, re-judge the eight part-B reports (`shakedown-*.json`, `control-*.json`, both browsers; and `m2-4-*`, `m2-1b-*` must not change) and show: the 4 C29/C30 records per report now pass, every other record's verdict is unchanged. If it cannot be recomputed, say so and write what a re-run must show; do not run one (see Limits).
- **A red case** (§6 of AGENTS.md): show the new keying refuses to pass C29/C30 as a no-op on a profile that does not declare C (e.g. the v19 records of the counted run), so the change is not a blanket loosening.
- **§34.4:** this is "repaired because of execution" +1, witness = the part-B reports. Write that line in the evidence README.

## Limits

- No browser run of any kind: `dist/editor-shell-v2/` currently holds a red shell candidate (finding 140, being fixed by a parallel task 10-14h). No `make`, no link, no freeze, no host, no `--write`.
- Edit only `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py` (and its unit tests if it has any), plus a new `findings/evidence/link-batch/v20-shakedown/merge/re-expectation/` directory. Do not touch `editor-shell-v2/`, `web/`, `sdk/`, `src/`, `findings/140-*`, `findings/evidence/paste-latency/`: a parallel fable owns those.
- Do not set `BINDING`; binding is a later step.
- Commit only your own paths (`git commit -- <paths>`); if `.git/index.lock` exists, wait and retry rather than delete it. End messages with your model's `Co-Authored-By` line; never a `Claude-Session` line; no push.
- Final reply: a `## SUMMARY` of at most 20 lines: the keying and why, the re-judge table (records changed / unchanged per report), the red case, the runner sha256 before and after.
