Read-only adversarial audit. Return at most 3 concrete bugs with sequence; no generic advice. This controller governs Calc committed-only autosave. Page calls update on every state emission, activity on key/beforeinput/composition/pointer events; flush on hidden. snapshot uses null editing for no draft and true busy/selectionPending during work. save callback calls serialized session.save(commitDraft:false), host conditional write; failures pause. Manual success to original resumes. Find data-loss/race/timer eligibility bugs, if none say none.
// Save committed spreadsheet changes without ending a cell edit. The page owns
// input/gesture eligibility; the existing host owns conditional writes and copies.
export const AUTOSAVE_TIMING = Object.freeze({idle:30000,cap:300000,quiet:3000});

export class CalcAutosave {
  constructor({snapshot,save,onState=()=>{},now=()=>performance.now(),
    setTimer=setTimeout,clearTimer=clearTimeout,timing=AUTOSAVE_TIMING}) {
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
