/* phase6-batch1 / apply-g10-rewrite.js
 * 以渲染为准回写 E7 / F1 的 G10 signature_operator / silhouette / invariants / DOM 测试，
 * 反映「明度签名」重构：E7 深墨前景面（浅纸深块）、F1 暗色玻璃中心聚焦（深底亮块）。
 * 幂等：命中即替换，未命中报错。
 */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../../..');
const log = [];

function patch(rel, pairs) {
  const f = path.join(ROOT, rel);
  let txt = fs.readFileSync(f, 'utf8');
  for (const [old, neu, tag] of pairs) {
    if (!txt.includes(old)) { log.push('MISS: ' + rel + ' :: ' + tag); continue; }
    txt = txt.replace(old, neu);
    log.push('OK: ' + rel + ' :: ' + tag);
  }
  fs.writeFileSync(f, txt, 'utf8');
}

// ---------- E7 ----------
patch('skills/SlideForge/references/themes/texture/e7/theme.md', [
  [
    `signature_operator: 把整页当作一张套色版画——横贯全宽的云霞/浪花带把画幅切成 2–3 个版次层，
  每层是一次独立落印的平涂色面；标题独占首版色面（信息容器，不是角标），
  说明与数字按版次逐层下移，每层左缘递增一个固定套印版差；
  三项数字作为版次标号压在每层右缘的墨线框内（不并列成格），姓名印落在末版右端收束。`,
    `signature_operator: 把整页当作一张套色版画——三层版次沿对角线纵深排布：远景(左上,轻,浅纸) → 中景(中,纸色) → 前景(右下,重,深墨面)；
  前景大版用深墨底 + 纸色字（木刻墨版），标题独占前景版；
  说明与数字沿对角逐层下沉，每层版次标号框落在层缘；姓名印落右上留白处收束。`,
    'E7 signature_operator'
  ],
  [
    `silhouette: 水平 2–3 层套印带 + 逐层左缘递增错位；水平主结构；重心左下；右上长留白。`,
    `silhouette: 对角线三层纵深（左上轻→右下重）；前景深墨面 vs 远景浅纸（明度签名 = 浅纸深块）；重心右下；上 1/3 留白做天空；右上姓名印。`,
    'E7 silhouette'
  ],
  [
    `invariants:
  - 横贯全宽的云霞/浪花带 ≥1 条，画幅被切成 2–3 层
  - 多层时各层左缘 x 严格递增且步长一致（48px ±2）
  - 主标题位于首层平涂色面内（信息容器）
  - 姓名印单页 1 枚且位于末版右端
  - 横排等权三格容器数 = 0`,
    `invariants:
  - 三层版次沿对角线排布（左上轻→右下重），前景版为深墨面（background: var(--ink)）
  - 前景版文字用纸色（color: var(--paper)），远景/中景为浅纸面
  - 主标题位于前景深墨版内
  - 姓名印单页 1 枚且位于右上留白处
  - 横排等权三格容器数 = 0`,
    'E7 invariants'
  ],
  [
    `- **DOM 结构测试签署**：删掉 signature_operator，两条横带、三个平涂版次层、逐层 48px 错位、三个版次标号框与末版印章位置全部消失，页面退回「标题 + 两段正文 + 横排三格」；元素数量/分组/顺序/位置**都变** → **PASS**。`,
    `- **DOM 结构测试签署**：删掉 signature_operator，对角线三层版次、深墨前景面、版次标号框与右上印章位置全部消失，页面退回「标题 + 两段正文 + 横排三格」；元素数量/分组/顺序/位置**都变** → **PASS**。`,
    'E7 DOM 测试'
  ],
]);

// ---------- F1 ----------
patch('skills/SlideForge/references/themes/light/f1/theme.md', [
  [
    `- **气质**：晨雾冷白 + 蓝紫环境光斑 + 悬浮玻璃卡——光是背景，玻璃是容器，层级靠透明`,
    `- **气质**：暗色玻璃（深底）+ 蓝紫环境光斑 + 悬浮亮玻璃卡——光是背景，玻璃是容器，层级靠透明（明度签名 = 深底亮块）`,
    'F1 气质'
  ],
  [
    `signature_operator: 把内容编译成左对齐的玻璃深度栈——三层玻璃左缘对齐、宽度单调递减
  （近景最宽在底、远景最窄在顶），每层有固定 z 深度与模糊/透明度档；
  近景承载标题（accent 蓝，唯一焦点）与结论数字，中景承载说明，远景承载正文与理念；
  三项数字为沿深度档后退的玻璃 chip，非横排三格。`,
    `signature_operator: 把内容编译成居中的单块主玻璃（中心聚焦）——整页深底 + 一块白色半透明主玻璃水平居中，
  四周大留白 + 对角柔光斑；近景承载标题（accent 蓝，唯一焦点）与结论数字，
  说明与正文在主玻璃内纵向排布；toc/data 用玻璃 chip 居中，analysis 用上下两块玻璃。
  三项数字为居中的玻璃 chip，非横排三格。`,
    'F1 signature_operator'
  ],
  [
    `silhouette: 左对齐 + 宽度递减的垂直堆叠（1560→1240→920）；深度靠模糊档体现；重心左下；左上长留白。`,
    `silhouette: 中心聚焦单玻璃（水平居中）+ 深底亮玻璃；明度签名 = 深底亮块（与 E7 浅纸深块相反）；重心居中；四周大留白。`,
    'F1 silhouette'
  ],
  [
    `invariants:
  - 玻璃层数 3–4，各层 z / 不透明度档互不相同
  - 三层左缘 x 相同，宽度单调递减
  - 无祖先-后代 backdrop-filter 嵌套（玻璃不叠玻璃）
  - 光斑层为文本层的兄弟节点，不进入任何文本节点的祖先链
  - 横排等权三格容器数 = 0`,
    `invariants:
  - 主玻璃水平居中（x 中心 ≈ 960），四周大留白
  - 玻璃为白色半透明（accent-on），页底为深色（明度签名 = 深底亮块）
  - 无祖先-后代 backdrop-filter 嵌套（玻璃不叠玻璃）
  - 光斑层为文本层的兄弟节点，不进入任何文本节点的祖先链
  - 横排等权三格容器数 = 0`,
    'F1 invariants'
  ],
  [
    `- **DOM 结构测试签署**：删掉 signature_operator，深度轴、3–4 层 z 档差异、逐级错位与三枚后退 chip 全部消失，页面退回同 gap 同 padding 的玻璃卡阵；元素数量/分组/顺序/位置**都变** → **PASS**。`,
    `- **DOM 结构测试签署**：删掉 signature_operator，居中主玻璃、深底亮玻璃、对角柔光斑与居中 chip 全部消失，页面退回同 gap 同 padding 的玻璃卡阵；元素数量/分组/顺序/位置**都变** → **PASS**。`,
    'F1 DOM 测试'
  ],
]);

fs.writeFileSync(path.join(__dirname, 'apply-g10-rewrite.log'), log.join('\n'), 'utf8');
console.log(log.join('\n'));
