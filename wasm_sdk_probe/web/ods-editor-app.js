import { CalcDocumentEngine, CELL_INPUT_LIMIT, ZOOM_PERCENTS } from "./spreadsheet-shell/calc-document-sdk.js";
import { CalcEditorSession, inputIntent, parseCellTarget, referenceSlot, sheetReference }
  from "./spreadsheet-shell/calc-editor-session.js";
import { CalcAutosave } from "./spreadsheet-shell/calc-autosave.js";

const ENGINE_OPTIONS = Object.freeze({workerUrl:"./profiles/ods-editor-v8/sdk-worker.js",timeoutMs:60000});
const HOST = globalThis.liteCoreHost ?? null;
const diagnostics = new URLSearchParams(location.search).get("diagnostics") === "1";
const $ = id => document.getElementById(id);
const ui = Object.fromEntries(["file-input","open-file","save-button","undo-button","redo-button","cell-address","formula-input",
  "cancel-button","commit-button","viewport","surface","tiles","selection","active-cell","cell-editor","empty",
  "tab-strip","state-pill","autosave-status","selection-label","s-doc","s-revision","toast",
  "save-as-button","save-as-dialog","save-as-name","save-as-suffix","save-as-formats","save-as-message","save-as-cancel",
  "save-as-confirm","sheet-frame","corner-header","column-headers","row-headers","reference-box","sheet-position",
  "zoom-out","zoom-level","zoom-in"]
  .map(id=>[id,$(id)]));
// SPEC-P-ms-formats 5.2: what each format this page writes is called and carries. A spreadsheet is saved in ITS format
// (the session's documentFormat(), from the engine's open reply); Save As offers ODF, and the original for an XLSX.
const CALC_FORMATS=Object.freeze({ods:{suffix:".ods",mime:"application/vnd.oasis.opendocument.spreadsheet"},
  xlsx:{suffix:".xlsx",mime:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}});
// A Save As the host placed: it is opening the new file and the original's lock is being let go (spec 5.3).
let handedOver=false;
let session = null, composing = false, paintPending = false, paintAgain = false, lastPaint = null, restoreGridFocus = false;
let pendingEntry = null, autosave = null, manualSaves = 0;
// SPEC-P-demo-batch-1 2: each sheet keeps its view for as long as the document
// is open. A switch does not paint until the session has settled on the new
// sheet, and `pendingView` is applied inside paint, after the surface has its
// new size: scrolling first would clamp to the sheet being left.
const sheetViews = new Map();
let sheetSwitching = false, pendingView = null, zooming = false;
const record = globalThis.__calcEditor = {schemaVersion:1,session:null,state:null,events:[],lastSave:null,lastCopy:null,
  get zoom(){return session?.state.zoom ?? null;}};
if(diagnostics)record.inputState=()=>({composing,pending:pendingEntry ? {replace:pendingEntry.replace,invalid:pendingEntry.invalid===true,textLength:pendingEntry.text.length}:null});

