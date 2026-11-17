/* phase6-batch3 / shoot-sampler-4.js
 * 重新截取 theme-sampler-4.html 中 4 张 1920×1080 截图
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

const DIR = __dirname;
const PNGDIR = path.join(DIR, 'sampler-png');
if (!fs.existsSync(PNGDIR)) fs.mkdirSync(PNGDIR, { recursive: true });
const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const page = await browser.newPage({ viewport: { width: 2000, height: 1200 }, deviceScaleFactor: 1 });

  const htmlPath = path.join(DIR, 'theme-sampler-4.html').replace(/\\/g, '/');
  await page.goto('file:///' + htmlPath, { waitUntil: 'load' });
  await page.waitForTimeout(500);

  const slides = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.slide')).map(s => ({
      id: s.getAttribute('data-slide-id'),
      el: s
    }))
  );

  // Get slide IDs via evaluate since elements aren't directly transferable
  const ids = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.slide')).map(s => s.getAttribute('data-slide-id'))
  );

  for (const id of ids) {
    const sel = '[data-slide-id="' + id + '"]';
    const el = page.locator(sel);
    const file = id.replace('theme-', '') + '.png';
    await el.screenshot({ path: path.join(PNGDIR, file) });
    console.log('Captured: ' + file);
  }

  await browser.close();
  console.log('Done. ' + ids.length + ' screenshots saved to sampler-png/');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
