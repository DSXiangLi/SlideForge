const { chromium } = require('playwright-core');
const path = require('path');

const DIR = __dirname;
const HTML_PATH = path.join(DIR, 'theme-sampler-6.html');
const OUT_DIR = path.join(DIR, '..', '..', '..', 'assets', 'theme-sampler');

const CHROME_PATH = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

const themes = [
  { id: 'd4', name: 'batch6-d4' },
  { id: 'e9', name: 'batch6-e9' },
  { id: 'e8', name: 'batch6-e8' },
  { id: 'e11', name: 'batch6-e11' }
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
    const out = path.join(OUT_DIR, `${t.name}.png`);
    await el.screenshot({ path: out, type: 'png' });
    console.log(`Screenshot: ${t.name}.png`);
  }

  await browser.close();
  console.log('Done.');
})();
