Adversarial review of completed Calc successor source. Return <=2 concrete data-loss or wrong-target bugs with reproducible sequences and code evidence; <=250words. Do not ask generic testing or redesign. Native has passed22 cases, browserChromeFirefoxN3 passed240 including mixed/allscriptformats, explicit targets aftercursorreads, protected/merge/stalerefusals, cap, XML/reopen/DOMtiles. Rectangle state hasactiveanchor/focus, nativepreflight wholeprotected/unmerged/cap andonesetPropertyValues. setFormat andsave are serialized via_chain including hostack; newtyping duringsave is draftonly, beginEdit collapsesrange. Rangeunknownoutcomes blockfurtherwrites; knownrefusals no mutation. Page sends explicit boolean mixed/off→true/allon→false. Autosave neverforceconfirmsdraft, idle30/cap5min+3quiet/hidden, skipsediting/composition/pending/busy/error; copy/errors pause untilmanualoriginalsuccess. Existinghost conditionalwrite/stickycopy/leaveguard remains. Judge these exact excerpts; if noactualbug found say so.
  setFormat(format,enabled) {
    return this._enqueue(async()=>{
      this._assertReady(true);
      if (!CELL_FORMATS.includes(format) || typeof enabled!=="boolean")
        throw new DocumentSdkError("INVALID_ARGUMENT","unknown cell format");
      if(this._selection?.multiple) {
        if(this.document.rangeFormattingSupported!==true)
          throw new DocumentSdkError("RANGE_FORMAT_UNSUPPORTED","this engine does not support range formatting");
        const selected=this._selection;
        const result=await this.document.setRangeFormat(selected.column,selected.row,selected.endColumn,selected.endRow,
          format,enabled,{part:selected.part,expectedRevision:this.document.revision});
        this.scheduler.invalidateRevision(this.document.revision);
        // Formatting can change row heights. Refresh both endpoint geometries,
        // retaining the explicit address rectangle and active anchor.
        try {
          const {cell:anchor}=await this.document.readCell(selected.anchor.column,selected.anchor.row,{part:selected.part});
          const {cell:focus}=await this.document.readCell(selected.focus.column,selected.focus.row,{part:selected.part});
          this._cell=anchor;this._selection=rectangle(anchor,focus);this._rangeFormat=result.range;
          this._draft=anchor.input;this._draftVersion++;
        } catch(error) {
          throw new DocumentSdkError("MUTATION_OUTCOME_UNKNOWN",`range applied but endpoint refresh failed: ${error.message}`);
        }
        this._emit();return result.range;
      }
      await this._commitNow();
      const cell=this._cell;
      const result=await this.document.setCellFormat(cell.column,cell.row,format,enabled,{part:cell.part});
      // _adopt emits synchronously: its listener can schedule tiles immediately.
      this.scheduler.invalidateRevision(this.document.revision);
      this._adopt(result.cell);
      return result.cell;
    });
  }
  save(target,{commitDraft=true}={}) {
    return this._enqueue(async()=>{
      this._assertReady();
      if (this._readOnly)
        throw new DocumentSdkError("READ_ONLY", "this spreadsheet cannot be saved");
      if(commitDraft)await this._commitNow();
      const revision=this.document.revision;
      this._saving++;this._emit();
      try {
        const bytes=await this.document.save({format:"ods"});
        const result=await target(bytes,{name:this.state.fileName});
        this._savedRevision=revision;
        return {bytes,result,revision};
      } catch (error) {
        if (error.outcome==="copy") this._savedRevision=revision;
        throw error;
      } finally { this._saving--;this._emit(); }
    });
  }

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
