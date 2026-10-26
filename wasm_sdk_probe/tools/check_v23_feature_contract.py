#!/usr/bin/env python3
"""Exact ABI6 successor delta; no new IDs, capabilities or diagnostic surface."""
import argparse
import copy
import hashlib
import json
import shlex
import re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_v23_diagnostic_build import read_feature_build_log, read_wasm
ROOT=Path(__file__).resolve().parent.parent
PROFILE='e2-editor-v23'
ARCHIVE=ROOT/'build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa'
BASE_SHA256='0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350'
WORKER=ROOT/'sdk/v23-feature-worker.js'
from inspect_wasm_function import leb, name as wasm_name
from validate_r5_artifacts import loader_exports
MOVES=('move-character-left','move-character-right','move-line-up','move-line-down','move-line-home','move-line-end')
BINDINGS={'loaderSha256':'probe.js','wasmSha256':'probe.wasm','workerSha256':'sdk-worker.js'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check_base(path=ARCHIVE/'sdk-worker.js',pin=BASE_SHA256):
    if Path(path).resolve()!=(ARCHIVE/'sdk-worker.js').resolve() or pin!=BASE_SHA256 or sha(Path(path))!=BASE_SHA256:
        raise ValueError('feature base must be the exact frozen v22 worker')
def expected_contract(reference):
    result=copy.deepcopy(reference['editorContract'])
    result['abiVersion']=6
    for name in MOVES:
        result['actions'][name]['gestures']=['collapsed','range-single','range-cross']
        if name.startswith('move-line-'):
            result['actions'][name]['limits']=[x for x in result['actions'][name]['limits'] if x!='no-extend-selection']
    return result

def contract_problems(candidate,reference):
    problems=[]
    if candidate.get('profile')!=PROFILE:problems.append('wrong feature identity')
    if reference.get('profile')!='e2-editor-v22':problems.append('wrong reference identity')
    expected=expected_contract(reference)
    got={k:v for k,v in candidate.get('editorContract',{}).items() if k not in BINDINGS}
    wanted={k:v for k,v in expected.items() if k not in BINDINGS}
    if got!=wanted:problems.append('feature contract differs from the exact ABI6 six-move delta')
    # The inherited v4 builder replaces the profile suffix; all other public
    # top-level data (including unknown new leaves) remains exactly inherited.
    top=copy.deepcopy(reference)
    top.pop('editorContract')
    top['profile']=PROFILE
    suffix='+'+reference['profile']
    if not reference['sdkVersion'].endswith(suffix):
        problems.append('reference sdkVersion has no exact profile suffix')
    else:
        top['sdkVersion']=reference['sdkVersion'][:-len(suffix)]+'+'+PROFILE
    if {k:v for k,v in candidate.items() if k!='editorContract'}!=top:
        problems.append('top-level manifest differs from exact successor identity delta')
    return problems

def input_problems(worker,exports,wasm):
    """Input bytes and exact sidecar only; actual_export_problems checks binary bindings."""
    check_base()
    problems=read_wasm(wasm.read_bytes())
    if worker.read_bytes()!=WORKER.read_bytes():problems.append('worker differs from isolated feature source')
    names=exports.read_text().splitlines()
    if names!=(ARCHIVE/'exports.txt').read_text().splitlines():problems.append('exports differ from frozen v22 public exports')
    if any(token in worker.read_bytes() for token in (b'oxsdk_v23_diagnostic',b'v23Diagnostic',b'v23-html-result')):
        problems.append('diagnostic worker entrance present')
    return problems

def binary_export_kinds(data):
    """Read section 7, retaining names (not indices, which can have aliases)."""
    if not data.startswith(b'\0asm\1\0\0\0'):
        raise ValueError('not a version-1 WebAssembly binary')
    i=8;exports=None
    while i<len(data):
        section=data[i];size,start=leb(data,i+1);end=start+size
        if end>len(data):raise ValueError('truncated WebAssembly section')
        if section==7:
            if exports is not None:raise ValueError('duplicate export section')
            exports={};payload=data[start:end];count,j=leb(payload,0)
            for _ in range(count):
                symbol,j=wasm_name(payload,j)
                kind=payload[j];_,j=leb(payload,j+1)
                if symbol in exports:raise ValueError('duplicate binary export name')
                exports[symbol]=kind
            if j!=len(payload):raise ValueError('malformed export section length')
        i=end
    if not exports:raise ValueError('missing or empty binary export section')
    return exports

def public_binary_exports(loader,wasm):
    """Resolve Emscripten's minified binary names through its actual loader.

    The frozen v22 binary exports db rather than oxsdk_editor_action; a raw
    name comparison would silently see zero SDK functions. The loader is the
    public name binding, while section 7 independently proves the target exists.
    """
    source=loader.read_text()
    public=loader_exports(loader)
    if not public:raise ValueError('empty loader SDK export inventory')
    pairs=re.findall(r'Module\["(_(?:oxsdk|probe)_[^"]+)"\]\s*=\s*[A-Za-z_$][\w$]*\s*=\s*wasmExports\["([^"]+)"\]',source)
    bindings=dict(pairs)
    if len(bindings)!=len(pairs) or set(bindings)!=public:
        raise ValueError('public loader export lacks a unique binary binding')
    kinds=binary_export_kinds(wasm.read_bytes())
    for public_name,binary_name in bindings.items():
        if kinds.get(binary_name)!=0:
            raise ValueError(f'{public_name} does not bind an actual binary function: {binary_name}')
    # Unminified SDK exports are also public and must not hide outside wrappers.
    direct={'_'+n.lstrip('_') for n in kinds if n.lstrip('_').startswith(('oxsdk_','probe_'))}
    return public|direct

def actual_export_problems(loader,wasm):
    expected={n for n in (ARCHIVE/'exports.txt').read_text().splitlines()
              if n.startswith(('_oxsdk_','_probe_'))}
    try:
        reference=public_binary_exports(ARCHIVE/'probe.js',ARCHIVE/'probe.wasm')
        actual=public_binary_exports(loader,wasm)
    except (ValueError,IndexError,UnicodeError) as error:
        return ['actual binary public export validation failed: '+str(error)]
    if reference!=expected:return ['archived public loader/binary surface disagrees with its sidecar']
    if actual!=expected:
        return ['actual public SDK exports differ: missing='+repr(sorted(expected-actual))+
                ' extra='+repr(sorted(actual-expected))]
    return []

def binding_problems(candidate,output):
    return [f'{key} does not bind {filename}' for key,filename in BINDINGS.items()
            if candidate.get('editorContract',{}).get(key)!=sha(output/filename)]

def feature_log_problems(text):
    problems=read_feature_build_log(text)
    compiles=[]
    for line in text.replace('\\\n',' ').splitlines():
        if ' -c ' in line and '-o build/e2/editor-v23/' in line:
            args=shlex.split(line);compiles.append(args)
            if '-DOXSDK_E2_V23_FEATURE_ABI6' not in args:
                problems.append('feature object lacks ABI6 selector')
            if any('OXSDK_FINDING_016_SCHEDULER_PROBE' in arg for arg in args):
                problems.append('obsolete scheduler instrumentation present')
    # Four source units are the specified fresh-link boundary, not an open-ended source claim.
    expected={'src/probe_engine.cpp','src/sdk_api.cpp','src/editor_api.cpp','src/unoembind_stub.cpp'}
    if len(compiles)!=4 or {args[args.index('-c')+1] for args in compiles}!=expected:
        problems.append('feature record must compile each of the four source units exactly once')
    return problems

def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check-worker-base',action='store_true');g.add_argument('--manifest',type=Path);g.add_argument('--build-log',type=Path)
    p.add_argument('--base-worker',type=Path,default=ARCHIVE/'sdk-worker.js');p.add_argument('--base-worker-sha256',default=BASE_SHA256);p.add_argument('--exports',type=Path)
    a=p.parse_args()
    if a.check_worker_base:check_base(a.base_worker,a.base_worker_sha256);problems=[]
    elif a.build_log:problems=feature_log_problems(a.build_log.read_text())
    else:
        if not a.exports:p.error('--manifest requires --exports')
        candidate=json.loads(a.manifest.read_text());reference=json.loads((ARCHIVE/'sdk-manifest.json').read_text())
        problems=contract_problems(candidate,reference)+binding_problems(candidate,a.manifest.parent)+input_problems(a.manifest.parent/'sdk-worker.js',a.exports,a.manifest.parent/'probe.wasm')+actual_export_problems(a.manifest.parent/'probe.js',a.manifest.parent/'probe.wasm')
    for problem in problems:print(problem)
    print('feature preconditions hold' if not problems else 'feature preconditions failed')
    return bool(problems)
if __name__=='__main__':raise SystemExit(main())
