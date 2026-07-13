// render-app.mjs <base-url> <out-dir> — полностраничные 390×844@2x скрины всех экранов webapp.
// login рендерится в ОТДЕЛЬНОМ контексте БЕЗ jwt (иначе редирект на hub — процедурный флаг J1 R2);
// остальные — с auth-гейтом localStorage['kodi.jwt']. playwright из cdp/frontend.
import { createRequire } from 'module';
const require = createRequire('/Users/esetseitkamal/cdp/frontend/package.json');
const { chromium } = require('playwright');

const [, , base, outDir] = process.argv;
const errors = [];

async function shoot(ctx, routes) {
  const page = await ctx.newPage();
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/40[34]|502|Failed to load resource/.test(m.text())) errors.push(m.text()); });
  for (const [name, path] of routes) {
    await page.goto(base + path, { waitUntil: 'networkidle' }).catch((e) => errors.push(`${name}: ${e.message}`));
    await page.waitForTimeout(1600);
    await page.evaluate(async () => {
      for (let y = 0; y <= document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 100)); }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${outDir}/${name}.png`, fullPage: true });
    console.log('OK', name);
  }
  await page.close();
}

const browser = await chromium.launch();
const vp = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 };

// 1) login — без jwt
const anonCtx = await browser.newContext(vp);
await shoot(anonCtx, [['login', '/app/login']]);
await anonCtx.close();

// 2) остальные — с jwt (DEV-мок)
const authCtx = await browser.newContext(vp);
await authCtx.addInitScript(() => localStorage.setItem('kodi.jwt', 'dev-panel'));
await shoot(authCtx, [
  ['hub', '/app/'],
  ['srez', '/app/srez'],
  ['drill', '/app/drill/wt-pc-01'],
  ['analytics', '/app/analytics'],
  ['closure', '/app/closure/wt-pc-01'],
  // Кульминация закрепления — dev-only (?dev=celebrate за import.meta.env.DEV), чтобы
  // панель ВИДЕЛА флаг+конфетти+штамп (прод-поведение не меняется).
  ['closure-celebrate', '/app/closure/wt-pc-01?dev=celebrate'],
]);
await authCtx.close();

console.log(errors.length ? 'CONSOLE ERRORS:\n' + errors.join('\n') : 'console clean');
await browser.close();
