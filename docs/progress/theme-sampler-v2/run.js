/* theme-sampler-v2 / run.js  (rev2)
 * 用系统 Chrome 渲染 sampler.html：逐页 1920×1080 截图 + 版面审计。
 * rev2 新增：容器内部溢出检测（文本超出其定位祖先容器）、同层文本块重叠检测、
 *            灰化弱读检测（正文 opacity < .9 视为弱读）。
 * 复用 phase3 已装好的 playwright-core（托管 node workspace），不下载 Chromium。
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('C:/Users/lixiang/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const DIR = __dirname;
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const KEYS = ['b1', 'c3', 'e5', 'h1'];
const W = 1920, H = 1080;

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const page = await browser.newPage({ viewport: { width: 2000, height: 1200 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto('file:///' + path.join(DIR, 'sampler.html').replace(/\\/g, '/'), { waitUntil: 'load' });
  await page.waitForTimeout(300);

  const report = { generated: new Date().toISOString(), canvas: [W, H], pages: {}, pageErrors: errors };

  for (const k of KEYS) {
    const sel = '#s-' + k;
    const el = page.locator(sel);
    await el.screenshot({ path: path.join(DIR, `new-${k}.png`) });

    const audit = await page.evaluate((sel) => {
      const slide = document.querySelector(sel);
      const box = slide.getBoundingClientRect();
      const rel = (r) => ({
        x: Math.round(r.left - box.left), y: Math.round(r.top - box.top),
        w: Math.round(r.width), h: Math.round(r.height)
      });
      const out = [];
      const walk = (node) => {
        for (const c of node.children) {
          const cs = getComputedStyle(c);
          if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) continue;
          const hasOwnText = Array.from(c.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
          if (hasOwnText) {
            const r = c.getBoundingClientRect();
            const b = rel(r);
            const fs = Math.round(parseFloat(cs.fontSize));
            // 最近的「有明确 top 与 height 的绝对定位祖先」作为容器
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
              cOver = b.y < cb.y - 2 || b.y + b.h > cb.y + cb.h + 2 ||
                      b.x < cb.x - 2 || b.x + b.w > cb.x + cb.w + 2;
            }
            // 旋转/变换元素的 AABB 会虚胖，重叠判定需排除（记录以便人工复核）
            let transformed = cs.transform !== 'none';
            let q = c.parentElement;
            while (q && q !== slide && !transformed) {
              transformed = getComputedStyle(q).transform !== 'none';
              q = q.parentElement;
            }
            out.push({
              tag: c.tagName.toLowerCase(), cls: (c.className || '').toString().slice(0, 48),
              text: c.textContent.trim().slice(0, 24), ...b, fs,
              opacity: +parseFloat(cs.opacity).toFixed(2), transformed,
              container: cbox, containerOverflow: cOver
            });
          }
          walk(c);
        }
      };
      walk(slide);
      return out;
    }, sel);

    const overflow = audit.filter(a => a.x < -2 || a.y < -2 || a.x + a.w > W + 2 || a.y + a.h > H + 2);
    const containerOverflow = audit.filter(a => a.containerOverflow);
    const weakRead = audit.filter(a => a.fs >= 18 && a.opacity < 0.9 && a.opacity > 0);
    // 同层文本块矩形重叠（排除父子/装饰件）：只比较面积 > 2000 的文本块
    const big = audit.filter(a => a.w * a.h > 2000 && a.h > 12 && !a.transformed);
    const overlaps = [];
    for (let i = 0; i < big.length; i++) for (let j = i + 1; j < big.length; j++) {
      const a = big[i], b = big[j];
      const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
      const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
      if (ox > 12 && oy > 12) overlaps.push({ a: a.text, b: b.text, ox, oy });
    }
    const sizes = audit.map(a => a.fs).filter(n => n > 0);
    report.pages[k] = {
      file: `new-${k}.png`,
      textNodes: audit.length,
      minFont: Math.min(...sizes), maxFont: Math.max(...sizes),
      ratio: +(Math.max(...sizes) / Math.min(...sizes)).toFixed(2),
      canvasOverflow: overflow,
      containerOverflow,
      weakRead,
      textOverlaps: overlaps,
      nodes: audit
    };
    console.log(`${k}: nodes=${audit.length} font=${report.pages[k].minFont}-${report.pages[k].maxFont}px (${report.pages[k].ratio}:1) | canvasOverflow=${overflow.length} containerOverflow=${containerOverflow.length} weakRead=${weakRead.length} overlaps=${overlaps.length}`);
    containerOverflow.slice(0, 5).forEach(o => console.log('   CONTAINER', o.text, JSON.stringify(o.container)));
    overlaps.slice(0, 5).forEach(o => console.log('   OVERLAP', o.a, '<>', o.b, o.ox + 'x' + o.oy));
  }

  const floors = await page.evaluate(() => {
    const res = {};
    document.querySelectorAll('.slide').forEach(s => {
      const k = s.dataset.theme;
      res[k] = {};
      ['display', 'heading', 'subhead', 'body', 'caption', 'meta', 'vertical'].forEach(r => {
        const e = s.querySelector('.t-' + r);
        if (e) res[k][r] = Math.round(parseFloat(getComputedStyle(e).fontSize));
      });
    });
    return res;
  });
  report.roleFonts = floors;

  fs.writeFileSync(path.join(DIR, 'report.json'), JSON.stringify(report, null, 2), 'utf8');
  console.log('pageErrors:', errors.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
