# Review 1 — the finding-133 SDK fix (`ec59e609`) and its unit tests (`47840e70`)

Reviewer: opus (adversarial, read-only), 2026-10-12. Brief: `brief-review-1.md` (§9.20 step 4). Tree at review time: `79e511c1` (the SDK and its test file are byte-identical to `ec59e609`; §9.21 was appended after the brief and is taken into account where it changes the weight of a finding).

Method: everything below was run on scratch copies of `wasm_sdk_probe/sdk/` under the session scratchpad (`/tmp/claude-1000/.../scratchpad/{base,mut/*}`), Node v24.16.0, `node --test`. No tracked file was edited. Mutations are exact string replacements in `document-sdk.js` (table in §2). Where I say a scratch test "passes on the fix", it ran against an unmodified copy of `ec59e609`'s SDK.

**Result: 0 BLOCKING, 4 SHOULD, 7 NOTE.** I found no failure in the fix's code: every property I could drive — the on-time/late boundary at exactly L, a second stop inside the grace, the production clock path, the default constants, abort/dispose/crash/restart during the grace, a reply after the post-grace TIMEOUT — behaves as §9.20 says (scratch tests X1–X4 and G1–G5, §3, all pass on the fix). What fails is the evidence: 133-U, as committed, passes a family of wrong fixes, including one (M3) that 133-B would not catch either. With §9.21 deferring the count chain, 133-U and 133-B are the only evidence 0.2.14 will carry, which is why R1-1…R1-3 are SHOULD and not NOTE. One design limit (R1-4) is real and unregistered.

## 1. Findings

### R1-1 — SHOULD — 133-U never runs the production configuration; an inert fix keeps 25/25 green

`document-sdk.js:112-120` (default clock, default L, default G). Both U1 (`document-sdk.test.mjs:279-295`) and U2 (`:297-314`) inject all three (`now`, `lateDeadlineMs: 2000`, `lateDeadlineGraceMs`); U3 (`:249-263`) uses the defaults but only on the on-time path, where any clock and any L ≥ a few ms give the same answer. So the code path the page actually runs — `performance.now()` + L = 2000 + G = 10 000 — is executed by no test that could tell whether it works.

Mutations that leave the full SDK suite 25/25 green (each in 0.15 s):

- M1 `: () => globalThis.performance?.now?.() ?? Date.now();` → `: () => 0;` (fix inert in production)
- M1b same line → `: () => globalThis.performance?.now ?? Date.now();` — a one-character typo: `_now()` returns the function, `dueAt` becomes a string, `late` is `NaN`, `NaN > 2000` is false, every deadline is "on time" → **fix inert**
- M2 `DEFAULT_LATE_DEADLINE_MS = 2000` → `= Infinity` (inert)
- M11 default clock → `() => Date.now()` (the wall clock §9.20 explicitly rejects)
- M15 `DEFAULT_LATE_DEADLINE_GRACE_MS = 10000` → `= 1`

Why this matters despite 133-B: 133-B's (b)(c) would turn red on an inert fix in any run where the stale timer beats the reply. But §9.20's 12-run branch says that if the guard never burns, "由 133-U 承載修法" — and 133-U cannot see an inert production configuration. With an inert fix the guard can never burn, so the fallback is reached exactly when every run happens to be reply-first: 0.4¹² ≈ 2e-5 under the measured 3/5 failure rate, 0.73¹² ≈ 2.3 % under the 27 % wake-up hypothesis. Small, but it is the branch where 133-U is the only carrier.

Remedy (scratch tests X3, X4 in §3; both pass on the fix): X3 stubs `globalThis.performance` (no `now` option, default L), jumps it 2 500 ms past a 5 ms deadline, replies inside an injected 200 ms grace → resolves, 0 cancels. It kills M1, M1b, M2, M11. X4 reads the two defaults (kills M2, M15). Tests are outside the shell bundle (`build_e2_c_shell_bundle.py:676-719` globs `*.js` non-recursively in `sdk/`), so adding them does not touch v63's "only `document-sdk.js` differs" condition.

