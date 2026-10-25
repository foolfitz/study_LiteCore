# Adversarial review: v23 diagnostic build preparation

Review only supplied source; do not use tools. Identify concrete blocking correctness defects (not stylistic or already disclosed limitations). Keep the response short. Owner will compile later. No engine integration or native restoration success is claimed. Native RESET original cohort just failed 15/15 continuation selection while content/undo/caret matched; alternative native measurement is being prepared. Build remains unready until engine/native gates. We want errors in diagnostic-only exports, worker behavior, profile contract or build controls. Private diagnostic operations must use existing SDK timeout, add no public capabilities/actions, and be absent in later feature builds.


## wasm_sdk_probe/tools/build_e2_v23_diagnostic_profile.py
```
#!/usr/bin/env python3
"""Package candidate C on ABI 5 without changing the inherited public contract.

This wrapper is diagnostic-only. v5/v4 builders and their frozen users remain
unchanged; the private export is not an editor action or an SDK capability.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_e2_editor_v5_profile as v5
from check_v23_diagnostic_build import read_wasm

PROFILE = "e2-editor-v23-diag"
PRIVATE_EXPORT = "_oxsdk_v23_diagnostic"


def contract_problems(candidate: dict, reference: dict) -> list[str]:
    problems = []
    if candidate.get("profile") != PROFILE:
        problems.append("candidate must be the exact v23 diagnostic profile")
    if reference.get("profile") != "e2-editor-v22":
        problems.append("reference must be the frozen v22 profile")
    if candidate.get("editorContract", {}).get("abiVersion") != 5:
        problems.append("diagnostic editor ABI must remain 5")
    if candidate.get("editorContract") != reference.get("editorContract"):
        problems.append("diagnostic public editor contract differs from v22")
    if candidate.get("capabilities") != reference.get("capabilities"):
        problems.append("diagnostic public capabilities differ from v22")
    return problems


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--exports", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    known, _ = parser.parse_known_args(argv[1:])
    if known.profile != PROFILE:
        raise SystemExit("this builder only packages " + PROFILE)
    problems = read_wasm(known.wasm.read_bytes())
    if PRIVATE_EXPORT not in known.exports.read_text().splitlines():
        problems.append("missing private diagnostic export")
    root = Path(__file__).resolve().parent.parent
    expected_worker = (root / "sdk/sdk-worker.js").read_bytes() + (
        root / "sdk/v23-diagnostic-worker-tail.js").read_bytes()
    if known.worker.read_bytes() != expected_worker:
        problems.append("worker is not the base worker plus diagnostic tail")
    if problems:
        raise SystemExit("; ".join(problems))
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        code = v5.main(argv)
    if code:
        return code
    manifest_path = known.output / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    reference = json.loads((root / "dist/profiles/e2-editor-v22/sdk-manifest.json").read_text())
    problems = contract_problems(manifest, reference)
    if problems:
        # Do not leave an invalid candidate manifest that make could accept.
        manifest_path.unlink()
        raise SystemExit("; ".join(problems))
    summary = json.loads(printed.getvalue())
    summary["diagnosticOnly"] = True
    summary["manifestSha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```


## wasm_sdk_probe/sdk/v23-diagnostic-worker-tail.js
```

// Concatenated only into e2-editor-v23-diag's worker. No public SDK method,
// action id or capability is added. The harness uses Engine._request so the
// existing SDK timeout/cancellation path, including its 30 s default, applies.
const v23ProductHandleRequest = handleRequest;
handleRequest = function handleV23DiagnosticRequest(request) {
  if (request.operation !== "v23Diagnostic")
    return v23ProductHandleRequest(request);
  if (!moduleInstance || activeManifest?.profile !== "e2-editor-v23-diag"
      || activeManifest?.editorContract?.abiVersion !== 5) {
    postResponse(request.requestId, false, {
      code: "UNSUPPORTED_OPERATION",
      message: "private v23 diagnostic requires the initialized diagnostic profile",
    });
    return;
  }
  const kind = request.payload?.kind;
  if (![1, 2, 3].includes(kind) || !Number.isInteger(request.requestId)
      || request.requestId <= 0 || request.requestId > 2147483647) {
    postResponse(request.requestId, false, {
      code: "INVALID_ARGUMENT", message: "invalid private v23 diagnostic request",
    });
    return;
  }
  // 1: queued never-return; 2: queued missing-proof; 3: direct JS-thread LOK.
  // The engine checks that kind 3 has an open document. It may never return.
  accept(request, () => callStatus("oxsdk_v23_diagnostic",
    ["number", "number"], [kind, request.requestId]));
};

```


