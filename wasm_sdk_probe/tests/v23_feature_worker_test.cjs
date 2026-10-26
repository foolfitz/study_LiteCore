const assert=require('node:assert/strict'), fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.join(__dirname,'..');
const base=fs.readFileSync(path.join(root,'build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/sdk-worker.js'));
assert.equal(crypto.createHash('sha256').update(base).digest('hex'),'0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350');
const original=fs.readFileSync(path.join(root,'sdk/v23-feature-worker.js'),'utf8');
const reference=JSON.parse(fs.readFileSync(path.join(root,'dist/profiles/e2-editor-v22/sdk-manifest.json')));
function exercise(source) {
 const messages=[],calls=[];let receive;
 const context=vm.createContext({TextEncoder,console,self:{addEventListener:(_,fn)=>receive=fn,postMessage:m=>messages.push(m)}});
 vm.runInContext(source,context);context.fake=(...args)=>{calls.push(args);return 0;};context.manifest=structuredClone(reference);context.manifest.profile='e2-editor-v23';context.manifest.editorContract.abiVersion=6;
 for(const name of ['move-character-left','move-character-right','move-line-up','move-line-down','move-line-home','move-line-end'])context.manifest.editorContract.actions[name].gestures=['collapsed','range-single','range-cross'];
 vm.runInContext('moduleInstance={ccall:fake};activeManifest=manifest;',context);
 let id=1;
 function send(action,extendSelection,enabled=false,extra={},operation='editorActionV2') {
  const before=calls.length;
  receive({data:{protocolVersion:1,kind:'request',requestId:id++,operation,payload:{documentHandle:1,expectedRevision:0xffffffff,action,extendSelection,enabled,...extra}}});
  return calls.length>before;
 }
 const moves=new Set(['move-character-left','move-character-right','move-line-up','move-line-down','move-line-home','move-line-end']);
 for(const [name,spec]of Object.entries(reference.editorContract.actions)) {
  assert.equal(send(name,true),moves.has(name),name);
  if(moves.has(name))assert.equal(calls.at(-1)[3][3],spec.id);
 }
 assert.equal(send('move-line-up',true,false,{},'editorActionV1'),false);
 for(const profile of ['e2-editor-v22','e2-editor-v23-diag-r2']) {
  context.manifest.profile=profile;
  assert.equal(send('move-line-up',true),false);
 }
 context.manifest.profile='e2-editor-v23';context.manifest.editorContract.abiVersion=5;
 assert.equal(send('move-line-up',true),false);
 context.manifest.editorContract.abiVersion=6;
 for(const extra of [{keyCode:1},{unoCommand:'.uno:Anything'},{command:'x'},{expectedRevision:-1},{expectedRevision:4294967296}]) assert.equal(send('move-line-up',true,false,extra),false);
 assert.equal(send('move-line-up',1),false);assert.equal(send('move-line-up',true,true),false);
 receive({data:{protocolVersion:1,kind:'request',requestId:id++,operation:'v23Diagnostic',payload:{kind:1}}});
 assert.equal(messages.at(-1).error.code,'UNKNOWN_OPERATION');
 assert(!source.includes('oxsdk_v23_diagnostic'));
}
exercise(original);
for(const [before,after]of [
 ['|| featureExtendPermitted(payload.action)',''],
 ['activeManifest?.editorContract?.abiVersion === 6','true'],
 ['activeManifest?.profile === "e2-editor-v23"','true'],
 ['"move-line-down", "move-line-home", "move-line-end",','"move-line-down", "move-line-home", "move-line-end", "move-document-end",']]) {
 assert(original.includes(before));assert.throws(()=>exercise(original.replace(before,after)));
}
console.log('feature archived-base worker: six moves, ABI/profile gating, legacy V1, negative fields and four causal controls pass');
