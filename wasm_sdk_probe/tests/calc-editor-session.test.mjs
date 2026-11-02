import assert from "node:assert/strict";
import test from "node:test";
const { CalcEditorSession, inputIntent } = await import(process.env.CALC_SESSION_MODULE || "../spreadsheet-shell/calc-editor-session.js");

async function opened(readOnly=false) {
  const calls=[];
  let formula="原始內容";
  const doc={revision:0,parts:2,documentType:"spreadsheet",partNames:["Sheet1","Sheet2"],partVisible:[true,true],
    currentPart:0,widthTwips:9000,heightTwips:9000,
    async setPart(part){calls.push(["part",part]);this.currentPart=part;return{part,widthTwips:9000,heightTwips:9000};},
    async close(){},async render(){},
    cell(col=0,row=0){return{part:this.currentPart,column:col,row,endColumn:col,endRow:row,input:formula,formula,text:formula,
      writable:true,bold:false,italic:false,underline:false,xTwips:col*1000,yTwips:row*300,widthTwips:999,heightTwips:299};},
    async readCell(col,row){return{cell:this.cell(col,row)};},
    async hitCell(x,y){calls.push(["hit",x,y]);return{cell:this.cell(1,0)};},
    async setCellInput(col,row,text,options){calls.push(["input",this.currentPart,col,row,text,options]);formula=text;this.revision++;return{cell:this.cell(col,row),changed:true};},
    async setCellFormat(col,row,format,enabled){calls.push(["format",format,enabled]);this.revision++;return{cell:{...this.cell(col,row),[format]:enabled},changed:true};},
    async save(options){calls.push(["export",options.format]);return new ArrayBuffer(10);},
  };
  const session=new CalcEditorSession({engineFactory:async()=>({manifest:{capabilities:["open-ods"]},open:async()=>doc,dispose(){}})});
  await session.open({bytes:new ArrayBuffer(8),name:"test.ods",readOnly});
  return{session,doc,calls};
}

test("each sheet keeps its active cell; a sheet not seen before starts at A1 (SPEC-P-demo-batch-1 2)",async()=>{
  const {session}=await opened();
  await session.selectAt(1200,100);
  assert.deepEqual([session.state.cell.part,session.state.cell.column,session.state.cell.row],[0,1,0]);
  await session.showPart(1);
  assert.deepEqual([session.state.cell.part,session.state.cell.column,session.state.cell.row],[1,0,0]);
  await session.showPart(0);
  assert.deepEqual([session.state.cell.part,session.state.cell.column,session.state.cell.row],[0,1,0]);
  // The tab of the sheet already shown does not move the cell.
  await session.showPart(0);
  assert.deepEqual([session.state.cell.part,session.state.cell.column,session.state.cell.row],[0,1,0]);
  await session.close();
});

test("cancelled drafts never enter the engine",async()=>{
  const {session,calls}=await opened();
  session.beginEdit("inline");session.setDraft("取消這份");session.cancelEdit();
  assert.equal(session.state.draft,"原始內容");assert.equal(session.hasUnsavedEdits(),false);
  assert.deepEqual(calls,[]);
  await session.close();
});

test("replacement entry clears only the draft; F2 entry preserves safe model input",async()=>{
  const {session,calls}=await opened();
  session.beginEdit("inline",{replace:true});
  assert.equal(session.state.draft,"");assert.equal(session.state.cell.input,"原始內容");
  assert.equal(session.hasUnsavedEdits(),true);assert.deepEqual(calls,[]);
  session.setDraft("替換");session.cancelEdit();
  session.beginEdit("inline");assert.equal(session.state.draft,"原始內容");
  session.cancelEdit();assert.equal(session.hasUnsavedEdits(),false);
  await session.close();
});

test("changing cells commits the captured original cell before hit testing",async()=>{
  const {session,calls}=await opened();
  session.beginEdit("inline");session.setDraft("第一格");
  await session.selectAt(1200,100);
  assert.equal(calls[0][0],"input");assert.deepEqual(calls[0].slice(1,5),[0,0,0,"第一格"]);
  assert.equal(calls[1][0],"hit");assert.equal(session.state.cell.column,1);
  assert.equal(session.hasUnsavedEdits(),true);
  await session.close();
});

