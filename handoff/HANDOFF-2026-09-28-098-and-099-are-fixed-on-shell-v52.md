# Handoff, 2026-09-28 — 098 and 099 are fixed on shell v52, the page still points at v8

Entry points, in order: this file, then `findings/098-*.md` and `findings/099-*.md`
(both read whole), then `findings/evidence/098/README.md` (it holds the evidence for
both). `handoff/HANDOFF-2026-09-10c-094-and-097-censused-098-registered.md` is the
previous entry point; its open list is superseded by the one below.

The owner was away for this round and delegated every decision to fable (a subagent
with `model: fable`), asking for a plain-language explanation of each. The ruling and
its plain-Chinese rationale are written into 098 and 099 under 「裁決」.

## What changed

| | |
| --- | --- |
| commit | `4ccfe2be` (fix + tests + freeze + findings + evidence), then a second commit for the product-path evidence and this handoff |
| file | `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js` only |
| shell generation | **v52**, `bundleSha256 7a1e8815…`, frozen in the same commit as the change |
| entrypoint | still pins `e2-editor-v8`; `web/e2-editor-app.js` byte-identical to v51 |
| engine / profiles / link | untouched |
| cutover | **none** — the shipping page still serves v8 on shell v48 |

**098 (candidate A)**: `action()` enqueues the six key-path moves
(`BOUNDARY_CAPABLE_MOVES`) with `mutation: false`. Before, every action went in as a
mutation, so one arrow key marked a never-typed document dirty and the second banked
a checkpoint of the opened bytes. Now aligned with the base class's `moveCharacter`,
the client's postcondition and the engine's own classification.

**099 (new, C1)**: half C's price control compares content stamps
(`_checkpointStamp === _currentContentStamp`) instead of revisions. Revision and
content part company in two ways, and both made the old guard skip a checkpoint the
user's work needed: across Workers (revisions restart at zero on open, the checkpoint
survives the rollback) and within one Worker (a format action that comes back
dispatched-unverified is counted as a mutation, but `failFormatBarrier` never
advances the revision). The stamp guard only works as a price control once moves stop
bumping the stamp — which is why 098 and 099 had to land together.

## Evidence (all in `findings/evidence/098/`)

- **Unit**: 37 tests in `editor-shell-v2/tests/narrow-editor-v2-session.test.mjs`;
  pre-fix 31/37, fix 37/37. A self-check (`unit-selfcheck/`) serves partial fixes and
  five wrong fixes built by the review seats; each wrong fix now reds at least one test.
- **Page**: `probe_098_a_caret_move_banks_a_checkpoint.py`, user's path on v8, two
  mirrors differing only in the fix. Unfixed: 無 then 有（r0） from press 2, 3/3.
  Fixed: 無 on every press, 3/3, rerun on the landed bytes (`--require-landed`) 3/3.
  Positive control 有（r1） in every attempt.
- **Product path** after landing: v8 and `--profile e2-editor-v14`, each 40 PASS / 2 NE,
  `ok: true`, no check changed outcome against the last pre-fix runs; check 42
  exercised B1/B3/B4 on v8 and all four clauses on v14.

## Review seats — what they found

Both ran BEFORE the commit. `codex exec` (the codex MCP server is gone; the CLI works,
`codex exec -s read-only -C <repo> -o <file> - < prompt`) and an opus subagent. Neither
broke the fix. **Both broke the tests**: codex built a wrong guard that passed the
first single-case 099 test; opus built four more that passed the widened grid. opus
also found the within-Worker mode of 099, which the main session confirmed from
`src/probe_engine.cpp` before adopting it. Lesson, again (AGENTS.md §6): a scenario
test pins a scenario; the property "the skip does not read the revision" was pinned
only when the guard was asked directly at every revision 0..40.

## Open list now

1. **The wrong-gesture wording (061's shape)** — owner's ruling, deliberately unfixed.
   Not touched; still cheapest folded into the next link.
2. **094 / 097** — bind / revisit at cutover, unchanged.
3. **099 at browser level** — not reproduced (needs two induced deaths plus a revision
   coincidence, or a controllable review-path inducer). Named limit in 099.
4. **Work item, not a gate criterion**: a product-path check for "a caret move banks
   nothing on a clean document". fable ruled against adding it now (§9; the defect is
   wholly in session logic with direct unit coverage). The page probe is the seed.
5. **Shipped shell v48 still carries `mutation: true` for moves** (without half C).
   Inference, not measured on v48: a clean document, an arrow key, then a drag banks a
   checkpoint of clean bytes. v52 reaches shipping bytes only at cutover.

## The gate

Unchanged: soak 0 of 12, reordered to the end of development, full run on the final
identity before any cutover, floor of three calendar days; T4 to be re-earned on the
final identity. Nothing identity-bound was live, so nothing was invalidated. **No
cutover has been performed.**
