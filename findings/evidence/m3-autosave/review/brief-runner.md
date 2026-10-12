# Review brief — the one dual-seat review of `check_m3_autosave.py` before its first counted use

Project rule §34.3 (`specs/SPEC-M3-paragraph-merge.md` §34): each new reader gets ONE dual-seat adversarial review before its first counted use, and none after. Threat model §34.2 = accidents in HONEST runs only — a wrong flag, a stale `dist/`, a moved page, a skipped step, a partial run, a browser crash, a missing key in a generated file, a slow machine, a stale line of page text. NOT forged or hand-edited reports, NOT edited constants. Repository: `/home/jiajun/LibreOffice/study_LiteCore`. **READ-ONLY**: do not edit, create or commit anything in the repository or in `~/Projects/Nextcloud_Apps/litecore` (a scratch copy under `/tmp` is fine); no browsers, no ddev, no builds, no network. You MAY run `python3 wasm_sdk_probe/tools/check_m3_autosave.py --selftest`, `--score <committed report>` and `--red-cases <committed report>`.

## What is under review

- The runner: `wasm_sdk_probe/tools/check_m3_autosave.py` (commit `f6e1706a`, sha256 `a60eff46dff5c274…`; two reader fixes since it was written, each with a committed witness — see `findings/evidence/m3-autosave/shakedown/README.md`). It imports helpers from the counted runners `check_m3_locks.py`, `check_m3_page_honesty.py`, `check_m3_production_ui.py`, `check_m3_skeleton_open.py`, `check_m3_host_entry.py` and the probes `probe_autosave_m1.py`, `probe_autosave_m3.py`; those are frozen and are NOT under review, but say so if the runner uses one of them in a way it was not built for.
- The criteria it implements: `specs/SPEC-M3-autosave.md` §9.4 (zh-TW; read §9.2–§9.5, §9.7 and §9.10 whole). The criterion text is the authority. Arms ↔ criteria are in the runner's docstring and `PLAN`; the brief it was written from is `handoff/tasks/TASK-2026-10-12e-check-m3-autosave-runner.md`.
- The product it drives (read to ground your scenarios, not to review it): page `wasm_sdk_probe/web/e2-editor-app.js` (the autosave scheduler from the `// ---- autosave` section, `run()`, `saveDocument`); host `~/Projects/Nextcloud_Apps/litecore/js/litecore-editor.js` (`save()`, `saveCopy`, `strand()`, the O2 label, the `data-litecore` record) and `templates/editor.php`.
- Real reports from the packaged 0.2.13 (host `appinfo/info.xml` 0.2.13, page `c7f904fa…`), both in `findings/evidence/m3-autosave/shakedown/`:
  - `2026-10-12T054150+0000.json` — the first shakedown (Chrome, as2-key + as4a). It is the §34.4 witness for the one fix already made (`afeef717`: `insert()` used to stop on any 「失敗」 in the latency line, and a save that wrote a copy leaves 「自動存回 失敗」 there).
  - `2026-10-12T054605+0000.json` — every arm, both browsers, once each (runner `afeef717`). It is the witness for the second fix (`f6e1706a`: `as2-toolbar` took the last mutation of `#s-revision` as the action's completion, and the page rewrites that value many times). Re-scored with the current runner it is `VERDICT clean`; `--red-cases` on it: 76/76 red (`…054605+0000.red-cases.txt`).

## Already registered — do not report these as findings, but DO say if one is mis-assessed

- §9.7 named limits (L-129, L-reload, L-discard, L-close, L-manual-conflict-toast) and §9.10's L-auto-engine-toast.
- K7 `expired`'s ~0.5 s margin to the 30 s clock, and the two pre-registered expectation changes of §9.4 「計數」 (host_entry `conflict`, locks K8): they belong to other runners and wait for their witness.
- AS-3(a) withdrawn (§9.5 note).
- AS-6(a), 128-B, 129-B, 130-U are other runners' cells.

## The writer's own judgement calls — confirm or reject each with a reason

1. `as5-held` passes when no held key is lost (the criterion is conditional on a loss); the score line prints `lossRuns`, how many runs exercised the toast path. Should a counted run with `lossRuns == 0` in a browser be PASS, or NOT_ESTABLISHED?
2. `as2h`: the tab going hidden more than 5 s after the key is NOT_ESTABLISHED, not red.
3. O2-1(d) also reads the host's `lastSaved` (`at`, `target`), not only the label text.
4. Every arm checks its own edits completed (`edited()`, `inserted()`) and a failed premise is a FAIL, not NE.

## Questions (answer each; say "no defect found" where you find none — do not invent one)

A. Per criterion of §9.4 the runner claims (AS-1, AS-2 both arms, AS-2h, AS-2c, AS-3, AS-4 a/b/c, AS-5 both arms, AS-6(b), AS-7, O2-1 a–e): does the arm drive the shape the criterion describes and does the scorer compare what the criterion says (window bounds, `<` vs `<=`, which record, which clock, which file)? Name a missing clause, a wrong field, a wrong comparison.
B. Construct a plausible HONEST run, grounded in the runner's, the page's or the host's code (cite file:line), where a cell returns PASS when the spec says FAIL, or FAIL/NE when the spec says PASS. Look in particular at: the two clocks (page `performance.timeOrigin + now()` vs host `started + relative ms`); `wait_autos()` counting `settled` records; `phase()` idling to 40 s after the edit; `snap()`'s `allowed` HH:MM (which attempt's `respondedAt`); the `as5` busy-pill trigger (could it catch a busy that is not the auto's engine part?); `typed_runs()` on the owner's document; `copy_list()` / `copy_facts()` naming; `as4c`'s wire capture (`wire(session.drain())`) and its URL match; `as6b`'s leave recorder; the Firefox path of `as2h`.
C. The binding: `binding_problems()` and the counted-run refusal — could an honest counted run on the wrong page / session / host version slip past, or the right one be refused?
D. Red cases (`RED_CASES`): which gated clause of §9.4 has no red case, and does that matter under §34.2?

Answer in English, ≤ 60 lines: BLOCKING items (would change a verdict on an honest run), then NON-BLOCKING, each with file:line evidence. Write your answer to stdout only (the main session saves it).
