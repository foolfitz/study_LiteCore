# 096 — RESULT after the link: the boundary press is answered, and the controls still die

Measured 2026-09-09 (UTC 15:05 → 15:54) against the predictions registered in
`handoff/HANDOFF-2026-09-09-096-is-landed-in-source-and-waits-on-the-same-link.md`,
**written before `dist/profiles/e2-editor-v14/` existed**. This document reads
those predictions back one at a time. It does not compose a new acceptance and
it names no cause.

**No build, no link, no product byte moved.** Nothing under `web/`, `dist/`,
`src/`, `sdk/`, `editor-shell-v2/` or `build/archive/` was written; no check in
`tools/run_e2_c_product_path.py` was modified.

## The artifact, hashed here rather than quoted

| file | sha256 |
|---|---|
| `probe.wasm` | `5847a1407d3af58fc8cae76d151b7d8d865b75b11beace5d8413ea823eca23ca` |
| `probe.js` | `6581cc948dd183f39c2c4c6be6eb2e8ec300c0a5598ab362efeb7db7daa9bc24` |
| `sdk-manifest.json` | `9943b064d4e185159cc12f57dddf083b7844672024357d3ec9374fed20b73250` |
| `sdk-worker.js` | `6e75829a2911c1dffa9457f64f6f04a67f0f7bb0bfdda82a663747c0f8b0bc97` |
| `base…metadata` | `b1e48f2b7ac50b60be588d3dda22dc95287115a9ab3b3e676e84304676309fec` |
| `cjk…metadata` | `fafab99558ab6f8b49a0a9d15c1e8bb2cbc9ae8fa73d6be5cd84b91f85dbfc79` |
| `fallback-fonts…metadata` | `924fb0ed8b4599463e9a9d53f6c1aa06cc306cced8ef112424275605ed0c907a` |

Re-verified here rather than taken on report: the literal `verified-move-readback`
occurs **once** in v14's `probe.wasm` and **zero** times in v13's and v8's, while
the positive control `verified-caret-readback` occurs once in all three. v14's
`sdk-worker.js` is byte-identical to v13's, as the link rule said it would be.
The baseline artifacts are unmoved: v8 `4a2710bba1ef07d9…`, v12
`4ec1e389aaab3b03…`, v13 `0fe25650bec1bac5…`.

**`build/archive/` has no `e2-editor-v14` entry.** Step 1 of the handoff's
post-link order ("record the five hashes; archive immediately") is outstanding;
it belongs to the owner and was not performed here.

## Prediction 1 — A: the boundary press is answered

> "the boundary press is answered in well under a second and the session stays
> `ready`, so the probe reports `NOT_REPRODUCED` rather than `REPRODUCED`."

**HELD, 10/10.** `boundary-arrow-e2-editor-v14.json`, the probe unmodified and
its defaults unchanged, the owner's own document (`63bf89cb…`), real keys via
`Input.dispatchKeyEvent`, caret placed by canvas pointerdown.

| direction | attempts | outcome |
|---|---|---|
| up | 5 | `NOT_REPRODUCED` 5/5 |
| down | 5 | `NOT_REPRODUCED` 5/5 |

In every attempt: `firstNonMovingPress: 2` (the same press index as pre-link),
no death, and after the probe's full 90 s death wait the frame reads
`state: ready`, `revision: 0`, `pending: 0`, `noticeShow: 0`,
`#s-checkpoint: 有（r0）`. No page errors, no rejections, and the live document
worker answered `Runtime.evaluate` in every attempt.

**The latencies, read from the product's own `#s-latency`:**

| press | n | range | median |
|---|---|---|---|
| the moving press before the boundary | 10 | 47–51 ms | 48 ms |
| **the first boundary press** | 10 | **623–958 ms** | **666 ms** |
| every later boundary press in the same session | 50 | 259–263 ms | 261 ms |

The steady-state 261 ms is the 250 ms deadline plus about 11 ms. **The first
boundary press is not that number** — see the surprises below.

## Prediction 2 — the controls must still die

**HELD as stated, with a label change that is measured rather than inferred.**
Both controls were run in this same session, on the same probe, immediately
after v14.

