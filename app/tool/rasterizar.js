// Converte os SVGs do ícone em PNG usando o Chromium do Playwright.
//   node app/tool/rasterizar.js
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const dir = path.join(__dirname, '..', 'assets', 'icone');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1024, height: 1024 }, deviceScaleFactor: 1 });
  for (const nome of ['araragov', 'araragov-arredondado']) {
    const svg = fs.readFileSync(path.join(dir, `${nome}.svg`), 'utf8');
    await page.setContent(`<html><body style="margin:0;background:transparent">${svg.replace('width="512" height="512"', 'width="1024" height="1024"')}</body></html>`);
    await page.locator('svg').screenshot({ path: path.join(dir, `${nome}.png`), omitBackground: true });
    console.log('escrito', `${nome}.png`);
  }
  await browser.close();
})();
