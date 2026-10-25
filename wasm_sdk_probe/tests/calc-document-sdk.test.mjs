import assert from "node:assert/strict";
import test from "node:test";
import { CalcDocumentEngine, normalizeCell } from "../spreadsheet-shell/calc-document-sdk.js";

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
  addEventListener(type,fn){if(type==="message")this.listeners.push(fn);}
  terminate(){}
  postMessage(message){
    if(message.kind!=="request")return;
    this.calls.push(message);
    let result;
    switch(message.operation){
      case "init":result={profile:"ods-editor-v1",capabilities:["open-ods","part-switch","cell-editing","save-ods"]};break;
      case "open":result={documentHandle:1,revision:0,parts:1,width:5000,height:5000,tileMode:1,documentType:"spreadsheet",inputSuffix:".ods"};break;
      case "currentPart":result={part:0};break;
      case "partName":result={name:"Sheet1"};break;
      default:result={revision:3,changed:message.operation==="cellInput",cell:raw};
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
