import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";

const host=process.env.CALC_HOST_DIR || "/home/jiajun/Projects/Nextcloud_Apps/litecore";
const ODT="application/vnd.oasis.opendocument.text";
const ODS="application/vnd.oasis.opendocument.spreadsheet";
// SPEC-P-ms-formats 5.3 (host 0.2.56).
const DOCX="application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const XLSX="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

test("the Files action chooses editing only for an updateable spreadsheet",async()=>{
  const source=readFileSync(path.join(host,"src/files.js"),"utf8").replace(/^import .*$/gm,"");
  let action,destination;
  vm.runInNewContext(source,{Permission:{READ:1,UPDATE:2},DefaultType:{DEFAULT:1},
    registerFileAction(value){action=value;},generateUrl(route,params){return params;},
    window:{location:{assign(value){destination=value;}}}});
  // An XLSX goes to the spreadsheet editor writable or not: the viewer's engine does not read XLSX (spec 5.3).
  for(const [mime,permissions,page] of [[ODS,3,"ods-editor.html"],[ODS,1,"ods-viewer.html"],[ODT,3,"e2-editor.html"],[ODT,1,"e2-editor.html"],
      [DOCX,3,"e2-editor.html"],[DOCX,1,"e2-editor.html"],[XLSX,3,"ods-editor.html"],[XLSX,1,"ods-editor.html"]]){
    const nodes=[{mime,permissions,fileid:42}];
    assert.equal(action.enabled({nodes}),true);
    await action.exec({nodes});
    assert.equal(destination.page,page);assert.equal(destination.fileId,42);
  }
  assert.equal(action.enabled({nodes:[{mime:ODS,permissions:0}]}),false);
});

// Host 0.2.56 (SPEC-P-ms-formats 5.3): the format is the FILE's, read from its mime, not the page's -- one page edits ODT and DOCX.
// The mime, the extension and the page always come as a pair; a controller that sent no mime (before 0.2.56) leaves the page to decide.
test("the save host takes the file's format from its mime, MIME and extension as a pair",()=>{
  const source=readFileSync(path.join(host,"js/litecore-editor.js"),"utf8");
  const table=/\tconst FORMATS = \{[\s\S]*?\n\t\}\n/.exec(source);
  const match=/\tfunction documentFormat\(\) \{([\s\S]*?)\n\t\}/.exec(source);
  assert.ok(table && match,"FORMATS and documentFormat must exist in the actual host source");
  const format=new Function("config",`${table[0]}\n${match[1]}`);
  const editor={name:"e2-editor.html"},calc={name:"ods-editor.html"};
  assert.deepEqual(format({file:{mime:ODT},page:editor}),{format:"odt",mime:ODT,extension:".odt",page:"e2-editor.html"});
  assert.deepEqual(format({file:{mime:DOCX},page:editor}),{format:"docx",mime:DOCX,extension:".docx",page:"e2-editor.html"});
  assert.deepEqual(format({file:{mime:ODS},page:calc}),{format:"ods",mime:ODS,extension:".ods",page:"ods-editor.html"});
  assert.deepEqual(format({file:{mime:XLSX},page:calc}),{format:"xlsx",mime:XLSX,extension:".xlsx",page:"ods-editor.html"});
  assert.deepEqual(format({page:calc}),{format:"ods",mime:ODS,extension:".ods",page:"ods-editor.html"});
  assert.deepEqual(format({}),{format:"odt",mime:ODT,extension:".odt",page:"e2-editor.html"});
});
