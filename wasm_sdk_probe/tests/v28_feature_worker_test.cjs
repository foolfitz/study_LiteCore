// SPEC-M3-v28-last-line-fallback 7.2 W2 on the real v28 worker source in a vm sandbox (the shape of
// v27_feature_worker_test.cjs): the `fallback` projection inside `formatBarrier` --
// {ran, selectionType, blockCount, lastListTag, lastBlockTag, refusal, restoreConfirmed}, never the markup,
// null when absent, null per field of the wrong type, last in the object so the F3 runner's
// WORKER_BARRIER_ANCHOR still matches -- and the profile term.  The causal controls remove each change in
// turn and require the exercise to fail.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.join(__dirname,'..');
const archive='build/archive/e2-editor-v27-c089dfd6-worker-8152448a';
const base=fs.readFileSync(path.join(root,archive,'sdk-worker.js'));
assert.equal(crypto.createHash('sha256').update(base).digest('hex'),'8152448ab83bc323edfa6982a1db08c4367b15b4c99978eeb1b39b3ef41a669d');
const original=fs.readFileSync(path.join(root,'sdk/v28-last-block-worker.js'),'utf8');
const manifest=JSON.parse(fs.readFileSync(path.join(root,archive,'sdk-manifest.json')));
manifest.profile='e2-editor-v28';
const ANCHOR='function productFormatBarrier(value = {}) {\n  return {\n';  // run_e2_c_product_path.py:287

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
const RECORD={ran:true,command:'.uno:CharLeftSel',resultSeen:true,selectionType:1,readable:true,readbackBytes:577,
              readback:{parsed:true,lastListTag:'',lastBlockTag:'p',blockCount:2,itemCount:1},
              readbackHtml:'<html><body><p>secret</p></body></html>',refusal:'unknown-structural-tag'};

async function exercise(source){
 assert.equal(source.split(ANCHOR).length-1,1,'WORKER_BARRIER_ANCHOR must occur exactly once');
 const s=sandbox(source);
 assert.equal(s.extendPermitted(),true,'line extension stays permitted under e2-editor-v28');
 for(const [fallback,restoreConfirmed,expected,label] of [
  [RECORD,true,{ran:true,selectionType:1,blockCount:2,lastListTag:'',lastBlockTag:'p',refusal:'unknown-structural-tag',restoreConfirmed:true},'a full record, markup dropped'],
  [undefined,true,null,'absent'],
  [{ran:false},false,{ran:false,selectionType:null,blockCount:null,lastListTag:null,lastBlockTag:null,refusal:null,restoreConfirmed:false},'not run'],
  [{ran:'yes',selectionType:1.5,readback:{blockCount:-1,lastListTag:3,lastBlockTag:null},refusal:7},'no',
   {ran:null,selectionType:null,blockCount:null,lastListTag:null,lastBlockTag:null,refusal:null,restoreConfirmed:null},'wrong types'],
  [[1,2],true,null,'an array is not a record'],
 ]){
  const requestId=action(s);
  s.engine({type:'error',requestId,code:'MUTATION_OUTCOME_UNKNOWN',message:'m',operation:'editor-action',
            formatBarrier:{failureShape:'fallback-readback-refused',route:'collapsed',dispatched:true,fallback,
                           readback:{restoreConfirmed}}});
  const projected=s.response(requestId)?.error?.formatBarrier;
  assert.ok(projected,label+': no projected formatBarrier');
  assert.deepEqual(projected.fallback===null?null:{...projected.fallback},expected,label);
  assert.ok(!projected.fallback||!('readbackHtml' in projected.fallback),label+': the markup was projected');
  assert.ok(!JSON.stringify(projected).includes('secret'),label+': document text leaked');
  const keys=Object.keys(projected);
  assert.equal(keys.at(-1),'fallback',label+': fallback is not the last field');
 }
 const requestId=action(s);
 s.engine({type:'error',requestId,code:'MUTATION_OUTCOME_UNKNOWN',message:'m',operation:'editor-action',
           fallback:RECORD,formatBarrier:{failureShape:'fallback-readback-refused',route:'collapsed',dispatched:true}});
 assert.equal(s.response(requestId)?.error?.formatBarrier?.fallback,null,'a top-level fallback leaked into the projection');
}

(async()=>{
 await exercise(original);
 const move=original.replace('    fallback: productFormatFallback(value.fallback, value.readback),\n','')
                   .replace(ANCHOR,ANCHOR+'    fallback: productFormatFallback(value.fallback, value.readback),\n');
 const controls=[
  ['  return activeManifest?.profile === "e2-editor-v28"','  return activeManifest?.profile === "e2-editor-v27"'],
  ['    fallback: productFormatFallback(value.fallback, value.readback),\n',''],
  ['    refusal: text(value.refusal),\n','    refusal: text(value.refusal),\n    readbackHtml: value.readbackHtml,\n'],
  ['    ran: flag(value.ran),','    ran: value.ran,'],
 ];
 for(const [before,after] of controls){
  assert(original.includes(before),before);
  await assert.rejects(exercise(original.replace(before,after)),undefined,'control did not turn red: '+before);
 }
 await assert.rejects(exercise(move),undefined,'control did not turn red: fallback moved to the front');
 console.log('v28 worker: fallback projection (no markup, typed fields, absent -> null, last field) and the profile term, '+(controls.length+1)+' causal controls pass');
})().catch(e=>{console.error(e);process.exit(1);});
