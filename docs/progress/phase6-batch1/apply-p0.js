/* phase6-batch1 / apply-p0.js
 * P0：以最终渲染为准，回写 E6/F1/E7 的 G10 composition_program（signature_operator / silhouette /
 * info_grammar / invariants / type_scale），同步 DOM 结构测试签署文案。
 * 只替换 ```yaml ... ``` 块；G2 的契约与渲染基本一致，仅 --t-body 已由 P1 更新，这里不动。
 */
const fs = require('fs');
const path = require('path');
const ROOT = 'C:/Users/lixiang/Desktop/SlideForge';
const DIR = path.join(ROOT, 'docs/progress/phase6-batch1');

const YAML = {
  e6: `doctrine: 反叛的秩序；信息不是被摆进格子，而是被一串有重量的积木沿路径推着走。
signature_operator: 把每条信息编译成一块 2px 彩色描边的白底积木，用一条之字折线把它们串成单向路径：
  积木沿路径吸附、填充按 palette 固定顺序轮转（彩色只作描边/编号/彩纸屑点缀，不作承载正文的面）；
  标题独占一块大积木（唯一 accent 焦点 + 硬偏移影），正文两块等大等 y 并排；
  三项数字重排为三块等宽等 y 横排，主数字带「行业前列」accent 标签。
silhouette: 左缘 140 / 右缘 1800 的统一网格；圆角矩形白底积木 + 彩色描边；重心左上；之字线为背景路径。
info_grammar:
  cover:    单块超大积木吞掉标题 + 之字线自页面左下引入
  toc:      3–5 块等大积木沿路径前段吸附，palette 轮转编号
  claim:    论点句独占焦点积木（唯一 accent + 硬偏移影），说明位于路径第二块
  analysis: 3–5 块白底彩色描边积木沿路径阶梯，palette 按固定顺序轮转
  data:     三项数字 → 三块等宽等 y 横排，主数字带 accent 标签
  closing:  焦点积木回到起点方向，之字线收束，彩纸屑一次强形态
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 132px  # 极粗 800 承载积木压强；与正文 5.5:1
  --t-body:    24px  # 正文段落（长段落可读）；图注/说明走 caption 18、注脚走 meta 15
  rule: 标题:正文 ≥1.8:1；正文层 opacity = 1，禁灰化弱读
  floor_note: heading/subhead/caption/meta 不覆盖，继承骨架 64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 左缘 140 / 右缘 1800 的统一网格，积木块心对齐网格
  - 积木描边 2px，palette 色轮转；硬偏移影单页 ≤1、偏移 8px 零模糊
  - accent 焦点单页 ≤1（accent 面积 3–10%）
  - 横排等权三格容器数 = 0
  - 彩纸屑在 DOM 上是积木的兄弟节点，不进任一积木内部
forbidden_defaults: [横向等权三格 KPI, 卡片墙成阵, 居中 hero, hairline 分区, 无路径撒布式彩纸屑, 玻璃拟态, 弥散软影]
dna_events: {cover: 强, claim: 强, analysis: 中, data: 强, toc: 中, closing: 强}`,

  f1: `doctrine: 层级不是靠线划出来的，是靠「离光源多远」量出来的。
signature_operator: 把内容编译成左对齐的玻璃深度栈——三层玻璃左缘对齐、宽度单调递减
  （近景最宽在底、远景最窄在顶），每层有固定 z 深度与模糊/透明度档；
  近景承载标题（accent 蓝，唯一焦点）与结论数字，中景承载说明，远景承载正文与理念；
  三项数字为沿深度档后退的玻璃 chip，非横排三格。
silhouette: 左对齐 + 宽度递减的垂直堆叠（1560→1240→920）；深度靠模糊档体现；重心左下；左上长留白。
info_grammar:
  cover:    单块近景玻璃吞掉标题 + 满幅光斑（封面特权）
  toc:      3–4 层按章节优先级，宽度递减，层号即深度档
  claim:    近景主张句 + 中景一行说明，沿深度档错位
  analysis: 3 层按信息优先级，左对齐宽度递减，不同 z 档
  data:     三项数字 → 三枚沿深度档后退的 chip，末枚为焦点
  closing:  深度栈收束回近景单层，光斑半亮呼应
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 108px  # 轻倒挂细字，靠深度而非字高压层级；与正文 4.5:1
  --t-body:    24px  # 正文段落（长段落可读）；图注/说明走 caption 18、注脚走 meta 15
  rule: 标题:正文 ≥1.8:1；文字层 opacity = 1，禁灰化弱读；环境光斑不计入 accent 面积但禁压正文主列
  floor_note: heading/subhead/caption/meta 不覆盖，继承骨架 64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 玻璃层数 3–4，各层 z / 不透明度档互不相同
  - 三层左缘 x 相同，宽度单调递减
  - 无祖先-后代 backdrop-filter 嵌套（玻璃不叠玻璃）
  - 光斑层为文本层的兄弟节点，不进入任何文本节点的祖先链
  - 横排等权三格容器数 = 0
forbidden_defaults: [玻璃卡成阵同gap同padding, 横向等权三格 KPI, 卡片墙, 居中 hero, 实心色块卡, 硬偏移影, 光斑压正文主列]
dna_events: {cover: 强, claim: 中, analysis: 中, data: 强, toc: 弱, closing: 中}`,

  e7: `doctrine: 一幅画是分版落印出来的；信息的先后就是版次的先后。
signature_operator: 把整页当作一张套色版画——横贯全宽的云霞/浪花带把画幅切成 2–3 个版次层，
  每层是一次独立落印的平涂色面；标题独占首版色面（信息容器，不是角标），
  说明与数字按版次逐层下移，每层左缘递增一个固定套印版差；
  三项数字作为版次标号压在每层右缘的墨线框内（不并列成格），姓名印落在末版右端收束。
silhouette: 水平 2–3 层套印带 + 逐层左缘递增错位；水平主结构；重心左下；右上长留白。
info_grammar:
  cover:    首版满幅平涂 + 题字 + 一枚姓名印；一条浪花带定下缘（单层强形态）
  toc:      三层短版各容一组章节名，版次标号 一/二/三（弱形态）
  claim:    首版题字 + 次版论点（两层），一条云霞横带
  analysis: 三层各容一类信息（题/论/证），层间云霞横带分隔
  data:     三项数字 → 三层右缘的版次标号框，非横排格
  closing:  单版收束 + 姓名印回押，与封面闭环
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display:  96px  # 版画题字恒重，不做压强巨字；与正文 4:1
  --t-body:     24px  # 正文段落（长段落可读）；图注/说明走 caption 18、注脚走 meta 15
  rule: 标题:正文 ≥1.8:1；正文层 opacity = 1，禁灰化弱读；accent 面积 ≤5%、满屏 accent 禁止（G1 立场）
  floor_note: heading/subhead/caption/meta 不覆盖，继承骨架 64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 横贯全宽的云霞/浪花带 ≥1 条，画幅被切成 2–3 层
  - 多层时各层左缘 x 严格递增且步长一致（48px ±2）
  - 主标题位于首层平涂色面内（信息容器）
  - 姓名印单页 1 枚且位于末版右端
  - 横排等权三格容器数 = 0
forbidden_defaults: [竖排题跋分列, 上下金轴与卷轴, 横向等权三格 KPI, 卡片墙, 网格矩阵密集排布, 同形重影叠印, 玻璃拟态, 渐变柔光]
dna_events: {cover: 强, claim: 中, analysis: 强, data: 中, toc: 弱, closing: 强}`
};

