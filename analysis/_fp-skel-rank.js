// 从指纹矩阵计算每套未升级主题的「结构撞脸」指标
const fs = require('fs');
const j = JSON.parse(fs.readFileSync('C:/Users/lixiang/Desktop/SlideForge/analysis/_fingerprint.json', 'utf8'));
const labels = j.matrix_labels;
const M = j.matrix;
const N = labels.length;
const rows = [];
for (let i = 0; i < N; i++) {
  const vals = [];
  for (let k = 0; k < N; k++) if (k !== i) vals.push({ other: labels[k], v: M[i][k] });
  const mean = vals.reduce((s, x) => s + x.v, 0) / vals.length;
  const hi = vals.filter(x => x.v > 0.8).sort((a, b) => b.v - a.v).slice(0, 3);
  const max = vals.reduce((a, x) => x.v > a.v ? x : a, vals[0]);
  const img = j.per_image.find(p => p.file === labels[i]) || {};
  rows.push({
    file: labels[i], mean: +mean.toFixed(3), max: +max.v.toFixed(3), maxWith: max.other,
    n80: vals.filter(x => x.v > 0.8).length,
    top3: hi.map(x => x.other.replace('.png', '') + ':' + x.v.toFixed(2)).join(' / '),
    sim_to_mean: img.sim_to_mean, edge: img.edge_dominant, cx: img.cx, cy: img.cy,
  });
}
rows.sort((a, b) => b.mean - a.mean);
fs.writeFileSync('C:/Users/lixiang/Desktop/SlideForge/analysis/_fp-skel-rank.txt',
  rows.map(r => [r.file, r.mean, r.max, r.maxWith, r.n80, r.sim_to_mean, r.edge, r.top3].join(' | ')).join('\n'));
console.log('ok');
