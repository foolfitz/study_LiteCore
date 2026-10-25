// SPEC-M4-cell-editing-v1. Reuse the document/part protocol; keep Writer and
// the frozen read-only viewer contracts unchanged.
import { OdsViewerEngine } from "../viewer-shell/ods-document-sdk.js";
import { DocumentSdkError } from "../sdk/document-sdk.js";

export const CELL_FORMATS = Object.freeze(["bold", "italic", "underline"]);
export const CELL_INPUT_LIMIT = 32767;
export const RANGE_CELL_LIMIT = 65536;

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

function rangeBounds(column,row,endColumn,endRow) {
  for(const [key,value] of Object.entries({column,row,endColumn,endRow}))unsigned(value,key);
  if(endColumn<column || endRow<row)invalid("range endpoints are reversed");
  if((endColumn-column+1)*(endRow-row+1)>RANGE_CELL_LIMIT)
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
  rangeBounds(range.column,range.row,range.endColumn,range.endRow);
  for(const key of CELL_FORMATS) {
    if(!["on","off","mixed"].includes(raw[key]))
      throw new DocumentSdkError("CELL_RESULT_INVALID",`range ${key} is not a tristate`);
    range[key]=raw[key]==="mixed" ? null : raw[key]==="on";
  }
  range.writable=boolean(raw.writable,"writable");
  if(typeof raw.refusalCode!=="string" || range.writable!==(raw.refusalCode===""))
    throw new DocumentSdkError("CELL_RESULT_INVALID","range refusal does not match writability");
  range.refusalCode=raw.refusalCode;
  return Object.freeze(range);
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
        if(operation==="rangeFormat")throw new DocumentSdkError("MUTATION_OUTCOME_UNKNOWN",error.message);
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
    const rangeRequest=(operation,column,row,endColumn,endRow,payload,callOptions)=>{
      if(!handle.rangeFormattingSupported)
        throw new DocumentSdkError("UNSUPPORTED_OPERATION","this engine has no range formatting contract");
      rangeBounds(column,row,endColumn,endRow);
      return request(operation,column,row,{endColumn,endRow,...payload},callOptions,normalizeRange)
        .then(({cell,changed,revision})=>({range:cell,changed,revision}));
    };
    handle.readRange=(column,row,endColumn,endRow,callOptions)=>
      rangeRequest("rangeRead",column,row,endColumn,endRow,{},callOptions);
    handle.setRangeFormat=(column,row,endColumn,endRow,format,enabled,callOptions)=>{
      if(!CELL_FORMATS.includes(format) || typeof enabled!=="boolean")invalid("invalid range format");
      return rangeRequest("rangeFormat",column,row,endColumn,endRow,{format,enabled},callOptions);
    };
    return handle;
  }
}
