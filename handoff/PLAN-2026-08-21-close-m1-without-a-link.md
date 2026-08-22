# Plan — 2026-08-21: close what M1 can close without asking for a link

From [`HANDOFF-2026-08-19-every-row-has-a-check.md`](HANDOFF-2026-08-19-every-row-has-a-check.md),
reconciled against the two documents written **after** it:
[`ROADMAP-2026-08-20-milestones.md`](../research/ROADMAP-2026-08-20-milestones.md) and
[`RESEARCH-2026-08-20-product-route-and-competitors.md`](../research/RESEARCH-2026-08-20-product-route-and-competitors.md).

**Autonomous items only.** Nothing here needs a relink, a core rebuild, or a human
operator. The user is away; the manual round is deferred by their instruction and
by the roadmap's own ordering (§2: the clipboard round belongs *after* cut can
delete, "otherwise only half the path is measured").

> **Outcome of this round: [`HANDOFF-2026-08-21-the-link-is-authorised.md`](HANDOFF-2026-08-21-the-link-is-authorised.md).**
> T0, T0.5, T1, T2, T3, T4, T5, T6 and T7 all ran. The user authorised the link;
> the payload is settled at six items; nothing is linked yet. `cut` and
> `turn-formatting-off` both moved, in opposite directions, on measurements taken
> that day.

> **v2. The first version was rejected by adversarial review (codex, 2026-08-21)
> on five counts, three of which were design errors that would have produced a
> measurement that could not fail.** What changed and why is §6. The most
> important one: T2's measurement design was impossible as written, and reading
> `probe_engine.cpp:4364-4374` says so in a comment.

> English per `AGENTS.md` (2026-08-19): the only reader of a `handoff/` file is
> the next agent.

---

## 0. State this plan starts from — measured, not quoted

Every number below came from running the tool today, not from reading the handoff.

| | |
|---|---|
| checklist | 13 done / **1 partial** (`cut`) / 0 unverified / 0 missing / **2 blocked** (`redo`, `move-by-line`); `--report` reconciled against today's baseline, `problems: []`, `ok: true` |
| queue | 45 items, 15 open, **0 blocking**, `P1 complete: True` |
| product path | 34 paths, 20 driven, **14 uncovered**, 0 waived, `ok: true` |
| baseline, Chrome | `ok: true`, 22 checks, `KNOWN_RED` `{}`, no stale declarations, served shell `07143f96…` == declared (v25). *"every product path this covers behaves; 1 not established"* |
| **baseline, Firefox** | **`ok: false` — *"a product path is broken"*.** Two `FAIL` (`the-caret-is-drawn-where-it-was-placed`, `ctrl-x-is-handled-by-the-product`) and **two** `NOT_ESTABLISHED` (both recovery checks). Served shell matched. See T0.5 |
| **matrix** | **`status: frozen-before-D0`, frozen 2026-08-17, bound to `wasmSha256: d538ce0b…`** — two relinks ago. The tree is on `29ec627b…`. See T7 |

The roadmap's M1 §2 names three things as *not needing a link*:

> **不需連結**：剪下真的能刪（先**量**範圍刪除再宣告，不要先放寬 manifest）／
> 14 條 uncovered 路徑接進回歸網／復原的第二個誘發器（解除對未修的 038 的依賴）

…and its completion criterion names a fourth: **`D0` 跑完、矩陣凍結**. The first
version of this plan excluded D0. That was wrong — see T7.

---

## 1. What is NOT scheduled, and why

| | Why not |
|---|---|
| **Clipboard OS-boundary round** | Needs a human (permission prompt, a real Ctrl+V, the OS boundary). Deferred by the user today. Correctly ordered *after* T2 anyway. |
| **relink** | The user's decision. **T2 needs none** — see §T2.0. T4 is the ask, prepared not executed. |
| **core rebuild** (a11y gate 0, M4 gate 0) | The user's scope (`user-handles-core-rebuilds`). T6 prepares it; it does not run it. |
| **Upstream submission** | On hold since 2026-08-15. T5 establishes attribution and stops there. |
| **finding 047's re-round** | Needs *both* shell generations, and whether the pre-048 `dist/` is archived is unchecked. **T3 routes around it**: the `notice-action-recovers-the-session` oracle is generic and does not require 047's route. Re-judging 047 itself stays a separate round. |
| **E4 Markdown G0** | Cheap, but out of M1's scope, and the roadmap says running G0 ≠ authorising E4. |

---

## 2. The tasks

| | What | Why now | Needs |
|---|---|---|---|
| **T0** | The coverage registry's *reasons* must be able to expire | One reason is provably no longer supportable; the registry cannot notice | — |
| **T0.5** | **The Firefox arm is red** | Found by running it instead of assuming it; `make test-e2-c-product-path` fails today | browser |
| **T1** | Drive the uncovered product paths | Five defects were found this way (049, 050, 053, 054, 063); two undriven ones are *relink 2's own payload* | browser |
| **T2** | `cut`: measure range delete, then declare it | The only `partial`; it gates the deferred manual round. **Measured 2026-08-21: the remedy is engine-side, so this moved into T4** | browser |
| **T3** | Recovery's second inducer | Coverage is tied to upstream 038 staying broken | browser |
| **T7** | **D0, then re-freeze the matrix** | **M1's completion criterion, and the matrix is bound two relinks stale** | browser |
| **T4** | The ABI question, written up but not executed | Roadmap §10 item 1 — M1's only fork | — |
| **T5** | The 32,767 tile limit: read the source | The queue item says the 2^15 inference is *unread source* | — |
| **T6** | *(optional)* a11y gate 0's patch, prepared | The rebuild is the user's hours; a ready patch runs it in parallel with M1's tail | — |

### Ordering — the real dependencies, not the merge hazards

```
T0 ──▶ T1 ──▶ T2 ──▶ T7        T0.5 ──▶ T3 ──▶ T7        T4  T5  T6  (parallel)
```

* **T0.5 first, or in parallel with T0.** Everything downstream is judged by a
  two-browser baseline, and one of the two is red. A plan that adds checks on top
  of a red arm cannot tell its own regressions from the ones already there.
* **T0.5 → T3 (hard).** T0.5 establishes that recovery is *already* uncovered on
  Firefox; T3's inducer has to work on both arms, not just the one where 038 fires.
* **T0 → T1 (hard).** T1's order is chosen from the registry's risk notes. Re-judge
  the notes before acting on them.
* **T1 → T2 (hard).** T2 widens `delete-backward`'s gestures, which also flips the
  toolbar button's disabled state (`e2-editor-app.js:151-161`). T1's
  `delete-backward`/`delete-forward` checks must exist first, or that change is
  discovered instead of measured.
* **T2 → T7 and T3 → T7 (hard).** T7 re-freezes the five bindings; it must be last.
  T2 moves `manifestSha256` specifically — see T7.
* **T3 is independent of T1 and T2.** The first version claimed otherwise.
* **Not a dependency, a merge hazard:** T1/T2/T3 all edit
  `tools/run_e2_c_product_path.py`. The 08-18 plan's §8 trap is narrower than the
  first version said — it is *"new checks go after every check that takes a save
  by positional index"*. The fix is a rule, not a serialisation: **every new save
  takes its index from `SAVE_COUNT`, or goes after all existing positional ones**
  (`capture_save(…, 2)`, `…, 3`, `…, 5` at lines 1886, 1921, 2056).

---

## T0 — a reason that can no longer be supported must go red

### The problem

`e2/product-path-coverage.json` records a `risk` sentence per uncovered path. One
of them (`:164`) says `listener:click#clear-format` is not driven **because
finding 059 has all four inline formats failing on the shipped artifact**.

