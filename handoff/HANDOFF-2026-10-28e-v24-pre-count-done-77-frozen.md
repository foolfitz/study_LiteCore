# Handoff: v24 §6.3 all hold, generation 77 frozen; §6.4 (the counts) next

Supersedes `HANDOFF-2026-10-28d-v24-linked-verified-page-cut-over.md`. Checkpoint 2026-10-28 ~16:00 +0800. **Nothing is running.** Tree clean except the unrelated untracked `codex-claude-code-delegation.md` (preserve it). 29 commits since `3a0cdc4a` (10-28d).

## Read these first (ruling 1 Addendum 1 §8)

- **I-enter-raw-substring** (declared instrument limit): on v24 the frozen product-path runner's `the-enter-key-reaches-the-document` FAILs in Chrome, every time. Its Shift-arm oracle is the raw substring `A<text:line-break/>B`; v24's typed runs carry `officeooo:rsid` spans, as native keyboard typing does (D-typed-rsid-spans), so the break is present but the substring is not. The property is read by `tools/check_v24_shift_enter.py` (`V24_ENTER_HOLDS` 3/3). Do not re-diagnose it.
- **No edits to the live-asserted set.** 40 paths = `counted-r1-s5-01/cohort.json` instrumentSources (30) ∪ `s5-native/settled-reference-reader-05.json` bindings under `wasm_sdk_probe/` (30) ∪ native run-03 identity sources (12). Reader-05 binds 1,772 files by live hash and **v24's own S5/R1 plan verifies it** (`v24_feature_selection_cases.config()` → v23 `s5()`), so editing e.g. `run_e2_c_product_path.py` or `build_e2_c_shell_bundle.py` breaks v24 itself, not only v23's re-read. E1 tried it and was reverted (`aaea5336`). `findings/evidence/link-batch-v24/pre-count/bound-tool-edits.json` is closed. `tools/run_v24_v0_double_prime.py` prints the 40 paths.
- **Generation 77 was frozen by `--manifest`**, the bundle tool untouched; its default `MANIFEST` stays v76 **by design**. The 10-28d instruction "bump MANIFEST / add v76 to FROZEN_MANIFESTS" is withdrawn. Plain runs of the product-path runner on v24 still name v76 and NE the four arms; A4-v24 needs the wrapper below.

## Decisions this session

- Owner: M2 owner-run (chose B); ruling questions to fable (chose A).
- **Fable ruling 1 (v24 pre-count) + Addendum 1**: `findings/evidence/link-batch-v24/pre-count/rulings/RULING-1.md` (brief `BRIEF-1.md`). T4 rule 2 → 2a/2b with a pinned volatile list, verdict from run 02; Enter = oracle defect, D-typed-rsid-spans declared; (b′) "edit bound tools with V0″" authorised, then **withdrawn** in Addendum 1 after V0″ run 01 exposed the reader-05 binding; 77 by `--manifest`; A4 by in-process MANIFEST rebinding; option B (re-issue the settled certificate) rejected, kept as the fallback for a product-forced edit. Spec appends: §16 (ruling 1) and §17 (Addendum 1, supersedes §16 items 1–3).

## Established (evidence under `findings/evidence/link-batch-v24/pre-count/`, each README written before its run)

