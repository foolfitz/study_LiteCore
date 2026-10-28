// SPEC-M3-link-batch-v24 6.1 W2, (d'), (viii) and the init presence check of
// fable ruling 2, on the real v24 worker source in a vm sandbox (the shape of
// v23_feature_worker_test.cjs).  The causal controls at the end remove each
// guard in turn and require the exercise to fail: a guard nothing turns red
// without is not tested.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.join(__dirname,'..');
const base=fs.readFileSync(path.join(root,'build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/sdk-worker.js'));
assert.equal(crypto.createHash('sha256').update(base).digest('hex'),'3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5');
const original=fs.readFileSync(path.join(root,'sdk/v24-feature-worker.js'),'utf8');
const v23=JSON.parse(fs.readFileSync(path.join(root,'dist/profiles/e2-editor-v23/sdk-manifest.json')));
const DECLARATION='document-sdk-insert-typed-text';
const MOVES=['move-character-left','move-character-right','move-line-up','move-line-down','move-line-home','move-line-end'];
function v24Manifest(){const m=structuredClone(v23);m.profile='e2-editor-v24';m.editorContract.typedInsert=DECLARATION;return m;}

function sandbox(source,manifest,symbols){
 const messages=[],calls=[];let receive;
 const context=vm.createContext({TextEncoder,console,self:{addEventListener:(_,fn)=>receive=fn,postMessage:m=>messages.push(m)}});
 vm.runInContext(source,context);
 context.fake=(...args)=>{calls.push(args);if(args[0]==='oxsdk_abi_version')return 0x00010001;if(args[0]==='oxsdk_editor_abi_version')return 6;if(args[0]==='oxsdk_buffer_alloc')return 16;return 0;};
 context.manifest=manifest;context.instance={ccall:context.fake,HEAPU8:new Uint8Array(1024)};
 for(const s of symbols)context.instance['_'+s]=()=>0;
 vm.runInContext('moduleInstance=instance;activeManifest=manifest;loadManifest=async()=>manifest;ensureModule=async()=>{};loadStartupResourcePacks=async()=>{};',context);
 let id=1;
 const request=(operation,payload)=>{const requestId=id++;receive({data:{protocolVersion:1,kind:'request',requestId,operation,payload}});return requestId;};
 const response=requestId=>messages.filter(m=>m.kind==='response'&&m.requestId===requestId).at(-1);
 return {messages,calls,request,response,context};
}

function insert(s,route){
 const before=s.calls.length;
 const payload={documentHandle:1,text:'x'};if(route!==undefined)payload.route=route;
 const requestId=s.request('insertText',payload);
 const symbols=s.calls.slice(before).map(c=>c[0]).filter(n=>n.startsWith('oxsdk_document_'));
 return {symbols,response:s.response(requestId)};
}