## wasm_sdk_probe/tests/v23_diagnostic_worker_test.cjs
```
// Run the actual frozen base plus the private tail in a worker-shaped VM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'sdk/sdk-worker.js'), 'utf8')
  + fs.readFileSync(path.join(root, 'sdk/v23-diagnostic-worker-tail.js'), 'utf8');
const messages = [], calls = [];
let listener;
const context = vm.createContext({TextEncoder, Map, Set, console,
  self: {addEventListener: (kind, fn) => { listener = fn; },
    postMessage: msg => messages.push(msg)}});
vm.runInContext(source, context);
const send = (operation, kind, id = 1) => listener({data: {
  protocolVersion: 1, kind: 'request', requestId: id, operation, payload: {kind}}});
send('v23Diagnostic', 1);
assert.equal(messages.pop()?.error?.code, 'UNSUPPORTED_OPERATION');
context.mockCall = (...args) => {calls.push(args); return 0;};
vm.runInContext(`moduleInstance = {ccall: mockCall};
  activeManifest = {profile:'e2-editor-v22', editorContract:{abiVersion:5}};`, context);
send('v23Diagnostic', 1);
assert.equal(messages.pop()?.error?.code, 'UNSUPPORTED_OPERATION');
assert.equal(calls.length, 0);
vm.runInContext(`activeManifest.profile='e2-editor-v23-diag';
  activeManifest.editorContract.abiVersion=6;`, context);
send('v23Diagnostic', 1);
assert.equal(messages.pop()?.error?.code, 'UNSUPPORTED_OPERATION');
vm.runInContext('activeManifest.editorContract.abiVersion=5;', context);
for (const kind of [0, 4, '1', null]) {
  send('v23Diagnostic', kind);
  assert.equal(messages.pop()?.error?.code, 'INVALID_ARGUMENT');
}
for (const id of [0, -1, 2147483648]) {
  send('v23Diagnostic', 1, id);
  assert.equal(messages.pop()?.error?.code, 'INVALID_ARGUMENT');
}
for (const kind of [1, 2, 3]) {
  send('v23Diagnostic', kind, kind);
  assert.equal(calls.at(-1)[0], 'oxsdk_v23_diagnostic');
  assert.deepEqual(Array.from(calls.at(-1)[3]), [kind, kind]);
  assert.equal(vm.runInContext(`pending.has(${kind})`, context), true);
}
assert.equal(messages.length, 0); // acceptance is not a fabricated completion
context.mockCall = () => 1;
vm.runInContext('moduleInstance.ccall=mockCall;', context);
send('v23Diagnostic', 2, 9);
assert.equal(messages.pop()?.error?.code, 'INVALID_ARGUMENT');
assert.equal(vm.runInContext('pending.has(9)', context), false);
send('notAnOperation', 1);
assert.equal(messages.pop()?.error?.code, 'UNKNOWN_OPERATION');
console.log('private diagnostic worker: guards, dispatch, pending and product delegation pass');

```


