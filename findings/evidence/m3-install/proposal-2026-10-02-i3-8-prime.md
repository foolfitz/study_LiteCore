# Proposal, 2026-10-02: replace I3-8 with I3-8′ for the install window on 0.2.5

Status: **proposed, not adopted** — sent to an adversarial review (opus, read-only) before any
0.2.5 window. Nothing here is in the spec yet.

## What happened

J (install-elsewhere on host 0.2.5, `SPEC-M3-install-elsewhere.md` revision row of 2026-10-02):
`install --reinstall --was release-0.2.1.json` succeeded (0.2.5 enabled from archive `602fe6bb…`,
binding clean). Then `check_m3_install_elsewhere.py equivalence` printed

    1/6 reports score and red-case the same; recording paths equal: False; old expressions found in 9748b714: True

(`equivalence.json`, at 2026-10-02T14:21:12Z, head `c129724d`).

- **Rows** (I3-8's "the four runners re-score every counted report that existed at PRE `9748b714`
  identically under the tools at PRE and now"): 5 of 6 differ. Every difference traces to a change
  made on purpose after the 0.2.1 counted window (`71e0ac8e`), each re-counted on its new binding:
  - page pin `fbfb59a4…` → `fc80050c…` (SPEC-M3-page-honesty §7.6) and host pins
    `5e53362`/`369e6ed` → `7420418` (SPEC-M3-zstd Z3): "static: page …", "host is … spec names …";
  - the asset runner's K2 "pre-leave save" instrument clauses (SPEC-M3-asset-delivery §7, K2 ruling
    A′, 2026-09-29): 09-28 reports have no `saved` record → `K2 chrome 0/3`;
  - the locks runner's `nowhere` arm after finding 108 (SPEC-M3-page-honesty §7.11): `nowhere 0/3`
    on 09-28 reports.
  The one unchanged row is host entry `2026-09-28T095100Z`.
- **Recording path** (dev instance: `binding_fields(host_binding)`, `package_for`,
  `Instance.describe`, PRE tools vs now): every field PRE records is recorded now with the same
  value; the only differences are fields that exist only now — `zstBytes`, `zstDecodedSha256`,
  `zstFrame`, `zstSha256` under `package/files/<path>` for each of the 22 paths (SPEC-M3-zstd Z0).

So I3-8 as written can no longer be satisfied: making it green would mean re-pinning old reports to
old bindings, i.e. building machinery to keep an old claim alive (CLAUDE.md "驗收判準的形式" §4).

## What I3-8 was for

Spec §3.3 / I3-8: the four runners were changed (2026-09-29, `--ddev-root`) to run against another
instance; I3-8 showed that change did not alter how they record or score the dev instance, so a
verdict on litecoreprobe is comparable to the dev instance's. That was established in the 0.2.1
counted window. The question it guards is still needed for any later window: **are the tools that
judge litecoreprobe the tools whose dev-instance verdicts we compare against?**

## Proposed I3-8′ (replaces I3-8 for windows on 0.2.5 and after)

1. **Recording path, additions allowed**: the dev-instance recording path run with the tools at PRE
   and now; every field present in PRE's record (recursively) is present now with an equal value.
   Fields present only now are listed in `equivalence.json`, not judged.
2. **Transcription**: unchanged (the old expressions found verbatim at PRE).
3. **Verdict parity on the release commit** (tool-closed over `RUNNERS`): for each of the four
   runners, the counted reports in its evidence `runs/` whose bound host commit starts with
   `release.json`'s `commit` are found by the tool (≥ 1 each); each re-scores to the verdict
   `RUNNERS` requires and red-cases all red under the current tools at the equivalence check; and
   each report's recorded runner sha256 equals the current runner file's sha256 (the tool that
   recorded the dev verdict is the tool that will judge litecoreprobe). Today that selects exactly
   one report per runner: assets `2026-09-29T163517+0000` (`3370dca9…`), versions
   `2026-09-29T182723+0000` (`c8855e8e…`), host entry `2026-09-29T183110Z` (`399cb112…`), locks
   `2026-09-29T174033+0000` (`4c507d3a…`), each recorded by the runner file as it is now.
4. **Binding across the window**: unchanged (runner and module sha256, `wasm_sdk_probe/` tree, last
   commit, porcelain, interpreter versions equal at the check, window start and window end).

Dropped: the PRE-era rows. Reason: their purpose (the `--ddev-root` change is neutral) was met in
the 0.2.1 counted window; since then the scorers changed on purpose and were re-counted, so the
rows now measure "have the criteria evolved", which they have.

Form (CLAUDE.md §9): written before any 0.2.5 window (none has run); forced by a named measurement
(`equivalence.json` above); I3-8′.1 and .3 are per-instance properties / tool-closed over `RUNNERS`
and the release record; closes when the 0.2.5 counted window lands. Count semantics: no 0.2.5
window exists, nothing to reset.

## Questions for the reviewer

- Does I3-8′ still catch what I3-8 was meant to catch? Find a change to a runner or to its
  recording path that makes litecoreprobe's verdicts incomparable with the dev instance's, yet
  passes I3-8′.
- Is "additions allowed" in .1 a hole (could a new field change a verdict while every old field
  stays equal)?
- Is the runner-sha condition in .3 sufficient, given the runners import shared modules
  (`check_m3_skeleton_open.py`, `probe_m3_assets.py`, `package_m3_engine.py`, …) whose shas are not
  in the reports?
- Is dropping the PRE rows losing anything that I3-8′.1 and .3 do not cover?
