import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { NarrowEditorV2Session } from '../narrow-editor-v2-session.js';

const base = JSON.parse(readFileSync(new URL('../../dist/profiles/e2-editor-v22/sdk-manifest.json', import.meta.url)));
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
async function fixture() {
  const calls = [], manifest = structuredClone(base);
  manifest.editorContract.abiVersion = 6;
  let current = { documentHandle: 1, revision: 0, caret: null, format: {},
    selection: { observed: true, collapsed: true, rectangles: [] } };
  let beforeRead = async () => {}, beforeAction = async () => {}, noop = false;
  const document = { handle: 1, revision: 0, widthTwips: 1000, heightTwips: 2000,
    _assertUsable() {}, async render() { return { pixels: new ArrayBuffer(4), revision: this.revision }; },
    async save() { calls.push({ operation: 'save' }); return new ArrayBuffer(16); },
    async close() {}, async getSelection() { return { text: '', selectionType: 'none' }; } };
  const engine = { manifest, onEvent() { return () => {}; }, async open() { return document; }, dispose() {},
    async _request(operation, payload) {
      calls.push({ operation, ...payload });
      if (operation === 'editorGetStateV2') { await beforeRead(); return structuredClone(current); }
      assert.equal(operation, 'editorActionV2');
      await beforeAction(payload.action);
      const moving = payload.action.startsWith('move-');
      current.selection = { observed: true, collapsed: !moving, rectangles: moving ? [{}] : [] };
      if (!moving && !noop) document.revision++;
      current.revision = document.revision;
      return { action: payload.action, beforeRevision: payload.expectedRevision, revision: document.revision,
        changed: !moving && !noop, completion: moving ? 'verified-move-readback' : noop ? 'verified-boundary-noop'
          : payload.action === 'delete-selection' ? 'uno-command-result' : 'verified-selection-delete',
        state: structuredClone(current) };
    } };
  document._engine = engine;
  const session = new NarrowEditorV2Session({ engineFactory: async () => engine, secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ''; } } });
  await session.open({ bytes: new ArrayBuffer(8), name: 'd.odt' });
  calls.length = 0;
  return { session, calls, document, manifest, setState: s => { current = s; },
    state: () => structuredClone(current), read: fn => { beforeRead = fn; },
    action: fn => { beforeAction = fn; }, noop: () => { noop = true; } };
}

test('an enqueued Backspace reads the range only after outstanding Shift completes', async () => {
  const f = await fixture(), entered = deferred(), release = deferred();
  f.action(async action => { if (action.startsWith('move-')) { entered.resolve(); await release.promise; } });
  const shift = f.session.action('move-character-right', { extendSelection: true });
  await entered.promise;
  assert.equal(f.session.state.snapshot.editorState.selection.collapsed, true);
  const deletion = f.session.deleteKey('delete-backward');
  assert.deepEqual(f.calls.map(x => x.operation), ['editorActionV2']);
  release.resolve();
  await shift;
  const result = await deletion;
  assert.equal(result.keyAction, 'delete-backward');
  assert.equal(result.action, 'delete-selection');
  assert.deepEqual(f.calls.map(x => x.operation), ['editorActionV2', 'editorGetStateV2', 'editorActionV2']);
  assert.equal(f.calls.at(-1).action, 'delete-selection');
  assert.equal(f.document.revision, 1);
  assert.equal(f.session.state.snapshot.dirty, true);
});

test('consecutive deletes and prefix-delete Shift delete each resolve at their own queue turn', async () => {
  const f = await fixture();
  const run = [f.session.deleteKey('delete-forward'),
    f.session.action('move-character-right', { extendSelection: true }),
    f.session.deleteKey('delete-backward'), f.session.deleteKey('delete-forward')];
  await Promise.all(run);
  assert.deepEqual(f.calls.filter(x => x.operation === 'editorActionV2').map(x => x.action),
    ['delete-forward', 'move-character-right', 'delete-selection', 'delete-forward']);
  assert.equal(f.calls.filter(x => x.operation === 'editorGetStateV2').length, 3);
  assert.equal(f.document.revision, 3);
});

test('unobserved, invalid, wrong-document or ungranted selection never dispatches a delete', async () => {
  for (const mutate of [s => { s.selection.observed = false; }, s => { delete s.selection.collapsed; },
    s => { s.selection.collapsed = 'false'; }, s => { s.documentHandle = 2; },
    s => { s.selection = null; }]) {
    const f = await fixture(), state = f.state(); mutate(state); f.setState(state);
    await assert.rejects(f.session.deleteKey('delete-backward'), { code: 'EDITOR_FORMAT_GESTURE_UNSUPPORTED' });
    assert.deepEqual(f.calls.map(x => x.operation), ['editorGetStateV2']);
    assert.equal(f.document.revision, 0);
  }
  const f = await fixture(), state = f.state(); state.selection.collapsed = false; f.setState(state);
  f.manifest.editorContract.actions['delete-selection'].gestures = [];
  await assert.rejects(f.session.deleteKey('delete-forward'), { code: 'EDITOR_FORMAT_GESTURE_UNSUPPORTED' });
  assert.equal(f.calls.filter(x => x.operation === 'editorActionV2').length, 0);
});

test('read failure and generation replacement do not dispatch; view-only does not even read', async () => {
  const f = await fixture();
  f.read(async () => { const e = new Error('read unavailable'); e.code = 'BUSY'; throw e; });
  await assert.rejects(f.session.deleteKey('delete-backward'), { code: 'BUSY' });
  assert.equal(f.calls.filter(x => x.operation === 'editorActionV2').length, 0);
  const g = await fixture();
  g.read(async () => { g.session._generation++; });
  await assert.rejects(g.session.deleteKey('delete-forward'), { code: 'STALE_EDITOR_GENERATION' });
  assert.equal(g.calls.filter(x => x.operation === 'editorActionV2').length, 0);
  const h = await fixture(); h.session.setViewOnly(true);
  await assert.rejects(h.session.deleteKey('delete-backward'), { code: 'EDITOR_VIEW_ONLY' });
  assert.deepEqual(h.calls, []);
});

test('no-op preserves unchanged accounting and the old public action route remains untouched', async () => {
  const f = await fixture(); f.noop();
  await f.session.deleteKey('delete-backward');
  assert.equal(f.document.revision, 0);
  assert.equal(f.session.state.snapshot.dirty, false);
  f.calls.length = 0;
  f.manifest.editorContract.abiVersion = 5;
  await assert.rejects(f.session.deleteKey('delete-backward'), { code: 'INVALID_ARGUMENT' });
  await f.session.action('delete-backward');
  assert.deepEqual(f.calls.map(x => x.operation), ['editorActionV2']);
  await assert.rejects(f.session.deleteKey('delete-selection'), { code: 'INVALID_ARGUMENT' });
});
