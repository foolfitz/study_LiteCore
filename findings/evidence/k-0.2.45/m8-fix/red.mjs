// Red case for the widened M8 match: the same pattern, the real markup, one thing changed each time.
import { readFileSync } from "node:fs";
const html = readFileSync(new URL("../../../../wasm_sdk_probe/web/e2-editor.html", import.meta.url), "utf8");
const source = readFileSync(new URL("../../../../wasm_sdk_probe/editor-shell-v2/tests/page-markdown-dialog.test.mjs", import.meta.url), "utf8");
const pattern = eval(source.match(/assert\.match\(HTML, (\/<button data-action="paste-markdown".*\/)\);/)[1]);
const cases = {
  real: [html, true],
  "hidden removed": [html.replace('data-action="paste-markdown" hidden', 'data-action="paste-markdown"'), false],
  "hidden on another attribute name": [html.replace('data-action="paste-markdown" hidden', 'data-action="paste-markdown" hidden-x'), false],
  "label moved out of the button": [html.replace('<span class="lbl">貼上為 Markdown…</span></button>', '</button><span>貼上為 Markdown…</span>'), false],
};
let bad = 0;
for (const [name, [text, want]] of Object.entries(cases)) {
  const got = pattern.test(text);
  console.log(`${got === want ? "ok  " : "FAIL"} ${name}: ${got}`);
  if (got !== want) bad += 1;
}
process.exit(bad ? 1 : 0);
