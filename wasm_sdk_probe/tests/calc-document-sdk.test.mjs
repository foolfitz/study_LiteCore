import assert from "node:assert/strict";
import test from "node:test";
const { CalcDocumentEngine, normalizeCell, normalizeRange } = await import(process.env.CALC_DOCUMENT_MODULE || "../spreadsheet-shell/calc-document-sdk.js");

const raw = {part:"0",column:"1",row:"2",endColumn:"1",endRow:"2",xTwips:"100",yTwips:"200",
  widthTwips:"300",heightTwips:"400",cellType:"3",formula:"=A1*2",input:"=A1*2",text:"84",value:"84",
  writable:"true",bold:"false",boldAsian:"false",boldComplex:"false",italic:"false",italicAsian:"false",italicComplex:"false",underline:"false"};

test("model snapshots retain formula, displayed result and exact cell identity", () => {
  const cell=normalizeCell(raw);
  assert.equal(cell.input,"=A1*2"); assert.equal(cell.text,"84"); assert.equal(cell.value,84);
  assert.equal(cell.column,1);assert.equal(cell.row,2);assert.equal(cell.writable,true);
  for (const broken of [{...raw,writable:"maybe"},{...raw,widthTwips:"0"},{...raw,input:undefined},{...raw,value:"NaN"}])
    assert.throws(()=>normalizeCell(broken));
});

class Worker {
  listeners=[]; calls=[];
  rangeEnabled=false; rangeReply=null;
  addEventListener(type,fn){if(type==="message")this.listeners.push(fn);}
  terminate(){}
  postMessage(message){
    if(message.kind!=="request")return;
    this.calls.push(message);
    let result;
    switch(message.operation){
      case "init":result={profile:"ods-editor-v1",capabilities:["open-ods","part-switch","cell-editing","save-ods",...(this.rangeEnabled?["cell-range-formatting"]:[])]};break;
      case "open":result={documentHandle:1,revision:0,parts:1,width:5000,height:5000,tileMode:1,documentType:"spreadsheet",inputSuffix:".ods"};break;
      case "currentPart":result={part:0};break;
      case "partName":result={name:"Sheet1"};break;
      default:result={revision:3,changed:message.operation==="cellInput",cell:message.operation.startsWith("range") ? this.rangeReply : raw};
    }
    queueMicrotask(()=>this.listeners.forEach(fn=>fn({data:{protocolVersion:1,kind:"response",requestId:message.requestId,ok:true,result}})));
  }
}

test("cell API carries part and expected revision; clear is an empty string",async()=>{
  const worker=new Worker();
  const engine=new CalcDocumentEngine({workerUrl:"https://test/sdk-worker.js",workerFactory:()=>worker});
  await engine._initialize();
  const handle=await engine.open(new ArrayBuffer(8),{name:"a.ods"});
  await handle.setCellInput(1,2,"");
  assert.deepEqual(worker.calls.at(-1).payload,{documentHandle:1,expectedRevision:0,part:0,column:1,row:2,text:""});
  await handle.setCellFormat(1,2,"underline",true);
  assert.equal(worker.calls.at(-1).payload.expectedRevision,3);
  const count=worker.calls.length;
  assert.throws(()=>handle.setCellInput(1,2,"x".repeat(32768)),{code:"CELL_TEXT_TOO_LONG"});
  assert.throws(()=>handle.setCellFormat(1,2,"bold",1),{code:"INVALID_ARGUMENT"});
  await assert.rejects(handle.readCell(1.2,2),{code:"INVALID_ARGUMENT"});
  assert.equal(worker.calls.length,count);
  engine.dispose();
});

const rangeRaw={part:"0",column:"1",row:"2",endColumn:"3",endRow:"4",writable:"true",refusalCode:"",
  bold:"mixed",italic:"off",underline:"on"};
test("range snapshot preserves mixed state and refuses malformed permission or bounds",()=>{
  assert.deepEqual(normalizeRange(rangeRaw),{part:0,column:1,row:2,endColumn:3,endRow:4,writable:true,refusalCode:"",bold:null,italic:false,underline:true});
  for(const broken of [{...rangeRaw,bold:true},{...rangeRaw,writable:"false"},{...rangeRaw,endRow:"1"},{...rangeRaw,endRow:"65538"}])
    assert.throws(()=>normalizeRange(broken));
});

test("range SDK gates v1, bounds work, carries explicit target and distrusts mutation reply",async()=>{
  const worker=new Worker();
  const engine=new CalcDocumentEngine({workerUrl:"https://test/sdk-worker.js",workerFactory:()=>worker});
  await engine._initialize();const old=await engine.open(new ArrayBuffer(8),{name:"a.ods"});
  assert.equal(old.rangeFormattingSupported,false);
  assert.throws(()=>old.readRange(1,2,3,4),{code:"UNSUPPORTED_OPERATION"});engine.dispose();
  const upgraded=new Worker();upgraded.rangeEnabled=true;upgraded.rangeReply=rangeRaw;
  const next=new CalcDocumentEngine({workerUrl:"https://test/sdk-worker.js",workerFactory:()=>upgraded});
  await next._initialize();const handle=await next.open(new ArrayBuffer(8),{name:"a.ods"});
  const snapshot=await handle.readRange(1,2,3,4);assert.equal(snapshot.range.bold,null);
  await handle.setRangeFormat(1,2,3,4,"bold",true,{expectedRevision:7});
  assert.deepEqual(upgraded.calls.at(-1).payload,{documentHandle:1,expectedRevision:7,part:0,column:1,row:2,endColumn:3,endRow:4,format:"bold",enabled:true});
  const count=upgraded.calls.length;
  assert.throws(()=>handle.readRange(0,0,65536,0),{code:"RANGE_TOO_LARGE"});
  assert.throws(()=>handle.readRange(2,2,1,3),{code:"INVALID_ARGUMENT"});
  assert.equal(upgraded.calls.length,count);
  upgraded.rangeReply={...rangeRaw,column:"0"};
  await assert.rejects(handle.setRangeFormat(1,2,3,4,"bold",true),{code:"MUTATION_OUTCOME_UNKNOWN"});
  next.dispose();
});

// SPEC-P-demo-batch-3 3.1.
test("style snapshots: absent on an older engine, closed on a new one, null when mixed",async()=>{
  const {normalizeRange,normalizeCell}=await import("../spreadsheet-shell/calc-document-sdk.js");
  const range={part:"0",column:"0",row:"0",endColumn:"1",endRow:"0",bold:"off",italic:"off",underline:"off",writable:"true",refusalCode:""};
  assert.equal("textColor" in normalizeRange(range),false);
  const styled=normalizeRange({...range,textColor:"#c00000",backColor:"mixed",horizontalAlign:"other"});
  assert.deepEqual([styled.textColor,styled.backColor,styled.horizontalAlign],["#c00000",null,"other"]);
  for(const bad of [{textColor:"red",backColor:"none",horizontalAlign:"left"},{textColor:"auto",backColor:"auto",horizontalAlign:"left"},
      {textColor:"auto",backColor:"none",horizontalAlign:"repeat"},{textColor:"auto"}])
    assert.throws(()=>normalizeRange({...range,...bad}),{code:"CELL_RESULT_INVALID"});
  assert.ok(normalizeCell);
});
