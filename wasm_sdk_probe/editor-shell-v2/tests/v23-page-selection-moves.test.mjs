import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { selectionShapeOf } from '../narrow-editor-v2-session.js';

const source = readFileSync(new URL('../../web/e2-editor-app.js', import.meta.url), 'utf8');
const fn = (name, body = source) => {
  const text = body.match(new RegExp(`^(?:async )?function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?^\\}`, 'm'))?.[0];
  assert.ok(text, name); return text;
};
const keys = { ArrowLeft: 'move-character-left', ArrowRight: 'move-character-right',
  ArrowUp: 'move-line-up', ArrowDown: 'move-line-down', Home: 'move-line-home', End: 'move-line-end' };
const tick = () => new Promise(resolve => setImmediate(resolve));
function fixture(mutate = s => s) {
  const subject = mutate(source);
  const wire = [], pending = [], order = [];
  let granted = true;
  const session = { document: { handle: 1 }, state: { snapshot: { state: 'ready',
    editorState: { selection: { observed: true, collapsed: false, rectangles: [{}] } } } },
    offersSelectionMove: () => granted };
  let api;
  const editorAction = (action, options) => {
    api.before();
    wire.push({ action, extendSelection: options.extendSelection, document: session.document });
    order.push(action);
    return new Promise((resolve, reject) => pending.push({ resolve, reject, answer: () => options.onResult?.({}) }));
  };
  const make = new Function('session', 'editorAction', 'selectionShapeOf', 'KEY_ACTIONS', `
    const SESSION_ACCEPTS = new Set(['ready','busy']); const HELD_DELETE_DEPTH = 2;
    let lastSelectionShape = 'collapsed';
    const selectionMoveHolds = new Map(); const selectionMovesOutstanding = new Set();
    let heldSelectionMove = null; let selectionMoveSending = false; let selectionMoveSequence = 0;
    function releaseHeldDeletesBeforeEnqueue() {}
    ${['takeSelectionMove','sendSelectionMove','releaseHeldSelectionMove','releaseHeldInputsBeforeEnqueue',
      'endSelectionMoveHold'].map(name => fn(name, subject)).join('\n')}
    return { take: takeSelectionMove, before: releaseHeldInputsBeforeEnqueue, up: endSelectionMoveHold,
      work: () => ({ outstanding: [...selectionMovesOutstanding], held: heldSelectionMove }) };
  `);
  api = make(session, editorAction, selectionShapeOf, keys);
  const down = (key = 'ArrowRight', extra = {}) => {
    let prevented = false;
    const taken = api.take({ key, shiftKey: true, repeat: false,
      preventDefault() { prevented = true; }, ...extra });
    return { taken, prevented };
  };
  return { api, down, session, wire, pending, order, grant: on => { granted = on; },
    enqueueOther: name => { api.before(); order.push(name); } };
}

test('the six actual product keys carry Shift directly; partial and old grants leave them alone', async () => {
  for (const key of Object.keys(keys)) for (const shiftKey of [false, true]) {
    const f = fixture();
    assert.deepEqual(f.down(key, { shiftKey }), { taken: true, prevented: true });
    assert.equal(f.wire[0].action, keys[key]);
    assert.equal(f.wire[0].extendSelection, shiftKey);
    f.pending[0].answer(); f.pending[0].resolve(); await tick();
  }
  for (const extra of [{ ctrlKey: true }, { metaKey: true }, { altKey: true }, { isComposing: true }]) {
    const f = fixture(); assert.equal(f.down('Home', extra).taken, false); assert.equal(f.wire.length, 0);
  }
  const f = fixture(); f.grant(false);
  assert.deepEqual(f.down(), { taken: false, prevented: false });
  assert.equal(f.wire.length, 0);
  // The real listener must call the tested path before its legacy Shift refusal.
  assert.match(source, /abiVersion === 6 && takeSelectionMove\(event\)\) return;[\s\S]*?if \(event.shiftKey\) return;/);
  assert.match(source, /window.addEventListener\("keyup", endSelectionMoveHold, true\)/);
});

test('unresolved first move admits only one held repeat; release discards it without a wire request', async () => {
  const f = fixture(); f.down();
  for (let i = 0; i < 51; i++) f.down('ArrowRight', { repeat: true });
  assert.equal(f.wire.length, 1);
  assert.equal(f.api.work().outstanding.length, 1);
  assert.ok(f.api.work().held);
  f.api.up({ type: 'keyup', key: 'ArrowRight' });
  assert.equal(f.api.work().held, null);
  f.pending[0].answer(); f.pending[0].resolve(); await tick();
  assert.equal(f.wire.length, 1);
  assert.equal(f.api.work().outstanding.length, 0);
});