test("readonly prevents drafts, formatting and exports",async()=>{
  const {session,calls}=await opened(true);
  assert.throws(()=>session.beginEdit("formula"),{code:"READ_ONLY"});
  assert.throws(()=>session.setDraft("不應寫入"),{code:"READ_ONLY"});
  await assert.rejects(session.setFormat("bold",true),{code:"READ_ONLY"});
  await assert.rejects(session.save(async()=>{}),{code:"READ_ONLY"});
  assert.deepEqual(calls,[]);await session.close();
});

test("failed host save keeps edits dirty and a retry can save them",async()=>{
  const {session,calls}=await opened();
  session.beginEdit("formula");session.setDraft("已提交但未存回");
  await assert.rejects(session.save(async()=>{throw new Error("offline");}));
  assert.equal(session.hasUnsavedEdits(),true);assert.equal(session.state.draft,"已提交但未存回");
  await session.save(async bytes=>{assert.equal(bytes.byteLength,10);return{name:"test.ods"};});
  assert.equal(session.hasUnsavedEdits(),false);assert.equal(calls.filter(c=>c[0]==="input").length,1);
  await session.close();
});

test("new typing during a host save remains an unsaved draft",async()=>{
  const {session}=await opened();let release,started;
  const begin=new Promise(resolve=>{started=resolve;});
  session.beginEdit("formula");session.setDraft("第一版");
  const save=session.save(async()=>{started();await new Promise(resolve=>{release=resolve;});});
  await begin;session.beginEdit("formula");session.setDraft("第二版");release();await save;
  assert.equal(session.state.draft,"第二版");assert.equal(session.hasUnsavedEdits(),true);
  await session.close();
});

test("committed-only save preserves an active draft and accounts only exported revision",async()=>{
  const {session,calls}=await opened();
  session.beginEdit();session.setDraft("committed");await session.commit();
  assert.equal(session.state.committedDirty,true);
  session.beginEdit("inline");session.setDraft("still editing");
  const selected=session.state.selection;
  await session.save(async()=>({name:"test.ods"}),{commitDraft:false});
  assert.equal(session.state.committedDirty,false);assert.equal(session.state.dirty,true);
  assert.equal(session.state.draft,"still editing");assert.equal(session.state.editing,"inline");
  assert.equal(session.state.selection,selected);
  assert.equal(calls.filter(c=>c[0]==="input").length,1);
  await session.close();
});

test("successor range formats use one explicit native operation and retain both endpoints",async()=>{
  const {session,doc,calls}=await opened();doc.rangeFormattingSupported=true;
  const range=(column,row,endColumn,endRow)=>({part:0,column,row,endColumn,endRow,writable:true,refusalCode:"",bold:null,italic:false,underline:false});
  doc.readRange=async(...a)=>({range:range(...a)});
  doc.setRangeFormat=async(c,r,ec,er,format,enabled,options)=>{
    calls.push(["range",c,r,ec,er,format,enabled,options]);doc.revision++;
    return{range:{...range(c,r,ec,er),[format]:enabled},changed:true};
  };
  await session.selectCell(2,3,{extend:true});
  assert.equal(session.state.rangeFormat.bold,null);
  await session.setFormat("bold",true);
  assert.deepEqual(calls,[ ["range",0,0,2,3,"bold",true,{part:0,expectedRevision:0}] ]);
  assert.equal(session.state.selection.multiple,true);assert.equal(session.state.cell.column,0);
  assert.equal(session.state.selection.focus.column,2);assert.equal(session.state.rangeFormat.bold,true);
  assert.equal(session.state.committedDirty,true);
  await session.close();
});