const FILES = { e6: 'color/e6/theme.md', f1: 'light/f1/theme.md', e7: 'texture/e7/theme.md' };
const log = [];
for (const [id, rel] of Object.entries(FILES)) {
  const f = path.join(ROOT, 'skills/SlideForge/references/themes', rel);
  let t = fs.readFileSync(f, 'utf8');
  const crlf = t.includes('\r\n');
  if (crlf) t = t.replace(/\r\n/g, '\n');
  // 定位 G10 的 yaml 块
  const start = t.indexOf('**G10 composition_program**');
  const end = t.indexOf('**Variants 配色变体**');
  if (start < 0 || end < 0) throw new Error(id + ': 未找到 G10/Variants 锚点');
  const seg = t.slice(start, end);
  const fence = seg.indexOf('```yaml');
  const fenceEnd = seg.indexOf('```', fence + 3);
  if (fence < 0 || fenceEnd < 0) throw new Error(id + ': 未找到 yaml 围栏');
  const newSeg = seg.slice(0, fence + 8) + '\n' + YAML[id] + '\n' + seg.slice(fenceEnd);
  t = t.slice(0, start) + newSeg + t.slice(end);
  fs.writeFileSync(f, crlf ? t.replace(/\n/g, '\r\n') : t, 'utf8');
  log.push(id.toUpperCase() + ': G10 yaml 已回写');
}
fs.writeFileSync(path.join(DIR, 'apply-p0.log'), log.join('\n'));
console.log(log.join('\n'));
