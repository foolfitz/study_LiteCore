import { CalcDocumentEngine, CELL_FORMATS } from "./spreadsheet-shell/calc-document-sdk.js";
import { CalcEditorSession, inputIntent } from "./spreadsheet-shell/calc-editor-session.js";

const ENGINE_OPTIONS = Object.freeze({workerUrl:"./profiles/ods-editor-v1/sdk-worker.js",timeoutMs:60000});
const HOST = globalThis.liteCoreHost ?? null;
const diagnostics = new URLSearchParams(location.search).get("diagnostics") === "1";
const $ = id => document.getElementById(id);
const ui = Object.fromEntries(["file-input","open-file","save-button","cell-address","formula-input",
  "cancel-button","commit-button","viewport","surface","tiles","selection","cell-editor","empty",
  "tab-strip","state-pill","selection-label","s-doc","s-revision","toast"].map(id=>[id,$(id)]));
let session = null, composing = false, paintPending = false, lastPaint = null;
const record = globalThis.__calcEditor = {schemaVersion:1,session:null,state:null,events:[],lastSave:null};

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
    PART_HIDDEN:"這張工作表已隱藏。"};
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
  ui["cell-editor"].disabled=!editable || waiting;
  ui["commit-button"].disabled=!editable || !state.editing || waiting;
  ui["cancel-button"].disabled=!state.editing || waiting;
  for(const node of document.querySelectorAll("[data-format]")) {
    node.disabled=!editable || state.busy;
    node.setAttribute("aria-pressed",state.cell?.[node.dataset.format] ? "true":"false");
  }
  if(!composing) {
    if(ui["formula-input"].value!==state.draft)ui["formula-input"].value=state.draft;
    if(ui["cell-editor"].value!==state.draft)ui["cell-editor"].value=state.draft;
  }
  ui.selection.hidden=!ready || !state.cell;
  ui["cell-editor"].hidden=state.editing!=="inline";
  if(state.cell) {
    const address=cellAddress(state.cell.column,state.cell.row);
    ui["cell-address"].value=address;
    ui["selection-label"].textContent=address;
    place(ui.selection,state.cell);place(ui["cell-editor"],state.cell);
  }
  const signature=state.tabs.map(t=>`${t.index}:${t.current}:${t.enabled}`).join("|");
  if(ui["tab-strip"].dataset.signature!==signature) {
    ui["tab-strip"].dataset.signature=signature;
    ui["tab-strip"].replaceChildren(...state.tabs.map(tab=>{
      const button=document.createElement("button");button.type="button";button.className="sheet-tab";
      button.textContent=tab.label;button.dataset.part=tab.index;button.setAttribute("role","tab");
      button.setAttribute("aria-selected",String(tab.current));button.disabled=!tab.enabled;
      button.title=tab.disabledReason || "";
      button.addEventListener("click",()=>action(()=>session.showPart(tab.index)));
      return button;
    }));
  }
  if(state.error) errorNotice(state.error);
  const paintKey=`${state.currentPart}/${state.revision}`;
  if(ready && lastPaint!==paintKey) {
    lastPaint=paintKey;ui.tiles.replaceChildren();void paint();
  }
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
  if(paintPending)return;
  paintPending=true;
  try {
    for(let round=0;round<2;round++) {
      const size=session.scheduler.documentCssSize;
      ui.surface.style.width=`${Math.ceil(size.width)}px`;ui.surface.style.height=`${Math.ceil(size.height)}px`;
      session.scheduleViewport({scrollLeft:ui.viewport.scrollLeft,scrollTop:ui.viewport.scrollTop,
        width:ui.viewport.clientWidth,height:ui.viewport.clientHeight});
      await session.drain();
      if(!session.refit())break;
      ui.tiles.replaceChildren();
    }
  } catch(error) {errorNotice(error);} finally {paintPending=false;}
}
async function openBytes(bytes,name,options={}) {
  if(session?.hasUnsavedEdits() && !confirm("尚有修改未儲存，仍要開啟其他檔案嗎？"))return;
  if(session)await session.close();
  lastPaint=null;ui.tiles.replaceChildren();ui.viewport.scrollTop=0;ui.viewport.scrollLeft=0;
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
  notice(options.readOnly ? "此檔案目前以唯讀開啟。" : "連按兩下儲存格編輯，或使用上方輸入欄。");
  await paint();
  return session.state;
}
record.openBytes=openBytes;
record.ready=Promise.resolve();
async function save() {
  if(!session)return;
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
function focusGrid(){ui.viewport.focus({preventScroll:true});}
ui["open-file"].addEventListener("click",()=>ui["file-input"].click());
ui["file-input"].addEventListener("change",()=>{
  const file=ui["file-input"].files[0];
  if(file)void action(async()=>openBytes(await file.arrayBuffer(),file.name));
});
ui["save-button"].addEventListener("click",()=>action(save));
ui["commit-button"].addEventListener("click",()=>action(async()=>{await session.commit();focusGrid();}));
ui["cancel-button"].addEventListener("click",()=>{session.cancelEdit();focusGrid();});
for(const node of document.querySelectorAll("[data-format]"))
  node.addEventListener("click",()=>action(()=>session.setFormat(node.dataset.format,!session.state.cell[node.dataset.format])));
for(const node of [ui["formula-input"],ui["cell-editor"]]) {
  node.addEventListener("compositionstart",()=>{composing=true;});
  node.addEventListener("compositionend",()=>{composing=false;void action(()=>session.setDraft(node.value));});
  node.addEventListener("input",()=>action(()=>session.setDraft(node.value)));
  node.addEventListener("keydown",event=>{
    const intent=inputIntent(event);if(!intent)return;
    event.preventDefault();
    if(intent==="cancel"){session.cancelEdit();focusGrid();}
    else void action(async()=>{await session.commit();focusGrid();});
  });
}
ui["formula-input"].addEventListener("focus",()=>action(()=>session.beginEdit("formula")));
ui["cell-address"].addEventListener("keydown",event=>{
  if(event.key!=="Enter")return;event.preventDefault();
  const match=/^([A-Z]+)([1-9][0-9]*)$/.exec(ui["cell-address"].value.trim().toUpperCase());
  if(!match){notice("請輸入儲存格位址，例如 A1。",true);return;}
  let column=0;for(const char of match[1])column=column*26+char.charCodeAt(0)-64;
  void action(async()=>{await session.selectCell(column-1,Number(match[2])-1);focusGrid();});
});
function point(event){const rect=ui.surface.getBoundingClientRect();return[Math.max(0,Math.round((event.clientX-rect.left)*15)),Math.max(0,Math.round((event.clientY-rect.top)*15))];}
ui.viewport.addEventListener("click",event=>{
  if(!session || event.target===ui["cell-editor"] || event.detail!==1)return;
  const [x,y]=point(event);void action(()=>session.selectAt(x,y));
});
ui.viewport.addEventListener("dblclick",event=>{
  if(!session || event.target===ui["cell-editor"])return;
  event.preventDefault();const [x,y]=point(event);
  void action(async()=>{
    await session.selectAt(x,y);session.beginEdit("inline");
    ui["cell-editor"].focus({preventScroll:true});
    ui["cell-editor"].setSelectionRange(ui["cell-editor"].value.length,ui["cell-editor"].value.length);
  });
});
ui.viewport.addEventListener("scroll",()=>void paint());
window.addEventListener("resize",()=>void paint());
window.addEventListener("keydown",event=>{
  if(!session || event.isComposing || event.keyCode===229 || !(event.ctrlKey||event.metaKey) || event.repeat)return;
  const key=event.key.toLowerCase();
  if(key==="s"){event.preventDefault();void action(save);return;}
  const format={b:"bold",i:"italic",u:"underline"}[key];
  if(format){event.preventDefault();void action(()=>session.setFormat(format,!session.state.cell[format]));}
});
const unsaved=()=>session?.hasUnsavedEdits()===true;
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
