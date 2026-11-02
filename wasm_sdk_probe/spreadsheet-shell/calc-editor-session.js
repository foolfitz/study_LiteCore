// A cell has one draft shared by the formula bar and in-place editor. Engine
// operations are serialized, and an edit's target is captured before it waits.
import { OdsViewerSession } from "../viewer-shell/ods-viewer-session.js";
import { DocumentSdkError } from "../sdk/document-sdk.js";
import { CELL_FORMATS, CELL_INPUT_LIMIT, CELL_STYLES } from "./calc-document-sdk.js";

export function inputIntent(event) {
  if (event.isComposing || event.keyCode === 229) return null;
  if (event.key === "Escape") return "cancel";
  if (event.key === "Enter" && !event.shiftKey && !event.altKey) return "commit";
  return null;
}

// Address rectangle with endpoint merge extents, not recursive merge closure.
function rectangle(anchor, focus = anchor) {
  return Object.freeze({part:anchor.part,anchor,focus,
    column:Math.min(anchor.column,focus.column),row:Math.min(anchor.row,focus.row),
    endColumn:Math.max(anchor.endColumn,focus.endColumn),endRow:Math.max(anchor.endRow,focus.endRow),
    xTwips:Math.min(anchor.xTwips,focus.xTwips),yTwips:Math.min(anchor.yTwips,focus.yTwips),
    widthTwips:Math.max(anchor.xTwips+anchor.widthTwips,focus.xTwips+focus.widthTwips)-Math.min(anchor.xTwips,focus.xTwips),
    heightTwips:Math.max(anchor.yTwips+anchor.heightTwips,focus.yTwips+focus.heightTwips)-Math.min(anchor.yTwips,focus.yTwips),
    multiple:anchor.column!==focus.column || anchor.row!==focus.row});
}

export class CalcEditorSession {
  constructor(options) {
    this.document = null;
    this._cell = null;
    this._sheetCells = new Map();
    this._selection = null;
    this._rangeFormat = null;
    this._draft = "";
    this._draftVersion = 0;
    this._editing = null;
    this._readOnly = false;
    this._savedRevision = null;
    this._saving = 0;
    this._busy = 0;
    this._selecting = 0;
    this._error = null;
    this._closed = false;
    this._uncertain = false;
    this._chain = Promise.resolve();
    this._onState = options.onState || (() => {});
    this.viewer = new OdsViewerSession({ ...options,
      onState: () => this._emit(),
      engineFactory: async config => {
        const engine = await options.engineFactory(config);
        return { manifest: engine.manifest, dispose: () => engine.dispose(),
          open: async (...args) => {
            this.document = await engine.open(...args);
            return this.document;
          } };
      },
    });
  }

  get scheduler() { return this.viewer.scheduler; }
  get state() {
    return { ...this.viewer.state, cell: this._cell, selection:this._selection, rangeFormat:this._rangeFormat,
      rangeFormattingSupported:this.document?.rangeFormattingSupported===true,
      rangeStylingSupported:this.document?.rangeStylingSupported===true, draft: this._draft,
      editing: this._editing, readOnly: this._readOnly, busy: this._busy > 0,
      selectionPending: this._selecting > 0,
      saving: this._saving > 0, revision: this.document?.revision ?? null,
      dirty: this.hasUnsavedEdits(), error: this._error || this.viewer.state.error,
      committedDirty:this.document!==null && this._savedRevision!==null && this.document.revision!==this._savedRevision,
      uncertain: this._uncertain };
  }
  _emit() { if (this.viewer) this._onState(this.state); }

  async open({bytes, name, readOnly = false}) {
    this._readOnly = readOnly === true;
    await this.viewer.open({bytes, name});
    if (this._closed) return;
    this._savedRevision = this.document.revision;
    const result = await this.document.readCell(0, 0);
    this._adopt(result.cell);
    return this.state;
  }

