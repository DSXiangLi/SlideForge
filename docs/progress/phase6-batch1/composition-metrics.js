/* phase6-batch1 / composition-metrics.js
 * 页面级构图度量：光栅化文本 bbox，算覆盖率(留白=1-覆盖)、质心偏移、四象限密度。
 * 消费 run.js 产出的 report.json，输出 metrics.txt + metrics.json。
 */
const fs = require('fs');
const path = require('path');
const DIR = __dirname;
const r = require(path.join(DIR, 'report.json'));
const W = 1920, H = 1080, CELL = 20;
const CW = Math.ceil(W / CELL), CH = Math.ceil(H / CELL);

function analyze(page) {
  const grid = new Uint8Array(CW * CH);
  const ns = page.nodes || [];
  let cx = 0, cy = 0, n = 0;
  for (const nd of ns) {
    const x = Math.max(0, nd.x || 0), y = Math.max(0, nd.y || 0);
    const w = nd.w || 0, h = nd.h || 0;
    if (w <= 0 || h <= 0) continue;
    const x0 = Math.min(CW - 1, Math.floor(x / CELL));
    const x1 = Math.min(CW - 1, Math.floor((x + w - 1) / CELL));
    const y0 = Math.min(CH - 1, Math.floor(y / CELL));
    const y1 = Math.min(CH - 1, Math.floor((y + h - 1) / CELL));
    for (let yy = y0; yy <= y1; yy++) for (let xx = x0; xx <= x1; xx++) {
      const idx = yy * CW + xx;
      if (!grid[idx]) { grid[idx] = 1; cx += (xx + 0.5) * CELL; cy += (yy + 0.5) * CELL; n++; }
    }
  }
  const total = CW * CH;
  const cover = n / total;
  // 象限密度（按覆盖单元中心）
  const q = { TL: 0, TR: 0, BL: 0, BR: 0 };
  for (let yy = 0; yy < CH; yy++) for (let xx = 0; xx < CW; xx++) {
    if (grid[yy * CW + xx]) {
      const mx = (xx + 0.5) * CELL, my = (yy + 0.5) * CELL;
      q[my < 540 ? (mx < 960 ? 'TL' : 'TR') : (mx < 960 ? 'BL' : 'BR')]++;
    }
  }
  const gx = n ? Math.round(cx / n) : 0, gy = n ? Math.round(cy / n) : 0;
  return {
    cover: +(cover * 100).toFixed(1),
    whitespace: +((1 - cover) * 100).toFixed(1),
    centroid: [gx, gy],
    offset: [gx - 960, gy - 540],
    quad: { TL: +(q.TL / n * 100).toFixed(0) || 0, TR: +(q.TR / n * 100).toFixed(0) || 0, BL: +(q.BL / n * 100).toFixed(0) || 0, BR: +(q.BR / n * 100).toFixed(0) || 0 }
  };
}

const lines = [];
const out = {};
lines.push('页面 | 覆盖率% | 留白% | 质心 | 偏移 | 象限 TL/TR/BL/BR');
lines.push('--- | --- | --- | --- | --- | ---');
for (const [k, p] of Object.entries(r.pages)) {
  const m = analyze(p);
  out[k] = m;
  const flag = (Math.abs(m.offset[0]) > 180 || Math.abs(m.offset[1]) > 150 || m.whitespace < 35 || m.quad.TR + m.quad.BR > 85 || m.quad.TL + m.quad.BL > 85) ? ' ⚠️' : '';
  lines.push(`${k} | ${m.cover} | ${m.whitespace} | (${m.centroid[0]},${m.centroid[1]}) | (${m.offset[0]},${m.offset[1]}) | ${m.quad.TL}/${m.quad.TR}/${m.quad.BL}/${m.quad.BR}${flag}`);
}

// 关键页汇总
const key = ['s-e6-full', 's-g2-full', 's-e7-full', 's-f1-full', 's-f1-full-b'];
const sum = [];
for (const k of key) {
  if (!out[k]) continue;
  const m = out[k];
  sum.push(`${k}: 留白${m.whitespace}% 质心(${m.centroid[0]},${m.centroid[1]}) 偏移(${m.offset[0]},${m.offset[1]}) 象限TL${m.quad.TL}/TR${m.quad.TR}/BL${m.quad.BL}/BR${m.quad.BR}`);
}
lines.push('\n== 关键完整内容页 ==');
lines.push(...sum);

fs.writeFileSync(path.join(DIR, 'metrics.txt'), lines.join('\n'), 'utf8');
fs.writeFileSync(path.join(DIR, 'metrics.json'), JSON.stringify(out, null, 2), 'utf8');
console.log('metrics done,', Object.keys(out).length, 'pages');
