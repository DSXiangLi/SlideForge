const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const DIR = __dirname;
const HTML_PATH = path.join(DIR, 'theme-sampler-6.html');
const OUT_DIR = DIR;

const CHROME_PATH = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PW_PATH = path.join(require('os').homedir(), '.workbuddy/binaries/node/workspace/node_modules');

const themes = [
  { id: 'd4', name: 'd4-brass-age' },
  { id: 'e9', name: 'e9-geo-strata' },
  { id: 'e10', name: 'e10-star-chart' },
  { id: 'e1', name: 'e1-riso-print' },
  { id: 'e8', name: 'e8-newsprint' },
  { id: 'e11', name: 'e11-ticket' }
];

(async () => {
  const browser = await chromium.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1
  });

  const page = await context.newPage();

  await page.goto('file:///' + HTML_PATH.replace(/\\/g, '/'), { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  for (const t of themes) {
    const sel = `[data-slide-id="theme-${t.id}"]`;
    const el = await page.$(sel);
    if (!el) { console.error(`NOT FOUND: ${t.id}`); continue; }
    const out = path.join(OUT_DIR, `sampler-${t.name}.png`);
    await el.screenshot({ path: out, type: 'png' });
    console.log(`Screenshot: sampler-${t.name}.png`);
  }

  await browser.close();
  console.log('Done.');
})();
