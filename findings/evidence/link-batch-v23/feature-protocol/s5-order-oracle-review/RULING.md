# Astra ruling: adopt A for witnessed every-member-settled native references

Issued under the owner's explicit delegation on 2026-10-27. The decision below is preserved verbatim except that the quoted owner delegation is translated into English. This supersedes the earlier advisory status, not historical observations.

> **Astra ruling: adopt A — witnessed, every-member-settled native references for the tool-derived order-dependent partition.**
>
> Authority: the owner's explicit delegation in this turn, “Send it to Astra for a ruling; I authorize it to decide on my behalf.” [translated from Chinese]. This is a binding decision, superseding my earlier advisory status. It authorizes the specified protocol amendment and implementation; it does not declare S5 acceptance.
>
> 1. **Reason and semantic claim.** The forcing evidence is `empty-mark-witness-01` plus `s5-order-prep-02`, reproduced by `s5-order-oracle-review/read-prep.py`. All 336 native cells pass the timestamp census; the four browser observations satisfy their single-line and own-before controls and match settled native. The two native witnesses remain two executions, not four repetitions.
>
>    For the affected partition, S5 shall claim agreement with Writer executing the exact continuation with an 800 ms quiet / 8000 ms cap settle and state read after **every member**. This is distinct from the existing WASM reference's Shift-only boundary wait. Their observed agreement does not establish schedule equivalence. Neither event reordering nor its responsible layer is established; exchanging two identical Backspaces alone cannot explain the difference. B unnecessarily discards available native parity; C remains the missing-evidence default.
>
> 2. **Exact supersession.** For newly versioned plans adopting this ruling, replace ruling 4, condition 1's requirement that a differing settled after-save be NE `native save not order-independent`, **only for the non-empty-mark partition defined below**. Replace its “expected 0” assumption with the measured, tool-derived disagreement population. Do not change `nativeOrderIndependent` to true. All remaining ruling-4 requirements survive, including empty-mark membership, consistency checks, its settled-WASM route, native refusal, non-vacuity, historical failure treatment and named guard limitation. Ruling 2's comparator, ruling 3's type oracle and the overlap requirement remain unchanged.
>
> 3. **Membership and eligibility.** Enumerate the generator's complete native-capable deletion population: exclude type and mandatory settled-WASM rows. Within it, derive membership where the bound own-sequence witness gives `emptyMark=false` and the queued versus every-member-settled native after-saves differ under the existing full native `reduce_content` comparison. No case-ID whitelist, browser outcome or agreement with the candidate may determine membership.
>
>    Validate complete, unique coverage before deriving the partition; invalid or missing evidence must not make a member disappear. Home/End still require the actual browser single-line witness for native comparison; otherwise retain the existing layout-reference rules. An eligible member uses the settled witness's **own before/after pair**. Missing or invalid required evidence means plan refusal or cell NE, never fallback to queued native or WASM to obtain PASS.
>
> 4. **Bindings and checks.** Bind the population generator, reader, fixture, archived harness sources/build receipt, native core/environment, raw records and both saves by their applicable identity/hash checks. Retain existing setup and consistency validation. Require exact generated sequence, step operations and key posts, with two posts per member; `interMemberSettle` must specify every member, 800/8000. Require valid non-capped open/setup/member settles, finite non-boolean timestamps, ordered posts and `atMs <= returnMs`. For each member require:
>
>    `keyUp.returnMs <= readStartMs <= readEndMs`
>
>    and, except at the last member:
>
>    `readEndMs < nextKeyDown.atMs`.
>
>    Require successful own before/after saves. Check candidate-original directly against witness-own-before, and queued-native-before against settled-native-before, using ruling 2's guarded native reduction. Apply its collapse guard to the witness's own pair. Compare candidate-after against witness-own-after with `strip_ffd(reduce_content(...))`; retain structural and automatic-style differences.
>
>    Accept the disclosed **source-bound setup/save lifecycle**. Member boundaries have timestamp witnesses; setup/save boundaries do not. Existing artifacts suffice: **no additional native measurement is required**. Do not describe these records as independently timestamping setup or saves.
>
> 5. **Records and red controls.** Record `reference: native-every-member-settled`, `nativeOrderIndependent:false`, `emptyMark:false`, the single-line decision, schedule and bound witness/save identities. Report derived and actually routed populations per browser; reconcile their identities against eligibility, rather than hardcoding “two”. Failure payloads must expose reduced structural differences, including cases where paragraph text is equal.
>
>    Before counted execution, demonstrate controls detecting: missing/duplicate witness, missing save, wrong hash, capped settle, wrong operation/posts, non-finite or boolean time, interleaved read/post boundaries, wrong own-before, collapse, and a generated new member lacking evidence. Feed queued heading and list outcomes as candidates: both must FAIL, including the structure-only list difference. Empty-mark input to either native route must refuse. Demonstrate relevant guard-removal mutations turn these controls red; preserve positive controls.
>
> 6. **Historical compatibility.** Introduce an explicit plan/schema distinction. Historical configurations retain their original oracle semantics and NE outcomes; do not infer adoption from newly available files. Unknown or malformed new configurations refuse or yield NE. Re-read preserved pages against their recorded configurations and compare all existing semantic fields; no blanket field-ignore workaround. Old pages, inspections and `s5-counted-01` remain unchanged and uncounted.
>
> 7. **Documentation, counts and sequence.** Append this ruling and explicit cross-references to ruling 4, S-CASES and native consumer documentation. Identify the forcing measurements, replacement clause, schedule limitation and defaults; retain originals. This changes the clean predicate before any qualifying S5 population exists. Start fresh full S5 counts; no preparation or partial-run credit. The cutoff remains each browser's first complete clean population; later concerns become findings.
>
>    Implement and verify the reader/plan/judge with red controls first; then run the specified two-browser S5 preparation under the final plan. Refresh hash-bound R1 validation affected by shared-file changes and verify historical compatibility. Freeze the instrument before full counted runs; do not edit their closure during execution. The independently qualifying four-arm cohort remains established within its existing scope and is not reset by this oracle amendment.
>
> Implementation and testing belong to the primary agent.
