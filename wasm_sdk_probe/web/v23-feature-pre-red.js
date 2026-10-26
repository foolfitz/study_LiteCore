// Observation-only entry around the pinned v57 product page; no SDK overrides.
import {NarrowEditorV2Session} from './editor-shell-v2/narrow-editor-v2-session.js';
const result = window.__featurePreRed = {schema:1, profile:'e2-editor-v19',
  caseId:new URLSearchParams(location.search).get('caseId'), userAgent:navigator.userAgent,
  requests:[],responses:[],events:[],cancels:[],workers:[],inputs:[],calls:[],opens:[],complete:false};
const bytes64 = bytes => {let s=''; const b=new Uint8Array(bytes);
  for(let i=0;i<b.length;i+=8192)s+=String.fromCharCode(...b.subarray(i,i+8192));return btoa(s);};
const hash = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
  .map(x=>x.toString(16).padStart(2,'0')).join('');
const snap = value => {
  if(value instanceof ArrayBuffer)return {encoding:'base64',bytes:value.byteLength,data:bytes64(value)};
  if(ArrayBuffer.isView(value))return snap(value.buffer.slice(value.byteOffset,value.byteOffset+value.byteLength));
  if(Array.isArray(value))return value.map(snap);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,snap(v)]));
  return value;
};
let generation=0,current,config;
const NativeWorker=window.Worker;
window.Worker=class extends NativeWorker {
  constructor(url,options){super(url,options);this.observedGeneration=++generation;
    const gen=this.observedGeneration;this.observedRecord={generation:gen,url:String(url),createdAt:performance.now()};
    result.workers.push(this.observedRecord);
    this.addEventListener('message',event=>{const item={generation:gen,at:performance.now(),message:snap(event.data)};
      if(event.data?.kind==='response')result.responses.push(item);
      if(event.data?.kind==='event')result.events.push(item);});}
  postMessage(message,...args){const item={generation:this.observedGeneration,at:performance.now(),message:snap(message)};
    if(message?.kind==='request')result.requests.push(item);
    if(message?.kind==='cancel')result.cancels.push(item);
    return super.postMessage(message,...args);}
  terminate(){this.observedRecord.terminatedAt=performance.now();return super.terminate();}
};
const openOriginal=NarrowEditorV2Session.prototype.open;
NarrowEditorV2Session.prototype.open=async function(input,...args){
  const record={serial:result.opens.length+1,name:input.name,fixtureSha256:await hash(input.bytes),startedAt:performance.now()};
  result.opens.push(record);current=this;
  const value=await openOriginal.call(this,input,...args);
  Object.assign(record,{finishedAt:performance.now(),generation,documentHandle:this.document.handle});
  result.currentOpen=record;return value;
};
const sinkSnapshot=()=>{const el=document.querySelector('#sink');return {id:el?.id,
  active:document.activeElement===el,disabled:el?.disabled,readOnly:el?.readOnly,connected:el?.isConnected,
  documentHandle:current?.document?.handle,generation};};
for(const type of ['keydown','keyup','beforeinput','input'])document.addEventListener(type,event=>{
  if(event.target?.id==='sink')result.inputs.push({type,at:performance.now(),isTrusted:event.isTrusted,
    key:event.key,code:event.code,repeat:event.repeat,inputType:event.inputType,data:event.data,sink:sinkSnapshot()});
},true);
async function call(name,fn){const entry={name,generation,documentHandle:current?.document?.handle,startedAt:performance.now()};
  result.calls.push(entry);try{const value=await fn();entry.result=snap(value);entry.ok=true;return value;}
  catch(error){entry.ok=false;entry.error={code:error?.code,message:String(error?.message||error)};throw error;}
  finally{entry.finishedAt=performance.now();}}
const state=name=>call(name,()=>current.editor.getState());
const move=(direction,name)=>call(name,()=>current.editor.action('move-'+direction));
const point=caret=>({xTwips:caret.x,yTwips:caret.y+Math.floor(caret.height/2)});
async function save(name){const saved=await call(name,()=>current.save());
  return {base64:bytes64(saved.bytes),sha256:await hash(saved.bytes)};}