function cellAddress(column,row) {
  let text="";
  for(let n=column;n>=0;n=Math.floor(n/26)-1) text=String.fromCharCode(65+n%26)+text;
  return text+(row+1);
}
function columnName(column){return cellAddress(column,0).replace(/[0-9]+$/,"");}
// SPEC-P-calc-headers 3.4: the header strips cover the viewport's top and left edges; the surface shows what is left.
const HEADER_LEFT=48,HEADER_TOP=20;
// SPEC-P-calc-zoom 3.3: twips per CSS px at the view's zoom (15 at 100%).  Every rectangle the engine gives is in twips of the
// layout at that zoom, so dividing by tw() lands on the tiles drawn at it.
function zoomScale(){return (session?.state.zoom ?? 100)/100;}
function tw(){return 15/zoomScale();}
function headersOn(){return session?.state.headersSupported===true;}
function visibleWidth(){return Math.max(1,ui.viewport.clientWidth-(headersOn() ? HEADER_LEFT : 0));}
function visibleHeight(){return Math.max(1,ui.viewport.clientHeight-(headersOn() ? HEADER_TOP : 0));}
function selectionText(range,address) {
  if(range?.whole==="sheet")return `全部儲存格 · 作用中 ${address}`;
  if(range?.whole==="columns")return `${columnName(range.column)}:${columnName(range.endColumn)} · 作用中 ${address}`;
  if(range?.whole==="rows")return `${range.row+1}:${range.endRow+1} · 作用中 ${address}`;
  return null;
}
function notice(text,error=false) {
  ui.toast.textContent=text;
  ui.toast.classList.toggle("error",error);
}
// SPEC-P-calc-sheets 2.3-2.4: pointed references.  `pointRef` is the span of the draft the last point inserted
// ({start, end, text}); `pointBox` the range it names, drawn on its own sheet.  `browsing` is a formula being written while
// another sheet than its cell's is shown; `away` is that sheet being shown at all (also for the moment after an Esc).
let pointRef=null, pointBox=null, pointWork=null, pointBusy=0, pointed=false, tabSlot=null;
const BROWSING_NOTICE="正在別張工作表上點選參照：請先按 Enter 完成，或按 Esc 取消公式的輸入。";
const HOME_VIEW=Object.freeze({scrollLeft:0,scrollTop:0,minWidth:"",minHeight:""});
function away(state=session?.state){return state?.away===true;}
function browsing(state=session?.state){return away(state) && state.editing!==null;}
function sheetNames(state){const names=[];for(const tab of state.tabs)names[tab.index]=tab.label;return names;}
function draftField() {
  const active=document.activeElement;
  return active===ui["formula-input"] || (active===ui["cell-editor"] && session?.state.editing==="inline") ? active : null;
}
function pointSlot() {
  const s=session?.state;
  if(!s || s.state!=="ready" || !s.editing || pendingEntry || composing || s.readOnly || s.cell?.writable!==true)return null;
  const field=draftField();
  if(!field)return null;
  const slot=referenceSlot(s.draft,field.selectionStart,field.selectionEnd,pointRef);
  return slot ? {...slot,field} : null;
}
function insertReference(slot,text) {
  const draft=session.state.draft,next=draft.slice(0,slot.start)+text+draft.slice(slot.end);
  session.setDraft(next);
  pointRef={start:slot.start,end:slot.start+text.length,text};
  const field=slot.field===ui["cell-editor"] && !browsing() ? ui["cell-editor"] : ui["formula-input"];
  field.value=next;field.focus({preventScroll:true});field.setSelectionRange(pointRef.end,pointRef.end);
}
function errorNotice(error) {
  const messages={READ_ONLY:"這個儲存格無法編輯。",CELL_TEXT_TOO_LONG:"儲存格內容超過 32,767 個字元，尚未寫入。",
    STALE_REVISION:"文件狀態已改變；你的輸入已保留，請先儲存或重新開啟。",
    MUTATION_OUTCOME_UNKNOWN:"無法確認剛才的修改，請保留此頁，避免遺失內容。",
    PART_HIDDEN:"這張工作表已隱藏。",RANGE_FORMAT_UNSUPPORTED:"目前的引擎尚未支援範圍格式。",
    RANGE_TOO_LARGE:"一次最多可設定 65,536 個儲存格的格式，請縮小選取範圍。",
    RANGE_MERGE_BOUNDARY:"選取範圍跨過合併格邊界，請選取完整的合併格後重試。",
    RANGE_PROTECTED:"選取範圍含有受保護的儲存格，無法變更格式。",
    STRUCTURE_REFUSED:"LibreOffice 拒絕了這個插入或刪除：資料會被推出工作表、會切開陣列公式，或範圍被鎖定。文件沒有變動。"};
  notice(messages[error.code] || error.message || String(error),true);
}
function autosaveState(state) {
  ui["autosave-status"].hidden=!state.enabled;
  ui["autosave-status"].textContent=state.paused ? "自動儲存已暫停，請手動儲存" : state.saving ? "自動儲存中…"
    : state.draft ? "編輯中（確認後自動儲存）" : "自動儲存已開啟";
  ui["autosave-status"].classList.toggle("error",!!state.paused);
}
async function action(work) {
  try { return await work(); } catch(error) { errorNotice(error); return null; }
}
function place(node,cell) {
  const t=tw();
  node.style.left=`${cell.xTwips/t}px`;node.style.top=`${cell.yTwips/t}px`;
  node.style.width=`${Math.max(1,cell.widthTwips/t)}px`;
  node.style.height=`${Math.max(1,cell.heightTwips/t)}px`;
}
function formatAvailable(state) {
  return state.state==="ready" && state.cell?.writable===true && !state.readOnly && !state.uncertain
    && !state.busy && !state.selectionPending && !pendingEntry && !dragWork && !state.away
    && (!state.selection?.multiple || (state.rangeFormattingSupported===true && state.rangeFormat?.writable===true));
}
function formatTitle(state,node) {
  const multiple=state.selection?.multiple,range=state.rangeFormat;
  return multiple && !state.rangeFormattingSupported ? "目前的引擎尚未支援範圍格式。"
    : multiple && range?.refusalCode ? formatRefusal(range.refusalCode) : node.getAttribute("aria-label");
}
function renderFormatControls(state) {
  for(const node of document.querySelectorAll("[data-format]")) {
    const multiple=state.selection?.multiple,range=state.rangeFormat;
    const value=multiple ? range?.[node.dataset.format] : state.cell?.[node.dataset.format];
    node.disabled=!formatAvailable(state);
    node.setAttribute("aria-pressed",multiple && value==null ? "mixed" : value ? "true":"false");
    node.title=formatTitle(state,node);
  }
  // Here and not in render(): a drag ends by calling this alone, and the styles must come back with the formats.
  renderStyleControls(state);
  // So must the zoom group, which a drag disables too (SPEC-P-calc-zoom append 3, Codex review 3).
  renderZoom(state);
}
// SPEC-P-demo-batch-3 3.3.  Ten columns, dark to light: Collabora's picker's base colours and shades (browser/src/control/ColorPicker.ts).
const COLOR_ROWS=Object.freeze([
  ["#000000","#5b0f00","#660000","#783f04","#7f6000","#274e13","#0c343d","#073763","#20124d","#4c1130"],
  ["#434343","#85200c","#990000","#b45f06","#bf9000","#38761d","#134f5c","#0b5394","#351c75","#741b47"],
  ["#666666","#a61c00","#cc0000","#e69138","#f1c232","#6aa84f","#45818e","#3d85c6","#674ea7","#a64d79"],
  ["#888888","#980000","#ff0000","#ff9900","#ffff00","#00ff00","#00ffff","#0000ff","#9900ff","#ff00ff"],
  ["#bbbbbb","#cc4125","#e06666","#f6b26b","#ffd966","#93c47d","#76a5af","#6fa8dc","#8e7cc3","#c27ba0"],
  ["#dddddd","#dd7e6b","#ea9999","#f9cb9c","#ffe599","#b6d7a8","#a2c4c9","#9fc5e8","#b4a7d6","#d5a6bd"],
  ["#ffffff","#e6b8af","#f4cccc","#fce5cd","#fff2cc","#d9ead3","#d0e0e3","#cfe2f3","#d9d2e9","#ead1dc"],
]);
const lastColor={textColor:"#ff0000",backColor:"#ffff00"};
const COLOR_NONE={textColor:["auto","自動"],backColor:["none","無填滿"]};
const colorPopover=$("color-popover"),colorClear=$("color-clear"),colorGrid=$("color-grid");
let colorTarget=null;
for(const color of COLOR_ROWS.flat()) {
  const swatch=document.createElement("button");
  swatch.type="button";swatch.dataset.swatch=color;swatch.style.background=color;
  swatch.setAttribute("aria-label",color);swatch.title=color;colorGrid.append(swatch);
}
function closeColorPopover(returnFocus=false) {
  if(colorTarget===null)return;
  const menu=document.querySelector(`[data-color-menu="${colorTarget}"]`);
  menu.setAttribute("aria-expanded","false");
  colorPopover.hidden=true;colorTarget=null;
  if(returnFocus)menu.focus();
}
function openColorPopover(key) {
  const reopen=colorTarget===key;
  closeColorPopover();
  if(reopen)return;
  const menu=document.querySelector(`[data-color-menu="${key}"]`),box=menu.getBoundingClientRect();
  colorTarget=key;menu.setAttribute("aria-expanded","true");
  colorClear.textContent=COLOR_NONE[key][1];
  colorPopover.hidden=false;
  colorPopover.style.left=`${Math.max(8,Math.min(box.left,innerWidth-colorPopover.offsetWidth-8))}px`;
  colorPopover.style.top=`${box.bottom+4}px`;
  colorClear.focus();
}
function applyStyle(style,value) {
  if(pendingEntry){notice("請先完成或取消目前的輸入。",true);return;}
  if(!session || !formatAvailable(session.state))return;
  void action(async()=>{await session.setStyle(style,value);focusGrid();});
}
function renderSwatch(key) {
  document.querySelector(`[data-color="${key}"] .swatch-bar`).style.setProperty("--swatch",lastColor[key]);
}
function pickColor(value) {
  const key=colorTarget;
  if(value!==COLOR_NONE[key][0]){lastColor[key]=value;renderSwatch(key);}
  closeColorPopover();
  applyStyle(key,value);
}
function currentStyle(state,key) {
  return state.selection?.multiple ? state.rangeFormat?.[key] : state.cell?.[key];
}
function renderStyleControls(state) {
  const supported=state.rangeStylingSupported===true;
  for(const node of document.querySelectorAll("[data-style-group]"))node.hidden=!supported;
  if(!supported){closeColorPopover();return;}
  const available=formatAvailable(state);
  if(!available)closeColorPopover();
  for(const node of document.querySelectorAll("[data-color],[data-color-menu]")) {
    node.disabled=!available;
    node.title=formatTitle(state,node);
  }
  const align=currentStyle(state,"horizontalAlign");
  for(const node of document.querySelectorAll("[data-align]")) {
    node.disabled=!available;
    node.title=formatTitle(state,node);
    node.setAttribute("aria-pressed",state.selection?.multiple && align===null ? "mixed" : align===node.dataset.align ? "true":"false");
  }
}
function render(state) {
  restoreGridFocus ||= document.activeElement===ui["cell-editor"];
  record.state=state;
  const ready=state.state==="ready";
  const editable=ready && !state.readOnly && state.cell?.writable && !state.uncertain;
  const waiting=state.busy && !state.saving;
  ui["state-pill"].dataset.state=state.state;
  ui["state-pill"].textContent=!ready ? ({opening:"開啟中…",error:"開啟失敗",closed:"已關閉"}[state.state]||"尚未開啟")
    : state.saving ? "儲存中…" : state.readOnly ? "唯讀" : state.dirty ? "尚未儲存" : "已儲存";
  ui["s-doc"].textContent=state.fileName || "";
  ui["s-revision"].textContent=String(state.revision ?? "");
  ui.empty.hidden=ready;
  ui["save-button"].disabled=!ready || state.readOnly || state.busy || state.uncertain;
  // SPEC-P-ms-formats 5.2: no Save As on a read-only document (L-saveas-readonly) or with a host that cannot place a file.
  ui["save-as-button"].hidden=!ready || !saveAsOffered(state);
  ui["save-as-button"].disabled=ui["save-button"].disabled || handedOver;
  // SPEC-P-calc-undo 4.3: shown when the profile carries undo; usable whenever a write would be, and with an entry
  // pending too (undo then drops the entry).
  ui["undo-button"].hidden=ui["redo-button"].hidden=!state.undoSupported;
  ui["undo-button"].disabled=ui["redo-button"].disabled=!ready || state.readOnly || state.uncertain || waiting
    || state.selectionPending;
  ui["cell-address"].disabled=!ready || state.busy;
  // A point or a sheet shown for one keeps the formula bar, which holds the caret (SPEC-P-calc-sheets 2.4).
  ui["formula-input"].disabled=!editable || (waiting && pointBusy===0);
  ui["cell-editor"].disabled=state.selectionPending || pendingEntry
    ? !ready || state.readOnly || state.uncertain : !editable || waiting;
  ui["commit-button"].disabled=!editable || !state.editing || waiting;
  ui["cancel-button"].disabled=!state.editing || waiting;
  renderFormatControls(state);
  if(!composing) {
    if(ui["formula-input"].value!==state.draft)ui["formula-input"].value=state.draft;
    if(!pendingEntry && ui["cell-editor"].value!==state.draft)ui["cell-editor"].value=state.draft;
  }
  ui.selection.hidden=!ready || !state.cell || away(state);
  ui["active-cell"].hidden=ui.selection.hidden;
  ui["cell-editor"].hidden=!ready || !state.cell || away(state);
  if(!state.editing){pointRef=null;pointBox=null;}
  const showBox=pointBox && pointRef && pointBox.part===state.currentPart && state.draft.slice(pointRef.start,pointRef.end)===pointRef.text;
  ui["reference-box"].hidden=!showBox;
  if(showBox)place(ui["reference-box"],pointBox);
  // SPEC-P-calc-sheets 2.1: the sheet's position, as Collabora's status bar has it.
  ui["sheet-position"].textContent=ready && state.tabs.length ? `工作表 ${state.currentPart+1}／${state.tabs.length}` : "";
  ui["cell-editor"].classList.toggle("grid-input",state.editing!=="inline");
  if(state.cell) {
    const address=cellAddress(state.cell.column,state.cell.row);
    if(document.activeElement!==ui["cell-address"])ui["cell-address"].value=address;
    const range=state.selection;
    ui["selection-label"].textContent=selectionText(range,address) ?? (range?.multiple
      ? `${cellAddress(range.column,range.row)}:${cellAddress(range.endColumn,range.endRow)} · 作用中 ${address}${state.rangeFormattingSupported ? "" : "（範圍格式尚未支援）"}` : address);
    ui["selection-label"].title="範圍依兩端儲存格框選；交界合併格不自動擴張。";
    place(ui.selection,range || state.cell);place(ui["active-cell"],state.cell);place(ui["cell-editor"],state.cell);
    if(state.editing!=="inline") {
      // A focused, real textarea receives beforeinput and IME without moving
      // focus midway through the first character. Keep its idle caret in view.
      ui["cell-editor"].style.left=`${Math.max(ui.viewport.scrollLeft,Math.min(state.cell.xTwips/tw(),ui.viewport.scrollLeft+visibleWidth()-4))}px`;
      ui["cell-editor"].style.top=`${Math.max(ui.viewport.scrollTop,Math.min(state.cell.yTwips/tw(),ui.viewport.scrollTop+visibleHeight()-4))}px`;
      if(!composing && !pendingEntry)ui["cell-editor"].value="";
    }
  }
  const signature=state.tabs.map(t=>`${t.index}:${t.current}:${t.enabled}:${state.partProtected?.[t.index]===true}`).join("|");
  if(ui["tab-strip"].dataset.signature!==signature) {
    ui["tab-strip"].dataset.signature=signature;
    ui["tab-strip"].replaceChildren(...state.tabs.map(tab=>{
      const button=document.createElement("button");button.type="button";button.className="sheet-tab";
      button.textContent=tab.label;button.dataset.part=tab.index;button.setAttribute("role","tab");
      button.setAttribute("aria-selected",String(tab.current));button.disabled=!tab.enabled;
      button.title=tab.disabledReason || "";
      // SPEC-P-calc-sheets 2.1: a protected sheet's tab carries a lock and says so.
      if(state.partProtected?.[tab.index]===true) {
        button.insertAdjacentHTML("beforeend",'<svg class="lock" aria-hidden="true" focusable="false"><use href="#i-lock"></use></svg>');
        button.dataset.protected="true";button.setAttribute("aria-label",`${tab.label}（受保護的工作表）`);
        if(!button.title)button.title="受保護的工作表";
      }
      // SPEC-P-calc-sheets 2.3: with the caret where a reference can go, a tab only shows its sheet.  The slot is read on
      // pointerdown, while the formula still has the focus.
      button.addEventListener("pointerdown",event=>{tabSlot=event.button===0 ? pointSlot() : null;if(tabSlot)event.preventDefault();});
      button.addEventListener("click",event=>{
        // A keyboard activation (detail 0) never reuses a slot left by a pointer gesture that did not click.
        const slot=event.detail>0 ? tabSlot : null;tabSlot=null;
        if(pendingEntry){notice("請先完成或取消目前的輸入。",true);focusGrid();return;}
        if(slot || (browsing() && tab.index===session.state.cell.part)){void browseTo(tab.index,slot);return;}
        if(browsing()){notice(BROWSING_NOTICE,true);return;}
        cancelDrag();void action(async()=>{await showSheet(tab.index);focusGrid();});
      });
      return button;
    }));
  }
  if(state.error) errorNotice(state.error);
  renderHeaders(state);
  renderZoom(state);
  const paintKey=`${state.currentPart}/${state.revision}/${state.zoom}`;
  if(ready && !sheetSwitching && !zooming && lastPaint!==paintKey) {
    lastPaint=paintKey;ui.tiles.replaceChildren();void paint();
  }
  if(!waiting && restoreGridFocus) {
    const active=document.activeElement;
    restoreGridFocus=false;
    if(active===document.body || active===ui.viewport || active===ui["cell-editor"])focusGrid();
  }
  if(pendingEntry && !state.selectionPending && !state.busy && !composing)queueMicrotask(flushPendingEntry);
  autosave?.update();
}
function flushPendingEntry() {
  if(!pendingEntry || composing || session.state.busy || session.state.selectionPending || dragWork)return;
  // A failed selection cannot redirect buffered input to the previous cell.
  if(pendingEntry.invalid || session.state.error){pendingEntry.invalid=true;notice("未能選到儲存格；輸入尚未寫入，按 Esc 取消後重試。",true);return false;}
  const entry=pendingEntry;
  const text=(entry.replace ? "" : session.state.cell.input)+entry.text;
  if(session.state.readOnly || !session.state.cell.writable){errorNotice({code:"READ_ONLY"});return false;}
  if(text.length>CELL_INPUT_LIMIT){errorNotice({code:"CELL_TEXT_TOO_LONG"});return false;}
  return action(async()=>{
    try {
      session.beginEdit("inline",{replace:entry.replace});
      session.setDraft(text);
    } catch(error){pendingEntry=entry;throw error;}
    pendingEntry=null;
    render(session.state);
    revealCell(session.state.cell);
    const node=ui["cell-editor"];node.focus({preventScroll:true});node.setSelectionRange(node.value.length,node.value.length);
    if(entry.commit){await session.commit();focusGrid();}
    return true;
  });
}
function drawTile(entry) {
  let canvas=ui.tiles.querySelector(`[data-key="${CSS.escape(entry.key)}"]`);
  if(!canvas) {canvas=document.createElement("canvas");canvas.dataset.key=entry.key;ui.tiles.append(canvas);}
  canvas.width=entry.tile.width;canvas.height=entry.tile.height;
  canvas.style.left=`${entry.xPx}px`;canvas.style.top=`${entry.yPx}px`;
  canvas.style.width=`${entry.cssWidth}px`;canvas.style.height=`${entry.cssHeight}px`;
  canvas.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(entry.tile.pixels),entry.tile.width,entry.tile.height),0,0);
}
function sheetView() {
  return {scrollLeft:ui.viewport.scrollLeft,scrollTop:ui.viewport.scrollTop,
    minWidth:ui.surface.style.minWidth,minHeight:ui.surface.style.minHeight};
}
async function showSheet(part) {
  const from=session.state.currentPart;
  sheetViews.set(from,sheetView());
  sheetSwitching=true;
  try { await session.showPart(part); } finally {
    sheetSwitching=false;
    const shown=session.state.currentPart;
    if(shown!==from)pendingView=sheetViews.get(shown) ?? {scrollLeft:0,scrollTop:0,minWidth:"",minHeight:""};
    render(session.state);
  }
}
// SPEC-P-calc-sheets 2.3: show `part` without committing; the formula goes on in the formula bar, caret kept.
async function viewPart(part,work) {
  const from=session.state.currentPart;
  sheetViews.set(from,sheetView());
  sheetSwitching=true;pointBusy++;
  try { return await action(work); } finally {
    pointBusy--;sheetSwitching=false;
    const shown=session.state.currentPart;
    if(shown!==from)pendingView=sheetViews.get(shown) ?? HOME_VIEW;
    render(session.state);
  }
}
async function browseTo(part,slot) {
  const field=slot?.field ?? draftField() ?? ui["formula-input"];
  const [start,end]=slot ? [slot.start,slot.end] : [field.selectionStart,field.selectionEnd];
  cancelDrag();
  if(session.state.editing==="inline" && part!==session.state.cell.part)session.beginEdit("formula");
  await viewPart(part,()=>session.browsePart(part));
  if(!session.state.editing)return;
  const node=ui["formula-input"];
  node.value=session.state.draft;node.focus({preventScroll:true});node.setSelectionRange(start,end);
}
// Enter, the commit button, Esc and the cancel button while another sheet is shown: home first, as desktop Calc.
function commitEntry() {
  return action(async()=>{
    if(away())await viewPart(session.state.cell.part,()=>session.commit());
    else await session.commit();
    focusGrid();
  });
}
function cancelEntry() {
  const home=session.state.cell?.part,wasAway=away();
  session.cancelEdit();
  if(wasAway)void viewPart(home,()=>session.browsePart(home)).then(()=>focusGrid());
  else focusGrid();
}
async function paint() {
  if(!session || session.state.state!=="ready" || sheetSwitching || zooming)return;
  if(paintPending){paintAgain=true;return;}
  paintPending=true;
  const view=pendingView;
  try {
    for(let round=0;round<2;round++) {
      const size=session.scheduler.documentCssSize;
      const focus=session.state.selection?.focus;
      ui.surface.style.width=`${Math.ceil(Math.max(size.width,focus ? (focus.xTwips+focus.widthTwips)/tw() : 0))}px`;
      ui.surface.style.height=`${Math.ceil(Math.max(size.height,focus ? (focus.yTwips+focus.heightTwips)/tw() : 0))}px`;
      if(view) {
        ui.surface.style.minWidth=view.minWidth;ui.surface.style.minHeight=view.minHeight;
        ui.viewport.scrollLeft=view.scrollLeft;ui.viewport.scrollTop=view.scrollTop;
      }
      session.scheduleViewport({scrollLeft:ui.viewport.scrollLeft,scrollTop:ui.viewport.scrollTop,
        width:visibleWidth(),height:visibleHeight()});
      await session.drain();
      if(!session.refit())break;
      ui.tiles.replaceChildren();
    }
    if(pendingView===view)pendingView=null;
  } catch(error) {errorNotice(error);} finally {
    paintPending=false;
    if(paintAgain){paintAgain=false;void paint();}
    void refreshHeaders();
  }
}
// SPEC-P-calc-headers 3.4: the visible headers, read when the visible rectangle, the sheet or the revision moved.  Labels and
// edges are the engine's (op 13); a hidden column or row has no element.  The newest reply is kept for the measurement
// (record.headers) with the rectangle it answered.
let headerKey=null,headerData=null,headerPending=false,headerAgain=false;
function headerRectangle() {
  const clamp=v=>Math.min(245760,Math.max(0,Math.round(v)));
  const t=tw();
  return {x:Math.max(0,Math.round(ui.viewport.scrollLeft*t)),y:Math.max(0,Math.round(ui.viewport.scrollTop*t)),
    width:clamp(visibleWidth()*t),height:clamp(visibleHeight()*t)};
}
async function refreshHeaders() {
  if(!session || session.state.state!=="ready" || sheetSwitching || !headersOn())return;
  if(headerPending){headerAgain=true;return;}
  const rect=headerRectangle(),owner=session;
  const key=`${session.state.currentPart}/${session.state.revision}/${session.state.zoom}/${rect.x}/${rect.y}/${rect.width}/${rect.height}`;
  if(key===headerKey)return;
  headerPending=true;
  try {
    const reply=await owner.readHeaders(rect);
    if(reply && owner===session) {
      headerKey=key;headerData=reply.headers;
      record.headers={rectangle:rect,part:reply.headers.part,revision:session.state.revision,zoom:session.state.zoom,reply:reply.headers};
      drawHeaders();renderHeaders(session.state);
    }
  } catch(error) {errorNotice(error);} finally {
    headerPending=false;
    if(headerAgain){headerAgain=false;void refreshHeaders();}
  }
}
function headerButton(axis,entry) {
  const node=document.createElement("button");
  node.type="button";node.tabIndex=-1;node.className="sheet-header";
  node.dataset.axis=axis;node.dataset.index=String(entry.index);node.textContent=entry.label;
  node.setAttribute("role",axis==="column" ? "columnheader" : "rowheader");
  node.setAttribute("aria-label",axis==="column" ? `欄 ${entry.label}` : `列 ${entry.label}`);
  node.setAttribute("aria-selected","false");
  const size=`${entry.endPx-entry.startPx}px`,start=`${entry.startPx}px`;
  if(axis==="column"){node.style.left=start;node.style.width=size;} else {node.style.top=start;node.style.height=size;}
  return node;
}
function drawHeaders() {
  if(!headerData)return;
  ui["column-headers"].replaceChildren(...headerData.columns.filter(e=>!e.hidden).map(e=>headerButton("column",e)));
  ui["row-headers"].replaceChildren(...headerData.rows.filter(e=>!e.hidden).map(e=>headerButton("row",e)));
}
function renderHeaders(state) {
  const on=state.headersSupported===true && state.state==="ready";
  ui["sheet-frame"].classList.toggle("with-headers",on);
  for(const node of [ui["corner-header"],ui["column-headers"],ui["row-headers"]])node.hidden=!on;
  if(!on)return;
  if(headerData && headerData.part!==state.currentPart){ui["column-headers"].replaceChildren();ui["row-headers"].replaceChildren();}
  const range=state.selection,cell=state.cell;
  const mark=(node,low,high,whole,currentLow,currentHigh)=>{
    const index=Number(node.dataset.index);
    node.setAttribute("aria-selected",String(!!whole && index>=low && index<=high));
    node.toggleAttribute("data-highlight",!!range && index>=low && index<=high);
    node.toggleAttribute("data-current",!!cell && index>=currentLow && index<=currentHigh);
  };
  for(const node of ui["column-headers"].children)
    mark(node,range?.column,range?.endColumn,range?.whole==="columns" || range?.whole==="sheet",cell?.column,cell?.endColumn);
  for(const node of ui["row-headers"].children)
    mark(node,range?.row,range?.endRow,range?.whole==="rows" || range?.whole==="sheet",cell?.row,cell?.endRow);
  ui["corner-header"].setAttribute("aria-selected",String(range?.whole==="sheet"));
}
// SPEC-P-calc-zoom 2.6: the zoom group at the toolbar's end; not while an entry is open (L-calc-zoom-not-while-editing).
function zoomBlocked(state) {
  return state.state!=="ready" || state.zoomSupported!==true || state.busy || state.selectionPending || state.editing!==null
    || pendingEntry!==null || !!dragWork || away(state) || sheetSwitching || zooming;
}
function renderZoom(state) {
  const on=state.state==="ready" && state.zoomSupported===true;
  for(const node of document.querySelectorAll("[data-zoom-group]"))node.hidden=!on;
  ui.surface.style.setProperty("--calc-zoom",String(zoomScale()));
  if(!on)return;
  const blocked=zoomBlocked(state);
  ui["zoom-out"].disabled=blocked || state.zoom<=ZOOM_PERCENTS[0];
  ui["zoom-in"].disabled=blocked || state.zoom>=ZOOM_PERCENTS.at(-1);
  ui["zoom-level"].disabled=blocked;
  ui["zoom-level"].textContent=`${state.zoom}%`;
}
// The viewport's centre in CSS px of the surface and in twips at the current zoom; the session asks the engine which cell is
// there (op 5), so it does not depend on headers that may still describe another place (Codex review 2026-11-07).
function centrePoint() {
  const x=ui.viewport.scrollLeft+visibleWidth()/2,y=ui.viewport.scrollTop+visibleHeight()/2,t=tw();
  return {x,y,xTwips:Math.round(x*t),yTwips:Math.round(y*t)};
}
// The same spot of the centre cell goes back to the centre: rows are whole pixels at each zoom, so a scroll position cannot
// be scaled (spec 1); without headers the ratio is the fallback.  Other sheets' remembered scrolls are scaled.
async function zoomTo(percent) {
  if(!session || zoomBlocked(session.state) || percent===session.state.zoom || !ZOOM_PERCENTS.includes(percent))return;
  cancelDrag();
  const from=zoomScale(),to=percent/100,centre=centrePoint();
  let x=(ui.viewport.scrollLeft+visibleWidth()/2)*to/from,y=(ui.viewport.scrollTop+visibleHeight()/2)*to/from;
  zooming=true;
  try {
    const result=await session.setZoom(percent,{centre:{xTwips:centre.xTwips,yTwips:centre.yTwips}});
    if(result.centre) {
      const {before,after}=result.centre,oldTw=15/from,newTw=15/to;
      const fx=(centre.x*oldTw-before.xTwips)/before.widthTwips,fy=(centre.y*oldTw-before.yTwips)/before.heightTwips;
      x=(after.xTwips+fx*after.widthTwips)/newTw;y=(after.yTwips+fy*after.heightTwips)/newTw;
    }
    for(const [part,view] of sheetViews)
      sheetViews.set(part,{scrollLeft:view.scrollLeft*to/from,scrollTop:view.scrollTop*to/from,minWidth:"",minHeight:""});
    pendingView={scrollLeft:Math.max(0,Math.round(x-visibleWidth()/2)),scrollTop:Math.max(0,Math.round(y-visibleHeight()/2)),
      minWidth:"",minHeight:""};
    headerKey=null;
  } catch(error) {errorNotice(error);} finally {
    zooming=false;
    render(session.state);
  }
  focusGrid();
}
function stepZoom(direction) {
  const zoom=session?.state.zoom ?? 100;
  const next=direction>0 ? ZOOM_PERCENTS.find(p=>p>zoom) : [...ZOOM_PERCENTS].reverse().find(p=>p<zoom);
  if(next!==undefined)void zoomTo(next);
}
async function openBytes(bytes,name,options={}) {
  if((pendingEntry || session?.hasUnsavedEdits()) && !confirm("尚有修改未儲存，仍要開啟其他檔案嗎？"))return;
  autosave?.dispose();autosave=null;
  pendingEntry=null;cancelDrag();
  if(session)await session.close();
  lastPaint=null;ui.tiles.replaceChildren();ui.viewport.scrollTop=0;ui.viewport.scrollLeft=0;
  ui.surface.style.minWidth="";ui.surface.style.minHeight="";
  sheetViews.clear();pendingView=null;
  headerKey=null;headerData=null;ui["column-headers"].replaceChildren();ui["row-headers"].replaceChildren();
  session=new CalcEditorSession({
    engineFactory:async({onEvent})=>{
      const engine=new CalcDocumentEngine({...ENGINE_OPTIONS,debug:diagnostics});
      engine.onEvent(event=>{onEvent(event);if(diagnostics && record.events.length<300)record.events.push(event);});
      return engine._initialize();
    },
    formControlsSupported:async()=>{
      const url=new URL("./sdk-manifest.json",new URL(ENGINE_OPTIONS.workerUrl,location.href));
      const response=await fetch(url,{cache:"no-cache"});
      return response.ok && (await response.json()).capabilities?.includes("form-controls")===true;
    },
    onState:render,onTile:drawTile,
  });
  record.session=session;
  await session.open({bytes,name,...options});
  const owner=session;
  autosave=new CalcAutosave({
    snapshot:()=>{
      const s=owner.state;
      return {host:!!HOST,state:s.state,readOnly:s.readOnly,editing:s.editing,revision:s.revision,
        committedDirty:s.committedDirty,busy:s.busy,saving:s.saving,selectionPending:s.selectionPending,
        uncertain:s.uncertain,error:s.error,composing,pendingEntry:pendingEntry!==null,
        dragging:dragWork!==null,manualPending:manualSaves>0};
    },
    save:conditions=>save("auto",conditions,owner),onState:autosaveState,
  });
  if(diagnostics)record.autosave=autosave;
  autosave.update();
  notice(options.readOnly ? "此檔案目前以唯讀開啟。" : "直接輸入取代內容；F2 編輯；拖曳或 Shift＋方向鍵選取範圍。");
  await paint();
  return session.state;
}
record.openBytes=openBytes;
record.ready=Promise.resolve();
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
function handToBrowser(bytes,name,format) {
  const url=URL.createObjectURL(new Blob([bytes],{type:CALC_FORMATS[format].mime}));
  const link=document.createElement("a");link.href=url;link.download=name;link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function saveToHost(owner,trigger,conditions) {
  // SPEC-P-ms-formats 5.3: after a Save As the host is opening the copy; nothing more goes to the original.
  if(handedOver){notice("已另存新檔，正在開啟新檔。");return;}
  const saved=await owner.save(async(bytes,{name,format})=>{
    if(HOST)return HOST.save(bytes,{name,trigger,conditions,format});
    handToBrowser(bytes,name,format);
    return{name};
  },{commitDraft:trigger!=="auto"});
  record.lastSave={revision:saved.revision,bytes:saved.bytes.byteLength,result:saved.result,trigger};
  if(diagnostics)record.lastExport=saved.bytes;
  if(trigger!=="auto")notice(HOST ? "已存回試算表。":"已交給瀏覽器下載，請確認檔案已存好。");
  return saved.result;
}
function focusGrid(){
  const node=ui["cell-editor"].disabled ? ui.viewport : ui["cell-editor"];
  node.focus({preventScroll:true});
}
function revealCell(cell) {
  if(!cell)return;
  const t=tw(),left=cell.xTwips/t,top=cell.yTwips/t,right=left+cell.widthTwips/t,bottom=top+cell.heightTwips/t;
  ui.surface.style.minWidth=`${Math.ceil(right)}px`;ui.surface.style.minHeight=`${Math.ceil(bottom)}px`;
  if(left<ui.viewport.scrollLeft)ui.viewport.scrollLeft=Math.floor(left);
  else if(right>ui.viewport.scrollLeft+visibleWidth())ui.viewport.scrollLeft=Math.ceil(right-visibleWidth());
  if(top<ui.viewport.scrollTop)ui.viewport.scrollTop=Math.floor(top);
  else if(bottom>ui.viewport.scrollTop+visibleHeight())ui.viewport.scrollTop=Math.ceil(bottom-visibleHeight());
}
ui.viewport.addEventListener("focus",focusGrid);
document.addEventListener("focusin",event=>{
  if(![document.body,ui.viewport,ui["cell-editor"]].includes(event.target))restoreGridFocus=false;
});
ui["open-file"].addEventListener("click",()=>ui["file-input"].click());
ui["file-input"].addEventListener("change",()=>{
  const file=ui["file-input"].files[0];
  if(file)void action(async()=>openBytes(await file.arrayBuffer(),file.name));
});
ui["save-button"].addEventListener("click",()=>{if(browsing()){notice(BROWSING_NOTICE,true);return;}void action(()=>save());});

// SPEC-P-ms-formats 5.2, Save As. The page's own dialog: a name (the document's, less its suffix) and the format -- ODF
// always, the original too for an XLSX, ODF preselected (the owner's use is converting to ODF); ODS to XLSX is not in this
// batch (L-saveas-ms-from-odf). Confirmed: the pending entry is put back first, as a manual save does; the engine writes the
// copy once (the session's saveCopy, in its queue) and it goes to HOST.saveAs -- NAME_TAKEN keeps the dialog open and says
// so -- or, without a host, to a download. A copy is not a save of this document: its edits still count as unsaved.
function saveAsOffered(state) {
  return !state.readOnly && (!HOST || typeof HOST.saveAs==="function");
}
function stemOf(name) { return String(name ?? "").replace(/\.(?:ods|xlsx)$/i,""); }
function saveAsChoices(format) {
  const choices=[{format:"ods",text:"ODF 試算表（.ods）"}];
  if(format!=="ods" && CALC_FORMATS[format])choices.push({format,text:`原格式（${CALC_FORMATS[format].suffix}）`});
  return choices;
}
function saveAsFileName(typed,format) {
  const stem=stemOf(String(typed ?? "").trim()).trim();
  if(stem==="")return {error:"請輸入檔名"};
  if(/[\\/\u0000-\u001f\u007f]/.test(stem))return {error:"檔名不能含有 / 或 \\"};
  return {name:stem+CALC_FORMATS[format].suffix};
}
function saveAsRefusalText(error,name) {
  if(error?.code==="NAME_TAKEN")return `這個資料夾已經有「${name}」，請換一個檔名`;
  return `另存新檔沒有完成：${error?.message || String(error)}`;
}
const chosenSaveAsFormat=()=>ui["save-as-formats"].querySelector('input[name="save-as-format"]:checked')?.value ?? "ods";
function showSaveAsMessage(text) { ui["save-as-message"].textContent=text;ui["save-as-message"].hidden=false; }
function openSaveAsDialog() {
  if(!session || session.state.state!=="ready" || !saveAsOffered(session.state) || handedOver)return;
  const legend=ui["save-as-formats"].querySelector("legend");
  ui["save-as-formats"].replaceChildren(...(legend ? [legend] : []),...saveAsChoices(session.documentFormat()).map((choice,index)=>{
    const label=document.createElement("label"),radio=document.createElement("input");
    radio.type="radio";radio.name="save-as-format";radio.value=choice.format;radio.checked=index===0;
    label.append(radio,choice.text);return label;
  }));
  ui["save-as-name"].value=stemOf(session.state.fileName);
  ui["save-as-suffix"].textContent=CALC_FORMATS[chosenSaveAsFormat()].suffix;
  ui["save-as-message"].hidden=true;ui["save-as-message"].textContent="";
  ui["save-as-confirm"].disabled=false;
  if(!ui["save-as-dialog"].open)ui["save-as-dialog"].showModal();
  ui["save-as-name"].focus();ui["save-as-name"].select();
}
function closeSaveAsDialog() {
  if(ui["save-as-dialog"].open)ui["save-as-dialog"].close();
  ui["save-as-message"].hidden=true;ui["save-as-message"].textContent="";
  ui["save-as-confirm"].disabled=false;
  focusGrid();
}
async function saveAs(name,format,owner=session) {
  manualSaves++;autosave?.update();
  try {
    await owner.whenIdle();
    if(owner!==session)return;
    const entryWasPending=pendingEntry!==null,flushed=await flushPendingEntry();
    if(entryWasPending && flushed!==true)throw new Error("輸入尚未接回儲存格，請先完成或取消輸入。");
    if(pendingEntry || composing)throw new Error("請先完成輸入或取消尚未寫入的內容，再另存新檔。");
    const saved=await owner.saveCopy(format,async bytes=>{
      if(!HOST){handToBrowser(bytes,name,format);return {name};}
      return HOST.saveAs(bytes,{name,format});
    });
    if(HOST){handedOver=true;autosave?.dispose();autosave=null;render(owner.state);}
    notice(HOST ? `已另存為 ${saved.result?.name ?? name}，正在開啟新檔。` : `已交給瀏覽器下載 ${name}，請確認檔案已存好。`);
    return saved;
  } finally {manualSaves--;autosave?.update();}
}
async function confirmSaveAs() {
  if(ui["save-as-confirm"].disabled)return;
  const format=chosenSaveAsFormat(),{name,error}=saveAsFileName(ui["save-as-name"].value,format);
  if(error){showSaveAsMessage(error);return;}
  ui["save-as-confirm"].disabled=true;ui["save-as-message"].hidden=true;
  try {await saveAs(name,format);closeSaveAsDialog();}
  catch(failure) {ui["save-as-confirm"].disabled=false;showSaveAsMessage(saveAsRefusalText(failure,name));}
}
ui["save-as-button"].addEventListener("click",()=>openSaveAsDialog());
ui["save-as-formats"].addEventListener("change",()=>{ui["save-as-suffix"].textContent=CALC_FORMATS[chosenSaveAsFormat()].suffix;});
ui["save-as-name"].addEventListener("keydown",event=>{
  if(event.key!=="Enter" || event.isComposing)return;
  event.preventDefault();void confirmSaveAs();
});
ui["save-as-cancel"].addEventListener("click",closeSaveAsDialog);
ui["save-as-dialog"].addEventListener("cancel",event=>{event.preventDefault();closeSaveAsDialog();});
ui["save-as-confirm"].addEventListener("click",()=>void confirmSaveAs());
ui["commit-button"].addEventListener("click",()=>void commitEntry());
ui["cancel-button"].addEventListener("click",()=>cancelEntry());
for(const node of document.querySelectorAll("[data-format]"))
  node.addEventListener("click",()=>{
    if(pendingEntry){notice("請先完成或取消目前的輸入。",true);return;}
    void action(()=>toggleFormat(node.dataset.format));
  });
for(const key of Object.keys(lastColor)) {
  renderSwatch(key);
  document.querySelector(`[data-color="${key}"]`).addEventListener("click",()=>applyStyle(key,lastColor[key]));
  document.querySelector(`[data-color-menu="${key}"]`).addEventListener("click",()=>openColorPopover(key));
}
colorGrid.addEventListener("click",event=>{
  const value=event.target.dataset?.swatch;
  if(value)pickColor(value);
});
colorClear.addEventListener("click",()=>pickColor(COLOR_NONE[colorTarget][0]));
colorPopover.addEventListener("keydown",event=>{
  if(event.key==="Escape"){event.preventDefault();event.stopPropagation();closeColorPopover(true);}
});
document.addEventListener("pointerdown",event=>{
  if(colorTarget!==null && !colorPopover.contains(event.target) && !event.target.closest?.("[data-color-menu]"))closeColorPopover();
},true);
// As Collabora's Calc: pressing the alignment a cell already has gives it back.
for(const node of document.querySelectorAll("[data-align]"))
  node.addEventListener("click",()=>{
    if(!session)return;
    applyStyle("horizontalAlign",currentStyle(session.state,"horizontalAlign")===node.dataset.align ? "standard" : node.dataset.align);
  });
function formatRefusal(code) {
  return ({RANGE_TOO_LARGE:"請縮小範圍至 65,536 格以內。",RANGE_MERGE_BOUNDARY:"請選取完整合併格後再設定格式。",
    RANGE_PROTECTED:"選取範圍含受保護的儲存格。",READ_ONLY:"此範圍無法編輯。"})[code] || "目前無法設定此範圍的格式。";
}
// SPEC-P-calc-undo 4.3 and 5.  An entry not yet sent is the newest change: undo drops it, redo waits for it.
function walk(direction) {
  if(!session?.state.undoSupported)return;
  if(browsing()){notice(BROWSING_NOTICE,true);return;}
  const entry=pendingEntry!==null || (session.state.editing!==null && session.state.draft!==session.state.cell?.input);
  if(entry && direction==="redo"){notice("請先完成或取消目前的輸入。",true);return;}
  if(entry && pendingEntry!==null) {
    pendingEntry=null;session.cancelEdit();focusGrid();notice("已取消輸入中的內容，文件沒有變動。");return;
  }
  cancelDrag();
  void action(async()=>{
    // As in showSheet: no paint until the session has settled.  An undo whose
    // restored cell is on another sheet switches the way a tab does, keeping the
    // view of the sheet left (Codex review 5).
    const from=session.state.currentPart,view=sheetView();
    let result;
    sheetSwitching=true;
    try { result=await session[direction](); } finally { sheetSwitching=false; }
    if(result?.otherSheet) {
      sheetViews.set(from,view);
      await showSheet(result.cursor.part);
      await session.selectCell(result.cursor.column,result.cursor.row);
    }
    render(session.state);
    if(result?.draftPending){notice("請先完成或取消目前的輸入。",true);return;}
    notice(result?.draftDiscarded ? "已取消輸入中的內容，文件沒有變動。"
      : result?.nothing ? (direction==="undo" ? "沒有可以復原的動作。" : "沒有可以重做的動作。")
      : direction==="undo" ? "已復原。" : "已重做。");
    revealCell(session.state.cell);focusGrid();
  });
}
ui["zoom-in"].addEventListener("click",()=>stepZoom(1));
ui["zoom-out"].addEventListener("click",()=>stepZoom(-1));
ui["zoom-level"].addEventListener("click",()=>void zoomTo(100));
ui["undo-button"].addEventListener("click",()=>walk("undo"));
ui["redo-button"].addEventListener("click",()=>walk("redo"));
function toggleFormat(format) {
  if(!session || !formatAvailable(session.state))return;
  const s=session.state,value=s.selection?.multiple ? s.rangeFormat?.[format] : s.cell[format];
  return session.setFormat(format,value!==true);
}
for(const node of [ui["formula-input"],ui["cell-editor"]]) {
  const bufferEntry=replace=>{
    if(!pendingEntry){pendingEntry={replace,text:""};node.value="";node.setSelectionRange(0,0);}
  };
  const startReplacement=()=>{
    if(node===ui["cell-editor"] && (pendingEntry || session.state.selectionPending)) {
      bufferEntry(true);return;
    }
    if(node===ui["cell-editor"] && !session.state.editing){session.beginEdit("inline",{replace:true});revealCell(session.state.cell);}
  };
  node.addEventListener("beforeinput",event=>{
    if(event.inputType.startsWith("insert"))void action(startReplacement);
  });
  node.addEventListener("compositionstart",()=>{void action(startReplacement);composing=true;});
  const updateDraft=()=>{
    if(node===ui["cell-editor"] && pendingEntry){pendingEntry.text=node.value;flushPendingEntry();}
    else void action(()=>session.setDraft(node.value));
  };
  node.addEventListener("compositionend",()=>{composing=false;updateDraft();});
  node.addEventListener("input",updateDraft);
  node.addEventListener("keydown",event=>{
    if(composing || event.isComposing || event.keyCode===229) {
      if(composing && !event.isComposing && event.keyCode!==229 && ["Enter","Escape"].includes(event.key))event.preventDefault();
      return;
    }
    if(node===ui["cell-editor"] && event.key==="F2" && !composing && !event.isComposing && event.keyCode!==229) {
      event.preventDefault();
      if(session.state.selectionPending){bufferEntry(false);return;}
      void action(()=>{
        session.beginEdit("inline");
        revealCell(session.state.cell);
        node.setSelectionRange(node.value.length,node.value.length);
      });
      return;
    }
    const intent=inputIntent(event);if(!intent)return;
    event.preventDefault();
    if(pendingEntry) {
      if(intent==="cancel"){pendingEntry=null;session.cancelEdit();focusGrid();}
      else {pendingEntry.commit=true;flushPendingEntry();}
      return;
    }
    if(intent==="cancel")cancelEntry();
    else void commitEntry();
  });
}
ui["formula-input"].addEventListener("focus",()=>{
  if(pendingEntry){focusGrid();return;}
  void action(()=>session.beginEdit("formula"));
});
ui["cell-address"].addEventListener("blur",()=>{
  const cell=session?.state.cell;
  if(cell)ui["cell-address"].value=cellAddress(cell.column,cell.row);
});
ui["cell-address"].addEventListener("keydown",event=>{
  if(event.key!=="Enter")return;event.preventDefault();
  if(pendingEntry){notice("請先完成或取消目前的輸入。",true);focusGrid();return;}
  if(browsing()){notice(BROWSING_NOTICE,true);return;}
  // SPEC-P-calc-sheets 2.2: A1, $A$1, Sheet.A1, 'Sheet name'.A1 and Excel's Sheet!A1.
  const target=parseCellTarget(ui["cell-address"].value,sheetNames(session.state));
  if(target.error==="UNKNOWN_SHEET"){notice(`找不到名為「${target.sheet}」的工作表。`,true);return;}
  if(target.error){notice("請輸入儲存格位址，例如 A1 或 另一張表.A1。",true);return;}
  cancelDrag();void action(async()=>{
    if(target.part!==null && target.part!==session.state.currentPart)await showSheet(target.part);
    const cell=await session.selectCell(target.column,target.row);revealCell(cell);focusGrid();
  });
});
function point(event){const rect=ui.surface.getBoundingClientRect(),t=tw();return[Math.max(0,Math.round((event.clientX-rect.left)*t)),Math.max(0,Math.round((event.clientY-rect.top)*t))];}
let drag=null, dragWork=null, gesture=0;
function cancelDrag(){
  if(pendingEntry && dragWork)pendingEntry.invalid=true;
  gesture++;const current=drag;drag=null;dragWork=null;
  if(current && ui.viewport.hasPointerCapture(current.pointer))ui.viewport.releasePointerCapture(current.pointer);
  if(session)renderFormatControls(session.state);
  autosave?.update();
}
function inViewport(event) {
  const r=ui.viewport.getBoundingClientRect();
  return event.clientX>=r.left && event.clientY>=r.top && event.clientX<r.left+ui.viewport.clientWidth && event.clientY<r.top+ui.viewport.clientHeight;
}
async function extendDrag(current) {
  if(current.pumping)return;
  current.pumping=true;
  try {
    if(!await current.start){if(pendingEntry)pendingEntry.invalid=true;return;}
    while(current.latest && current.generation===gesture) {
      const [x,y]=current.latest;current.latest=null;
      const selected=await action(()=>current.owner.selectAt(x,y,{extend:true,valid:()=>current.generation===gesture}));
      if(!selected && pendingEntry)pendingEntry.invalid=true;
    }
  } finally {
    current.pumping=false;
    if(!current.active && current.generation===gesture){
      if(dragWork===current)dragWork=null;
      if(session)renderFormatControls(session.state);
      autosave?.update();
      void flushPendingEntry();focusGrid();
    }
  }
}
// SPEC-P-calc-headers 3.4: click, shift-click and drag on the headers; the corner selects the sheet.
let headerDrag=null;
function announceWhole(kind,first,last) {
  const low=Math.min(first,last),high=Math.max(first,last);
  notice(kind==="sheet" ? "已選取整張工作表" : kind==="columns"
    ? (low===high ? `已選取整欄 ${columnName(low)}` : `已選取第 ${columnName(low)} 到 ${columnName(high)} 欄`)
    : (low===high ? `已選取整列 ${low+1}` : `已選取第 ${low+1} 到 ${high+1} 列`));
}
function selectWhole(kind,first,last,valid=()=>true) {
  return action(async()=>{
    const cell=await session.selectWhole(kind,first,last,{valid});
    if(cell && valid())announceWhole(kind,first,last);
    return cell;
  });
}
function headerIndexAt(kind,event) {
  if(!headerData)return null;
  const strip=kind==="columns" ? ui["column-headers"] : ui["row-headers"],rect=strip.getBoundingClientRect();
  const at=kind==="columns" ? event.clientX-rect.left : event.clientY-rect.top;
  const entry=(kind==="columns" ? headerData.columns : headerData.rows).find(e=>!e.hidden && at>=e.startPx && at<e.endPx);
  return entry ? entry.index : null;
}
async function pumpHeaderDrag(current) {
  if(current.pumping)return;
  current.pumping=true;
  try {
    await current.start;
    while(current.latest!==null && current.latest!==current.shown && current.generation===gesture) {
      const index=current.latest;current.shown=index;
      await selectWhole(current.kind,current.first,index,()=>current.generation===gesture);
    }
  } finally {current.pumping=false;}
}
for(const [strip,kind] of [[ui["column-headers"],"columns"],[ui["row-headers"],"rows"]]) {
  strip.addEventListener("pointerdown",event=>{
    const node=event.target.closest?.(".sheet-header");
    event.stopPropagation();
    if(!session || !node || event.button!==0)return;
    event.preventDefault();
    if(pendingEntry){notice("請先完成或取消目前的輸入。",true);return;}
    if(browsing()){notice(BROWSING_NOTICE,true);return;}
    cancelDrag();
    const index=Number(node.dataset.index),range=session.state.selection,cell=session.state.cell;
    const first=!event.shiftKey ? index : range?.whole===kind ? range.first : kind==="columns" ? cell.column : cell.row;
    const current={kind,first,pointer:event.pointerId,generation:gesture,latest:null,shown:index,pumping:false};
    headerDrag=current;strip.setPointerCapture(event.pointerId);
    current.start=selectWhole(kind,first,index,()=>current.generation===gesture);
    focusGrid();
  });
  strip.addEventListener("pointermove",event=>{
    if(!headerDrag || headerDrag.kind!==kind || event.pointerId!==headerDrag.pointer)return;
    const index=headerIndexAt(kind,event);
    if(index!==null){headerDrag.latest=index;void pumpHeaderDrag(headerDrag);}
  });
  const end=event=>{
    if(!headerDrag || event.pointerId!==headerDrag.pointer)return;
    if(strip.hasPointerCapture(event.pointerId))strip.releasePointerCapture(event.pointerId);
    const current=headerDrag;headerDrag=null;
    void pumpHeaderDrag(current).then(()=>focusGrid());
  };
  strip.addEventListener("pointerup",end);strip.addEventListener("pointercancel",end);
}
ui["corner-header"].addEventListener("pointerdown",event=>event.stopPropagation());
ui["corner-header"].addEventListener("click",()=>{
  if(!session)return;
  if(pendingEntry){notice("請先完成或取消目前的輸入。",true);focusGrid();return;}
  if(browsing()){notice(BROWSING_NOTICE,true);return;}
  cancelDrag();void selectWhole("sheet",0,0).then(()=>focusGrid());
});
// SPEC-P-calc-structure 2.2-2.4, 3.3: insert and delete rows or columns.  A right click on a row or column header lists that
// axis's three items, on a cell all six; outside the selection it first selects there (desktop Calc).  Shift+F10 or the menu
// key opens it at the active cell; Ctrl+＋ / Ctrl+－ act on a whole-row or whole-column selection.
const structureMenu=$("structure-menu");
const STRUCTURE_ITEMS=Object.freeze([
  ["rows","insert","before","上方插入列"],["rows","insert","after","下方插入列"],["rows","delete","before","刪除列"],
  ["columns","insert","before","左方插入欄"],["columns","insert","after","右方插入欄"],["columns","delete","before","刪除欄"]]);
let structureReturn=null;
function structureOn(){return session?.state.structureSupported===true && session.state.state==="ready";}
function structureReason(axis,act,where) {
  const state=session.state;
  if(state.readOnly)return "這份試算表是唯讀的，不能插入或刪除欄列。";
  if(state.cell?.writable!==true)return "工作表受保護，不能插入或刪除欄列。";
  if(state.uncertain)return "無法確認剛才的修改，請保留此頁。";
  if(state.busy || state.selectionPending || pendingEntry || dragWork)return "請先完成目前的輸入或選取。";
  const plan=session.structurePlan(axis,act,where);
  return plan.refused==="WHOLE_AXIS" ? (axis==="rows" ? "選取範圍涵蓋所有列，不能再插入或刪除列。" : "選取範圍涵蓋所有欄，不能再插入或刪除欄。")
    : plan.refused==="PAST_THE_END" ? "插入的位置超出工作表。" : plan.refused ? "目前不能插入或刪除欄列。" : null;
}
function closeStructureMenu(returnFocus=false) {
  if(structureMenu.hidden)return;
  structureMenu.hidden=true;structureMenu.replaceChildren();
  if(returnFocus)focusGrid();
}
function openStructureMenu(axes,x,y) {
  closeColorPopover();
  const items=[];
  for(const [axis,act,where,label] of STRUCTURE_ITEMS) {
    if(!axes.includes(axis))continue;
    if(items.length && items.at(-1).dataset.axis!==axis){const line=document.createElement("div");line.setAttribute("role","separator");items.push(line);}
    const node=document.createElement("button");
    node.type="button";node.tabIndex=-1;node.setAttribute("role","menuitem");node.textContent=label;
    node.dataset.structure=`${axis}-${act}${act==="insert" ? `-${where}` : ""}`;node.dataset.axis=axis;
    const reason=structureReason(axis,act,where);
    node.setAttribute("aria-disabled",String(reason!==null));node.title=reason ?? label;
    node.addEventListener("click",()=>runStructure(axis,act,where,node));
    items.push(node);
  }
  structureMenu.replaceChildren(...items);structureMenu.hidden=false;
  structureMenu.style.left=`${Math.max(8,Math.min(x,innerWidth-structureMenu.offsetWidth-8))}px`;
  structureMenu.style.top=`${Math.max(8,Math.min(y,innerHeight-structureMenu.offsetHeight-8))}px`;
  structureMenu.querySelector('[role="menuitem"]')?.focus({preventScroll:true});
}
function structureSentence(result) {
  const rows=result.axis==="rows",name=index=>rows ? `第 ${index+1} 列` : ` ${columnName(index)} 欄`;
  const unit=rows ? "列" : "欄",last=result.index+result.count-1;
  if(result.action==="delete")return result.count===1 ? `已刪除${name(result.index)}。`
    : `已刪除${rows ? `第 ${result.index+1} 到 ${last+1} 列` : ` ${columnName(result.index)} 到 ${columnName(last)} 欄`}。`;
  return result.where==="after" ? `已在${name(result.index-1)}${rows ? "下方" : "右方"}插入 ${result.count} ${unit}。`
    : `已在${name(result.index)}${rows ? "上方" : "左方"}插入 ${result.count} ${unit}。`;
}
function runStructure(axis,act,where,node=null) {
  if(node?.getAttribute("aria-disabled")==="true"){notice(node.title,true);return;}
  closeStructureMenu();
  const reason=structureReason(axis,act,where);
  if(reason){notice(reason,true);focusGrid();return;}
  cancelDrag();
  void (async()=>{
    try {
      const result=await session.changeStructure(axis,act,where);
      render(session.state);void refreshHeaders();
      notice(structureSentence(result));
    } catch(error) {
      if(error.code==="READ_ONLY")notice("工作表受保護或文件是唯讀的，不能插入或刪除欄列。",true);
      else errorNotice(error);
      if(session)render(session.state);
    }
    focusGrid();
  })();
}
async function structureAt(kind,event) {
  if(zooming)return false;
  // The header or cell under the pointer joins the selection first unless it is already in it.
  const range=session.state.selection;
  if(kind==="rows" || kind==="columns") {
    const index=headerIndexAt(kind,event);
    if(index===null)return false;
    const low=kind==="rows" ? range?.row : range?.column,high=kind==="rows" ? range?.endRow : range?.endColumn;
    const covers=range && (range.whole===kind || range.whole==="sheet") && index>=low && index<=high;
    if(!covers)await selectWhole(kind,index,index);
    return true;
  }
  const [x,y]=point(event);
  const inside=range && x>=range.xTwips && x<range.xTwips+range.widthTwips && y>=range.yTwips && y<range.yTwips+range.heightTwips;
  if(!inside)await action(()=>session.selectAt(x,y));
  return true;
}
for(const [target,kind] of [[ui["row-headers"],"rows"],[ui["column-headers"],"columns"],[ui.viewport,"cells"]]) {
  target.addEventListener("contextmenu",event=>{
    if(!structureOn())return;
    event.preventDefault();event.stopPropagation();
    if(session.state.editing || pendingEntry){notice("請先完成或取消目前的輸入。",true);return;}
    if(kind==="cells" && (event.target.closest?.(".sheet-header,#corner-header") || !inViewport(event)))return;
    cancelDrag();
    const x=event.clientX,y=event.clientY;
    void structureAt(kind,event).then(ok=>{if(ok)openStructureMenu(kind==="cells" ? ["rows","columns"] : [kind],x,y);});
  });
}
structureMenu.addEventListener("keydown",event=>{
  const items=[...structureMenu.querySelectorAll('[role="menuitem"]')];
  const at=items.indexOf(document.activeElement);
  if(event.key==="Escape" || event.key==="Tab"){event.preventDefault();closeStructureMenu(true);return;}
  const next={ArrowDown:at+1,ArrowUp:at-1,Home:0,End:items.length-1}[event.key];
  if(next!==undefined){event.preventDefault();items[(next+items.length)%items.length]?.focus({preventScroll:true});return;}
  if(event.key==="Enter" || event.key===" "){event.preventDefault();document.activeElement?.click();}
});
document.addEventListener("pointerdown",event=>{if(!structureMenu.hidden && !structureMenu.contains(event.target))closeStructureMenu();},true);
function structureKey(event) {
  if(!structureOn() || session.state.editing || composing || event.isComposing || event.keyCode===229)return false;
  if(event.key==="ContextMenu" || (event.key==="F10" && event.shiftKey && !event.ctrlKey && !event.altKey && !event.metaKey)) {
    event.preventDefault();event.stopPropagation();
    if(pendingEntry){notice("請先完成或取消目前的輸入。",true);return true;}
    const box=ui["active-cell"].getBoundingClientRect();
    openStructureMenu(["rows","columns"],box.left,box.bottom+2);
    return true;
  }
  if(!(event.ctrlKey || event.metaKey) || event.altKey)return false;
  const insert=event.key==="+" || (event.key==="=" && event.shiftKey),remove=event.key==="-" || event.key==="_";
  if(!insert && !remove)return false;
  event.preventDefault();event.stopPropagation();
  if(event.repeat)return true;
  const range=session.state.selection,axis=range?.whole==="rows" ? "rows" : range?.whole==="columns" ? "columns" : null;
  if(!axis){notice("整列或整欄選取時才能用 Ctrl+＋／Ctrl+－；其他選取請用右鍵選單。",true);return true;}
  runStructure(axis,insert ? "insert" : "delete","before");
  return true;
}
ui["cell-editor"].addEventListener("keydown",structureKey);
ui.viewport.addEventListener("keydown",event=>{if(event.target!==ui["cell-editor"])structureKey(event);});
// Ctrl+Space and Ctrl+Shift+Space (Calc's own zh-TW key; input methods often take Ctrl+Space) select the columns of the
// selection, Shift+Space its rows.  Caught on keydown: the typing focus is #cell-editor, where a space would start an entry.
function wholeKey(event) {
  if(!session || !(event.key===" " || event.code==="Space") || event.altKey || event.metaKey)return;
  const kind=event.ctrlKey ? "columns" : event.shiftKey ? "rows" : null;
  if(!kind || !headersOn() || session.state.editing || composing || event.isComposing || event.keyCode===229)return;
  event.preventDefault();event.stopPropagation();
  if(pendingEntry){notice("請先完成或取消目前的輸入。",true);return;}
  const range=session.state.selection;
  if(!range)return;
  const [first,last]=kind==="columns" ? [range.column,range.whole==="rows" || range.whole==="sheet" ? range.column : range.endColumn]
    : [range.row,range.whole==="columns" || range.whole==="sheet" ? range.row : range.endRow];
  cancelDrag();void selectWhole(kind,first,last).then(()=>focusGrid());
}
ui["cell-editor"].addEventListener("keydown",wholeKey);
ui.viewport.addEventListener("keydown",event=>{if(event.target!==ui["cell-editor"])wholeKey(event);});
ui.viewport.addEventListener("pointerdown",event=>{
  if(!session || event.button!==0 || event.target===ui["cell-editor"] || !inViewport(event))return;
  // A point taken during a zoom would be converted at the old zoom and hit-tested at the new one (Codex review 2026-11-07).
  if(zooming){event.preventDefault();return;}
  if(pendingEntry){event.preventDefault();notice("正在接收前一個儲存格的輸入，請稍候。",true);return;}
  const slot=pointSlot();
  if(slot){event.preventDefault();startPoint(event,slot);return;}
  if(browsing()){event.preventDefault();notice(BROWSING_NOTICE,true);return;}
  pointed=false;
  cancelDrag();
  const [x,y]=point(event), current={owner:session,generation:gesture,pointer:event.pointerId,active:true,latest:null,pumping:false};
  drag=dragWork=current;ui.viewport.setPointerCapture(event.pointerId);
  current.start=action(()=>current.owner.selectAt(x,y,{extend:event.shiftKey,valid:()=>current.generation===gesture}));
  focusGrid();
  void current.start.then(()=>{if(!current.active && !current.pumping && current.generation===gesture)focusGrid();});
});
ui.viewport.addEventListener("pointermove",event=>{
  if(!drag || event.pointerId!==drag.pointer || !inViewport(event))return;
  drag.latest=point(event);void extendDrag(drag);
});
ui.viewport.addEventListener("pointerup",event=>{
  if(!drag || event.pointerId!==drag.pointer)return;
  const current=drag;current.active=false;drag=null;
  if(inViewport(event))current.latest=point(event);
  if(ui.viewport.hasPointerCapture(event.pointerId))ui.viewport.releasePointerCapture(event.pointerId);
  void extendDrag(current);
});
ui.viewport.addEventListener("pointercancel",()=>{cancelDrag();focusGrid();});
ui.viewport.addEventListener("lostpointercapture",event=>{if(drag?.pointer===event.pointerId)cancelDrag();});
window.addEventListener("blur",cancelDrag);
for(const name of ["keydown","beforeinput","compositionstart","compositionend","pointerdown"])
  window.addEventListener(name,()=>autosave?.activity(),{capture:true});
ui.viewport.addEventListener("pointermove",()=>{if(drag)autosave?.activity();});
document.addEventListener("visibilitychange",()=>{if(document.hidden)void autosave?.flush("hidden");});
function gridKey(event) {
  if(!session || session.state.editing || composing || event.isComposing || event.keyCode===229 || event.ctrlKey || event.metaKey || event.altKey)return;
  const direction={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];
  if(!direction)return;
  if(pendingEntry){event.preventDefault();return;}
  event.preventDefault();cancelDrag();
  void action(async()=>{const cell=await session.moveSelection(...direction,{extend:event.shiftKey});revealCell(cell);focusGrid();});
}
ui.viewport.addEventListener("keydown",gridKey);
// SPEC-P-calc-sheets 2.3: a click (or a drag) inserts the reference; the edited cell and the selection stay.
function pointRange(anchor,focus) {
  if(anchor.column===focus.column && anchor.row===focus.row)
    return {range:{part:anchor.part,column:anchor.column,row:anchor.row},box:anchor};
  const x0=Math.min(anchor.xTwips,focus.xTwips),y0=Math.min(anchor.yTwips,focus.yTwips);
  return {range:{part:anchor.part,column:Math.min(anchor.column,focus.column),row:Math.min(anchor.row,focus.row),
      endColumn:Math.max(anchor.endColumn,focus.endColumn),endRow:Math.max(anchor.endRow,focus.endRow)},
    box:{xTwips:x0,yTwips:y0,widthTwips:Math.max(anchor.xTwips+anchor.widthTwips,focus.xTwips+focus.widthTwips)-x0,
      heightTwips:Math.max(anchor.yTwips+anchor.heightTwips,focus.yTwips+focus.heightTwips)-y0}};
}
function applyPoint(current,focus) {
  if(pointWork!==current && current.active)return;
  const {range,box}=pointRange(current.anchor,focus),s=session.state;
  const slot=current.inserted ? {start:pointRef.start,end:pointRef.end,field:current.slot.field} : current.slot;
  try { insertReference(slot,sheetReference(sheetNames(s),s.cell.part,range)); } catch(error){errorNotice(error);return;}
  current.inserted=true;current.focus=focus;pointBox={part:range.part,...box};
  render(session.state);
}
function startPoint(event,slot) {
  cancelDrag();pointed=true;
  const [x,y]=point(event),current={pointer:event.pointerId,slot,anchor:null,focus:null,latest:null,active:true,pumping:false,inserted:false};
  pointWork=current;ui.viewport.setPointerCapture(event.pointerId);pointBusy++;
  current.start=action(()=>session.pointAt(x,y,{valid:()=>pointWork===current})).then(cell=>{
    if(cell){current.anchor=cell;applyPoint(current,cell);}
    return cell;
  }).finally(()=>pointBusy--);
}
async function pumpPoint(current) {
  if(current.pumping)return;
  current.pumping=true;pointBusy++;
  try {
    if(!await current.start)return;
    while(current.latest) {
      const [x,y]=current.latest;current.latest=null;
      const cell=await action(()=>session.pointAt(x,y,{valid:()=>true}));
      if(cell && (cell.column!==current.focus?.column || cell.row!==current.focus?.row))applyPoint(current,cell);
    }
  } finally {
    current.pumping=false;pointBusy--;
    if(!current.active){if(pointWork===current)pointWork=null;render(session.state);}
  }
}
ui.viewport.addEventListener("pointermove",event=>{
  if(!pointWork || event.pointerId!==pointWork.pointer || !inViewport(event))return;
  pointWork.latest=point(event);void pumpPoint(pointWork);
});
for(const name of ["pointerup","pointercancel"])
  ui.viewport.addEventListener(name,event=>{
    if(!pointWork || event.pointerId!==pointWork.pointer)return;
    const current=pointWork;current.active=false;
    if(name==="pointerup" && inViewport(event))current.latest=point(event);
    if(ui.viewport.hasPointerCapture(event.pointerId))ui.viewport.releasePointerCapture(event.pointerId);
    void pumpPoint(current);
  });
ui.viewport.addEventListener("dblclick",event=>{
  if(!session || event.target===ui["cell-editor"])return;
  if(zooming){event.preventDefault();return;}
  // The second click of a double click on a pointed cell is a point too, never an edit of that cell.
  if(pointed || browsing()){event.preventDefault();return;}
  if(pendingEntry){event.preventDefault();notice("請先完成或取消目前的輸入。",true);focusGrid();return;}
  event.preventDefault();cancelDrag();const [x,y]=point(event);
  void action(async()=>{
    await session.selectAt(x,y);session.beginEdit("inline");
    ui["cell-editor"].focus({preventScroll:true});
    ui["cell-editor"].setSelectionRange(ui["cell-editor"].value.length,ui["cell-editor"].value.length);
  });
});
ui.viewport.addEventListener("scroll",()=>{if(session)render(session.state);void paint();});
window.addEventListener("resize",()=>void paint());
window.addEventListener("keydown",event=>{
  if(pendingEntry && event.key==="Escape" && !composing && !event.isComposing && event.keyCode!==229) {
    event.preventDefault();pendingEntry=null;session.cancelEdit();focusGrid();return;
  }
  if(!session || event.isComposing || event.keyCode===229 || !(event.ctrlKey||event.metaKey) || event.repeat)return;
  const key=event.key.toLowerCase();
  // SPEC-P-calc-copy 2.4: Ctrl+C / Ctrl+Insert on the grid copies the selection; in a field it is the browser's own copy.
  if((key==="c" || key==="insert") && session.state.copySupported) {
    const active=document.activeElement;
    if(session.state.editing!==null || pendingEntry!==null || composing
        || (active && active!==ui["cell-editor"] && active!==ui.viewport && active.matches?.("input,textarea,select,[contenteditable]")))return;
    event.preventDefault();void copyCells();return;
  }
  // Ctrl+Z / Ctrl+Y fall through: in the formula bar they are its own text undo, and walk() refuses the document's.
  if(browsing() && ["s","b","i","u"].includes(key)){event.preventDefault();notice(BROWSING_NOTICE,true);return;}
  if(key==="s"){event.preventDefault();void action(()=>save());return;}
  // SPEC-P-calc-undo 4.3: the document's undo from the grid; inside an entry, the formula bar or the address box the
  // field keeps its own text undo.  Without the capability nothing changes from before.
  if((key==="z" || key==="y") && session.state.undoSupported) {
    const field=[ui["formula-input"],ui["cell-address"]].includes(document.activeElement);
    if(field || session.state.editing!==null || pendingEntry!==null)return;
    event.preventDefault();walk(key==="y" || event.shiftKey ? "redo" : "undo");return;
  }
  const format={b:"bold",i:"italic",u:"underline"}[key];
  if(format){event.preventDefault();if(pendingEntry){notice("請先完成或取消目前的輸入。",true);return;}void action(()=>toggleFormat(format));}
});
// SPEC-P-calc-copy 3.3: the core's own copy text for the selection, written to the clipboard as plain text; 9.1.4: with the
// core's text/html beside it when the engine gives one and the browser has ClipboardItem, plain text alone otherwise.
let copyGeneration=0;
async function writeClipboard(result) {
  const generation=++copyGeneration;
  let refused=null;
  if(typeof result.htmlText==="string" && typeof globalThis.ClipboardItem==="function" && navigator.clipboard?.write) {
    try {
      await navigator.clipboard.write([new ClipboardItem({"text/plain":new Blob([result.plainText],{type:"text/plain"}),
        "text/html":new Blob([result.htmlText],{type:"text/html"})})]);
      return {formats:["text/plain","text/html"],htmlRefused:null};
    } catch(error) {refused=String(error?.name || error);}
    // A newer Ctrl+C has written since: its content stands (Codex review 2026-11-07).
    if(generation!==copyGeneration)return {formats:[],htmlRefused:refused,superseded:true};
  }
  await navigator.clipboard.writeText(result.plainText);
  return {formats:["text/plain"],htmlRefused:refused};
}
function copyLabel(range) {
  if(range.whole==="sheet")return "整張工作表";
  if(range.whole==="columns")return range.column===range.endColumn ? `${columnName(range.column)} 欄`
    : `${columnName(range.column)} 到 ${columnName(range.endColumn)} 欄`;
  if(range.whole==="rows")return range.row===range.endRow ? `第 ${range.row+1} 列` : `第 ${range.row+1} 到 ${range.endRow+1} 列`;
  const first=cellAddress(range.column,range.row);
  return range.endColumn===range.column && range.endRow===range.row ? first : `${first}:${cellAddress(range.endColumn,range.endRow)}`;
}
async function copyCells() {
  let result;
  try { result=await session.copySelection(); } catch(error) {
    notice(error.code==="COPY_UNAVAILABLE" ? "這個範圍沒有可以複製的文字。"
      : error.code==="RANGE_TOO_LARGE" ? "一次最多可複製 65,536 個儲存格，請縮小選取範圍（整欄、整列與整張工作表不受此限）。"
      : `無法複製：${error.message || error}`,true);
    return;
  }
  try { record.lastCopy=await writeClipboard(result); } catch(error) {
    record.lastCopy={formats:[],error:String(error?.name || error)};
    notice(`瀏覽器沒有讓頁面寫入剪貼簿（${error?.name || error}），請再按一次 Ctrl+C。`,true);
    return;
  }
  notice(`已複製 ${copyLabel(result.range)}`);
}
const unsaved=()=>pendingEntry!==null || session?.hasUnsavedEdits()===true;
if(HOST?.watchUnsaved)HOST.watchUnsaved(unsaved);
else window.addEventListener("beforeunload",event=>{if(unsaved()){event.preventDefault();event.returnValue="";}});
document.documentElement.setAttribute("data-litecore-page-guard","own");
window.addEventListener("pagehide",()=>{autosave?.dispose();void session?.close();});
if(HOST) {
  ui["open-file"].hidden=true;
  record.ready=action(async()=>{
    if(typeof HOST.load!=="function" || typeof HOST.save!=="function")throw new Error("無法連接文件的開啟與儲存服務。");
    const source=await HOST.load();
    return openBytes(source.bytes,source.name,{readOnly:source.readOnly===true || source.lockRefused===true});
  });
}
