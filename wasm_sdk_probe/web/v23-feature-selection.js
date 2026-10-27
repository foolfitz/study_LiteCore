// Observation-only entry around the frozen v76 product page; no SDK overrides.
import {NarrowEditorV2Session} from './editor-shell-v2/narrow-editor-v2-session.js';
const result = window.__featureSelection = {schema:1, profile:'e2-editor-v23',
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
// Paint bitmaps (one 900x1153 RGBA page each) were 99.8% of a cell and no reader
// predicate reads them; selection-prep-04's shift-Up@doc-end overflowed a single
// JSON string. Keep each bitmap's length and SHA-256, not its bytes.
const paintIds=new Set(),pending=window.__featureSelectionPending=[];
function paintResponse(data){
  const pixels=data?.result?.pixels;
  if(!(pixels instanceof ArrayBuffer||ArrayBuffer.isView(pixels)))return snap(data);
  const copy=(ArrayBuffer.isView(pixels)?new Uint8Array(pixels.buffer,pixels.byteOffset,pixels.byteLength):new Uint8Array(pixels)).slice();
  const message=snap({...data,result:{...data.result,pixels:undefined}});
  message.result.pixels={encoding:'sha256',bytes:copy.byteLength,sha256:null};
  pending.push(hash(copy).then(h=>{message.result.pixels.sha256=h;}));
  return message;
}
let generation=0,current,config;
const NativeWorker=window.Worker;
window.Worker=class extends NativeWorker {
  constructor(url,options){super(url,options);this.observedGeneration=++generation;
    const gen=this.observedGeneration;this.observedRecord={generation:gen,url:String(url),createdAt:performance.now()};
    result.workers.push(this.observedRecord);
    this.addEventListener('message',event=>{const paint=event.data?.kind==='response'&&paintIds.delete(gen+':'+event.data.requestId);
      const item={generation:gen,at:performance.now(),message:paint?paintResponse(event.data):snap(event.data)};
      if(event.data?.kind==='response')result.responses.push(item);
      if(event.data?.kind==='event')result.events.push(item);});}
  postMessage(message,...args){const item={generation:this.observedGeneration,at:performance.now(),message:snap(message)};
    if(message?.kind==='request')result.requests.push(item);
    if(message?.kind==='request'&&message.operation==='paint')paintIds.add(this.observedGeneration+':'+message.requestId);
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
    key:event.key,code:event.code,repeat:event.repeat,shiftKey:event.shiftKey,ctrlKey:event.ctrlKey,altKey:event.altKey,metaKey:event.metaKey,inputType:event.inputType,data:event.data,sink:sinkSnapshot()});
},true);
async function call(name,fn){const entry={name,generation,documentHandle:current?.document?.handle,startedAt:performance.now(),requestStart:result.requests.length};
  result.calls.push(entry);try{const value=await fn();entry.result=snap(value);entry.ok=true;return value;}
  catch(error){entry.ok=false;entry.error={code:error?.code,message:String(error?.message||error)};throw error;}
  finally{entry.requestEnd=result.requests.length;entry.finishedAt=performance.now();}}
const state=name=>call(name,()=>current.editor.getState());
const move=(direction,name)=>call(name,()=>current.editor.action('move-'+direction));
const point=caret=>({xTwips:caret.x,yTwips:caret.y+Math.floor(caret.height/2)});
async function save(name){const saved=await call(name,()=>current.save());
  return {base64:bytes64(saved.bytes),sha256:await hash(saved.bytes)};}
