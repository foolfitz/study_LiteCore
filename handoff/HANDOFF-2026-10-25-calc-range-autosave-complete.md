# Calc range formatting and autosave complete — host 0.2.37 installed

This supersedes the status/next-work portions of `HANDOFF-2026-10-25-calc-range-autosave-await-build.md` and its build/host runbooks. The owner completed the requested build, and the authorized short-term batch is finished. **No remaining human/build blocker in this batch.** Do not restart full K, v23 or closed manual tests automatically.

## Current identities and state

- Study main; final product correction `d9eb3e60` shares format eligibility between toolbar and shortcuts and refreshes controls after drag. Source/criteria/evidence commits preserve each bounded unit.
- Host `/home/jiajun/Projects/Nextcloud_Apps/litecore`: clean main **2f7a1193e3c296ea1c51dabe470fd2b289d3279b**, installed **0.2.37**, package **754ae8eafd15edda**, manifest SHA **51c3552f9cd8b9db6d3d5f061f0470af170ecf901e5f176b4c0cf46ccb517842**.
- Frozen **ods-editor-v2**, capability bits **522291**, wasm **5bc53490b95fa7a0f7f9ff2e26a6e02cd480e9867171a89d0e1ddd13f035c96f**, worker **0bed22bdb979138f1f0c23bd41bc05896e14f69e29fba10d4e42ccbcda5e1de9**. Owner loader **f61796cd…**, manifest **2a9b8a82…** and shared filesystem bytes retained exactly; all six hashes are in host release/freeze evidence. The owner performed native compilation/linking; the agent only copied assets/profile and packaged.
- Writer **e2-editor-v22 / f7a40bcc**, readonly **ods-viewer-v3 / ebb7e0cb** and predecessor Calc v1 remain untouched. E1-C **187706b2dcb07d2b** intact. The package has 46 files: 35 complete old records identical, four existing Calc files changed, six v2 files and one autosave module added, six v1 served paths removed. Old frozen files/archive remain.
- Actual ddev before/after identical: **litecore running as found**, fgp-nc/nc-bridge paused, all others stopped. Existing lock list exactly **[24674]**. Owner24920 path `LiteCore 手動驗收 2026-10-25/Markdown 焦點測試.odt` remains **31,008 bytes / a84629657cf01ea0adeb26991c6f62932e2df601637ecaee0b1fa6721afa6adb**. No global lock writes, owner-file restores or root commands.
- Test folder/share/user deleted; independent folder404/user-absent queries pass. Own locks released normally, **ownedUnlocks: []**. Disposable 22 native profiles removed; observations retained. Isolated host worktree removed after direct comparison with archive/live; branch `host-0.2.37` retained.
- Full K/global pins/BINDING/chain deferred, nominal shipped host **0.2.26**. Section34.4 **+0/+0**, cumulative **47/27**. The unrelated pre-existing untracked `codex-claude-code-delegation.md` remains intentionally uncommitted.

## Delivered finite contract

Multi-cell B/I/U uses one explicit rectangle, sheet, expected revision and boolean target. Native operations6–9 append to the existing cell ABI; one `XMultiPropertySet` pattern includes Latin/Asian/Complex font items. At most **65,536 logical cells**, including hidden/empty cells. Fully contained merges are allowed; boundary-crossing merges refuse the entire operation without expansion. Protected sheets require a uniformly unlocked protection aggregate; ambiguity is conservatively refused. Known refusals do not mutate; unknown post-mutation outcomes block further writes. No crash rollback is claimed.

Mixed format is `null`/`aria-pressed="mixed"`; mixed/off→on, all-on→off. Preserve active anchor/selection, invalidate before emit, refresh endpoint geometry. Toolbar and Ctrl/Meta+B/I/U share ready/writable/no-busy/no-selection/no-buffer/no-drag eligibility. The focused address field survives render and normalizes on blur. Prior direct entry/F2/selection semantics remain; the owner had already accepted them manually.

Autosave is HOST-only and **committed-model-only**: 30-second idle, five-minute dirty cap plus at least three quiet seconds, hidden attempt when eligible. It never forcibly commits active draft/IME. Pending selection/input/drag, busy/save/manual pending, errors and uncertainty defer it. `save(...,{commitDraft:false})` exports committed state while preserving new draft input. Manual save defaults to commit. Copy/stranded/other save failure pauses retry; explicit manual success to original resumes, sticky-copy target stays paused. Existing host owns conditional writes, locks, stranded bytes and leave guards. Standalone pages do not auto-download; no async unload completion promise.

## Authoritative evidence and readers

Canonical spec append-only through **section22**. Owner report: `research/2026-10-25-calc-range-autosave.md`. Evidence READMEs: `findings/evidence/calc-range-autosave/README.md` and `findings/evidence/host-0.2.37/README.md`.

