// SPEC-P-demo-batch-3 S2 (finding 179): every ABI 6 profile's own worker, under that profile's own manifest, takes
// extendSelection on the six moves.  One profile, one verdict, printed as JSON; tools/check_extend_gate_instances.py
// generates the population.  The real worker source in a vm, the real message path.
//   node check_extend_gate_instances.cjs <worker.js> <sdk-manifest.json> [profile name to pretend]
const fs = require('node:fs'), vm = require('node:vm');
const [worker, manifestPath, pretend] = process.argv.slice(2);
const manifest = JSON.parse(fs.readFileSync(manifestPath));
if (pretend) manifest.profile = pretend;
const MOVES = ['move-character-left', 'move-character-right', 'move-line-up', 'move-line-down', 'move-line-home', 'move-line-end'];
const messages = []; let receive;
const context = vm.createContext({TextEncoder, console, self: {addEventListener: (_, fn) => receive = fn, postMessage: m => messages.push(m)}});
vm.runInContext(fs.readFileSync(worker, 'utf8'), context);
const calls = [];
context.fake = (...args) => { calls.push(args[0]); if (args[0] === 'oxsdk_abi_version') return 0x00010001;
  if (args[0] === 'oxsdk_editor_abi_version') return manifest.editorContract.abiVersion; if (args[0] === 'oxsdk_buffer_alloc') return 16; return 0; };
context.manifest = manifest; context.instance = {ccall: context.fake, HEAPU8: new Uint8Array(1024)};
vm.runInContext('moduleInstance=instance;activeManifest=manifest;loadManifest=async()=>manifest;ensureModule=async()=>{};loadStartupResourcePacks=async()=>{};', context);
let id = 1; const cells = [];
(async () => {
  for (const action of MOVES) {
    const requestId = id++, before = calls.length;
    receive({data: {protocolVersion: 1, kind: 'request', requestId, operation: 'editorActionV2',
                    payload: {documentHandle: 1, expectedRevision: 1, action, extendSelection: true, enabled: false}}});
    await new Promise(resolve => setTimeout(resolve, 0));
    const refused = messages.filter(m => m.kind === 'response' && m.requestId === requestId && m.ok === false).at(-1);
    cells.push({action, refused: refused?.error?.code ?? null, reachedEngine: calls.slice(before).includes('oxsdk_editor_action_v2') || calls.slice(before).includes('oxsdk_editor_action')});
  }
  console.log(JSON.stringify({profile: manifest.profile, abi: manifest.editorContract.abiVersion, cells}));
})();
