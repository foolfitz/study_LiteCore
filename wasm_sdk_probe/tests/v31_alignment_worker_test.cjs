// SPEC-P-demo-batch-3 W1, W2 on the real v31 worker source in a vm sandbox: the closed delta rebuilds it, the four alignments reach
// the engine with wire ids 24-27 and both flags false, a flag on them stops at the worker, a manifest without them refuses them, and
// the extend gate is still free of any profile name.  Causal controls remove each change and require the exercise to fail.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.join(__dirname,'..');
const base=fs.readFileSync(path.join(root,'sdk/v30-extend-gate-worker.js'),'utf8');
const source=fs.readFileSync(path.join(root,'sdk/v31-alignment-worker.js'),'utf8');
const delta=JSON.parse(fs.readFileSync(path.join(root,'tests/v31-worker-delta.json')));
let rebuilt=base;
for(const h of delta.hunks){assert.equal(rebuilt.split(h.old).length-1,1,h.item);rebuilt=rebuilt.replace(h.old,()=>h.new);}
assert.equal(rebuilt,source,'the v31 worker is not v30 plus the closed list');
const manifestBase=JSON.parse(fs.readFileSync(path.join(root,'dist/profiles/e2-editor-v30/sdk-manifest.json')));
const ALIGN={'set-align-left':24,'set-align-center':25,'set-align-right':26,'set-align-justify':27};
function sandbox(src,withActions){
  const manifest=JSON.parse(JSON.stringify(manifestBase));manifest.profile='e2-editor-v31';
  if(withActions)for(const [name,id] of Object.entries(ALIGN))manifest.editorContract.actions[name]={id,gestures:['collapsed','range-single','range-cross'],limits:[]};
  const messages=[],calls=[];let receive;
  const context=vm.createContext({TextEncoder,console,self:{addEventListener:(_,fn)=>receive=fn,postMessage:m=>messages.push(m)}});
  vm.runInContext(src,context);
  context.fake=(name,ret,types,args)=>{calls.push({name,args});if(name==='oxsdk_abi_version')return 0x00010001;
    if(name==='oxsdk_editor_abi_version')return 6;if(name==='oxsdk_buffer_alloc')return 16;return 0;};
  context.manifest=manifest;context.instance={ccall:context.fake,HEAPU8:new Uint8Array(1024)};
  vm.runInContext('moduleInstance=instance;activeManifest=manifest;loadManifest=async()=>manifest;ensureModule=async()=>{};loadStartupResourcePacks=async()=>{};',context);
  let id=1;
  const send=async(action,flags={})=>{const requestId=id++,before=calls.length;
    receive({data:{protocolVersion:1,kind:'request',requestId,operation:'editorActionV2',payload:{documentHandle:1,expectedRevision:1,action,extendSelection:false,enabled:false,...flags}}});
    await new Promise(r=>setTimeout(r,0));
    return{call:calls.slice(before).find(c=>c.name==='oxsdk_editor_action'),reply:messages.filter(m=>m.kind==='response'&&m.requestId===requestId).at(-1)};};
  return{send};
}
async function exercise(src){
  const s=sandbox(src,true);
  for(const [name,id] of Object.entries(ALIGN)){
    const {call}=await s.send(name);
    assert.ok(call,name+' did not reach the engine');
    assert.equal(call.args[3],id,name+' wire id');
    assert.deepEqual([call.args[4],call.args[5]],[0,0],name+' flags');
    assert.equal((await s.send(name,{extendSelection:true})).reply?.error?.code,'INVALID_ARGUMENT',name+' took extendSelection');
    assert.equal((await s.send(name,{enabled:true})).reply?.error?.code,'INVALID_ARGUMENT',name+' took enabled');
  }
  assert.ok((await s.send('move-line-up',{extendSelection:true})).call,'the extend gate went back to a name');
  const old=sandbox(src,false);
  const {call,reply}=await old.send('set-align-center');
  assert.equal(call,undefined,'a manifest without the action reached the engine');
  assert.equal(reply?.error?.code,'UNSUPPORTED_OPERATION');
}
(async()=>{
  await exercise(source);
  const controls={
    'old lookup':source.replace('const actionId = EDITOR_V5_ACTION_IDS[payload.action];\n      const forbiddenFields = ["keyCode", "unoCommand", "command"];\n      const hasForbiddenField = forbiddenFields.some((field) =>\n        Object.hasOwn(payload, field));\n      const validRevision = Number.isInteger(payload.expectedRevision)\n        && payload.expectedRevision >= 0\n        && payload.expectedRevision <= 0xffffffff;\n      const typedFlags = typeof payload.extendSelection === "boolean"\n        && typeof payload.enabled === "boolean";\n      const paragraph','const actionId = EDITOR_V4_ACTION_IDS[payload.action];\n      const forbiddenFields = ["keyCode", "unoCommand", "command"];\n      const hasForbiddenField = forbiddenFields.some((field) =>\n        Object.hasOwn(payload, field));\n      const validRevision = Number.isInteger(payload.expectedRevision)\n        && payload.expectedRevision >= 0\n        && payload.expectedRevision <= 0xffffffff;\n      const typedFlags = typeof payload.extendSelection === "boolean"\n        && typeof payload.enabled === "boolean";\n      const paragraph'),
    'wrong id':source.replace('"set-align-right": 26','"set-align-right": 28'),
    'name back in the gate':source.replace('return activeManifest?.editorContract?.abiVersion === 6\n    && EDITOR_V23_EXTEND_ACTIONS.has(action);','return activeManifest?.profile === "e2-editor-v30" && EDITOR_V23_EXTEND_ACTIONS.has(action);'),
  };
  for(const [name,mutated] of Object.entries(controls)){
    assert.notEqual(mutated,source,name+': control did not apply');
    await assert.rejects(exercise(mutated),undefined,name+': control stayed green');
  }
  console.log('v31 worker holds; '+Object.keys(controls).length+' controls red');
})().catch(e=>{console.error(e);process.exit(1);});
