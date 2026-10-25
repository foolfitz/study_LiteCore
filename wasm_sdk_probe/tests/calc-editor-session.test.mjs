import assert from "node:assert/strict";
import test from "node:test";
import { CalcEditorSession, inputIntent } from "../spreadsheet-shell/calc-editor-session.js";

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

test("cancelled drafts never enter the engine",async()=>{
  const {session,calls}=await opened();
  session.beginEdit("inline");session.setDraft("取消這份");session.cancelEdit();
  assert.equal(session.state.draft,"原始內容");assert.equal(session.hasUnsavedEdits(),false);
  assert.deepEqual(calls,[]);
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