async function place(p,name){return call(name,()=>current.placeCaret(p.xTwips,p.yTwips));}
function rectangles(found){
  const rows=found?.selections;
  if(!Array.isArray(rows)||rows.length!==1||!rows[0]||![0,'0'].includes(rows[0].part)
    ||typeof rows[0].rectangles!=='string')throw new Error('ambiguous search match/part');
  const values=rows[0].rectangles.split(';').map(raw=>{
    if(!/^\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*$/.test(raw))throw new Error('malformed search rectangle');
    const r=raw.split(',').map(Number);if(!r.every(Number.isSafeInteger)||r[2]<=0||r[3]<=0)throw new Error('invalid search rectangle');return r;});
  if(new Set(values.map(r=>`${r[0]},${r[1]}`)).size!==values.length)throw new Error('ambiguous search origin');
  return values.sort((a,b)=>a[1]-b[1]||a[0]-b[0]);
}
async function locate(plan,prefix){
  const found=await call(prefix+'-search',()=>current.document.search(plan.query));
  const boxes=rectangles(found),r=boxes[0];
  await place({xTwips:r[0],yTwips:r[1]+Math.floor(r[3]/2)},prefix+'-search-click');
  if(plan.anchor==='search-first-displayed-line')await move('line-home',prefix+'-home');
  const start=await state(prefix+'-start-state');
  if(start.caret?.x!==r[0]||start.caret?.y!==r[1])throw new Error('actual text start differs');
  if(Number.isInteger(plan.offset))for(let i=0;i<plan.offset;i++)await move('character-right',prefix+'-right-'+i);
  else{await move('line-end',prefix+'-end');if(plan.offset==='next-empty')await move('character-right',prefix+'-next-empty');}
  const target=await state(prefix+'-target-state');
  await call(prefix+'-prefix-select',()=>current.editor.selectRange(point(start.caret),point(target.caret)));
  const selected=await call(prefix+'-prefix-text',()=>current.document.getSelection());
  const expected=plan.prefix;
  if(expected!==undefined&&selected.text!==expected)throw new Error('logical prefix differs');
  if(plan.offset==='visual-end'&&(!selected.text||!plan.query.startsWith(selected.text)||target.caret.y!==r[1]))throw new Error('first visual line differs');
  await place(point(target.caret),prefix+'-restore-point');
  const final=await state(prefix+'-final-state');
  if(JSON.stringify(final.caret)!==JSON.stringify(target.caret))throw new Error('restored caret differs');
  return {plan,boxes,start,target,selected,final};
}
// R1 (PROTOCOL-2026-10-26-v23-r1-inputs): the same point plan the Python plan builds
// (v23_feature_selection_cases.r1_point_plan), offsets in code points.
const codePoints=text=>Array.from(text);
function r1PointPlan(texts,spec,wrap){
  const p=spec.paragraph;if(!(p>=0&&p<texts.length))throw new Error('R1 point outside the fixture');
  const segment=q=>texts[q].split('\u2028')[0],base={name:spec.name,paragraph:p};
  if(spec.kind==='next-empty'){
    if(texts[p]||p===0||!texts[p-1]||texts[p-1].includes('\u2028'))throw new Error('undeclared empty-paragraph traversal');
    return {...base,searchParagraph:p-1,query:texts[p-1],anchor:'search-text-start',offset:'next-empty',
      prefix:texts[p-1]+'\n',requiredWitness:'preceding-paragraph-end-right-empty-caret'};}
  if(!texts[p])throw new Error('an empty paragraph is reached by next-empty only');
  if(spec.kind==='visual-end')return {...base,query:segment(p),anchor:'search-text-start',offset:'visual-end',requiredWitness:'actual-first-line-end'};
  if(spec.kind!=='offset')throw new Error('unknown R1 point kind');
  let offset;
  if(spec.wrapDelta===undefined||spec.wrapDelta===null)offset=spec.offset;
  else if(Number.isInteger(wrap))offset=wrap+spec.wrapDelta;
  else throw new Error('wrap-relative point without a discovered wrap');
  if(!Number.isInteger(offset)||offset<0||offset>codePoints(segment(p)).length)throw new Error('logical offset outside the paragraph line segment');
  return {...base,query:segment(p),anchor:'search-text-start',offset,prefix:codePoints(texts[p]).slice(0,offset).join(''),
    requiredWitness:'actual-text-start-prefix-and-restored-caret'};
}
// The first visual wrap W: a fresh Right walk from the paragraph's text start until the caret's y
// changes, bounded by the paragraph's own length (closed fixture population, no open scan).
async function r1Walk(plan,prefix){
  const found=await call(prefix+'-search',()=>current.document.search(plan.query));
  const boxes=rectangles(found),r=boxes[0];
  await place({xTwips:r[0],yTwips:r[1]+Math.floor(r[3]/2)},prefix+'-search-click');
  const start=await state(prefix+'-start-state');
  if(start.caret?.x!==r[0]||start.caret?.y!==r[1])throw new Error('actual text start differs');
  const steps=[];
  for(let i=1;i<=plan.limit;i++){
    await move('character-right',prefix+'-right-'+i);
    const step=await state(prefix+'-step-'+i);steps.push(step);
    if(step.caret?.y!==start.caret.y)return {plan,boxes,start,steps,wrap:i};
  }
  throw new Error('no visual wrap inside the paragraph');
}
let armed=null,actionPromise=null,keyArm=null;
result.keyArms=[];
// S4: the product's own pointer handler calls placeCaret; when armed, that call is recorded
// like an instrumented one, so its wire window and completion are bound.
let placeArmed=null,placePromise=null;
const originalPlace=NarrowEditorV2Session.prototype.placeCaret;
NarrowEditorV2Session.prototype.placeCaret=function(...args){
  if(!placeArmed)return originalPlace.apply(this,args);
  const name=placeArmed;placeArmed=null;
  placePromise=call(name,()=>originalPlace.apply(this,args));
  return placePromise;
};
const originalAction=NarrowEditorV2Session.prototype.action;
NarrowEditorV2Session.prototype.action=function(action,options){
  if(!armed)return originalAction.call(this,action,options);
  const name=armed;armed=null;
  actionPromise=call(name,()=>originalAction.call(this,action,options));
  return actionPromise;
};
for(const type of ['pointerdown','pointermove','pointerup'])document.addEventListener(type,event=>{
  if(event.target?.closest?.('#paper'))result.inputs.push({type,at:performance.now(),isTrusted:event.isTrusted,
    clientX:event.clientX,clientY:event.clientY,buttons:event.buttons,button:event.button,generation,
    paper:(()=>{const r=document.querySelector('#paper').getBoundingClientRect();return {left:r.left,top:r.top,width:r.width,height:r.height};})(),
    size:{w:current.document.widthTwips,h:current.document.heightTwips}});
},true);
function fail(error){result.fatal={code:error?.code,message:String(error?.message||error)};result.complete=true;return false;}
let phase=null,phaseName=null;
window.__selectionControl={
  async prepareReadiness(){try{
    result.readiness={open:snap(result.currentOpen)};
    result.readiness.setup=await locate(config.readinessPoint,'readiness');
    result.readiness.beforeState=await state('readiness-before-state');
    result.readiness.beforeSave=await save('readiness-before-save');
    document.querySelector('#sink').focus();result.readiness.beforeInput=sinkSnapshot();return true;
  }catch(error){return fail(error);}},
  async finishReadiness(){try{
    result.readiness.afterSave=await save('readiness-after-save');
    result.readiness.afterState=await state('readiness-after-state');return true;
  }catch(error){return fail(error);}},
  // S5: the whole sequence goes through the real product keys with no wait between members;
  // the settled reference arm alone observes the Shift terminal before its continuation.
  armSequence(){phase.sequence={generation,inputStart:result.inputs.length,requestStart:result.requests.length,at:performance.now()};
    document.querySelector('#sink').focus();return true;},
  async settledWitness(){try{
    // Existing S2 observation interval (ruling-3 line 55), only in the reference arm.
    await new Promise(resolve=>setTimeout(resolve,500));
    phase.settledState=await state(phaseName+'-settled-state');
    phase.settledSelection=await call(phaseName+'-settled-text',()=>current.document.getSelection());
    phase.sequence.continuationInputStart=result.inputs.length;document.querySelector('#sink').focus();return true;
  }catch(error){return fail(error);}},
  async finishSequence(){try{
    phase.sequence.inputEnd=result.inputs.length;
    if(typeof current.input?.idle==='function')await current.input.idle();
    phase.finalSave=await save(phaseName+'-final-save');
    phase.sequence.requestEnd=result.requests.length;
    phase.finalState=await state(phaseName+'-final-state');
    await call(phaseName+'-close',()=>current.close());return true;
  }catch(error){return fail(error);}},
  completeS5(){result.complete=true;result.phase='complete';return true;},
  // R1: one shape per fresh arm of the cell's own fixture; the control (layout-relative cells
  // only) runs first and is placed collapsed at its own shape's point before any key.
  async prepareR1(which){try{
    if(!['r1control','r1cand'].includes(which))throw new Error('unknown R1 arm');
    const row=config.r1?.[result.caseId];if(!row)throw new Error('unknown R1 cell');
    const fixture=config.r1Fixtures[row.fixture],texts=fixture.paragraphs;
    if(result.currentOpen?.fixtureSha256!==fixture.sha256||result.currentOpen?.name!==fixture.servedName)throw new Error('R1 fixture not open');
    phaseName=which;phase=result[which]={open:snap(result.currentOpen),points:{}};
    phase.originalSave=await save(which+'-original-save');
    let wrap=null;
    if(row.setup.walk){phase.walk=await r1Walk(row.setup.walk,which+'-walk');wrap=phase.walk.wrap;}
    for(const spec of row.setup.points)phase.points[spec.name]=await locate(r1PointPlan(texts,spec,wrap),which+'-point-'+spec.name);
    const anchor=phase.points.anchor.final.caret,size={w:current.document.widthTwips,h:current.document.heightTwips};
    if(row.setup.method!=='drag')await place(point(anchor),which+'-anchor-click');
    phase.inputStart=result.inputs.length;phase.requestStart=result.requests.length;
    if(row.setup.method!=='drag')return {method:row.setup.method,size};
    // Past the first line's right edge: the middle of the paper right of the first displayed
    // line's search rectangle, at that line's height (public geometry only).
    const line=phase.walk.boxes[0],right=line[0]+line[2];
    phase.dragEnd={x:right+Math.floor((size.w-right)/2),y:line[1],height:line[3]};
    return {method:'drag',points:[anchor,phase.dragEnd],size};
  }catch(error){return fail(error);}},
  async shapeR1(){try{
    phase.setupState=await state(phaseName+'-setup-state');
    phase.setupSelection=await call(phaseName+'-setup-text',()=>current.document.getSelection());
    phase.inputEnd=result.inputs.length;phase.requestEnd=result.requests.length;
    phase.before=await state(phaseName+'-before-state');return true;
  }catch(error){return fail(error);}},
  async controlPointR1(){try{
    // Native emu: the visible cursor rectangle; emuend (the three wrong-old-click Down cells):
    // the actual TEXT_SELECTION_END rectangle.  Both read from this arm's own shape.
    const rule=config.r1[result.caseId].control.rule;
    const r=rule==='emuend'?phase.before.selection?.end:phase.before.caret;
    if(!r)throw new Error('control rectangle absent');
    phase.controlRect=r;
    await place({xTwips:r.x,yTwips:r.y+Math.floor(r.height/2)},phaseName+'-control-click');
    phase.controlState=await state(phaseName+'-control-state');return true;
  }catch(error){return fail(error);}},
  async finishR1(){try{
    if(!actionPromise)throw new Error('measured product action absent');phase.reply=await actionPromise;keyArm.inputEnd=result.inputs.length;
    // Existing S2 observation interval, distinct from product completion.
    await new Promise(resolve=>setTimeout(resolve,500));
    phase.readback=await state(phaseName+'-readback');
    phase.activeSelection=await call(phaseName+'-active-selection',()=>current.document.getSelection());
    phase.marker={generation,inputStart:result.inputs.length,requestStart:result.requests.length,at:performance.now()};
    document.querySelector('#sink').focus();return true;
  }catch(error){return fail(error);}},
  async markerR1(){try{
    phase.marker.inputEnd=result.inputs.length;
    if(typeof current.input?.idle==='function')await current.input.idle();
    phase.finalSave=await save(phaseName+'-final-save');
    phase.marker.requestEnd=result.requests.length;
    phase.finalState=await state(phaseName+'-final-state');
    await call(phaseName+'-close',()=>current.close());
    if(phaseName==='r1cand'){result.complete=true;result.phase='complete';}
    return true;
  }catch(error){return fail(error);}},
  async prepareInteraction(){try{
    const row=config.interactions[result.caseId];if(!row)throw new Error('unknown interaction');
    phaseName='interaction';phase=result.interaction={open:snap(result.currentOpen),points:{}};
    phase.originalSave=await save('interaction-original-save');
    for(const [name,plan] of Object.entries(row.pointPlans))phase.points[name]=await locate(plan,'interaction-point-'+name);
    await place(point(phase.points[row.originPointName].final.caret),'interaction-origin-click');
    phase.before=await state('interaction-before-state');
    return {method:row.method,points:row.logicalPointNames.map(n=>phase.points[n].final.caret),
      size:{w:current.document.widthTwips,h:current.document.heightTwips}};
  }catch(error){return fail(error);}},
  async afterFirstKey(){try{
    phase.firstState=await state('interaction-first-state');
    phase.firstSelection=await call('interaction-first-text',()=>current.document.getSelection());return true;
  }catch(error){return fail(error);}},
  markStep(){phase.inputStart=result.inputs.length;phase.requestStart=result.requests.length;return true;},
  armPlace(name){placeArmed=name;placePromise=null;return true;},
  async answeredPlace(){try{if(!placePromise)throw new Error('product pointer did not call placeCaret');await placePromise;return true;}catch(error){return fail(error);}},
  async selectRangeStep(){try{
    const row=config.interactions[result.caseId];const [a,b]=row.logicalPointNames.map(n=>phase.points[n].final.caret);
    await call('interaction-select-range',()=>current.editor.selectRange(point(a),point(b)));return true;
  }catch(error){return fail(error);}},
  async afterStep(){try{
    phase.inputEnd=result.inputs.length;phase.requestEnd=result.requests.length;
    phase.stepState=await state('interaction-step-state');
    phase.stepSelection=await call('interaction-step-text',()=>current.document.getSelection());return true;
  }catch(error){return fail(error);}},
  async finishInteraction(){try{
    // Existing S2 observation interval, distinct from product completion.
    await new Promise(resolve=>setTimeout(resolve,500));
    phase.readback=await state('interaction-readback');
    phase.activeSelection=await call('interaction-active-selection',()=>current.document.getSelection());
    await call('interaction-close',()=>current.close());result.complete=true;result.phase='complete';return true;
  }catch(error){return fail(error);}},
  async prepare(which){try{
    if(!['reference','candidate','s5cand','s5ref'].includes(which))throw new Error('unknown arm');
    phaseName=which;phase=result[which]={open:snap(result.currentOpen),points:{}};
    phase.originalSave=await save(which+'-original-save');
    // S5 arms reuse their Table 1 source arm's candidate shape.
    const row=config.cases[result.caseId]??config.cases[config.s5?.[result.caseId]?.sourceArm];
    for(const [name,plan] of Object.entries(row.pointPlans))phase.points[name]=await locate(plan,which+'-point-'+name);
    const moving=phase.points[row.movingPointName].final.caret;
    if(which==='reference')await place(point(moving),which+'-origin-click');
    else if(row.nativeSetupMethod!=='drag')await place(point(phase.points[row.anchorPointName].final.caret),which+'-origin-click');
    phase.inputStart=result.inputs.length;
    phase.requestStart=result.requests.length;
    return {method:which==='reference'?'click':row.nativeSetupMethod,
      points:row.setup.logicalPointNames.map(n=>phase.points[n].final.caret),
      size:{w:current.document.widthTwips,h:current.document.heightTwips}};
  }catch(error){return fail(error);}},
  arm(name){armed=name;actionPromise=null;keyArm={name,generation,inputStart:result.inputs.length,at:performance.now()};result.keyArms.push(keyArm);document.querySelector('#sink').focus();return true;},
  async answered(){try{if(!actionPromise)throw new Error('product key did not dispatch session.action');await actionPromise;keyArm.inputEnd=result.inputs.length;return true;}catch(error){return fail(error);}},
  async before(){try{
    phase.setupState=await state(phaseName+'-setup-state');
    phase.setupSelection=await call(phaseName+'-setup-text',()=>current.document.getSelection());
    phase.inputEnd=result.inputs.length;
    phase.requestEnd=result.requests.length;
    phase.before=await state(phaseName+'-before-state');
    return true;
  }catch(error){return fail(error);}},
  async finish(){try{
    if(!actionPromise)throw new Error('measured product action absent');phase.reply=await actionPromise;keyArm.inputEnd=result.inputs.length;
    const c=result.calls.find(c=>c.name===phaseName+'-move');if(!c)throw new Error('measured call missing');
    // Existing S2 observation interval, distinct from product completion.
    await new Promise(resolve=>setTimeout(resolve,500));
    phase.readback=await state(phaseName+'-readback');
    phase.activeSelection=await call(phaseName+'-active-selection',()=>current.document.getSelection());
    if(phaseName==='reference'){
      phase.endpoint=phase.readback.caret;phase.mapping=[];
      // Closed fixture population, no search-until-success loop.
      for(const plan of config.mappingPoints){
        const prefix='reference-map-'+plan.paragraph;
        const origin=await locate(plan,prefix);
        phase.mapping.push({paragraph:plan.paragraph,origin});
      }
      const endpoint=phase.endpoint;
      const candidates=phase.mapping.filter(row=>{
        if(config.fixtureParagraphs[row.paragraph]==='')return row.origin.final.caret.x===endpoint.x&&row.origin.final.caret.y===endpoint.y;
        return row.origin.boxes.some(([x,y,w,h])=>x<=endpoint.x&&endpoint.x<=x+w&&y<=endpoint.y&&endpoint.y<=y+h);
      });
      if(candidates.length!==1)throw new Error('logical endpoint geometry missing/ambiguous');
      const chosen=candidates[0],prefix='reference-map-'+chosen.paragraph;
      await call(prefix+'-endpoint-select',()=>current.editor.selectRange(point(chosen.origin.final.caret),point(endpoint)));
      const selected=await call(prefix+'-endpoint-text',()=>current.document.getSelection());
      phase.endpointMapping={paragraph:chosen.paragraph,selected};
    }
    await call(phaseName+'-close',()=>current.close());
    if(phaseName==='candidate'){result.complete=true;result.phase='complete';}
    return true;
  }catch(error){return fail(error);}}
};
try{
  const bytes=await(await fetch('./selection-config.json',{cache:'no-store'})).arrayBuffer();
  result.configSha256=await hash(bytes);config=JSON.parse(new TextDecoder().decode(bytes));
  result.servedSources={};result.artifacts={};
  for(const path of Object.keys(config.servedSources)){
    const response=await fetch('./'+path,{cache:'no-store'});if(!response.ok)throw new Error('source HTTP '+path);
    result.servedSources[path]=await hash(await response.arrayBuffer());}
  for(const path of Object.keys(config.profile.artifacts)){
    const response=await fetch('./profiles/e2-editor-v23/'+path,{cache:'no-store'});if(!response.ok)throw new Error('artifact HTTP '+path);
    result.artifacts[path]=await hash(await response.arrayBuffer());}
  result.fixtureManifestSha256=await hash(await(await fetch('./e1-fixtures/manifest.json',{cache:'no-store'})).arrayBuffer());
  await import('./e2-editor-app.js');result.booted=true;
}catch(error){fail(error);}
