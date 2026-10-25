import {createDocumentEngine} from './sdk/document-sdk.js';
import {NarrowEditorV2Session} from './editor-shell-v2/narrow-editor-v2-session.js';
const params = new URLSearchParams(location.search);
const arm = params.get('arm');
const profile = params.get('profile') || 'e2-editor-v23-diag';
const r = globalThis.__v23remaining = {schema: 1, profile, arm, userAgent: navigator.userAgent, complete: false,
  steps: [], requests: [], cancels: [], responses: [], events: [], workers: [], artifacts: {}, fixtures: {}, instrumentServed: {}};
const hash = async b => [...new Uint8Array(await crypto.subtle.digest('SHA-256', b))]
  .map(x => x.toString(16).padStart(2, '0')).join('');
const err = e => ({code: e?.code, message: String(e?.message || e), details: e?.details});
let gen = 0, session;
const pendingHashes = [];
function factory(url) {
  const w = new Worker(url), generation = ++gen;
  const rec = {generation, createdAt: performance.now()}; r.workers.push(rec);
  w.addEventListener('message', ({data: m}) => {
    if (m.kind === 'event') r.events.push({generation, at: performance.now(), message: m});
    if (m.kind === 'response') {
      const result = {...m.result};
      for (const [k,v] of Object.entries(result))
        if (v instanceof ArrayBuffer || ArrayBuffer.isView(v)) result[k] = {byteLength: v.byteLength};
      r.responses.push({generation, at: performance.now(), message: {...m, result}});
    }
  });
  return {addEventListener: (...a) => w.addEventListener(...a),
    removeEventListener: (...a) => w.removeEventListener(...a),
    postMessage: (m, ...a) => {
      if (m.kind === 'request') {
        const payload = {...m.payload};
        if (payload.buffer) {
          const input = payload.buffer.slice(0);
          payload.buffer = {byteLength: input.byteLength};
          pendingHashes.push(hash(input).then(digest => {payload.buffer.sha256 = digest;}));
        }
        if (typeof payload.text === 'string') payload.textUtf8Bytes = new TextEncoder().encode(payload.text).length;
        r.requests.push({generation, at: performance.now(), ...m, payload});
      }
      if (m.kind === 'cancel') r.cancels.push({generation, at: performance.now(), ...m});
      w.postMessage(m, ...a);
    }, terminate: () => {rec.terminatedAt = performance.now(); w.terminate();}};
}
async function step(name, fn) {
  const s = {name, startedAt: performance.now()}; r.steps.push(s);
  try {const v = await fn(); s.ok = true;
    s.value = v instanceof ArrayBuffer ? {byteLength: v.byteLength} : v;
    return v;
  } catch (e) {s.ok = false; s.error = err(e); throw e;}
  finally {s.finishedAt = performance.now();}
}
async function open(name, useSession = false) {
  const bytes = await (await fetch(`./${name}.odt`)).arrayBuffer();
  r.fixtures[name] = {sha256: await hash(bytes), bytes: bytes.byteLength};
  if (useSession) {
    session = new NarrowEditorV2Session({engineFactory: () => createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, workerFactory: factory, debug: true})});
    await step(`open-${name}`, () => session.open({bytes, name: `${name}.odt`}));
    return {engine: session.engine, doc: session.document};
  }
  const engine = await createDocumentEngine({workerUrl: `./profiles/${profile}/sdk-worker.js`,
    workerFactory: factory, debug: true});
  // Unlike session.open's historical180s, honest-command timing uses SDK30s.
  const doc = await step(`open-${name}`, () => engine.open(bytes, {name: `${name}.odt`}));
  return {engine, doc};
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function saved(doc, name) {
  const bytes = await step(name, () => doc.save());
  r[name] = {sha256: await hash(bytes), byteLength: bytes.byteLength};
}
let engine;
try {
  for (const file of ['e2-editor.html', 'v23-remaining.js']) {
    const response = await fetch(`./${file}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`instrument HTTP ${response.status}: ${file}`);
    r.instrumentServed[file] = await hash(await response.arrayBuffer());
  }
  for (const file of ['probe.wasm', 'probe.js', 'sdk-worker.js', 'sdk-manifest.json']) {
    const response = await fetch(`./profiles/${profile}/${file}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`${file}: ${response.status}`);
    r.artifacts[file] = await hash(await response.arrayBuffer());
  }
  if (arm === 'html-positive' || arm === 'html-negative') {
    const opened = await open('frame', true); engine = opened.engine;
    const found = await step('040-anchor', () => opened.doc.search('IV-ASCHAR'));
    const q = String(found?.selections?.[0]?.rectangles || '').split(';')[0].split(',').map(Number);
    if (!found.found || q.length !== 4 || q.some(x => !Number.isFinite(x)))
      throw new Error('IV-ASCHAR actual search rectangle absent');
    r.selectionSetup = {anchor: 'IV-ASCHAR', rectangle: q, startXTwips: q[0],
      startYTwips: q[1] + Math.floor(q[3] / 2), endXTwips: q[0] + 8000, endYTwips: q[1] + Math.floor(q[3] / 2)};
    await step('040-select', () => engine._request('editorSelectRangeV2', {
      documentHandle: opened.doc.handle, ...r.selectionSetup}));
    r.preSelection = await step('040-complex-read', () => opened.doc.getSelection());
    if (r.preSelection.selectionType !== 'complex') throw new Error('040 precondition: selection is not COMPLEX');
    const kind = arm === 'html-positive' ? 9 : 3;
    r.control = {kind, startedAt: performance.now()};
    try {r.control.result = await session._enqueue('040-private-html',
      () => engine._request('v23Diagnostic', {kind}));}
    catch (e) {r.control.error = err(e);}
    r.control.finishedAt = performance.now();
    await Promise.resolve(); r.control.stateAfter = session.state.snapshot;
    if (kind === 3 && session.state.snapshot.state === 'recoverable-error') {
      await step('040-restart', () => session.restart()); engine = session.engine;
      r.recovered = session.state.snapshot;
      await saved(session.document, '040-recovery-save');
    }
  } else if (arm === 'frame') {
    const opened = await open('frame'); engine = opened.engine;
    // A public close success must have an actual worker close response, not timeout recovery.
    await step('frame-close', () => opened.doc.close());
    r.exactHtmlSelection = {status: 'NOT_ESTABLISHED', reason: 'retained037guard-no-public-frame-html-entrance'};
  } else if (arm === 'largest') {
    const opened = await open('largest'); engine = opened.engine;
    r.firstState = await step('first-reply-after-largest', () => engine._request('editorGetStateV2',
      {documentHandle: opened.doc.handle}));
    r.geometry = await step('largest-page-rectangles', () => opened.doc.pageRectangles());
    await step('largest-close', () => opened.doc.close());
  } else if (arm === 'workload') {
    const opened = await open('plain'); engine = opened.engine;
    // Exactly65536 UTF8bytes, many short paragraphs rather than one oversized paragraph.
    const markdown = 'v23 markdown timing paragraph.\n\n'.repeat(2048).slice(0, 65536).padEnd(65536, 'x');
    r.markdown = {bytes: new TextEncoder().encode(markdown).length,
      sha256: await hash(new TextEncoder().encode(markdown))};
    await step('markdown-64KiB', () => opened.doc.pasteMarkdown(markdown));
    await saved(opened.doc, 'markdown-save');
    await step('plain-close', () => opened.doc.close()); engine.dispose(); engine = null;
    const long = await open('long60', true); engine = long.engine;
    await step('long60-type', () => session.commitText('V23_TIMING'));
    r.dirtyMove = await step('long60-dirty-move', () => session.action('move-character-left'));
    await saved(long.doc, 'long60-save');
    const search = await step('merge-anchor', () => long.doc.search('LD-P01-L02'));
    const coords = String(search?.selections?.[0]?.rectangles || '').split(';')[0].split(',').map(Number);
    if (!search.found || coords.length !== 4 || coords.some(x => !Number.isFinite(x)))
      throw new Error('long60 merge anchor absent');
    await step('merge-place-caret', () => session.placeCaret(coords[0], coords[1] + coords[3] / 2));
    await step('merge-home', () => session.action('move-line-home'));
    r.merge = await step('long60-merge', () => session.action('delete-backward'));
    r.afterMerge = await step('first-reply-after-merge', () => session.editor.getState());
    // Fixed observation windows only. No declaration that engine idle layout completed.
    r.layoutWindows = [];
    for (const mode of ['painting', 'idle']) {
      const window = {mode, start: performance.now(), observations: []}; r.layoutWindows.push(window);
      const until = window.start + 2000;
      if (mode === 'painting') {
        while (performance.now() < until) {
          const painted = await long.doc.render({canvasWidthPx: 128, canvasHeightPx: 128});
          window.observations.push({at: performance.now(), width: painted.documentWidthTwips,
            height: painted.documentHeightTwips});
        }
      } else await pause(2000);
      window.end = performance.now();
      window.geometry = await long.doc.pageRectangles();
    }
    await saved(long.doc, 'long60-after-merge-save');
    await step('long60-close', () => long.doc.close());
  } else throw new Error(`unknown arm: ${arm}`);
} catch (e) {r.fatal = err(e);}
finally {
  engine?.dispose(); session?.engine?.dispose();
  await Promise.all(pendingHashes);
  r.complete = true; document.querySelector('#status').textContent = JSON.stringify({arm, fatal: r.fatal});
}
