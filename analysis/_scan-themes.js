// 扫描 26 套未升级主题的结构指标，输出 JSON 供评审
const fs = require('fs');
const path = require('path');
const ROOT = 'C:/Users/lixiang/Desktop/SlideForge/skills/SlideForge/references/themes';
const DONE = new Set(['b1', 'c3', 'e5', 'h1']);
const files = [];
for (const cat of fs.readdirSync(ROOT)) {
  const catDir = path.join(ROOT, cat);
  if (!fs.statSync(catDir).isDirectory()) continue;
  for (const id of fs.readdirSync(catDir)) {
    const f = path.join(catDir, id, 'theme.md');
    if (DONE.has(id) || !fs.existsSync(f)) continue;
    files.push({ cat, id, f });
  }
}
function grab(txt, re) { const m = txt.match(re); return m ? m[1].trim().replace(/\s+/g, ' ') : ''; }
function section(txt, name) {
  const i = txt.indexOf('**' + name);
  if (i < 0) return '';
  const j = txt.indexOf('**G', i + 4);
  return txt.slice(i, j < 0 ? i + 1800 : j);
}
const RISK = ['opacity', 'text-shadow', 'filter:', 'blur(', 'gradient', 'rotate(', 'inset:0', '::before', '::after', 'mix-blend', 'box-shadow', 'backdrop-filter'];
const out = [];
for (const { cat, id, f } of files) {
  const t = fs.readFileSync(f, 'utf8');
  const g9 = section(t, 'G9 motif');
  const g2 = section(t, 'G2 typography');
  const g8 = section(t, 'G8 component');
  const cssBlocks = [...t.matchAll(/```css([\s\S]*?)```/g)].map(m => m[1]).join('\n');
  const g9css = [...g9.matchAll(/```css([\s\S]*?)```/g)].map(m => m[1]).join('\n');
  out.push({
    id: id.toUpperCase(), cat,
    name: grab(t, /^#\s+(.+)$/m),
    lines: t.split('\n').length,
    hasG10: /composition_program/.test(t),
    hasPx1920: /px@1920/.test(t),
    hasTRole: /--t-display|--t-body/.test(t),
    hasBake: /\*\*bake_brief\*\*/.test(t),
    world: grab(t, /\*\*世界参考\*\*：(.*)/),
    unforgettable: grab(t, /\*\*unforgettable\*\*：(.*)/),
    diff: grab(t, /\*\*分化声明\*\*：(.*)/),
    focus: grab(t, /\*\*focus\*\*：(.*)/),
    typeScale: grab(g2, /\*\*字号对比\*\*：(.*)/) || grab(t, /\*\*字号对比\*\*：(.*)/),
    weightMap: grab(g2, /\*\*字重映射\*\*：(.*)/) || grab(t, /\*\*字重映射\*\*：(.*)/),
    affinity: grab(g8, /\*\*亲和\*\*：(.*)/) || grab(t, /\*\*亲和\*\*：(.*)/),
    taboo: grab(g8, /\*\*禁忌\*\*：(.*)/) || grab(t, /\*\*禁忌\*\*：([^\n]*)/),
    g9words: grab(g9, /\*\*词汇\*\*：(.*)/),
    g9CssLines: g9css ? g9css.split('\n').filter(x => x.trim()).length : 0,
    risks: RISK.filter(k => g9css.includes(k)),
    cqwCount: (cssBlocks.match(/cqw/g) || []).length,
    hasGradient: /gradient\(/i.test(g9css),
    hasOpacity: /opacity\s*:/.test(g9css),
    hasRot: /rotate\(/.test(g9css),
    hasFullBleed: /inset\s*:\s*0/.test(g9css),
    accentBudget: grab(t, /\*\*accent 预算\*\*：(.*)/).slice(0, 160),
    blueprints: /layout_blueprints/.test(t),
  });
}
out.sort((a, b) => a.id.localeCompare(b.id));
fs.writeFileSync('C:/Users/lixiang/Desktop/SlideForge/analysis/_scan-themes.json', JSON.stringify(out, null, 2));
// 同时输出紧凑表格
const rows = out.map(o => [o.id, o.name, o.cat, o.lines, o.hasBake ? 'B' : '-', o.hasG10 ? 'G10' : '-', o.g9CssLines, o.risks.join(','), o.cqwCount, (o.typeScale || '').slice(0, 60), (o.unforgettable || '').slice(0, 90)].join(' | '));
fs.writeFileSync('C:/Users/lixiang/Desktop/SlideForge/analysis/_scan-themes.txt', rows.join('\n'));
console.log('done ' + out.length);
