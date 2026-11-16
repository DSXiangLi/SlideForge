/* phase6-batch1 / apply-page-composition.js
 * 为 4 套 theme.md 的 G10 composition_program 新增顶层字段 page_composition，
 * 落在 doctrine 行之后（同缩进层级）。幂等：已存在则跳过。
 */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const THEMES = {
  e6: { rel: 'skills/SlideForge/references/themes/color/e6/theme.md', block: `page_composition:
  skeleton: 模块网格 + Z 型动线
  grid: {margin: 120, gutter: 40, columns: 12}
  balance: {anchor: 标题块(左上), counterweight: 右上装饰块}
  whitespace_ratio: "≥50%"
  flow: "Z 型：标题(左上) → 装饰(右上) → 正文两栏(中) → 数据三块(下) → 页脚"
` },
  g2: { rel: 'skills/SlideForge/references/themes/color/g2/theme.md', block: `page_composition:
  skeleton: 非对称两栏（正文 : 批注 ≈ 58 : 4 : 38）
  grid: {margin: 120, gutter: 40, text_col: 980, index_col: 560}
  balance: {anchor: 正文栏(左), counterweight: 批注索引脊(右)}
  whitespace_ratio: "≥50%"
  flow: "左 → 右：正文行 → 荧光引线 → 批注索引脊"
` },
  e7: { rel: 'skills/SlideForge/references/themes/texture/e7/theme.md', block: `page_composition:
  skeleton: 对角线纵深（前景大物 → 远景）
  grid: {margin: 120, gutter: 40}
  balance: {anchor: 前景版(右下,重), counterweight: 印章(右上) + 远景(左上,轻)}
  whitespace_ratio: "≥55%"
  flow: "对角：远景(左上,轻) → 中景 → 前景(右下,重)；上 1/3 留白做天空"
` },
  f1: { rel: 'skills/SlideForge/references/themes/light/f1/theme.md', block: `page_composition:
  skeleton: 对角深度栈（默认）/ 中心聚焦（备选 full-b）
  grid: {margin: 120, gutter: 40}
  balance: {anchor: 前景玻璃(右下,实), counterweight: 柔光斑(左上/右上)}
  whitespace_ratio: "≥60%"
  flow: "对角：远景(左上,透) → 中景 → 前景(右下,实)；重心回光学中心"
` }
};
const log = [];
for (const [id, cfg] of Object.entries(THEMES)) {
  const f = path.join(ROOT, cfg.rel);
  let txt = fs.readFileSync(f, 'utf8');
  if (txt.includes('page_composition:')) { log.push(id + ': 已含 page_composition，跳过'); continue; }
  const m = txt.match(/\ndoctrine:[^\n]*\n/);
  if (!m) { log.push(id + ': 未找到 doctrine 行，跳过'); continue; }
  txt = txt.replace(m[0], m[0] + '\n' + cfg.block);
  fs.writeFileSync(f, txt, 'utf8');
  log.push(id + ': 已插入 page_composition');
}
fs.writeFileSync(path.join(__dirname, 'apply-page-composition.log'), log.join('\n'), 'utf8');
console.log(log.join('\n'));
