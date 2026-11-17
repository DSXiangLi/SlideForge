/* phase6-batch3 / compare.js — 生成 compare.html
 * 4 套主题 × 4 页型 = 16 页，灰度去色并排展示做盲测
 */
const fs = require('fs');
const path = require('path');
const DIR = __dirname;

const IDS = ['g4', 'g5', 'e2', 'e3'];
const LABEL = { g4: 'G4 靛墨黄页', g5: 'G5 三色旬刊', e2: 'E2 蓝图', e3: 'E3 装饰艺术' };
const ROLES = ['cover', 'claim', 'analysis', 'data'];

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Phase6 Batch3 · A/B 灰度盲测</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:#0e1014;font-family:"PingFang SC","Noto Sans SC",sans-serif;color:#e8ebf0}
.wrap{padding:30px 0 80px}
.hd{text-align:center;margin-bottom:8px;font-size:22px;font-weight:600}
.sub{color:#8b93a3;text-align:center;margin-bottom:28px;font-size:13px;line-height:1.7}
.group{margin:0 auto 40px;max-width:1920px}
.group-hd{color:#dbe0ea;font-size:16px;font-weight:600;margin-bottom:12px;padding-left:4px}
.row{display:flex;gap:12px;justify-content:center}
.cell{flex:none}
.cell-lbl{color:#9aa3b4;font-size:12px;letter-spacing:.06em;margin-bottom:6px;text-align:center}
.img-wrap{width:480px;height:270px;overflow:hidden;border:1px solid #2a2e36}
.img-wrap img{width:1920px;height:1080px;transform:scale(.25);transform-origin:top left;filter:grayscale(100%) contrast(1.1)}
</style>
</head>
<body>
<div class="wrap">
  <div class="hd">Phase 6 · 批次 3 · 灰度盲测</div>
  <div class="sub">4 套主题 × 4 页型 = 16 页，去色灰度 + 缩略图并排。<br>遮住主题名后，能否从灰度结构辨认出每套主题的 signature_operator？</div>
${ROLES.map(role => `
  <div class="group">
    <div class="group-hd">页型：${role}</div>
    <div class="row">
${IDS.map(id => `      <div class="cell">
        <div class="cell-lbl">${LABEL[id]}</div>
        <div class="img-wrap"><img src="png/${id}-${role}.png" alt="${id}-${role}"></div>
      </div>`).join('\n')}
    </div>
  </div>`).join('')}
</div>
</body>
</html>`;

fs.writeFileSync(path.join(DIR, 'compare.html'), html, 'utf8');
console.log('written compare.html', Buffer.byteLength(html), 'bytes');
