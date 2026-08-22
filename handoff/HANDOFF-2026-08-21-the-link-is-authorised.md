# Handoff — 2026-08-21: the link is authorised, the payload is settled, nothing is linked yet

> Entry point. Reading this page is enough to take over.
> Previous: `HANDOFF-2026-08-19-every-row-has-a-check.md`.
> The plan this day ran from: `PLAN-2026-08-21-close-m1-without-a-link.md`
> (v2 — its first version was rejected by adversarial review; §5 there records
> the five rejections and §2.5 is the execution log).
>
> **English per `AGENTS.md`.** `devlog/`, `research/`, `specs/` stay zh-TW —
> and the ABI proposal is deliberately in `research/`, in zh-TW, because its
> reader is the user.
>
> The title is the one thing that must not be misread: **the user authorised
> the link and no link has happened.** The remaining runway is below.

## 0. Bindings

| | |
|---|---|
| artifact | **`29ec627bf8a5588b…`** — unchanged today. No relink, no engine rebuild |
| shell | **v25 `07143f961d82c4b3…`** — unchanged today. **No `web/`, `sdk/`, or `editor-shell*/` file was modified**; only `tools/`, `e2/`, tests and docs |
| matrix | `e2/validation-matrix-v2.json` — **re-frozen 2026-08-21, all five bindings re-stated, D0 RUN and PASSING on both browsers** |
| checklist | **12 done / 2 partial / 0 unverified / 0 missing / 2 blocked**, `problems: []` |
| `KNOWN_RED` | **1** — `every-inline-format-reaches-the-document`, finding 064 |
| queue | 45 items, 15 open, **0 blocking**, `P1 complete: True` |
| product path | **32 driven / 2 uncovered / 0 waived** (was 20 / 14 / 0), **29 checks** (was 22) |
| static tests | 56 pass |

Both browsers are `ok: true`. **Nothing is committed** — the user was asked and
had not decided; `e2/`'s frozen matrix and checklist are among the changes, so a
reviewer should look before it lands.

## 1. The decision that matters

**The user authorised the link** ("ok 可以連結"). It is M1's third and closing
link. The reasoning is `research/PROPOSAL-2026-08-21-abi-revision.md` (zh-TW) plus
fable's adjudication, and the payload is **six items**:

| | |
|---|---|
| 1 | `move-by-line` ×4 → wire ids **16–19** |
| 2 | `redo` → a **sibling SDK operation**, **zero wire ids** |
| 3 | **`delete-selection` → id 20, gestures range-single + range-cross only** |
| 4 | `select-all` → engine half shipped, **manifest-withheld** pending characterisation |
| 5 | the a11y honesty fix (`queue-engine-must-report-core-lacks-accessibility` — its own note says "ride along with the next one") |
| 6 | the 32,767 tile refusal (attributed today, so the remedy is known) |

Plus: `abiVersion` 3→4, a **successor builder**, ids 1–15 inherited verbatim,
the exact-match ABI handshake, frozen v2/v3 bytes untouched, and SPEC E2-C 4.2
revised in the same change.

**Execution discipline, non-negotiable:** archive the profile first
(`wasm-build-not-reproducible`); no rebuild between sweep and verdict; re-state
all five bindings and re-run D0 on both browsers immediately after. The T7 guard
demonstrated today, four days after it was predicted, that the relink-to-freeze
window is exactly where the mistake lives.

**Do not wait for the a11y link.** Gate 0 is contingent and its artifact may
never exist. And link **before** M2a: M2a's toolchain work churns the artifact
and its criterion is A/B evidence chains — a contract change landing mid-M2a
invalidates them.

### The one thing still gating execution

**Finding 064's mechanism is not established, and it is the only remaining thing
that can change the payload.** Product-side (which the evidence suggests) → fixed
in the shell, independent, in parallel. Engine-side → it becomes item 7 and the
link waits for it. **Start here.** The candidate is named and it is a
measurement, not a hunt: the `renderDocument()` the product's `run()` performs
between the format action and the typing (`web/e2-editor-app.js:377-382`).

## 2. Findings filed today

| | |
|---|---|
| **064** | **An inline format set in the product never reaches the text you type.** All four, both directions, eight arms. HIGH. **Attributed, not guessed**: D1's harness on the *same* artifact, read by the *same* oracle, gets all eight right — so the engine is fine and the product path is broken. Mechanism NOT established. `KNOWN_RED`, and it put `turn-formatting-off` back to `partial` |
| **062** | **Attributed.** The 32,767 wall is Cairo's `MAX_IMAGE_SIZE` for pixman's **16.16 fixed-point** coordinates — **not** a signed 16-bit height, which was our inference. `doc_paintTile` (`init.cxx:4288`) discards the `bool` SVP correctly returns; the LOK ABI is `void`. Upstream error-propagation defect; statement drafted, submission stays on hold |

