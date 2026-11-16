/* phase6-batch1 / run.js
 * Playwright + 系统 Chrome：40 页逐页 1920×1080 截图 + 9 项自动审计。
 * 复用 phase3/4 的四类版面审计，新增：裸写 inline font-size、字号地板、层级落差、
 * 内容溢出（scrollHeight）、G10 几何不变量的 DOM 举证。
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('C:/Users/lixiang/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const DIR = __dirname;
const PNGDIR = path.join(DIR, 'png');
if (!fs.existsSync(PNGDIR)) fs.mkdirSync(PNGDIR, { recursive: true });
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const W = 1920, H = 1080;
const FLOOR = { display: 64, heading: 32, subhead: 24, body: 18, caption: 16, meta: 14, vertical: 64 };

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const page = await browser.newPage({ viewport: { width: 2000, height: 1200 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto('file:///' + path.join(DIR, 'sampler.html').replace(/\\/g, '/'), { waitUntil: 'load' });
  await page.waitForTimeout(400);

  const ids = await page.evaluate(() => Array.from(document.querySelectorAll('.slide')).map(s => s.id));
  const report = { generated: new Date().toISOString(), canvas: [W, H], pageCount: ids.length, pages: {}, pageErrors: errors };

  for (let n = 0; n < ids.length; n++) {
    const sel = '#' + ids[n];
    const el = page.locator(sel);
    const file = ids[n].replace(/^s-/, '') + '.png';
    await el.screenshot({ path: path.join(PNGDIR, file) });

    const audit = await page.evaluate(({ sel, FLOOR }) => {
      const slide = document.querySelector(sel);
      const box = slide.getBoundingClientRect();
      const rel = r => ({ x: Math.round(r.left - box.left), y: Math.round(r.top - box.top), w: Math.round(r.width), h: Math.round(r.height) });
      const out = [];
      const walk = node => {
        for (const c of node.children) {
          const cs = getComputedStyle(c);
          if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) continue;
          const hasOwnText = Array.from(c.childNodes).some(x => x.nodeType === 3 && x.textContent.trim());
          if (hasOwnText) {
            const b = rel(c.getBoundingClientRect());
            const fs = Math.round(parseFloat(cs.fontSize));
            let p = c.parentElement, container = null;
            while (p && p !== slide) {
              const ps = getComputedStyle(p);
              if (ps.position === 'absolute' && p.style.top && p.style.height) { container = p; break; }
              p = p.parentElement;
            }
            let cbox = null, cOver = false;
            if (container) {
              const cb = rel(container.getBoundingClientRect());
              cbox = cb;
              cOver = b.y < cb.y - 12 || b.y + b.h > cb.y + cb.h + 12 || b.x < cb.x - 2 || b.x + b.w > cb.x + cb.w + 2;
            }
            let transformed = cs.transform !== 'none';
            let q = c.parentElement;
            while (q && q !== slide && !transformed) { transformed = getComputedStyle(q).transform !== 'none'; q = q.parentElement; }
            out.push({
              tag: c.tagName.toLowerCase(), cls: (c.className || '').toString().slice(0, 48),
              text: c.textContent.trim().slice(0, 24), ...b, fs,
              opacity: +parseFloat(cs.opacity).toFixed(2), transformed,
              inlineFontSize: c.style.fontSize || '',
              contentOverflow: c.scrollHeight > c.clientHeight + 14 && c.clientHeight > 0,
              scroll: [c.scrollHeight, c.clientHeight],
              container: cbox, containerOverflow: cOver
            });
          }
          walk(c);
        }
      };
      walk(slide);
      // 角色类 computed 字号 vs 地板
      const roleFonts = {};
      let floorViolations = [];
      ['display', 'heading', 'subhead', 'body', 'caption', 'meta', 'vertical'].forEach(r => {
        const e = slide.querySelector('.t-' + r);
        if (e) {
          const v = Math.round(parseFloat(getComputedStyle(e).fontSize));
          roleFonts[r] = v;
          if (v < FLOOR[r]) floorViolations.push({ role: r, value: v, floor: FLOOR[r] });
        }
      });
      // 裸写 inline font-size（含任意元素，不限文本节点）
      const inline = Array.from(slide.querySelectorAll('[style]')).filter(e => e.style.fontSize).map(e => ({
        tag: e.tagName.toLowerCase(), cls: (e.className || '').toString(), value: e.style.fontSize
      }));
      // G10 几何不变量的 DOM 举证
      const invariants = {
        blocks: slide.querySelectorAll('.mt-mem-block').length,
        path: slide.querySelectorAll('.mt-mem-path').length,
        leads: slide.querySelectorAll('.mt-hl-lead').length,
        indexes: slide.querySelectorAll('.mt-hl-index').length,
        lineno: slide.querySelectorAll('.mt-hl-lineno').length,
        plates: slide.querySelectorAll('.mt-uki-plate').length,
        bands: slide.querySelectorAll('.mt-uki-band').length,
        seals: slide.querySelectorAll('.mt-uki-seal').length,
        depths: slide.querySelectorAll('.mt-gls-depth').length,
        axis: slide.querySelectorAll('.mt-gls-axis').length,
        chips: slide.querySelectorAll('.mt-gls-chip-n').length,
        vertical: Array.from(slide.querySelectorAll('*')).filter(e => getComputedStyle(e).writingMode.startsWith('vertical')).length,
        grid3: 0
      };
      return { nodes: out, roleFonts, floorViolations, inline, invariants };
    }, { sel, FLOOR });

    const nodes = audit.nodes;
    const overflow = nodes.filter(a => a.x < -2 || a.y < -2 || a.x + a.w > W + 2 || a.y + a.h > H + 2);
    const containerOverflow = nodes.filter(a => a.containerOverflow);
    const contentOverflow = nodes.filter(a => a.contentOverflow);
    const weakRead = nodes.filter(a => a.fs >= 18 && a.opacity < 0.9 && a.opacity > 0);
    const big = nodes.filter(a => a.w * a.h > 2000 && a.h > 12 && !a.transformed);
    const overlaps = [];
    for (let i = 0; i < big.length; i++) for (let j = i + 1; j < big.length; j++) {
      const a = big[i], b = big[j];
      const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
      const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
      if (ox > 12 && oy > 12) overlaps.push({ a: a.text, b: b.text, ox, oy });
    }
    const sizes = nodes.map(a => a.fs).filter(x => x > 0);
    const ratio = +(Math.max(...sizes) / Math.min(...sizes)).toFixed(2);
    const role = await el.getAttribute('data-role');
    report.pages[ids[n]] = {
      file, theme: await el.getAttribute('data-theme'), role,
      variant: await el.getAttribute('data-variant'),
      textNodes: nodes.length, minFont: Math.min(...sizes), maxFont: Math.max(...sizes), ratio,
      canvasOverflow: overflow, containerOverflow, contentOverflow, weakRead,
      textOverlaps: overlaps, inlineFontSize: audit.inline,
      roleFonts: audit.roleFonts, floorViolations: audit.floorViolations,
      invariants: audit.invariants, nodes
    };
    if (n % 10 === 9 || n === ids.length - 1) {
      console.log(`${n + 1}/${ids.length} done`);
    }
  }

  // 汇总
  const P = Object.values(report.pages);
  const sum = k => P.reduce((s, p) => s + p[k].length, 0);
  report.summary = {
    pages: P.length,
    canvasOverflow: sum('canvasOverflow'), containerOverflow: sum('containerOverflow'),
    contentOverflow: sum('contentOverflow'), weakRead: sum('weakRead'),
    textOverlaps: sum('textOverlaps'), inlineFontSize: sum('inlineFontSize'),
    floorViolations: sum('floorViolations'), pageErrors: errors.length,
    lowDensityRatioMin: Math.min(...P.filter(p => ['cover', 'claim', 'closing'].includes(p.role)).map(p => p.ratio)),
    baselinePages: P.filter(p => p.role !== 'stress').length,
    stressPages: P.filter(p => p.role === 'stress').length
  };
  fs.writeFileSync(path.join(DIR, 'report.json'), JSON.stringify(report, null, 2));
  fs.writeFileSync(path.join(DIR, 'audit-summary.txt'), JSON.stringify(report.summary, null, 2));
  console.log('SUMMARY', JSON.stringify(report.summary));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