1. Native **22/22**, `native-01/report.json`, including direct native65536/65537, protected/merge/hidden/mixed/idempotence. Exact owner build hashes verified before execution.
2. Final **range-browser-03: 240/240**, Chrome/Firefox each N=3, 40 checks/run; **six views / 156 actual DOM tiles** match direct engine; independent ODS script-family XML and new-session reopen. Reader rejects six controls, including actual corrupted ODS style.
3. Final **auto-v2-02: 108/108**, Chrome/Firefox each N=3, 18 checks/run, **18 ODS exports**; actual engine/typing with a deterministic host double. Reader binds wrapper/native files/current source and rejects six controls. This is distinct from actual WebDAV evidence.
4. Final **cell-v2-02: 62/62**, both browsers N=1, unchanged single-cell input/formula/format/protection/download/reopen population. Source units **59/59** plus **four XML resolver tests**; format-entry mutation census **15/15** rejected.
5. Actual **host-0.2.37/range-autosave-host-01: 54/54**, both browsers editable and readonly routes; true toolbar range toggles, two production autosaves/browser, real If-Match/token/ODS PUTs, **four independent server GET ODS**, **two views / 56 actual DOM tiles**, >30s draft retention, new trusted typing during a held real export, cancel/normal leave/reopen/lock release. Host reader rejects **seven** controls and verifies fresh preservation facts.
6. Offline package zero problems, **22/22** red controls. Guarded install 20:06:08–20:06:22 Asia/Taipei, maintenance disabled and three unauthenticated routes401. Archives and rollback committed before live mutation. Post-test live/isolated engine bytes directly match immutable archive.

Read artifacts without browsers/services:

```bash
python3 wasm_sdk_probe/tools/read_calc_range_format.py findings/evidence/calc-range-autosave/range-browser-03 --red-cases
python3 wasm_sdk_probe/tools/read_calc_autosave.py findings/evidence/calc-range-autosave/auto-v2-02 --red-cases
python3 wasm_sdk_probe/tools/read_calc_range_autosave_host.py findings/evidence/host-0.2.37/range-autosave-host-01 --release findings/evidence/host-0.2.37/release.json --safety-dir findings/evidence/host-0.2.37 --red-cases
```

Keep accepted build/mirror directories: readers verify the recorded file hashes and actual artifact bytes. Old cohorts have old source identities; do not replace their hashes or present them as current candidate acceptance. `range-browser-02` and `auto-v2-01` passed before the shortcut correction and remain historical; current authoritative cohorts are03/02 respectively.

## Archives, rollback and provenance

- Exact raw successor: `wasm_sdk_probe/build/archive/ods-editor-v2-5bc53490-worker-0bed22bd`.
- Exact installed engine package: `wasm_sdk_probe/build/archive/host-0.2.37-engine-754ae8eafd15edda` (94 files including attribution, external SHA list).
- Predecessor package: `wasm_sdk_probe/build/archive/host-0.2.36-engine-2b17a0e790b24eb3`.
- `findings/evidence/host-0.2.37/rollback-package.sh` is prepared, not executed; functional rollback restores the predecessor engine while retaining host label0.2.37. Never blindly rerun it after later upgrades.
- `install-0.2.37.sh` is historical and requires parent0.2.36; **do not rerun against current main**. Source worktree was removed; branch and archives retained. New changes need their own exact package/guards.

Preserved failures: browser01 reached38 then its XML reader assumed cell-local style names. Actual ODS hoisted formatting into column defaults; independent resolver now follows ODF1.3 property/default/parent rules and repeats, without loosening format expectations. Earlier timer/address-input failures and pre-criteria/interrupt/lock-busy runs remain classified in the evidence README.

Astra reusable canonical ID **`/root/astra_calc_scope`**, acting under owner delegation, supplied scope, implemented/reviewed source, adjudicated reviews and independently read final release/host/preservation artifacts to close the finite batch. Completed Claude source reviews: autosave03 **4b697d5f-b933-4ee0-834e-662ce50d0543**, successor05 **3271b97d-adf0-42d5-80df-481aa232cd86**; raw English requests/results/dispositions retained for resume. The successor excerpt's original conditional repros had unsupported chain premises, but full-chain audit exposed a real stale-enabled shortcut bypass. It was demonstrated with actual page/session source plus fake host, corrected in d9eb3e60, then replayed once under predeclared section21. Review timeouts01/02/04 are not approvals.

## Remaining limits and next work

No required work remains for this batch. Ordinary cell-commit waiting still has the pre-existing unmeasured continuous-key-reception limitation; real OS IME is not established. Arbitrary concurrent external SDK callers, rich text, full Calc merge closure and drag autoscroll were not added to this finite contract. Future requested work needs its own criteria; do not reopen these closed gates on hypothetical concerns.

Use Taiwan Traditional Chinese with the owner; English in evidence/upstream/handoff. Preserve owner documents, unrelated locks, frozen identities and actual shared service state. Compiling make remains the owner's job absent explicit applicable authorization; never run sudo/su/doas or root system modifications. Keep cohesive English commits with Codex coauthor and no session identifiers in commit messages.