## 3. What is left

| | |
|---|---|
| **064's mechanism** | Gates the link's execution. §1 |
| **The link itself** | Authorised, payload settled, not started |
| **`cut`** | In the payload. One probe worth running *inside* the link work: **does LOK's `paste` with zero-length text delete a selection?** No arm has reached it. If yes, `delete-selection` can relax `sdk_api.cpp`'s length check and reuse `handleReplaceSelection`; if no, the barrier-entry route is the fallback and is independently sound |
| **`blur` / `pointercancel`** | The only 2 uncovered paths, and they are uncovered **on purpose** — the check exists, has a positive control, and **abstains**. Next step is a real observable: the copy path's `codePoints`, not `button.disabled` |
| **Recovery's second inducer** | **No inducer found.** Three candidates eliminated with evidence, and two of the queue item's own claims corrected. Open and narrowed |
| **D0 / matrix** | **Done.** M1's fourth criterion is met |
| **a11y gate 0** | Prepared, not run: `handoff/a11y-gate-0/` has the patch, the PREDICTION, and a probe that refuses to run on today's core. **The rebuild is the user's hours** |

## 4. The traps that cost time today

These are the reusable part.

**A check can pass *because* it could not measure.** `the-caret-lands-where-the-click-was`
passed at `fractionNearStart: -0.229` — a value `argmin` returned by **tie-break**
when no column had lost ink. It satisfied `< 0.25` precisely because the caret was
never found. A question asked of missing data must return **null**, not a value.

**Every "X did not happen" arm needs a positive control**, and this cost three
separate checks in one day. The aborted-gesture check stayed **green with
`pointercancel` unwired entirely**, because the drag had never started. If a
mutation does not redden a check, suspect the precondition before suspecting the
mutation. Recorded in `probe-measurement-discipline`.

**Reading a handler is not reading the path to it.** `handleReplaceSelection`
genuinely has no empty-text gate — and is unreachable, because
`sdk_api.cpp:172-174` refuses `utf8Length == 0` at the ABI boundary. Two
diagnostic arms were designed from a source reading that stopped one layer short.

**A format press at a collapsed caret restyles the run the caret is in.** Six
markers committed at one position coalesced into a single `<text:span>` and every
later press rewrote the earlier ones. The tell was the **explicit**
`fo:font-style="normal"` — absence of formatting does not spell itself out.

**A reason can expire, and the registry could not notice.** `click#clear-format`
was excused by a finding that shipped its fix two relinks ago. The audit reported
`ok: true` throughout. It now takes an optional, typed `reasonBoundTo` and goes
red when the binding moves.

**`make test-e2-c-static` was already red at HEAD** before anything was touched —
`e2-c-assets` never owned `dist/editor-shell/recovery-notice.js`; it worked only
because a different target put the file there.

## 5. Do not repeat

* **Do not fix the assertion when the setup is wrong.** The edit-button sequence
  first read the wanted string **plus the tail of the paragraph it had split**.
  Relaxing to `startswith` would have destroyed the separability the whole
  sequence rests on. The fix was to break at a **line end**.
* **Do not claim a path is driven by a check that cannot fail.** `blur` and
  `pointercancel` were moved to `driven` and then **moved back** when the
  mutation would not redden them.
* **Do not escalate a parameter on an arm that cannot show it ran.** 40 pages →
  200 pages, on a probe that never proved a range was selected, only attaches a
  number to a measurement that did not happen.
* **Do not read the shell's bookkeeping as the engine's answer.**
  `checkpoint: 有（r1）` proves the shell thought it was a selection gesture. It
  proves nothing about what the engine selected.
* **Do not name a layer without showing the line** — and when a subagent names
  one, re-read the line yourself. codex was right about Cairo and fable was
  wrong about `replaceSelection`; both were checked before being used.
* **`make e2-c-assets` after every `web/` or `sdk/` edit** — and note it does
  **not** rebuild the v3 profile manifest.

## 6. Tools added today

| | |
|---|---|
| `tools/probe_a11y_gate0.py` | Gate 0. Refuses to run on today's core, without starting a browser |
| `tools/probe_second_recovery_inducer.py` | The inducer verification obligation. Wires nothing in |
| `run_e2_c_product_path.py --range-delete-diagnostic` | Grants both range bits in a **mirrored** manifest |
| `run_e2_c_product_path.py --cut-via-replace-selection` | Mirrors three files to walk the empty-text gates |
| `tests/test_caret_from_columns.py` | 7 cases; **4 fail against pre-fix HEAD** |
| `tests/test_inline_styles_of.py` | 9 cases, incl. ODF's `"none"` line styles, which a presence test reads backwards |

All four diagnostics stamp their reports `evidenceClass: "diagnostic"` and never
write `dist/`.
