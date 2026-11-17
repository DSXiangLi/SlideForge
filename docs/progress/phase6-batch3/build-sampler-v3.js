/* phase6-batch3 / build-sampler-v3.js
 * 从 gallery/index.html 精确提取 4 主题 cover slide HTML + 完整骨架框架 CSS
 * 只做截图 CSS 修复（--slide-scale:1 + content-visibility:visible + transform:none + reveal 终态）
 * 内容与 README gallery 一致（"想象的形状" / "同一段内容，二十九个世界"）
 * 布局效果与 gallery 完全一致——不重写任何布局
 */
const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const galleryPath = path.resolve(DIR, '../../..', 'skills/SlideForge/gallery/index.html');
const galleryHTML = fs.readFileSync(galleryPath, 'utf8');

// ===== 1. 提取 gallery <style>...</style> 完整块 =====
const styleStart = galleryHTML.indexOf('<style>');
const styleEnd = galleryHTML.indexOf('</style>');
const galleryStyleBlock = galleryHTML.substring(styleStart, styleEnd + 8);

// ===== 2. 提取 4 主题 cover slide HTML =====
function extractSlide(html, slideId) {
  const marker = `data-slide-id="theme-${slideId}"`;
  const markerPos = html.indexOf(marker);
  if (markerPos === -1) throw new Error(`Slide ${slideId} not found`);

  const slotStart = html.lastIndexOf('<div class="slide-slot">', markerPos);
  const sectionEnd = html.indexOf('</section>', markerPos);
  const slotEnd = html.indexOf('</div>', sectionEnd) + 6;

  return html.substring(slotStart, slotEnd);
}

const slideE2 = extractSlide(galleryHTML, 'e2');
const slideE3 = extractSlide(galleryHTML, 'e3');
const slideG4 = extractSlide(galleryHTML, 'g4');
const slideG5 = extractSlide(galleryHTML, 'g5');

// ===== 3. 组装 HTML =====
const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1920">
<title>Theme Sampler v3 · E2 / E3 / G4 / G5（gallery cover 原样提取）</title>
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
${slideG5}
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
console.log('  G5 slide: ' + slideG5.length + ' chars');

// 验证 G5 色值是正确的赭石/苔绿/暗夜蓝
const g5HasCorrect = slideG5.includes('#E4C9A8') && slideG5.includes('#8BAE6F') && slideG5.includes('#1A2B3D');
const g5HasOld = slideG5.includes('#F2B6C6') || slideG5.includes('#F2D86A') || slideG5.includes('#7A1F35');
console.log('  G5 color check: ' + (g5HasCorrect && !g5HasOld ? 'PASS - correct colors (赭石/苔绿/暗夜蓝)' : 'FAIL'));
console.log('  G5 label check: ' + (slideG5.includes('赭石') ? 'PASS - 赭石' : 'FAIL - still has 胭脂'));
