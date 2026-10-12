// Feed real HostInputAdapter traces through the page's own predicate (read from the file, not copied).
import { readFileSync } from "node:fs";
import { HostInputAdapter } from "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/input/input-adapter.js";
const page = readFileSync("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/e2-editor-app.js", "utf8");
const m = page.match(/onInputTrace\(entry\) \{([\s\S]*?)\n    \},/);
if (!m) throw new Error("onInputTrace not found");
const toasts = [];
const onInputTrace = new Function("entry", "toast", "VIEW_ONLY_TEXT", m[1]);
const traces = [];
let release;
const gate = new Promise((r) => { release = r; });
const adapter = new HostInputAdapter({
  commit: async (text) => { if (text === "x") throw Object.assign(new Error("engine said no"), { code: "EDITOR_X" }); await gate; return { revision: 1 }; },
  onTrace: (e) => { traces.push(e); onInputTrace(e, (msg, bad) => toasts.push(msg), "唯讀"); },
});
const results = [];
for (let i = 0; i < 10; i++) results.push(adapter.commitText("a" + i).then(() => "ok", (e) => e.code));
release();
const settled = await Promise.all(results);
const failing = adapter.commitText("x").then(() => "ok", (e) => e.code);
console.log("commits:", settled.join(","), "| failing commit:", await failing);
console.log("trace types:", [...new Set(traces.map((t) => `${t.type}/${t.reason ?? ""}/${t.status}`))].join("  "));
console.log("toasts from the page's predicate:", JSON.stringify(toasts));
