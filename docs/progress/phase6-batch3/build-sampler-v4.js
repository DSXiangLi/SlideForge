/* phase6-batch3 / build-sampler-v4.js
 * 从原版 sampler (commit 41a3147) 精确提取 4 主题 claim 页 HTML
 * + gallery 骨架框架 CSS（含 G9 装饰母题完整定义）
 * + G5 色值修正（胭脂/黄油/酒红 → 赭石/苔绿/暗夜蓝）
 * + 截图 CSS 修复
 * 内容：山禾集业务汇报（与 assets/theme-sampler/ 截图一致）
 * 布局：原版 sampler 的 claim 页布局（G4 不对称出血 / G5 三色反转 / E2 图框阵列 / E3 中轴金线）
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const DIR = __dirname;

// ===== 1. 提取原版 sampler HTML =====
const originalHTML = execSync('git show 41a3147:tests/decks/theme-sampler/index.html', {
  cwd: path.resolve(DIR, '../..'),
  encoding: 'utf8',
  maxBuffer: 20 * 1024 * 1024
});

// ===== 2. 提取 gallery 的 <style> 块（含完整骨架框架 CSS + G9 装饰母题） =====
const galleryPath = path.resolve(DIR, '../../..', 'skills/SlideForge/gallery/index.html');
const galleryHTML = fs.readFileSync(galleryPath, 'utf8');
const gStyleStart = galleryHTML.indexOf('<style>');
const gStyleEnd = galleryHTML.indexOf('</style>');
const galleryStyleBlock = galleryHTML.substring(gStyleStart, gStyleEnd + 8);

// ===== 3. 从原版 sampler 提取 4 主题 slide HTML =====
function extractSlide(html, slideId) {
  const marker = `data-slide-id="theme-${slideId}"`;
  const markerPos = html.indexOf(marker);
  if (markerPos === -1) throw new Error(`Slide ${slideId} not found`);

  const slotStart = html.lastIndexOf('<div class="slide-slot">', markerPos);
  const sectionEnd = html.indexOf('</section>', markerPos);
  const slotEnd = html.indexOf('</div>', sectionEnd) + 6;

  return html.substring(slotStart, slotEnd);
}

const slideE2 = extractSlide(originalHTML, 'e2');
const slideE3 = extractSlide(originalHTML, 'e3');
const slideG4 = extractSlide(originalHTML, 'g4');
const slideG5 = extractSlide(originalHTML, 'g5');

// ===== 4. G5 色值外科手术 =====
// 原版 G5: --paper:#F2B6C6;--paper-tint:#F2D86A;--ink:#7A1F35;--ink-tint:#5E1828;--accent:#F2D86A;--accent-on:#7A1F35
// 正确色值: --paper:#E4C9A8;--paper-tint:#8BAE6F;--ink:#1A2B3D;--ink-tint:#121E2D;--accent:#8BAE6F;--accent-on:#1A2B3D
const slideG5Fixed = slideG5
  .replace('#F2B6C6', '#E4C9A8')  // paper: 胭脂粉 → 赭石
  .replace(/#F2D86A/g, '#8BAE6F')  // paper-tint & accent: 黄油 → 苔绿
  .replace(/#7A1F35/g, '#1A2B3D')  // ink & accent-on: 酒红 → 暗夜蓝
  .replace('#5E1828', '#121E2D')  // ink-tint: 深酒红 → 深暗夜蓝
  .replace('G5 · 三色旬刊 · 胭脂', 'G5 · 三色旬刊 · 赭石');

// 验证替换
const oldColors = ['#F2B6C6', '#F2D86A', '#7A1F35', '#5E1828'];
const remaining = oldColors.filter(c => slideG5Fixed.includes(c));
if (remaining.length > 0) {
  console.error('ERROR: G5 still has old colors:', remaining);
  process.exit(1);
}

// ===== 5. 组装 HTML =====
const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1920">
<title>Theme Sampler v4 · E2 / E3 / G4 / G5（原版 claim 布局 + G5 色值修正）</title>
${galleryStyleBlock}

/* ===== 截图修复：强制 1:1 渲染，不缩放 ===== */
:root{--slide-scale:1}
html,body{background:#222;height:auto}
.deck{
  display:flex!important;
  flex-direction:column!important;
  align-items:center!important;
  height:auto!important;
  overflow:visible!important;
  padding:24px 0;
  scroll-snap-type:none!important;
}
.slide-slot{
  width:1920px!important;
  height:1080px!important;
  margin:12px 0!important;
  position:relative;
  overflow:visible!important;
  content-visibility:visible!important;
  scroll-snap-align:none!important;
}
.slide{
  width:1920px!important;
  height:1080px!important;
  transform:none!important;
  overflow:hidden;
}
/* 动效终态——截静态图 */
.reveal{opacity:1!important;transform:none!important}
[data-anim="wipe-clip"]{clip-path:inset(0 0 0 0)!important}
[data-anim="mask-lines"] .ml-inner{transform:none!important}
[data-anim="blur-in"]{filter:none!important}
[data-anim="flicker-in"]{opacity:1!important;animation:none!important}
[data-anim="ring"]{stroke-dashoffset:calc(100 - var(--val,0))!important}
[data-anim="gradient-flow"]{animation:none!important}
[data-anim="typewriter"].tw-live::after{animation:none!important}
.split-anim .sp-unit{opacity:1!important;transform:none!important}
.amb-pulse,.amb-drift,.amb-glow{animation:none!important}
</style>
</head>
<body>
<div class="deck" id="deck">
${slideE2}
${slideE3}
${slideG4}
${slideG5Fixed}
</div>
<script>(function(){
  document.documentElement.classList.add("js");
  document.querySelectorAll(".slide").forEach(function(s){
    s.classList.add("in-view");
  });
})();</script>
</body>
</html>`;

fs.writeFileSync(path.join(DIR, 'theme-sampler-4.html'), html);
console.log('Generated theme-sampler-4.html (' + html.length + ' chars)');
console.log('  E2 slide: ' + slideE2.length + ' chars');
console.log('  E3 slide: ' + slideE3.length + ' chars');
console.log('  G4 slide: ' + slideG4.length + ' chars');
console.log('  G5 slide (fixed): ' + slideG5Fixed.length + ' chars');
console.log('  G5 color check: PASS (all old colors replaced)');
console.log('  Content: 山禾集业务汇报 (claim page)');
