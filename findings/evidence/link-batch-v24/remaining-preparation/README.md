# Fresh R1/S1-S4 preparation after complete S5

SPEC section 19 precedes all fresh counts. The owner authorized agent execution while away.
Original S5 is complete PASS (1,176), original R1 refused on external Zen CPU 105.8% with zero
cells, and selection never started. The original cohort/status/config/tools remain frozen.

The new `v24_remaining_counts` verifier runs the original verifier's code object with exactly
two globals changed: `KINDS` and `stage_spec`. The latter names new collector/judge entry points.
The original launcher, collector, judge, and completion-reader code are unchanged. New wrapper
entry points install only the named verifier override; the original 38-file plan stays identical.
The extra orchestration closure is tool-generated, frozen separately, and checked live/by archive.

Before any fresh count, controls must establish: original code-object identity and two-global
diff; same config/product/populations; unmodified new cohort dry-run; altered case/browser list,
source S5 receipt, orchestration source/archive or override rejected; valid launch admission
accepted but wrong V0 refused; missing/empty status earns no complete population; existing status
refuses launch without V0/browser work. Controls run against a separate scratch declaration only.
Default if controls fail: no remaining count may start. No control earns a browser cell.

The final combined reader re-reads original S5 raw artifacts, not just its verdict, and reads
fresh R1/S1-S4 with the original completion code object adapted only at verifier lookup. All three
populations must hold for `V24_SELECTION_COUNTS_HOLD`. No CPU threshold or retry rule is relaxed.

Qualification: `python3 -m unittest discover -s wasm_sdk_probe/tests -p test_v24_remaining_counts.py -v`,
6/6 PASS in 100.422 s (`controls-01.stdout.txt`). The controls include the original raw S5 reread,
code-object/two-global identity, six receipt/population/override mutants, a re-hashed archive with
one member removed, missing/empty status, admission with a real retained V0 receipt versus wrong
hash, CLI dry-run and duplicate-status refusal. The scratch declaration is never a counted run.