  hasUnsavedEdits() {
    return this._uncertain || this._saving > 0
      || (this.document !== null && this._savedRevision !== null && this.document.revision !== this._savedRevision)
      || (this._editing !== null && this._draft !== this._cell?.input);
  }
  _assertReady(writable = false) {
    if (this._closed || this.viewer.state.state !== "ready" || !this.document)
      throw new DocumentSdkError("NOT_READY", "spreadsheet is not ready");
    if (this._uncertain)
      throw new DocumentSdkError("MUTATION_OUTCOME_UNKNOWN", "the last edit could not be confirmed; keep this page open");
    if (writable && (this._readOnly || !this._cell?.writable))
      throw new DocumentSdkError("READ_ONLY", "this spreadsheet cell cannot be edited");
  }
  _adopt(cell) {
    this._cell = cell;
    this._selection = rectangle(cell);
    this._rangeFormat = null;
    this._draft = cell.input;
    this._draftVersion++;
    this._editing = null;
    this._emit();
  }
  _enqueue(work, {selection = false} = {}) {
    if(selection){this._selecting++;this._emit();}
    const run = this._chain.then(async () => {
      this._assertReady();
      this._busy++;this._error=null;this._emit();
      try { return await work(); }
      catch (error) {
        this._error={code:error.code || "EDIT_FAILED",message:error.message || String(error)};
        if (["MUTATION_OUTCOME_UNKNOWN","TIMEOUT","WORKER_CRASHED"].includes(error.code)) this._uncertain=true;
        throw error;
      } finally { this._busy--;this._emit(); }
    });
    const completed=run.finally(()=>{if(selection){this._selecting--;this._emit();}});
    this._chain = completed.catch(() => {});
    return completed;
  }

