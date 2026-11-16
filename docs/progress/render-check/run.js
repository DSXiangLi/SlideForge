// playwright-core 由 PLAYWRIGHT_CORE 环境变量定位（托管 node workspace），避免写死本机路径
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
const fs = require('fs');

const WORK = path.resolve(__dirname, '../../..');
const SKELETON = path.join(WORK, 'skills/SlideForge/assets/skeleton.html');
const EDITOR = path.join(WORK, 'editor.html');
const OUTDIR = path.join(WORK, 'docs/progress/render-check');

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';

// Each theme's :root token override — exact text from theme.md G9 block (px@1920)
const THEMES = {
  b1: { override: ':root{--ease-out:cubic-bezier(.2,.9,.25,1);--t-display:176px;--t-body:35px}', expect: { display: 176, body: 35 } },
  c3: { override: ':root{--t-display:104px;--t-body:35px}', expect: { display: 104, body: 35 } },
  e5: { override: ':root{--ease-out:cubic-bezier(.8,0,.2,1);--t-display:128px;--t-body:35px}', expect: { display: 128, body: 35 } },
  h1: { override: ':root{--ease-out:cubic-bezier(.2,.7,.3,1);--t-display:92px;--t-body:35px;--t-vertical:118px}', expect: { display: 92, body: 35, vertical: 118 } },
};

// A deliberately hostile theme token set — tries to push text below every legibility floor.
// The skeleton's max() must clamp these back up. This is the "design-level avoidance" proof.
const HOSTILE = ':root{--t-display:8px;--t-heading:8px;--t-subhead:8px;--t-body:4px;--t-caption:8px;--t-meta:6px;--t-vertical:8px}';

// Structural floors enforced by skeleton .t-* max() (px@1920)
const FLOORS = { display: 64, heading: 32, subhead: 24, body: 18, caption: 16, meta: 14, vertical: 64 };
const ROLES = Object.keys(FLOORS);
const EXPECT_DEFAULT = { display: 96, heading: 64, subhead: 40, body: 28, caption: 18, meta: 15, vertical: 96 };

const fileUrl = (p) => 'file://' + p.replace(/\\/g, '/');

// Screenshot-only helper: the skeleton's .reveal children start at opacity:0 until
// the JS marks a slide in-view. Forcing them visible makes the typography legible in
// the PNG. It only touches opacity/transform — never font-size.
const REVEAL_VISIBLE = '.js .slide .reveal{opacity:1!important;transform:none!important}';

const sampleDeck = `<!doctype html><html><head><meta charset="utf-8"><style>
:root{
  --t-display:96px; --t-heading:64px; --t-subhead:40px; --t-body:28px;
  --t-caption:18px; --t-meta:15px; --t-vertical:96px;
  --ink:#0d0d10; --paper:#f4f1ea; --accent:#e0322e;
  --font-display:'PingFang SC','Microsoft YaHei',sans-serif;
}
.t-display{font-size:max(var(--t-display),64px);line-height:1.15}
.t-heading{font-size:max(var(--t-heading),32px);line-height:1.25}
.t-subhead{font-size:max(var(--t-subhead),24px);line-height:1.3}
.t-body{font-size:max(var(--t-body),18px);line-height:1.6}
.t-caption{font-size:max(var(--t-caption),16px);line-height:1.5}
.t-meta{font-size:max(var(--t-meta),14px);line-height:1.4}
.t-vertical{font-size:max(var(--t-vertical),64px);line-height:1.12;writing-mode:vertical-rl}
.slide{position:relative;width:1920px;height:1080px;background:var(--ink);color:var(--paper);font-family:var(--font-display);padding:120px;box-sizing:border-box}
</style></head><body>
<section class="slide" data-slide-id="s1">
  <h1 id="target1" class="t-display" data-editable>产品发布会主题</h1>
  <p id="target2" class="t-body" data-editable style="margin-top:40px">这是一段说明文字，用于验证角色切换后字号是否跟随令牌、且不再出现裸写 font-size。</p>
</section>
</body></html>`;

// Inject probe elements for roles the two example slides don't use.
const ensureProbes = (roles) => {
  roles.forEach((r) => {
    if (!document.querySelector('.t-' + r)) {
      const d = document.createElement('div');
      d.className = 't-' + r;
      d.textContent = r + ' probe';
      d.style.position = 'fixed';
      d.style.left = '-9999px';
      d.style.top = '0';
      document.body.appendChild(d);
    }
  });
};

const measureFn = (roles) => {
  const out = {};
  for (const r of roles) {
    const el = document.querySelector('.t-' + r);
    out[r] = el ? Math.round(parseFloat(getComputedStyle(el).fontSize)) : null;
  }
  return out;
};