**Conditional BLOCKING:** if 133-B ends on its 12-run NOT_ESTABLISHED branch, X3/X4 (or equivalent) must exist first, because that branch hands the fix to 133-U alone.

### R1-2 — SHOULD — U3 does not test "準時到期 → 行為不變"; the L boundary is unpinned

§9.20 (spec `:606`) lists U3 as "on time → behaviour unchanged". U3 asserts only `instanceof SdkTimeoutError && code === "TIMEOUT"` and that some cancel exists — not when it happened, not that `details` lacks the extension keys, not the message. `node --test` has no default per-test timeout, so slowness is invisible.

- **M3** `if (this._now() - dueAt > this._lateDeadlineMs) {` → `if (extensions === 0) {` (every deadline, on time or not, gets one 10 s extension): **full suite 25/25 green** in 20.16 s — U3 took 10 009 ms, "close timeout recycles the owning Worker" 10 007 ms. In production every real TIMEOUT (getState 30 s, close 10 s, checkpoint save 5 s, save 180 s) would be 10 s later and labelled "extended". **133-B would not catch M3 either**: in K8 the save deadline is late, M3 extends it, the reply arrives, the guard "burns", (a)–(d) pass. Under §9.21 no count chain runs before 0.2.14, so nothing downstream would see it.
- **M10** `>` → `>=` and **M19** `> this._lateDeadlineMs` → `> 50`: 25/25 green. No test has a lateness between ~1 ms (U3) and 9 995 ms (U1/U2), so the value of L — the width of L-133-band — is not pinned by anything.

U1's red case (`unit/red-on-641843c9.txt`) is red for the right reason (`paint timed out after 5 ms` from the pre-fix timer at `document-sdk.js:188`), but it is red by construction: the pre-fix SDK has no clock, so it fails U1 with or without the 10 s jump. It shows U1 can fail; it does not show that U1 discriminates "late" from "on time". The discriminating control — the fixed SDK, same request, no jump → plain TIMEOUT — is not in 133-U.

Remedy (X1 in §3, passes on the fix): injected clock, late ∈ {0, 1000, 2000} → rejects TIMEOUT with `details.extensions`/`extendedMs` undefined, message exactly `paint timed out after 5 ms`, settles in < 1 s, 1 cancel. Kills M3 (all three), M19 (1000, 2000), M10 (2000 = exactly L).

### R1-3 — SHOULD — "再到期時再看一次" is untested; three wrong second-look behaviours stay green

§9.20 (spec `:601`): after re-arming, "look again". U1 and U2 each produce exactly one expiry after the re-arm, with the clock not moved again, so nothing distinguishes "look again" from "give up".

- **M4** extend only while `extensions === 0` (at most one extension): 25/25 green.
- **M5** `extendedMs += …` → `extendedMs = …` (not cumulative): 25/25 green.
- **M9** the re-armed timer TIMEOUTs unconditionally (`entry.timer = setTimeout(() => failAndCancel(new SdkTimeoutError(operation, timeoutMs, { extendedMs, extensions })), G)`): 25/25 green.

The case is real: a second sleep or freeze inside the 10 s grace (lid closed again, or a tab frozen again by the browser), which L-133-hidden-verdict itself relies on ("每次遲到都重新上鏈").

Remedy (X2 in §3, passes on the fix): late → extend; the clock jumps again inside the grace → second extension; then on time → TIMEOUT with `extensions === 2`, `extendedMs === 2G`, 1 cancel. Kills M4, M5, M9.

Related: M13 (drop `dueAt = this._now() + G`, so every later look sees the original lateness) is killed by U2 only by **hanging** — the run did not finish in 90 s. Under `node --test` with no timeout that is a stuck run, not a red one. Giving U1/U2 a `{ timeout: 5000 }` option turns that into a failure.

