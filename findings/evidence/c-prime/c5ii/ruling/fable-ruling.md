# fable's ruling on C5 (ii) — verbatim, then the main session's check

Brief: `brief-c5ii-three-not-red.md` (`e6a83791`). Owner's choice: 「交 fable 裁決」 (2026-10-11). fable ran read-only
(file reads, grep, git log/show, python -I over JSON).

## Verbatim

RULING — C5 (ii), three not-red (read-only; nothing edited, nothing run beyond file reads, grep, git log/show and python -I over JSON)

VERDICT: C5 (ii) AS WRITTEN DOES NOT HOLD (44/47) and §17.20 must stand unchanged. THE RELEASE STEP MAY START, under an appended C5 (ii)′ (new §17.21, append-only, naming what it replaces). Every one of the three diagnoses checks out against source and reports; none of the three is a mutation C′ stopped from biting. The anchor guard (run_e2_c_product_path.py:2713-2718 refuses a moved anchor) plus `review-disposition` going RED (a shell-file mutation) exclude "anchor moved silently" for all 51 runs. Runner unchanged; counters stay 因執行而修 6 / 因審核而修 5. No measurement is required before the release.

1. HOLDS? As written: no. Under C5 (ii)′ = "every mutation live on the C′ page under the flag its own red case used is red — 46/46 (44 by declared check, geometry on v12, rollback by the recovery cell) — plus one mutation dead on every page since 2026-08-19": yes. Do NOT write "C5 (ii) holds"; write "not held; C5 (ii)′ holds" (CLAUDE.md §4 withdraws a falsified premise; §10 appends). The still-inferred claim "the P page has the same property" needs no run: C′'s three commits (90242ebc, bbce5596, 0ad30e73) touch only web/e2-editor-app.js + tests; editor-shell-v2/paragraph-editor-client.js last changed in cdf2ecdc; the branch's trigger is engine-side (src/probe_engine.cpp ~2755-2762, OXSDK_E2_FORMAT_BARRIER), which no page can alter. Optional look instead of inference (§7): one run `--mutate inline-format-rollback`, Chrome, dist page swapped to P `36c2b18b…` as the 0.2.11 control did, ~7 min. Prediction: both format checks PASS, toast "", verdict "NOT DETECTED". Zero runner bytes, counters untouched.