(async () => {
  const report = { generator: { scenarios: {} }, editor: {}, verdict: {} };
  let browser;
  try {
    browser = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox', '--disable-gpu'] });
  } catch (e) {
    report.fatal = 'launch failed: ' + e.message;
    fs.writeFileSync(path.join(OUTDIR, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
    return;
  }

  // ---------- GENERATOR: one FRESH page per scenario (no cumulative CSS) ----------
  async function genScenario(name, css) {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    const errs = [];
    page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
    page.on('pageerror', (e) => errs.push('PAGEERROR: ' + e.message));

    await page.goto(fileUrl(SKELETON), { waitUntil: 'load' });
    await page.waitForTimeout(250);
    if (css) await page.addStyleTag({ content: css });
    await page.evaluate(ensureProbes, ROLES);
    const measured = await page.evaluate(measureFn, ROLES);
    await page.addStyleTag({ content: REVEAL_VISIBLE });
    await page.screenshot({ path: path.join(OUTDIR, 'skeleton-' + name + '.png') });

    const floorViolations = ROLES.filter((r) => measured[r] != null && measured[r] < FLOORS[r])
      .map((r) => `${r}=${measured[r]} < ${FLOORS[r]}`);
    await page.close();
    return { measured, floorViolations, consoleErrors: errs };
  }

  const def = await genScenario('default', null);
  def.expected = EXPECT_DEFAULT;
  def.matchesExpected = ROLES.every((r) => def.measured[r] === EXPECT_DEFAULT[r]);
  report.generator.scenarios.default = def;

  for (const [key, t] of Object.entries(THEMES)) {
    const s = await genScenario(key, t.override);
    s.expected = t.expect;
    s.matchesExpected = Object.entries(t.expect).every(([r, v]) => s.measured[r] === v);
    report.generator.scenarios[key] = s;
  }

  const hostile = await genScenario('hostile', HOSTILE);
  hostile.clampedTo = Object.fromEntries(ROLES.map((r) => [r, FLOORS[r]]));
  hostile.allClamped = ROLES.every((r) => hostile.measured[r] === FLOORS[r]);
  report.generator.scenarios.hostile = hostile;

  report.generator.floors = FLOORS;

  // ---------- EDITOR ----------
  const epage = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  const edErr = [];
  epage.on('console', (m) => { if (m.type() === 'error') edErr.push(m.text()); });
  epage.on('pageerror', (e) => edErr.push('PAGEERROR: ' + e.message));
  await epage.goto(fileUrl(EDITOR), { waitUntil: 'load' });
  await epage.waitForTimeout(400);

  report.editor.stRoleExists = await epage.evaluate(() => !!document.querySelector('#stRole'));
  report.editor.stRoleOptions = await epage.evaluate(() => Array.from(document.querySelectorAll('#stRole option')).map((o) => o.value));
  report.editor.applyRoleType = await epage.evaluate(() => { try { return typeof applyRole; } catch (e) { return 'undefined'; } });
  report.editor.roleClasses = await epage.evaluate(() => { try { return JSON.parse(JSON.stringify(ROLE_CLASSES)); } catch (e) { return 'undefined'; } });
  report.editor.consoleErrors = edErr;

  const deckPath = path.join(OUTDIR, 'sample-deck.html');
  fs.writeFileSync(deckPath, sampleDeck);
  let interaction = { status: 'skip' };
  try {
    await epage.setInputFiles('#fileInput', deckPath);
    await epage.waitForTimeout(800);
    const deckFrame = await (await epage.$('#deckFrame')).contentFrame();
    await deckFrame.waitForSelector('#target1', { timeout: 5000 });
    await epage.addStyleTag({ content: REVEAL_VISIBLE });
    await epage.screenshot({ path: path.join(OUTDIR, 'editor-loaded.png') });

    // Seed a LEGACY bare font-size to verify applyRole() migrates it away.
    await deckFrame.evaluate(() => { document.querySelector('#target1').style.fontSize = '37px'; });
    const before = await deckFrame.evaluate(() => {
      const el = document.querySelector('#target1');
      return { cls: el.className, inlineFont: el.style.fontSize, computed: Math.round(parseFloat(getComputedStyle(el).fontSize)) };
    });

    await deckFrame.click('#target1');
    await epage.waitForTimeout(250);
    const stRoleDisabled = await epage.evaluate(() => document.querySelector('#stRole').disabled);

    let after = null;
    if (!stRoleDisabled) {
      await epage.selectOption('#stRole', 't-heading');
      await epage.waitForTimeout(250);
      after = await deckFrame.evaluate(() => {
        const el = document.querySelector('#target1');
        return { cls: el.className, inlineFont: el.style.fontSize, computed: Math.round(parseFloat(getComputedStyle(el).fontSize)) };
      });
      await epage.screenshot({ path: path.join(OUTDIR, 'editor-after-role-switch.png') });
    }
    interaction = {
      status: 'done', before, stRoleDisabled, after,
      legacyInlineCleared: after ? after.inlineFont === '' : null,
      roleApplied: after ? after.cls.indexOf('t-heading') >= 0 : null,
      oldRoleRemoved: after ? after.cls.indexOf('t-display') < 0 : null,
      sizeFollowedRole: after ? after.computed === 64 : null,
    };
  } catch (e) {
    interaction = { status: 'error', message: e.message };
  }
  report.editor.interaction = interaction;
  await epage.close();

  await browser.close();

  // ---------- VERDICT ----------
  const scen = report.generator.scenarios;
  const genOk =
    Object.keys(THEMES).every((k) => scen[k].matchesExpected && scen[k].floorViolations.length === 0) &&
    scen.default.matchesExpected && scen.default.floorViolations.length === 0 &&
    hostile.allClamped && hostile.floorViolations.length === 0;
  const edOk =
    report.editor.stRoleExists &&
    report.editor.applyRoleType === 'function' &&
    report.editor.stRoleOptions.length === 8 &&
    interaction.status === 'done' &&
    interaction.legacyInlineCleared === true &&
    interaction.roleApplied === true &&
    interaction.oldRoleRemoved === true &&
    interaction.sizeFollowedRole === true;
  report.verdict = {
    generator: genOk ? 'PASS' : 'FAIL',
    editor: edOk ? 'PASS' : 'FAIL',
    note: 'Two file:// CORS errors on /api/health are the editor probing a local bridge server in standalone mode — expected, unrelated to the role system.',
  };

  fs.writeFileSync(path.join(OUTDIR, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
})().catch((e) => {
  console.error('SCRIPT ERROR', e);
  process.exit(1);
});
