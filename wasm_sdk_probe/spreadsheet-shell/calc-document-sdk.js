// SPEC-M4-cell-editing-v1. Reuse the document/part protocol; keep Writer and
// the frozen read-only viewer contracts unchanged.
import { OdsViewerEngine } from "../viewer-shell/ods-document-sdk.js";
import { DocumentSdkError } from "../sdk/document-sdk.js";

export const CELL_FORMATS = Object.freeze(["bold", "italic", "underline"]);
// SPEC-P-demo-batch-3 3.1.  Colours are lower-case #rrggbb; "auto" and "none" are not colours.
export const CELL_STYLES = Object.freeze({
  textColor: value => value === "auto" || /^#[0-9a-f]{6}$/.test(value),
  backColor: value => value === "none" || /^#[0-9a-f]{6}$/.test(value),
  horizontalAlign: value => ["standard", "left", "center", "right", "block"].includes(value),
});
export const CELL_INPUT_LIMIT = 32767;
export const RANGE_CELL_LIMIT = 65536;
// SPEC-P-calc-headers 3.2: a sheet's fixed size (no jumbo sheets); whole columns, rows and the sheet pass the cell limit.
export const SHEET_COLUMNS = 16384;
export const SHEET_ROWS = 1048576;
export const HEADER_RECTANGLE_LIMIT = 245760;  // twips per side, the bridge's limit

export function isWholeRange(column,row,endColumn,endRow) {
  return (row===0 && endRow===SHEET_ROWS-1) || (column===0 && endColumn===SHEET_COLUMNS-1);
}

function invalid(message) {
  throw new DocumentSdkError("INVALID_ARGUMENT", message);
}

function unsigned(value, name) {
  if (!Number.isInteger(value) || value < 0 || value > 0x7fffffff)
    invalid(`${name} must be a non-negative integer`);
  return value;
}

function boolean(value, name) {
  if (value === true || value === "true") return true;
  if (value === false || value === "false") return false;
  throw new DocumentSdkError("CELL_RESULT_INVALID", `${name} is not a boolean`);
}

// An engine without the style contract sends none of these keys; one with it sends all three.
function styleSnapshot(target,raw,allowMixed) {
  if(Object.keys(CELL_STYLES).every(key=>raw[key]===undefined))return;
  for(const key of Object.keys(CELL_STYLES)) {
    if(allowMixed && raw[key]==="mixed") {target[key]=null;continue;}
    // A document can hold what the buttons cannot set (REPEAT reads "other").
    if(!(CELL_STYLES[key](raw[key]) || (key==="horizontalAlign" && raw[key]==="other")))
      throw new DocumentSdkError("CELL_RESULT_INVALID",`${key} is not a style value`);
    target[key]=raw[key];
  }
}

function rangeBounds(column,row,endColumn,endRow,allowWhole=false) {
  for(const [key,value] of Object.entries({column,row,endColumn,endRow}))unsigned(value,key);
  if(endColumn<column || endRow<row)invalid("range endpoints are reversed");
  if((endColumn-column+1)*(endRow-row+1)>RANGE_CELL_LIMIT && !(allowWhole && isWholeRange(column,row,endColumn,endRow)))
    throw new DocumentSdkError("RANGE_TOO_LARGE",`range exceeds ${RANGE_CELL_LIMIT} logical cells`);
  return {column,row,endColumn,endRow};
}

export function normalizeRange(raw) {
  if(!raw || typeof raw!=="object")invalid("range reply is missing");
  const range={};
  for(const key of ["part","column","row","endColumn","endRow"]) {
    if(typeof raw[key]!=="number" && !(typeof raw[key]==="string" && /^[0-9]+$/.test(raw[key])))
      throw new DocumentSdkError("CELL_RESULT_INVALID",`range ${key} is not an integer`);
    range[key]=unsigned(Number(raw[key]),key);
  }
  rangeBounds(range.column,range.row,range.endColumn,range.endRow,true);
  for(const key of CELL_FORMATS) {
    if(!["on","off","mixed"].includes(raw[key]))
      throw new DocumentSdkError("CELL_RESULT_INVALID",`range ${key} is not a tristate`);
    range[key]=raw[key]==="mixed" ? null : raw[key]==="on";
  }
  range.writable=boolean(raw.writable,"writable");
  if(typeof raw.refusalCode!=="string" || range.writable!==(raw.refusalCode===""))
    throw new DocumentSdkError("CELL_RESULT_INVALID","range refusal does not match writability");
  range.refusalCode=raw.refusalCode;
  styleSnapshot(range,raw,true);
  return Object.freeze(range);
}