| arm | wasm | page sha256 | up | down | state reached |
|---|---|---|---|---|---|
| `e2-editor-v13` | `0fe25650bec1bac5` | `31787584290e42bd…` | 5/5 died | 5/5 died | `recoverable-error` |
| `e2-editor-v8` (shipping) | `4a2710bba1ef07d9` | `1ec7baf9fb53c808…` | 5/5 died | 5/5 died | `recoverable-error` |

**Every one of the twenty attempts died.** The instrument did not change and
the v14 result stands.

But the probe labels them `DIED_WITH_CHECKPOINT`, not `REPRODUCED`, because its
`REPRODUCED` predicate requires `noticeRescue == "none"`. The page bytes are
**byte-identical** to the pre-link runs (`31787584…` and `1ec7baf9…`) and so are
the two engines, so exactly one thing differs: the shell in `dist/` now carries
half C. Measured, side by side:

| | pre-link (09:12 UTC) | post-link (this session) |
|---|---|---|
| outcome | `REPRODUCED` | `DIED_WITH_CHECKPOINT` |
| `data-rescue` | `none` | `checkpoint` |
| `#s-checkpoint` after the key | `無` | `有（r0）` |

So the death is unchanged on both frozen engines and the **loss** is not. That
is half C, demonstrated on two engines with the page held fixed — a comparison
this round did not set out to make.

The notice these controls now raise is the one finding 096 registered and
deliberately did not fix: 「這一步可能已經改到文件，而且無法驗證。回到**選取手勢**前的
檢查點。」 There was no selection gesture. Registered again here; still not fixed.

## Prediction 3 — C: `ENGINE_ANSWERED`, not `RECOVERED`

> "Expect the `with` arm to report `ENGINE_ANSWERED` rather than `RECOVERED`.
> A `RECOVERED` there after the link means the deadline is not in the artifact."

**HELD — but only once the probe is pointed at v14, which it does not do by
itself.** `probe_096_checkpoint_before_the_gesture.py` has no `--profile`: it
mirrors `dist/` and the page there pins `e2-editor-v8`
(`PINNED_WASM_SHA256 = "4a2710bba1ef07d9"`). A literal re-run measures the
shipping engine, so the prediction's inference rule does not hold for it. Both
runs were therefore taken.

**C on v14** (`checkpoint-before-the-gesture-e2-editor-v14.json`; the probe
byte-identical, the served mirror's `e2-editor-app.js` replaced by
`repointed_page()` through `run_c_on_v14.py`, banked beside this file; page
`d74801324d243949…`, pin `4a2710bba1ef07d9` → `5847a1407d3af58f`):

| arm | outcome | `boundaryPressAnsweredSeconds` | `stateAfterPress` | `#s-checkpoint` after the key |
|---|---|---|---|---|
| `without` | **`ENGINE_ANSWERED`** 3/3 | 4.10, 4.11, 4.11 | `ready` | `無` |
| `with` | **`ENGINE_ANSWERED`** 3/3 | 4.11, 4.11, 4.11 | `ready` | `有（r1）` |

`boundaryPressAnsweredSeconds` was `null` in all six pre-link attempts and is
non-null in all six here. **Its value is the probe's own 4 s movement-watch
window, not the engine's answer time** — the field is `presses[-1]["seconds"]`,
and the caret never moves at a boundary, so the watch always runs to its
ceiling. What the field carries is the binary fact that the session did not die.
The answer latency is the A probe's, above.

**C on the shipping page, probe unmodified** (`checkpoint-before-the-gesture-post-link-v8.json`),
run in the same session as the control on C itself:

| arm | outcome | `data-rescue` | the typed text came back |
|---|---|---|---|
| `without` | **`WORK_LOST`** 3/3 | `none` | no |
| `with` | **`RECOVERED`** 3/3 | `checkpoint` | yes |

`armsDisagree: true` — cell for cell what the pre-link run measured. Half C
still holds on the shipping bytes.

**Is C still reachable on v14? No, not through this gesture.** Both arms answer,
so neither loses the work, `armsDisagree` is `false`, and the probe's red case no
longer discriminates on this engine. Half C still *runs* on v14 — the `with` arm
banks `有（r1）` where `without` stays `無` — it is simply never needed. C remains
falsifiable only on an engine without the move-path deadline.

