// Finding 186: active probe. Opens a Writer document from the Start Center of qt_soffice.html, types three letters
// (positive control: the keyboard reaches the application), then presses F11 and Ctrl+H, which are bound only by
// Accelerators-unxwnt.xcu (.uno:DesignerDialog and .uno:SearchDialog). A screenshot after every step.
// usage: NODE_PATH=<wasm-lite/tools/pw/node_modules> node probe_keys.js <url> <out-prefix>
// Browser launch options are those of wasm-lite/tools/pw/probe.js.
const { chromium } = require('playwright');
const url = process.argv[2];
const out = process.argv[3];

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--enable-features=SharedArrayBuffer', '--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
  });
  const page = await browser.newPage();
  const t0 = Date.now();
  const lines = [];
  const push = (tag, txt) => lines.push(`[${((Date.now() - t0) / 1000).toFixed(1).padStart(5)}s ${tag}] ${txt}`);
  page.on('console', m => push(m.type().toUpperCase(), m.text()));
  page.on('pageerror', e => push('PAGEERROR', e.message));
  page.on('crash', () => push('CRASH', 'page crashed'));
  const shot = async (n, what) => { await page.screenshot({ path: `${out}-${n}-${what}.png` }); push('PROBE', `shot ${n} ${what}`); };

  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(15000);
  await shot(0, 'start-center');

  await page.mouse.click(130, 325);              // "Writer Document"
  push('PROBE', 'clicked 130,325 (Writer Document)');
  await page.waitForTimeout(25000);
  await shot(1, 'writer-opened');

  await page.mouse.click(600, 420);              // into the page
  push('PROBE', 'clicked 600,420 (document area)');
  await page.waitForTimeout(1500);
  await page.keyboard.type('abc', { delay: 150 });
  push('PROBE', 'typed abc');
  await page.waitForTimeout(3000);
  await shot(2, 'typed-abc');

  await page.keyboard.press('F11');
  push('PROBE', 'pressed F11');
  await page.waitForTimeout(6000);
  await shot(3, 'after-F11');

  await page.keyboard.press('Control+h');
  push('PROBE', 'pressed Control+h');
  await page.waitForTimeout(6000);
  await shot(4, 'after-ctrl-h');

  console.log(lines.filter(l => !/ (REQ|RESP)\] /.test(l)).join('\n'));
  await browser.close();
})();
