Read-only adversarial audit. Return at most3 concrete bugs and reproducible event sequences; <=350words, no general advice. Calc committed-only autosave: never forcecommits draft; skips active editing/IME/pending input/pointer/busy/error. Host conditional writes and stickycopytarget preexist. Controller update runs on every session state and input/pointer activity. session.save(target,{commitDraft:false}) serializes export+host, records saved revision captured beforeexport; normal manual true commits draftfirst. Host copythrows outcome=copy afterstoringbytes and then retains target; errorstranded retainsbytes. Ordinarycommit disabledinput preexistingoutsidebatch. Check actual code below.
// Save committed spreadsheet changes without ending a cell edit. The page owns
// input/gesture eligibility; the existing host owns conditional writes and copies.
export const AUTOSAVE_TIMING = Object.freeze({idle:30000,cap:300000,quiet:3000});

export class CalcAutosave {
  constructor({snapshot,save,onState=()=>{},now=()=>performance.now(),
    setTimer=(fn,delay)=>setTimeout(fn,delay),clearTimer=id=>clearTimeout(id),timing=AUTOSAVE_TIMING}) {
    Object.assign(this,{snapshot,save,onState,now,setTimer,clearTimer,timing});
    this.timer=null;this.firstDirty=null;this.lastActivity=now();this.revision=null;
    this.inFlight=false;this.paused=null;this.closed=false;this.events=[];
  }
  get state() {
    const s=this.snapshot();
    return {enabled:s.host===true,paused:this.paused,saving:this.inFlight,
      draft:s.editing!==null && s.editing!==undefined,committedDirty:s.committedDirty===true};
  }
  _clear() {if(this.timer!==null)this.clearTimer(this.timer);this.timer=null;}
  activity() {this.lastActivity=this.now();this.update();}
  update() {
    if(this.closed)return;
    const s=this.snapshot(),now=this.now();
    if(s.revision!==this.revision) {
      if(this.revision!==null)this.lastActivity=now;
      this.revision=s.revision;
    }
    if(s.committedDirty===true){if(this.firstDirty===null)this.firstDirty=now;}
    else this.firstDirty=null;
    this._clear();
    if(s.host===true && this.firstDirty!==null && !this.paused && !this.inFlight) {
      const deadline=Math.min(this.lastActivity+this.timing.idle,
        Math.max(this.firstDirty+this.timing.cap,this.lastActivity+this.timing.quiet));
      // A blocked overdue save waits for the next input/session notification.
      // Repeated onState callbacks must not create a zero-delay timer loop.
      if(this._allowed(s))this.timer=this.setTimer(()=>{this.timer=null;void this.flush("idle");},Math.max(0,deadline-now));
    }
    this.onState(this.state);
  }
  _allowed(s) {
    return s.host===true && s.state==="ready" && s.committedDirty===true
      && s.readOnly!==true && s.busy!==true && s.saving!==true
      && s.selectionPending!==true && s.editing==null && s.composing!==true
      && s.pendingEntry!==true && s.dragging!==true && s.manualPending!==true
      && s.uncertain!==true && !s.error;
  }
  async flush(reason="hidden") {
    this._clear();
    if(this.closed || this.paused || this.inFlight)return false;
    const conditions={...this.snapshot(),reason};
    if(!this._allowed(conditions))return false;
    this.inFlight=true;this.events.push({type:"start",at:this.now(),conditions});this.update();
    try {
      const result=await this.save(conditions);
      this.events.push({type:"saved",at:this.now(),revision:conditions.revision});
      // A host returning a copy target is never permission to resume autosave.
      if(result?.target && result.target!=="original")this.paused="copy";
      return true;
    } catch(error) {
      this.paused=error.outcome || error.code || "failed";
      this.events.push({type:"failed",at:this.now(),outcome:this.paused});
      return false;
    } finally {this.inFlight=false;this.update();}
  }
  manualSaved(result) {
    if(!result?.target || result.target==="original")this.paused=null;
    else this.paused="copy";
    this.update();
  }
  manualFailed(error) {this.paused=error.outcome || error.code || "failed";this.update();}
  dispose() {this.closed=true;this._clear();}
}

PAGE SAVE
async function save(trigger="manual",conditions,owner=session) {
  if(!owner)return;
  const controller=autosave;
  if(trigger==="auto") {
    // Recheck synchronously immediately before enqueueing. Autosave never
    // consumes a pending textarea buffer or ends a cell/IME edit.
    if(owner!==session || composing || pendingEntry || dragWork || owner.state.editing || owner.state.busy)return;
    return saveToHost(owner,trigger,conditions);
  }
  manualSaves++;controller?.update();
  try {
    await owner.whenIdle();
    if(owner!==session)return;
    const entryWasPending=pendingEntry!==null,flushed=await flushPendingEntry();
    if(entryWasPending && flushed!==true){notice("輸入尚未接回儲存格，請先完成或取消輸入。",true);return;}
    if(pendingEntry || composing){notice("請先完成輸入或取消尚未寫入的內容，再儲存。",true);return;}
    const result=await saveToHost(owner,trigger);
    controller?.manualSaved(result);
    return result;
  } catch(error) {controller?.manualFailed(error);throw error;}
  finally {manualSaves--;controller?.update();}
}
async function saveToHost(owner,trigger,conditions) {
  const saved=await owner.save(async(bytes,{name})=>{
    if(HOST)return HOST.save(bytes,{name,trigger,conditions});
    const url=URL.createObjectURL(new Blob([bytes],{type:"application/vnd.oasis.opendocument.spreadsheet"}));
    const link=document.createElement("a");link.href=url;link.download=name;link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    return{name};
  },{commitDraft:trigger!=="auto"});
  record.lastSave={revision:saved.revision,bytes:saved.bytes.byteLength,result:saved.result,trigger};
  if(diagnostics)record.lastExport=saved.bytes;
  if(trigger!=="auto")notice(HOST ? "已存回試算表。":"已交給瀏覽器下載，請確認檔案已存好。");
  return saved.result;
}