## Prediction 4 — the forty-second check, and clause B2

> "the product path, whose new check reports `clausesExercised` including `B2`
> for the first time." Composition: **40 PASS / 2 NE**.

**HELD.** `findings/evidence/096/product-path/plain-e2-editor-v14.json`,
`tools/run_e2_c_product_path.py --profile e2-editor-v14`, no mutation.

* **42 checks: 40 PASS / 2 NE / 0 FAIL**, `ok: true`, `complete: true`,
  `pageErrors: null`, `knownRed: {}`, `staleKnownRedDeclarations: []`,
  liveness 41 probes, `lastState: ready`.
* The NE pair is the registered one and is unchanged:
  `notice-action-recovers-the-session`,
  `a-refused-action-is-reported-and-changes-nothing`.
* `servedShell`: bundle `e2/editor-shell-v2-bundle-v51.json`, declared
  `2ffbec81…`, served `e7873d7e…`, `differingPaths: ["web/e2-editor-app.js"]`,
  `differsOnlyInTheEntrypoint: true` — the repointed page and nothing else.

**`a-boundary-arrow-press-does-not-cost-the-work`: PASS, and B2 actually ran.**

`clausesExercised: ["B1", "B3", "B2"]` — pre-link it was `["B1", "B3", "B4"]`.
The clause was driven, not merely declared:

| observation | value |
|---|---|
| `takenByThePage` on the boundary press | `[true]` — the page took the key |
| `theEngineAnsweredThePress` | `true` |
| `stateAfterPress` | `ready` |
| `revisionBeforeTyping` → `revisionAfterTyping` | `0` → `1` |
| revision after the press | `1` — unmoved by the press |
| `#s-checkpoint` before / after the key | `無` / `有（r1）` |
| presses | 1 moved (0.61 s), 2 did not (4.1 s, the watch ceiling) |

The `defaultPrevented` control fired, so this is not the false green the check
was built to refuse — a key the page never took would have left the session
`ready` for a reason that has nothing to do with the engine.

## What this round did not anticipate

**S1. The first boundary press costs 623–958 ms, not 261 ms.** 10 attempts out
of 10, both directions, median 666 ms, against a 250 ms deadline and a
steady-state of 259–263 ms for every later press in the same session. The press
is still answered and the session still stays usable, so no prediction fails on
it; but "answered in 250 ms" is not what the first one does, and the handoff's
own note that **nobody has measured this path under load** now has a companion:
nobody has measured why the first one differs from the rest. **No cause is named
here.** What is measured is the distribution and that it is not intermittent.

**S2. `boundaryPressAnsweredSeconds` does not measure the answer.** It is the
probe's 4 s watch window; only its null-ness is informative. Reading 4.11 s as
"the engine took 4.11 s" would be wrong, and the field's name invites it.

**S3. The A probe's controls stopped saying `REPRODUCED`.** They still die,
which is the condition that matters, but a future reader diffing outcome strings
against `RESULT.md`'s 40/40 `REPRODUCED` will find twenty cells that changed for
a reason that is in the shell, not in the engine.

**S4. B4 stops being exercised on v14.** With the press answered, the session
never dies, so the product path never presses the recovery notice and never asks
whether what comes back contains what was typed. On the shipping profile the
check exercises B1/B3/B4; on v14 it exercises B1/B3/B2. **No single run of this
check now covers all four clauses**, and the clause that half C exists to
protect is the one that goes quiet on the engine that fixes half A.

**S5. Step 3 of the post-link order cannot be executed literally.** See
prediction 3: the probe has no `--profile`, so the run it names measures v8.

**S6. `build/archive/` has no v14.** Step 1 was not done before the measurements
were taken. Nothing here depends on it, but the artifact is unarchived.

## What is still not measured

* **Why the first boundary press differs from the rest** (S1).
* **The path under load.** Every number here was taken on an idle machine with
  one headless browser at a time, deliberately sequential.
* **Home / End and the two character moves**, in both directions — unchanged
  from before the link.
* **Whether 250 ms is enough on a long document**, and the rate at which a
  slower press falls through to the readback.
* **Any v1 profile.** `editor-shell/editor-client.js` still rejects
  `verified-move-readback`; no v1 artifact moved and none was exercised.