// SPEC-P-calc-headers 3.1/3.3: the bridge's op 13 reply, closed.  An empty array arrives as "" (boost's JSON writer).
export function normalizeHeaders(raw) {
  if(!raw || typeof raw!=="object")throw new DocumentSdkError("CELL_RESULT_INVALID","header reply is missing");
  const integer=(value,name)=>{
    if(typeof value!=="number" && !(typeof value==="string" && /^[0-9]+$/.test(value)))
      throw new DocumentSdkError("CELL_RESULT_INVALID",`${name} is not an integer`);
    return unsigned(Number(value),name);
  };
  const out={part:integer(raw.part,"part"),maxColumns:integer(raw.maxColumns,"maxColumns"),maxRows:integer(raw.maxRows,"maxRows")};
  if(out.maxColumns!==SHEET_COLUMNS || out.maxRows!==SHEET_ROWS)
    throw new DocumentSdkError("CELL_RESULT_INVALID","the sheet is not 16384 x 1048576 (jumbo sheets are a named limit)");
  for(const [axis,label] of [["columns",/^[A-Z]+$/],["rows",/^[1-9][0-9]*$/]]) {
    const list=raw[axis]==="" ? [] : raw[axis];
    if(!Array.isArray(list))throw new DocumentSdkError("CELL_RESULT_INVALID",`${axis} is not a list`);
    let previous=null;
    out[axis]=Object.freeze(list.map(entry=>{
      const e={index:integer(entry?.index,"index"),label:entry?.label,startPx:integer(entry?.startPx,"startPx"),
        endPx:integer(entry?.endPx,"endPx"),hidden:boolean(entry?.hidden,"hidden")};
      if(typeof e.label!=="string" || !label.test(e.label) || e.startPx>e.endPx || e.hidden!==(e.startPx===e.endPx)
          || (previous && (e.index!==previous.index+1 || e.startPx!==previous.endPx))
          || e.index>=(axis==="columns" ? out.maxColumns : out.maxRows))
        throw new DocumentSdkError("CELL_RESULT_INVALID",`${axis} entries are not one closed run`);
      previous=e;
      return Object.freeze(e);
    }));
  }
  return Object.freeze(out);
}

export function normalizeCell(raw) {
  if (!raw || typeof raw !== "object")
    throw new DocumentSdkError("CELL_RESULT_INVALID", "cell reply has no model snapshot");
  const cell = {};
  for (const key of ["part", "column", "row", "endColumn", "endRow", "xTwips", "yTwips", "widthTwips", "heightTwips", "cellType"]) {
    if (typeof raw[key] !== "number" && !(typeof raw[key] === "string" && /^[0-9]+$/.test(raw[key])))
      throw new DocumentSdkError("CELL_RESULT_INVALID", `${key} is not an integer`);
    cell[key] = unsigned(Number(raw[key]), key);
  }
  if (cell.widthTwips === 0 || cell.heightTwips === 0
      || cell.endColumn < cell.column || cell.endRow < cell.row)
    throw new DocumentSdkError("CELL_RESULT_INVALID", "cell reply has invalid geometry");
  for (const key of ["formula", "input", "text"]) {
    if (typeof raw[key] !== "string")
      throw new DocumentSdkError("CELL_RESULT_INVALID", `${key} is not text`);
    cell[key] = raw[key];
  }
  for (const key of ["writable", "bold", "boldAsian", "boldComplex", "italic", "italicAsian", "italicComplex", "underline"])
    cell[key] = boolean(raw[key], key);
  cell.value = Number(raw.value);
  if (raw.value === "" || raw.value === null || !Number.isFinite(cell.value))
    throw new DocumentSdkError("CELL_RESULT_INVALID", "cell value is not finite");
  styleSnapshot(cell, raw, false);
  return Object.freeze(cell);
}

