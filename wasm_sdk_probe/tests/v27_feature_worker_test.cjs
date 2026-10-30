// SPEC-M3-v27-finding-176 7.2 W2 on the real v27 worker source in a vm sandbox (the shape of
// v25_feature_worker_test.cjs): finding 176's `undo` projection inside `formatBarrier` --
// {read, changed, actionsBefore, actionsAfter}, never `top`, null when absent, null per field
// of the wrong type -- and the profile term that keeps line extension alive.  The causal
// controls remove each change in turn and require the exercise to fail.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.join(__dirname,'..');
const archive='build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae';
const base=fs.readFileSync(path.join(root,archive,'sdk-worker.js'));
assert.equal(crypto.createHash('sha256').update(base).digest('hex'),'95d6e7ae375e60ef58de3e1bbeb838f0d4922a0d4737287b262c23f595aed964');
const original=fs.readFileSync(path.join(root,'sdk/v27-first-block-worker.js'),'utf8');
const manifest=JSON.parse(fs.readFileSync(path.join(root,archive,'sdk-manifest.json')));
manifest.profile='e2-editor-v27';

function sandbox(source){
 const messages=[];let receive;
 const context=vm.createContext({TextEncoder,console,self:{addEventListener:(_,fn)=>receive=fn,postMessage:m=>messages.push(m)}});
 vm.runInContext(source,context);
 context.fake=(...args)=>{if(args[0]==='oxsdk_abi_version')return 0x00010001;if(args[0]==='oxsdk_editor_abi_version')return 6;if(args[0]==='oxsdk_buffer_alloc')return 16;return 0;};
 context.manifest=manifest;context.instance={ccall:context.fake,HEAPU8:new Uint8Array(1024)};
 vm.runInContext('moduleInstance=instance;activeManifest=manifest;loadManifest=async()=>manifest;ensureModule=async()=>{};loadStartupResourcePacks=async()=>{};',context);
 let id=1;
 const request=(operation,payload)=>{const requestId=id++;receive({data:{protocolVersion:1,kind:'request',requestId,operation,payload}});return requestId;};
 const response=requestId=>messages.filter(m=>m.kind==='response'&&m.requestId===requestId).at(-1);
 const engine=event=>{context.event=event;vm.runInContext('handleCEvent(JSON.stringify(event))',context);};
 const extendPermitted=()=>vm.runInContext('[...EDITOR_V23_EXTEND_ACTIONS].length>0&&[...EDITOR_V23_EXTEND_ACTIONS].every(a=>featureExtendPermitted(a))',context);
 return {request,response,engine,extendPermitted};
}

function action(s){return s.request('editorActionV2',{documentHandle:1,expectedRevision:1,action:'set-list-unordered'});}
const RECORD={read:true,changed:true,actionsBefore:0,actionsAfter:1,top:'Number On/Off'};

async function exercise(source){
 const s=sandbox(source);
 assert.equal(s.extendPermitted(),true,'line extension stays permitted under e2-editor-v27');
 for(const [undo,expected,label] of [
  [RECORD,{read:true,changed:true,actionsBefore:0,actionsAfter:1},'a full record, top dropped'],
  [undefined,null,'absent'],
  [{read:false},{read:false,changed:null,actionsBefore:null,actionsAfter:null},'not read'],
  [{read:'yes',changed:1,actionsBefore:-1,actionsAfter:2.5,top:7},{read:null,changed:null,actionsBefore:null,actionsAfter:null},'wrong types'],
  [[1,2],null,'an array is not a record'],
 ]){
  const requestId=action(s);
  s.engine({type:'error',requestId,code:'EDITOR_FORMAT_POSTCONDITION_FAILED',message:'m',operation:'editor-action',
            formatBarrier:{failureShape:'postcondition-not-met',route:'collapsed',dispatched:true,undo}});
  const projected=s.response(requestId)?.error?.formatBarrier;
  assert.ok(projected,label+': no projected formatBarrier');
  assert.deepEqual(projected.undo===null?null:{...projected.undo},expected,label);
  assert.ok(!projected.undo||!('top' in projected.undo),label+': top was projected');
 }
 // A top-level `undo` (the keyUndo shape) is not the engine's place for it, and is not read as one.
 const requestId=action(s);
 s.engine({type:'error',requestId,code:'EDITOR_FORMAT_POSTCONDITION_FAILED',message:'m',operation:'editor-action',
           undo:RECORD,formatBarrier:{failureShape:'postcondition-not-met',route:'collapsed',dispatched:true}});
 assert.equal(s.response(requestId)?.error?.formatBarrier?.undo,null,'a top-level undo leaked into the projection');
}

(async()=>{
 await exercise(original);
 const controls=[
  ['  return activeManifest?.profile === "e2-editor-v27"','  return activeManifest?.profile === "e2-editor-v26"'],
  ['    undo: productFormatUndo(value.undo),\n',''],
  ['    actionsAfter: count(value.actionsAfter),\n','    actionsAfter: count(value.actionsAfter),\n    top: value.top,\n'],
  ['    read: typeof value.read === "boolean" ? value.read : null,','    read: value.read,'],
 ];
 for(const [before,after] of controls){
  assert(original.includes(before),before);
  await assert.rejects(exercise(original.replace(before,after)),undefined,'control did not turn red: '+before);
 }
 console.log('v27 worker: undo projection (no top, typed fields, absent -> null) and the profile term, '+controls.length+' causal controls pass');
})().catch(e=>{console.error(e);process.exit(1);});
