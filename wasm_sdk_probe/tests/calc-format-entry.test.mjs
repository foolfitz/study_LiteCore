import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import vm from "node:vm";
import {CalcEditorSession} from "../spreadsheet-shell/calc-editor-session.js";

const source=readFileSync(process.env.CALC_FORMAT_APP || new URL("../web/ods-editor-app.js",import.meta.url),"utf8");
function extract(name) {
  const match=new RegExp(`(?:async )?function ${name}\\([^\\n]*\\)\\s*\\{[\\s\\S]*?\\n\\}`).exec(source);
  assert.ok(match,`actual page function ${name} must exist`);return match[0];
}
const clean=()=>({state:"ready",cell:{writable:true,bold:false},readOnly:false,uncertain:false,busy:false,
  selectionPending:false,selection:{multiple:false},rangeFormattingSupported:true,rangeFormat:{writable:true,bold:null}});
function page(state=clean()) {
  const calls=[],nodes=["bold","italic","underline"].map(format=>({dataset:{format},setAttribute(){},getAttribute(){return format;}}));
  const context={session:{state,setFormat:(...args)=>calls.push(args)},pendingEntry:null,dragWork:null,
    document:{querySelectorAll:()=>nodes},formatRefusal:code=>code};
  vm.createContext(context);
  vm.runInContext(["formatAvailable","renderFormatControls","toggleFormat"].map(extract).join("\n"),context);
  return {context,calls,nodes};
}
const refusals={
  opening:s=>s.state="opening",locked:s=>s.cell.writable=false,readonly:s=>s.readOnly=true,
  uncertain:s=>s.uncertain=true,busy:s=>s.busy=true,selection:s=>s.selectionPending=true,
  unsupported:s=>{s.selection.multiple=true;s.rangeFormattingSupported=false;},
  protectedRange:s=>{s.selection.multiple=true;s.rangeFormat.writable=false;},
  unknownRange:s=>{s.selection.multiple=true;s.rangeFormat=null;},
};
for(const [name,mutate] of Object.entries(refusals))test(`actual page refuses ${name} in toolbar and shortcut`,()=>{
  const state=clean();mutate(state);const {context,calls,nodes}=page(state);
  context.renderFormatControls(state);context.toggleFormat("bold");
  assert.ok(nodes.every(n=>n.disabled));assert.deepEqual(calls,[]);
});
for(const field of ["pendingEntry","dragWork"])test(`actual page refuses ${field} and refreshes when cleared`,()=>{
  const {context,calls,nodes}=page();context[field]={};
  context.renderFormatControls(context.session.state);context.toggleFormat("bold");
  assert.ok(nodes.every(n=>n.disabled));assert.deepEqual(calls,[]);
  context[field]=null;context.renderFormatControls(context.session.state);
  assert.ok(nodes.every(n=>!n.disabled));
});
test("actual page allows mixed on and all-on off",()=>{
  const state=clean();state.selection.multiple=true;const {context,calls}=page(state);
  context.toggleFormat("bold");state.rangeFormat.bold=true;context.toggleFormat("bold");
  assert.deepEqual(calls,[["bold",true],["bold",false]]);
});
test("drag completion and cancellation refresh actual format controls",async()=>{
  const {context,nodes}=page();let refreshes=0;
  const refresh=context.renderFormatControls;context.renderFormatControls=state=>{refreshes++;refresh(state);};
  Object.assign(context,{drag:{pointer:1},dragWork:{},gesture:0,autosave:null,
    ui:{viewport:{hasPointerCapture:()=>false}},flushPendingEntry(){},focusGrid(){}});
  vm.runInContext(["cancelDrag","extendDrag"].map(extract).join("\n"),context);
  context.cancelDrag();assert.equal(refreshes,1);assert.ok(nodes.every(n=>!n.disabled));
  const current={start:Promise.resolve(true),active:false,generation:context.gesture};context.dragWork=current;
  await context.extendDrag(current);assert.equal(refreshes,2);assert.equal(context.dragWork,null);
  assert.ok(nodes.every(n=>!n.disabled));
});
test("actual queued selection cannot consume a shortcut computed for old cell",async()=>{
  const calls=[];
  const doc={revision:0,parts:1,documentType:"spreadsheet",partNames:["Sheet1"],partVisible:[true],currentPart:0,
    widthTwips:9000,heightTwips:9000,async close(){},async render(){},async save(){return new ArrayBuffer(8);},
    cell(column=0,row=0){return{part:0,column,row,endColumn:column,endRow:row,input:"text",writable:true,
      bold:column===4,xTwips:column*1000,yTwips:row*300,widthTwips:999,heightTwips:299};},
    async readCell(c,r){return{cell:this.cell(c,r)};},
    async setCellFormat(c,r,f,v){calls.push([c,r,f,v]);this.revision++;return{cell:{...this.cell(c,r),[f]:v}};}};
  const session=new CalcEditorSession({engineFactory:async()=>({manifest:{capabilities:["open-ods"]},open:async()=>doc,dispose(){}})});
  await session.open({bytes:new ArrayBuffer(8),name:"test.ods"});
  let release,started;const start=new Promise(resolve=>started=resolve);
  const saving=session.save(async()=>{started();await new Promise(resolve=>release=resolve);});await start;
  const selection=session.selectCell(4,4);const {context}=page();context.session=session;
  assert.equal(session.state.busy,true);assert.equal(session.state.selectionPending,true);
  const format=context.toggleFormat("bold");release();await Promise.all([saving,selection,format]);
  assert.deepEqual(calls,[]);assert.equal(session.state.cell.column,4);assert.equal(session.state.cell.bold,true);
  await session.close();
});
