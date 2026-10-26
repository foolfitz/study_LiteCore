import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { NarrowEditorV2Session, selectionShapeOf } from '../narrow-editor-v2-session.js';
const source = readFileSync(new URL('../../web/e2-editor-app.js', import.meta.url), 'utf8');
const extract = (name, optional = false) => {
  const found = source.match(new RegExp(`^(?:async )?function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?^\\}`, 'm'));
  if (!optional) assert.ok(found, name);
  return found?.[0] ?? '';
};
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return {promise,resolve}; };
async function fixture({ abi = 6 } = {}) {
  const manifest = JSON.parse(readFileSync(new URL('../../dist/profiles/e2-editor-v22/sdk-manifest.json', import.meta.url)));
  manifest.editorContract.abiVersion = abi;
  manifest.editorContract.actions['move-character-right'].gestures = ['collapsed','range-single','range-cross'];
  let revision = 0;
  const entered = deferred(), release = deferred(), calls = [], events = [], listeners = [];
  const state = () => ({ documentHandle: 1, revision, format: {}, caret: null,
    selection: { observed: true, collapsed: true, rectangles: [] } });
  const document = { handle: 1, revision: 0, widthTwips: 1000, heightTwips: 2000,
    _assertUsable() {}, async save() { return new ArrayBuffer(16); }, async close() {},
    async render() { return { pixels: new ArrayBuffer(4), revision }; },
    async insertText(text) { calls.push(`type:${text}`); document.revision = ++revision; return {revision,state:state()}; } };
  const engine = { manifest, onEvent() { return () => {}; }, async open() { return document; }, dispose() {},
    async _request(operation, payload) {
      if (operation === 'editorGetStateV2') return state();
      calls.push(payload.action);
      if (calls.length === 1) { entered.resolve(); await release.promise; }
      return { action: payload.action, beforeRevision: payload.expectedRevision, revision, changed: false,
        completion: 'verified-move-readback', state: state() };
    } };
  document._engine = engine;
  const session = new NarrowEditorV2Session({ engineFactory: async () => engine, secureContext: true,
    clipboard: {async writeText() {}, async readText() {return '';} } });
  await session.open({ bytes: new ArrayBuffer(8), name: 'd.odt' });
  const sink = { value: '', disabled: false,
    addEventListener(type, fn, capture = false) { listeners.push({type,fn,capture: capture === true}); },
    removeEventListener(type, fn) { const i = listeners.findIndex(l => l.type === type && l.fn === fn); if (i >= 0) listeners.splice(i,1); },
    dispatch(type, extra = {}) {
      const event = {type, preventDefault() {this.defaultPrevented = true;}, ...extra};
      events.push({type, inputType: extra.inputType, data: extra.data});
      // Target capture listeners precede target bubble listeners even when installed later.
      return [...listeners.filter(l => l.type === type && l.capture), ...listeners.filter(l => l.type === type && !l.capture)]
        .map(l => l.fn(event));
    } };
  session.input.attach(sink);
  const hooks = ['releaseHeldSelectionMoveBeforeInput','releaseHeldSelectionMoveBeforeComposition',
    'releaseHeldSelectionMoveBeforePaste'];
  const registrations = hooks.map(name => source.match(new RegExp(`^el\\.sink\\.addEventListener\\([^\\n]*${name}[^\\n]*$`, 'm'))?.[0] ?? '').join('\n');
  const api = new Function('session','selectionShapeOf','el', `
    const KEY_ACTIONS={ArrowRight:'move-character-right'}, SESSION_ACCEPTS=new Set(['ready','busy']), HELD_DELETE_DEPTH=2;
    const FORMAT_ACTIONS=new Set(), ACTION_LABELS={}; let engineActionsOut=0, busyLeftToAction=false;
    const run=async(label,operation)=>operation(), renderDocument=()=>{}, formatStateFor=()=>false;
    let lastSelectionShape='collapsed'; const selectionMoveHolds=new Map(), selectionMovesOutstanding=new Set();
    let heldSelectionMove=null,selectionMoveSending=false,selectionMoveSequence=0;
    function releaseHeldDeletesBeforeEnqueue() {}
    ${['editorAction','takeSelectionMove','sendSelectionMove','releaseHeldSelectionMove',
      'releaseHeldInputsBeforeEnqueue','endSelectionMoveHold'].map(n=>extract(n)).join('\n')}
    ${hooks.map(n=>extract(n,true)).join('\n')}
    ${registrations}
    el.sink.addEventListener('keydown', takeSelectionMove);
    return {before:releaseHeldInputsBeforeEnqueue, held:()=>heldSelectionMove};
  `)(session, selectionShapeOf, {sink, toolbar:{querySelector:()=>null}});
  session._beforeEnqueue = api.before;
  const start = async () => {
    sink.dispatch('keydown',{key:'ArrowRight',shiftKey:true,repeat:false}); await entered.promise;
    sink.dispatch('keydown',{key:'ArrowRight',shiftKey:true,repeat:true});
    assert.ok(api.held());
  };
  const finish = async (promises) => {
    release.resolve(); await Promise.all(promises); await session.input.idle();
    // Drain the already admitted operation promises, without a timing threshold.
    await new Promise(r=>setImmediate(r));
  };
  return {session,sink,api,calls,events,start,finish,release};
}

for (const inputType of ['insertText','insertReplacementText','insertFromPaste']) {
  test(`actual ${inputType} event preserves the earlier held move before adapter admission`, async () => {
    const f = await fixture(); await f.start();
    const pending = f.sink.dispatch('beforeinput',{inputType,data:'x',isComposing:false});
    await f.finish(pending);
    assert.deepEqual(f.calls,['move-character-right','move-character-right','type:x']);
    assert.equal(f.events.filter(e=>e.type==='beforeinput').length,1);
  });
}

test('composition updates do not flush; the actual composition commit flushes once before adapter admission', async () => {
  const f = await fixture(); await f.start();
  f.sink.dispatch('compositionstart'); f.sink.dispatch('compositionupdate',{data:'字'});
  await Promise.all(f.sink.dispatch('beforeinput',{inputType:'insertCompositionText',data:'字',isComposing:true}));
  assert.ok(f.api.held()); assert.equal(f.calls.length,1);
  f.sink.value='字';
  const pending=f.sink.dispatch('compositionend',{data:'字'});
  await f.finish(pending);
  assert.deepEqual(f.calls,['move-character-right','move-character-right','type:字']);
  assert.equal(f.events.filter(e=>e.type==='compositionend').length,1);
});

test('the actual paste event preserves the earlier held move before its independent adapter commit', async () => {
  const f = await fixture(); await f.start();
  const pending=f.sink.dispatch('paste',{clipboardData:{getData:type=>type==='text/plain'?'x':''}});
  await f.finish(pending);
  assert.deepEqual(f.calls,['move-character-right','move-character-right','type:x']);
  assert.equal(f.events.filter(e=>e.type==='paste').length,1);
  assert.equal(f.events.filter(e=>e.type==='beforeinput').length,0);
});
