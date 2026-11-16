/* phase6-batch1 / gen-pages.js
 * 生成验收包：复制旧图到 old/，产出 compare.html（4 组 A/B 并排）与 blind-test.html（灰度盲测）。
 */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const DIR = path.join(ROOT, 'docs/progress/phase6-batch1');
const OLD = [
  { id: 'e6', old: 'p15-e6.png', label: 'E6 孟菲斯' },
  { id: 'g2', old: 'p26-g2.png', label: 'G2 腮红荧光笔' },
  { id: 'e7', old: 'p16-e7.png', label: 'E7 浮世绘' },
  { id: 'f1', old: 'p22-f1.png', label: 'F1 浮光玻璃' }
];
const OLDIR = path.join(DIR, 'old');
if (!fs.existsSync(OLDIR)) fs.mkdirSync(OLDIR, { recursive: true });
OLD.forEach(o => fs.copyFileSync(path.join(ROOT, 'assets/theme-sampler', o.old), path.join(OLDIR, o.old)));

const blindMeta = JSON.parse(fs.readFileSync(path.join(DIR, 'blind-meta.json'), 'utf8'));

/* ---- compare.html ---- */
const groups = OLD.map((o, i) => {
  const newPng = `${o.id}-full.png`;
  return `<div class="grp">
  <div class="gtitle">${o.label} · 同一份完整内容「山禾集 1.1 整体特色及优势」（标题 + 两段正文 + 三 KPI + 三条理念 + 脚注，逐字一致）</div>
  <div class="cols">
    <div class="col"><div class="tag">旧 Gallery（换皮同骨架）</div><img src="old/${o.old}" alt="${o.label} old"></div>
    <div class="col"><div class="tag">新 · G10 构图程序（完整内容页）</div><img src="png/${newPng}" alt="${o.label} new"></div>
  </div>
</div>`;
}).join('\n');
const compare = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>Phase6 批次1 · 新旧 A/B</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{background:#14161c;color:#dfe4ec;font-family:"PingFang SC","Microsoft YaHei",sans-serif;padding:36px 20px}
h1{font-size:22px;text-align:center;font-weight:600}.sub{color:#8b93a3;text-align:center;font-size:13px;margin:8px 0 30px;line-height:1.7}
.grp{max-width:1500px;margin:0 auto 44px}.gtitle{font-size:15px;font-weight:600;margin-bottom:10px;letter-spacing:.04em}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}.col{background:#1c1f27;border-radius:10px;padding:12px}
.tag{font-size:12px;color:#9aa3b4;margin-bottom:8px;letter-spacing:.08em}
.col img{width:100%;height:auto;border-radius:6px;display:block}
</style></head><body>
<h1>Phase 6 · 批次 1 · 同一份完整内容 × G10 构图程序（新旧 A/B）</h1>
<div class="sub">左 = 旧 Gallery 展示图（4 主题共享同一版式骨架，只换皮）· 右 = 本批按 signature_operator 重编译的<strong>完整内容页</strong>（与旧图同字段逐字一致，不删减任何文字）。<br>完整 45 页见 sampler.html / png/。</div>
<div class="grp">
  <div class="gtitle">F1 浮光玻璃 · 构图方向择优（同一份完整内容，两个骨架方向并排）</div>
  <div class="cols">
    <div class="col"><div class="tag">A · 对角深度栈（左上远→右下近）</div><img src="png/f1-full.png" alt="F1 A"></div>
    <div class="col"><div class="tag">B · 中心聚焦（单块主玻璃居中）</div><img src="png/f1-full-b.png" alt="F1 B"></div>
  </div>
  <div style="font-size:12px;color:#9aa3b4;margin-top:10px;line-height:1.7">量化：A 质心偏移(-28,-34) / 留白 65.4% · B 偏移(-53,-9) / 留白 65.7%。指纹类间可分 B 更优（vs E7 0.40、vs G2 0.41；A 为 0.47、0.53）。<b style="color:#cfd6e2">推荐 B</b>（更克制、更 SOTA 玻璃风、且与 E7/G2 更可分）。</div>
</div>
${groups}
</body></html>`;
fs.writeFileSync(path.join(DIR, 'compare.html'), compare, 'utf8');

/* ---- blind-test.html（灰度 240×135 缩略，遮主题名） ---- */
const answer = OLD.map(o => ({ id: o.id, label: o.label }));
const cells = blindMeta.map((m, i) => {
  const idx = String(i + 1).padStart(2, '0');
  const themeId = m.id.split('-')[0];
  const role = m.id.split('-').slice(1).join('-');
  const ans = answer.find(a => a.id === themeId);
  return `<div class="cell"><img src="blind/${m.thumb}" alt="T${idx}"><div class="no">T${idx}</div><div class="ans">${ans ? ans.label : ''} · ${role}</div></div>`;
}).join('\n');
const blind = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>Phase6 批次1 · 盲测页</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{background:#14161c;color:#dfe4ec;font-family:"PingFang SC","Microsoft YaHei",sans-serif;padding:36px 20px}
h1{font-size:20px;text-align:center;font-weight:600}.sub{color:#8b93a3;text-align:center;font-size:13px;margin:8px 0 10px;line-height:1.7}
.note{color:#7d8699;text-align:center;font-size:12px;margin-bottom:26px}
.grid{display:grid;grid-template-columns:repeat(8,1fr);gap:10px;max-width:1500px;margin:0 auto}
.cell{position:relative}.cell img{width:100%;height:auto;border-radius:4px;display:block;filter:grayscale(1)}
.no{position:absolute;left:4px;top:4px;background:rgba(0,0,0,.6);color:#fff;font-size:10px;padding:1px 5px;border-radius:3px}
.ans{font-size:11px;color:#9aa3b4;margin-top:3px;text-align:center}
.legend{margin:30px auto 0;max-width:1500px;font-size:12px;color:#8b93a3;line-height:1.9}
.legend b{color:#cfd6e2}
</style></head><body>
<h1>盲测 · 灰度 + 240×135 缩略 + 遮主题名</h1>
<div class="sub">40 页（4 主题 × 10 页）全部去色缩略。先只看图不看下方答案，看能否把每页归回它的主题。</div>
<div class="note">（答案在每格下方与底部对照，验收时建议先遮住再判）</div>
<div class="grid">${cells}</div>
<div class="legend"><b>答案对照：</b>
  ${answer.map((a, i) => `<span style="margin-right:18px">T${String(i + 1).padStart(2, '0')} 起为 ${a.label}（6 页型 + 4 压力）</span>`).join('')}<br>
  判读目标：遮名 + 去色后，能否仅凭结构（积木阶梯 / 正文行栏+索引脊 / 三层套印 / 玻璃深度栈）把页归回主题世界。</div>
</body></html>`;
fs.writeFileSync(path.join(DIR, 'blind-test.html'), blind, 'utf8');

console.log('compare.html', compare.length, 'bytes; blind-test.html', blind.length, 'bytes; old copied', OLD.length);