async function exercise(source){
 // W2: each route calls its export; an unknown one calls nothing.
 const all=['oxsdk_document_insert_text','oxsdk_document_insert_typed_text','oxsdk_document_page_rectangles','oxsdk_document_paste_markdown'];
 let s=sandbox(source,v24Manifest(),all);
 assert.deepEqual(insert(s,'uno-insert-text').symbols,['oxsdk_document_insert_typed_text']);
 assert.deepEqual(insert(s,'paste').symbols,['oxsdk_document_insert_text']);
 assert.deepEqual(insert(s,undefined).symbols,['oxsdk_document_insert_text']);
 for(const bogus of ['typed','UNO-INSERT-TEXT','',null,1]){
  const r=insert(s,bogus);assert.deepEqual(r.symbols,[],String(bogus));
  assert.equal(r.response?.error?.code,'INVALID_ARGUMENT',String(bogus));assert.equal(r.response.error.dispatched,false);
 }
 // (d'): a leafless manifest refuses the typed route before any symbol.
 const leafless=v24Manifest();delete leafless.editorContract.typedInsert;
 s=sandbox(source,leafless,all);
 let r=insert(s,'uno-insert-text');assert.deepEqual(r.symbols,[]);assert.equal(r.response?.error?.code,'UNSUPPORTED_OPERATION');
 assert.deepEqual(insert(s,undefined).symbols,['oxsdk_document_insert_text'],'a leafless manifest still pastes');
 // (viii) = ruling 2 (e): the profile term is live.
 for(const [profile,expected] of [['e2-editor-v24',true],['e2-editor-v23',false]]){
  const m=v24Manifest();m.profile=profile;
  for(const name of MOVES)m.editorContract.actions[name].gestures=['collapsed','range-single','range-cross'];
  s=sandbox(source,m,all);
  // Character moves accepted extend before ABI6; the profile term gates the
  // four line moves (v23_feature_worker_test.cjs checks the same set).
  for(const name of expected?MOVES:MOVES.filter(n=>n.startsWith('move-line-'))){
   const before=s.calls.length;
   s.request('editorActionV2',{documentHandle:1,expectedRevision:0xffffffff,action:name,extendSelection:true,enabled:false});
   assert.equal(s.calls.length>before,expected,profile+' '+name);
  }
 }
 // Init presence check (ruling 2 (c), sandbox half): declared but absent is
 // refused by name; present passes that point; undeclared and absent passes.
 const init=async (manifest,symbols)=>{const t=sandbox(source,manifest,symbols);const requestId=t.request('init',{requestedAbiVersion:0x00010001});await new Promise(r=>setTimeout(r,0));await new Promise(r=>setTimeout(r,0));return t.messages.filter(m=>m.requestId===requestId);};
 const withoutTyped=all.filter(n=>n!=='oxsdk_document_insert_typed_text');
 let out=await init(v24Manifest(),withoutTyped);
 assert.equal(out.at(-1)?.error?.code,'DECLARED_EXPORT_MISSING');assert.match(out.at(-1).error.message,/oxsdk_document_insert_typed_text/);
 out=await init(v24Manifest(),all);assert(!out.some(m=>m.error?.code==='DECLARED_EXPORT_MISSING'),'present export refused');
 out=await init(leafless,withoutTyped);assert(!out.some(m=>m.error?.code==='DECLARED_EXPORT_MISSING'),'undeclared export required');
 // The typed reply's proof reaches the response; a paste reply keeps its v23 shape.
 s=sandbox(source,v24Manifest(),all);
 let requestId=s.request('insertText',{documentHandle:1,text:'x',route:'uno-insert-text'});
 s.context.event={type:'inserted',requestId,method:'uno-insert-text',completion:'uno-command-result',resultPayload:'{"commandName":".uno:InsertText"}',revision:2};
 vm.runInContext('handleCEvent(JSON.stringify(event))',s.context);
 assert.deepEqual({...s.response(requestId).result},{method:'uno-insert-text',revision:2,completion:'uno-command-result',resultPayload:'{"commandName":".uno:InsertText"}'});
 requestId=s.request('insertText',{documentHandle:1,text:'x',route:'paste'});
 s.context.event={type:'inserted',requestId,method:'paste',revision:3};
 vm.runInContext('handleCEvent(JSON.stringify(event))',s.context);
 assert.deepEqual(Object.keys(s.response(requestId).result),['method','revision']);
}

(async()=>{
 await exercise(original);
 const controls=[
  ['payload.route === "uno-insert-text"\n            ? "oxsdk_document_insert_typed_text" : "oxsdk_document_insert_text"','"oxsdk_document_insert_text"'],
  ['if (payload.route !== undefined && !INSERT_ROUTES.has(payload.route)) {','if (false) {'],
  ['if (!documentExportDeclared(exportOperation(request))) {','if (!documentExportDeclared(request.operation)) {'],
  ['&& typeof moduleInstance?.["_" + spec.symbol] !== "function") {','&& false) {'],
  ['return activeManifest?.profile === "e2-editor-v24"','return activeManifest?.profile === "e2-editor-v23"'],
  ['...(event.completion === undefined ? {} : {','...(true ? {} : {'],
 ];
 for(const [before,after] of controls){
  assert(original.includes(before),before);
  await assert.rejects(exercise(original.replace(before,after)),undefined,'control did not turn red: '+before);
 }
 console.log('v24 worker: routes, unknown route, leafless (d\'), profile term (viii), init presence, reply projection and '+controls.length+' causal controls pass');
})().catch(e=>{console.error(e);process.exit(1);});