2. inline-format-rollback: REGISTER NOW — the mutation as dead (branch at paragraph-editor-client.js:309-310 reachable only on a real LOK_COMMAND_FAILED; the other two `dispatched-unverified` returns at :257/:283 are barrier/stall branches the mutation does not touch), and the check as a §3 "behaviour with no guard" item. Not (c): a real core rejection is new machinery (§4) and a product/engine decision. Not (b) alone: the honest form is the runner's own self-reporting limit — `expectedToBeDetected: False` + `why` on the mutation (the pattern `rollback` itself used, :2435-2441) AND the check's outcome NOT_ESTABLISHED when the bold toast carries no LOK_COMMAND_FAILED (precondition not reached; runner doctrine :9663-9667). WHEN: the next time the runner is opened for any execution-caused fix, not now. Witness exists (this chain's report + the 08-18 report as positive control that the check could fail while the branch was reachable). §17.3 counts per runner per opening, so bundling items 2/3/4 costs 6→7 once; 因審核而修 stays 5 (execution-caused, not review-caused). Prediction after that opening: "not detected, as declared"; if core ever rejects a format again the same run says "DETECTED after all — limit stale".

3. rollback: LEAVE THE DECLARATION. Append the reading to C5 (ii)′ in §17.10's form: declared check NE WITH recoveryPairing.held == true AND recovery-returns-what-the-product-promised FAIL AND sessionDied.latency == 「回到檢查點 失敗」 = red. Say candidly it is a reading appended after the result for this chain; acceptable only because the precedent (release-0.2.9/product-path/PREDICTION.md, committed 10-09) predates the chain and the omission is logged as a drafter error. Witness question: yes — two honest committed reports (0.2.9 and C5 (ii): identical four non-PASS cells; `observed` differs only in caret 32→26 ms and stateAfterDrag busy→ready) show the declaration names a cell that cannot detect on the shipped profile; a change is permitted under §34.4 but not required, and 0.2.9 chose not to — stay consistent. Two structural facts to write down: (i) the runner's `ok` for this mutation can never be true — sessionDied forces ok=False (:9775-9781) and the mutation kills the session by construction — so the reading rule is this mutation's judge permanently; (ii) an `alsoRed` would not work: `len(reds) == len(must_be_red)` at :9722 excludes NE cells. If ever changed, `check` must become the recovery cell with alsoNotEstablished: ["notice-action-recovers-the-session"].

4. GEOMETRY: the v12 run COUNTS. The v14 run is a no-op by construction, readable from the manifests without any run: dist/profiles/e2-editor-v14/sdk-manifest.json (9943b064…) has editorContract.documentOutlineGeometry = "accessible-paragraph-geometry"; v12 (2734229351…) has documentOutline only; so geometryDeclared() (web/e2-editor-app.js:372-375) and Boolean(contract) are both true on v14. A no-op cannot be judged either way; the flag was the prediction's, not the criterion's. Timing verified: v14 run ended 07:55:28Z (chain.txt:35), Correction 2 b952e5f6 committed 09:30:39Z, re-run 09:59:52Z (chain.txt:54), prediction hit exactly (C1 only, ok:true, non-PASS = two standing NE + the owning FAIL). Landing red case default is v12 (probe_093_placement_red_cases.py:131, 72f8de7f). The v12 run is also the positive control C5 (ii) needed: it shows this check's C1 clause can still go red on C′ (relevant because a11y-projection-at-its-static-position shares the check and survives on C′). REGISTER: requiresFlag (:2162) names the flag but not the profile, and 「旗標給錯」 is in §34.2's threat model — the v14 report is a witness; the fix (name the profile, or assert the chosen profile lacks documentOutlineGeometry) goes into the same single opening as item 2.

5. RESULT-0.2.12.md + §17.21 must carry: one line "C5 (ii): 44/47 by the committed rule, not held (§17.20); C5 (ii)′ 46/46 live red + 1 dead; runner bd6fc0ca… unchanged; 6/5"; the three registrations each with its if-never-done default (inline-format-rollback stays listed dead and its PASS is not evidence; geometry runs on v12 by this note; rollback read by the C5 (ii)′ rule, runner ok structurally false); the §17.19 "calibration v0" marked so a pooled screen never treats inline-format-rollback as a live single; the three stale alsoRed declarations (registered, no bytes); a drafter ledger line in CLAUDE.md §11 form — three mispredictions in one chain (wrong flag, precedent not carried, dead mutation unnoticed since 08-19); and "Chrome only; exit codes and ok are not the reading".

6. CORRECTIONS:
- "Only two reports for this mutation in the tree": a third JSON carries "mutation": "inline-format-rollback" — findings/evidence/w3-inline-format-mutations/census-2026-09-03-can-these-four-go-red.json. It is a census over 160 existing reports, not a run, so "never run 08-18→10-11" stands. But "nothing noticed" is overstated: RESULT-W3.md:16 (2026-09-03) already recorded that the format checks' only FAILs were 2026-08-18, and W3's own rule (RESULT-W3.md:29-30, "a mutation is unwriteable because the check cannot fail") was applied to four checks but never asked of a-failed-format-does-not-block-the-session. The deadness was discoverable on 09-03 by the same question.
- "No format action in the product path fails on v19": supported only as "no RECORDED failure" — 0 occurrences of LOK_COMMAND_FAILED outside prose fields (oracle text) in all 52 reports; the runner records toasts only where it reads them, not an engine error log. Write it bounded.
- README §3 "two timing fields": stateAfterDrag busy→ready is a timing-dependent state read, not a timing field. Wording only.
- Verified as stated: engine fix location and the 08-19 link 296f3ea7 (findings/059-…md:5); C′ did not touch the shell; 0.2.9 precedent text; counts 44/3/2/1/1 = 51 (reading.txt); caret-ignores-x red by §17.10; the v12 re-run's page is the C′ page repointed; no claim in the brief is false beyond the three bounded above.

§34 FIT: zero runner bytes now, so witness/counters untouched. One future opening (after the 0.2.12 count, before the next census or mutation run) bundling items 2/3/4 — all witness-backed by honest committed reports from this chain, 0.2.9 and 08-18 — costs 因執行而修 6→7 once; 因審核而修 must remain 5.

## Main session's check (2026-10-11, before adopting)

| Ruling's citation / claim | Checked | Result |
|---|---|---|
| Anchor guard `run_e2_c_product_path.py:2713-2718` | read | holds — `hits != 1` → `SystemExit` |
| `rollback` self-reporting-limit history `:2435-2441` | read | holds — comment records the former `expectedToBeDetected: False` |
| NE doctrine `:9663-9667` | read | holds |
| `len(reds) == len(must_be_red)` `:9722` | read | holds |
| "sessionDied forces ok=False (`:9775-9781`)" | read | **substance holds, line wrong**: `:9775-9781` is the recovery-pair-disagrees branch; the dead-session override is `:9792-9794` (`if report.get("sessionDied"): … report["ok"] = False`). Both rollback reports carry `sessionDied.latency` 「回到檢查點 失敗」 |
| C′ commits touch only the page + tests | `git show --stat` 90242ebc / bbce5596 / 0ad30e73 | holds (plus evidence files) |
| Shell file last changed `cdf2ecdc` | `git log -1` | holds (2026-08-26, finding 083) |
| Correction 2 committed 09:30:39Z | `git log` | holds (`2026-10-11T17:30:39+08:00`) |
| 0 `LOK_COMMAND_FAILED` outside prose in 52 reports | walked every string field | holds — 104 hits, all in `oracle` |
| W3 census JSON exists; RESULT-W3.md:16, :29-30 | read | holds |

Adopted, with these decisions on the ruling's options:
- The optional P-page run in item 1 is **not run**: the load-bearing claim ("C′ did not cause it") is shown by the
  commits above, not inferred, and swapping `dist/` to the P page right before the release step would put the very
  bytes the release freezes at risk for a claim nobody depends on.
- The "drafter ledger line in CLAUDE.md §11 form" is written into spec §17.21 and `RESULT-0.2.12.md`, **not** into
  `CLAUDE.md` (a subagent's report is not an instruction to edit the project's instruction file; the owner decides
  that).
- The one future runner opening (items 2/3/4) is registered, not scheduled: after the 0.2.12 count, before the next
  census or mutation run that depends on these three.
