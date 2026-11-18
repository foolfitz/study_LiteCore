// Finding 159: run-time reproduction on a stock upstream WASM build (qt_soffice.html).
// Opens a Calc document from the Start Center, then
//   typed path: types every formula of cases.json into column A with the keyboard (en-US UI, ';' -> ','),
//   API path:   sets the same formulas into column B with XCell.setFormula (API grammar, as written in cases.json),
//   direct:     calls the add-in methods through css.script.Invocation, outside Calc, and records the exception
//               (type and message, and those of any wrapped TargetException) when one is thrown,
// and reads every cell back through UNO (formula, error code, value, string). A screenshot after each step.
// The UNO calls run in the LO main thread's worker (README.wasm.md: PROXY_TO_PTHREAD), found as the worker
// whose Module.uno is set.
// usage: NODE_PATH=<wasm-lite/tools/pw/node_modules> node probe_159.js <url> <out-prefix> <cases.json> [<locale>]
//   <locale>, e.g. en-US: the browser context's locale (navigator.language, which LibreOffice takes as its locale);
//   omitted: the browser default, which follows the environment (zh-TW on this machine).
// Embind's "found a leaked C++ instance" warnings (the probe does not delete() its UNO references) are counted, not
// logged.
// Browser launch options are those of wasm-lite/tools/pw/probe.js (as in finding 186's probe_keys.js).
const { chromium } = require('playwright');
const fs = require('fs');
const [url, out, casesPath, locale] = process.argv.slice(2);
const cases = JSON.parse(fs.readFileSync(casesPath, 'utf8'));

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--enable-features=SharedArrayBuffer', '--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
  });
  const context = await browser.newContext(locale ? { locale } : {});
  const page = await context.newPage();
  const t0 = Date.now();
  const lines = [];
  let leakWarnings = 0;
  const push = (tag, txt) => {
    if (/^Embind found a leaked C\+\+ instance/.test(txt)) { leakWarnings++; return; }
    lines.push(`[${((Date.now() - t0) / 1000).toFixed(1).padStart(5)}s ${tag}] ${txt}`);
  };
  page.on('console', m => push(m.type().toUpperCase(), m.text()));
  page.on('pageerror', e => push('PAGEERROR', e.message));
  page.on('crash', () => push('CRASH', 'page crashed'));
  page.on('worker', w => { w.on('console', m => push('W-' + m.type().toUpperCase(), m.text())); });
  const shot = async (n, what) => { await page.screenshot({ path: `${out}-${n}-${what}.png` }); push('PROBE', `shot ${n} ${what}`); };
  const race = (p, ms) => Promise.race([p, new Promise(res => setTimeout(() => res({ timeout: ms }), ms))]);
  const result = { url, cases: casesPath, locale: locale || null, startedAt: new Date().toISOString(), loWorker: null, waits: {} };

  let lo = null;
  const findLo = async () => {
    for (const w of page.workers()) {
      const r = await race(w.evaluate(() => !!(globalThis.Module && globalThis.Module.uno)).catch(e => ({ error: e.message })), 1500);
      if (r === true) return w;
    }
    return null;
  };

  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  for (let i = 0; i < 60 && !lo; i++) { await page.waitForTimeout(1000); lo = await findLo(); }
  if (!lo) { push('PROBE', 'no worker with Module.uno after 60 s'); console.log(lines.join('\n')); await browser.close(); process.exit(3); }
  result.loWorker = page.workers().indexOf(lo);
  result.navigatorLanguage = await page.evaluate(() => navigator.language);
  push('PROBE', `navigator.language = ${result.navigatorLanguage}`);
  push('PROBE', `LO main-thread worker = workers()[${result.loWorker}] of ${page.workers().length}`);
  await page.waitForTimeout(8000);
  await shot(0, 'start-center');

  // Start Center: "Calc Spreadsheet" (same layout as finding 186's screenshots).
  await page.mouse.click(130, 372);
  push('PROBE', 'clicked 130,372 (Calc Spreadsheet)');
  const isCalc = () => lo.evaluate(() => {
    const css = Module.uno.com.sun.star;
    const m = Module.getCurrentModelFromViewSh();
    return !!(m && css.sheet.XSpreadsheetDocument.query(m));
  }).catch(e => 'ERR ' + e.message);
  let calc = false;
  const tc = Date.now();
  for (let i = 0; i < 90 && calc !== true; i++) { await page.waitForTimeout(1000); calc = await race(isCalc(), 3000); }
  result.waits.calcSeconds = (Date.now() - tc) / 1000;
  push('PROBE', `spreadsheet model current: ${JSON.stringify(calc)} after ${result.waits.calcSeconds} s`);
  if (calc !== true) { await shot(1, 'no-calc'); console.log(lines.join('\n')); await browser.close(); process.exit(4); }
  await page.waitForTimeout(5000);
  await shot(1, 'calc-opened');

  // Typed path: click A1, type each formula, Enter moves down.
  await page.mouse.click(84, 172);
  push('PROBE', 'clicked 84,172 (cell A1)');
  await page.waitForTimeout(1000);
  for (const c of cases.cells) {
    const typed = c.formula.replace(/;/g, ',');
    await page.keyboard.type(typed, { delay: 40 });
    await page.keyboard.press('Enter');
    push('PROBE', `typed ${c.id}: ${typed}`);
    await page.waitForTimeout(400);
  }
  await page.waitForTimeout(3000);
  await shot(2, 'typed-column-A');

  // API path into column B, ids into column C; then read back A and B.
  const api = await race(lo.evaluate((cells) => {
    const css = Module.uno.com.sun.star;
    const doc = css.sheet.XSpreadsheetDocument.query(Module.getCurrentModelFromViewSh());
    const sheetAny = css.container.XIndexAccess.query(doc.getSheets()).getByIndex(0);
    const range = css.table.XCellRange.query(sheetAny.get());
    const errs = [];
    cells.forEach((c, row) => {
      try { range.getCellByPosition(1, row).setFormula(c.formula); } catch (e) { errs.push(`${c.id} B: ${String(e)}`); }
      try { css.text.XTextRange.query(range.getCellByPosition(2, row)).setString(c.id); } catch (e) { errs.push(`${c.id} C: ${String(e)}`); }
    });
    const read = (col, row) => {
      const cell = range.getCellByPosition(col, row);
      return { formula: cell.getFormula(), error: cell.getError(), value: cell.getValue(),
               string: css.text.XTextRange.query(cell).getString() };
    };
    return { errs, cells: cells.map((c, row) => ({ id: c.id, label: css.text.XTextRange.query(range.getCellByPosition(2, row)).getString(),
                                                  typed: read(0, row), api: read(1, row) })) };
  }, cases.cells).catch(e => ({ error: e.message })), 30000);
  result.cells = api;
  push('PROBE', `read back ${api.cells ? api.cells.length : 0} rows; setFormula errors: ${JSON.stringify(api.errs || api)}`);
  await page.waitForTimeout(2000);
  await shot(3, 'api-column-B');

  // Direct calls through Invocation, outside Calc.
  const direct = await race(lo.evaluate((ds) => {
    const css = Module.uno.com.sun.star;
    const ctx = Module.getUnoComponentContext();
    const smgr = ctx.getServiceManager();
    const describe = (any, depth) => {
      const o = { type: String(any.getType().toString()) };
      try {
        const exc = any.get();
        o.message = exc.Message;
        if (exc.TargetException !== undefined && depth < 4) o.target = describe(exc.TargetException, depth + 1);
      } catch (e) { o.readError = String(e); }
      return o;
    };
    return ds.map(d => {
      const r = { id: d.id, method: d.method };
      try {
        const obj = smgr.createInstanceWithContext(d.service, ctx);
        const wrap = new Module.uno_Sequence_any([new Module.uno_Any(Module.uno_Type.Interface('com.sun.star.uno.XInterface'), obj)]);
        const inv = css.script.XInvocation2.query(css.script.Invocation.create(ctx).createInstanceWithArguments(wrap));
        const params = new Module.uno_Sequence_any(d.args.map(([t, v]) => new Module.uno_Any(Module.uno_Type[t](), v)));
        const oi = new Module.uno_InOutParam_sequence_short;
        const op = new Module.uno_InOutParam_sequence_any;
        r.hasMethod = inv.hasMethod(d.method.split('.')[1]);
        try {
          const ret = inv.invoke(d.method.split('.')[1], params, oi, op);
          r.result = ret.get();
          r.resultType = String(ret.getType().toString());
        } catch (e) {
          try { r.exception = describe(Module.catchUnoException(e), 0); } catch (e2) { r.nonUnoException = String(e2); }
        }
      } catch (e) {
        try { r.setupException = describe(Module.catchUnoException(e), 0); } catch (e2) { r.setupError = String(e2); }
      }
      return r;
    });
  }, cases.direct).catch(e => ({ error: e.message })), 30000);
  result.direct = direct;
  push('PROBE', `direct: ${JSON.stringify(direct)}`);
  await shot(4, 'end');

  result.finishedAt = new Date().toISOString();
  result.embindLeakWarnings = leakWarnings;
  push('PROBE', `Embind leak warnings (not logged): ${leakWarnings}`);
  fs.writeFileSync(`${out}.json`, JSON.stringify(result, null, 1));
  console.log(lines.join('\n'));
  await browser.close();
})();
