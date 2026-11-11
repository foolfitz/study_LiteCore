// Diagnostic probe for finding 002 (not the evidence probe): load, wait, screenshot,
// click the canvas, wait, screenshot; log console with timestamps.
// usage: node probe_click.js <url> <outprefix>
const { chromium } = require('playwright');
const [url, out] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch({ headless: true, args: [
    '--enable-features=SharedArrayBuffer', '--use-gl=swiftshader',
    '--enable-unsafe-swiftshader', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const t0 = Date.now(); const lines = [];
  const push = (tag, txt) => lines.push(`[${((Date.now()-t0)/1000).toFixed(1).padStart(5)}s ${tag}] ${txt}`);
  page.on('console', m => push(m.type().toUpperCase(), m.text()));
  page.on('pageerror', e => push('PAGEERROR', e.message));
  page.on('crash', () => push('CRASH', ''));
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(15000);
  await page.screenshot({ path: `${out}-1-before-click.png` }); push('PROBE', 'shot 1');
  await page.mouse.click(300, 200); push('PROBE', 'clicked 300,200');
  await page.waitForTimeout(5000);
  await page.screenshot({ path: `${out}-2-after-click.png` }); push('PROBE', 'shot 2');
  await page.keyboard.press('Escape'); push('PROBE', 'pressed Escape');
  await page.waitForTimeout(5000);
  await page.screenshot({ path: `${out}-3-after-key.png` }); push('PROBE', 'shot 3');
  console.log(lines.join('\n'));
  await browser.close();
})();
