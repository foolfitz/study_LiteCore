// SPEC-P-demo-batch-3 W1, W2 on the real worker source in a vm sandbox: rangeStyle reaches oxsdk_document_cell with the closed
// operation numbers and the value in the payload; every spelling outside the closed list stops at the worker; a profile without the
// capability never reaches for it.  Causal controls remove each change and require the exercise to fail.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.join(__dirname,'..');
const baseFile=path.join(root,'dist/profiles/ods-editor-v2/sdk-worker.js');
const base=fs.readFileSync(baseFile,'utf8');
assert.equal(crypto.createHash('sha256').update(base).digest('hex'),'0bed22bdb979138f1f0c23bd41bc05896e14f69e29fba10d4e42ccbcda5e1de9');
const source=fs.readFileSync(path.join(root,'sdk/ods-editor-v3-worker.js'),'utf8');
const delta=JSON.parse(fs.readFileSync(path.join(root,'tests/ods-v3-worker-delta.json')));
let rebuilt=base;
for(const h of delta.hunks){assert.equal(rebuilt.split(h.old).length-1,1,h.item);rebuilt=rebuilt.replace(h.old,()=>h.new);}
assert.equal(rebuilt,source,'the v3 worker is not the frozen worker plus the closed list');
const manifestBase=JSON.parse(fs.readFileSync(path.join(root,'dist/profiles/ods-editor-v2/sdk-manifest.json')));

function sandbox(src,capabilities){
  const manifest={...manifestBase,profile:'ods-editor-v3',capabilities};
  const messages=[],calls=[];let receive;
  const heap=new Uint8Array(4096);
  const context=vm.createContext({TextEncoder,console,self:{addEventListener:(_,fn)=>receive=fn,postMessage:m=>messages.push(m)}});
  vm.runInContext(src,context);
  context.fake=(name,ret,types,args)=>{calls.push({name,args});
    if(name==='oxsdk_abi_version')return 0x00010001;if(name==='oxsdk_buffer_alloc')return 16;return 0;};
  context.manifest=manifest;context.instance={ccall:context.fake,HEAPU8:heap};
  vm.runInContext('moduleInstance=instance;activeManifest=manifest;loadManifest=async()=>manifest;ensureModule=async()=>{};loadStartupResourcePacks=async()=>{};',context);
  let id=1;
  const send=async(operation,payload)=>{const requestId=id++;const before=calls.length;
    receive({data:{protocolVersion:1,kind:'request',requestId,operation,payload}});
    await new Promise(r=>setTimeout(r,0));
    const reply=messages.filter(m=>m.kind==='response'&&m.requestId===requestId).at(-1);
    const call=calls.slice(before).find(c=>c.name==='oxsdk_document_cell');
    return{reply,call,text:call?new TextDecoder().decode(heap.slice(16,16+call.args[8])):null};};
  return{send};
}
const P={documentHandle:1,expectedRevision:3,part:0,column:1,row:2,endColumn:3,endRow:4};
const CAP=[...manifestBase.capabilities,'cell-range-styling'];

async function exercise(src){
  const s=sandbox(src,CAP);
  for(const [style,value,operation] of [['textColor','#c00000',10],['textColor','auto',10],['backColor','#ffe599',11],['backColor','none',11],
      ['horizontalAlign','center',12],['horizontalAlign','standard',12],['horizontalAlign','block',12]]){
    const {call,text}=await s.send('rangeStyle',{...P,style,value});
    assert.ok(call,`${style} ${value} did not reach the engine`);
    assert.equal(call.args[6],operation);
    assert.deepEqual(JSON.parse(text),{endColumn:3,endRow:4,value});
  }
  for(const [style,value] of [['textColor','red'],['textColor','#C00000'],['textColor','none'],['textColor',16711680],['backColor','auto'],
      ['backColor','#fff'],['horizontalAlign','repeat'],['horizontalAlign',''],['font','#000000'],['textColor',undefined]]){
    const {call}=await s.send('rangeStyle',{...P,style,value});
    assert.equal(call,undefined,`${style}=${value} reached the engine`);
  }
  const {call:format}=await s.send('rangeFormat',{...P,format:'bold',enabled:true});
  assert.equal(format.args[6],7,'rangeFormat kept its number');
  const old=sandbox(src,manifestBase.capabilities);
  const {call,reply}=await old.send('rangeStyle',{...P,style:'textColor',value:'#000000'});
  assert.equal(call,undefined,'a profile without the capability reached for it');
  assert.equal(reply.ok,false);
}
(async()=>{
  await exercise(source);
  const controls={
    'no closed values':[source.replace('!styleValueIsClosed(payload.style, payload.value)','false')],
    'no operation number':[source.replace('request.operation === "rangeStyle" ? styles[payload.style]','false ? 0')],
    'no capability row':[source.replace('  ["rangeStyle", "cell-range-styling"],\n','')],
    'no value in the payload':[source.replace('endRow:payload.endRow,value:payload.value}','endRow:payload.endRow}')],
  };
  for(const [name,[mutated]] of Object.entries(controls)){
    assert.notEqual(mutated,source,name+': control did not apply');
    await assert.rejects(exercise(mutated),undefined,name+': control stayed green');
  }
  console.log('ods-v3 worker holds; '+Object.keys(controls).length+' controls red');
})().catch(e=>{console.error(e);process.exit(1);});
