// SPEC-M3-link-batch-v25 6.1 W2 on the real v25 worker source in a vm sandbox (the
// shape of v24_feature_worker_test.cjs): finding 171's `dispatched` (engine boolean
// first, stage fallback for engines that do not send it) and finding 172's `witness`
// (known set forwarded, anything else null).  The causal controls remove each change
// in turn and require the exercise to fail.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.join(__dirname,'..');
const base=fs.readFileSync(path.join(root,'build/archive/e2-editor-v24-27615808-worker-41041fe7/sdk-worker.js'));
assert.equal(crypto.createHash('sha256').update(base).digest('hex'),'41041fe746b2355a1768bc774a10ac59802a8e359579618be405e3696f3b9461');
const original=fs.readFileSync(path.join(root,'sdk/v25-feature-worker.js'),'utf8');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'build/archive/e2-editor-v24-27615808-worker-41041fe7/sdk-manifest.json')));
manifest.profile='e2-editor-v25';

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
 return {request,response,engine};
}

function action(s){return s.request('editorActionV2',{documentHandle:1,expectedRevision:1,action:'set-bold',enabled:false});}

async function exercise(source){
 const s=sandbox(source);
 // 171: the engine's boolean wins over the stage; a missing boolean falls back.
 const barrier=(extra)=>({failureShape:'multi-block-readback',route:'collapsed',...extra});
 for(const [extra,expected,label] of [
  [{stage:'idle',dispatched:true},true,'ordered engine: posted, stage idle'],
  [{stage:'awaiting-result',dispatched:false},false,'engine says not posted'],
  [{stage:'awaiting-result'},true,'legacy engine: stage only'],
  [{stage:'idle'},false,'legacy refusal: stage only'],
 ]){
  const requestId=action(s);
  s.engine({type:'error',requestId,code:'MUTATION_OUTCOME_UNKNOWN',message:'m',operation:'editor-action',formatBarrier:barrier(extra)});
  assert.equal(s.response(requestId)?.error?.formatBarrier?.dispatched,expected,label);
 }
 // 172: a known witness is forwarded, anything else is null.
 for(const [witness,expected] of [['state-noop','state-noop'],['on-time-item','on-time-item'],['uno-success','uno-success'],
                                  ['made-up',null],[undefined,null],[7,null]]){
  const requestId=action(s);
  s.engine({type:'editor-action-completed',requestId,action:'set-bold',option:false,beforeRevision:1,revision:2,changed:true,
            completion:'uno-command-result',witness,callbackSequenceBefore:1,callbackSequenceAfter:2,state:{}});
  assert.equal(s.response(requestId)?.result?.witness,expected,String(witness));
 }
}

(async()=>{
 await exercise(original);
 const controls=[
  ['dispatched: typeof value.dispatched === "boolean" ? value.dispatched\n      : typeof value.stage === "string" && value.stage !== "idle",',
   'dispatched: typeof value.stage === "string" && value.stage !== "idle",'],
  ['witness: FORMAT_WITNESSES.has(event.witness) ? event.witness : null,','witness: event.witness,'],
  ['witness: FORMAT_WITNESSES.has(event.witness) ? event.witness : null,',''],
 ];
 for(const [before,after] of controls){
  assert(original.includes(before),before);
  await assert.rejects(exercise(original.replace(before,after)),undefined,'control did not turn red: '+before);
 }
 console.log('v25 worker: dispatched (engine first, stage fallback), witness projection and '+controls.length+' causal controls pass');
})().catch(e=>{console.error(e);process.exit(1);});
