// specs/SPEC-P-ms-formats.md 6.1 F3: the e2-editor-v33 and ods-editor-v5 workers in a vm sandbox.  Each is its frozen base plus the
// closed list in tests/v33-worker-delta.json / tests/ods-v5-worker-delta.json, derived the way tools/derive_ms_formats_worker.py
// derives it (the tool is run and must give the same bytes).  For each:
//   - a Microsoft-format name opens, and that format saves, only with the manifest's capability (UNSUPPORTED_OPERATION without it,
//     and the engine is never called);
//   - the ODF open and save keep their rows;
//   - the engine's `format` on `opened` reaches the open reply.
// Causal control: the frozen base runs the same exercise and must fail it (it gates nothing and drops `format`).
//   node tests/ms_formats_worker_test.cjs
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const crypto = require('node:crypto'), os = require('node:os'), child = require('node:child_process');
const root = path.join(__dirname, '..');
const sha = (text) => crypto.createHash('sha256').update(text).digest('hex');

const PROFILES = {
  writer: { base: 'dist/profiles/e2-editor-v32', baseSha: 'c394302c589baff3b40ff67a7579e07cf53fc7447dd3f04b26ff9c827280ff36',
            delta: 'tests/v33-worker-delta.json', ms: 'docx', odf: 'odt', profile: 'e2-editor-v33' },
  calc: { base: 'dist/profiles/ods-editor-v4', baseSha: '4a06fbe45c458b4c9aa60ab7bcd624894dace729a2b83f009f3e9008ccc8919c',
          delta: 'tests/ods-v5-worker-delta.json', ms: 'xlsx', odf: 'ods', profile: 'ods-editor-v5' },
};

function derive(name) {
  const p = PROFILES[name];
  const base = fs.readFileSync(path.join(root, p.base, 'sdk-worker.js'), 'utf8');
  assert.equal(sha(base), p.baseSha, `${name}: the frozen base worker moved`);
  let source = base;
  for (const h of JSON.parse(fs.readFileSync(path.join(root, p.delta))).hunks) {
    assert.equal(source.split(h.old).length - 1, 1, `${name}: ${h.item}`);
    source = source.replace(h.old, () => h.new);
  }
  const out = path.join(os.tmpdir(), `ms-formats-worker-${name}-${process.pid}.js`);
  const tool = JSON.parse(child.execFileSync('python3', [path.join(root, 'tools/derive_ms_formats_worker.py'), '--profile', name, '--out', out], { encoding: 'utf8' }));
  fs.unlinkSync(out);
  assert.equal(tool.sha256, sha(source), `${name}: the tool derives another worker`);
  return { base, source };
}

function sandbox(src, manifestBase, capabilities, profile) {
  const manifest = { ...manifestBase, profile, capabilities };
  const messages = [], calls = [];
  let receive;
  const context = vm.createContext({ TextEncoder, console, self: { addEventListener: (_, fn) => receive = fn, postMessage: (m) => messages.push(m) } });
  vm.runInContext(src, context);
  context.fake = (name, ret, types, args) => {
    calls.push({ name, args });
    if (name === 'oxsdk_abi_version') return manifestBase.abiVersion;
    if (name === 'oxsdk_buffer_alloc') return 16;
    return 0;
  };
  context.manifest = manifest;
  context.instance = { ccall: context.fake, HEAPU8: new Uint8Array(1 << 16) };
  vm.runInContext('moduleInstance=instance;activeManifest=manifest;loadManifest=async()=>manifest;ensureModule=async()=>{};loadStartupResourcePacks=async()=>{};', context);
  let id = 1;
  const send = async (operation, payload, events = []) => {
    const requestId = id++;
    const before = calls.length;
    receive({ data: { protocolVersion: 1, kind: 'request', requestId, operation, payload } });
    await new Promise((r) => setTimeout(r, 0));
    for (const event of events) context.handleCEvent(JSON.stringify({ ...event, requestId }));
    await new Promise((r) => setTimeout(r, 0));
    return { reply: messages.filter((m) => m.kind === 'response' && m.requestId === requestId).at(-1),
             call: calls.slice(before).find((c) => c.name === `oxsdk_document_${operation}`) };
  };
  // The buffer is made in the sandbox's realm: the worker checks `instanceof ArrayBuffer`.
  return { send, buffer: () => vm.runInContext('new ArrayBuffer(8)', context) };
}

const opened = (format) => [
  { type: 'opened', documentHandle: 1, revision: 0, parts: 1, width: 100, height: 100, tileMode: 0, schemaVersion: 1, ...(format ? { format } : {}) },
  { type: 'view-ready', documentHandle: 1, revision: 0, schemaVersion: 1 },
];

async function exercise(name, src) {
  const p = PROFILES[name];
  const manifestBase = JSON.parse(fs.readFileSync(path.join(root, p.base, 'sdk-manifest.json')));
  const withMs = [...manifestBase.capabilities, `open-${p.ms}`, `save-${p.ms}`];
  // The Microsoft format, granted.
  const granted = sandbox(src, manifestBase, withMs, p.profile);
  const open = await granted.send('open', { buffer: granted.buffer(), name: `Report.${p.ms.toUpperCase()}` }, opened(p.ms));
  assert.ok(open.call, `${name}: a granted .${p.ms} open did not reach the engine`);
  assert.equal(open.reply.ok, true);
  assert.equal(open.reply.result.format, p.ms, `${name}: the engine's format did not reach the open reply`);
  const save = await granted.send('save', { documentHandle: 1, format: p.ms });
  assert.ok(save.call, `${name}: a granted ${p.ms} save did not reach the engine`);
  // Not granted: refused before the engine.
  const plain = sandbox(src, manifestBase, manifestBase.capabilities, p.profile);
  const refusedOpen = await plain.send('open', { buffer: plain.buffer(), name: `report.${p.ms}` });
  assert.equal(refusedOpen.call, undefined, `${name}: an ungranted .${p.ms} open reached the engine`);
  assert.equal(refusedOpen.reply.error.code, 'UNSUPPORTED_OPERATION');
  assert.equal(refusedOpen.reply.error.requiredCapability, `open-${p.ms}`);
  const refusedSave = await plain.send('save', { documentHandle: 1, format: p.ms });
  assert.equal(refusedSave.call, undefined, `${name}: an ungranted ${p.ms} save reached the engine`);
  assert.equal(refusedSave.reply.error.requiredCapability, `save-${p.ms}`);
  // ODF keeps its rows, and a reply without `format` keeps its shape.
  const odfOpen = await plain.send('open', { buffer: plain.buffer(), name: `report.${p.odf}` }, opened(null));
  assert.ok(odfOpen.call, `${name}: the .${p.odf} open was refused`);
  assert.equal(odfOpen.reply.ok, true);
  assert.equal('format' in odfOpen.reply.result, false, `${name}: a format appeared that the engine did not send`);
  const odfSave = await plain.send('save', { documentHandle: 1, format: p.odf });
  assert.ok(odfSave.call, `${name}: the ${p.odf} save was refused`);
}

(async () => {
  for (const name of Object.keys(PROFILES)) {
    const { base, source } = derive(name);
    await exercise(name, source);
    await assert.rejects(exercise(name, base), /reached the engine|did not reach the open reply/,
                         `causal control: the frozen ${name} base passed`);
  }
  console.log('ms-formats workers: deltas closed and derived by the tool; docx/xlsx open and save only with their capabilities; '
              + 'ODF rows unchanged; format reaches the open reply; both frozen bases fail the same exercise');
})().catch((error) => { console.error(error); process.exit(1); });
