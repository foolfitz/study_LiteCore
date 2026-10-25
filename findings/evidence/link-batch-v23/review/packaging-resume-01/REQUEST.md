Review this narrowly scoped packaging repair adversarially. No tools. Identify only concrete high-impact defects. The owner already compiled four objects and linked WASM, then packaging failed: v22 worker SHA0d55 was wrongly checked against live shared worker0bed (Calc evolved). Chosen repair: use immutable archived v22 worker0d55 + diagnostic tail. Never change live worker or recompile. Resume must validate exactly7 preserved outputs and originallog, all original compiler/core inputs, allow only reviewed packaging changes, compare exact compile/link plan, package, then preserve those7bytes. Default check-only. Existing failed build outputs/log stay immutable; candidate profile never existed. These are local controlled inputs, not untrusted adversarial CLI input. Focus on accidental integrity errors, semantics, and failure cleanup. Do not propose unrelated refactors. Reply with evidence and minimal fix; say no concrete finding if none.

diff --git a/wasm_sdk_probe/Makefile b/wasm_sdk_probe/Makefile
index 2d1648e3..b1241638 100644
--- a/wasm_sdk_probe/Makefile
+++ b/wasm_sdk_probe/Makefile
@@ -1858,8 +1858,14 @@ E2_V23D_SOURCES := $(E2_C_SOURCES)
 E2_V23D_OBJECTS := $(patsubst src/%.cpp,$(E2_V23D_BUILD)/%.o,$(E2_V23D_SOURCES))
 E2_V23D_MD4C_INCLUDE := $(LOBUILD)/workdir/UnpackedTarball/md4c/src
 # Frozen base worker; the private diagnostic tail is concatenated in build/.
+E2_V23D_BASE_WORKER := build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/sdk-worker.js
 E2_V23D_WORKER_SHA256 := 0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350
 
