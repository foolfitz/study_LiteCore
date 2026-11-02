// SPEC-P-demo-batch-4 W1, W2 on the real v32 worker source in a vm sandbox: the closed delta rebuilds it, the six toggles reach the
// engine with wire ids 28-33 and both flags false, a flag on them stops at the worker, a manifest without them refuses them, and the
// three format fields survive the projection a reply goes through.  Causal controls remove each change and require the exercise to fail.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.join(__dirname,'..');
const base=fs.readFileSync(path.join(root,'sdk/v31-alignment-worker.js'),'utf8');
const source=fs.readFileSync(path.join(root,'sdk/v32-paragraph-read-worker.js'),'utf8');
const delta=JSON.parse(fs.readFileSync(path.join(root,'tests/v32-worker-delta.json')));
let rebuilt=base;
for(const h of delta.hunks){assert.equal(rebuilt.split(h.old).length-1,1,h.item);rebuilt=rebuilt.replace(h.old,()=>h.new);}
assert.equal(rebuilt,source,'the v32 worker is not v31 plus the closed list');
const manifestBase=JSON.parse(fs.readFileSync(path.join(root,'dist/profiles/e2-editor-v31/sdk-manifest.json')));
const TOGGLES={'toggle-heading-1':28,'toggle-heading-2':29,'toggle-heading-3':30,'toggle-heading-4':31,'toggle-list-unordered':32,'toggle-list-ordered':33};
function sandbox(src,withActions){
  const manifest=JSON.parse(JSON.stringify(manifestBase));manifest.profile='e2-editor-v32';
  if(withActions)for(const [name,id] of Object.entries(TOGGLES))manifest.editorContract.actions[name]={id,gestures:['collapsed','range-single','range-cross'],limits:[]};
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
  return{send,context};
}
function project(src){
  const s=sandbox(src,true);
  return vm.runInContext('productEditorState({format:{bold:true,listBullet:true,listNumber:false,paragraphStyle:"Heading 2"}}).format',s.context);
}
async function exercise(src){
  const s=sandbox(src,true);
  for(const [name,id] of Object.entries(TOGGLES)){
    const {call}=await s.send(name);
    assert.ok(call,name+' did not reach the engine');
    assert.equal(call.args[3],id,name+' wire id');
    assert.deepEqual([call.args[4],call.args[5]],[0,0],name+' flags');
    assert.equal((await s.send(name,{extendSelection:true})).reply?.error?.code,'INVALID_ARGUMENT',name+' took extendSelection');
    assert.equal((await s.send(name,{enabled:true})).reply?.error?.code,'INVALID_ARGUMENT',name+' took enabled');
  }
  assert.ok((await s.send('set-align-center')).call,'v31 alignment stopped reaching the engine');
  const old=sandbox(src,false);
  const {call,reply}=await old.send('toggle-list-ordered');
  assert.equal(call,undefined,'a manifest without the action reached the engine');
  assert.equal(reply?.error?.code,'UNSUPPORTED_OPERATION');
  const format=project(src);
  assert.deepEqual([format.listBullet,format.listNumber,format.paragraphStyle],[true,false,'Heading 2'],'the projection dropped a field');
}
(async()=>{
  await exercise(source);
  const controls={
    'old lookup':source.replace('const actionId = EDITOR_V6_ACTION_IDS[payload.action];','const actionId = EDITOR_V5_ACTION_IDS[payload.action];'),
    'wrong id':source.replace('"toggle-list-ordered": 33','"toggle-list-ordered": 34'),
    'projection drops listBullet':source.replace('listBullet: typeof value.format?.listBullet === "boolean"\n        ? value.format.listBullet : null,\n',''),
    'projection drops paragraphStyle':source.replace('paragraphStyle: typeof value.format?.paragraphStyle === "string"\n        ? value.format.paragraphStyle : null,\n',''),
  };
  for(const [name,mutated] of Object.entries(controls)){
    assert.notEqual(mutated,source,name+': control did not apply');
    await assert.rejects(exercise(mutated),undefined,name+': control stayed green');
  }
  console.log('v32 worker holds; '+Object.keys(controls).length+' controls red');
})().catch(e=>{console.error(e);process.exit(1);});
