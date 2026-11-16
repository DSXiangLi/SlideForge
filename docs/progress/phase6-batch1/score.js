/* phase6-batch1 / score.js
 * 26 套未升级主题的「问题严重度」评分。机器项来自实测数据，人工项逐套列理由。
 * 输出 score.json / score.txt，供 brief.md 引用与复核。
 */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const DIR = path.join(ROOT, 'docs/progress/phase6-batch1');
const scan = JSON.parse(fs.readFileSync(path.join(ROOT, 'analysis/_scan-themes.json'), 'utf8'));
const fp = JSON.parse(fs.readFileSync(path.join(ROOT, 'analysis/_fingerprint.json'), 'utf8'));

// 骨架层相关矩阵 → 每图与其他 27 图的均值
const labels = fp.matrix_labels, M = fp.matrix;
const skel = {};
labels.forEach((f, i) => {
  let s = 0, n = 0;
  for (let k = 0; k < labels.length; k++) if (k !== i) { s += M[i][k]; n++; }
  skel[f.replace('.png', '').toLowerCase()] = s / n;
});
const sim = {};
fp.per_image.forEach(p => { sim[p.file.replace('.png', '').toLowerCase()] = p.sim_to_mean; });

// 旧 Gallery 现役 11 套（HANDOVER §4 的 G 标记）
const GALLERY = new Set(['c1', 'e7', 'g1', 'f1', 'e2', 'e3', 'e10', 'f2', 'e6', 'g2', 'g4']);
// 旧 sampler 图名（pNN-id）
const PNG = { a1:'p01-a1', c1:'p03-c1', c2:'p04-c2', c4:'p06-c4', d1:'p07-d1', d2:'p08-d2', d3:'p09-d3',
  e1:'p10-e1', e2:'p11-e2', e3:'p12-e3', e4:'p13-e4', e6:'p15-e6', e7:'p16-e7', e8:'p17-e8',
  e9:'p18-e9', e10:'p19-e10', e11:'p20-e11', e12:'p21-e12', f1:'p22-f1', f2:'p23-f2', f3:'p24-f3',
  g1:'p25-g1', g2:'p26-g2', g4:'p28-g4', g5:'p29-g5' };

// 人工项 D：身份是否只是「可贴任意版式的贴纸/容器皮肤」（G10 草案 §1 DOM 结构测试）
// 3 = 纯装饰或纯容器皮肤；1.5 = 已含信息容器/结构语义；0 = 已有构图主权
const D = {
  a1:[3,'Ghost 残影巨字只是背景层'], c1:[1.5,'橙色块是唯一焦点，已有面积主张'], c2:[1.5,'标本引线缝合图与图注'],
  c4:[1.5,'首字下沉是段落结构的一部分'], d1:[3,'贴纸徽章'], d2:[3,'显影/辉光是动效与光效'],
  d3:[3,'笔触块垫在标题后'], d4:[3,'刻线框是容器皮肤'], e1:[1.5,'套色错位定义形状生成方式'],
  e2:[1.5,'尺寸标注线缝合图与尺寸'], e3:[1.5,'扇形放射定页顶结构'], e4:[1.5,'三几何形有构成关系'],
  e6:[3,'彩纸屑 inset:0 全页撒布，删掉 DOM 不变'], e7:[3,'姓名印 + 浪花带是草案 §1 点名反例'],
  e8:[1.5,'号外头条 + 多栏小字是版式结构'], e9:[1.5,'层理带段长可对应数据'], e10:[1.5,'星座连线是关系隐喻'],
  e11:[1.5,'撕线分主券/副券'], e12:[3,'硬偏移投影是容器皮肤'], f1:[3,'玻璃卡是容器皮肤，G4 还强制成阵'],
  f2:[3,'灯管卡 + 倒影是容器皮肤'], f3:[1.5,'地平线色带定义画幅'], g1:[3,'金箔奖章是落款贴纸'],
  g2:[3,'荧光带垫在关键词下，删掉 DOM 不变'], g4:[1.5,'满版黄底是面积主张'], g5:[3,'三色反转卡是容器皮肤']
};
// 人工项 F：与已升级 4 套或跨轴 >0.8 撞脸 / 同设计轴全靠单一语言
const F = {
  a1:[3,'与 B1 骨架相关 0.833'], c1:[2,'色法轴 7 套全靠色彩'], c2:[2,'质感轴 8 套'], c4:[2,'质感轴 8 套'],
  d1:[2,'质感轴 8 套'], d2:[2,'光线轴 4 套全靠光效'], d3:[2,'质感轴 8 套'], d4:[2,'质感轴 8 套'],
  e1:[2,'色法轴 7 套全靠色彩'], e2:[3,'与 B1 0.808、与 E7 0.822'], e3:[1,'空间轴'], e4:[1,'空间轴'],
  e6:[3,'与已升级 C3 骨架相关 0.851'], e7:[3,'与已升级 H1 世界重叠 + 与 E2 0.822'],
  e8:[1,'线法轴'], e9:[1,'质感轴'], e10:[3,'字法轴且与 C3 0.730'], e11:[1,'线法轴'],
  e12:[3,'与 G2 骨架相关 0.811'], f1:[2,'光线轴 4 套全靠光效'], f2:[2,'光线轴 4 套全靠光效'],
  f3:[3,'与 G2 骨架相关 0.924（全库最高）'], g1:[2,'色法轴 7 套全靠色彩'],
  g2:[3,'与 F3 0.924、E12 0.811'], g4:[2,'色法轴 7 套全靠色彩'], g5:[2,'色法轴 7 套全靠色彩']
};