### R1-4 — SHOULD — the grace is a fixed 10 s whatever the request still needed: an unregistered limit, and the comment claims more than the code does

`document-sdk.js:221-226`: a late deadline is moved to `now + G` (G = 10 000 ms) regardless of `timeoutMs` and of how much of it the engine had used before the stop. The comment at `:211-214` says "the deadline counts only time the page could run", and `:4-9` says the stopped time "is not time the engine had to answer". The code does not give back the unused budget; it gives a fresh 10 s.

Failing input (from reading the code, not measured): a request whose remaining engine work after resume is > G (plus the post-thaw release phase), sent shortly before a stop that runs past its deadline by > L. Example: `autosaveNow("hidden")` sends a `save` (180 s) for a document whose save takes 15 s of engine time; the machine sleeps 5 ms later for 330 s; at resume the deadline is ~150 s late → one 10 s grace → the engine still needs ~5 s → `TIMEOUT {extensions: 1, extendedMs: 10000}` → `RECOVERY_ERRORS` (`editor-session.js:15-22`) → `recoverable-error`: finding 133's symptom, unchanged. The same holds for `open` (120 s budget) of a file that takes > 10 s to load.

Size of the exposure: measured saves on the owner's document are 0.16–0.72 s (`specs/SPEC-M3-autosave.md:91`, `:104`), a ~14× margin. Larger documents: not measured here. None of L-133-band / -suspend / -hidden-verdict / -firefox (spec `:622-625`) describes this; L-133-band is about stops ending near the deadline, not about operations longer than G.

