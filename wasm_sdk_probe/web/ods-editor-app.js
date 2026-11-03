import { CalcDocumentEngine, CELL_INPUT_LIMIT } from "./spreadsheet-shell/calc-document-sdk.js";
import { CalcEditorSession, inputIntent } from "./spreadsheet-shell/calc-editor-session.js";
import { CalcAutosave } from "./spreadsheet-shell/calc-autosave.js";

const ENGINE_OPTIONS = Object.freeze({workerUrl:"./profiles/ods-editor-v4/sdk-worker.js",timeoutMs:60000});
const HOST = globalThis.liteCoreHost ?? null;
const diagnostics = new URLSearchParams(location.search).get("diagnostics") === "1";
const $ = id => document.getElementById(id);
const ui = Object.fromEntries(["file-input","open-file","save-button","undo-button","redo-button","cell-address","formula-input",
  "cancel-button","commit-button","viewport","surface","tiles","selection","active-cell","cell-editor","empty",
  "tab-strip","state-pill","autosave-status","selection-label","s-doc","s-revision","toast"].map(id=>[id,$(id)]));
let session = null, composing = false, paintPending = false, paintAgain = false, lastPaint = null, restoreGridFocus = false;
let pendingEntry = null, autosave = null, manualSaves = 0;
// SPEC-P-demo-batch-1 2: each sheet keeps its view for as long as the document
// is open. A switch does not paint until the session has settled on the new
// sheet, and `pendingView` is applied inside paint, after the surface has its
// new size: scrolling first would clamp to the sheet being left.
const sheetViews = new Map();
let sheetSwitching = false, pendingView = null;
const record = globalThis.__calcEditor = {schemaVersion:1,session:null,state:null,events:[],lastSave:null};
if(diagnostics)record.inputState=()=>({composing,pending:pendingEntry ? {replace:pendingEntry.replace,invalid:pendingEntry.invalid===true,textLength:pendingEntry.text.length}:null});