+.PHONY: v23-diagnostic-worker-preflight
+v23-diagnostic-worker-preflight:
+	python3 tools/build_e2_v23_diagnostic_profile.py --check-worker-base \
+		--base-worker $(E2_V23D_BASE_WORKER) --base-worker-sha256 $(E2_V23D_WORKER_SHA256)
+
 $(E2_V23D_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_api.h \
 		src/editor_discovery_api.h src/format_readback_text.hpp \
 		src/a11y_paragraph_identity.hpp src/merge_key_undo.hpp \
@@ -1867,7 +1873,7 @@ $(E2_V23D_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_api.h \
 		src/ordered_delete_route.hpp src/ordered_poll.hpp src/ordered_engine_guards.hpp src/reply_state_reads.hpp \
 		src/ordered_engine_state.inc src/ordered_engine_reply.inc src/ordered_engine_poll.inc \
 		src/ordered_engine_delete.inc src/ordered_format.inc $(E2_V23D_MD4C_INCLUDE)/md4c.h Makefile \
-		| $(E2_V23D_BUILD)
+		| $(E2_V23D_BUILD) v23-diagnostic-worker-preflight
 	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -I$(E2_V23D_MD4C_INCLUDE) \
 		-DOXSDK_EDITOR_DISCOVERY \
 		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
@@ -1904,9 +1910,9 @@ $(E2_V23D_BUILD)/probe.wasm: $(E2_V23D_BUILD)/probe.js
 	@test -s $@
 
 # No public worker/API edit: append the private entry to the pinned base.
-$(E2_V23D_BUILD)/sdk-worker.js: sdk/sdk-worker.js sdk/v23-diagnostic-worker-tail.js Makefile | $(E2_V23D_BUILD)
-	echo "$(E2_V23D_WORKER_SHA256)  sdk/sdk-worker.js" | sha256sum -c --quiet
-	cat sdk/sdk-worker.js sdk/v23-diagnostic-worker-tail.js > $@
+$(E2_V23D_BUILD)/sdk-worker.js: $(E2_V23D_BASE_WORKER) sdk/v23-diagnostic-worker-tail.js Makefile | $(E2_V23D_BUILD)
+	echo "$(E2_V23D_WORKER_SHA256)  $(E2_V23D_BASE_WORKER)" | sha256sum -c --quiet
+	cat $(E2_V23D_BASE_WORKER) sdk/v23-diagnostic-worker-tail.js > $@
 
 # ABI 5 and the complete v22 action contract are preserved by the wrapper.
 $(E2_V23D_DIST)/sdk-manifest.json: $(E2_V23D_BUILD)/probe.js $(E2_V23D_BUILD)/probe.wasm \
@@ -1919,7 +1925,7 @@ $(E2_V23D_DIST)/sdk-manifest.json: $(E2_V23D_BUILD)/probe.js $(E2_V23D_BUILD)/pr
 		tools/check_v23_diagnostic_build.py \
 		tools/build_e2_editor_v4_profile.py tools/build_e2_c_profile.py \
 		tools/build_e2_b_profile.py tools/e1_support.py | $(E2_V23D_DIST)
-	echo "$(E2_V23D_WORKER_SHA256)  sdk/sdk-worker.js" | sha256sum -c --quiet
+	echo "$(E2_V23D_WORKER_SHA256)  $(E2_V23D_BASE_WORKER)" | sha256sum -c --quiet
 	python3 tools/build_base_no35_pack.py --check
 	python3 tools/build_cjk_subset_mono_pack.py --check
 	python3 tools/build_e2_v23_diagnostic_profile.py \

FILE wasm_sdk_probe/tools/resume_v23_diagnostic_packaging.py
#!/usr/bin/env python3
"""Validate preserved link inputs and optionally pack; never run make/compiler."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_e2_v23_diagnostic_profile as packer
from check_v23_diagnostic_build import logical_lines, read_build_log, read_wasm, read_makefile, rule_body, macros
ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / 'wasm_sdk_probe'
BUILD = Path('wasm_sdk_probe/build/e2/editor-v23-diag')
OBJECTS = {'sdk_api.o', 'probe_engine.o', 'unoembind_stub.o', 'editor_api.o'}
EXPECTED = {str(BUILD / name) for name in OBJECTS | {'probe.js', 'probe.wasm', 'exports.txt'}}
PACKAGING_DELTAS = {'wasm_sdk_probe/Makefile', 'wasm_sdk_probe/tools/build_e2_v23_diagnostic_profile.py'}

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def verify_rows(rows, root=ROOT):
    for row in rows:
        path = root / row['path']
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('input escapes repository: ' + row['path'])
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError('preserved input changed: ' + row['path'])

def build_commands(text):
    found = {}
    for line in logical_lines(text):
        args = shlex.split(line)
        if '-o' not in args: continue
        output = args[args.index('-o') + 1]
        if output.startswith('build/e2/editor-v23-diag/') and (output.endswith('.o') or output.endswith('/probe.js')):
            if output in found: raise ValueError('duplicate compile/link output: ' + output)
            found[output] = args
    if set(found) != {'build/e2/editor-v23-diag/' + n for n in OBJECTS | {'probe.js'}}:
        raise ValueError('exact four compiles and one link are required')
    return found

def validate(audit, boundary, build_log, planned_log, root=ROOT):
    if {row['path'] for row in audit['build_artifacts']} != EXPECTED or len(audit['build_artifacts']) != 7:
        raise ValueError('audit must bind exactly seven linked artifacts')
    if (root / audit['link_log']['path']).resolve() != build_log.resolve():
        raise ValueError('build log is not the preserved audited attempt')
    protected = audit['build_artifacts'] + [audit['link_log']]
    verify_rows(protected, root)
    actual, planned = build_log.read_text(), planned_log.read_text()
    problems = read_build_log(actual) + read_build_log(planned)
    if problems: raise ValueError('; '.join(problems))
    if build_commands(actual) != build_commands(planned):
        raise ValueError('planned compile/link commands differ from linked attempt')
    source = json.loads((boundary / 'source-inputs.json').read_text())
    verify_rows([row for row in source['files'] if row['path'] not in PACKAGING_DELTAS], root)
    verify_rows(json.loads((boundary / 'core-inputs.json').read_text())['files'], root)
    current_make = (root / 'wasm_sdk_probe/Makefile').read_text()
    problems = read_makefile(current_make)
    if problems: raise ValueError('; '.join(problems))
    # A stale supplied dry-run cannot conceal changes to current compile/link flags.
    old_make = subprocess.check_output(['git', 'show', source['commit'] + ':wasm_sdk_probe/Makefile'], cwd=root, text=True)
    target = '$(E2_V23D_BUILD)/%.o:'
    if rule_body(current_make, target).replace(' v23-diagnostic-worker-preflight', '') != rule_body(old_make, target):
        raise ValueError('current diagnostic compilation rule changed')
    if macros(current_make)['link_v23_diagnostic'] != macros(old_make)['link_v23_diagnostic']:
        raise ValueError('current diagnostic link macro changed')
    # Only the explicit packaging-base/preflight delta is exempt from the old
    # whole Makefile hash. Header flags and library/source variables also bind.
    normalized = re.sub(r'^E2_V23D_BASE_WORKER := .*\n', '', current_make, flags=re.M)
    normalized = re.sub(r'^\.PHONY: v23-diagnostic-worker-preflight\n.*?\n\n', '', normalized, flags=re.M | re.S)
    normalized = normalized.replace(' v23-diagnostic-worker-preflight', '')
    normalized = normalized.replace('$(E2_V23D_BASE_WORKER)', 'sdk/sdk-worker.js')
    if normalized != old_make:
        raise ValueError('Makefile changed outside the reviewed packaging-only delta')
    problems = read_wasm((root / BUILD / 'probe.wasm').read_bytes())
    if problems: raise ValueError('; '.join(problems))
    packer.checked_base_worker()
    return protected

def package():
    worker = ROOT / BUILD / 'sdk-worker.js'
    output = SDK / 'dist/profiles/e2-editor-v23-diag'
    manifest = output / 'sdk-manifest.json'
    temporary = worker.with_suffix('.js.pending')
    failed = [manifest.with_name('sdk-manifest.failed.json'), worker.with_name('sdk-worker.failed.js'), worker.with_name('sdk-worker.pending.failed.js')]
    if any(p.exists() for p in [worker, manifest, temporary] + failed):
        raise ValueError('existing worker/manifest/failed bytes require a preserved retry decision')
    for script in ('build_base_no35_pack.py', 'build_cjk_subset_mono_pack.py'):
        subprocess.run([sys.executable, str(SDK / 'tools' / script), '--check'], cwd=SDK, check=True)
    try:
        with temporary.open('xb') as stream:
            stream.write(packer.checked_base_worker() + (SDK / 'sdk/v23-diagnostic-worker-tail.js').read_bytes())
        os.replace(temporary, worker)
        args = ['builder', '--source-manifest', str(SDK / 'sdk/v18-writer-review-manifest.json'),
                '--loader', str(ROOT / BUILD / 'probe.js'), '--wasm', str(ROOT / BUILD / 'probe.wasm'),
                '--worker', str(worker), '--exports', str(ROOT / BUILD / 'exports.txt'),
                '--profile', packer.PROFILE, '--inline-range-gestures', 'all',
                '--page-rectangles', '--paste-markdown', '--output', str(output)]
        previous = Path.cwd()
        try:
            os.chdir(SDK)
            code = packer.main(args)
        finally: os.chdir(previous)
        if code: raise RuntimeError('diagnostic packer returned ' + str(code))
        return {name: digest(output / name) for name in ('probe.js', 'probe.wasm', 'sdk-worker.js', 'sdk-manifest.json')}
    except BaseException:
        # Failed bytes remain inspectable under non-target names.
        for path, target in zip([manifest, worker, temporary], failed):
            if path.exists(): os.rename(path, target)
        raise

def main():
    parser = argparse.ArgumentParser()
    for name in ('linked-inputs','prelink-boundary','build-log','planned-build-log','receipt'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--package', action='store_true')
    args = parser.parse_args()
    with args.receipt.open('x') as receipt:
        result = {'mode': 'package' if args.package else 'check-only', 'ok': False,
                  'auditSha256': digest(args.linked_inputs)}
        protected = None
        try:
            protected = validate(json.loads(args.linked_inputs.read_text()), args.prelink_boundary, args.build_log, args.planned_build_log)
            if args.package: result['packaged'] = package()
            verify_rows(protected)
            result['linkedArtifactsUnchanged'] = True
            result['ok'] = True
        except BaseException as error:
            result['error'] = str(error)
            raise
        finally:
            if protected is not None:
                try:
                    verify_rows(protected)
                    result['linkedArtifactsUnchanged'] = True
                except BaseException as error:
                    result.update(linkedArtifactsUnchanged=False, preservationError=str(error), ok=False)
            receipt.write(json.dumps(result, indent=2) + '\n')
    return 0 if result['ok'] else 1
if __name__ == '__main__': raise SystemExit(main())

FILE wasm_sdk_probe/tools/build_e2_v23_diagnostic_profile.py
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
ROOT = Path(__file__).resolve().parent.parent
BASE_WORKER = ROOT / "build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/sdk-worker.js"
BASE_WORKER_SHA256 = "0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350"


def checked_base_worker(path=BASE_WORKER, expected=BASE_WORKER_SHA256):
    path = Path(path)
    if path.resolve() != BASE_WORKER.resolve() or expected != BASE_WORKER_SHA256:
        raise ValueError("diagnostic base must be the exact frozen v22 archive identity")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("frozen v22 worker hash mismatch")
    return data

# build_e2_b_profile.build_profile binds these to each candidate's own bytes.
ARTIFACT_BINDINGS = {"loaderSha256": "probe.js", "wasmSha256": "probe.wasm",
                     "workerSha256": "sdk-worker.js"}


def contract_problems(candidate: dict, reference: dict) -> list[str]:
    problems = []
    if candidate.get("profile") != PROFILE:
        problems.append("candidate must be the exact v23 diagnostic profile")
    if reference.get("profile") != "e2-editor-v22":
        problems.append("reference must be the frozen v22 profile")
    if candidate.get("editorContract", {}).get("abiVersion") != 5:
        problems.append("diagnostic editor ABI must remain 5")
    candidate_contract = {k: v for k, v in candidate.get("editorContract", {}).items()
                          if k not in ARTIFACT_BINDINGS}
    reference_contract = {k: v for k, v in reference.get("editorContract", {}).items()
                          if k not in ARTIFACT_BINDINGS}
    if candidate_contract != reference_contract:
        problems.append("diagnostic public editor contract differs from v22")
    if candidate.get("capabilities") != reference.get("capabilities"):
        problems.append("diagnostic public capabilities differ from v22")
    return problems


def binding_problems(candidate: dict, output: Path) -> list[str]:
    problems = []
    for key, filename in ARTIFACT_BINDINGS.items():
        actual = hashlib.sha256((output / filename).read_bytes()).hexdigest()
        if candidate.get("editorContract", {}).get(key) != actual:
            problems.append(f"{key} does not bind the packaged {filename}")
    return problems


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--check-worker-base" in argv[1:]:
        check = argparse.ArgumentParser(allow_abbrev=False)
        check.add_argument("--check-worker-base", action="store_true")
        check.add_argument("--base-worker", type=Path, required=True)
        check.add_argument("--base-worker-sha256", required=True)
        args = check.parse_args(argv[1:])
        checked_base_worker(args.base_worker, args.base_worker_sha256)
        print("frozen v22 diagnostic worker base verified")
        return 0
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
    expected_worker = checked_base_worker() + (
        root / "sdk/v23-diagnostic-worker-tail.js").read_bytes()
    if known.worker.read_bytes() != expected_worker:
        problems.append("worker is not the base worker plus diagnostic tail")
    if problems:
        raise SystemExit("; ".join(problems))
    printed = io.StringIO()
    manifest_path = known.output / "sdk-manifest.json"
    validated = False
    try:
        # Fail before packing if the inherited contract cannot be read. Keep
        # this read inside the cleanup boundary so a stale target cannot mask
        # the failed attempt on the next make invocation.
        reference = json.loads((root / "dist/profiles/e2-editor-v22/sdk-manifest.json").read_text())
        with contextlib.redirect_stdout(printed):
            code = v5.main(argv)
        if code:
            return code
        manifest = json.loads(manifest_path.read_text())
        problems = contract_problems(manifest, reference) + binding_problems(manifest, known.output)
        if problems:
            raise SystemExit("; ".join(problems))
        summary = json.loads(printed.getvalue())
        summary["diagnosticOnly"] = True
        summary["manifestSha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        print(json.dumps(summary, indent=2))
        validated = True
        return 0
    finally:
        if not validated:
            # Includes nonzero returns, SystemExit, parse/IO failures and
            # interruption after the underlying packer wrote the make target.
            # Keep partial non-manifest files for diagnosis; make must retry.
            try:
                manifest_path.unlink(missing_ok=True)
            finally:
                sys.stderr.write(printed.getvalue())



if __name__ == "__main__":
    raise SystemExit(main())
