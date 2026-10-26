import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { NarrowEditorV2Client } from '../narrow-editor-v2-client.js';

const moves = ['move-character-left', 'move-character-right', 'move-line-up',
  'move-line-down', 'move-line-home', 'move-line-end'];
const gestures = ['collapsed', 'range-single', 'range-cross'];
const base = JSON.parse(readFileSync(new URL('../../dist/profiles/e2-editor-v22/sdk-manifest.json', import.meta.url)));
function client(abi = 6, mutate = () => {}, reply = (r) => r) {
  const manifest = structuredClone(base);
  manifest.editorContract.abiVersion = abi;
  for (const action of moves) {
    manifest.editorContract.actions[action].gestures = [...gestures];
    manifest.editorContract.actions[action].limits = [];
  }
  mutate(manifest);
  const sent = [];
  const document = { handle: 7, revision: 4, _assertUsable() {}, _engine: {
    manifest, async _request(operation, payload) {
      sent.push({ operation, payload });
      return reply({ action: payload.action, beforeRevision: 4, revision: 4,
        changed: false, completion: 'verified-move-readback', state: { caret: { x: 10 } } });
    },
  } };
  return { api: new NarrowEditorV2Client(document), sent, document };
}

test('ABI6 selection offers require an actual six-move gesture grant', () => {
  const { api } = client();
  for (const action of moves) for (const gesture of gestures)
    assert.equal(api.offersSelectionMove(action, gesture), true);
  for (const abi of [4, 5, 7, undefined]) {
    const { api } = client(abi, m => { m.editorContract.abiVersion = abi; });
    for (const action of moves) assert.equal(api.offersSelectionMove(action, 'collapsed'), false);
  }
  for (const change of [m => { delete m.editorContract.actions['move-line-up']; },
    m => { m.editorContract.actions['move-line-up'].gestures = []; },
    m => { m.editorContract.actions['move-line-up'].limits = ['no-extend-selection']; }])
    assert.equal(client(6, change).api.offersSelectionMove('move-line-up', 'collapsed'), false);
  const partial = client(6, m => { m.editorContract.actions['move-line-up'].gestures = ['collapsed']; }).api;
  assert.equal(partial.offersSelectionMove('move-line-up', 'range-cross'), false);
  for (const action of ['move-document-start', 'move-document-end', 'delete-selection', 'set-bold'])
    assert.equal(api.offersSelectionMove(action, 'collapsed'), false);
});

test('six existing moves send typed extension and keep their move postcondition', async () => {
  for (const action of moves) {
    const { api, sent, document } = client();
    await api.action(action, { extendSelection: true });
    assert.deepEqual(sent[0], { operation: 'editorActionV2', payload: {
      documentHandle: 7, expectedRevision: 4, action, extendSelection: true, enabled: false,
    } });
    assert.equal(document.revision, 4);
    for (const mutation of [r => ({ ...r, changed: true }), r => ({ ...r, revision: 5 }),
      r => ({ ...r, completion: 'uno-command-result' })])
      await assert.rejects(client(6, () => {}, mutation).api.action(action, { extendSelection: true }),
        { code: 'EDITOR_RESULT_INVALID' });
  }
});

test('legacy character SDK extension stays callable; line and document extension remain closed', async () => {
  for (const abi of [4, 5]) {
    const { api, sent } = client(abi);
    await api.moveCharacter('right', { extendSelection: true });
    for (const direction of ['up', 'down', 'home', 'end'])
      await assert.rejects(api.moveLine(direction, { extendSelection: true }), { code: 'INVALID_ARGUMENT' });
    assert.equal(sent.length, 1);
  }
  const { api, sent } = client();
  for (const action of ['move-document-start', 'move-document-end', 'delete-selection'])
    await assert.rejects(api.action(action, { extendSelection: true }), { code: 'INVALID_ARGUMENT' });
  await assert.rejects(api.moveLine('up', { extendSelection: 'true' }), { code: 'INVALID_ARGUMENT' });
  assert.equal(sent.length, 0);
});