function cellAddress(column,row) {
  let text="";
  for(let n=column;n>=0;n=Math.floor(n/26)-1) text=String.fromCharCode(65+n%26)+text;
  return text+(row+1);
}
function notice(text,error=false) {
  ui.toast.textContent=text;
  ui.toast.classList.toggle("error",error);
}
function errorNotice(error) {
  const messages={READ_ONLY:"這個儲存格無法編輯。",CELL_TEXT_TOO_LONG:"儲存格內容超過 32,767 個字元，尚未寫入。",
    STALE_REVISION:"文件狀態已改變；你的輸入已保留，請先儲存或重新開啟。",
    MUTATION_OUTCOME_UNKNOWN:"無法確認剛才的修改，請保留此頁，避免遺失內容。",
    PART_HIDDEN:"這張工作表已隱藏。",RANGE_FORMAT_UNSUPPORTED:"目前的引擎尚未支援範圍格式。",
    RANGE_TOO_LARGE:"一次最多可設定 65,536 個儲存格的格式，請縮小選取範圍。",
    RANGE_MERGE_BOUNDARY:"選取範圍跨過合併格邊界，請選取完整的合併格後重試。",
    RANGE_PROTECTED:"選取範圍含有受保護的儲存格，無法變更格式。"};
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
  node.style.left=`${cell.xTwips/15}px`;node.style.top=`${cell.yTwips/15}px`;
  node.style.width=`${Math.max(1,cell.widthTwips/15)}px`;
  node.style.height=`${Math.max(1,cell.heightTwips/15)}px`;
}
function formatAvailable(state) {
  return state.state==="ready" && state.cell?.writable===true && !state.readOnly && !state.uncertain
    && !state.busy && !state.selectionPending && !pendingEntry && !dragWork
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
  // SPEC-P-calc-undo 4.3: shown when the profile carries undo; usable whenever a write would be, and with an entry
  // pending too (undo then drops the entry).
  ui["undo-button"].hidden=ui["redo-button"].hidden=!state.undoSupported;
  ui["undo-button"].disabled=ui["redo-button"].disabled=!ready || state.readOnly || state.uncertain || waiting
    || state.selectionPending;
  ui["cell-address"].disabled=!ready || state.busy;
  ui["formula-input"].disabled=!editable || waiting;
  ui["cell-editor"].disabled=state.selectionPending || pendingEntry
    ? !ready || state.readOnly || state.uncertain : !editable || waiting;
  ui["commit-button"].disabled=!editable || !state.editing || waiting;
  ui["cancel-button"].disabled=!state.editing || waiting;
  renderFormatControls(state);
  if(!composing) {
    if(ui["formula-input"].value!==state.draft)ui["formula-input"].value=state.draft;
    if(!pendingEntry && ui["cell-editor"].value!==state.draft)ui["cell-editor"].value=state.draft;
  }
  ui.selection.hidden=!ready || !state.cell;
  ui["active-cell"].hidden=ui.selection.hidden;
  ui["cell-editor"].hidden=!ready || !state.cell;
  ui["cell-editor"].classList.toggle("grid-input",state.editing!=="inline");
  if(state.cell) {
    const address=cellAddress(state.cell.column,state.cell.row);
    if(document.activeElement!==ui["cell-address"])ui["cell-address"].value=address;
    const range=state.selection;
    ui["selection-label"].textContent=range?.multiple
      ? `${cellAddress(range.column,range.row)}:${cellAddress(range.endColumn,range.endRow)} · 作用中 ${address}${state.rangeFormattingSupported ? "" : "（範圍格式尚未支援）"}` : address;
    ui["selection-label"].title="範圍依兩端儲存格框選；交界合併格不自動擴張。";
    place(ui.selection,range || state.cell);place(ui["active-cell"],state.cell);place(ui["cell-editor"],state.cell);
    if(state.editing!=="inline") {
      // A focused, real textarea receives beforeinput and IME without moving
      // focus midway through the first character. Keep its idle caret in view.
      ui["cell-editor"].style.left=`${Math.max(ui.viewport.scrollLeft,Math.min(state.cell.xTwips/15,ui.viewport.scrollLeft+ui.viewport.clientWidth-4))}px`;
      ui["cell-editor"].style.top=`${Math.max(ui.viewport.scrollTop,Math.min(state.cell.yTwips/15,ui.viewport.scrollTop+ui.viewport.clientHeight-4))}px`;
      if(!composing && !pendingEntry)ui["cell-editor"].value="";
    }
  }
  const signature=state.tabs.map(t=>`${t.index}:${t.current}:${t.enabled}`).join("|");
  if(ui["tab-strip"].dataset.signature!==signature) {
    ui["tab-strip"].dataset.signature=signature;
    ui["tab-strip"].replaceChildren(...state.tabs.map(tab=>{
      const button=document.createElement("button");button.type="button";button.className="sheet-tab";
      button.textContent=tab.label;button.dataset.part=tab.index;button.setAttribute("role","tab");
      button.setAttribute("aria-selected",String(tab.current));button.disabled=!tab.enabled;
      button.title=tab.disabledReason || "";
      button.addEventListener("click",()=>{
        if(pendingEntry){notice("請先完成或取消目前的輸入。",true);focusGrid();return;}
        cancelDrag();void action(async()=>{await showSheet(tab.index);focusGrid();});
      });
      return button;
    }));
  }
  if(state.error) errorNotice(state.error);
  const paintKey=`${state.currentPart}/${state.revision}`;
  if(ready && !sheetSwitching && lastPaint!==paintKey) {
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
async function paint() {
  if(!session || session.state.state!=="ready" || sheetSwitching)return;
  if(paintPending){paintAgain=true;return;}
  paintPending=true;
  const view=pendingView;
  try {
    for(let round=0;round<2;round++) {
      const size=session.scheduler.documentCssSize;
      const focus=session.state.selection?.focus;
      ui.surface.style.width=`${Math.ceil(Math.max(size.width,focus ? (focus.xTwips+focus.widthTwips)/15 : 0))}px`;
      ui.surface.style.height=`${Math.ceil(Math.max(size.height,focus ? (focus.yTwips+focus.heightTwips)/15 : 0))}px`;
      if(view) {
        ui.surface.style.minWidth=view.minWidth;ui.surface.style.minHeight=view.minHeight;
        ui.viewport.scrollLeft=view.scrollLeft;ui.viewport.scrollTop=view.scrollTop;
      }
      session.scheduleViewport({scrollLeft:ui.viewport.scrollLeft,scrollTop:ui.viewport.scrollTop,
        width:ui.viewport.clientWidth,height:ui.viewport.clientHeight});
      await session.drain();
      if(!session.refit())break;
      ui.tiles.replaceChildren();
    }
    if(pendingView===view)pendingView=null;
  } catch(error) {errorNotice(error);} finally {
    paintPending=false;
    if(paintAgain){paintAgain=false;void paint();}
  }
}
async function openBytes(bytes,name,options={}) {
  if((pendingEntry || session?.hasUnsavedEdits()) && !confirm("尚有修改未儲存，仍要開啟其他檔案嗎？"))return;
  autosave?.dispose();autosave=null;
  pendingEntry=null;cancelDrag();
  if(session)await session.close();
  lastPaint=null;ui.tiles.replaceChildren();ui.viewport.scrollTop=0;ui.viewport.scrollLeft=0;
  ui.surface.style.minWidth="";ui.surface.style.minHeight="";
  sheetViews.clear();pendingView=null;
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
function focusGrid(){
  const node=ui["cell-editor"].disabled ? ui.viewport : ui["cell-editor"];
  node.focus({preventScroll:true});
}
function revealCell(cell) {
  if(!cell)return;
  const left=cell.xTwips/15,top=cell.yTwips/15,right=left+cell.widthTwips/15,bottom=top+cell.heightTwips/15;
  ui.surface.style.minWidth=`${Math.ceil(right)}px`;ui.surface.style.minHeight=`${Math.ceil(bottom)}px`;
  if(left<ui.viewport.scrollLeft)ui.viewport.scrollLeft=Math.floor(left);
  else if(right>ui.viewport.scrollLeft+ui.viewport.clientWidth)ui.viewport.scrollLeft=Math.ceil(right-ui.viewport.clientWidth);
  if(top<ui.viewport.scrollTop)ui.viewport.scrollTop=Math.floor(top);
  else if(bottom>ui.viewport.scrollTop+ui.viewport.clientHeight)ui.viewport.scrollTop=Math.ceil(bottom-ui.viewport.clientHeight);
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
ui["save-button"].addEventListener("click",()=>action(()=>save()));
ui["commit-button"].addEventListener("click",()=>action(async()=>{await session.commit();focusGrid();}));
ui["cancel-button"].addEventListener("click",()=>{session.cancelEdit();focusGrid();});
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
    if(intent==="cancel"){session.cancelEdit();focusGrid();}
    else void action(async()=>{await session.commit();focusGrid();});
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
  const match=/^([A-Z]+)([1-9][0-9]*)$/.exec(ui["cell-address"].value.trim().toUpperCase());
  if(!match){notice("請輸入儲存格位址，例如 A1。",true);return;}
  let column=0;for(const char of match[1])column=column*26+char.charCodeAt(0)-64;
  cancelDrag();void action(async()=>{const cell=await session.selectCell(column-1,Number(match[2])-1);revealCell(cell);focusGrid();});
});
function point(event){const rect=ui.surface.getBoundingClientRect();return[Math.max(0,Math.round((event.clientX-rect.left)*15)),Math.max(0,Math.round((event.clientY-rect.top)*15))];}
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
ui.viewport.addEventListener("pointerdown",event=>{
  if(!session || event.button!==0 || event.target===ui["cell-editor"] || !inViewport(event))return;
  if(pendingEntry){event.preventDefault();notice("正在接收前一個儲存格的輸入，請稍候。",true);return;}
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
ui.viewport.addEventListener("dblclick",event=>{
  if(!session || event.target===ui["cell-editor"])return;
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