function bScore(v) { return v >= 0.43 ? 3 : v >= 0.40 ? 2.5 : v >= 0.35 ? 2 : v >= 0.28 ? 1.5 : 1; }
function cScore(v) { return v >= 0.78 ? 3 : v >= 0.65 ? 2 : v >= 0.50 ? 1 : 0; }
function eScore(o) {
  const R = o.risks;
  let v = 0;
  if (R.includes('backdrop-filter')) v += .5;
  if (R.includes('text-shadow')) v += .5;
  if (R.includes('filter:')) v += .5;
  if (R.includes('blur(')) v += .5;
  if (R.includes('inset:0')) v += .5;
  if (R.includes('opacity')) v += .5;
  if (R.includes('gradient')) v += .5;
  if (R.includes('rotate(')) v += .5;
  if (R.includes('box-shadow')) v += .5;
  // G4/G8 明令「卡片成阵」= 默认构图被写进制度
  if (/成阵|卡片墙|网格矩阵/.test(o.affinity + o.taboo + JSON.stringify(o))) v += 0; // 占位：见下方硬编码
  return Math.min(3, v);
}
// 卡片成阵的制度性加分（逐套人工核对 G4「高密度容器边界」）
const ARRAY = new Set(['e6','f1','f2','g2','g1','e12','d1','c2']);

const rows = scan.map(o => {
  const id = o.id.toLowerCase();
  const png = PNG[id] || '';
  const A = GALLERY.has(id) ? 3 : 0;
  const bRaw = skel[png] != null ? +skel[png].toFixed(3) : null;
  const cRaw = sim[png] != null ? sim[png] : null;
  const B = bRaw == null ? 0 : bScore(bRaw);
  const C = cRaw == null ? 0 : cScore(cRaw) * 0.5;
  const dInfo = D[id] || [1.5, '未逐条判读'];
  const eVal = Math.min(3, eScore(o) + (ARRAY.has(id) ? 1 : 0));
  const fInfo = F[id] || [1, '一般'];
  const total = +(A + B + C + dInfo[0] + eVal + fInfo[0] * 0.5).toFixed(2);
  return {
    id: o.id, name: o.name, A, B, bRaw, C, cRaw, D: dInfo[0], dWhy: dInfo[1],
    E: eVal, eWhy: o.risks.join(',') + (ARRAY.has(id) ? ' + G4卡片成阵' : ''),
    F: fInfo[0] * 0.5, fWhy: fInfo[1], total
  };
});
rows.sort((a, b) => b.total - a.total || a.id.localeCompare(b.id));
rows.forEach((r, i) => r.rank = i + 1);
fs.writeFileSync(path.join(DIR, 'score.json'), JSON.stringify(rows, null, 2));
fs.writeFileSync(path.join(DIR, 'score.txt'),
  ['rank | id | A曝光 | B撞脸(原始) | C平均脸(原始) | D贴纸化 | E风险 | F轴内 | 总分 | D理由 | F理由',
   ...rows.map(r => [r.rank, r.id, r.A, `${r.B}(${r.bRaw})`, `${r.C}(${r.cRaw})`, r.D, r.E, r.F, r.total, r.dWhy, r.fWhy].join(' | '))].join('\n'));
console.log('ok');
