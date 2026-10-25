Review only this final Calc buffer-transfer/save code. Reason briefly, no extended thinking, no tools. Report at most three concrete data-loss or wrong-target bugs with plausible reproduction, or say no blocker in this scope. The page has one JS thread; beginEdit and setDraft are synchronous and validate writable target/UTF-16 length before mutation. All engine writes run through a serialized chain with explicit active cell and expected revision. New pointer/tab/A1/format/double-click while pendingEntry exists are refused; selection failures permanently mark the entry invalid, and Escape clears retained input. Pointer pump lifetime prevents transfer before final endpoint read. Enter commits without automatic movement. Do not demand autosave, multicell writes or unimplemented undo. Output English.

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
