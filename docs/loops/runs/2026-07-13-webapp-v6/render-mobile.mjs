// render-mobile.mjs <abs-путь.html|url> <abs-выход.png> — мобильный full-page скрин 390×844.
// playwright резолвится из cdp/frontend/node_modules (ESM ищет от файла скрипта, не от cwd —
// поэтому createRequire с явным якорем; запускать можно из любой директории).
import { createRequire } from 'module';
const require = createRequire('/Users/esetseitkamal/cdp/frontend/package.json');
const { chromium } = require('playwright');

const [, , src, out] = process.argv;
if (!src || !out) {
  console.error('usage: node render-mobile.mjs <file.html|url> <out.png>');
  process.exit(1);
}
const url = src.startsWith('http') ? src : 'file://' + src;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
await page.goto(url, { waitUntil: 'networkidle' });
// дать шрифтам/entrance-анимациям дожить, затем скролл для scroll-triggered motion
await page.waitForTimeout(1400);
await page.evaluate(async () => {
  for (let y = 0; y <= document.body.scrollHeight; y += 600) {
    window.scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 120));
  }
  window.scrollTo(0, 0);
});
await page.waitForTimeout(600);
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log('OK', out);
