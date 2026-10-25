// Separate no-host instrument: no private entrance or shared SDK modification.
import {createDocumentEngine} from './sdk/document-sdk.js';
import {NarrowEditorV2Session} from './editor-shell-v2/narrow-editor-v2-session.js';
const query = new URLSearchParams(location.search);
const profile = query.get('profile'), caseId = query.get('caseId');
const result = globalThis.__sinit = {schema: 1, profile, caseId, complete: false,
  userAgent: navigator.userAgent, requests: [], responses: [], events: [], workers: [],
  steps: [], artifacts: {}, observations: []};
const b64 = bytes => {
  let out = ''; const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 8192) out += String.fromCharCode(...view.subarray(i, i + 8192));
  return btoa(out);
};
const hash = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
  .map(x => x.toString(16).padStart(2, '0')).join('');
const errorData = error => ({code: error?.code, message: String(error?.message || error), details: error?.details});
function snapshot(value) {
  if (value instanceof ArrayBuffer) return {encoding: 'base64', bytes: value.byteLength, data: b64(value)};
  if (ArrayBuffer.isView(value)) return snapshot(value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength));
  if (Array.isArray(value)) return value.map(snapshot);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, snapshot(v)]));
  return value;
}
let generation = 0, session;
function workerFactory(url) {
  const worker = new Worker(url), gen = ++generation;
  const record = {generation: gen, url: String(url), createdAt: performance.now(), terminatedAt: null};
  result.workers.push(record);
  worker.addEventListener('message', event => {
    const message = snapshot(event.data), item = {generation: gen, at: performance.now(), message};
    if (message.kind === 'response') result.responses.push(item);
    if (message.kind === 'event') result.events.push(item);
  });
  return {
    addEventListener: (...args) => worker.addEventListener(...args),
    removeEventListener: (...args) => worker.removeEventListener(...args),
    postMessage: (message, ...args) => {
      if (message.kind === 'request') result.requests.push({generation: gen, at: performance.now(), message: snapshot(message)});
      worker.postMessage(message, ...args);
    },
    terminate: () => {record.terminatedAt = performance.now(); worker.terminate();},
  };
}
async function step(name, fn) {
  const record = {name, generation, startedAt: performance.now()}; result.steps.push(record);
  try {const value = await fn(); record.ok = true; return value;}
  catch (error) {record.ok = false; record.error = errorData(error); throw error;}
  finally {record.finishedAt = performance.now();}
}
async function open(bytes, name) {
  session = new NarrowEditorV2Session({engineFactory: () => createDocumentEngine({
    workerUrl: `./profiles/${profile}/sdk-worker.js`, workerFactory, debug: true,
  })});
  await step('open', () => session.open({bytes, name}));
}
function dispose() { session?.engine?.dispose(); session = null; }
async function save(name) {
  const saved = await step(name, () => session.save());
  return {sha256: await hash(saved.bytes), base64: b64(saved.bytes), bytes: saved.bytes};
}
try {
  const configResponse = await fetch('./s-init-config.json', {cache: 'no-store'});
  if (!configResponse.ok) throw new Error(`config HTTP ${configResponse.status}`);
  const configBytes = await configResponse.arrayBuffer();
  result.configSha256 = await hash(configBytes);
  const config = JSON.parse(new TextDecoder().decode(configBytes));
  const plan = config.cases[caseId], expected = config.profiles[profile];
  if (!plan || !expected) throw new Error('case/profile not in finite comparison');
  result.plan = plan; result.servedSources = {};
  for (const path of Object.keys(config.servedSources)) {
    const response = await fetch(`./${path}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`source HTTP ${response.status}: ${path}`);
    result.servedSources[path] = await hash(await response.arrayBuffer());
  }
  for (const path of Object.keys(expected.artifacts)) {
    const response = await fetch(`./profiles/${profile}/${path}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`artifact HTTP ${response.status}: ${path}`);
    const bytes = await response.arrayBuffer();
    result.artifacts[path] = await hash(bytes);
    if (path === 'sdk-manifest.json') result.manifest = JSON.parse(new TextDecoder().decode(bytes));
  }
  // Available served pack identity is deliberately not described as worker FS.
  for (const fixtureName of plan.fixtures) {
    const response = await fetch(`./s-init-fixtures/${fixtureName}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`fixture HTTP ${response.status}`);
    const fixture = await response.arrayBuffer();
    const observation = {fixtureName, fixtureSha256: await hash(fixture)};
    result.observations.push(observation);
    await open(fixture, fixtureName);
    observation.openGeneration = generation;
    if (caseId === 'paragraph-break') {
      const setup = observation.paragraphSetup = {};
      setup.initialState = await step('initial-caret-state', () => session.editor.getState());
      const caret = setup.initialState.caret;
      if (!caret || ![caret.x, caret.y, caret.height].every(Number.isFinite) ||
          setup.initialState.selectionType !== 'none')
        throw Object.assign(new Error('initial empty-paragraph caret unavailable'), {code: 'S_INIT_PRECONDITION_NOT_ESTABLISHED'});
      setup.point = {xTwips: Math.round(caret.x), yTwips: Math.round(caret.y) + Math.floor(caret.height / 2)};
      // One public client call, without session retry/grace loops or extra keys.
      setup.placement = await step('place-initial-caret', () =>
        session.editor.placeCaret(setup.point.xTwips, setup.point.yTwips));
      setup.afterPlacementState = await step('placed-caret-state', () => session.editor.getState());
      if (setup.afterPlacementState.selection?.observed !== true ||
          setup.afterPlacementState.selection?.collapsed !== true)
        throw Object.assign(new Error('public placement did not establish observed collapsed selection'), {code: 'S_INIT_PRECONDITION_NOT_ESTABLISHED'});
    }
    if (plan.input !== undefined) await step('insertText', () => session.commitText(plan.input));
    if (caseId === 'paragraph-break') {
      observation.paragraphSetup.postMarkerState = await step('post-marker-state', () => session.editor.getState());
      if (observation.paragraphSetup.postMarkerState.selection?.observed !== true ||
          observation.paragraphSetup.postMarkerState.selection?.collapsed !== true)
        throw Object.assign(new Error('post-marker selection precondition absent'), {code: 'S_INIT_PRECONDITION_NOT_ESTABLISHED'});
      await step('InsertPara', () => session.action('insert-paragraph-break'));
    }
    if (caseId === 'linguistic-layout') {
      observation.geometry = await step('pageRectangles', () => session.document.pageRectangles());
      const tile = await step('render', () => session.document.render(config.region));
      observation.render = {region: config.region, width: tile.width, height: tile.height,
        rgbaSha256: await hash(tile.pixels), rgbaBase64: b64(tile.pixels)};
    }
    const saved = await save('save');
    observation.saved = {sha256: saved.sha256, base64: saved.base64};
    if (caseId === 'direct-load-reopen') {
      dispose();
      // Use the actual returned bytes, not the original fixture or a re-export.
      await open(saved.bytes.slice(0), 'exact-saved-reopen.odt');
      observation.reopenGeneration = generation;
      observation.reopenInputSha256 = await hash(saved.bytes);
      const reopened = await save('reopen-save');
      observation.reopened = {sha256: reopened.sha256, base64: reopened.base64};
    }
    dispose();
  }
} catch (error) {result.fatal = errorData(error);}
finally {
  dispose(); result.complete = true;
  document.querySelector('#log').textContent = JSON.stringify({caseId, profile, complete: true, fatal: result.fatal});
}
