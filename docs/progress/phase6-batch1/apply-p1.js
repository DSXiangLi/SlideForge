/* phase6-batch1 / apply-p1.js  (幂等版)
 * P1：--t-body 35px → 24px（正文段落档）。只改本批 4 套。
 */
const fs = require('fs');
const path = require('path');
const ROOT = 'C:/Users/lixiang/Desktop/SlideForge';
const FILES = { e6: 'color/e6/theme.md', g2: 'color/g2/theme.md', e7: 'texture/e7/theme.md', f1: 'light/f1/theme.md' };
const log = [];
for (const [id, rel] of Object.entries(FILES)) {
  const f = path.join(ROOT, 'skills/SlideForge/references/themes', rel);
  let t = fs.readFileSync(f, 'utf8');
  const crlf = t.includes('\r\n');
  if (crlf) t = t.replace(/\r\n/g, '\n');
  const before = (t.match(/--t-body:35px/g) || []).length + (t.match(/--t-body:\s+35px/g) || []).length;
  if (before === 0) { log.push(id.toUpperCase() + ': 已改过，跳过'); continue; }
  // :root 无空格
  t = t.replace(/--t-body:35px/g, '--t-body:24px');
  // type_scale 有空格（保留空格，更新过时注释）
  t = t.replace(/--t-body:(\s+)35px(\s*#\s*[^\n]*)?/g, (m, sp) => '--t-body:' + sp + '24px  # 正文段落（长段落可读）；图注/说明走 caption 18、注脚走 meta 15');
  fs.writeFileSync(f, crlf ? t.replace(/\n/g, '\r\n') : t, 'utf8');
  log.push(id.toUpperCase() + ': --t-body 35px → 24px（' + before + ' 处）');
}
fs.writeFileSync(path.join(ROOT, 'docs/progress/phase6-batch1/apply-p1.log'), log.join('\n'));
console.log(log.join('\n'));
