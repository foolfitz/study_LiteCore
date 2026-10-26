Adversarial source review. Reply in English, no tools. Find concrete bugs only, with exact input/mutation and consequence. Units: new exact ABI6 packaging/artifact checker and narrowly scoped queued deletion. Authoritative contract: frozenv22 inherited fullmanifest except profile/sdkVersion suffix, editorABI6 and six existing move grants; realbinary functions are minified, so loader+actualexportsection jointly expose names. Publicselection/type contracts unchanged; selectall withheld; no private diagnosticoperation. Session deleteKey preserves two original key directions and reads current publicV2 state only when its existingqueue turn starts, choosing action20 only for observedrange+grant. Read failures retain existing codes/recovery; oldprofiles keep oldaction route. No new waits/resolvercallback/queue. No runtime/acceptance result is claimed; references/pre-red future. Review provided code/diff as source, not proof of WASM readiness. State NO_CONCRETE_FINDING if appropriate.

===== wasm_sdk_probe/tools/check_v23_feature_contract.py =====
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

===== wasm_sdk_probe/tools/build_e2_v23_feature_profile.py =====
#!/usr/bin/env python3
"""ABI6 feature wrapper; inherited builders and their defaults stay unchanged."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import os
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_e2_editor_v5_profile as v5
import check_v23_feature_contract as contract
BASE_ACTION_MAP=v5.action_map

def action_map():
    actions=BASE_ACTION_MAP()
    for name in contract.MOVES:
        actions[name]['gestures']=['collapsed','range-single','range-cross']
        if name.startswith('move-line-'):
            actions[name]['limits']=[x for x in actions[name]['limits'] if x!='no-extend-selection']
    return actions

def main(argv=None):
    argv=list(sys.argv if argv is None else argv)
    parser=argparse.ArgumentParser(add_help=False,allow_abbrev=False)
    parser.add_argument('--profile',required=True)
    for field in ('loader','worker','wasm','exports','output'):parser.add_argument('--'+field,type=Path,required=True)
    args,_=parser.parse_known_args(argv[1:])
    if args.profile!=contract.PROFILE:raise SystemExit('feature builder requires exactly '+contract.PROFILE)
    if args.output.exists() and any(args.output.iterdir()):raise SystemExit('existing feature profile/partial files must be preserved')
    problems=contract.input_problems(args.worker,args.exports,args.wasm)+contract.actual_export_problems(args.loader,args.wasm)
    if problems:raise SystemExit('; '.join(problems))
    manifest=args.output/'sdk-manifest.json';printed=io.StringIO();validated=False
    original=(v5.ABI_VERSION,v5.action_map)
    try:
        reference=json.loads((contract.ARCHIVE/'sdk-manifest.json').read_text())
        v5.ABI_VERSION=6;v5.action_map=action_map
        with contextlib.redirect_stdout(printed):code=v5.main(argv)
        if code:return code
        candidate=json.loads(manifest.read_text())
        problems=contract.contract_problems(candidate,reference)+contract.binding_problems(candidate,args.output)
        if problems:raise SystemExit('; '.join(problems))
        summary=json.loads(printed.getvalue());summary.update(profile=contract.PROFILE,abiVersion=6,manifestSha256=contract.sha(manifest))
        print(json.dumps(summary,indent=2));validated=True;return 0
    finally:
        v5.ABI_VERSION,v5.action_map=original
        if not validated:
            try:
                if manifest.exists():
                    fd,failed=tempfile.mkstemp(prefix='sdk-manifest.failed-',suffix='.json',dir=args.output)
                    os.close(fd);os.replace(manifest,failed)
            finally:sys.stderr.write(printed.getvalue())
if __name__=='__main__':raise SystemExit(main())

===== session change =====
diff --git a/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js b/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js
index 00cb228e..a54f8b41 100644
--- a/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js
+++ b/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js
@@ -1027,6 +1027,21 @@ export class NarrowEditorV2Session extends EditorSession {
    * expects would be the other's.
    */
   action(action, options = {}) {
+    return this._action(action, options, false);
+  }
+
+  /** ABI6 product keys keep their direction until their existing queue turn. */
+  deleteKey(action, options = {}) {
+    if (!["delete-backward", "delete-forward"].includes(action)
+        || this.engine?.manifest?.editorContract?.abiVersion !== 6) {
+      const error = new Error("deleteKey requires an ABI6 backward or forward delete");
+      error.code = "INVALID_ARGUMENT";
+      return Promise.reject(this._withDisposition(error));
+    }
+    return this._action(action, options, true);
+  }
+
+  _action(action, options, fromKey) {
     if (!ACTIONS.has(action)) {
       const error = new Error(`unsupported v2 editor action: ${String(action)}`);
       error.code = "EDITOR_ACTION_UNSUPPORTED";
@@ -1035,13 +1050,34 @@ export class NarrowEditorV2Session extends EditorSession {
     return this._enqueue(
       `action:${action}`,
       async ({ document, editor }, tools) => {
+        let dispatchedAction = action;
+        if (fromKey) {
+          const generation = this._generation;
+          // One ordered read at dequeue, not a cached page shape or a waiter.
+          const state = await editor.getState(options);
+          if (generation !== this._generation || document !== this.document) {
+            const error = new Error("delete key belongs to a stale Worker generation");
+            error.code = "STALE_EDITOR_GENERATION";
+            throw error;
+          }
+          const shape = selectionShapeOf({ state });
+          if (state?.documentHandle !== document.handle
+              || state?.selection?.observed !== true || shape === null
+              || (shape !== "collapsed" && !editor.gesturesFor("delete-selection")?.includes(shape))) {
+            const error = new Error("the current selection does not permit this delete key");
+            error.code = "EDITOR_FORMAT_GESTURE_UNSUPPORTED";
+            error.details = { dispatched: false, keyAction: action };
+            throw error;
+          }
+          if (shape !== "collapsed") dispatchedAction = "delete-selection";
+        }
         if (CHECKPOINTED_MOVES.has(action))
           await this._checkpointBeforeBoundaryMove(document);
         try {
-          const result = await editor.action(action, options);
+          const result = await editor.action(dispatchedAction, options);
           if (result?.completion === "verified-boundary-noop" && result?.changed === false)
             tools.completedUnchanged();
-          return result;
+          return fromKey ? { ...result, keyAction: action } : result;
         } catch (error) {
           // FINDING 119.  A delete the selection barrier could not verify in
           // time comes back as EDITOR_STATE_UNAVAILABLE with no barrier detail;
@@ -1055,7 +1091,7 @@ export class NarrowEditorV2Session extends EditorSession {
           // posted, so nothing here or on the page may say "unchanged" -- every
           // typed change survives, only the key's own effect is uncertain.
           // Scoped by action and code, never by message text (spec §14.1).
-          if (stateUnavailableOnDelete(action, error)) {
+          if (stateUnavailableOnDelete(dispatchedAction, error)) {
             await this._checkpointBeforeBoundaryRestart(document);
             this._blockQueue(error, "restart-required", "editor-boundary");
             error.recovery = "restart";
@@ -1323,6 +1359,10 @@ export class NarrowEditorV2Session extends EditorSession {
     return this.editor?.gesturesFor(action) ?? null;
   }
 
+  offersSelectionMove(action, gesture) {
+    return this.editor?.offersSelectionMove(action, gesture) ?? false;
+  }
+
   offers(action) {
     return this.editor?.offers(action) ?? false;
   }

===== inherited selection accessor =====
/**
 * The shape of the selection a `selectRange` result describes, or null when the
 * result does not describe one.
 *
 * FINDING 079, AND THIS IS THE SEAM THAT WAS MISSING.  The product page derived
 * the shape inline from `result.collapsed` and `result.rectangles` -- the shape
 * `editor-shell/editor-client.js` assembles on the V1 path.  The v2 client
 * assembles nothing: `ParagraphEditorClient.selectRange` hands back the
 * worker's envelope, whose keys are `method, revision, completion,
 * callbackSequenceBefore, callbackSequenceAfter, state`, and the selection sits
 * at `state.selection`.  Both reads were `undefined`, `undefined === false` is
 * false, `undefined?.length ?? 0` is 0, and the page computed `collapsed` for
 * every drag ever made.  Nothing was stale; nothing was ever read.
 *
 * It lives here, exported and unit-tested, rather than inline in the page,
 * because the defect's CLASS is "a derivation with no test read a shape some
 * other layer assembles".  A DOM flag on the page is a tripwire for the next
 * drift; it is not a guard against a second reader looking in a second wrong
 * place.  One accessor with its own tests is.
 *
 * Returns null rather than "collapsed" when it cannot tell.  Those are
 * different claims and conflating them is the whole finding: the caller decides
 * what to do about not knowing, and cannot do that if not-knowing has been
 * spelled as an answer.
 */
export function selectionShapeOf(result) {
  const selection = result?.state?.selection;
  if (typeof selection?.collapsed !== "boolean") return null;
  if (selection.collapsed) return "collapsed";
  // `rectangles.length > 1` as the cross-paragraph test is INHERITED, not
  // established here: a single paragraph that wraps onto two lines also yields
  // more than one rectangle.  Measured 2026-08-23 on e2-editor-v7 -- a drag
  // inside one line gave 1 rectangle and one across two paragraphs gave 3 --
  // which shows the two cases this profile meets are separated, not that the
  // rule is right in general.  Both range shapes are offered together for every
  // action that takes a range, so nothing currently turns on the distinction.
  return (selection.rectangles?.length ?? 0) > 1 ? "range-cross" : "range-single";
}

/**

===== profile controls =====
"""Full-contract deltas and transactional wrapper faults; no product build."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK/'tools'))
import build_e2_v23_feature_profile as builder
import check_v23_feature_contract as checker

