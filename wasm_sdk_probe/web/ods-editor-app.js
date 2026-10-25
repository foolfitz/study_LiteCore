import { CalcDocumentEngine, CELL_INPUT_LIMIT } from "./spreadsheet-shell/calc-document-sdk.js";
import { CalcEditorSession, inputIntent } from "./spreadsheet-shell/calc-editor-session.js";

const ENGINE_OPTIONS = Object.freeze({workerUrl:"./profiles/ods-editor-v1/sdk-worker.js",timeoutMs:60000});
const HOST = globalThis.liteCoreHost ?? null;
const diagnostics = new URLSearchParams(location.search).get("diagnostics") === "1";
const $ = id => document.getElementById(id);
const ui = Object.fromEntries(["file-input","open-file","save-button","cell-address","formula-input",
  "cancel-button","commit-button","viewport","surface","tiles","selection","active-cell","cell-editor","empty",
  "tab-strip","state-pill","selection-label","s-doc","s-revision","toast"].map(id=>[id,$(id)]));
let session = null, composing = false, paintPending = false, paintAgain = false, lastPaint = null, restoreGridFocus = false;
let pendingEntry = null;
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
    PART_HIDDEN:"這張工作表已隱藏。",RANGE_FORMAT_UNSUPPORTED:"目前尚未支援整個選取範圍的格式，請先選取單一儲存格。"};
  notice(messages[error.code] || error.message || String(error),true);
}
async function action(work) {
  try { return await work(); } catch(error) { errorNotice(error); return null; }
}
function place(node,cell) {
  node.style.left=`${cell.xTwips/15}px`;node.style.top=`${cell.yTwips/15}px`;
  node.style.width=`${Math.max(1,cell.widthTwips/15)}px`;
  node.style.height=`${Math.max(1,cell.heightTwips/15)}px`;
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
  ui["cell-address"].disabled=!ready || state.busy;
  ui["formula-input"].disabled=!editable || waiting;
  ui["cell-editor"].disabled=state.selectionPending || pendingEntry
    ? !ready || state.readOnly || state.uncertain : !editable || waiting;
  ui["commit-button"].disabled=!editable || !state.editing || waiting;
  ui["cancel-button"].disabled=!state.editing || waiting;
  for(const node of document.querySelectorAll("[data-format]")) {
    node.disabled=!editable || state.busy || state.selection?.multiple || pendingEntry!==null;
    node.setAttribute("aria-pressed",state.selection?.multiple ? "false" : state.cell?.[node.dataset.format] ? "true":"false");
    node.title=state.selection?.multiple ? "目前尚未支援範圍格式，請先選取單一儲存格。" : node.getAttribute("aria-label");
  }
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
    ui["cell-address"].value=address;
    const range=state.selection;
    ui["selection-label"].textContent=range?.multiple
      ? `${cellAddress(range.column,range.row)}:${cellAddress(range.endColumn,range.endRow)} · 作用中 ${address}（範圍格式尚未支援）` : address;
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
        cancelDrag();void action(async()=>{await session.showPart(tab.index);focusGrid();});
      });
      return button;
    }));
  }
  if(state.error) errorNotice(state.error);
  const paintKey=`${state.currentPart}/${state.revision}`;
  if(ready && lastPaint!==paintKey) {
    lastPaint=paintKey;ui.tiles.replaceChildren();void paint();
  }
  if(!waiting && restoreGridFocus) {
    const active=document.activeElement;
    restoreGridFocus=false;
    if(active===document.body || active===ui.viewport || active===ui["cell-editor"])focusGrid();
  }
  if(pendingEntry && !state.selectionPending && !state.busy && !composing)queueMicrotask(flushPendingEntry);
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
async function paint() {
  if(!session || session.state.state!=="ready")return;
  if(paintPending){paintAgain=true;return;}
  paintPending=true;
  try {
    for(let round=0;round<2;round++) {
      const size=session.scheduler.documentCssSize;
      const focus=session.state.selection?.focus;
      ui.surface.style.width=`${Math.ceil(Math.max(size.width,focus ? (focus.xTwips+focus.widthTwips)/15 : 0))}px`;
      ui.surface.style.height=`${Math.ceil(Math.max(size.height,focus ? (focus.yTwips+focus.heightTwips)/15 : 0))}px`;
      session.scheduleViewport({scrollLeft:ui.viewport.scrollLeft,scrollTop:ui.viewport.scrollTop,
        width:ui.viewport.clientWidth,height:ui.viewport.clientHeight});
      await session.drain();
      if(!session.refit())break;
      ui.tiles.replaceChildren();
    }
  } catch(error) {errorNotice(error);} finally {
    paintPending=false;
    if(paintAgain){paintAgain=false;void paint();}
  }
}
async function openBytes(bytes,name,options={}) {
  if((pendingEntry || session?.hasUnsavedEdits()) && !confirm("尚有修改未儲存，仍要開啟其他檔案嗎？"))return;
  pendingEntry=null;cancelDrag();
  if(session)await session.close();
  lastPaint=null;ui.tiles.replaceChildren();ui.viewport.scrollTop=0;ui.viewport.scrollLeft=0;
  ui.surface.style.minWidth="";ui.surface.style.minHeight="";
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
  notice(options.readOnly ? "此檔案目前以唯讀開啟。" : "直接輸入取代內容；F2 編輯；拖曳或 Shift＋方向鍵選取範圍。");
  await paint();
  return session.state;
}
record.openBytes=openBytes;
record.ready=Promise.resolve();
async function save() {
  if(!session)return;
  await session.whenIdle();
  const entryWasPending=pendingEntry!==null,flushed=await flushPendingEntry();
  if(entryWasPending && flushed!==true){notice("輸入尚未接回儲存格，請先完成或取消輸入。",true);return;}
  if(pendingEntry || composing){notice("請先完成輸入或取消尚未寫入的內容，再儲存。",true);return;}
  const saved=await session.save(async(bytes,{name})=>{
    if(HOST)return HOST.save(bytes,{name,trigger:"manual"});
    const url=URL.createObjectURL(new Blob([bytes],{type:"application/vnd.oasis.opendocument.spreadsheet"}));
    const link=document.createElement("a");link.href=url;link.download=name;link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    return{name};
  });
  record.lastSave={revision:saved.revision,bytes:saved.bytes.byteLength,result:saved.result};
  if(diagnostics)record.lastExport=saved.bytes;
  notice(HOST ? "已存回試算表。":"已交給瀏覽器下載，請確認檔案已存好。");
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
ui["save-button"].addEventListener("click",()=>action(save));
ui["commit-button"].addEventListener("click",()=>action(async()=>{await session.commit();focusGrid();}));
ui["cancel-button"].addEventListener("click",()=>{session.cancelEdit();focusGrid();});
for(const node of document.querySelectorAll("[data-format]"))
  node.addEventListener("click",()=>{
    if(pendingEntry){notice("請先完成或取消目前的輸入。",true);return;}
    void action(()=>session.setFormat(node.dataset.format,!session.state.cell[node.dataset.format]));
  });
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
  if(key==="s"){event.preventDefault();void action(save);return;}
  const format={b:"bold",i:"italic",u:"underline"}[key];
  if(format){event.preventDefault();if(pendingEntry){notice("請先完成或取消目前的輸入。",true);return;}void action(()=>session.setFormat(format,!session.state.cell[format]));}
});
const unsaved=()=>pendingEntry!==null || session?.hasUnsavedEdits()===true;
if(HOST?.watchUnsaved)HOST.watchUnsaved(unsaved);
else window.addEventListener("beforeunload",event=>{if(unsaved()){event.preventDefault();event.returnValue="";}});
document.documentElement.setAttribute("data-litecore-page-guard","own");
window.addEventListener("pagehide",()=>{void session?.close();});
if(HOST) {
  ui["open-file"].hidden=true;
  record.ready=action(async()=>{
    if(typeof HOST.load!=="function" || typeof HOST.save!=="function")throw new Error("無法連接文件的開啟與儲存服務。");
    const source=await HOST.load();
    return openBytes(source.bytes,source.name,{readOnly:source.readOnly===true || source.lockRefused===true});
  });
}
