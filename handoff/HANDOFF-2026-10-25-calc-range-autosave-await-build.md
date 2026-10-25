# Calc range formatting and autosave — owner build boundary

This supersedes the next-work/status portion of `HANDOFF-2026-10-25-calc-input-range-complete.md`. The owner has manually accepted that prior batch and explicitly requested multi-cell B/I/U and autosave. Do not repeat the accepted manual tests or restart full K.

## State and required human action

The source, protocol, unit controls and executable continuation tools are prepared. **No native compile, WASM link, frozen v2 profile, new package or live install has been performed.** Installed host stays **0.2.36 / 702bad6d72be5a70d9e3aaca3290b99f0d9fc1d5 / package 2b17a0e790b24eb3**. Host source main is clean; `unchanged-identities.json` verifies the installed manifest and frozen Calc v1/Writer v22/viewer v3 identities against the prior release.

The owner's standing AGENTS.md reserves compiling make for the owner. The exact reviewed build is in [RUNBOOK-build-calc-range-v2.md](RUNBOOK-build-calc-range-v2.md). It compiles a small native bridge/driver and four SDK objects, then links against existing cores; no LibreOffice core rebuild or root command is needed. Estimate 3–10 minutes, not a measured duration for v2.

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
uptime
pgrep -a make
# When no other build/long measurement is active:
make -j1 build/calc-range-native/calc-cell-native build/ods/editor-v2/profile/sdk-manifest.json
```

The owner should report completion and the printed manifest/hash JSON, or the first compiler/link error with context. Expected profile `ods-editor-v2`, capability bits **522291**, added `cell-range-formatting`, range limit **65536**. No frozen-relink override. Agent preparation used only `make -n` to inspect this graph. Do not infer new compilation permission from this handoff.

## Implemented contract

Native range operations append 6–9 to the existing cell ABI, behind capability bit 18 and `OXSDK_ODS_RANGE`. Explicit part/address rectangle/expected revision/format/boolean target; one native `XMultiPropertySet` pattern, all script families together. No per-cell JS writes. At most 65,536 logical cells including hidden/empty cells. Boundary-intersecting merges refuse the entire operation, contained merges are allowed. Protected sheets require a uniformly unlocked `CellProtection` aggregate; ambiguous protection is conservatively refused even if only other protection flags differ. Post-mutation exceptions/failed confirmation are uncertain and block further writes; no crash rollback is claimed.

Range state is independent of the active anchor: `null` format means mixed, toolbar `aria-pressed="mixed"`; mixed/off→on and all-on→off. Geometry refresh reads the two endpoints after formatting, preserving selection. Frozen v1 still refuses multi-cell formatting. **The product's engine URL remains v1 until native/v2 acceptance.** Only the range browser mirror switches its own URL/symlink to v2 and records the identities.

Autosave is HOST-only and committed-model-only. Timing matches Writer: 30 seconds idle, a five-minute dirty cap with three seconds quiet, hidden visibility attempts when eligible. Active draft/IME/pending input/selection/drag/busy/save/manual-pending/error/uncertainty defer it. `save(target,{commitDraft:false})` exports committed state without ending an edit; manual default still commits. New input during export/host write stays dirty. Copy/stranded/other save errors pause automatic retry, including after new edits; only explicit manual success to original resumes. Sticky-copy destinations stay paused. Existing host handles conditional writes, locks, stranded bytes and leave guards. No automatic standalone download or async unload promise.

The focused address field now survives session-state rendering and normalizes on blur. A deterministic pre-fix red case showed B2 overwritten by A1. Waiting for public ready alone had not explained earlier failures; the ruling preserves that correction and does not claim exclusive causation of every historical setup symptom.

## Evidence and independent readers

Evidence root: `findings/evidence/calc-range-autosave/`; [README](../findings/evidence/calc-range-autosave/README.md) distinguishes accepted reports from all failed/development attempts. Owner-facing report: [research](../research/2026-10-25-calc-range-autosave.md). Canonical spec is append-only through section 19: criteria 17/18 preceded the accepted execution; section 19 records its closure.

- `session-sdk-worker-final.txt`: **45/45** units (session/SDK/worker/host and autosave). Nine clock/default-timer cases; seven autosave mutation controls, six range mutation controls, five synthetic range-reader controls and two profile-freeze controls rejected. These do not prove native execution.
- `e1-c-intact.json`: bundle `187706b2dcb07d2b` intact.
- Accepted finite autosave candidate **`auto-final-05`**: Chrome/Firefox N=3, 18 executable cases per browser/round, **108/108**, with candidate/tool hashes and 18 exported ODS snapshots. `autosave-reader-final.json` passes current source identity, byte hash/XML verification and six red controls. Astra independently read this result and authorized finite mirror/source-preparation closure. The host is a deterministic double; native v2 and real WebDAV/Files/lock acceptance remain **NOT_ESTABLISHED**.

```bash
python3 wasm_sdk_probe/tools/read_calc_autosave.py findings/evidence/calc-range-autosave/auto-final-05 --red-cases
```

Earlier attempts must not be relabeled: development 01/02 exposed DOM timer receiver failure; development 03 passed Chrome. Final 01 started before criteria and was interrupted; 02 refused the private browser lock during cleanup. Final 03 passed five rounds then failed last setup; final 04 also failed setup after waiting for ready and was interrupted. `address-red-01` proves the focused-render overwrite. The fixed final attempt starts from scratch; no successful rounds are combined.

## Delegation and reviews

The owner authorized Astra to decide ambiguity. Reusable canonical ID **`/root/astra_calc_scope`**; source ruling [RULING-2026-10-25-calc-range-autosave.md](RULING-2026-10-25-calc-range-autosave.md). It implemented/reviewed range source, committed-only save, build/probes, and adjudicated the focused address correction. It remains available for follow-up.

English `claude -p` work orders/raw outputs/dispositions are preserved. Completed autosave review 03 session **4b697d5f-b933-4ee0-834e-662ce50d0543** can be resumed. Its nullable-blocker and concurrent-model-commit sequences had false premises in the full snapshot/serialized chain; pre-host failure pausing is intended policy. Astra adjudicated each. Review attempts 01/02 and native 04 timed out without verdict, not approvals. A bare READY control did not use existing login and failed without changing credentials; normal READY succeeded. [Review dispositions](../findings/evidence/calc-range-autosave/review-outcomes.md) preserve the limits.

## Continue autonomously after successful owner build

1. Run the native probe (22 fixture-derived cases) without compiling:

   ```bash
   python3 wasm_sdk_probe/tools/probe_calc_range_native.py --out findings/evidence/calc-range-autosave/native-01
   ```

2. Run actual v2 browser acceptance, Chrome/Firefox N=3 (40 cases/run), then its artifact reader/red controls:

   ```bash
   python3 wasm_sdk_probe/tools/probe_calc_range_format.py --profile wasm_sdk_probe/build/ods/editor-v2/profile --out findings/evidence/calc-range-autosave/range-browser-01 --browsers chrome,firefox --repeats 3
   python3 wasm_sdk_probe/tools/read_calc_range_format.py findings/evidence/calc-range-autosave/range-browser-01 --red-cases
   ```

3. Diagnose native/compiler/harness failures from their payloads; do not alter criteria to preserve an incorrect claim. Use new evidence directories. The old v1 formatting-refusal tests cannot be used as v2 success. Apply focused existing input/selection regression with honest successor expectations. Actual tile comparison, script-family XML, save/reopen, protected/merge/hidden/cap/stale/target checks remain required.
4. After combined v2 acceptance, switch the reviewed candidate URL, archive exact bytes, freeze v2 once, package a fresh host version, prepare guarded install/rollback, and run actual Files range/autosave verification with owned fixtures/locks. Existing host layer already supports `trigger:"auto"` and persistent last-save/copy notices; do not replace its conditional-write machinery.

No ddev or live file/lock writes were made in this preparation. Re-read actual shared service state before future live work; prior state was litecore running, fgp-nc/nc-bridge paused, others stopped. Preserve owner document 24920 and unrelated lock 24674; do not globally clear locks or restore older owner fixtures. No global counts/pins/BINDING/chain/full K change: nominal shipped stays 0.2.26, last section 34.4 cumulative 47/27. The pre-existing unrelated untracked `codex-claude-code-delegation.md` is intentionally preserved.

Use Taiwan Traditional Chinese with the owner; English in evidence/upstream/handoff. Keep cohesive commits with Codex coauthor and no session identifiers in commit messages. Ordinary cell-commit waiting still has the pre-existing unmeasured continuous-key-reception limitation; real OS IME is not established. Neither limitation is reopened as a new manual gate.