test("native range refusal retains selection; post-mutation refresh failure locks uncertain state",async()=>{
  const {session,doc}=await opened();doc.rangeFormattingSupported=true;
  doc.readRange=async(c,r,ec,er)=>({range:{part:0,column:c,row:r,endColumn:ec,endRow:er,writable:false,refusalCode:"RANGE_MERGE_BOUNDARY",bold:null,italic:false,underline:false}});
  await session.selectCell(2,3,{extend:true});const selection=session.state.selection;
  doc.setRangeFormat=async()=>{throw Object.assign(new Error("merge"),{code:"RANGE_MERGE_BOUNDARY"});};
  await assert.rejects(session.setFormat("bold",true),{code:"RANGE_MERGE_BOUNDARY"});
  assert.equal(session.state.selection,selection);assert.equal(doc.revision,0);assert.equal(session.state.uncertain,false);
  doc.setRangeFormat=async()=>{doc.revision++;return{range:session.state.rangeFormat};};
  doc.readCell=async()=>{throw new Error("geometry unavailable");};
  await assert.rejects(session.setFormat("bold",true),{code:"MUTATION_OUTCOME_UNKNOWN"});
  assert.equal(session.state.uncertain,true);assert.equal(session.state.dirty,true);
  await session.close();
});

test("a style written and then not read back locks uncertain state, as a format does",async()=>{
  const {session,doc}=await opened();doc.rangeFormattingSupported=true;doc.rangeStylingSupported=true;
  doc.readRange=async(c,r,ec,er)=>({range:{part:0,column:c,row:r,endColumn:ec,endRow:er,writable:true,refusalCode:"",bold:false,italic:false,underline:false}});
  await session.selectCell(2,3,{extend:true});
  doc.setRangeStyle=async()=>{doc.revision++;return{range:session.state.rangeFormat};};
  doc.readCell=async()=>{throw new Error("geometry unavailable");};
  await assert.rejects(session.setStyle("backColor","#ffe599"),{code:"MUTATION_OUTCOME_UNKNOWN"});
  assert.equal(session.state.uncertain,true);assert.equal(session.state.dirty,true);
  await session.close();
});

test("stale revision keeps the draft and does not start a following sheet switch",async()=>{
  const {session,doc,calls}=await opened();
  doc.setCellInput=async()=>{throw Object.assign(new Error("stale"),{code:"STALE_REVISION"});};
  session.beginEdit("inline");session.setDraft("不可丟失");
  await assert.rejects(session.showPart(1),{code:"STALE_REVISION"});
  assert.equal(session.state.draft,"不可丟失");assert.equal(session.hasUnsavedEdits(),true);
  assert.deepEqual(calls,[]);await session.close();
});

test("formatting commits the shared draft first and updates tile revision",async()=>{
  const {session,calls,doc}=await opened();
  session.beginEdit("formula");session.setDraft("粗體內容");await session.setFormat("bold",true);
  assert.deepEqual(calls.map(c=>c[0]),["input","format"]);assert.equal(session.state.cell.bold,true);
  assert.equal(doc.revision,2);await session.close();
});

test("oversized drafts refuse without changing the existing draft",async()=>{
  const {session}=await opened();session.beginEdit("inline");session.setDraft("保留");
  assert.throws(()=>session.setDraft("x".repeat(32768)),{code:"CELL_TEXT_TOO_LONG"});
  assert.equal(session.state.draft,"保留");await session.close();
});

test("selecting a protected cell does not prevent saving earlier edits",async()=>{
  const {session,doc}=await opened();
  session.beginEdit();session.setDraft("已編輯");await session.commit();
  doc.readCell=async()=>({cell:{...doc.cell(),writable:false}});
  await session.selectCell(0,0);
  assert.throws(()=>session.beginEdit(),{code:"READ_ONLY"});
  await session.save(async()=>({name:"test.ods"}));
  assert.equal(session.hasUnsavedEdits(),false);await session.close();
});

test("IME Enter and keyCode 229 never submit; Escape and ordinary Enter do",()=>{
  assert.equal(inputIntent({key:"Enter",isComposing:true}),null);
  assert.equal(inputIntent({key:"Enter",keyCode:229}),null);
  assert.equal(inputIntent({key:"Enter"}),"commit");
  assert.equal(inputIntent({key:"Escape"}),"cancel");
  assert.equal(inputIntent({key:"Enter",shiftKey:true}),null);
});