async function place(p,name){return call(name,()=>current.placeCaret(p.xTwips,p.yTwips));}
async function locate(plan,prefix){
  const found=await call(prefix+'-search',()=>current.document.search(plan.query));
  let coords=String(found?.selections?.[0]?.rectangles||'').split(';')[0].split(',').map(Number);
  const firstLine=plan.anchor==='search-first-displayed-line';
  if(firstLine){
    // Full-paragraph search may return the last visual line first. This Writer
    // setup can address part0 only; multiple matches/parts are ambiguous.
    const selections=found?.selections;
    if(!Array.isArray(selections)||selections.length!==1||![0,'0'].includes(selections[0].part)
      ||typeof selections[0].rectangles!=='string')throw new Error('ambiguous wrap search match or part');
    const rectangles=selections[0].rectangles.split(';').map(raw=>{
      if(!/^\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*$/.test(raw))throw new Error('malformed wrap search rectangle');
      const r=raw.split(',').map(Number);
      if(!r.every(Number.isSafeInteger)||r[2]<=0||r[3]<=0)throw new Error('invalid wrap search rectangle');
      return r;
    });
    if(new Set(rectangles.map(r=>`${r[0]},${r[1]}`)).size!==rectangles.length)
      throw new Error('ambiguous wrap search rectangle origin');
    coords=rectangles.sort((a,b)=>a[1]-b[1]||a[0]-b[0])[0];
  }
  if(coords.length!==4||!coords.every(Number.isFinite))throw new Error('actual search rectangle missing');
  await place({xTwips:coords[0],yTwips:coords[1]+Math.floor(coords[3]/2)},prefix+'-search-click');
  // List Home enters the label position; native p7.5 counts from text start.
  if(plan.anchor!=='search-text-start')await move('line-home',prefix+'-home');
  const start=await state(prefix+'-start-state');
  if(typeof plan.offset==='number')for(let n=0;n<plan.offset;n++)await move('character-right',prefix+'-right-'+n);
  else {await move('line-end',prefix+'-end');
    if(plan.offset==='next-empty')await move('character-right',prefix+'-next-empty');}
  const target=await state(prefix+'-target-state');
  const a=point(start.caret),b=point(target.caret);
  await call(prefix+'-prefix-select',()=>current.editor.selectRange(a,b));
  const selected=await call(prefix+'-prefix-text',()=>current.document.getSelection());
  await place(b,prefix+'-restore-point');
  const final=await state(prefix+'-final-state');
  if(firstLine&&(start.caret?.x!==coords[0]||start.caret?.y!==coords[1]
    ||target.caret?.y!==coords[1]||!(target.caret?.x>start.caret.x)
    ||!selected.text||!plan.query.startsWith(selected.text)))throw new Error('wrap first-line witness differs');
  return {plan,start,target,selected,final};
}
function fail(error){result.fatal={code:error?.code,message:String(error?.message||error)};result.complete=true;return false;}
window.__preRedControl={
  async prepareReadiness(){try{
    result.readiness={open:snap(result.currentOpen)};
    result.readiness.setup=await locate({query:config.fixtureParagraphs[0],paragraph:0,offset:0},'readiness');
    result.readiness.beforeState=await state('readiness-before-state');
    result.readiness.beforeSave=await save('readiness-before-save');
    document.querySelector('#sink').focus();result.readiness.beforeInput=sinkSnapshot();
    result.phase='send-readiness-Z';return true;
  }catch(error){return fail(error);}},
  async finishReadiness(){try{
    result.readiness.afterSave=await save('readiness-after-save');
    result.readiness.afterState=await state('readiness-after-state');
    result.phase='readiness-recorded';return true;
  }catch(error){return fail(error);}},
  async measure(){try{
    const plan=config.cases[result.caseId];
    if(!plan||result.currentOpen.serial<=result.readiness.open.serial)throw new Error('fresh measured open absent');
    result.measured={open:snap(result.currentOpen)};
    result.measured.originalSave=await save('measured-original-save');
    result.measured.setup=await locate(plan.discovery,'measured');
    result.measured.before=await state('measured-before-state');
    result.measured.reply=await call('measured-shift',()=>current.editor.moveCharacter(plan.key.toLowerCase(),{extendSelection:true}));
    result.measured.replyAt=performance.now();
    // Observation-only delay from the original S2 criterion, never a completion policy.
    await new Promise(resolve=>setTimeout(resolve,500));
    result.measured.readbackRequestedAt=performance.now();
    result.measured.readback=await state('measured-readback');
    result.measured.activeSelection=await call('measured-active-selection',()=>current.document.getSelection());
    await call('measured-close',()=>current.close());
    result.complete=true;result.phase='complete';return true;
  }catch(error){return fail(error);}}
};
try{
  const configBytes=await (await fetch('./pre-red-config.json',{cache:'no-store'})).arrayBuffer();
  result.configSha256=await hash(configBytes);config=JSON.parse(new TextDecoder().decode(configBytes));
  result.servedSources={};result.artifacts={};
  for(const path of Object.keys(config.servedSources)){
    const response=await fetch('./'+path,{cache:'no-store'});if(!response.ok)throw new Error('source HTTP '+path);
    result.servedSources[path]=await hash(await response.arrayBuffer());}
  for(const path of Object.keys(config.profile.artifacts)){
    const response=await fetch('./profiles/e2-editor-v19/'+path,{cache:'no-store'});if(!response.ok)throw new Error('artifact HTTP '+path);
    result.artifacts[path]=await hash(await response.arrayBuffer());}
  result.fixtureManifestSha256=await hash(await (await fetch('./e1-fixtures/manifest.json',{cache:'no-store'})).arrayBuffer());
  await import('./e2-editor-app.js');result.booted=true;
}catch(error){fail(error);}