Options (owner's or judge's choice, not mine):
- A — register it as a named limit (e.g. L-133-grace: "a request that needs more than G of engine time after the stop still times out after one extension") and reword the two comments to say what the code does. Text only.
- B — re-arm with `Math.max(G, timeoutMs)`: the request gets back at least its full budget after a stop. It stays inside `document-sdk.js` (v63's one-file condition still holds), but it departs from the ruled G and doubles, in the worst case, how long a dead engine takes to be declared dead after a stop.
- C — leave it as is, and record in the release text that the fix covers saves up to ~10 s of engine time.

### R1-5 — NOTE — a main-thread long task > L in a visible page also triggers the extension, and there the Worker was not stopped

The comment's premise (`:4-9`, "the page -- and the Worker with it -- was stopped") holds for a freeze or a sleep. A synchronous long task on the page's main thread delays the timer just as much while the dedicated Worker keeps running. Measured in Node with the **production** clock (no `now` injected), G = 300: a 50 ms deadline straddled by a 2.5 s busy loop → `TIMEOUT {extendedMs: 300, extensions: 1}` after 2 801 ms instead of a plain TIMEOUT at ~2 500 ms. In a browser the effect is benign or better: a reply the Worker posted during the long task gets processed instead of losing the race, and a truly wedged engine is declared dead G later. It is bounded (one G per stall > L), but no L-133-* names it. No product page task near 2 s is known to me; the realistic sources are modal dialogs (`beforeunload`), heavy GC, a starved machine.

### R1-6 — NOTE — in a long-hidden Chrome tab the re-arm makes L-133-hidden-verdict the expected outcome, not a possibility

The re-arm (`:225`) is a `setTimeout` called from a timer callback, so each extension adds one to the timer's nesting/chain count. Chrome's intensive wake-up throttling (from Chrome's published rules, from memory, not verified in this tree: page hidden ≥ 5 min, chain count ≥ 5, silent ≥ 30 s, no WebRTC) aligns such timers to one wake-up per minute. Once eligible, each 10 s grace fires about a minute after it was armed, is found ~50 s late (> L), and re-arms. For a dead engine the extension then repeats deterministically for as long as the tab stays hidden, and the verdict lands about G after the tab is shown again. L-133-hidden-verdict (spec `:624`) covers the outcome but says "可能"; the mechanism makes it the default once the chain reaches 5. Firefox's budget throttling of background tabs can delay timers by more than L too (same limit). No change needed; the limit's wording could say so.

### R1-7 — NOTE — engine-side deadlines measured inside the Worker are not covered; the ruling's "covers editorAction" holds only for SDK deadlines

`src/probe_engine.cpp:993` (`FormatBarrierStageDeadlineMs = 5000`), `:4386-4410`, `:4950-4957`: each awaiting stage of the format barrier arms a `std::chrono::steady_clock` deadline in the Worker. When it runs out, the loop synthesises a deadline step and the barrier fails with `MUTATION_OUTCOME_UNKNOWN`, which is in `RECOVERY_ERRORS` (`editor-session.js:20`). The v2 session routes it to rollback/review (`narrow-editor-v2-session.js:540-561`). A format action whose barrier is in an awaiting stage when the page and Worker are stopped for > 5 s can therefore still end that way after resume, and an SDK-side fix cannot reach it. From reading the code, not measured. The window is a barrier's duration (tens of ms), so rare. §9.20 rules "不動 Worker", but no L-133-* names it, and fable-ruling §1 lists "一次打字的 `editorAction`" among the paths the SDK fix covers. That is true of the SDK's own deadline only.

### R1-8 — NOTE — clocks: page vs Worker, CDP freeze, OS suspend, the `Date.now()` fallback

- `_now` runs on the page's main thread (the engine is built by the page, `web/e2-editor-app.js:2764-2769`). It is never compared with a Worker clock, so different time origins cannot skew it.
- CDP freeze: page tasks stop while the monotonic clock runs on, so `late` is measured as intended. The probe's `rearm` logpoint logs `this._now() - dueAt`, so 133-B measures this directly.
- OS suspend: what the fix needs is that `setTimeout`'s scheduling clock and `performance.now()` are the **same** clock. Then either both stand still across the suspend (no late timer, the deadline is effectively paused, nothing to fix) or both advance (late detected, the fix applies). As far as I know both run on one monotonic source in each engine (Chromium `base::TimeTicks`, Gecko `TimeStamp`), but that is from memory, not checked in this tree. Unmeasured on every platform, as L-133-suspend already says.
- The `Date.now()` fallback (`:114`) cannot be reached in a browser or in Node. If it ever were, a wall-clock step forward > L during a request would give a spurious extension (benign, +G), and a step backward would give the old behaviour. The comment at `:110-111` ("a clock step cannot fake a late deadline") is true only of the `performance.now()` branch. The pieces that would pin this down are the tests in R1-1.

### R1-9 — NOTE — a burned guard leaves no trace, and the error carries the scheduled grace instead of the measured lateness

`extendedMs` (`:223`) adds up the graces that were scheduled; the one number that says the page was stopped for N s (`now − dueAt` at the late look) is thrown away. The probe's logpoint is the only place it exists. In the field an extension that ends in a reply is invisible: no event, no log. One that ends in TIMEOUT reports `+10000 ms in 1 extension(s)` but not "deadline found 150 s late". CLAUDE.md §7 asks for the payload, not a summary of it. Optional: carry `lateMs` (largest or last observed) in the extension detail. That is one file, and no consumer parses `details` or the message (grep across `web/`, `editor-shell*`, `tools/`: none).

### R1-10 — NOTE — spec ↔ code: no divergence found; two choices worth stating

- `details.extendedMs`/`extensions` appear only after an extension. §9.20 says "最終的 `SdkTimeoutError.details` 帶 …" without "only when extended". The code's choice is what keeps the on-time path "unchanged" (§9.20 U3) and is consistent with it; X1 confirms the on-time message is the pre-fix one and the details carry no extension keys.
- The new options are a test seam that no caller passes. The product page passes the literal `{workerUrl, timeoutMs: 30000}`; no file outside `sdk/` mentions `lateDeadline*`. `now` must be a function and L/G finite > 0 (`:112-120`), so an accidental non-function `now` is ignored. `document-sdk.d.ts` is deliberately not updated. Updating it would not break the v63 condition either, because `.d.ts` and `sdk/tests/*.mjs` are outside the bundle's `*.js` glob.

### R1-11 — NOTE — bookkeeping verified; three survivors are equivalent or near-equivalent mutants

Scratch tests G1–G5 (§3) pass on the fix:
- G1: abort during the grace → `ABORTED` once, exactly 1 cancel, the re-armed timer cleared (active-timer count back to baseline).
- G2–G4: dispose / Worker `error` event / `restart()` during the grace → `ENGINE_DISPOSED` / `WORKER_CRASHED` / `WORKER_RESTARTED`, re-armed timer cleared, no cancel (as before the fix).
- G5: a reply after the post-grace TIMEOUT is dropped, no double settle, 1 cancel.

`failAndCancel`'s `_pending.delete` guard (`:195`) and `_handleMessage`'s `if (!entry) return` (`:275`) still make every settlement single.

The survivors:
- M7 (remove the `_pending.has` guard, `:219-220`) is unobservable: every path that settles a request clears its current timer, so the guard is belt-and-braces.
- M6 (drop the `entry.timer =` write-back at `:225`) is green in 133-U and visible only to an active-timer count (G1–G4 red): it leaves an orphan timer of up to G after abort/dispose/crash/restart, harmless because of the guard.
- M18 (ignore `options.lateDeadlineMs`) is equivalent because every test passes L = 2000 = the default.

A reply that lands in the same turn as the grace timer is the same single-threaded race as before the fix (whichever task runs first wins; `clearTimeout` stops an already-queued timer task), i.e. L-133-band at the grace's edge.

## 2. Mutation table

"133-U + suite" = first `node --test sdk/tests/document-sdk.test.mjs` (18 tests, timings below), then every survivor re-run on the tree's full command over the two committed files (`document-sdk.test.mjs` + `sdk-worker-merge-key.test.mjs`): each "green" row is 25/25, exit 0. "X/G" = reviewer scratch tests in §3.

| id | exact change in `document-sdk.js` | 133-U + suite | X/G (scratch) |
|---|---|---|---|
| M0 | none | green (U1 41 ms, U2 27 ms) | all pass |
| M1 | `:114` → `: () => 0;` | **green** | X3 red |
| M1b | `:114` → `: () => globalThis.performance?.now ?? Date.now();` | **green** | X3 red |
| M2 | `:10` → `= Infinity;` | **green** | X3, X4 red |
| M3 | `:221` → `if (extensions === 0) {` | **green** (20.16 s; U3 10 009 ms) | X1×3, X2 red |
| M4 | `:221` → `if (extensions === 0 && this._now() - dueAt > this._lateDeadlineMs) {` | **green** | X2 red |
| M5 | `:223` `+=` → `=` | **green** | X2 red |
| M6 | `:225` drop `entry.timer =` | **green** | G1–G4 red |
| M7 | delete `:219-220` | **green** | all pass (equivalent) |
| M8 | M6 + M7 | **green** | G1–G4 red |
| M9 | `:225` → grace timer calls `failAndCancel(new SdkTimeoutError(operation, timeoutMs, { extendedMs, extensions }))` | **green** | X2 red |
| M10 | `:221` `>` → `>=` | **green** | X1 late=2000 red |
| M11 | `:114` → `: () => Date.now();` | **green** | X3 red |
| M12 | `:225` re-arm with `timeoutMs` instead of G | U1 red | — |
| M13 | delete `:224` (`dueAt` not moved) | U2 **hangs** (> 90 s) | — |
| M15 | `:11` → `= 1;` | **green** | X4 red |
| M16 | post a `cancel` after `:225` | U1, U2 red | — |
| M18 | `:115` ignore `options.lateDeadlineMs` | **green** | all pass (equivalent) |
| M19 | `:221` → `> 50` | **green** | X1 late=1000, 2000 red |

## 3. Reviewer scratch tests (pass on `ec59e609`; offered as the remedy for R1-1…R1-3, not committed)

Shared harness: a `FakeWorker` that answers `init`/`open` and holds `paint`; `cancels()` counts `kind === "cancel"` messages to worker 0.

```js
// X1 — on time (late <= L, injected clock) is a plain TIMEOUT, at once.  Kills M3, M10, M19.
for (const late of [0, 1000, 2000]) test(`X1 late=${late}`, async () => {
  const s = setup(); const clock = { now: 0 };
  const engine = await createDocumentEngine({ workerFactory: s.factory, now: () => clock.now,
    lateDeadlineMs: 2000, lateDeadlineGraceMs: 5000 });
  const doc = await engine.open(new ArrayBuffer(16)); const t0 = Date.now();
  const p = doc.render({}, { timeoutMs: 5 }); clock.now += 5 + late;
  await assert.rejects(() => p, (e) => e instanceof SdkTimeoutError && e.details.extensions === undefined
    && e.details.extendedMs === undefined && e.message === "paint timed out after 5 ms");
  assert.ok(Date.now() - t0 < 1000); assert.equal(s.cancels(), 1); engine.dispose();
});
// X2 — a second stop inside the grace is looked at again; extendedMs accumulates.  Kills M4, M5, M9.
test("X2", async () => {
  const s = setup(); const clock = { now: 0 };
  const engine = await createDocumentEngine({ workerFactory: s.factory, now: () => clock.now,
    lateDeadlineMs: 2000, lateDeadlineGraceMs: 30 });
  const doc = await engine.open(new ArrayBuffer(16));
  const p = doc.render({}, { timeoutMs: 5 }); p.catch(() => {});
  clock.now += 10000; await sleep(15); clock.now += 10000;
  await assert.rejects(() => p, (e) => e instanceof SdkTimeoutError
    && e.details.extensions === 2 && e.details.extendedMs === 60);
  assert.equal(s.cancels(), 1); engine.dispose();
});
// X3 — production clock and production L (no `now`, no `lateDeadlineMs`).  Kills M1, M1b, M2, M11.
test("X3", async () => {
  const s = setup(); const original = Object.getOwnPropertyDescriptor(globalThis, "performance");
  let offset = 0; const realNow = performance.now.bind(performance);
  Object.defineProperty(globalThis, "performance", { configurable: true, value: { now: () => realNow() + offset } });
  try {
    const engine = await createDocumentEngine({ workerFactory: s.factory, lateDeadlineGraceMs: 200 });
    const doc = await engine.open(new ArrayBuffer(16));
    const p = doc.render({}, { timeoutMs: 5 }); offset += 2500; await sleep(40);
    s.workers[0].respond(s.held[0], { pixels: new ArrayBuffer(16), width: 2, height: 2, revision: 0 });
    assert.equal((await p).width, 2); assert.equal(s.cancels(), 0); engine.dispose();
  } finally { Object.defineProperty(globalThis, "performance", original); }
});
// X4 — the defaults.  Kills M2, M15.
test("X4", async () => {
  const engine = await createDocumentEngine({ workerFactory: setup().factory });
  assert.equal(engine._lateDeadlineMs, 2000); assert.equal(engine._lateDeadlineGraceMs, 10000); engine.dispose();
});
```

G1–G5 (R1-11) use the same harness. The request is put into its grace with an injected clock (+10 000 after a 5 ms deadline, then 20 ms of real time). Then: G1 aborts the `signal`; G2 calls `dispose()`; G3 emits a Worker `error`; G4 calls `restart()`; G5 lets a 20 ms grace expire and then replies. Each asserts the rejection code, the cancel count, and `process.getActiveResourcesInfo().filter(x => x === "Timeout").length` back at its pre-request baseline.

Main-thread long-task demo (R1-5): production clock, `lateDeadlineGraceMs: 300`, `render({}, { timeoutMs: 50 })`, then `while (Date.now() < start + 2500) {}`. Output: `{"code":"TIMEOUT","details":{"operation":"paint","timeoutMs":50,"extendedMs":300,"extensions":1},"msg":"paint timed out after 50 ms (+300 ms in 1 extension(s) after a late deadline)","settledAfterMs":2801,"cancels":1}`.

## SUMMARY

Review 1 of finding 133's SDK fix (`ec59e609`) and 133-U (`47840e70`): **0 BLOCKING, 4 SHOULD, 7 NOTE.**

No failure found in the fix's code. On `ec59e609`, reviewer scratch tests pass for: the boundary at exactly L, a second stop inside the grace, the production clock, the defaults, and abort/dispose/crash/restart during the grace (timer cleared, single settle, cancel only where it was before). The failures are in the evidence.

- **R1-1 SHOULD** — 133-U never runs the production clock, L or G (`document-sdk.js:112-120`). An inert fix keeps 25/25 green: M1 `() => 0`, M1b the one-character typo `performance?.now ?? …` (NaN, every deadline "on time"), M2 L = Infinity, M11 wall clock, M15 G = 1. This becomes BLOCKING if 133-B ends on its 12-run NOT_ESTABLISHED branch, where 133-U alone carries the fix. Remedy: scratch X3/X4.
- **R1-2 SHOULD** — U3 does not test "on time → unchanged". M3 (always extend once) keeps 25/25 green, with every real TIMEOUT 10 s later; 133-B would pass it too, and §9.21 leaves no count chain behind it. L is unpinned (M10 `>=`, M19 `> 50` green). U1's pre-fix red is red by construction. Remedy: X1 (late 0/1000/2000 → plain TIMEOUT, no extension keys, < 1 s).
- **R1-3 SHOULD** — "look again" is untested: M4 (at most one extension), M5 (extendedMs not cumulative) and M9 (the grace always TIMEOUTs) all stay green. Remedy: X2. M13 is caught only by a hang; give U1/U2 a test timeout.
- **R1-4 SHOULD** — the fixed 10 s grace (`:221-226`) does not restore the unused budget. A save or open that needs more than 10 s of engine time after the stop still dies with 133's symptom. No L-133-* covers this, and the comments at `:4-9` and `:211-214` claim more than the code does. Options A (register a limit and reword), B (`max(G, timeoutMs)`), C (state it in the release text).
- **R1-5 NOTE** — a main-thread long task > L in a visible page also extends (measured in Node, production clock), although the Worker kept running. Benign, unregistered.
- **R1-6 NOTE** — the re-arm is a chained timer. Under Chrome's intensive throttling of long-hidden tabs it re-extends every minute, so L-133-hidden-verdict is the expected outcome, not a "maybe".
- **R1-7 NOTE** — engine-side `steady_clock` stage deadlines (`probe_engine.cpp:993`, `:4386-4410`) can still yield `MUTATION_OUTCOME_UNKNOWN` across a stop of more than 5 s. The SDK cannot reach them; not registered.
- **R1-8 NOTE** — the fix needs the timer clock and `performance.now()` to be one clock. That holds by construction as far as I know, but it is unverified, and suspend is unmeasured (L-133-suspend). The `Date.now()` fallback cannot be reached.
- **R1-9 NOTE** — the error carries the scheduled grace, not the measured lateness, and a burned guard leaves no trace outside the probe.
- **R1-10 NOTE** — no spec↔code divergence. Extension details appear only when extended, which matches U3. No caller can pass the seam by accident. Tests and `.d.ts` are outside the bundle glob, so v63's one-file condition is untouched.
- **R1-11 NOTE** — equivalent mutants M7 and M18; M6 (no timer write-back) is visible only to an active-timer count. The same-turn reply/grace race is L-133-band.
