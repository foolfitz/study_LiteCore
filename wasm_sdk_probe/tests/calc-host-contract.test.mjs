import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";

const host=process.env.CALC_HOST_DIR || "/home/jiajun/Projects/Nextcloud_Apps/litecore";
const ODT="application/vnd.oasis.opendocument.text";
const ODS="application/vnd.oasis.opendocument.spreadsheet";

test("the Files action chooses editing only for an updateable spreadsheet",async()=>{
  const source=readFileSync(path.join(host,"src/files.js"),"utf8").replace(/^import .*$/gm,"");
  let action,destination;
  vm.runInNewContext(source,{Permission:{READ:1,UPDATE:2},DefaultType:{DEFAULT:1},
    registerFileAction(value){action=value;},generateUrl(route,params){return params;},
    window:{location:{assign(value){destination=value;}}}});
  for(const [mime,permissions,page] of [[ODS,3,"ods-editor.html"],[ODS,1,"ods-viewer.html"],[ODT,3,"e2-editor.html"],[ODT,1,"e2-editor.html"]]){
    const nodes=[{mime,permissions,fileid:42}];
    assert.equal(action.enabled({nodes}),true);
    await action.exec({nodes});
    assert.equal(destination.page,page);assert.equal(destination.fileId,42);
  }
  assert.equal(action.enabled({nodes:[{mime:ODS,permissions:0}]}),false);
});

test("the existing save host selects the spreadsheet MIME and extension as a pair",()=>{
  const source=readFileSync(path.join(host,"js/litecore-editor.js"),"utf8");
  const match=/\tfunction documentFormat\(\) \{([\s\S]*?)\n\t\}/.exec(source);
  assert.ok(match,"documentFormat must exist in the actual host source");
  const format=new Function("config","ODT","ODS",match[1]);
  assert.deepEqual(format({page:{name:"ods-editor.html"}},ODT,ODS),{mime:ODS,extension:".ods"});
  assert.deepEqual(format({page:{name:"e2-editor.html"}},ODT,ODS),{mime:ODT,extension:".odt"});
  assert.deepEqual(format({},ODT,ODS),{mime:ODT,extension:".odt"});
});
