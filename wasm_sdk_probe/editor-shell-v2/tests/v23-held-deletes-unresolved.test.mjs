import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { selectionShapeOf } from '../narrow-editor-v2-session.js';
const source = readFileSync(new URL('../../web/e2-editor-app.js', import.meta.url), 'utf8');
const extract = name => {
  const found = source.match(new RegExp(`^function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?^\\}`, 'm'));
  assert.ok(found, name); return found[0];
};
const tick = () => new Promise(r => setImmediate(r));
function fixture() {
  const requests = [], state = { caret: { x: 10, y: 20, width: 0, height: 30 },
    selection: { observed: true, collapsed: true, rectangles: [] } };
  const session = { document: { handle: 1 }, engine: { manifest: { editorContract: { abiVersion: 6 } } },
    state: { snapshot: { state: 'ready', editorState: state } }, offers: () => true,
    offersSelectionMove: () => true, enqueueCount: 0 };
  let api, beforeinput;
  const editorAction = (action, options) => {
    api.before(); session.enqueueCount++;
    return new Promise((resolve, reject) => requests.push({ action, options, resolve, reject,
      answer: result => options.onResult(result) }));
  };
  api = new Function('session', 'editorAction', 'selectionShapeOf', 'el', `
    let lastSelectionShape = 'collapsed'; let deletesInFlight = 0; let deletesUnanswered = 0;
    let deleteRefusedThisHold = false;
    const heldDeletes = { last: null, count: 0, sending: false };
    const SESSION_ACCEPTS = new Set(['ready', 'busy']); const HELD_DELETE_DEPTH = 2;
    const KEY_ACTIONS = { ArrowRight: 'move-character-right' };
    const selectionMoveHolds = new Map(); const selectionMovesOutstanding = new Set();
    let heldSelectionMove = null; let selectionMoveSending = false; let selectionMoveSequence = 0;
    const DELETE_INPUT_TYPES = {deleteContentBackward:'delete-backward',deleteContentForward:'delete-forward'};
    const paint = () => {};
    ${['deleteActionFor','deleteStateOf','boundaryNoopStands','holdsDelete','dropHeldDeletes',
      'releaseHeldDelete','releaseHeldDeletesBeforeEnqueue','settleDelete','dispatchDelete',
      'takeSelectionMove','sendSelectionMove','releaseHeldSelectionMove',
      'releaseHeldInputsBeforeEnqueue','endSelectionMoveHold'].map(extract).join('\n')}
    ${source.match(/^el\.sink\.addEventListener\("beforeinput", \(event\) => \{[\s\S]*?^\}\);/m)[0]}
    return { before: releaseHeldInputsBeforeEnqueue, move: takeSelectionMove,
      moveWork: () => ({held:heldSelectionMove,out:selectionMovesOutstanding.size}),
      work: () => ({held:heldDeletes.count,out:deletesInFlight,unanswered:deletesUnanswered}) };
  `)(session, editorAction, selectionShapeOf, { sink: { addEventListener: (_, fn) => { beforeinput = fn; } } });
  return { session, requests, api, state, press: (type = 'deleteContentBackward') => beforeinput({ inputType: type, preventDefault() {} }),
    noop: () => ({ completion: 'verified-boundary-noop', beforeRevision: 0, revision: 0, changed: false, state }),
    real: () => ({ completion: 'verified-selection-delete', beforeRevision: 0, revision: 1, changed: true, state }) };
}

test('18 unflagged same-boundary presses are held behind a deliberately unresolved request, not a timer', async () => {
  const f = fixture(); for (let i = 0; i < 18; i++) f.press();
  assert.equal(f.requests.length, 1); assert.equal(f.api.work().held, 17);
  assert.equal(f.requests[0].options.deleteKey, true);
  f.requests[0].answer(f.noop()); f.requests[0].resolve(); await tick();
  assert.deepEqual(f.api.work(), {held:0,out:0,unanswered:0});
  assert.equal(f.requests.length, 1);
});

test('real deletions preserve all18 original keys; no clock or synthetic beforeinput releases them', async () => {
  const f = fixture(); for (let i = 0; i < 18; i++) f.press();
  for (let i = 0; i < 18; i++) {
    assert.equal(f.requests.length, i + 1);
    assert.equal(f.requests[i].action, 'delete-backward');
    f.requests[i].answer(f.real()); f.requests[i].resolve(); await tick();
  }
  assert.equal(f.requests.length, 18);
  assert.deepEqual(f.api.work(), {held:0,out:0,unanswered:0});
});

test('intervening input flushes earlier retained keys and replacement drops only old-document work', async () => {
  const f = fixture(); f.press(); f.press();
  f.api.before(); f.session.enqueueCount++;
  f.press('deleteContentForward');
  assert.deepEqual(f.requests.map(x => x.action), ['delete-backward','delete-backward','delete-forward']);
  const g = fixture(); g.press(); g.press(); g.session.document = {handle:2};
  g.requests[0].answer(g.real()); g.requests[0].resolve(); await tick();
  assert.equal(g.requests.length, 1);
  assert.deepEqual(g.api.work(), {held:0,out:0,unanswered:0});
});

test('interleaved held moves and deletes flush earlier admissions before a different retained key', () => {
  const f = fixture();
  const move = repeat => f.api.move({ key: 'ArrowRight', shiftKey: true, repeat, preventDefault() {} });
  move(false); f.press(); f.press();
  assert.equal(f.api.work().held, 1);
  move(true);
  assert.equal(f.api.work().held, 0);
  assert.ok(f.api.moveWork().held);
  f.press();
  assert.equal(f.api.moveWork().held, null);
  assert.deepEqual(f.requests.map(r => r.action), ['move-character-right', 'delete-backward',
    'delete-backward', 'move-character-right', 'delete-backward']);
});
