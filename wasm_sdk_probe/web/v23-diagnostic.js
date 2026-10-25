// Private no-host instrument. No frozen SDK/session source is modified.
import {createDocumentEngine} from './sdk/document-sdk.js';
import {NarrowEditorV2Session} from './editor-shell-v2/narrow-editor-v2-session.js';
const PROFILE = 'e2-editor-v23-diag';
const params = new URLSearchParams(location.search);
const arm = params.get('arm') || 'smoke';
const fixtureName = params.get('fixtureName') || 'v23-diagnostic.odt';
const result = globalThis.__v23 = {schema: 1, arm, profile: PROFILE, userAgent: navigator.userAgent,
  fixtureName, complete: false, events: [], requests: [], responses: [], opens: [], steps: [], workers: [], artifacts: {}};
let generation = 0;
const errorData = e => ({code: e?.code, message: String(e?.message || e), details: e?.details});
const hash = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
  .map(x => x.toString(16).padStart(2, '0')).join('');
const b64 = bytes => {
  let out = ''; const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 8192) out += String.fromCharCode(...view.subarray(i, i + 8192));
  return btoa(out);
};
function workerFactory(url) {
  const worker = new Worker(url), gen = ++generation;
  const record = {generation: gen, createdAt: performance.now(), terminatedAt: null};
  result.workers.push(record);
  worker.addEventListener('message', event => {
    const m = event.data;
    // Capture all actual open responses, including session recovery opens.
    const request = result.requests.find(r => r.generation === gen && r.requestId === m.requestId);
    if (m.kind === 'response') result.responses.push({generation: gen, at: performance.now(), message: m});
    if (m.kind === 'response' && request?.operation === 'open')
      result.opens.push({generation: gen, requestId: m.requestId, response: m});
    if (m.kind === 'event') result.events.push({generation: gen, at: performance.now(), message: m});
  });
  return {
    addEventListener: (...args) => worker.addEventListener(...args),
    removeEventListener: (...args) => worker.removeEventListener(...args),
    postMessage: (message, ...args) => {
      if (message.kind === 'request') result.requests.push({generation: gen, at: performance.now(),
        requestId: message.requestId, operation: message.operation, payload: Object.fromEntries(Object.entries(message.payload || {}).filter(([k]) => !['buffer', 'bytes'].includes(k)))});
      worker.postMessage(message, ...args);
    },
    terminate: () => {record.terminatedAt = performance.now(); worker.terminate();},
  };
}
async function step(name, fn) {
  const record = {name, startedAt: performance.now()}; result.steps.push(record);
  try {const value = await fn(); record.ok = true; return value;}
  catch (e) {record.ok = false; record.error = errorData(e); throw e;}
  finally {record.finishedAt = performance.now();}
}
let session;
try {
  for (const name of ['sdk-manifest.json', 'probe.wasm', 'probe.js', 'sdk-worker.js']) {
    const response = await fetch(`./profiles/${PROFILE}/${name}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
    const bytes = await response.arrayBuffer(); result.artifacts[name] = await hash(bytes);
    if (name === 'sdk-manifest.json') result.manifest = JSON.parse(new TextDecoder().decode(bytes));
  }
  const fixture = await (await fetch('./fixture.odt')).arrayBuffer();
  result.fixtureSha256 = await hash(fixture);
  session = new NarrowEditorV2Session({engineFactory: () => createDocumentEngine({
    workerUrl: `./profiles/${PROFILE}/sdk-worker.js`, workerFactory, debug: true,
    // Omit timeoutMs: this intentionally tests the existing SDK default.
  })});
  globalThis.__v23Session = session;
  await step('open', () => session.open({bytes: fixture, name: fixtureName}));
  result.initialState = session.state.snapshot;
  if (arm === 'smoke') {
    await step('type', () => session.commitText('V23_DIAGNOSTIC_TOKEN'));
    await step('move', () => session.action('move-character-left'));
    const saved = await step('save', () => session.save());
    result.savedBase64 = b64(saved.bytes);
    // Deliberately bypass the session's serial queue: contend at the engine.
    await step('queue-pair', () => Promise.all([1, 2].map(() => session.engine._request(
      'editorGetStateV2', {documentHandle: session.document.handle}))));
  } else if (arm === 'wd') {
    const {runWd} = await import('./v23-diagnostic-wd.js');
    result.wd = await runWd({session, result, step, b64, hash}, {caseId: params.get('caseId')});
  } else if (['proof', 'hang', 'js-thread'].includes(arm)) {
    const kind = {proof: 2, hang: 1, 'js-thread': 3}[arm];
    result.control = {kind, startedAt: performance.now()};
    try {
      await session._enqueue('v23-private-control', () => session.engine._request('v23Diagnostic', {kind}));
      result.control.returned = true;
    } catch (e) {result.control.error = errorData(e);}
    result.control.finishedAt = performance.now();
    // A microtask permits the existing queue's catch to enter its recovery state.
    await Promise.resolve();
    result.control.stateAfter = session.state.snapshot;
    if (kind !== 2 && ['recoverable-error', 'restart-required'].includes(session.state.snapshot.state)) {
      await step('restart', () => session.restart());
      result.recoveredState = session.state.snapshot;
      const saved = await step('recovery-save', () => session.save());
      result.savedBase64 = b64(saved.bytes);
    }
  } else throw new Error(`unknown arm ${arm}`);
} catch (e) {result.fatal = errorData(e);}
finally {
  // Disposal terminates only the worker owned by this page, even if LOK is stuck.
  session?.engine?.dispose();
  result.complete = true;
  document.querySelector('#log').textContent = JSON.stringify({arm, complete: true, fatal: result.fatal});
}
