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