export class CalcDocumentEngine extends OdsViewerEngine {
  async open(input, options = {}) {
    for (const capability of ["cell-editing", "save-ods"])
      if (!this.manifest?.capabilities?.includes(capability))
        throw new DocumentSdkError("UNSUPPORTED_OPERATION", `spreadsheet editing requires ${capability}`);
    const handle = await super.open(input, options);
    if (handle.documentType !== "spreadsheet") {
      await handle.close();
      throw new DocumentSdkError("DOCUMENT_TYPE_REFUSED", "cell editing requires a spreadsheet");
    }
    const request = async (operation, column, row, payload = {}, callOptions = {}, normalize = normalizeCell) => {
      handle._assertUsable();
      const expectedRevision = callOptions.expectedRevision ?? handle.revision;
      if (!Number.isInteger(expectedRevision) || expectedRevision < 0 || expectedRevision > 0xffffffff)
        invalid("expectedRevision must be an unsigned 32-bit integer");
      const result = await this._request(operation, {
        documentHandle: handle.handle, expectedRevision,
        part: unsigned(callOptions.part ?? handle.currentPart, "part"),
        column: unsigned(column, "column"), row: unsigned(row, "row"), ...payload,
      }, callOptions);
      let cell;
      try {
        cell=normalize(result.cell);
        if(operation.startsWith("range") && (cell.part!==(callOptions.part ?? handle.currentPart)
            || cell.column!==column || cell.row!==row || cell.endColumn!==payload.endColumn || cell.endRow!==payload.endRow))
          throw new DocumentSdkError("CELL_RESULT_INVALID","range reply target differs from request");
      } catch(error) {
        if(operation==="rangeFormat" || operation==="rangeStyle")throw new DocumentSdkError("MUTATION_OUTCOME_UNKNOWN",error.message);
        throw error;
      }
      handle.revision = result.revision;
      return { cell, changed: result.changed === true, revision: result.revision };
    };
    handle.readCell = (column, row, callOptions) => request("cellRead", column, row, {}, callOptions);
    handle.hitCell = (xTwips, yTwips, callOptions) => request("cellHit", xTwips, yTwips, {}, callOptions);
    handle.setCellInput = (column, row, text, callOptions) => {
      if (typeof text !== "string") invalid("cell input must be text");
      if (text.length > CELL_INPUT_LIMIT)
        throw new DocumentSdkError("CELL_TEXT_TOO_LONG", `cell input exceeds ${CELL_INPUT_LIMIT} UTF-16 code units`);
      return request("cellInput", column, row, {text}, callOptions);
    };
    handle.setCellFormat = (column, row, format, enabled, callOptions) => {
      if (!CELL_FORMATS.includes(format) || typeof enabled !== "boolean")
        invalid("cell format must be bold, italic or underline and enabled must be boolean");
      return request("cellFormat", column, row, {format, enabled}, callOptions);
    };
    handle.rangeFormattingSupported=this.manifest.capabilities.includes("cell-range-formatting");
    // SPEC-P-calc-headers: op 13 and whole ranges ride on one capability.
    handle.headersSupported=this.manifest.capabilities.includes("cell-headers");
    handle.readHeaders=(rectangle,callOptions)=>{
      if(!handle.headersSupported)
        throw new DocumentSdkError("UNSUPPORTED_OPERATION","this engine has no header contract");
      const r=rectangle ?? {};
      for(const key of ["x","y","width","height"])unsigned(r[key],key);
      if((r.width===0 && r.height===0) || r.width>HEADER_RECTANGLE_LIMIT || r.height>HEADER_RECTANGLE_LIMIT)
        invalid("invalid header rectangle");
      return request("cellHeaders",0,0,{rectangle:{x:r.x,y:r.y,width:r.width,height:r.height}},callOptions,normalizeHeaders)
        .then(({cell,revision})=>{
          if(cell.part!==(callOptions?.part ?? handle.currentPart))
            throw new DocumentSdkError("CELL_RESULT_INVALID","header reply part differs from request");
          return {headers:cell,revision};
        });
    };
    const rangeRequest=(operation,column,row,endColumn,endRow,payload,callOptions)=>{
      if(!handle.rangeFormattingSupported)
        throw new DocumentSdkError("UNSUPPORTED_OPERATION","this engine has no range formatting contract");
      rangeBounds(column,row,endColumn,endRow,handle.headersSupported);
      return request(operation,column,row,{endColumn,endRow,...payload},callOptions,normalizeRange)
        .then(({cell,changed,revision})=>({range:cell,changed,revision}));
    };
    handle.readRange=(column,row,endColumn,endRow,callOptions)=>
      rangeRequest("rangeRead",column,row,endColumn,endRow,{},callOptions);
    handle.setRangeFormat=(column,row,endColumn,endRow,format,enabled,callOptions)=>{
      if(!CELL_FORMATS.includes(format) || typeof enabled!=="boolean")invalid("invalid range format");
      return rangeRequest("rangeFormat",column,row,endColumn,endRow,{format,enabled},callOptions);
    };
    // SPEC-P-calc-undo 4.3: undo and redo are DocumentHandle's own (document-sdk.js); the worker refuses them without
    // the `undo` capability, and the page shows its buttons only when this is true.
    handle.undoSupported=this.manifest.capabilities.includes("undo");
    handle.rangeStylingSupported=this.manifest.capabilities.includes("cell-range-styling");
    handle.setRangeStyle=(column,row,endColumn,endRow,style,value,callOptions)=>{
      if(!handle.rangeStylingSupported)
        throw new DocumentSdkError("UNSUPPORTED_OPERATION","this engine has no cell style contract");
      if(!Object.hasOwn(CELL_STYLES,style) || !CELL_STYLES[style](value))invalid("invalid cell style");
      return rangeRequest("rangeStyle",column,row,endColumn,endRow,{style,value},callOptions);
    };
    return handle;
  }
}