That reason was written against artifact `d538ce0b…`. The binding has moved twice
since (`296f3ea7…`, then `29ec627b…`), and 059's fix shipped in the first of
those. **The reason can no longer support itself**, and the audit still reports
`ok: true`, `highRiskUncovered: []`.

> **Stated carefully, because the first version overstated it.** What is proven is
> that the *reason* is bound to an artifact that is gone. It is **not** proven that
> the four formats now work on `29ec627b…` — no saved product-path report records
> a WASM hash at all (`run_e2_c_product_path.py:1662` writes `servedShell` only).
> Source is not artifact, in this tree by rule. T1 measures it; T0 only makes the
> staleness visible.

### Method

An **optional, typed** binding — not a blanket one.

```json
"reasonBoundTo": { "wasmSha256": "d538ce0b…" }
```

The audit goes **RED** when a named binding no longer matches the live value.
Re-affirming is a deliberate edit that re-states the hash — the same expectation-flip
discipline the queue uses for `absent` items.

**Typed, because product-path identity is five things, not one.** The matrix binds
`wasmSha256`, `loaderSha256`, `workerSha256`, `shellBundleSha256`, `manifestSha256`
(`validation-matrix-v2.json`, `whyFive`). A reason about engine behaviour binds to
the wasm; one about a worker allowlist binds to the worker.

**Optional, because most reasons are structural and must NOT be bound.**
`change#fixture` (reopening a document), `blur`, `resize`, `pointercancel`,
`open-file` forwarding are UI-shaped and do not expire when an artifact moves.
Binding all fourteen would manufacture a false expiry on every relink — the
first version of this plan asked for exactly that and was rejected for it.
`set-underline`/`set-strikethrough` carry a bare `LOW` with no artifact-dependent
excuse at all; they need no binding, they need **driving** (T1).

The hash is available and verifiable:

```
dist/profiles/e2-editor-v3/sdk-manifest.json   "wasmSha256": "29ec627bf8a5588b…"
sha256sum dist/profiles/e2-editor-v3/probe.wasm  29ec627bf8a5588b…
```

`tools/run_e2_c_d0.py:33` already computes profile hashes — reuse it, do not
rewrite it. **Finishing the 08-18 T0's other half — writing the artifact hash into
the product-path report — belongs here.**

### Acceptance

`--self-test` on synthetic data: stale binding red, current binding green, no
binding unchanged. Against the tree today it must go **RED on `click#clear-format`**;
if it passes on the first run the check is wrong
(`first-run-of-a-regression-net-is-the-measurement`).

---

## T0.5 — the Firefox arm is red, and nothing in the tree says so

**This was not in either version of the plan's scope. It came from running the
Firefox baseline instead of assuming it.** The handoff's green numbers — 22 checks,
21 PASS, 1 NOT_ESTABLISHED, `KNOWN_RED` empty — are a **Chrome** fact. Nothing
claims Firefox, and Firefox is `ok: false` today. `make test-e2-c-product-path`
runs both arms, so that target fails as it stands.

| Check | Firefox | What it means |
|---|---|---|
| `the-caret-is-drawn-where-it-was-placed` | **FAIL** — `caretAfterClickNearStart: 0`, `fractionNearStart: -0.229`, `fractionPastEnd: 1.002`, ink span 101→543 | Clicking near the start puts the reported caret at **x = 0**, outside the line's own ink |
| `ctrl-x-is-handled-by-the-product` | **FAIL** — `CLIPBOARD_DENIED`, `refusalReported: false`, `documentUnchanged: true` | Fails for a **capability gap**, not a defect: `clipboardPermission: {granted: false, why: "this browser session has no CDP"}` |
| `recovery-returns-what-the-product-promised` | **NOT_ESTABLISHED** (passes on Chrome) | The 038 inducer does not reproduce on Firefox — this is the loud-exit branch at `run_e2_c_product_path.py:3327` **firing today** |

### The three questions, and none of them may be guessed

1. **The caret: product or check?** Finding 060 fixed this check on 2026-08-18 by
   anchoring to the line's own ink — and its own reproduction row says
   **「Chrome 1/1（725×929 的畫布）；**Firefox 未量**」**. So Firefox is the browser
   060 never covered, and today it fails on the post-fix criterion. Settle it with
   **060's own method**: two roots, clean versus the `caret` mutation mirror,
   per-row dark-pixel diff. Do not name a layer without measuring it.
2. **Ctrl+X: the disposition is wrong even if the behaviour is right.** A check
   that cannot run because the browser has no clipboard must report
   `NOT_ESTABLISHED` **and name the capability**, not `FAIL`. As it stands a
   capability gap is indistinguishable from a defect, and the tree already knows
   what that costs — it is why the recovery check has a loud exit. Fix the
   disposition; the Chrome arm keeps measuring the real thing.
3. **Recovery on Firefox is already uncovered.** This is not a hypothesis about
   the day 038 gets fixed — it is the state on Firefox **now**. It moves T3 from
   "a resilience debt" to "a live hole on one of two supported browsers".

### Acceptance

Both browsers `ok: true`, or every remaining red is a **named** finding with a
`KNOWN_RED` declaration that a mutation shows can go green again. **First-run-red
is the measurement** — do not soften a criterion to make Firefox pass
(`Do not widen a check to close a row`).

---

## T1 — drive the undriven paths, newest defect surface first

| Order | Path | Why here |
|---|---|---|
| 1 | `set-underline`, `set-strikethrough` | **Relink 2's payload.** Proven today only at engine and cache level. The worker allowlist bit twice in one afternoon (handoff §4) |
| 2 | `set-italic` | 059's fix covered all four; only bold is driven |
| 3 | `click#clear-format` | T0's stale reason; dispatches `enabled:false` to all four — the *off* direction |
| 4 | `delete-backward`, `delete-forward` | Feeds T2; `delete-backward` is at the centre of finding 063 |
| 5 | `insert-line-break`, `move-character-left/right` | Covered through the shell by D1, never through the button |
| 6 | `change#fixture` | MEDIUM; the only product path near `queue-search-after-reopen-wedges` |
| 7 | `blur`, `pointercancel`, `resize` | Cheap |
| 8 | `click#open-file` | **Drive it, do not waive it** — see below |

### The oracle for the inline formats — *not* the paragraph-action pattern

**This is the correction that matters most in T1.** At a collapsed caret an inline
format leaves `<office:body>` **byte-identical**; it shows up only in text
committed afterwards. The matrix established this on 2026-08-15, *before* D1 ran,
and amended its own oracles for it:

