// SPEC-P-calc-undo 4.2: the ods-editor-v4 worker in a vm sandbox.  It is the frozen v3 worker plus the closed list in
// tests/ods-v4-worker-delta.json, derived the way tools/derive_ods_v4_worker.py derives it; undo and redo reach their exports only with the `undo` capability; the engine's `undone` and
// `redone` carry the counts and the cell cursor through to the reply; NOTHING_TO_UNDO comes back as itself.  Causal control: the
// frozen v3 worker runs the same exercise and must fail it (it drops the counts and the cursor).
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.join(__dirname,'..');
const base=fs.readFileSync(path.join(root,'dist/profiles/ods-editor-v3/sdk-worker.js'),'utf8');
assert.equal(crypto.createHash('sha256').update(base).digest('hex'),'6df703229c9dea12efa9584df94f970bb0bb0a5d5787d0a43ce3052d1320f306');
// The worker is derived at build time (tools/derive_ods_v4_worker.py); the same derivation, run here and by the tool.
const delta=JSON.parse(fs.readFileSync(path.join(root,'tests/ods-v4-worker-delta.json')));
let source=base;
for(const h of delta.hunks){assert.equal(source.split(h.old).length-1,1,h.item);source=source.replace(h.old,()=>h.new);}
const derivedFile=path.join(require('node:os').tmpdir(),`ods-v4-worker-${process.pid}.js`);
const derived=require('node:child_process').execFileSync('python3',[path.join(root,'tools/derive_ods_v4_worker.py'),'--out',derivedFile],{encoding:'utf8'});
fs.unlinkSync(derivedFile);
assert.equal(JSON.parse(derived).sha256,crypto.createHash('sha256').update(source).digest('hex'),'the tool derives another worker');
const manifestBase=JSON.parse(fs.readFileSync(path.join(root,'dist/profiles/ods-editor-v3/sdk-manifest.json')));

function sandbox(src,capabilities){
  const manifest={...manifestBase,profile:'ods-editor-v4',capabilities};
  const messages=[],calls=[];let receive;
  const context=vm.createContext({TextEncoder,console,self:{addEventListener:(_,fn)=>receive=fn,postMessage:m=>messages.push(m)}});
  vm.runInContext(src,context);
  context.fake=(name,ret,types,args)=>{calls.push({name,args});if(name==='oxsdk_abi_version')return 0x00010001;return 0;};
  context.manifest=manifest;context.instance={ccall:context.fake,HEAPU8:new Uint8Array(64)};
  vm.runInContext('moduleInstance=instance;activeManifest=manifest;loadManifest=async()=>manifest;ensureModule=async()=>{};loadStartupResourcePacks=async()=>{};',context);
  let id=1;
  const send=async(operation,payload,event)=>{const requestId=id++;const before=calls.length;
    receive({data:{protocolVersion:1,kind:'request',requestId,operation,payload}});
    await new Promise(r=>setTimeout(r,0));
    if(event)context.handleCEvent(JSON.stringify({...event,requestId}));
    await new Promise(r=>setTimeout(r,0));
    return{reply:messages.filter(m=>m.kind==='response'&&m.requestId===requestId).at(-1),
           call:calls.slice(before).find(c=>c.name.startsWith('oxsdk_document_'))};};
  return{send};
}
const P={documentHandle:1,expectedRevision:3};
const CAP=[...manifestBase.capabilities,'undo'];
const CURSOR={part:0,column:5,row:0,moved:true};

async function exercise(src){
  const s=sandbox(src,CAP);
  for(const [operation,exported,type,counts] of [['undo','oxsdk_document_undo','undone',{undoCount:0,redoCount:1}],
      ['redo','oxsdk_document_redo','redone',{undoCount:1,redoCount:0}]]){
    const {call,reply}=await s.send(operation,P,{type,documentHandle:1,revision:4,...counts,cursor:CURSOR});
    assert.ok(call,`${operation} did not reach the engine`);
    assert.equal(call.name,exported);
    assert.deepEqual([...call.args.slice(1)],[1,3]);
    assert.equal(reply.ok,true);
    assert.equal(reply.result.revision,4);
    assert.equal(reply.result.undoCount,counts.undoCount,`${operation}: the counts did not reach the reply`);
    assert.equal(reply.result.redoCount,counts.redoCount,`${operation}: the counts did not reach the reply`);
    assert.deepEqual({...reply.result.cursor},CURSOR,`${operation}: the cursor did not reach the reply`);
  }
  const {reply:none}=await s.send('undo',P,{type:'undone',documentHandle:1,revision:4,undoCount:0,redoCount:1,cursor:null});
  assert.equal(none.result.cursor,null);
  const {reply:empty}=await s.send('undo',P,{type:'error',operation:'undone',code:'NOTHING_TO_UNDO',message:'there is nothing to undo; nothing was dispatched',documentHandle:1,revision:3});
  assert.equal(empty.ok,false);
  assert.equal(empty.error.code,'NOTHING_TO_UNDO');
  const old=sandbox(src,manifestBase.capabilities);
  for(const operation of ['undo','redo']){
    const {call,reply}=await old.send(operation,P);
    assert.equal(call,undefined,`a profile without undo reached for ${operation}`);
    assert.equal(reply.ok,false);
    assert.equal(reply.error.code,'UNSUPPORTED_OPERATION');
  }
}
(async()=>{
  await exercise(source);
  await assert.rejects(exercise(base),/did not reach the reply/,'causal control: the frozen v3 worker passed');
  console.log('ods-v4 worker: delta closed, undo and redo walk, counts and cursor reach the reply; v3 fails the same exercise');
})().catch(error=>{console.error(error);process.exit(1);});
