import assert from "node:assert/strict";
import test from "node:test";
import {pathToFileURL} from "node:url";
const {CalcAutosave}=await import(process.env.CALC_AUTOSAVE_MODULE
  ? pathToFileURL(process.env.CALC_AUTOSAVE_MODULE) : "../spreadsheet-shell/calc-autosave.js");

function fixture(save) {
  let now=0,id=0;const timers=new Map(),calls=[];
  const s={host:true,state:"ready",readOnly:false,editing:null,committedDirty:false,revision:0};
  const clock={now:()=>now,setTimer:(fn,delay)=>{timers.set(++id,{fn,at:now+delay});return id;},clearTimer:id=>timers.delete(id)};
  const c=new CalcAutosave({snapshot:()=>({...s}),save:async conditions=>{
    calls.push(conditions);if(save)return save(conditions);s.committedDirty=false;return{target:"original"};
  },...clock});
  c.update();
  async function advance(ms) {
    const end=now+ms;let rounds=0;
    for(;;) {
      const next=[...timers].filter(([,v])=>v.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];
      if(!next)break;
      assert.ok(++rounds<1000,"no overdue blocked timer spin");
      now=next[1].at;timers.delete(next[0]);next[1].fn();
      for(let i=0;i<8;i++)await Promise.resolve();
    }
    now=end;
  }
  function dirty(){s.revision++;s.committedDirty=true;c.update();}
  return{c,s,calls,timers,advance,dirty};
}

test("idle save waits 30 seconds and includes exact eligibility and revision",async()=>{
  const f=fixture();f.dirty();await f.advance(29999);assert.equal(f.calls.length,0);
  await f.advance(1);assert.equal(f.calls.length,1);assert.equal(f.calls[0].revision,1);
  assert.equal(f.calls[0].reason,"idle");assert.equal(f.s.committedDirty,false);
  await f.advance(600000);assert.equal(f.calls.length,1);
});
test("navigation and actual mutation restart idle; five-minute cap still needs three quiet seconds",async()=>{
  const f=fixture();f.dirty();await f.advance(29000);f.c.activity();
  await f.advance(29999);assert.equal(f.calls.length,0);
  await f.advance(1);assert.equal(f.calls.length,1);
  const g=fixture();g.dirty();
  for(let n=0;n<149;n++){await g.advance(2000);g.c.activity();}
  await g.advance(2000);g.c.activity();assert.equal(g.calls.length,0);
  await g.advance(2999);assert.equal(g.calls.length,0);
  await g.advance(1);assert.equal(g.calls.length,1);
});
test("every input/session blocker defers; clearing it permits an overdue save",async()=>{
  const blockers={host:false,state:"opening",readOnly:true,editing:"inline",busy:true,saving:true,
    selectionPending:true,composing:true,pendingEntry:true,dragging:true,manualPending:true,uncertain:true,error:{code:"STALE"}};
  for(const [key,value] of Object.entries(blockers)) {
    const f=fixture();f.dirty();const prior=f.s[key];f.s[key]=value;f.c.update();
    await f.advance(40000);await f.c.flush("hidden");assert.equal(f.calls.length,0,key);
    f.s[key]=prior;f.c.update();await f.advance(0);assert.equal(f.calls.length,1,key);
  }
});
test("an unconfirmed draft alone never creates an autosave or download",async()=>{
  const f=fixture();f.s.editing="formula";f.c.activity();
  await f.advance(600000);await f.c.flush();assert.equal(f.calls.length,0);assert.equal(f.c.state.draft,true);
});
test("hidden bypasses idle only for eligible committed changes and saves only once",async()=>{
  const f=fixture();f.dirty();assert.equal(await f.c.flush("hidden"),true);
  assert.equal(f.calls.length,1);assert.equal(f.calls[0].reason,"hidden");
  await f.c.flush("hidden");await f.advance(40000);assert.equal(f.calls.length,1);
});
test("a slow save is single flight and newer changes remain due",async()=>{
  let release;const f=fixture(()=>new Promise(resolve=>{release=resolve;}));f.dirty();
  const pending=f.c.flush();await f.c.flush();await f.advance(40000);assert.equal(f.calls.length,1);
  f.dirty();release({target:"original"});await pending;
  await f.advance(29999);assert.equal(f.calls.length,1);
  await f.advance(1);assert.equal(f.calls.length,2);release({target:"original"});
});
test("copy, stranded and export failures pause until explicit successful original save",async()=>{
  for(const error of [{outcome:"copy"},{outcome:"stranded"},{code:"WORKER_CRASHED"}]) {
    const f=fixture(async()=>{throw error;});f.dirty();await f.c.flush();
    assert.ok(f.c.state.paused);f.dirty();await f.advance(600000);await f.c.flush();assert.equal(f.calls.length,1);
    f.c.manualSaved({target:"a-copy.ods"});await f.c.flush();assert.equal(f.calls.length,1);
    f.c.manualSaved({target:"original"});await f.c.flush();assert.equal(f.calls.length,2);
  }
});
test("manual failure pauses and disposal cancels scheduled and hidden requests",async()=>{
  const f=fixture();f.dirty();f.c.manualFailed({outcome:"stranded"});
  await f.advance(60000);assert.equal(f.calls.length,0);
  f.c.manualSaved({target:"original"});f.c.dispose();
  await f.advance(600000);await f.c.flush();assert.equal(f.calls.length,0);assert.equal(f.timers.size,0);
});
test("browser timer functions never receive the controller as their DOM receiver",t=>{
  let armed=0,cleared=0;
  t.mock.method(globalThis,"setTimeout",function(){assert.ok(!(this instanceof CalcAutosave));armed++;return 17;});
  t.mock.method(globalThis,"clearTimeout",function(){assert.ok(!(this instanceof CalcAutosave));cleared++;});
  const c=new CalcAutosave({snapshot:()=>({host:true,state:"ready",committedDirty:true,revision:1}),save:async()=>{}});
  c.update();assert.equal(armed,1);c.dispose();assert.equal(cleared,1);
});