test('partial hold releases exactly the retained repeat at answer and counts repaint in depth', async () => {
  const f = fixture(); f.down(); f.down('ArrowRight', { repeat: true });
  f.pending[0].answer();
  assert.equal(f.wire.length, 2);
  assert.equal(f.api.work().outstanding.length, 2);
  f.down('ArrowRight', { repeat: true });
  assert.equal(f.api.work().held, null);
  f.pending[0].resolve(); await tick();
  f.down('ArrowRight', { repeat: true });
  assert.ok(f.api.work().held);
  f.api.up({ type: 'keyup', key: 'Shift' });
  f.pending[1].answer(); f.pending[1].resolve(); await tick();
  assert.equal(f.wire.length, 2);
  assert.equal(f.api.work().outstanding.length, 0);
});

test('retained original direction precedes another key, save, type or click; initial presses are not cancelled', () => {
  for (const next of ['save', 'type:x', 'click']) {
    const f = fixture(); f.down('ArrowLeft'); f.down('ArrowLeft', { repeat: true });
    f.enqueueOther(next);
    assert.deepEqual(f.order, ['move-character-left', 'move-character-left', next]);
    assert.equal(f.api.work().held, null);
  }
  const f = fixture(); f.down('ArrowLeft'); f.down('ArrowLeft', { repeat: true }); f.down('ArrowDown');
  assert.deepEqual(f.order, ['move-character-left', 'move-character-left', 'move-line-down']);
  f.api.up({ type: 'keyup', key: 'ArrowDown' });
  assert.equal(f.wire.length, 3);
});

test('blur, rejection and document replacement never transfer a held repeat to another document', async () => {
  for (const cause of ['blur', 'reject', 'document']) {
    const f = fixture(); f.down(); f.down('ArrowRight', { repeat: true });
    if (cause === 'blur') f.api.up({ type: 'blur' });
    if (cause === 'document') f.session.document = { handle: 2 };
    if (cause === 'reject') f.pending[0].reject(new Error('refused'));
    else { f.pending[0].answer(); f.pending[0].resolve(); }
    await tick();
    assert.equal(f.wire.length, 1, cause);
    assert.equal(f.api.work().held, null, cause);
    assert.equal(f.api.work().outstanding.length, 0, cause);
  }
});

test('the page action bridge forwards extension and the ordered-delete choice to the real session API', async () => {
  const sent = [], results = [];
  const session = { state: { snapshot: { state: 'ready' } },
    action: async (action, options) => { sent.push({ method: 'action', action, options }); return { action }; },
    deleteKey: async (action, options) => { sent.push({ method: 'deleteKey', action, options }); return { action }; } };
  const action = new Function('session', `
    const SESSION_ACCEPTS = new Set(['ready','busy']); const FORMAT_ACTIONS = new Set();
    const ACTION_LABELS = {}; const el = { toolbar: { querySelector: () => null } };
    let engineActionsOut = 0; let busyLeftToAction = false;
    const run = async (label, operation) => operation();
    const renderDocument = () => {}; const formatStateFor = () => false;
    ${fn('editorAction')}
    return editorAction;
  `)(session);
  await action('move-line-down', { extendSelection: true, onResult: r => results.push(r.action) });
  await action('delete-backward', { deleteKey: true, onResult: r => results.push(r.action) });
  await action('delete-forward');
  assert.deepEqual(sent, [
    { method: 'action', action: 'move-line-down', options: { extendSelection: true } },
    { method: 'deleteKey', action: 'delete-backward', options: {} },
    { method: 'action', action: 'delete-forward', options: {} },
  ]);
  assert.deepEqual(results, ['move-line-down', 'delete-backward']);
});

test('causal controls expose a missing release discard and a depth guard that ignores painting work', async () => {
  const releaseMutant = fixture(s => s.replace(fn('endSelectionMoveHold'), 'function endSelectionMoveHold(event) {\n}'));
  releaseMutant.down(); releaseMutant.down('ArrowRight', { repeat: true });
  releaseMutant.api.up({ type: 'keyup', key: 'ArrowRight' });
  releaseMutant.pending[0].answer();
  assert.equal(releaseMutant.wire.length, 2, 'mutant must violate the one-wire release witness');
  const depthMutant = fixture(s => s.replace('>= HELD_DELETE_DEPTH', '>= Infinity'));
  depthMutant.down(); depthMutant.down('ArrowRight', { repeat: true });
  depthMutant.pending[0].answer();
  depthMutant.down('ArrowRight', { repeat: true });
  assert.equal(depthMutant.api.work().outstanding.length + (depthMutant.api.work().held ? 1 : 0), 3,
    'mutant must violate admitted-outstanding depth2');
});