## wasm_sdk_probe/tests/v23_diagnostic_packaging_test.py
```
#!/usr/bin/env python3
"""Contract controls use the complete actual v22 contract as their population."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from build_e2_v23_diagnostic_profile import contract_problems, PROFILE


class DiagnosticContract(unittest.TestCase):
    def setUp(self):
        self.reference = json.loads((ROOT / 'dist/profiles/e2-editor-v22/sdk-manifest.json').read_text())
        self.candidate = copy.deepcopy(self.reference)
        self.candidate['profile'] = PROFILE

    def test_inherited_contract(self):
        self.assertEqual([], contract_problems(self.candidate, self.reference))

    def test_v22_cannot_masquerade_as_diagnostic(self):
        self.assertTrue(contract_problems(self.reference, self.reference))

    def test_abi6_is_feature_only(self):
        self.candidate['editorContract']['abiVersion'] = 6
        self.assertTrue(contract_problems(self.candidate, self.reference))

    def test_every_action_is_inherited_verbatim(self):
        for name in self.reference['editorContract']['actions']:
            with self.subTest(action=name):
                changed = copy.deepcopy(self.candidate)
                del changed['editorContract']['actions'][name]
                self.assertTrue(contract_problems(changed, self.reference))

    def test_new_action_is_refused(self):
        self.candidate['editorContract']['actions']['invented-shift'] = {'id': 999, 'gestures': []}
        self.assertTrue(contract_problems(self.candidate, self.reference))

    def test_diagnostic_capability_is_not_public(self):
        self.candidate['capabilities'].append('v23-diagnostic')
        self.assertTrue(contract_problems(self.candidate, self.reference))

    def test_reference_identity(self):
        self.reference['profile'] = PROFILE
        self.assertTrue(contract_problems(self.candidate, self.reference))


if __name__ == '__main__':
    unittest.main()

```


