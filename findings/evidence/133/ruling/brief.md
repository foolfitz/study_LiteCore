# Brief for fable — finding 133 blocks the 0.2.13 count: dispose of it

The owner chose 「交 fable 裁決」 over three options the main session offered (A fix first / B ship and register / C drop the on-hidden autosave). Rule on the disposition and write its conditions. You are the judge; the main session will execute, re-derive your numbers, and the owner reads your plain-language reasons.

Repository root `/home/jiajun/LibreOffice/study_LiteCore`. Read-only except the one output file named at the end. Do not run browsers, touch the ddev host (`~/Projects/Nextcloud_Apps/litecore`), or edit any other file. Project rules: `CLAUDE.md` (criteria forms §1–§11: per-instance or tool-closed criteria only; no criteria that quantify over a future judgement; withdraw a claim rather than build machinery to keep it; a drafter's own judgement must not carry a termination claim) and the checks stop rule `specs/SPEC-M3-paragraph-merge.md` §34 (checks frozen; threat model = accidents; each reader reviewed once; changing a check needs a witness report; ledger 因執行而修 11 / 因審核而修 6 as of now).

## Where the release stands

Read `handoff/HANDOFF-2026-10-12f-v62-frozen-0.2.13-bound-owner-hand-test-chain-running.md` (State, Next, Open) and `specs/SPEC-M3-autosave.md` §9.2–§9.4 (autosave behaviour and criteria), §9.12–§9.19 (finding 131 fix, rulings, owner hand test §9.18, freeze/binding §9.19).

- Shell generation **v62 frozen** (`75e29eb2…`), page `d761f1ce…`, host 0.2.13 `e028517`, seven runners bound (`3a6603de`). Shipped is still 0.2.12.
- The owner hand-tested 0.2.13 before the count and chose to ship with L-128-rapid / 132 as registered (§9.18).
- The count chain (`findings/evidence/m3-production-ui/runs-0.2.13/chain-2026-10-12.out`) passed the `page_honesty` shakedown and **stopped at the `locks` shakedown: 21/22, K8 `frozen` Chrome 0/1**. No counted run started.

## What was measured (main session, today)

All in `findings/evidence/m3-locks/k8-recoverable-2026-10-12/README.md`; finding file `findings/133-a-save-in-flight-across-a-page-freeze-is-declared-dead.md`.

- K8 (`specs/SPEC-M3-locks-and-permissions.md:86`; driver `wasm_sdk_probe/tools/check_m3_locks.py:606-622`): open (lock held), one edit, CDP `Page.setWebLifecycleState frozen` for ~330 s, thaw, press save. Its expectation was changed for 0.2.13 (`ce758882`, spec §9.4 「計數」: last record manual; earlier `auto` records allowed, each must pass AS-1).
- History: 27 K8 runs 2026-09-28 … 2026-10-12 morning, every page up to 0.2.12 plus the pre-fix 0.2.13 witness, all `ready`, save landed.
- Today on `d761f1ce…`: chain run 1/1 `recoverable-error`; logpoint probe (`wasm_sdk_probe/tools/probe_k8_frozen_recovery.py`, report `probe-2026-10-12T121440+0000.json`) 2/3. Across 0.2.13's pages 3/5 (witness 0/1).
- Mechanism (logpoint timeline, all three probe runs): 1–2 ms after `freezeAt` the page goes `hidden` and `autosaveNow("hidden")` starts an engine `save` (request 18, `timeoutMs` 180000). At thaw (~150 s past that deadline) the overdue `setTimeout` races the Worker's reply. Timer first (runs 1, 3; ~180 ms after thaw): `failAndCancel save TIMEOUT` → `_blockQueue(recoverable-error, editor-recovery)`. Reply first (run 2; ~270 ms after thaw): save completes, both auto and manual saves land.
- After `recoverable-error` with no checkpoint the page says 「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。」 Whether a restart really loses the edit: not measured.

## Code (read these; line numbers checked today)

- `wasm_sdk_probe/sdk/document-sdk.js:155-200` — `_request`: per-request `setTimeout(failAndCancel(new SdkTimeoutError))`; `:221-242` `_handleMessage`.
- `wasm_sdk_probe/editor-shell/editor-session.js:15-22` `RECOVERY_ERRORS` (includes `TIMEOUT`); `:315-326` the drain's catch ("a selection readback TIMEOUT means the engine thread is already dead"); `:342-352` `_blockQueue`.
- `wasm_sdk_probe/web/e2-editor-app.js:2605-2618` `autosaveNow`; `:2629-2633` the `visibilitychange` → `autosaveNow("hidden")` listener (127, spec §9.2 「切到背景」).
- E1-C binding: `wasm_sdk_probe/e1/editor-shell-bundle-v2.json` includes `editor-shell/editor-client.js`, `editor-session.js`, `state-machine.js`, `input/clipboard-adapter.js`, `input/input-adapter.js` (a change there breaks E1-C's verdict, `check_e1_c_bundle_intact.py`). `sdk/document-sdk.js`, the v2 session (`editor-shell-v2/`) and the page are outside E1-C but inside the E2 shell bundle (`tools/build_e2_c_shell_bundle.py` SCOPE) → any change there is a new generation (v63), re-bind, and the page criteria it reaches re-run.

## The main session's reading (claims for you to test, not facts)

1. The root cause is older than 0.2.13: any request with a wall-clock timeout in flight across a freeze/suspend can be declared dead; a manual save pressed just before a lid close is exposed on 0.2.12 too (code reading, **not measured**). 0.2.13 adds a trigger at the exact moment of hiding.
2. Real-world reachability is unmeasured: whether Chrome fires `visibilitychange` on lid close / screen lock on each OS; whether a `setTimeout` is overdue after OS suspend (platform clock); Chrome's own background-tab freezing comes minutes after hiding, long after a 0.5–0.7 s save. Firefox not tested (K8 is Chrome-only).
3. Candidate fix locations: (a) SDK — a timer that fires far later than scheduled (e.g. > 5 s late) means the page or machine was stopped; re-arm a grace period instead of failing; (b) the v2 session subclass; (c) the page (e.g. the Page Lifecycle `resume` event). (a) is generic and outside E1-C. Each is a new mechanism under CLAUDE.md §4 ("stop and report") — hence this brief.

## Questions

- **Q1 Disposition.** A (fix before counting), B (ship 0.2.13 as is; K8 recorded red / LOCKS LAND not established, or K8's premise re-ruled; 133 in the release text), C (remove the on-hidden trigger), or something else. Give the owner plain zh-TW reasons and weigh: the owner's acceptance of 0.2.13 (§9.18), the autosave's purpose (protect work at the moment the user leaves), that 0.2.12 is what is shipped meanwhile, and the cost of a new generation (every page criterion the change reaches is re-run).
- **Q2 If a fix:** where (and why not the others); its criterion in a permitted form, written before any run; the red case (the current page/package, 3/5 red today — what N of clean runs makes "fixed" a measurement for an intermittent defect, given the base rate); what the change re-opens (which of 131-B, 121-B, 129-B, 130-U, 128-B, AS-*, the six M3 runners, the product-path net must be re-run for a change at that location, and which may stand on the v62 measurements with a stated reason).
- **Q3 K8 itself.** Its premise was "lock expiry while frozen, then save". With autosave on hidden it now also tests "a save in flight across a freeze". Is K8 still the right check, or does it need a separate arm/criterion for 133 so K8 keeps testing locks? Any change to `check_m3_locks.py` falls under §34 (witness = the committed shakedown `113020Z` and the probe report).
- **Q4 Anything the main session got wrong** in the measurement, the mechanism, or the readings above (say which file/line shows it).

## Output

Write `findings/evidence/133/ruling/fable-ruling.md` (create it; nothing else). Sections: the ruling per question; plain-language reasons for the owner (zh-TW); any spec text to append to `SPEC-M3-autosave.md` (zh-TW, append-only, as a new §9.20, written so the main session can paste it verbatim); conditions/steps in order with what each needs committed before the next; numbers you rely on with the file they come from. Keep it under ~250 lines. Return a ≤30-line SUMMARY as your final message.
