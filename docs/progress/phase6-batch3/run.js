/* phase6-batch3 / run.js  (Step 4a: 8 页截图 + 审计)
 * Playwright + 系统 Chrome：8 页逐页 1920×1080 截图 + 9 项自动审计。
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

const DIR = __dirname;
const PNGDIR = path.join(DIR, 'png');
if (!fs.existsSync(PNGDIR)) fs.mkdirSync(PNGDIR, { recursive: true });
const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
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
            // Measure actual text rendering width via Range API (not block container width)
            let textWidth = b.w;
            try {
              const range = document.createRange();
              range.selectNodeContents(c);
              const rects = range.getClientRects();
              if (rects.length > 0) textWidth = Math.round(rects[0].width);
            } catch(e) {}
            // record parent element id for overlap parent-child exclusion
            const parentId = c.parentElement && c.parentElement !== slide ? (c.parentElement.id || c.parentElement.className || c.parentElement.tagName) : null;
            out.push({
              tag: c.tagName.toLowerCase(), cls: (c.className || '').toString().slice(0, 48),
              text: c.textContent.trim().slice(0, 24), ...b, textWidth, fs,
              opacity: +parseFloat(cs.opacity).toFixed(2), transformed,
              inlineFontSize: c.style.fontSize || '',
              contentOverflow: c.scrollHeight > c.clientHeight + 14 && c.clientHeight > 0,
              scroll: [c.scrollHeight, c.clientHeight],
              container: cbox, containerOverflow: cOver,
              parentId
            });
          }
          walk(c);
        }
      };
      walk(slide);
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
      const inline = Array.from(slide.querySelectorAll('[style]')).filter(e => e.style.fontSize && !/var\(--t-/.test(e.style.fontSize)).map(e => ({
        tag: e.tagName.toLowerCase(), cls: (e.className || '').toString(), value: e.style.fontSize
      }));
      return { nodes: out, roleFonts, floorViolations, inline };
    }, { sel, FLOOR });

    const nodes = audit.nodes;
    const overflow = nodes.filter(a => a.x < -2 || a.y < -2 || a.x + a.w > W + 2 || a.y + a.h > H + 2);
    const containerOverflow = nodes.filter(a => a.containerOverflow);
    const contentOverflow = nodes.filter(a => a.contentOverflow);
    const weakRead = nodes.filter(a => a.fs >= 18 && a.opacity < 0.9 && a.opacity > 0);
    const big = nodes.filter(a => a.w * a.h > 2000 && a.h > 12 && !a.transformed);
    // Exclude parent-child pairs: a span inside a div is not an overlap
    const childParentMap = {};
    nodes.forEach(n => { if (n.parentId) childParentMap[n.tag + ':' + n.cls + ':' + n.text] = n.parentId; });
    const isParentChild = (a, b) => {
      // Check if a is parent of b or b is parent of a by comparing text content
      // A parent contains all text of the child, and child text is a prefix/substring
      if (a.text && b.text && a.text.includes(b.text) && a.w >= b.w && a.h >= b.h) return true;
      if (a.text && b.text && b.text.includes(a.text) && b.w >= a.w && b.h >= a.h) return true;
      return false;
    };
    const overlaps = [];
    for (let i = 0; i < big.length; i++) for (let j = i + 1; j < big.length; j++) {
      const a = big[i], b = big[j];
      if (isParentChild(a, b)) continue;
      const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
      const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
      if (ox > 12 && oy > 12) overlaps.push({ a: a.text, b: b.text, ox, oy });
    }
    const sizes = nodes.map(a => a.fs).filter(x => x > 0);
    const ratio = +(Math.max(...sizes) / Math.min(...sizes)).toFixed(2);

    // 9-grid blank cell detection: divide canvas into 3x3, check each cell has content
    const CW3 = W / 3, CH3 = H / 3; // 640, 360
    const gridCells = [];
    for (let gy = 0; gy < 3; gy++) for (let gx = 0; gx < 3; gx++) {
      const cx = gx * CW3, cy = gy * CH3;
      const hasContent = nodes.some(n =>
        n.x + n.w > cx + 20 && n.x < cx + CW3 - 20 &&
        n.y + n.h > cy + 20 && n.y < cy + CH3 - 20
      );
      if (!hasContent) gridCells.push({ row: gy + 1, col: gx + 1, x: cx, y: cy });
    }

    // Title flush detection: display-size text (fs >= 80) whose actual rendered text width
    // (measured via Range API, not block width) exceeds 97% of container inner width
    const titleFlush = [];
    nodes.forEach(n => {
      if (n.container && n.fs >= 80 && n.container.w > 0 && n.text.length > 4) {
        const innerW = n.container.w - 52 - 6; // padding 26*2 + border 3*2
        const tw = n.textWidth || n.w;
        const ratio = tw / innerW;
        if (ratio > 0.97) titleFlush.push({ text: n.text.slice(0, 20), textWidth: tw, innerW, ratio: +ratio.toFixed(3) });
      }
    });

    // Same-group width detection: KPI heading numbers (fs>=40) in the same flex row
    // should be inside equal-width containers, not have equal text widths themselves.
    // Instead, detect if their container x-positions create unequal columns:
    // Group KPIs by y-band, check if their x-spacing is irregular
    const groupWidthMismatch = [];
    const kpiNodes = nodes.filter(n => n.fs >= 40 && n.text.length >= 3 && n.y < 1000);
    // Group by y-band
    const yBands = {};
    kpiNodes.forEach(n => {
      const band = Math.round(n.y / 20) * 20;
      if (!yBands[band]) yBands[band] = [];
      yBands[band].push(n);
    });
    Object.entries(yBands).forEach(([band, items]) => {
      if (items.length >= 2) {
        // Check x-spacing: sort by x, check if gaps are equal
        items.sort((a, b) => a.x - b.x);
        for (let i = 1; i < items.length; i++) {
          const gap = items[i].x - (items[i-1].x + items[i-1].w);
          // Only flag if items overlap or gap is negative (real alignment problem)
          if (gap < -5) groupWidthMismatch.push({
            a: items[i-1].text.slice(0, 16), aX: items[i-1].x, aW: items[i-1].w,
            b: items[i].text.slice(0, 16), bX: items[i].x, bW: items[i].w, gap
          });
        }
      }
    });

    const role = await el.getAttribute('data-role');
    report.pages[ids[n]] = {
      file, theme: await el.getAttribute('data-theme'), role,
      textNodes: nodes.length, minFont: Math.min(...sizes), maxFont: Math.max(...sizes), ratio,
      canvasOverflow: overflow, containerOverflow, contentOverflow, weakRead,
      textOverlaps: overlaps, inlineFontSize: audit.inline,
      roleFonts: audit.roleFonts, floorViolations: audit.floorViolations,
      blankGridCells: gridCells, titleFlush, groupWidthMismatch,
      nodes
    };
    console.log(`${n + 1}/${ids.length} ${ids[n]}: overflow=${overflow.length} cOver=${containerOverflow.length} weak=${weakRead.length} overlap=${overlaps.length} inline=${audit.inline.length} ratio=${ratio} blankCells=${gridCells.length} titleFlush=${titleFlush.length} groupWidth=${groupWidthMismatch.length}`);
  }

  const P = Object.values(report.pages);
  const sum = k => P.reduce((s, p) => s + p[k].length, 0);
  report.summary = {
    pages: P.length,
    canvasOverflow: sum('canvasOverflow'), containerOverflow: sum('containerOverflow'),
    contentOverflow: sum('contentOverflow'), weakRead: sum('weakRead'),
    textOverlaps: sum('textOverlaps'), inlineFontSize: sum('inlineFontSize'),
    floorViolations: sum('floorViolations'), pageErrors: errors.length,
    lowDensityRatioMin: Math.min(...P.filter(p => ['claim'].includes(p.role)).map(p => p.ratio)),
    blankGridCells: P.reduce((s, p) => s + (p.blankGridCells ? p.blankGridCells.length : 0), 0),
    titleFlush: P.reduce((s, p) => s + (p.titleFlush ? p.titleFlush.length : 0), 0),
    groupWidthMismatch: P.reduce((s, p) => s + (p.groupWidthMismatch ? p.groupWidthMismatch.length : 0), 0),
  };
  fs.writeFileSync(path.join(DIR, 'report.json'), JSON.stringify(report, null, 2));
  console.log('SUMMARY', JSON.stringify(report.summary));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