## New Makefile blocks
```make
define link_v23_diagnostic
	$(CXX) $(1) \
		-L$(LOBUILD)/instdir/program $$(cat $(LINKDEPS)) \
		-pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm --no-entry -Oz \
		-sMODULARIZE -sEXPORT_NAME=createProbeModule \
		-sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0 \
		-sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=1048576 \
		-sSTACK_OVERFLOW_CHECK=2 \
		-sFORCE_FILESYSTEM=1 -sWASM_BIGINT=1 -sERROR_ON_UNDEFINED_SYMBOLS=1 -sFETCH=1 \
		-sASSERTIONS=0 -sEXIT_RUNTIME=0 \
		-sEXPORTED_RUNTIME_METHODS=ccall,FS,HEAPU8 \
		-sEXPORTED_FUNCTIONS=@$(2) \
		-Wl,--wrap=_Z18initJsUnoScriptingv \
		--pre-js $(LOSRC)/static/emscripten/environment.js \
		--pre-js $(FS_PRE_JS) \
		-o $(3)
endef
E2_V23D_BUILD := build/e2/editor-v23-diag
E2_V23D_DIST := dist/profiles/e2-editor-v23-diag
E2_V23D_SOURCES := $(E2_C_SOURCES)
E2_V23D_OBJECTS := $(patsubst src/%.cpp,$(E2_V23D_BUILD)/%.o,$(E2_V23D_SOURCES))
E2_V23D_MD4C_INCLUDE := $(LOBUILD)/workdir/UnpackedTarball/md4c/src
# Frozen base worker; the private diagnostic tail is concatenated in build/.
E2_V23D_WORKER_SHA256 := 0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350

$(E2_V23D_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_api.h \
		src/editor_discovery_api.h src/format_readback_text.hpp \
		src/a11y_paragraph_identity.hpp src/merge_key_undo.hpp \
		src/markdown_paste.hpp src/ordered_command_proof.hpp \
		src/ordered_delete_route.hpp src/ordered_poll.hpp $(E2_V23D_MD4C_INCLUDE)/md4c.h Makefile \
		| $(E2_V23D_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -I$(E2_V23D_MD4C_INCLUDE) \
		-DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-DOXSDK_MERGE_KEY_UNDO -DOXSDK_E2_V20_LINK_BATCH \
		-DOXSDK_E2_V21_LINK_BATCH -DOXSDK_MAINLOOP_ENGINE \
		-DOXSDK_E2_V23_LINK_BATCH -DOXSDK_E2_V23_DIAGNOSTIC \
		$(EXTRA_DEFINES) -c $< -o $@

# v22 public exports with one private diagnostic entrance.
$(E2_V23D_BUILD)/exports.txt: $(R5_BUILD)/writer-review/exports.txt Makefile \
		| $(E2_V23D_BUILD)
	cp $< $@
	printf '%s\n' \
		_oxsdk_editor_action \
		_oxsdk_editor_get_state \
		_oxsdk_editor_select_range \
		_oxsdk_editor_place_caret \
		_oxsdk_editor_abi_version \
		_oxsdk_editor_set_action_gestures \
		_oxsdk_document_redo \
		_oxsdk_document_page_rectangles \
		_oxsdk_document_paste_markdown \
		_oxsdk_v23_diagnostic >> $@
	@if grep -q editor_discovery $@; then \
		echo "product export list contains a discovery symbol"; exit 1; fi

# Guarded from the first link, like every product artifact before it.
$(E2_V23D_BUILD)/probe.js: $(E2_V23D_OBJECTS) $(EXTRA_OBJECTS) \
		$(E2_V23D_BUILD)/exports.txt $(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call refuse_unasked_relink,the v23 diagnostic candidate C (ABI 5; unipoll; diagnostic instruments) -- every link mints a new hash)
	$(call link_v23_diagnostic,$(E2_V23D_OBJECTS) $(EXTRA_OBJECTS),$(E2_V23D_BUILD)/exports.txt,$@)

$(E2_V23D_BUILD)/probe.wasm: $(E2_V23D_BUILD)/probe.js
	@test -s $@

# No public worker/API edit: append the private entry to the pinned base.
$(E2_V23D_BUILD)/sdk-worker.js: sdk/sdk-worker.js sdk/v23-diagnostic-worker-tail.js Makefile | $(E2_V23D_BUILD)
	echo "$(E2_V23D_WORKER_SHA256)  sdk/sdk-worker.js" | sha256sum -c --quiet
	cat sdk/sdk-worker.js sdk/v23-diagnostic-worker-tail.js > $@

# ABI 5 and the complete v22 action contract are preserved by the wrapper.
$(E2_V23D_DIST)/sdk-manifest.json: $(E2_V23D_BUILD)/probe.js $(E2_V23D_BUILD)/probe.wasm \
		$(E2_V23D_BUILD)/exports.txt $(E2_V23D_BUILD)/sdk-worker.js \
		sdk/v18-writer-review-manifest.json \
		tools/build_base_no35_pack.py tools/build_r5_profiles.py \
		tools/build_cjk_subset.py tools/build_cjk_subset_ttc_pack.py \
		tools/build_cjk_subset_mono_pack.py \
		tools/build_e2_editor_v5_profile.py tools/build_e2_v23_diagnostic_profile.py \
		tools/build_e2_editor_v4_profile.py tools/build_e2_c_profile.py \
		tools/build_e2_b_profile.py tools/e1_support.py | $(E2_V23D_DIST)
	echo "$(E2_V23D_WORKER_SHA256)  sdk/sdk-worker.js" | sha256sum -c --quiet
	python3 tools/build_base_no35_pack.py --check
	python3 tools/build_cjk_subset_mono_pack.py --check
	python3 tools/build_e2_v23_diagnostic_profile.py \
		--source-manifest sdk/v18-writer-review-manifest.json \
		--loader $(E2_V23D_BUILD)/probe.js --wasm $(E2_V23D_BUILD)/probe.wasm \
		--worker $(E2_V23D_BUILD)/sdk-worker.js \
		--exports $(E2_V23D_BUILD)/exports.txt \
		--profile e2-editor-v23-diag --inline-range-gestures all \
		--page-rectangles --paste-markdown \
		--output $(E2_V23D_DIST)
	@test -s $(E2_V23D_DIST)/probe.js
	@test -s $(E2_V23D_DIST)/probe.wasm
	@test -s $(E2_V23D_DIST)/sdk-worker.js

$(E2_V23D_BUILD) $(E2_V23D_DIST):
	mkdir -p $@

# ---------------------------------------------------------------- v5, a
```