def uleb(value):
    out=bytearray()
    while True:
        byte=value&127;value>>=7
        out.append(byte|(128 if value else 0))
        if not value:return bytes(out)

def wasm_string(value):
    raw=value.encode();return uleb(len(raw))+raw

def synthetic_public_pair(names=None):
    if names is None:
        names=[n for n in (checker.ARCHIVE/'exports.txt').read_text().splitlines() if n.startswith(('_oxsdk_','_probe_'))]
    rows=[(n,'f'+str(i)) for i,n in enumerate(names)]
    loader=';'.join(f'Module["{n}"]={n}=wasmExports["{symbol}"]' for n,symbol in rows)
    exports=uleb(len(rows))+b''.join(wasm_string(symbol)+b'\0\0' for _,symbol in rows)
    def section(kind,data):return bytes([kind])+uleb(len(data))+data
    wasm=(b'\0asm\1\0\0\0'+section(0,wasm_string('core-built-without-accessibility'))+
          section(1,b'\1\x60\0\0')+section(3,b'\1\0')+section(7,exports)+section(10,b'\1\2\0\x0b'))
    return loader.encode(),wasm

class Profile(unittest.TestCase):
    def setUp(self):
        self.reference=json.loads((checker.ARCHIVE/'sdk-manifest.json').read_text())
        self.candidate=copy.deepcopy(self.reference)
        self.candidate['profile']=checker.PROFILE
        self.candidate['sdkVersion']=self.reference['sdkVersion'].removesuffix('+e2-editor-v22')+'+'+checker.PROFILE
        self.candidate['editorContract']=checker.expected_contract(self.reference)

    def test_every_action_field_is_bound(self):
        self.assertEqual(checker.contract_problems(self.candidate,self.reference),[])
        actions=self.candidate['editorContract']['actions']
        self.assertEqual(len(actions),23)
        for name,action in actions.items():
            for field in action:
                with self.subTest(action=name,field=field):
                    bad=copy.deepcopy(self.candidate)
                    del bad['editorContract']['actions'][name][field]
                    self.assertTrue(checker.contract_problems(bad,self.reference))
        for change in ('new-action','capability','abi','profile','withheld'):
            bad=copy.deepcopy(self.candidate)
            if change=='new-action':bad['editorContract']['actions']['invented']={'id':24,'gestures':[]}
            elif change=='capability':bad['capabilities'].append('invented')
            elif change=='abi':bad['editorContract']['abiVersion']=5
            elif change=='profile':bad['profile']='e2-editor-v23-diag-r2'
            else:bad['editorContract']['actions']['select-all']['gestures']=['collapsed']
            self.assertTrue(checker.contract_problems(bad,self.reference))

    def test_every_top_level_public_field_is_bound(self):
        for key in self.candidate:
            if key=='editorContract':continue
            for mutation in ('delete','replace'):
                with self.subTest(key=key,mutation=mutation):
                    bad=copy.deepcopy(self.candidate)
                    if mutation=='delete':del bad[key]
                    else:bad[key]={'unexpected':'value'}
                    self.assertTrue(checker.contract_problems(bad,self.reference))
        for key in ('diagnosticOnly','inventedPublicGrant'):
            bad=copy.deepcopy(self.candidate);bad[key]=True
            self.assertTrue(checker.contract_problems(bad,self.reference))
        bad=copy.deepcopy(self.candidate);bad['expectedCapabilityBits']^=1
        self.assertTrue(checker.contract_problems(bad,self.reference))

    def test_actual_binary_bindings_and_frozen_controls(self):
        self.assertEqual(checker.actual_export_problems(checker.ARCHIVE/'probe.js',checker.ARCHIVE/'probe.wasm'),[])
        # An actual retained diagnostic binary has a public entrance absent from v22.
        r2=SDK/'dist/profiles/e2-editor-v23-diag-r2'
        self.assertTrue(checker.actual_export_problems(r2/'probe.js',r2/'probe.wasm'))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);loader,wasm=synthetic_public_pair()
            (p/'probe.js').write_bytes(loader);(p/'probe.wasm').write_bytes(wasm)
            self.assertEqual(checker.actual_export_problems(p/'probe.js',p/'probe.wasm'),[])
            names=[n for n in (checker.ARCHIVE/'exports.txt').read_text().splitlines() if n.startswith('_oxsdk_')]
            for variant in (names[:-1],names+['_oxsdk_v23_diagnostic'],names+['_oxsdk_invented']):
                l,w=synthetic_public_pair(variant);(p/'probe.js').write_bytes(l);(p/'probe.wasm').write_bytes(w)
                self.assertTrue(checker.actual_export_problems(p/'probe.js',p/'probe.wasm'))
            (p/'probe.js').write_bytes(loader)
            for bad in (b'\0asm\1\0\0\0',wasm[:-1],wasm.replace(b'f0',b'z0',1)):
                (p/'probe.wasm').write_bytes(bad)
                self.assertTrue(checker.actual_export_problems(p/'probe.js',p/'probe.wasm'))

    def test_exact_archived_base_and_inputs(self):
        checker.check_base()
        with self.assertRaises(ValueError):checker.check_base(SDK/'sdk/sdk-worker.js')
        with self.assertRaises(ValueError):checker.check_base(pin='0'*64)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);w=p/'worker';e=p/'exports';a=p/'wasm'
            w.write_bytes(checker.WORKER.read_bytes());e.write_bytes((checker.ARCHIVE/'exports.txt').read_bytes())
            a.write_bytes(b'\0asm\1\0\0\0core-built-without-accessibility')
            self.assertEqual(checker.input_problems(w,e,a),[])
            w.write_bytes((SDK/'sdk/sdk-worker.js').read_bytes())
            self.assertTrue(checker.input_problems(w,e,a))
            w.write_bytes(checker.WORKER.read_bytes());e.write_text(e.read_text()+'_oxsdk_v23_diagnostic\n')
            self.assertTrue(checker.input_problems(w,e,a))
            e.write_bytes((checker.ARCHIVE/'exports.txt').read_bytes());a.write_bytes(b'not wasm')
            self.assertTrue(checker.input_problems(w,e,a))

    def test_actual_inherited_builder_chain_on_standin_bytes(self):
        # No compiler/linker or frozen output: real v5/v4/c/b packing in a temporary directory.
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);output=p/'profile'
            loader,wasm=synthetic_public_pair()
            (p/'probe.js').write_bytes(loader)
            (p/'probe.wasm').write_bytes(wasm)
            (p/'sdk-worker.js').write_bytes(checker.WORKER.read_bytes())
            (p/'exports.txt').write_bytes((checker.ARCHIVE/'exports.txt').read_bytes())
            args=['builder','--source-manifest',str(SDK/'sdk/v18-writer-review-manifest.json'),
                  '--profile',checker.PROFILE,'--loader',str(p/'probe.js'),'--wasm',str(p/'probe.wasm'),
                  '--worker',str(p/'sdk-worker.js'),'--exports',str(p/'exports.txt'),'--output',str(output),
                  '--inline-range-gestures','all','--page-rectangles','--paste-markdown']
            originals=(builder.v5.ABI_VERSION,builder.v5.action_map,builder.v5.v4.ABI_VERSION,builder.v5.v4.action_map)
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                self.assertEqual(builder.main(args),0)
            manifest=json.loads((output/'sdk-manifest.json').read_text())
            self.assertEqual(checker.contract_problems(manifest,self.reference),[])
            self.assertEqual(checker.binding_problems(manifest,output),[])
            self.assertEqual(json.loads(printed.getvalue())['withheld'],['select-all'])
            self.assertEqual(originals,(builder.v5.ABI_VERSION,builder.v5.action_map,builder.v5.v4.ABI_VERSION,builder.v5.v4.action_map))

    def test_transactional_wrapper_faults(self):
        original=(builder.v5.ABI_VERSION,builder.v5.action_map)
        for fault in ('none','exception','nonzero','manifest-parse','contract','binding','summary'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as tmp:
                output=Path(tmp)/'profile'
                def underlying(argv):
                    self.assertEqual(builder.v5.ABI_VERSION,6)
                    self.assertEqual(builder.v5.action_map()['move-line-end']['gestures'],['collapsed','range-single','range-cross'])
                    output.mkdir();candidate=copy.deepcopy(self.candidate)
                    for key,name in checker.BINDINGS.items():
                        (output/name).write_bytes(name.encode());candidate['editorContract'][key]=checker.sha(output/name)
                    if fault=='contract':candidate['editorContract']['abiVersion']=5
                    if fault=='binding':candidate['editorContract']['workerSha256']='0'*64
                    (output/'sdk-manifest.json').write_text('invalid' if fault=='manifest-parse' else json.dumps(candidate))
                    print('CAPTURED FAILURE' if fault in ('summary','exception','nonzero') else '{}')
                    if fault=='exception':raise RuntimeError('postwrite failure')
                    return 7 if fault=='nonzero' else 0
                args=['builder','--profile',checker.PROFILE,'--loader','unused','--worker','unused','--wasm','unused','--exports','unused','--output',str(output)]
                err=io.StringIO()
                with patch.object(checker,'input_problems',return_value=[]),patch.object(checker,'actual_export_problems',return_value=[]),patch.object(builder.v5,'main',side_effect=underlying),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(err):
                    if fault in ('exception','manifest-parse','contract','binding','summary'):
                        with self.assertRaises((RuntimeError,ValueError,SystemExit)):builder.main(args)
                    else:self.assertEqual(builder.main(args),7 if fault=='nonzero' else 0)
                self.assertEqual((builder.v5.ABI_VERSION,builder.v5.action_map),original)
                self.assertEqual((output/'sdk-manifest.json').exists(),fault=='none')
                failed=list(output.glob('sdk-manifest.failed-*.json'))
                self.assertEqual(len(failed),int(fault!='none'))
                if fault in ('summary','exception','nonzero'):self.assertIn('CAPTURED FAILURE',err.getvalue())
                # Every partial/successful output is preserved on a repeated invocation.
                before={p.name:p.read_bytes() for p in output.iterdir()}
                with self.assertRaises(SystemExit):builder.main(args)
                self.assertEqual(before,{p.name:p.read_bytes() for p in output.iterdir()})

if __name__=='__main__':unittest.main()
