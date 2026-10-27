# R1 ruling 1 (fable, 2026-10-27), verbatim

Requested with `BRIEF-ruling.md` in this directory under the owner's authorization for this session.

> # R1 ruling 1
>
> Ruled 2026-10-27 by fable under the owner's session authorization. Inputs: `BRIEF-ruling.md`, `REVIEW.md`, `../r1-source/README.md`, `../r1-prep-01/` (24 pages; `report.json` has `preparationOnly: true`, `preRed: NOT_ESTABLISHED`), the reader at `2b561678` (`r1_arm`, `inspect_r1`, `arm`, `s2_compare`, `check_pre_red`), the runner's `main`, and `handoff/PROTOCOL-2026-10-26-v23-r1-inputs.md`. Nothing was edited or run beyond reading files.
>
> ## 1. "late" includes the S2 stale comparison (option b)
>
> The protocol's "late/error/recovery result" names the move's result, i.e. its reply, not the reader's readback schedule. The reader at `2b561678` only guards an early readback (`readback too early`, NE) and the marker's ordering; neither tests the result itself. The collector's own meaning of a late result is S2's `stale`: the reply's reported `state.caret`/`state.selection` differ from the delayed readback, or its collapsed flag disagrees with the active selection type (`s2_compare`). The same six moves from the same ranges are already held to it in S2. Ruling: R1 adopts `s2_compare` unchanged, for both arms, called with the neutralised `comparison` dict exactly as `arm()` builds it (`changed: False`, `revision = beforeRevision`), so a changed document stays a FAIL through `bad` instead of becoming an NE inside `s2_compare`. Candidate stale is FAIL with `staleFields` recorded, placed with the other candidate FAIL checks before `r1_marker_witness`. Control stale is NE through the existing `label` ("independent control outcome invalid: reply stale"). A reply without `state` is NE (`move/state absent`). S2-style `lateCursorObservations` may be recorded; that is a record, not a criterion. No other mechanism is added.
>
> §9 check: before satisfaction (no counted R1 cell exists); forced and named (`REVIEW.md` issue 1: a stale reply whose cursor settles correctly would PASS); per-instance form (§1); cutoff = the first complete 72-cell population per browser, after which further "late" concerns are findings. Counting semantics: nothing resets, because nothing has been counted; the review measured `s2_compare == []` on all 36 prep-01 arms, so no preparation verdict changes.
>
> ## 2. The v19 pre-red stays a prerequisite
>
> Keep the runner and reader refusal. The pre-red is an instrument prerequisite, not a cell criterion: the protocol's silence does not remove an existing refusal, and removing it would be an instrument change with no forcing measurement (§9 condition 2) and a new mechanism (§4). It can only block, never create a PASS. The counted run passes `--pre-red-report findings/evidence/link-batch-v23/feature-pre-red/counted-05/report.json`; `check_pre_red` re-verifies it at run start and again in `judge main`. If it refuses, the run does not start and the refusal is reported with its payload; it is not patched around.
>
> ## 3. Token-wrap exposure: FAIL with note stands; no NE premise now
>
> Confirmed default: a literal m1r/m1e/m1d Left/Right cell whose setup is not at the native logical position reads FAIL with the note `(setup not at the native logical position)`, as `test_token_wrap_exposure_is_recorded_not_decided` pins. No NE premise is added: no measurement forces it (prep-01: B = 89 and browser twips equal native twips in both browsers), so it fails §9 condition 2 and belongs in work items, not the gate. Pre-decided outcome: if such a FAIL occurs in a counted run, it is that cell's verdict and R1's verdict as recorded, and it is not relabelled afterwards. The record already carries `wrap` and `setupAtNativePosition`, so the cause is readable without a rerun; that FAIL would be the measurement that could justify an NE premise for a later population under §9.
>
> ## Not ruled
>
> `REVIEW.md` items 2–6 and Q3–Q7 need no ruling (false FAIL/NE or record only). The counted run's stop-at-first-nonpassing rule is unchanged.
>
> ## Conditions before the first counted R1 run
>
> - C1. Land item 1 in `r1_arm` as written above; the reader is the only code that changes. Red cases first (§6), in `test_v23_feature_r1.py` on the model pages: (a) candidate reply `state.caret` at the pre-move position, readback and marker at the correct landing → FAIL, `staleFields` contains `caret` (this is the review's scenario; today it is PASS); (b) candidate reply `state.selection` still the range, readback collapsed, active `none` → FAIL (`selection`, `active-selection-type`); (c) control reply with a stale caret, candidate clean → NOT_ESTABLISHED with the control-invalid label, neither PASS nor FAIL; (d) candidate reply without `state` → NOT_ESTABLISHED `move/state absent`.
> - C2. Re-run `../r1-source/reader-mutation-sweep.py`: its `ast` census must list the new check and report `ALL_KILLED`; regenerate `reader-mutation-sweep.output.json` with the new reader/test hashes (a disabled-condition census cannot see an absent check, which is why C1's red cases are required).
> - C3. Re-read all 24 prep-01 pages with the changed reader and their stored configs: expected 24 PASS with records identical apart from the new empty `staleFields`. Any difference stops the count and is reported, not fixed in place.
> - C4. Existing tests unchanged and green (S1–S5 preserved-page re-reads; `test_token_wrap_exposure_is_recorded_not_decided` untouched).
> - C5. Counted invocation: `--population r1 --pre-red-report <counted-05 report>`, no `--preparation-only`, `--keep-going`, `--case-id` or `--browser`; the report must record `preRed.verdict == EXPECTED_RED` and `judge main` must accept it.
> - C6. Commit the reader change and the sweep output before the run (the run binds instrument hashes), and confirm no counted run whose import closure includes the reader is in flight (the merge note in `../r1-source/README.md`).
>
> ## Plain-language rationale for the owner (fable)
>
> - Item 1: the protocol says a "late" result cannot pass. The reader only checked that it waited long enough before looking; it never checked that the engine's answer to the key press matched what the engine actually did afterwards. That check already exists for the S2 cells, so we reuse it as is. On the 24 real pages it changes nothing. It can only add a way to fail, never a way to pass.
> - Item 2: the run tool already refuses to start a counted run without the old pre-red report. Keeping it costs one argument; removing it would be a change nobody measured a need for.
> - Item 3: six cells could fail purely because a browser wrapped a long word somewhere other than native did. Both browsers were measured wrapping exactly where native does, so this cannot happen on this profile. If it ever does, it is a FAIL on the record and we investigate; we do not pre-write an excuse for it.