| Item | Result | Where |
|---|---|---|
| (vi) | stale v23 engine pair → init `DECLARED_EXPORT_MISSING`, both browsers, + control | `page-gates/` |
| (vii) | leafless manifest → `PAGE_BUILD_MISMATCH`, 0 `insertText` over three typing attempts, + control | `page-gates/` |
| J-red | 36/36; route-only (iii′) added because (iii) is caught by both T2 clauses; T3 (v) done | `j-red/` |
| (i) | scratch SDK routes typing to paste → T2 FAIL naming the route; T1 alone passes | `i-red/` |
| M2 | **168/168 PASS** (owner-run, 65 min), 448 insert replies, 0 proof-absent | `m2/` |
| T5 | 12/12: typed `""`/`x`; Ctrl+V `A1 cell textx`/`B1 cell textx#` (169) | `t5/` |
| T4 | **holds** by `read-02.json` (rule 1 41/41; 2a 5/5, 2b 3 leaf-equal); Enter frozen-oracle FAIL + replay PASS; run-02 differential had one intermittent Chrome change (`editing-a-long-document-stays-responsive`, an ink-trigger race; the insert succeeded in 22 ms), moved back in run 03 | `t4/` |
| D-typed-rsid-spans | M1 native key vs `.uno:InsertText`: same rsid/span structure 48/48, both native runs | `rsid-spans/` |
| Generation 77 | digest `56ce44c7…` (= candidate), 7 explicit exclusions, file `f8a7bd81…`; Makefile:4843 passes `--manifest`; v24 `identity()` pins it | `freeze-77/` |
| V0″ | `V0PP_HOLDS` before (run-03) and after (run-04) the freeze; reds V-1, V-3 | `v0-double-prime/` |

Also: **finding 170** — the native M1 harness exits 1 with `Unspecified Application Error` after its last record, 2/2 (`m1-rerun/`); native only, cause not traced.

## Named limits and open observations (not gates)

- T4 reader: checks recorded at the same instant share one step interval and only the first gets its requests (t4/README "shared step intervals"). Fix in the next reader of this kind, not retroactively.
- `make test-e2-c-reachability` is red at `audit_product_path_coverage.py` (pre-existing since v21: paste-markdown paths, 7 unattributable listeners). The bundle line itself is green on v77.
- (vii) observation: after `PAGE_BUILD_MISMATCH` the state pill flips from `expired` back to `ready` while the expired panel stays (`page-gates/README.md`); same path on a wrong wasm; untriaged.
- Inherited from v23, reproduced leaf for leaf on v24 (not T4's blessing): `a-boundary-arrow-press-does-not-cost-the-work` (Chrome FAIL / Firefox NE), `clear-format-removes-every-inline-format` and `every-inline-format-reaches-the-document` (NE).
- Design note (ruling): reader-05's static closure binds the product-path runner via `run_merge_wasm_shakedown.py:96` though no reader executes it.

## Next (spec §6.4; V0″ `V0PP_HOLDS` before every count, `python3 -I tools/run_v24_v0_double_prime.py --out <new>`)

1. **Counted S5-v24 mode.** `tools/run_v24_feature_selection.py` is preparation-only. Counting needs v23's counted machinery shape (frozen config + instrument closure + launch/status, `counted-r1-s5-01/` and `run-counted-r1-s5.py`) re-done for v24 in new files, a fresh directory, both browsers, full population (588), T1 + T2 (the reader `tools/judge_v24_feature_selection.py` derives S5 only). Then R1-v24 (144) and S1–S4 (234): the v24 reader must derive `inspect` for those (they currently answer NE).
2. **A4-v24**: `tools/run_v24_four_arms.py` (rebind `build_e2_c_shell_bundle.MANIFEST` to v77 before importing the runner; record the override) + a v24 four-arm judge wrapper (profile/ABI pins at `judge_v23_product_four_arms.py:198`; require the identity to name frozen 77) + reds (no override → NE; v78 → refusal; run 01's v76 dirs → NE).
3. Each count is hours: ask the owner (detached vs owner-run) before starting; no DDEV here.
4. Then host package, BINDING, K (count chain; ledger `research/2026-10-25-count-batching-and-next-work.md`; ask for the DDEV slot).

§34.4 this batch: fixed because of a run **1** (`read_v24_t4.py` rule 2), because of review **0**. E1 landed and reverted; the runner is byte-identical throughout. My own tools had three errors caught by their own checks before any verdict: the rsid reader's family filter (non-vacuity), V0″'s relative `--out` (run-02), and a README naming the wrong flipped leaf (R-c).

Constraints unchanged: no sudo; object-producing builds owner-run; never overwrite frozen v23; evidence/handoff in English, conversation and specs zh-TW.