> at a collapsed caret an inline format leaves `<office:body>` byte-identical and
> shows up only in text committed afterwards. The original oracle ('this anchor
> became bold') could not be satisfied at the gesture the [contract offers]

So the paragraph-action pattern the first version proposed — anchor to the target
paragraph's text, require neighbours to survive — **would pass on a no-op.** Use
the matrix's own method:

* each on/off arm commits a **unique marker** at the caret afterwards, and the
  oracle is the style of the span that marker lands in (`fo:font-weight`,
  `fo:font-style`, `style:text-underline-style`, `style:text-line-through-style`);
* **off as well as on** — on-only is what hid the toggle bug for weeks;
* `clear-format`: turn all four **on** first, then clear, then commit a marker, and
  require **none** of the four styles on it. Clearing an already-clear document is
  the no-op that must not pass;
* neighbour survival stays, but only as a damage witness, never as the verdict.

### `click#open-file` — driven, not waived

The first version proposed waiving it as "needs a human". **That was wrong**, and
it is the antipattern the registry exists to prevent. The path is one line:

```js
el.openFile.addEventListener("click", () => el.file.click());   // e2-editor-app.js:813
```

The runner already shims a `.click()` to count it instead of performing it —
`HTMLAnchorElement.prototype.click` for download anchors, `run_e2_c_product_path.py:178`.
The same technique on `#file.click()` drives the **forwarding**, which is the part
that is unproven; `change#file` continues to prove the actual open. No OS chooser
is opened and no human is needed. Mutations: delete the forwarding, and point it
at the wrong element — both must go red.

### Method

One path at a time, each with a mutation that must turn it red. **Expect
findings** — five product defects came out of exactly this move; do not fold a new
one in silently.

### Acceptance

`audit_product_path_coverage.py` reports **`uncovered: []` and `waived: []`**,
every new check has a reddening mutation, and both browsers stay clean.

---

## T2 — `cut`: measure range delete, *then* declare it

### T2.0 — no link needed, and the line that says so

`src/probe_engine.cpp:5736-5748`, at the gesture mask:

> The default is every class; the worker calls the setter once per action at init
> from the profile manifest, and **the setter INTERSECTS** — so a manifest can
> withhold a class this binary implements and **can never grant one it does not**.
> […] a manifest choice made after the artifact exists, **which is why neither
> needs its own link.**

No second caret-only gate exists: `sdk-worker.js:936-952` pushes `spec.gestures`
into the engine and re-checks only that the action exists (`:1181`);
`narrow-editor-v2-client.js:97` returns the manifest verbatim, documented as *"for
enabling buttons rather than for failing"*. Cut does not go through the toolbar —
`e2-editor-app.js:688` calls `session.action("delete-backward")` directly.

### T2.1 — the two range bits **cannot be measured separately**

**The first version's design was impossible, and the engine says so in a comment**
(`probe_engine.cpp:4364-4374`):

> An unclassified range must satisfy **BOTH** range bits, because
> `editorGesturePermitted()` accepts on any intersection: passing the OR of the two
> would let a profile that allows only range-single admit a range this build never
> classified […] Telling them apart needs the html read, and that read is the wedge
> risk findings 037/038 describe — so the check is conservative instead.

```cpp
collapsed ? editorGesturePermitted(action, kGestureCollapsed)
          : (editorGesturePermitted(action, kGestureRangeSingle) &&
             editorGesturePermitted(action, kGestureRangeCross));
```

Granting one bit alone refuses **every** range. Two arms designed that way would
both have measured the same refusal and been read as "range delete does not work".

**Corrected design: grant both bits together, and vary the actual selection
shape** — a single-paragraph range and a cross-paragraph range — since that is the
axis the engine does not classify and the product will actually produce.

### T2.2 — override in the **v3** builder, not the shared one

The first version proposed editing `build_e2_b_profile.action_map()`. That
rewrites the **frozen E2-B v2** profile's identity from the same code path, which
is precisely the failure that builder's own docstring was written against:

> The version of an allowlist is an identity, not a setting, and **"one path, two
> identities"** is how E1-C extended v1 in place while the freeze test kept pinning
> eight of ten actions.

`tests/test_e2_b_profile.py:78` pins it directly:
`test_v1_actions_stay_caret_only_under_both_dispositions`.

So: **override `delete-backward` inside `build_e2_c_profile.py`'s v3 `action_map()`**
(`:54`, `:92`), leaving v2's semantics untouched.

And **rebuild explicitly** — `e2-c-assets` does *not* depend on the v3 profile
manifest; the target is `Makefile:987`. "Change one place and the shipped profile
picks it up" is not true here.

### T2.3 — method

1. **`PREDICTION.md` first.** Thresholds before results.
2. **Measure on a diagnostic profile**, `probe.wasm` byte-identical to `29ec627b…`
   (the p1-3b withdrawal was measured this way). Do not rebuild between sweep and
   verdict (`wasm-build-not-reproducible`).
3. **One arm per fresh engine session** — the 08-19 trap was a sweep that carried
   state between arms and exonerated the engine wrongly.
4. **The oracle is the saved ODT**, not the revision counter: a revision that
   advanced proves a dispatch, not a deletion.
5. **Declare only if it measured true**: `RANGE_DELETE_CHARACTERISED` in the v3
   builder naming the evidence path, gesture widened, `queue-cut-cannot-remove-text`
   flipped, the cut check extended to assert the text is **gone**, row `cut` → `done`.
6. **If it measured false**, that is a result too: the row stays `partial` with a
   *measured* reason, and "an action that deletes a selection" joins T4. Do not
   widen the manifest to close the row (handoff §5).

### Acceptance

`check_e1_c_bundle_intact.py` green; **the v2 profile's bytes unchanged**;
`dist/profiles/e2-editor-v3/probe.wasm` still `29ec627b…`; `test_e2_b_profile.py`
still green; the mutation that reverts the gesture reddens the cut check. Note the
clipboard permission is **Chrome-only** here, so the Firefox arm measures the
refusal path, not the removal.

---

## T3 — a second inducer that does not depend on an unfixed bug

Two checks, two different debts — the handoff's §3 puts both under 038:

| | |
|---|---|
| `recovery-returns-what-the-product-promised` | **Passes.** Its inducer is upstream finding **038** staying broken (`queue-recovery-inducer-depends-on-an-unfixed-defect`) |
| `notice-action-recovers-the-session` | **`NOT_ESTABLISHED` in today's baseline.** Its `why` (`run_e2_c_product_path.py:2093`) names finding **047**, not 038 |

> Say *"today's baseline's only NOT_ESTABLISHED"*, not *"the tree's only one"* —
> `run_e2_c_product_path.py:3327` carries a second NOT_ESTABLISHED branch for when
> the 038 inducer fails.

### The inducer: short-timeout `selectRange`. Not worker termination.

Only one of the two candidates serves both oracles:

* `notice-action-recovers-the-session`'s oracle is **generic** (`:2113`) — a
  dispatched failure blocks the queue, the notice is offered, pressing it returns
  the session to `ready`, and a save works afterwards. It does *not* require 047's
  route, so a second inducer can establish it.
* `recovery-returns-what-the-product-promised` carries a **capability clause**
  (`:3316`, fable's 2026-08-18 adjudication): the inducer must be a **selection
  gesture on a dirty document**. `selectRange(…, {timeoutMs})` satisfies it — the
  session checkpoints first, then passes options through (`editor-session.js:455`).
* **Terminating the worker does not**, and it is **not public API**: `_worker.terminate()`
  is private, reached only inside `restart()`/`dispose()` (`document-sdk.js:333`).
  At most it is a second recovery-machine control; it cannot close the first check
  and must not be described as public.

**Verification obligation first** (finding 037's lesson, and the queue item states
it): show the shape lands in `recoverable-error` rather than being refused by name.
And beyond the state string — measure that the notice is **shown**
(`#notice[data-rescue]`), because the oracle requires the button to be *offered*.

**A supplement, never a replacement.** It measures the recovery *machine*; the 038
route measures the user's route *into* it. The existing inducer stays.

**And it must work on both arms.** T0.5 measured `recovery-returns-what-the-product-promised`
as `NOT_ESTABLISHED` on Firefox today — 038 does not reproduce there. So on one of
the two supported browsers the recovery coverage is *already* gone, and an inducer
that only fires on Chrome would leave it that way.

### Acceptance

`INDUCE_RECOVERY_WITHOUT_A_DEFECT` in the runner, both inducers run,
`recovery-returns-what-the-product-promised` passes without 038,
`notice-action-recovers-the-session` stops reporting `NOT_ESTABLISHED`, queue item
flipped with the evidence path. If it still cannot be established it must say so
**and name why** — a check that goes quiet is worse than one reporting
`NOT_ESTABLISHED`.

---

## T7 — D0, then re-freeze the matrix

**The first version excluded D0 and was wrong to.** The roadmap's M1 completion
criterion is *清單全綠 ＋ 每個 done 的檢查綠 ＋ 沒有 blocked ＋ **D0 跑完、矩陣凍結***.
A plan called "close M1" cannot drop one of the four.

The old reasoning — *"once D0 runs, moving the shell means changing the matrix"* —
is an argument for running it **last**, not for never running it. And the matrix is
already stale in exactly that way:

| | frozen (2026-08-17) | today |
|---|---|---|
| `wasmSha256` | `d538ce0b…` | **`29ec627b…`** |
| `shellBundleSha256` | `e48685976e…` | **v25 `07143f96…`** |
| status | `frozen-before-D0` | still |

**T2 moves a third one.** The matrix's own `whyFive` note says `manifestSha256` was
added as a binding precisely because *"this round changes semantics that live in
`sdk-manifest.json` itself — abiVersion, limits, **gestures**, and the gesture mask
the engine pushes in at init"*. T2 changes gestures. So T7 must follow T2.

D0 is autonomous: `tools/run_e2_c_d0.py` takes `--browser chrome|firefox`,
`--profile`, `--matrix`, and computes the profile hashes itself (`:33`, `:43`).

**Method:** after T1/T2/T3 land, re-derive all five bindings, update the matrix,
run D0 on both browsers against the v3 profile, then freeze — `frozenDate` set,
status off `frozen-before-D0`. Re-freezing is a deliberate edit that re-states
every hash, not a refresh.

---

## T4 — the ABI question, costed but not executed

Roadmap §10 item 1, and the handoff's *"ask before starting"*. Four things want
wire ids past 15 — `EDITOR_V2_ACTION_IDS` uses 1–15 exactly (`sdk-worker.js:65-72`):

| | Today |
|---|---|
| `redo` | `blocked`. Engine dispatches `.uno:Redo`; no wire id |
| `move-by-line` (↑↓/Home/End) | `blocked`. Engine postKeyEvents them; its own enum numbers move-line-up as **3**, which is `delete-backward`'s product id — that collision is how the numberings got confused |
| `select-all` | Deliberately unbound; the geometric substitute was **measured selecting nothing** |
| *(possibly)* delete-selection | Only if T2 step 6 |

It is a link either way: the worker intersects too — *"a manifest can withhold an
action this worker knows how to dispatch, and can never add one"* (`:79-86`) — and
the id→internal mapping is compiled in.

**Deliverable: the proposal, not the change.** Exact ids, engine mapping, manifest
entries, the SPEC E2-C 4.2 revision (both are under 明確不承諾 today), and what each
row buys. It does not touch the shipped contract.

### Adjudicated by fable, 2026-08-21 — and my leaning was wrong

I leaned toward *version the contract*, on the grounds that M5 needs a different
action set anyway. **That argument does not hold, and the roadmap says why.** The
id space is scoped by operation name and capability (`sdk-worker.js:140-148`), and
roadmap §8 says each app runs its own discovery → narrow contract → validation
(「每個 app 各自走一次」). So Calc's contract will be a **sibling** minted from its
own discovery round, never a successor of the Writer one. Appending Writer actions
to the Writer contract welds nothing into anyone else's future — and designing a
successor now would mean writing a contract *ahead of* discovery data, which this
project has never done.

**But appending in place is also not what this tree does.** Its precedent is
v1→v2: mint a **successor identity**, inherit ids 1-10 verbatim, append 11-15, and
gate it with the exact-match ABI handshake that fails a mismatched profile at init
(`sdk-worker.js:63-72`, `:925-930`). Done that way, "extend" *is* "version":
`abiVersion` 3→4, a successor builder, frozen v2/v3 bytes untouched.

**The four capabilities are four different kinds of thing** — this matters more
than A-versus-B:

| | What it actually is |
|---|---|
| **`redo`** | **Not a wire-id problem at all.** Undo never touches the editor contract: `e2-editor-app.js:499` → `session.undo()` → `document-sdk.js:482` `_request("undo", …)`, a top-level SDK operation with its own capability (`sdk-worker.js:32`). **Verified.** Redo's home is a sibling operation — still a link (a new compiled export), but **zero wire ids**. `queue-redo-and-line-movement-need-wire-ids` and the checklist `redo` row are both wrong about the reason |
| **`move-by-line`** | The genuine append. Four caret actions, ids 16-19; `extendSelection` already exists for move-character-left/right (`editor_api.cpp:59-62`) |
| **`select-all`** | **Different in kind.** Not even in the discovery map (`sdk-worker.js:102-122`, 19 actions, no select-all) — never dispatched through any ABI here. And the corpus holds a **measured** full-select wedge (`SPEC-E2-C…:502`, 「不要用它」) sitting on 038's select-then-read fault line. Needs discovery-grade characterisation first |
| **`delete-selection`** | Contingent on T2 |

**The move the intersection design was built for:** ship the engine half for
select-all (and delete-selection if needed) in the link and **withhold it in the
manifest** until characterised. The grant is then a manifest edit needing no link.

**Timing: not a link for these ids alone.** The next link's cargo already exists
(a11y honesty, marked "ride along with the next one"; the tile-limit refusal after
T5), and the governing precedent is 2026-08-16's `linkDecision: WAIT`. Also —
**no link can be judged at all while the Firefox arm is red** (T0.5): the 08-19
double link only worked because the net was green when the surprises landed.

### Can M1 close with `blocked` rows?

**Not as the criterion is written.** Roadmap §2 says 清單全綠 ＋ 沒有 `blocked` ＋
D0 跑完、矩陣凍結. But that document self-describes as 「排序與理由，不是規格…不構成
執行授權」 and lists this exact fork in §10 as undecided — so the criterion is
*pending this decision*. Two honest closes:

1. **Do the link** as M1's third, or
2. **Revise the criterion explicitly** — a roadmap revision-log entry that
   re-scopes the rows out of M1 and names their destination.

What the project's own discipline forbids is shipping with the criterion as-is and
calling it green (`Do not widen a check to close a row`).

**If revised, `move-by-line` should be re-scoped into the a11y milestone, not
"later"** — the buyer is institutional, the a11y rationale is procurement gates,
and moving the caret by line without a mouse is exactly what keyboard-operability
audits test. An editor failing it would fail that milestone's purpose.

### What would flip this

A shared cross-app action namespace anywhere in the plan (today the repo says the
opposite); a11y gate 0 failing (removes the carrier link); or T2 measuring true
*and* the user judging redo + line movement not worth a link — in which case
explicit criterion revision becomes the only honest close.

### Follow-on work this creates (autonomous, small)

**Correct the reason in two places**, the way the 08-18 plan's T1.0 corrected 059's
`wasModified` before measuring anything: `queue-redo-and-line-movement-need-wire-ids`
and the checklist `redo` row both say redo needs a wire id. It does not. The
verdict (`blocked`, needs a link) survives; the reason does not.

---

## T5 — read the source before the 32,767 wall is called ours

`queue-engine-reports-success-for-an-unpainted-tile`:

> WHERE in the engine is not established: that a 2^15 boundary is a signed 16-bit
> quantity is **an inference from the number** and **no source at that point has
> been read**.

Confirmed: finding 062 cites no core source at all. Pure archaeology in
`libreoffice-26-8/` — no build, no browser, an objective answer. **Delegate to codex.**

Facts it must explain: 45 MB paints at height 32,767 and 45 MB is blank at 32,768,
so it is the height not the memory; the buffer returns exactly `width × height × 4`
bytes; `ImageData` builds; nothing throws.

**The governing rule**: *do not name a layer without measuring it* (040, 048, 062).
If the source does not settle it, the output is **"still not established"**, not a
better guess. Submission stays on hold. If any output lands under
`findings/evidence/**` it is **English** (`AGENTS.md`).

---

## T6 — *(optional)* a11y gate 0's patch, prepared for the user's hands

Beyond the handoff, included for one asymmetry: **the rebuild costs the user's
hours, not mine.** The roadmap puts a11y immediately after M1 and calls its gate 0
the highest-uncertainty question in the plan — *"WASM 上的 LOK accessibility 到底能
不能用" 完全沒有量過*. A ready patch lets it run in parallel with M1's tail.

Prepare three things, run none:

1. **The patch.** Finding 057 located two directions — make the `AC_DEFINE` follow
   the module decision (`configure.ac:4372/4379/4386`), or make `:1280`'s
   unconditional-yes-on-Emscripten defer to an explicit choice (`:3498`). Pick one,
   with the reason.
2. **The probe** for gate 0's single question: does LOK emit a focused paragraph on
   WASM.
3. **The pass/fail criterion, written before the result.**

Explicitly **not** the fix: adding `calc` back to `--with-wasm-module` — 057 already
rejected it (objects compiled in, call sites still removed by the macro).

Say the word and this is dropped; it is the one item the handoff does not ask for.

---

## 2.5 Execution log (2026-08-21, written as it happened)

**T0 — done.**

* `audit_product_path_coverage.py` grew an **optional, typed** `reasonBoundTo`
  rule. `live_bindings()` computes `wasmSha256`, `loaderSha256`, `workerSha256`
  and `manifestSha256` **from the files themselves**, importing D0's
  `artifact_hashes()` rather than reimplementing it — so a reason and the matrix
  cannot drift apart by being hashed two different ways. It never reads the
  profile's own manifest for a hash: a manifest that merely *claims* one is what
  this tree has been bitten by.
* Self-test **12/12** (was 7). Five new cases, each isolating its own axis:
  pinned-to-a-gone-artifact goes red, pinned-to-current does not, an
  unevaluatable key goes red, a bare string is rejected, and no-pin is judged
  exactly as before.
* The self-test's first case was **split**: the ACCOUNTING rule
  (`paths - driven - waived` empty) and the EXPIRY rule now fail separately, so
  a declared expiry can never make the audit stop noticing an unaccounted path.
* `listener:click#clear-format` pinned to `wasmSha256 d538ce0b…`. **The audit
  now exits 1 on the first run**, naming the expiry —
  `first-run-of-a-regression-net-is-the-measurement`. This red is expected and
  stays until T1 drives the path.

**T0.5 — in progress. One defect already established, and it is not the failing check.**

Both caret checks read the same measurement (`caret_from_columns`, `:1217-1256`):
two reads of one band, the column that *gains* ink is the caret's second
position, the one that *loses* it is the first.

| | Chrome | Firefox |
|---|---|---|
| `strokeGained` / `strokeLost` | 19 / **15** | 24 / **0** |
| `fractionNearStart` | -0.006 | **-0.229** |
| `the-caret-is-drawn-where-it-was-placed` | PASS | **FAIL** |
| `the-caret-lands-where-the-click-was` | PASS | **PASS** |

`strokeLost: 0` means **no column lost ink** - the caret was never located in the
first read. `lost` is then `argmin` over an all-non-negative array, which returns
**index 0 by tie-break**, and `fractionNearStart` is computed from it anyway:
`(0 - 101) / 442 = -0.229`.

**So the FAIL is honest and the PASS is not.** `the-caret-lands-where-the-click-was`
requires `near < 0.25`, and -0.229 satisfies it *because the caret was not found*.
The check passes on a tie-break artifact. That is the shape this tree keeps
paying for - finding 046's `checked:false` meaning "something else answered
first", 059's `success` field anti-correlated with success - and it is worse than
the red one, because a red says something.

**Fix (T0.5): `strokeLost == 0` is `NOT_ESTABLISHED`, not a position.** The
oracle already declares the sibling limit out loud ("a caret pinned to a constant
column reads the same as one that is never drawn"); this one was undeclared.

**The `--mutate caret` control on Firefox came back, and it does NOT prove the
above - it proves something narrower and more useful.** With the caret draw
turned off entirely: `gained 0 / lost 0`, `near = past = -0.2285`, and **both**
checks FAIL - `the-caret-lands-where-the-click-was` is saved by its `past > 0.75`
clause, which a tie-break `past` cannot satisfy.

So the oracle is not defenceless against "no caret at all". It is defenceless
against exactly one state: **caret drawn on the second click but not the first**,
where `past` is real and `near` is a tie-break. That is the state Firefox is in
at baseline, and **no mutation in the suite produces it** - which is precisely
why the suite never caught this. A new mutation that suppresses only the FIRST
placement is what would red it, and writing that mutation is part of the fix.

| Firefox arm | gained / lost | near / past | verdicts |
|---|---|---|---|
| baseline | 24 / **0** | **-0.229** / 1.002 | drawn=FAIL, lands=**PASS** |
| `--mutate caret` | 0 / 0 | -0.229 / **-0.229** | both FAIL |

**The oracle fix landed.** `caret_from_columns` now reports a fraction **only
when the read it comes from actually found the caret**; `None` means "not found",
never "column zero". The two checks are treated differently on purpose:
`the-caret-is-drawn-where-it-was-placed` keeps the strokes as its subject and
keeps FAILING (that is finding 058 - a product that draws no caret at all must
not be able to make this check abstain), while
`the-caret-lands-where-the-click-was` withholds a position it cannot support and
reports `NOT_ESTABLISHED`.

Proven with `tests/test_caret_from_columns.py` - a **unit test, not a page
mutation**, because the triggering state (caret drawn on the second click only)
is one no mutation in the suite produces. 7 cases, wired into
`test-e2-c-static`. Run against `HEAD`'s pre-fix implementation, **4 of the 7
fail**, including the Firefox one; the 3 that pass are the behaviours the fix did
not change. A check that cannot fail is not a check.

**Found while wiring that in: `make test-e2-c-static` was ALREADY RED at HEAD**,
before anything in this plan was touched. `test_make_owns_the_dist_copy_of_every_bound_module`
fails on `dist/editor-shell/recovery-notice.js` - the shell bundle binds it, a
copy rule exists (`Makefile:1791`), another target lists it (`:343`), and
`e2-c-assets` never learned to own it. It works today only because a *different*
target puts the file on disk. That is the ownership half of the same trap the
handoff §4 records the exclusion half of, and it has been red since the page
began importing the module. **Fixed** - one prerequisite line; the file was
verified byte-identical to its source, so no run was served a stale copy.

Verified pre-existing by stashing the Makefile change and re-running: still red.

**Not yet established, and it must not be guessed** (040, 048, 062): *why* the
caret is absent from Firefox's first read. Ruled out already - **the caret does
not blink** (no `setInterval`/`requestAnimationFrame` for it in
`web/e2-editor-app.js`), so a missed blink phase is not it. Still open: whether
the first `placeCaret` completes at all on Firefox, and whether
`wait_for(... "定位游標" in latency ...)` can be satisfied by a **stale** latency
string from a previous placement.

**The mechanism for that is now confirmed to exist** (`web/e2-editor-app.js:377-382`):
`run(label, op)` writes `"<label> NNN ms"` into `#s-latency` only after the
operation resolves *and* `renderDocument()` completes - but it **never clears it
first**. Earlier steps place carets (the recovery block records
`"caret": "定位游標 35 ms"`), so by the time the caret block runs, the predicate
is already true and `wait_for` returns without waiting for the new placement.
The 1.0 s sleep then has to cover the whole round trip on its own.

**PREDICTION RECORDED FAILED.** The controlled arm - clear `#s-latency` before
each click, so the wait means what it says - changed **nothing**:
`gained 24 / lost 0`, and `fractionPastEnd` came back bit-identical
(`1.002262443438914`). The stale predicate is real and the fix is kept on its own
merits, but it **was not the cause**.

### The cause, and it is not the product

One variable, one arm: move the FIRST click from `x = 0.06` to `x = 0.20`.

| Firefox, first click at | gained / lost | fractionNearStart |
|---|---|---|
| `0.06` (three runs) | 24 / **0** | withheld |
| `0.20` | 24 / **19** | **0.170** |

**The caret is drawn on the first click.** `the-caret-is-drawn-where-it-was-placed`
failing on Firefox is **not a product defect** - it is the check's hardcoded
click fraction interacting with canvas geometry.

The arithmetic is consistent with the caret hiding inside the line's own first
glyph: `fractionNearStart = (lost - 101) / 442` puts `lost` at column 176 for
`x = 0.20`, so the canvas is about 880 px wide and `x = 0.06` is column ~53 -
**left of `inkLeft = 101`, in the margin**, where the engine snaps the caret to
the line's first character and it lands on top of ink that is already dark.

> **Not established, and deliberately not asserted:** why `0.06` separates on
> Chrome (725 px canvas, `lost 15`) and not on Firefox (~880 px). The geometry
> above is consistent with it; it is not a measurement of it. Naming the
> mechanism would be 040/048/062 again.

**This is finding 060's third incarnation.** 060 fixed the *band* being a
viewport fraction by anchoring it to the line's own ink. The **click position is
still a hardcoded viewport fraction**, and whether the caret is separable from
the glyph at that fraction depends on the canvas width, which depends on the
browser window. Same defect, one layer along.

**Remedy, implemented.** `LINE_INK` reads the band once, `caret_click_fractions()`
puts the near click at `inkLeft + 0.12 x span` and the far one just past
`inkRight`, both converted to canvas fractions, and the chosen positions are
recorded in `observed.clickedAt` - a verdict whose input is derived must show the
derivation. Both caret checks now PASS on **both** browsers.

**One thing was tried and made it worse, and the reason generalises.** Aiming the
near click at the *sparsest* column in the line's first quarter - targeting the
mechanism rather than an offset - took Chrome from `strokeLost` 2 to **1**.
Reverted. The harness chooses where it **clicks**; the engine chooses where the
caret **lands**, and it lands on a character boundary, which is adjacent to glyph
ink by definition. **A gap in the ink is not a gap the caret can occupy.**

**Residual limit, now declared in the oracle** rather than left implicit: the
caret is 1 px and sits next to glyph ink by construction, so `strokeLost` can be
small - 19 on Firefox, 2 on Chrome at the same derived position. A margin, not a
cliff. The robust alternative is differencing a clean root against the `caret`
mutation mirror, which is how 060 was actually diagnosed; it costs a second page
load and is not run per round.

**And the Ctrl+X disposition, the second of T0.5's three questions.** The
clipboard grant needs CDP and the Firefox session has none, so the copy half is
denied by the **driver**, the delete half never runs, and the refusal the check
exists to verify (finding 063) cannot be produced. It was scored a product
**FAIL**. It now reports `NOT_ESTABLISHED` naming the capability - the same loud
exit the recovery check has. A browser the harness cannot drive must not be
indistinguishable from a product that broke.

### T0.5 result

| | before | after |
|---|---|---|
| Chrome | `ok: true`, 1 not established | `ok: true`, 1 not established |
| **Firefox** | **`ok: false`** - 2 FAIL, 2 not established | **`ok: true`** - **0 FAIL**, 3 not established |

Every remaining Firefox abstention is named: `notice-action-recovers-the-session`
and `recovery-returns-what-the-product-promised` are **T3's work** (038 does not
reproduce on Firefox, so recovery coverage is already gone on one of two
supported browsers), and `ctrl-x-is-handled-by-the-product` is the CDP gap.

**No product defect was found.** Both Firefox reds were the harness measuring
badly and reporting confidently.

---

**T1 - in progress. The first four paths driven found a HIGH-severity product
defect, which is what this task existed to do.**

Driven so far: `set-italic`, `set-underline`, `set-strikethrough`,
`listener:click#clear-format` - and `set-bold`'s document side, which was
already "driven" but only through `aria-pressed`. Uncovered is down from 14
to 10, and **T0's declared red is retired by driving the path**, not by
re-pinning it.

### finding 064 - an inline format set in the product never reaches the text you type

Press B/I/U/S at a collapsed caret, type through the product's own insert
field, save: **the marker carries no format. Four formats, both directions,
eight arms, all of them.** No disabled button, no error toast, session `ready`,
revision advancing every time - every surface the product has says it worked.

**Attributed, not guessed** - the rule 040/048/062 exists for. D1's own harness,
run on the **same artifact `29ec627b`** and read by the **same
`inline_styles_of()`**, gets all eight arms right:

| | bold | italic | underline | strikethrough |
|---|---|---|---|---|
| `D1BOLDON` / `D1ITALON` / `D1UNDRON` / `D1STRKON` | **true** | **true** | **true** | **true** |
| the four `…OFF` markers | false | false | false | false |

So the engine has not regressed, the oracle is correct, and the defect is on the
**product path**. That is `harness-path-vs-user-path` exactly: D1 drives the
shell client, the product drives its own handlers, and only one of the two had
ever been asked. The mechanism is **not established** - the candidate is the
`renderDocument()` the product's `run()` performs between the format and the
typing, and it has not been measured.

**Why it survived this long, measured in the same run:**
`bold-can-be-turned-off-again` is **green** - `aria-pressed` goes
`false -> true -> false`, correctly - while `MKBOLDON` and `MKBOLDOFF` carry no
bold at all. The page's cache is written correctly and the document is never
touched, and that check only ever looked at the cache. **A `done` row resting on
a check that cannot see the defect** - finding 044's shape, one layer along.
`turn-formatting-off` is therefore back to **`partial`**, citing 064.

### Two measurement traps this cost, both worth carrying

**A format press at a collapsed caret restyles the run the caret is in.** The
first version committed all six markers at one position; they coalesced into a
single `<text:span>` and every later press restyled the earlier markers, so only
the last arm's state survived. The tell was the **explicit** `fo:font-style="normal"`
and `style:text-underline-style="none"` - absence of formatting does not spell
itself out. Fix: one paragraph per arm.

**ODF does not spell underline and strike as booleans.** They are line *styles*
whose off value is the literal string `"none"`, so an oracle asking whether the
attribute is PRESENT reads an explicitly-turned-off underline as underlined -
and that is precisely the direction relink 2 shipped and nothing had driven.
Pinned by `tests/test_inline_styles_of.py` (9 cases).

### The rest of T1 - ten more paths, and one check that had to be un-claimed

**Driven and passing:** the five edit BUTTONS (`delete-backward`,
`delete-forward`, `insert-line-break`, `move-character-left/right`),
`listener:click#open-file`, `listener:resize`, `listener:change#fixture`.
Each has a mutation that reddens it and only it.

**`click#open-file` passes** - so codex was right and v1's proposed waiver was
wrong. Shimming `#file.click` to be counted rather than performed drives the
forwarding with no OS chooser and no human; `open-button-forwards-nowhere`
reddens it.

**Two corrections the runs forced, both of them mine, not the product's:**

* The edit-button sequence first read `EDITBTNABCXD` **plus the tail of the
  paragraph it had split**. The core string was exactly right - all five
  buttons work. Relaxing the oracle to `startswith` would have destroyed the
  separability the whole sequence is built on (a `delete-forward` no-op yields
  `EDITBTNABCXDE…`, which still starts with the wanted string), so the SETUP
  was fixed instead: break at a **line end** so the new paragraph starts empty.
* The sample picker compared a doc name against a picker VALUE - `plain-grapheme.odt`
  vs `plain-grapheme` - so the wait burned its full timeout on a switch that had
  already happened; and it sampled ink at one hardcoded band, which reports a
  perfectly drawn document as blank when the sample puts its text elsewhere.
  **Finding 060's mistake, nearly made twice in one day.** Ink is now found
  anywhere via `stable_bands`.

### `blur` and `pointercancel`: registered back as UNCOVERED, on purpose

`an-aborted-gesture-stops-selecting` was written, and its first mutation run
**left it green with `pointercancel` unwired entirely**. The reason is the trap
the handoff names: the drag had never started, so a selection that never
extended proved nothing - *unreachable rather than untested, and it looks green*,
walked into on the day it was quoted.

A **positive control** was added - a drag with no abort, which must extend the
selection - and it fails on all four gesture shapes tried: split `evaluate()`
calls, a one-script mid-gesture abort, `LINE_INK`-derived coordinates, and the
`stable_bands` derivation the copy and cut drags use. So the check now
**abstains** rather than passing.

The observable is what is missing, not the gesture: copy and cut **do** produce
a range at their own named line. Reading it back through `button.disabled` is
what has not been made to work; the next step is the copy path's `codePoints`.

Two consequences, both deliberate:

* those two paths went **back to `uncovered`** with the measurement written
  down. A path is not driven by a check that cannot fail.
* `gesture-abort-not-wired` is declared **`expectedToBeDetected: False`** with
  its reason, so the limit lives in the evidence instead of in somebody's head -
  and the runner will say the declaration is stale the day the control works.

**`uncovered` is therefore 2, not 0.** T1's acceptance said `uncovered: []`;
that is not met, and saying so is cheaper than the alternative.

### State after T1 so far

| | |
|---|---|
| Chrome | `ok: true` - 1 known red (064), 2 not established |
| Firefox | `ok: true` - 1 known red (064), 4 not established |
| static tests | 56 pass |
| coverage audit | **green**, `staleReasons: []`, **32 driven / 2 uncovered / 0 waived** (was 20/14/0) |
| checks in the runner | **29** (was 22) |
| checklist | `ok: true` - 12 done, **2 partial** (`turn-formatting-off`, `cut`), 2 blocked |

---

**T2 - measured, and the answer moves the item out of this plan's scope.**

`PREDICTION.md` was written first. Then, with **both** range bits granted to
`delete-backward` in a **mirrored** manifest (`dist/` never written,
`probe.wasm` byte-identical to `29ec627b`, report stamped
`evidenceClass: "diagnostic"`):

| | Prediction | Outcome |
|---|---|---|
| P-CUT-1 | the gesture refusal disappears | **HOLDS** - `EDITOR_FORMAT_GESTURE_UNSUPPORTED` gone |
| P-CUT-2 | the range is removed from the saved ODT | **NOT ESTABLISHED** |
| P-CUT-3 | the session survives | **FAILS** - `recoverable-error` |

```
剪下：EDITOR_STATE_UNAVAILABLE：selection barrier requires a
      callback-confirmed collapsed caret
儲存：EDITOR_NOT_READY：editor operation save is unavailable in recoverable-error
```

The mask lets the dispatch through and the **selection barrier** refuses instead
- it is built for a callback-confirmed *collapsed* caret. So the queue item's
diagnosis is confirmed **and** its own warning is vindicated by measurement
rather than by argument: *"The fix is not simply to widen the manifest."*

**Whether the engine can remove a range is still unknown** - the barrier refused
before any deletion was attempted, and the save that would have answered it was
refused too.

### The consequence for this plan

`queue-cut-cannot-remove-text` said **"NOT a link either way -- gestures are a
manifest choice"**. That is now **superseded**: both remaining remedies -- a
barrier that can confirm a RANGE, or a distinct delete-selection action -- are
engine work.

**So `cut` is no longer no-link work.** It moves next to `redo`,
`move-by-line` and `select-all` in T4's proposal. The roadmap's M1 §2 lists
「剪下真的能刪」 under 不需連結; **that line is wrong, and this is the measurement
that says so.** The row stays `partial` with a measured reason.

### One more artifact of the same family, caught in the same hour

The first version of this record reported `targetStillPresent: false`,
`neighboursSurvive: false`, `linesAfter: 0` -- **from a save that never
happened**. `after_texts` was `[]`, so every "is it still there" question
answered "no", and the record read as *the cut deleted the whole document*. It
meant *nothing was measured*.

That is the caret oracle's tie-break, **the same day, in a record I wrote after
fixing the first one**. The recording now guards on `documentReadableAfter` and
returns `null` with a named reason. A question asked of missing data must return
null, not a value - and knowing the rule is evidently not the same as not
breaking it.

The `--range-delete-diagnostic` flag stays: it is the cheapest way to re-ask this
after any engine change, and it writes its own evidence class.

### State after T2

| | |
|---|---|
| Chrome / Firefox | both `ok: true`, no unexplained failures, diagnostic stamp absent on normal runs |
| static tests | 56 pass |
| coverage audit | green, 32 driven / 2 uncovered / 0 waived |
| checklist | 12 done, 2 partial (`turn-formatting-off`, `cut`), 2 blocked |
| queue | 15 open, **0 blocking** |

---

**T3 - no inducer found. Three candidates eliminated with evidence, and two of
the queue item's own claims corrected.**

The verification obligation was honoured first and **nothing was wired into the
regression net**. Probe: `tools/probe_second_recovery_inducer.py`, stamped
`evidenceClass: "diagnostic"`.

| Candidate | Outcome |
|---|---|
| `selectRange` with a short `timeoutMs` | **Not reachable.** The product constructs its session **without** `selectionTimeoutMs` (`web/e2-editor-app.js:762`), so it defaults to 5000 (`editor-session.js:84`). Reaching it means putting test-only configuration into the product |
| terminating the worker | **Not public API** - `_worker.terminate()` is private, reached only inside `restart()`/`dispose()` (`document-sdk.js:333`) - **and not a selection gesture**, so it cannot satisfy the capability clause either |
| a whole-canvas drag in a long, dirty document | **Did not reach** `recoverable-error`: 40 pages -> 160 ms, 200 pages -> 401 ms, notice never offered |

**The queue item said both of the first two were "reachable through public API".
That is wrong, and the item is corrected.**

### The third arm is a WEAK elimination, and it says so

It does **not** establish that a range was selected at all. The reported latency
is `定位游標` - **placeCaret's**, not the selection readback's. The pre-gesture
checkpoint fired (`有（r1）`), but that is the shell's bookkeeping, not the
engine's answer. So what is supported is only *"the session did not enter
`recoverable-error`"*, **not** *"the selection did not time out"*.

**That is the third check today that needed a positive control and did not have
one** - after the caret oracle's tie-break and the aborted-gesture check whose
mutation stayed green because the drag had never started. The page count was
**not** escalated further: putting a bigger number on an arm that cannot show it
exercised the mechanism is how a measurement that never happened acquires a
figure.

Recorded in `probe-measurement-discipline`, because knowing the rule was
evidently not enough to stop me breaking it three times in one day.

### Where the item stands

**Open, narrowed.** The remedy is now one of: make the selection timeout
configurable (which should be argued, not assumed); find a route this round did
not think of; or accept the dependency and say so where the checklist can see
it. The check still reports `NOT_ESTABLISHED` and names 038, so the loud exit is
intact and nothing regressed.

**Next step before any retry:** give the probe a positive control that reads the
**engine's** answer - the copy path's `codePoints`, which the runner already
uses.

---

**T7 - done. D0 passes on both browsers, and the guard is what made it possible.**

The matrix was frozen 2026-08-17 against artifact `d538ce0b`. `e2_c_matrix_entry.py`
**refused to start a browser**, naming three stale bindings. That refusal is
recorded as the guard working - external review named the window between a relink
and a freeze, on 2026-08-16, as the one place round one's mistake could repeat,
and this is it catching exactly that window four days later.

All five bindings **re-stated** (re-freezing is a deliberate edit, not a refresh),
before/after pairs in the matrix's own `refreezeLog`. `manifestSha256` moved
because the 08-19 relink changed what is *in* the manifest - the reason SPEC E2-C
11.3 bound it as the fifth identity.

**D0: `pass: true`, `problems: []` on Chrome and Firefox**, judged by
`analyze_e2_c_d0.py`, not by reading raw output. Evidence installed at
`findings/evidence/sdk-e2/e2-c-validation/d0/e2-editor-v3-29ec627b/` - a separate
namespace from round one's `e2-editor-v2-572035ac`, so neither can overwrite the
other. No shell or profile file was touched this round, so this D0 binds the same
artifact the day's other measurements were made on.

**T4 - written, not executed.** `research/PROPOSAL-2026-08-21-abi-revision.md`
(zh-TW: it is decision material for the user). It carries fable's adjudication -
**my leaning toward "version the contract" was wrong**, because roadmap section 8
says each app gets its own sibling contract, so appending welds nothing - and the
correction I verified myself: **`redo` is not a wire-id problem at all**
(`session.undo()` -> `document-sdk.js:482` `_request("undo")`, its own SDK
capability). The four blocked things are four different kinds of thing, `cut`
joined them by measurement, and the recommendation is this tree's own v1->v2 move:
a successor identity that inherits and appends, gated by the exact-match ABI
handshake. Timing: **not a link for these ids alone**.

**T5 - ESTABLISHED, and the inference the queue item forbade asserting was wrong.**

Delegated to codex, then **the crux re-read directly before accepting it**. The
32,767 wall is Cairo's explicit image-surface size check
(`cairo-image-surface.c:59`), and its own comment gives the reason: **pixman
coordinates are 16.16 fixed point**. `pixman_fixed_t` is `int32_t`. **Not a signed
16-bit height, not an overflow**, and it applies to width equally - our widths
were simply always under it.

Why it reports success: Cairo returns a nil/error surface and drawing on one is a
documented no-op; SVP **does** catch it (`svpvd.cxx:107-111`) and `VirtualDevice`
**does** return it (`virdev.cxx:384`); **`doc_paintTile` discards the bool**
(`init.cxx:4288`) and paints anyway. The LOK ABI is `void`. So the buffer comes
back exactly `width*height*4` bytes and untouched - **the zeros are our own
malloc**. Every layer is locally truthful and the composite is a silent lie.

Upstream statement drafted, submission stays on hold. Six candidates ruled out
with reasons. `findings/evidence/062/layer/ATTRIBUTION.md`.

**T6 - prepared, not run.** `handoff/a11y-gate-0/` holds the `configure.ac` patch
(direction chosen: make the macro follow the module decision, **and the AC_DEFINE
has to move after the module loop** - `:3498` runs before `:4371-4392`, which is
the detail that would otherwise waste a rebuild), the PREDICTION with the pass/fail
criterion fixed before any result, and `tools/probe_a11y_gate0.py`.

The probe **refuses to run** on today's core and does not start a browser:
`check_core_build_provides.py` reports `macroValue: 1`, `callersCompiled: false`.
G0-2 requires **three** paragraphs and >= 2 distinct identities - a positive
control, put there because three checks on 2026-08-21 passed or abstained for want
of one.

---

## 3. Traps carried forward

* **An engine field nobody forwards does not exist.** `sdk-worker.js` allowlists
  reply fields; it bit twice in one afternoon. T1 and T2 both add reads.
* **Iterating on the page mints a shell generation each time.** Standalone probe
  first, then mint one.
* **`make e2-c-assets` after every `web/` or `sdk/` edit** — and note it does *not*
  rebuild the v3 profile manifest (T2.2).
* **Do not compare wording in an oracle** — T0's mechanism avoids it by construction.
* **Ascending sweeps hide cold-start limits** — T2's arms.
* **A duplicated id silently swallows edits** — T2, T3 and T7 all flip queue or
  matrix entries.

## 4. Sent outside

* **T5** → codex: objective, source-only, no shared files.
* **This plan** → codex, adversarially. It came back **REVISE** with five rejections;
  §6 records them.
* **T4's design question** → fable, if the user wants it.

## 5. What v1 got wrong (codex, 2026-08-21) — each verified before accepting

| | v1 said | Verified | v2 says |
|---|---|---|---|
| **1** | Widen the gesture in `build_e2_b_profile.action_map()` — one place | `tests/test_e2_b_profile.py:78` pins v1 actions caret-only under both dispositions; the builder's docstring names *"one path, two identities"* as the failure | Override in the **v3** builder; rebuild `Makefile:987` explicitly |
| **2** | Grant `RANGE_SINGLE`, and separately `RANGE_CROSS` | `probe_engine.cpp:4372-4374` is an **`&&`**, with a comment saying why | **Impossible as written.** Grant both; vary the selection *shape* instead |
| **3** | Inline formats use the paragraph-action ODT oracle | The matrix amended its own oracles on 2026-08-15: at a collapsed caret `<office:body>` is **byte-identical** | Commit a **marker** and read its span's style |
| **4** | Waive `click#open-file` — needs a human | The runner already shims `.click()` (`:178`); the path is one forwarding line (`:813`) | **Drive it.** `waived: []` too |
| **5** | Bind all 14 reasons to the wasm hash | Most reasons are structural; identity is **five** hashes, not one | Optional, **typed** `reasonBoundTo` |
| **6** | D0 excluded | It is in M1's completion criterion, the matrix is two relinks stale, and `run_e2_c_d0.py` is autonomous | **T7**, last |
| **7** | T0→T1→T2→T3 all sequential (index-shift trap) | The 08-18 §8 trap is narrower: new checks after positional-index saves | Real dependencies only; the trap becomes a `SAVE_COUNT` rule |
| — | 059 "is fixed on the current artifact" | No saved report records a wasm hash (`:1662`) | The *reason* is unsupportable; whether the formats work now is **T1's measurement** |
| — | v1 §0: "baseline, Firefox: exit 0" | Exit 0 ≠ `ok: true`. The report says `ok: false` | **T0.5.** Found by reading the report instead of the exit code |

## 6. Revision log

| Date | |
|---|---|
| 2026-08-21 | **v2 after adversarial review.** Five rejections and two weakenings, all verified in source before accepting; §5 is the table. Three were design errors that would have produced a measurement incapable of failing (T2's range bits, T2's shared builder, T1's inline-format oracle), one was a dishonest waiver, one was a missing M1 criterion (D0). |
| 2026-08-21 | **T0.5 added after the Firefox baseline came back `ok: false`.** Two FAILs and a second NOT_ESTABLISHED on an arm the handoff never claimed and nothing in the tree records. Finding 060's own reproduction row says 「Chrome 1/1…；**Firefox 未量**」, so the caret check has never been measured on the browser that now fails it. This is the same lesson as `first-run-of-a-regression-net-is-the-measurement`, arriving from the other direction: the arm was not new, it was **unrun**. |
| 2026-08-21 | First version. Written from the 08-19 handoff, reconciled against the 08-20 roadmap. All state numbers re-measured. T0 came out of reading the coverage registry's own reasons and finding one bound to an artifact two relinks gone. |
