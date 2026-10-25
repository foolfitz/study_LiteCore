// The real DocumentEngine request path and real base worker, with only WASM
// replaced by an accepted submission and an injected engine error event.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');

(async () => {
  const sdkSource = fs.readFileSync(path.join(root, 'sdk/document-sdk.js'), 'utf8');
  const {DocumentEngine} = await import('data:text/javascript;base64,'
    + Buffer.from(sdkSource).toString('base64'));
  let receive;
  const messages = [];
  const engine = new DocumentEngine({workerUrl: 'http://diagnostic.invalid/sdk-worker.js'});
  const context = vm.createContext({TextEncoder, console,
    self: {addEventListener: (_, fn) => { receive = fn; },
      postMessage: message => {messages.push(message); engine._handleMessage(message);}}});
  vm.runInContext(fs.readFileSync(path.join(root, 'build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/sdk-worker.js'), 'utf8')
    + fs.readFileSync(path.join(root, 'sdk/v23-diagnostic-worker-tail.js'), 'utf8'), context);
  vm.runInContext(`moduleInstance = {ccall: () => 0};
    activeManifest = {profile: 'e2-editor-v23-diag', editorContract: {abiVersion: 5}};`, context);
  engine._worker = {postMessage: message => receive({data: message}), terminate() {}};
  try {
    assert.equal(engine._defaultTimeoutMs, 30000);
    const promise = engine._request('v23Diagnostic', {kind: 2});
    const requestId = engine._nextRequestId - 1;
    assert.equal(requestId, 1); // actual SDK-generated id, not a fabricated VM message
    assert.equal(vm.runInContext(`pending.has(${requestId})`, context), true);
    context.raw = JSON.stringify({type: 'error', requestId,
      code: 'MUTATION_OUTCOME_UNKNOWN', message: 'missing proof',
      failureShape: 'proof-absent-at-poll:UNO_COMMAND_RESULT',
      operation: 'v23Diagnostic', documentHandle: 42, revision: 7,
      expectedRevision: 6, currentRevision: 7, dispatched: true});
    vm.runInContext('handleCEvent(raw)', context);
    await assert.rejects(promise, error => {
      assert.equal(error.code, 'MUTATION_OUTCOME_UNKNOWN');
      assert.equal(error.details.failureShape, 'proof-absent-at-poll:UNO_COMMAND_RESULT');
      assert.equal(error.details.documentHandle, 42);
      assert.equal(error.details.revision, 7);
      assert.equal(error.details.expectedRevision, 6);
      assert.equal(error.details.currentRevision, 7);
      assert.equal(error.details.dispatched, true);
      return true;
    });
    assert.equal(engine._pending.size, 0);
    assert.equal(vm.runInContext('pending.size', context), 0);
    // The diagnostic projection does not leak into other profiles or errors.
    for (const [profile, abi, shape] of [
      ['e2-editor-v22', 5, 'proof-absent-at-poll:UNO_COMMAND_RESULT'],
      ['e2-editor-v23-diag', 6, 'proof-absent-at-poll:UNO_COMMAND_RESULT'],
      ['e2-editor-v23-diag', 5, undefined],
      ['e2-editor-v23-diag', 5, {untrusted: 'not a string'}],
    ]) {
      context.profile = profile; context.abi = abi;
      vm.runInContext('activeManifest.profile=profile; activeManifest.editorContract.abiVersion=abi;', context);
      context.raw = JSON.stringify({type:'error', requestId: 99, code:'ENGINE_ERROR', failureShape:shape});
      vm.runInContext('handleCEvent(raw)', context);
      assert.equal(Object.hasOwn(messages.at(-1).error, 'failureShape'), false);
    }
    // Malformed event remains the base worker's protocol error, with no context leakage.
    vm.runInContext('handleCEvent("not JSON")', context);
    assert.equal(messages.at(-1).event, 'worker-protocol-error');
    vm.runInContext('postResponse(1, false, {code:"UNRELATED"})', context);
    assert.equal(Object.hasOwn(messages.at(-1).error, 'failureShape'), false);
    console.log('actual SDK request: typed proof error, original fields and pending cleanup pass');
  } finally {
    engine.dispose();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
