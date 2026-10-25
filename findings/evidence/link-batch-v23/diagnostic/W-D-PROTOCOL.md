# W-D diagnostic topology protocol, before candidate browser execution

This implements existing ordered-command specification9.2,16.5 and the private-input clarification19. It adds no public ABI6 feature or new gate population. No candidate WASM/browser result is established by the source or synthetic tests here.

## Population and inputs

The executable population is `tools/v23_wd_cases.py`: all seven deciding native D1–D6 arms (including d2p), one plain P2 merge, and the four predeclared D7 shipping-core limitation positions. Exactly both browsers × five rounds ×12 cases =120 cells are needed. Empty, missing, extra or duplicate populations are NOT_ESTABLISHED. Native deciding arms are derived from `native/ordered-commands/tool/run_arms.py`; an unhandled added native arm makes the mapping fail rather than silently disappear. The actual JS fixture table is tested against that population.

Every case uses the exact existing native FODT fixture bytes. The private HTTP alias and C API file name end in `.odt` because the current C entry refuses `.fodt` suffixes. This does not claim a public FODT capability; successful content detection remains to be observed on the actual candidate. Record the source fixture SHA256 and actual open request name. A preparation trial may use a separate fresh output path and is never merged into the five-round reading.

The module `web/v23-diagnostic-wd.js` uses the generic instrumented private page's `arm=wd&caseId=...` hook. Setup follows the native sequence. D1–D6 trigger+two operations are issued immediately in one Promise burst, bypassing only the shell serial queue. The reader requires those three actual posted inputs to precede the first terminal response. Public actions still use the original ABI5 gesture contract. Closed private inputs4–8 provide only range Left, ShiftLeft/Right and native L's ShiftEnd/Home; the shared ordered engine key path supplies their effects and completions. Every input is labeled public/private and independently checked against the actual worker request stream. Unknown operations outside the protocol's explicit initialization/save/state/selection observers are refused by the reader.

D6's click uses the actual state query completed after the third Right response and before the first setup Left request. Its x and vertical-midpoint y must match the real click payload. The reader does not trust only a page-supplied clickTarget. d4 requires enabled:true and a true Bold witness from the matching successful wire response; page result labels must equal the actual responses for all actor inputs. These controls prevent an idempotent format or wrong click from being accepted on an accidentally equal save.

Save precedes L's selection observer, as in native S,L. Saved ODT styles/content XML are joined into the same native shape reader, preserving paragraph text/list/style/indent/run weights. The expected D1–D6 shape and L prefix/suffix come from five clean, stable native seq rounds; merge comes from the separately passed DELETE-Q direct reference. No expected landing is invented from the new implementation. D7 instead compares the same-process before/after saves and requires immediate verified-boundary-noop with unchanged revision, preserving the registered unclosed limitation.

## Evidence and reading

The runner records SHA256 for the actual local instrument import graph plus runner, reader and case sources. It records the copied W-D module in the retained mirror; the reader compares that executed copy to the recorded source. The actual candidate profile and all four artifact hashes must bind the explicit owner-linked WASM pin. Ordinary W-D paths require zero proof-absent events. Missing/unreadable evidence gives NOT_ESTABLISHED; clean observed deviations give FAIL. Neither is a pass. A W-D pass establishes topology using the declared private inputs, not public Shift/range support.

After the actual owner diagnostic link, run each case from the repository root using its fixture name from the executable table, with a fresh output directory and the exact actual WASM SHA256. For example:

```bash
python3 -I wasm_sdk_probe/tools/run_v23_diagnostic.py \
  --wasm-sha256 ACTUAL_CANDIDATE_SHA256 \
  --fixture findings/evidence/link-batch-v23/native/ordered-commands/fixtures/abcd.fodt \
  --fixture-name wd-d2.odt --arm wd --case-id d2 --rounds 5 \
  --output findings/evidence/link-batch-v23/diagnostic/wd-candidate-01/d2
```

The remaining11 case directories use the corresponding native fixture. The reader receives all12 `report.json` paths, `--profile-dir wasm_sdk_probe/dist/profiles/e2-editor-v23-diag` and the same `--wasm-sha256`. It refuses a partial case set. Existing runner browser lock and owned process cleanup apply. Do not touch host/ddev/documents or modify frozen profiles. Keep every interrupted/failed attempt; no in-place reruns or preferred-result accumulation.

## Pre-execution controls and audit

`python3 -I wasm_sdk_probe/tests/test_v23_wd_reader.py` passes7 synthetic test groups: all12 actual-native-shape cases, actual JS population,16 deliberate invalid-record controls, exact120-cell population and copied-instrument tampering. These are not browser evidence. The native Astra reviewer found four real pre-fix false greens (disabled Bold, false raw Bold result, wrong click coordinates and an extra click request); each is now a rejecting control. The original native JSON-string landing representation was also checked directly and normalized before comparison. The recorded passing output is `wd-reader/unit-controls-01.txt`.
