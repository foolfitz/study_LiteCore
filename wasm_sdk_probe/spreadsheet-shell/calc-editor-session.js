// A cell has one draft shared by the formula bar and in-place editor. Engine
// operations are serialized, and an edit's target is captured before it waits.
import { OdsViewerSession } from "../viewer-shell/ods-viewer-session.js";
import { DocumentSdkError } from "../sdk/document-sdk.js";
import { CELL_FORMATS, CELL_INPUT_LIMIT, CELL_STYLES, SHEET_COLUMNS, SHEET_ROWS, ZOOM_PERCENTS } from "./calc-document-sdk.js";

export function inputIntent(event) {
  if (event.isComposing || event.keyCode === 229) return null;
  if (event.key === "Escape") return "cancel";
  if (event.key === "Enter" && !event.shiftKey && !event.altKey) return "commit";
  return null;
}

// SPEC-P-calc-sheets 3.  A1-style addresses; columns A..XFD, rows 1..1048576.
export function columnLetters(column) {
  let text = "";
  for (let n = column; n >= 0; n = Math.floor(n / 26) - 1) text = String.fromCharCode(65 + n % 26) + text;
  return text;
}
// E1: the core quotes a sheet name unless it is a plain name (letters -- CJK included --, digits and underscores, not starting
// with a digit), doubling an apostrophe.  Quoting is always accepted, so anything else is quoted.
function sheetName(name) {
  return /^[\p{L}_][\p{L}\p{N}_]*$/u.test(name) ? name : `'${name.replaceAll("'", "''")}'`;
}
// The text a click (or a drag) inserts: B1, B1:C2, or $Sheet.B1 / $Sheet.B1:C2 for another sheet than the edited cell's.
export function sheetReference(names, home, range) {
  const first = columnLetters(range.column) + (range.row + 1);
  const end = range.endColumn ?? range.column, endRow = range.endRow ?? range.row;
  const address = end === range.column && endRow === range.row ? first : `${first}:${columnLetters(end)}${endRow + 1}`;
  return range.part === home ? address : `$${sheetName(names[range.part])}.${address}`;
}
// Where a pointed reference goes, or null: the span to replace in a formula draft.  `last` is the span the previous point
// inserted ({start, end, text}); a caret right after it replaces it, as desktop Calc does.
const SLOT_BEFORE = new Set(["=", "(", ",", ";", ":", "!", "~", "+", "-", "*", "/", "^", "&", "<", ">"]);
export function referenceSlot(text, start, end = start, last = null) {
  if (typeof text !== "string" || !text.startsWith("=") || start < 1 || end < start || end > text.length) return null;
  if (last && start === end && last.end === start && text.slice(last.start, last.end) === last.text)
    return {start: last.start, end: last.end};
  let before = start - 1;
  while (before > 0 && text[before] === " ") before--;
  return SLOT_BEFORE.has(text[before]) ? {start, end} : null;
}
// The name box: A1, $A$1, Sheet.A1, $Sheet.A1, 'Sheet name'.A1, and Excel's Sheet!A1.  Sheet names compare without case,
// as the core's references do (E1).
export function parseCellTarget(text, names) {
  const value = String(text ?? "").trim();
  const match = /^(?:\$?(?:'((?:[^']|'')+)'|([^.!'$][^.!']*))[.!])?\$?([A-Za-z]{1,3})\$?([0-9]+)$/u.exec(value);
  if (!match) return {error: "INVALID_ADDRESS"};
  let column = 0;
  for (const char of match[3].toUpperCase()) column = column * 26 + char.charCodeAt(0) - 64;
  const row = Number(match[4]);
  if (column > SHEET_COLUMNS || row < 1 || row > SHEET_ROWS || !/^[1-9]/.test(match[4])) return {error: "INVALID_ADDRESS"};
  const target = {column: column - 1, row: row - 1, part: null};
  const wanted = match[1] !== undefined ? match[1].replaceAll("''", "'") : match[2];
  if (wanted === undefined) return target;
  let part = names.indexOf(wanted);
  if (part < 0) part = names.findIndex(name => name.toLocaleLowerCase() === wanted.toLocaleLowerCase());
  return part < 0 ? {error: "UNKNOWN_SHEET", sheet: wanted} : {...target, part};
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

// SPEC-P-calc-headers 3.4: whole columns (kind "columns"), whole rows ("rows") or the sheet.  The address rectangle is the
// indices asked for, first..last; anchor and focus are the cells in row 1 (columns) or column A (rows), read there and never at
// the sheet's end (a read at row 1048576 would stretch the engine's tiled area).  The drawn box spans the document's extent.
function wholeRectangle(kind, first, last, anchor, focus, extent) {
  const columns = kind === "columns", rows = kind === "rows";
  const low = Math.min(first, last), high = Math.max(first, last);
  const x0 = Math.min(anchor.xTwips, focus.xTwips), x1 = Math.max(anchor.xTwips + anchor.widthTwips, focus.xTwips + focus.widthTwips);
  const y0 = Math.min(anchor.yTwips, focus.yTwips), y1 = Math.max(anchor.yTwips + anchor.heightTwips, focus.yTwips + focus.heightTwips);
  return Object.freeze({part: anchor.part, anchor, focus, whole: kind, first, last,
    column: columns ? low : 0, endColumn: columns ? high : SHEET_COLUMNS - 1,
    row: rows ? low : 0, endRow: rows ? high : SHEET_ROWS - 1,
    xTwips: columns ? x0 : 0, widthTwips: columns ? x1 - x0 : Math.max(extent.widthTwips, x1),
    yTwips: rows ? y0 : 0, heightTwips: rows ? y1 - y0 : Math.max(extent.heightTwips, y1),
    multiple: true});
}

// SPEC-P-ms-formats 5.2: the formats a spreadsheet is saved in.  The engine's
// open reply names the one it accepted (E5); a Calc engine also reports `odt`
// for a document it opened under a .odt name (v4's path, spec 5.1 E1), which it
// cannot save as -- that document is saved as ODS, as it always was, and so is
// one from an engine that does not say (every profile before ods-editor-v5).
export const CALC_SAVE_FORMATS = Object.freeze(["ods", "xlsx"]);
export function calcDocumentFormatOf(document) {
  const format = document?.format;
  return CALC_SAVE_FORMATS.includes(format) ? format : "ods";
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
    this._zoom = 100;  // SPEC-P-calc-zoom: percent; the engine starts at 3840 twips per tile
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
      rangeStylingSupported:this.document?.rangeStylingSupported===true,
      headersSupported:this.document?.headersSupported===true,
      structureSupported:this.document?.structureSupported===true,
      copySupported:this.document?.copySupported===true,
      copyHtmlSupported:this.document?.copyHtmlSupported===true,
      zoomSupported:this.document?.zoomSupported===true, zoom:this._zoom,
      // SPEC-P-calc-sheets 2.3: another sheet than the edited (or selected) cell's is shown.
      away:this._cell!==null && this.viewer.state.currentPart!==this._cell.part,
      // SPEC-P-calc-sheets 2.1: which sheets are protected, from part-info (null when the engine could not say).
      partProtected:this.document?.partProtected ?? null,
      undoSupported:this.document?.undoSupported===true, draft: this._draft,
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
    // SPEC-P-calc-sheets 2.3: a formula written while another sheet is shown goes home first, then into its own cell.
    if (this.viewer.state.currentPart !== cell.part) await this.viewer.showPart(cell.part);
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
  _extent() {
    const size=this.scheduler?.documentCssSize ?? {width:0,height:0}, scale=this.viewer.scale ?? 1;
    return {widthTwips:Math.ceil(size.width*15/scale),heightTwips:Math.ceil(size.height*15/scale)};
  }
  _reselect(selected,anchor,focus) {
    return selected.whole ? wholeRectangle(selected.whole,selected.first,selected.last,anchor,focus,this._extent()) : rectangle(anchor,focus);
  }
  // SPEC-P-calc-headers 3.4: select whole columns first..last, whole rows, or the sheet ("sheet", 0, 0).
  selectWhole(kind,first,last,{valid=()=>true}={}) {
    return this._enqueue(async()=>{
      if(!["columns","rows","sheet"].includes(kind) || !Number.isInteger(first) || !Number.isInteger(last) || first<0 || last<0
          || first>=(kind==="rows" ? SHEET_ROWS : SHEET_COLUMNS) || last>=(kind==="rows" ? SHEET_ROWS : SHEET_COLUMNS))
        throw new DocumentSdkError("INVALID_ARGUMENT","a whole selection is columns, rows or the sheet, by index");
      if(this.document.headersSupported!==true)
        throw new DocumentSdkError("UNSUPPORTED_OPERATION","this engine has no header contract");
      if(!valid())return;
      await this._commitNow();
      if(kind==="sheet")first=last=0;
      const at=index=>kind==="rows" ? [0,index] : kind==="columns" ? [index,0] : [0,0];
      const {cell:anchor}=await this.document.readCell(...at(first));
      const focus=first===last ? anchor : (await this.document.readCell(...at(last))).cell;
      if(!valid())return;
      this._cell=anchor;this._draft=anchor.input;this._draftVersion++;this._editing=null;
      this._selection=wholeRectangle(kind,first,last,anchor,focus,this._extent());this._rangeFormat=null;
      this._emit();
      await this._refreshRangeFormat();
      return anchor;
    },{selection:true});
  }
  // SPEC-P-calc-headers 3.1: the visible headers, outside the edit queue (a read the bridge serves without selecting anything).
  readHeaders(rectangle) {
    if(this._closed || this.viewer.state.state!=="ready" || this.document?.headersSupported!==true)return Promise.resolve(null);
    return this.document.readHeaders(rectangle,{part:this.viewer.state.currentPart});
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
  // SPEC-P-calc-sheets 2.3: show another sheet while a formula is written, for its references.  Nothing is committed and
  // the edited cell, its draft and the selection stay; going back to the edited cell's own sheet is always allowed.
  browsePart(part) {
    return this._enqueue(async()=>{
      if(part!==this._cell?.part && !this._editing)
        throw new DocumentSdkError("INVALID_ARGUMENT","only a cell being edited can look at another sheet");
      if(this.viewer.state.currentPart!==part)await this.viewer.showPart(part);
      return this.state;
    },{selection:true});
  }
  // The cell under a point of the sheet shown, for a reference.  Read-only: nothing is committed or selected here.
  pointAt(xTwips,yTwips,{valid=()=>true}={}) {
    return this._enqueue(async()=>{
      if(!valid() || !this._editing)return null;
      const result=await this.document.hitCell(xTwips,yTwips);
      return valid() ? result.cell : null;
    },{selection:true});
  }
  // SPEC-P-calc-copy 3.2: the core's copy text for the selection.  A read: not a mutation, no revision moves.
  copySelection() {
    return this._enqueue(async()=>{
      if(!this.document?.copySupported)
        throw new DocumentSdkError("UNSUPPORTED_OPERATION","this engine has no copy contract");
      const range=this._selection ?? rectangle(this._cell);
      const {copy}=await this.document.copyRange(range.column,range.row,range.endColumn,range.endRow,{part:range.part});
      return {plainText:copy.plainText,htmlText:copy.htmlText ?? null,range};
    });
  }
  // SPEC-P-calc-zoom 2.7: the engine's zoom first (op 16), then the active cell and the selection's ends read again at it --
  // every rectangle in twips moves with the zoom -- then the tiles at the new scale for the size the engine gave.
  // `centre` ({column,row}, optional) is the cell under the viewport's centre: its rectangle before and after comes back as
  // {centre:{before,after}} so the page can put the same spot back in the centre (spec 2.6).  A rectangle at one zoom cannot
  // be scaled into another: rows are whole pixels at each zoom (spec 1).
  setZoom(percent,{centre=null}={}) {
    return this._enqueue(async()=>{
      if(!this.document?.zoomSupported)
        throw new DocumentSdkError("UNSUPPORTED_OPERATION","this engine has no zoom contract");
      if(!ZOOM_PERCENTS.includes(percent))
        throw new DocumentSdkError("INVALID_ARGUMENT","the zoom is not one of the levels");
      if(this._editing!==null)
        throw new DocumentSdkError("EDIT_IN_PROGRESS","finish or cancel the entry before zooming");
      const part=this.document.currentPart;
      const target=centre && Number.isInteger(centre.column) && Number.isInteger(centre.row) ? centre : null;
      const before=target ? (await this.document.readCell(target.column,target.row)).cell : null;
      const {zoom}=await this.document.setZoom(384000/percent,{part});
      this._zoom=percent;
      const after=target ? (await this.document.readCell(target.column,target.row)).cell : null;
      const selected=this._selection, cell=this._cell;
      if(cell && cell.part===part) {
        const anchor=(await this.document.readCell(cell.column,cell.row)).cell;
        let focus=anchor;
        if(selected?.focus && selected.part===part && (selected.focus.column!==cell.column || selected.focus.row!==cell.row))
          focus=(await this.document.readCell(selected.focus.column,selected.focus.row)).cell;
        this._cell=anchor;
        this._selection=selected?.part===part ? this._reselectAt(selected,anchor,focus,zoom) : rectangle(anchor);
      }
      this.viewer.setScale(percent/100,{widthTwips:zoom.widthTwips,heightTwips:zoom.heightTwips});
      this._emit();
      return {zoom:percent,centre:before && after ? {before,after} : null};
    },{selection:true});
  }
  _reselectAt(selected,anchor,focus,zoom) {
    return selected.whole ? wholeRectangle(selected.whole,selected.first,selected.last,anchor,focus,
      {widthTwips:zoom.widthTwips,heightTwips:zoom.heightTwips}) : rectangle(anchor,focus);
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
          this._cell=anchor;this._selection=this._reselect(selected,anchor,focus);this._rangeFormat=result.range;
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
          this._cell=anchor;this._selection=this._reselect(selected,anchor,focus);this._rangeFormat=result.range;
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
  // SPEC-P-calc-structure 2.2/2.5/3.2: what a structure change would do with the current selection, or why it cannot --
  // for the page's menu (enabled items, reasons) and for changeStructure itself.  `where` is "before" or "after" (insert).
  structurePlan(axis,action,where="before") {
    const selected=this._selection;
    if(this.document?.structureSupported!==true)return {refused:"UNSUPPORTED_OPERATION"};
    if(!selected)return {refused:"NOT_READY"};
    if(this._readOnly)return {refused:"READ_ONLY"};
    if(!["rows","columns"].includes(axis) || !["insert","delete"].includes(action) || !["before","after"].includes(where))
      return {refused:"INVALID_ARGUMENT"};
    const rows=axis==="rows", max=rows ? SHEET_ROWS : SHEET_COLUMNS;
    const low=rows ? selected.row : selected.column, high=rows ? selected.endRow : selected.endColumn;
    const count=high-low+1;
    if(count>=max)return {refused:"WHOLE_AXIS"};
    const index=action==="insert" && where==="after" ? high+1 : low;
    if(index+count>max)return {refused:"PAST_THE_END"};
    return {axis,action,where,index,count,part:selected.part};
  }
  changeStructure(axis,action,where="before") {
    return this._enqueue(async()=>{
      this._assertReady(true);
      const plan=this.structurePlan(axis,action,where);
      if(plan.refused)throw new DocumentSdkError(plan.refused==="UNSUPPORTED_OPERATION" || plan.refused==="READ_ONLY"
        ? plan.refused : "INVALID_ARGUMENT",`this structure change is not available: ${plan.refused}`);
      await this._commitNow();
      const selected=this._selection;
      const result=await this.document.changeStructure({axis,action,index:plan.index,count:plan.count},
        {part:plan.part,expectedRevision:this.document.revision});
      this.scheduler.invalidateRevision(this.document.revision);
      // 2.5: the same indices stay selected; the cells there are read again (they now hold other content).  A hidden row
      // or column reads like any other (its cursor is 14 twips: measured natively, spec append 3).
      try {
        const {cell:anchor}=await this.document.readCell(selected.anchor.column,selected.anchor.row,{part:selected.part});
        const {cell:focus}=await this.document.readCell(selected.focus.column,selected.focus.row,{part:selected.part});
        this._cell=anchor;this._selection=this._reselect(selected,anchor,focus);this._rangeFormat=null;
        this._draft=anchor.input;this._draftVersion++;this._editing=null;
        await this._refreshRangeFormat();
      } catch(error) {
        throw new DocumentSdkError("MUTATION_OUTCOME_UNKNOWN",`structure changed but the cell refresh failed: ${error.message}`);
      }
      this._emit();
      return {...result.structure,where,revision:result.revision};
    });
  }
  // SPEC-P-calc-undo 4.3 and 5.  An entry not yet sent is the newest change:
  // undo drops it and sends nothing (sending it first would only make the undo
  // take it back again).  Redo leaves it and answers {draftPending}.
  _draftPending() { return this._editing!==null && this._draft!==this._cell?.input; }
  undo() {
    if(this._draftPending()) {
      this.cancelEdit();
      return Promise.resolve({draftDiscarded:true});
    }
    return this._walk("undo");
  }
  redo() {
    if(this._draftPending())return Promise.resolve({draftPending:true});
    return this._walk("redo");
  }
  _walk(direction) {
    return this._enqueue(async()=>{
      this._assertReady();
      if(this._readOnly)throw new DocumentSdkError("READ_ONLY","this spreadsheet cannot be edited");
      if(this.document.undoSupported!==true)
        throw new DocumentSdkError("UNSUPPORTED_OPERATION","this engine has no document undo");
      // Codex review 3: an entry begun while this waited in the queue (behind a
      // save, say) was not the change this press meant; keep it, send nothing.
      if(this._draftPending())return {draftPending:true};
      this._editing=null;
      let result;
      try {
        result=await this.document[direction]({expectedRevision:this.document.revision});
      } catch(error) {
        // Refused before anything was dispatched: a sentence, not an error state.
        if(error.code===(direction==="undo" ? "NOTHING_TO_UNDO" : "NOTHING_TO_REDO"))return {nothing:direction};
        throw error;
      }
      this.scheduler.invalidateRevision(this.document.revision);
      // The engine's cell cursor moves to the restored cell for an input undo and
      // stays for an attribute undo (NU-2); the session follows a move only.  A
      // move to another sheet is answered {otherSheet}: the caller switches the
      // way a sheet tab does (showPart, then selectCell), so its own view of the
      // sheet left is kept (Codex review 5).
      const cursor=result.cursor;
      if(cursor?.moved===true && cursor.part!==this._cell.part)return {...result,otherSheet:true};
      try {
        if(cursor?.moved===true) {
          const {cell}=await this.document.readCell(cursor.column,cursor.row,{part:cursor.part});
          this._adopt(cell);
        } else if(this._selection?.multiple) {
          const selected=this._selection;
          const {cell:anchor}=await this.document.readCell(selected.anchor.column,selected.anchor.row,{part:selected.part});
          const {cell:focus}=await this.document.readCell(selected.focus.column,selected.focus.row,{part:selected.part});
          this._cell=anchor;this._selection=this._reselect(selected,anchor,focus);this._rangeFormat=null;
          this._draft=anchor.input;this._draftVersion++;
          await this._refreshRangeFormat();
        } else {
          const cell=this._cell;
          const {cell:refreshed}=await this.document.readCell(cell.column,cell.row,{part:cell.part});
          this._adopt(refreshed);
        }
      } catch(error) {
        throw new DocumentSdkError("MUTATION_OUTCOME_UNKNOWN",`${direction} applied but the cell refresh failed: ${error.message}`);
      }
      this._emit();
      return result;
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
        const format=this.documentFormat();
        const bytes=await this.document.save({format});
        const result=await target(bytes,{name:this.state.fileName,format});
        this._savedRevision=revision;
        return {bytes,result,revision};
      } catch (error) {
        if (error.outcome==="copy") this._savedRevision=revision;
        throw error;
      } finally { this._saving--;this._emit(); }
    });
  }
  /** SPEC-P-ms-formats 5.2: the format this document's saves are written in. */
  documentFormat() { return calcDocumentFormatOf(this.document); }
  /**
   * SPEC-P-ms-formats 5.2, Save As: the spreadsheet in `format`, as a copy.  In
   * the session's queue, after the draft is committed the way a save commits
   * it; NOT a save of this document: the saved revision does not move, so the
   * edits still count as unsaved.  What happens to the copy is the caller's.
   */
  saveCopy(format,target) {
    return this._enqueue(async()=>{
      this._assertReady();
      if (this._readOnly)
        throw new DocumentSdkError("READ_ONLY", "this spreadsheet cannot be saved");
      if (!CALC_SAVE_FORMATS.includes(format))
        throw new DocumentSdkError("INVALID_ARGUMENT", `a spreadsheet is not saved as ${format}`);
      await this._commitNow();
      this._saving++;this._emit();
      try {
        const bytes=await this.document.save({format});
        const result=await target(bytes,{format});
        return {bytes,result,format};
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