test("actual host copy outcome marks the exported revision saved while preserving the notice",async()=>{
  const {session}=await opened();session.beginEdit();session.setDraft("衝突副本內容");
  const conflict=Object.assign(new Error("saved to conflict.ods"),{code:"CONFLICT",outcome:"copy",savedAs:"conflict.ods"});
  await assert.rejects(session.save(async()=>{throw conflict;}),error=>error===conflict);
  assert.equal(session.hasUnsavedEdits(),false);
  assert.equal(session.state.error.code,"CONFLICT");
  await session.close();
});

test("a stranded host export remains dirty",async()=>{
  const {session}=await opened();session.beginEdit();session.setDraft("仍未存好");
  const error=Object.assign(new Error("offline"),{code:"HOST_SAVE_FAILED",outcome:"stranded"});
  await assert.rejects(session.save(async()=>{throw error;}));
  assert.equal(session.hasUnsavedEdits(),true);await session.close();
});

test("format state never exposes a revision before its tile scheduler is invalidated",async()=>{
  const {session}=await opened();let observed=0;
  session._onState=state=>{
    if(state.state === "ready" && state.revision>0){observed++;assert.equal(session.scheduler._context.revision,state.revision);}
  };
  await session.setFormat("bold",true);
  assert.ok(observed>0);await session.close();
});

test("range selection retains active cell, uses bounded reads and refuses every format",async()=>{
  const {session,doc,calls}=await opened();let reads=0;
  doc.readCell=async(c,r)=>{reads++;return{cell:doc.cell(c,r)};};
  await session.selectCell(100000,100000,{extend:true});
  assert.equal(reads,1);assert.equal(session.state.cell.column,0);
  assert.equal(session.state.selection.endColumn,100000);
  assert.equal(session.state.selection.multiple,true);
  for(const format of ["bold","italic","underline"])
    await assert.rejects(session.setFormat(format,true),{code:"RANGE_FORMAT_UNSUPPORTED"});
  assert.equal(doc.revision,0);assert.deepEqual(calls,[]);
  session.beginEdit("inline",{replace:true});
  assert.equal(session.state.selection.multiple,false);assert.equal(session.state.cell.column,0);
  session.setDraft("active only");await session.commit();
  assert.deepEqual(calls[0].slice(1,5),[0,0,0,"active only"]);
  await session.close();
});

test("expired hit replies never replace a newer gesture or its draft",async()=>{
  const {session,doc}=await opened();let release,started,valid=true;
  const pending=new Promise(r=>{started=r;});
  doc.hitCell=async()=>{started();await new Promise(r=>{release=r;});return{cell:doc.cell(8,9)};};
  const select=session.selectAt(500,200,{extend:true,valid:()=>valid});
  await pending;valid=false;release();await select;
  assert.equal(session.state.cell.column,0);assert.equal(session.state.selection.multiple,false);
  assert.equal(session.state.draft,"原始內容");
  await session.close();
});

test("arrows hit beyond exact focus geometry once, then collapse or extend",async()=>{
  const {session,doc,calls}=await opened();
  const hit=[];doc.hitCell=async(x,y)=>{hit.push([x,y]);return{cell:doc.cell(4,5)};};
  await session.moveSelection(1,0,{extend:true});
  assert.deepEqual(hit,[[1000,149]]);assert.equal(session.state.cell.column,0);
  assert.equal(session.state.selection.focus.column,4);
  await session.moveSelection(0,1);
  assert.deepEqual(hit[1],[4499,1800]);assert.equal(session.state.cell.column,4);
  assert.equal(session.state.selection.multiple,false);assert.equal(hit.length,2);
  assert.deepEqual(calls,[]);assert.equal(doc.revision,0);
  await session.setFormat("bold",true);assert.equal(doc.revision,1);
  await session.close();
});

test("geometry refusal leaves selection unchanged and sheet switch resets it",async()=>{
  const {session,doc}=await opened();
  await session.selectCell(2,3,{extend:true});const before=session.state.selection;
  doc.hitCell=async()=>{throw Object.assign(new Error("no geometry"),{code:"CELL_GEOMETRY_UNAVAILABLE"});};
  await assert.rejects(session.moveSelection(1,0),{code:"CELL_GEOMETRY_UNAVAILABLE"});
  assert.equal(session.state.selection,before);assert.equal(doc.revision,0);
  await session.showPart(1);
  assert.equal(session.state.selection.part,1);assert.equal(session.state.selection.multiple,false);
  await session.close();
});

