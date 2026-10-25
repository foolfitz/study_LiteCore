// A cell has one draft shared by the formula bar and in-place editor. Engine
// operations are serialized, and an edit's target is captured before it waits.
import { OdsViewerSession } from "../viewer-shell/ods-viewer-session.js";
import { DocumentSdkError } from "../sdk/document-sdk.js";
import { CELL_FORMATS, CELL_INPUT_LIMIT } from "./calc-document-sdk.js";

export function inputIntent(event) {
  if (event.isComposing || event.keyCode === 229) return null;
  if (event.key === "Escape") return "cancel";
  if (event.key === "Enter" && !event.shiftKey && !event.altKey) return "commit";
  return null;
}

export class CalcEditorSession {
  constructor(options) {
    this.document = null;
    this._cell = null;
    this._draft = "";
    this._draftVersion = 0;
    this._editing = null;
    this._readOnly = false;
    this._savedRevision = null;
    this._saving = 0;
    this._busy = 0;
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
    return { ...this.viewer.state, cell: this._cell, draft: this._draft,
      editing: this._editing, readOnly: this._readOnly, busy: this._busy > 0,
      saving: this._saving > 0, revision: this.document?.revision ?? null,
      dirty: this.hasUnsavedEdits(), error: this._error || this.viewer.state.error,
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
    this._draft = cell.input;
    this._draftVersion++;
    this._editing = null;
    this._emit();
  }
  _enqueue(work) {
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
    this._chain = run.catch(() => {});
    return run;
  }

  beginEdit(mode = "formula") {
    this._assertReady(true);
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
    this.scheduler.invalidateRevision(this.document.revision);
    if (version === this._draftVersion) {
      this._draft=result.cell.input;this._editing=null;
    }
    this._emit();
    if (version !== this._draftVersion) await this._commitNow();
  }
  commit() { return this._enqueue(() => this._commitNow()); }
  selectAt(xTwips,yTwips) {
    return this._enqueue(async()=>{
      await this._commitNow();
      const result=await this.document.hitCell(xTwips,yTwips);
      this._adopt(result.cell);
      return result.cell;
    });
  }
  selectCell(column,row) {
    return this._enqueue(async()=>{
      await this._commitNow();
      const result=await this.document.readCell(column,row);
      this._adopt(result.cell);
      return result.cell;
    });
  }
  showPart(part) {
    return this._enqueue(async()=>{
      await this._commitNow();
      await this.viewer.showPart(part);
      const result=await this.document.readCell(0,0);
      this._adopt(result.cell);
      return this.state;
    });
  }
  setFormat(format,enabled) {
    return this._enqueue(async()=>{
      this._assertReady(true);
      if (!CELL_FORMATS.includes(format) || typeof enabled!=="boolean")
        throw new DocumentSdkError("INVALID_ARGUMENT","unknown cell format");
      await this._commitNow();
      const cell=this._cell;
      const result=await this.document.setCellFormat(cell.column,cell.row,format,enabled,{part:cell.part});
      // _adopt emits synchronously: its listener can schedule tiles immediately.
      this.scheduler.invalidateRevision(this.document.revision);
      this._adopt(result.cell);
      return result.cell;
    });
  }
  save(target) {
    return this._enqueue(async()=>{
      this._assertReady();
      if (this._readOnly)
        throw new DocumentSdkError("READ_ONLY", "this spreadsheet cannot be saved");
      await this._commitNow();
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
  drain() { return this.viewer.drain(); }
  refit() { return this.viewer.refit(); }
  async close() {
    this._closed=true;
    await this._chain;
    await this.viewer.close();
  }
}
