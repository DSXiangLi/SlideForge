/* phase6-batch1 / verify-theme.js
 * 校验 4 份 theme.md 的 G10 落地：7 字段齐备 / 令牌注入 / 结构件类唯一 / 旧条款已改 / CSS 纪律。
 */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const T = (p) => path.join(ROOT, 'skills/SlideForge/references/themes', p);
const FILES = { E6: 'color/e6/theme.md', G2: 'color/g2/theme.md', E7: 'texture/e7/theme.md', F1: 'light/f1/theme.md' };
const DISPLAY = { E6: '132px', G2: '112px', E7: '96px', F1: '108px' };
const FIELDS = ['doctrine:', 'signature_operator:', 'silhouette:', 'info_grammar:', 'type_scale:', 'invariants:', 'forbidden_defaults:', 'dna_events:'];
const out = [];
let bad = 0;
for (const [id, rel] of Object.entries(FILES)) {
  const t = fs.readFileSync(T(rel), 'utf8').replace(/\r\n/g, '\n');
  const miss = FIELDS.filter(f => !t.includes(f));
  const hasRoot = t.includes('--t-display:' + DISPLAY[id]) && t.includes('--t-body:24px');
  const g10 = t.slice(t.indexOf('**G10 composition_program**'), t.indexOf('**Variants 配色变体**'));
  const domTest = g10.includes('DOM 结构测试签署') && g10.includes('PASS');
  const geo = /invariants:[\s\S]*?(轴|角|左缘|位移|层|x |y )/.test(g10);
  const cssFence = t.slice(t.indexOf('```css', t.indexOf('**G9 motif**')));
  const cssBlock = cssFence.slice(0, cssFence.indexOf('```', 5));
  const literalHex = /#[0-9a-fA-F]{3,8}\b/.test(cssBlock);
  const badSelector = /\.slide|\.masthead|\.mastfoot/.test(cssBlock);
  const cssLines = cssBlock.split('\n').filter(x => x.trim() && !x.includes('```')).length;
  const stale = ['卡片墙成阵是它的原生形态', '便签卡成阵（旋转角全页统一方向', '玻璃卡成阵（同 gap 同 padding 同圆角）', '手账散布贴卡——不是居中内容带']
    .filter(s => t.includes(s));
  const ok = !miss.length && hasRoot && domTest && geo && !literalHex && !badSelector && cssLines <= 40 && !stale.length;
  if (!ok) bad++;
  out.push(`${id}: ${ok ? 'PASS' : 'FAIL'} | G10字段 ${8 - miss.length}/8 | 令牌 ${hasRoot} | DOM测试 ${domTest} | 几何不变量 ${geo} | G9 CSS ${cssLines}行(≤40) | 字面hex ${literalHex} | 框架选择器 ${badSelector} | 残留旧条款 ${stale.length}`);
  if (miss.length) out.push('  缺字段: ' + miss.join(','));
  if (stale.length) out.push('  残留: ' + stale.join(' / '));
}
// 类名全库唯一
const all = [];
for (const cat of fs.readdirSync(path.join(ROOT, 'skills/SlideForge/references/themes'))) {
  const d = path.join(ROOT, 'skills/SlideForge/references/themes', cat);
  if (!fs.statSync(d).isDirectory()) continue;
  for (const id of fs.readdirSync(d)) {
    const f = path.join(d, id, 'theme.md');
    if (!fs.existsSync(f)) continue;
    const t = fs.readFileSync(f, 'utf8');
    for (const m of t.matchAll(/\.(mt-[a-z0-9-]+)\s*\{/g)) all.push({ cls: m[1], id });
  }
}
const dup = {};
all.forEach(x => { (dup[x.cls] = dup[x.cls] || []).push(x.id); });
const conflicts = Object.entries(dup).filter(([, ids]) => new Set(ids).size > 1);
out.push(`母题类名总数 ${all.length}，跨主题重名 ${conflicts.length}`);
conflicts.slice(0, 10).forEach(([c, ids]) => out.push('  重名 ' + c + ' → ' + [...new Set(ids)].join(',')));
out.push(bad === 0 && conflicts.length === 0 ? 'VERIFY: ALL PASS' : `VERIFY: ${bad} 份主题不达标 / ${conflicts.length} 个重名`);
fs.writeFileSync(path.join(ROOT, 'docs/progress/phase6-batch1/theme-verify.txt'), out.join('\n'));
console.log(out.join('\n'));