  beginEdit(mode = "formula", {replace = false} = {}) {
    this._assertReady(true);
    this._selection = rectangle(this._cell);
    this._rangeFormat = null;
    if (replace && !this._editing) {
      this._draft = "";
      this._draftVersion++;
    }
    this._editing = mode;
    this._emit();
  }
  setDraft(text) {
    this._assertReady(true);
    if (typeof text !== "string") throw new TypeError("draft must be text");
    if (text.length > CELL_INPUT_LIMIT)
      throw new DocumentSdkError("CELL_TEXT_TOO_LONG", `cell input exceeds ${CELL_INPUT_LIMIT} UTF-16 code units`);
    this._draft = text;
    this._draftVersion++;
    this._editing ||= "formula";
    this._emit();
  }
  cancelEdit() {
    this._draft = this._cell?.input ?? "";
    this._draftVersion++;
    this._editing=null;this._error=null;this._emit();
  }
  async _commitNow() {
    if (!this._editing) return;
    this._assertReady(true);
    const cell = this._cell, text = this._draft, version = this._draftVersion;
    if (text === cell.input) { this._editing=null;this._emit();return; }
    const result = await this.document.setCellInput(cell.column,cell.row,text,
      {part:cell.part,expectedRevision:this.document.revision});
    this._cell=result.cell;
    this._selection=rectangle(result.cell);
    this._rangeFormat=null;
    this.scheduler.invalidateRevision(this.document.revision);
    if (version === this._draftVersion) {
      this._draft=result.cell.input;this._editing=null;
    }
    this._emit();
    if (version !== this._draftVersion) await this._commitNow();
  }
  commit() { return this._enqueue(() => this._commitNow()); }
  _selectResult(cell, extend) {
    this._rangeFormat=null;
    if (extend && this._cell?.part===cell.part) {
      this._selection=rectangle(this._cell,cell);
      this._emit();
    } else this._adopt(cell);
    return cell;
  }
  async _refreshRangeFormat() {
    const selection=this._selection;
    if(!selection?.multiple || this.document.rangeFormattingSupported!==true)return;
    try {
      const {range}=await this.document.readRange(selection.column,selection.row,selection.endColumn,selection.endRow,
        {part:selection.part,expectedRevision:this.document.revision});
      if(this._selection===selection)this._rangeFormat=range;
    } catch(error) {
      if(error.code!=="RANGE_TOO_LARGE")throw error;
      if(this._selection===selection)this._rangeFormat={...selection,bold:null,italic:null,underline:null,
        textColor:null,backColor:null,horizontalAlign:null,writable:false,refusalCode:error.code};
    }
    this._emit();
  }
  selectAt(xTwips,yTwips,{extend=false,valid=()=>true}={}) {
    return this._enqueue(async()=>{
      if(!valid())return;
      await this._commitNow();
      const result=await this.document.hitCell(xTwips,yTwips);
      if(valid()) {
        this._selectResult(result.cell,extend);await this._refreshRangeFormat();return result.cell;
      }
    },{selection:true});
  }
  selectCell(column,row,{extend=false,valid=()=>true}={}) {
    return this._enqueue(async()=>{
      if(!valid())return;
      await this._commitNow();
      const result=await this.document.readCell(column,row);
      if(valid()) {
        this._selectResult(result.cell,extend);await this._refreshRangeFormat();return result.cell;
      }
    },{selection:true});
  }
  moveSelection(dx,dy,{extend=false}={}) {
    return this._enqueue(async()=>{
      if(!Number.isInteger(dx) || !Number.isInteger(dy) || Math.abs(dx)+Math.abs(dy)!==1)
        throw new DocumentSdkError("INVALID_ARGUMENT","selection movement must be one axis step");
      await this._commitNow();
      const focus=this._selection.focus;
      const x=dx<0 ? focus.xTwips-1 : dx>0 ? focus.xTwips+focus.widthTwips+1 : focus.xTwips+Math.floor(focus.widthTwips/2);
      const y=dy<0 ? focus.yTwips-1 : dy>0 ? focus.yTwips+focus.heightTwips+1 : focus.yTwips+Math.floor(focus.heightTwips/2);
      if(x<0 || y<0){this._selectResult(focus,extend);await this._refreshRangeFormat();return focus;}
      const result=await this.document.hitCell(x,y);
      this._selectResult(result.cell,extend);await this._refreshRangeFormat();return result.cell;
    },{selection:true});
  }
  showPart(part) {
    return this._enqueue(async()=>{
      await this._commitNow();
      // SPEC-P-demo-batch-1 2: each sheet keeps its active cell for as long as
      // the document is open; a sheet not seen before starts at A1.
      if(this._cell)this._sheetCells.set(this._cell.part,{column:this._cell.column,row:this._cell.row});
      await this.viewer.showPart(part);
      const cell=this._sheetCells.get(part) ?? {column:0,row:0};
      const result=await this.document.readCell(cell.column,cell.row);
      this._adopt(result.cell);
      return this.state;
    },{selection:true});
  }
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
  // SPEC-P-demo-batch-3 3.1.  The bridge writes styles over a range only, so one cell goes as its merged extent.
  setStyle(style,value) {
    return this._enqueue(async()=>{
      this._assertReady(true);
      if(!Object.hasOwn(CELL_STYLES,style) || !CELL_STYLES[style](value))
        throw new DocumentSdkError("INVALID_ARGUMENT","unknown cell style");
      if(this.document.rangeStylingSupported!==true)
        throw new DocumentSdkError("RANGE_FORMAT_UNSUPPORTED","this engine does not support cell styles");
      const selected=this._selection;
      if(selected?.multiple) {
        const result=await this.document.setRangeStyle(selected.column,selected.row,selected.endColumn,selected.endRow,
          style,value,{part:selected.part,expectedRevision:this.document.revision});
        this.scheduler.invalidateRevision(this.document.revision);
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
      await this.document.setRangeStyle(cell.column,cell.row,cell.endColumn,cell.endRow,style,value,
        {part:cell.part,expectedRevision:this.document.revision});
      this.scheduler.invalidateRevision(this.document.revision);
      let refreshed;
      try {
        ({cell:refreshed}=await this.document.readCell(cell.column,cell.row,{part:cell.part}));
      } catch(error) {
        throw new DocumentSdkError("MUTATION_OUTCOME_UNKNOWN",`style applied but cell refresh failed: ${error.message}`);
      }
      this._adopt(refreshed);
      return refreshed;
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
  scheduleViewport(viewport) { return this.viewer.scheduleViewport(viewport); }
  whenIdle() { return this._chain; }
  drain() { return this.viewer.drain(); }
  refit() { return this.viewer.refit(); }
  async close() {
    this._closed=true;
    await this._chain;
    await this.viewer.close();
  }
}