// SPEC-P-demo-batch-3 3.1.
async function styled(opts={}) {
  const opened_=await opened();
  const {session,doc,calls}=opened_;
  const styles={textColor:"auto",backColor:"none",horizontalAlign:"standard"};
  const cell=doc.cell.bind(doc);
  doc.cell=(c=0,r=0)=>({...cell(c,r),...styles,...opts.cell});
  doc.rangeStylingSupported=opts.supported!==false;
  doc.rangeFormattingSupported=true;
  doc.setRangeStyle=async(column,row,endColumn,endRow,style,value,options)=>{
    calls.push(["style",column,row,endColumn,endRow,style,value,options]);
    if(opts.refuse)throw Object.assign(new Error("refused"),{code:opts.refuse});
    styles[style]=value;doc.revision++;
    return{range:{part:0,column,row,endColumn,endRow,bold:false,italic:false,underline:false,...styles,writable:true,refusalCode:""},changed:true,revision:doc.revision};
  };
  doc.readRange=async(column,row,endColumn,endRow)=>({range:{part:0,column,row,endColumn,endRow,bold:false,italic:false,underline:false,...styles,writable:true,refusalCode:""}});
  await session.selectCell(0,0);
  return{...opened_,styles};
}

test("one cell is styled as its merged extent, and the cell is read back",async()=>{
  const {session,calls}=await styled({cell:{endColumn:2,endRow:1}});
  await session.setStyle("backColor","#ffe599");
  const call=calls.find(c=>c[0]==="style");
  assert.deepEqual(call.slice(1,7),[0,0,2,1,"backColor","#ffe599"]);
  assert.equal(session.state.cell.backColor,"#ffe599");
});

test("a range is styled whole, keeps its anchor and refreshes its snapshot",async()=>{
  const {session,calls}=await styled();
  await session.selectCell(0,0);
  await session.selectAt(1200,100,{extend:true});
  assert.equal(session.state.selection.multiple,true);
  await session.setStyle("horizontalAlign","center");
  const call=calls.find(c=>c[0]==="style");
  assert.deepEqual(call.slice(1,7),[0,0,1,0,"horizontalAlign","center"]);
  assert.equal(session.state.rangeFormat.horizontalAlign,"center");
  assert.equal(session.state.cell.column,0);
});

test("a style the contract does not close, or an engine without it, reaches nothing",async()=>{
  for(const [opts,style,value,code] of [[{},"textColor","red","INVALID_ARGUMENT"],[{},"textColor","none","INVALID_ARGUMENT"],
      [{},"backColor","auto","INVALID_ARGUMENT"],[{},"horizontalAlign","repeat","INVALID_ARGUMENT"],[{},"font","#000000","INVALID_ARGUMENT"],
      [{supported:false},"textColor","#000000","RANGE_FORMAT_UNSUPPORTED"]]) {
    const {session,calls}=await styled(opts);
    await assert.rejects(session.setStyle(style,value),{code});
    assert.equal(calls.filter(c=>c[0]==="style").length,0);
  }
});

test("a pending cell input is committed before a single-cell style, not lost",async()=>{
  const {session,calls}=await styled();
  session.beginEdit("inline");session.setDraft("新內容");
  await session.setStyle("textColor","#c00000");
  assert.deepEqual(calls.map(c=>c[0]).filter(n=>n==="input"||n==="style"),["input","style"]);
});

test("a refused style leaves the revision and the cell alone",async()=>{
  const {session,doc}=await styled({refuse:"RANGE_MERGE_BOUNDARY"});
  const before=doc.revision;
  await assert.rejects(session.setStyle("textColor","#c00000"),{code:"RANGE_MERGE_BOUNDARY"});
  assert.equal(doc.revision,before);
  assert.equal(session.state.cell.textColor,"auto");
});
