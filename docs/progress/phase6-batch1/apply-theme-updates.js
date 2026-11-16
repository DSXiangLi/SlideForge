/* phase6-batch1 / apply-theme-updates.js
 * 把本批 4 套主题升级到 G10：
 *   1) G9 css 块注入 px@1920 的 --t-* 令牌 + 新增签名结构件类（.mt-* 命名空间全库唯一）
 *   2) 改写与 G10 冲突的旧制度条款（卡片成阵 / 横排等权三格 / 竖排题跋等）
 *   3) 在 Variants 之前插入完整 G10 composition_program（含 DOM 结构测试签署）
 *   4) 顺手把 analysis/ 下的 G10 草案复制进 docs/progress/，规避换机丢失（HANDOVER §6 建议）
 * 每个替换都校验命中，未命中即抛错；已含 composition_program 则跳过，保证幂等。
 */
const fs = require('fs');
const path = require('path');
const ROOT = 'C:/Users/lixiang/Desktop/SlideForge';
const T = (p) => path.join(ROOT, 'skills/SlideForge/references/themes', p);
const DIR = path.join(ROOT, 'docs/progress/phase6-batch1');
const log = [];

/* ---------------- 1. G9 CSS 新增与 :root 令牌 ---------------- */
const CSS = {
  e6: {
    root: ':root{--ease-out:cubic-bezier(.5,1.7,.4,1);--t-display:132px;--t-body:35px}',
    replaceRoot: ':root{--ease-out:cubic-bezier(.5,1.7,.4,1)}',
    add: [
      '.mt-mem-path{position:absolute;inset:0;pointer-events:none;user-select:none}',
      '.mt-mem-path::before{content:"";position:absolute;left:2%;top:78%;width:96%;height:12px;background-image:linear-gradient(135deg,var(--ink) 25%,transparent 25%),linear-gradient(225deg,var(--ink) 25%,transparent 25%);background-size:24px 12px;transform:rotate(-12deg);opacity:.55}',
      '.mt-mem-block{position:absolute;border:3px solid var(--ink);border-radius:14px;background:var(--paper);padding:20px 26px}',
      '.mt-mem-block--focus{box-shadow:8px 8px 0 color-mix(in srgb,var(--accent) 85%,var(--ink))}',
      '.mt-mem-step{display:inline-block;width:1.6em;height:.32em;background:var(--ink);margin-right:.5em;vertical-align:middle}'
    ].join('\n')
  },
  g2: {
    root: ':root{--t-display:112px;--t-body:35px}',
    add: [
      '.mt-hl-lineno{position:absolute;width:56px;text-align:right;color:color-mix(in srgb,var(--ink) 45%,transparent);font-family:var(--font-mono)}',
      '.mt-hl-lead{position:absolute;height:5px;background:color-mix(in srgb,var(--hl-c,var(--hl-1)) 60%,transparent);pointer-events:none}',
      '.mt-hl-index{position:absolute;border-left:3px solid var(--hl-c,var(--hl-1));padding-left:14px}'
    ].join('\n')
  },
  e7: {
    root: ':root{--t-display:96px;--t-body:35px;--t-vertical:72px}',
    add: [
      '.mt-uki-plate{position:absolute;left:0;right:0;background:var(--paper-tint);border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);padding:18px 28px}',
      '.mt-uki-plate--first{background:color-mix(in srgb,var(--ink-tint) 12%,var(--paper))}',
      '.mt-uki-edition{position:absolute;border:1px solid var(--ink);padding:6px 12px;font-family:var(--font-mono)}',
      '.mt-uki-band{position:absolute;left:0;right:0;height:10px;pointer-events:none}'
    ].join('\n')
  },
  f1: {
    root: ':root{--t-display:108px;--t-body:35px}',
    add: [
      '.mt-gls-depth{position:absolute;border:1px solid color-mix(in srgb,var(--accent-on) 65%,transparent);border-radius:24px;background:linear-gradient(155deg,color-mix(in srgb,var(--paper) 82%,transparent),color-mix(in srgb,var(--paper) 62%,transparent));backdrop-filter:blur(14px) saturate(130%);-webkit-backdrop-filter:blur(14px) saturate(130%);box-shadow:inset 0 1px 0 color-mix(in srgb,var(--accent-on) 70%,transparent),0 16px 40px -12px color-mix(in srgb,var(--ink) 20%,transparent)}',
      '.mt-gls-axis{position:absolute;height:1px;background:color-mix(in srgb,var(--accent) 35%,transparent);transform-origin:left center;pointer-events:none}',
      '.mt-gls-chip-n{display:inline-flex;align-items:center;gap:.5em;padding:.35em 1em;border-radius:999px;border:1px solid color-mix(in srgb,var(--accent-on) 60%,transparent);background:color-mix(in srgb,var(--paper) 70%,transparent)}'
    ].join('\n')
  }
};

/* ---------------- 2. 与 G10 冲突的旧条款（按行前缀整行替换） ---------------- */
// 注意：字符串统一用双引号，允许内含反引号；内部英文双引号用中文引号替代或转义。
const LINES = {
  e6: [
    ['| 5 | 版式 |', '| 5 | 版式 | 之字路径积木——信息沿单向折线逐块吸附，不是居中带也不是横排格 | 积木有路径才有信息引导，散落只有混乱 |'],
    ['- **并列信息**', '- **并列信息**（目录章节、4 种店型、4 个流程步骤）→ 沿之字路径逐块吸附，等大等间距、颜色按 palette 固定顺序轮转，全部统一投影（全有或全无）；**禁横排等权三格**'],
    ['- **有主次信息**', '- **有主次信息**（KPI 有焦点项、漏斗有断点）→ 焦点块**更大** + 8px 硬偏移投影且位于路径末段，辅助块更小 + 无投影；块宽沿路径单调不减'],
    ['- **色面块对齐**', '- **色面块对齐**——块心落在之字路径的折点上，按 45°/135° 转折吸附；不是横排对齐，也不是散落'],
    ['- **禁倾斜/旋转容器**', '- **禁倾斜/旋转容器**——信息要正可读；旋转只给之字路径本身与彩纸屑，不给积木内的文字'],
    ['- **并列信息等大对齐**', '- **并列信息等大对齐**——信息必须沿之字路径编译为积木；**禁横排等权三格 KPI 与卡片墙成阵**（G10 composition_program 优先于本节其余条款）']
  ],
  g2: [
    ['| 5 | 版式 |', '| 5 | 版式 | 左正文行栏 + 右标注索引脊的双坐标——不是居中内容带，也不是便签散布 | 重点是被划出来的，划痕连回原行才成结构 |'],
    ['- **禁居中内容带布局**', '- **禁居中内容带布局**（display:flex;flex-direction:column;justify-content:center）——用正文层/批注层双坐标：左侧带行号等距正文行，右侧标注索引脊，水平荧光引线连回原行'],
    ['- **禁 box-shadow**', '- **禁 box-shadow**——便签卡用 1px 细描边 + 微旋转贴上墙，深度靠层叠不靠投影；**禁便签卡成阵**，KPI 作为页边批注贴在对应笔记行外侧（G10 优先）'],
    ['- **高密度容器边界**', '- **高密度容器边界**：正文行栏（左 2/3，行号 + 铅笔虚线等距行）＋ 标注索引脊（右 1/3）；两栏由荧光引线一一连接，禁便签卡成阵']
  ],
  e7: [
    ['- **亲和**', '- **亲和**：三层套印版次（题/论/证各占一层，层间云霞或浪花横带）、图文证据（画 + 题跋）、巨字宣言（封面题字 + 印章落款，画册封面的仪式感）'],
    ['- **词汇**', '- **词汇**：姓名印（.mt-uki-seal：accent 实色小方块 + 反白篆意字，末版右端落款位，每页至多一方）/ 浪花带（.mt-uki-wave：鳞片浪纹横带）/ 云霞横带（.mt-uki-cloud：断续横带，版次层分界）/ 远景题名列（.mt-uki-inscription：右上留白处竖排小字，每页至多一列，**非主标题、非题跋分列**）/ 版次层（.mt-uki-plate：签名结构件，内部文字保持可编辑）/ 版次标号框（.mt-uki-edition：每层右缘的墨线数字框）/ 横带定位（.mt-uki-band）'],
    ['- **禁忌**：姓名印每页至多一方', '- **禁忌**：姓名印每页至多一方且只在末版右端；浪花带/云霞带合计每页 2 条且横贯全宽、禁进图表区；**禁竖排题跋分列、禁上下金轴与卷轴（H1 氤氲手卷词汇）**；**禁同形重影叠印（E1 孔版印刷词汇）**；.mt-uki-inscription 是文本载体类母题，文本保持可编辑；其余母题件一律 data-editable-skip']
  ],
  f1: [
    ['- **高密度容器边界**', '- **高密度容器边界**：玻璃深度栈 3–4 层，沿 ≈12° 深度轴逐级错位叠压，各层 z 与不透明度档互不相同；**禁并列成阵、禁玻璃叠玻璃（无祖先-后代 backdrop-filter 嵌套）**；文字层 opacity = 1，禁对文字降透明度'],
    ['- **亲和**', '- **亲和**：深度栈分层（近/中/远景玻璃沿斜向轴错位，非网格矩阵）、数据英雄（沿深度轴逐级后退的三枚玻璃 chip）、图文证据（图片垫在远景层，边缘透出光斑）'],
    ['- **禁忌**：玻璃禁叠玻璃', '- **禁忌**：玻璃禁叠玻璃（两层 blur 即糊）；光斑层是文本层的兄弟节点，禁进入任何文本节点的祖先链、禁压正文阅读主列；**禁玻璃卡成阵与横排等权三格**；每页玻璃层 3–4、文字层 opacity = 1；其余母题件一律 data-editable-skip']
  ]
};

/* ---------------- 3. G10 契约（与 brief.md §3 逐字一致） ---------------- */
const G10 = {
  e6: `**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：之字路径与积木是签名结构件，形状由 CSS 承担（data-editable-skip），其内部承载的文字仍是 data-editable 叶子节点。
- **DOM 结构测试签署**：删掉 signature_operator，页面回到「标题 + 两段正文 + 横排三格 KPI」，之字路径、积木分组、阶梯宽度、palette 轮转顺序、数字台阶全部消失，元素数量/分组/顺序/位置**都变** → **PASS**。

\`\`\`yaml
doctrine: 反叛的秩序；信息不是被摆进格子，而是被一串有重量的积木沿路径推着走。
signature_operator: 把每条信息编译成一块 3px 墨线粗描边的积木，用一条之字折线把它们串成单向路径：
  积木沿路径逐块吸附、宽度随信息权重阶梯放大、填充按 palette 固定顺序轮转；
  三项数字重排为沿路径递进的三块台阶，唯一焦点积木带 8px 硬偏移影；之字线是路径本身而非分隔装饰。
silhouette: 之字折线主路径（45°/135° 转折）；圆角矩形积木块面；起点左下、终点右上；重心沿对角带；右下 ≥15% 留白。
info_grammar:
  cover:    单块超大积木吞掉标题 + 之字线自页面左下引入
  toc:      3–5 块等大积木沿路径前段吸附，palette 轮转编号
  claim:    论点句独占焦点积木（最大 + 硬偏移影），说明位于路径第二块
  analysis: 3–5 块积木沿路径阶梯，块宽单调不减，palette 按固定顺序轮转
  data:     三项数字 → 三块逐级放大的台阶积木，末块承载结论短句
  closing:  焦点积木回到起点方向，之字线收束，彩纸屑一次强形态
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 132px  # 极粗 800 承载积木压强；与正文 3.77:1
  --t-body:    35px   # ≈1.8cqw@480 换算基准
  rule: 标题:正文 ≥1.8:1，巨字:正文 ≥3:1；正文层 opacity = 1，禁灰化弱读
  floor_note: heading/subhead/caption/meta 不覆盖，继承骨架 64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 之字路径 1 条，转折角 ∈ {45°,135°}，路径长度 ≥ 60% 画幅对角
  - 积木块宽沿路径单调不减；焦点块面积 ≥ 其余块 1.4×
  - 硬偏移投影单页 ≤1，偏移量 8px 且零模糊
  - 横排等权三格容器数 = 0
  - 彩纸屑在 DOM 上是积木的兄弟节点，不进任一积木内部
forbidden_defaults: [横向等权三格 KPI, 卡片墙成阵, 居中 hero, hairline 分区, 无路径撒布式彩纸屑, 玻璃拟态, 弥散软影]
dna_events: {cover: 强, claim: 强, analysis: 中, data: 强, toc: 中, closing: 强}
\`\`\``,

  g2: `**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：荧光引线从「垫在词下的渐变」升级为连接两个信息层的结构件；引线由 CSS 承担（data-editable-skip），两端文字仍是 data-editable 叶子节点。
- **DOM 结构测试签署**：删掉 signature_operator，右侧整条索引脊、全部水平引线、行号列与页边批注消失，正文退回通栏两段；元素数量/分组/位置**都变** → **PASS**。

\`\`\`yaml
doctrine: 重点不是写出来的，是被划出来的；阅读的痕迹本身就是信息结构。
signature_operator: 把页面拆成笔记正文层与标注索引层两套坐标——正文拆成带行号的等距行、只占左 2/3；
  被标注的关键词从正文抽出，按标注发生顺序在右 1/3 生成一条纵向标注索引脊，
  每个索引项用一根水平荧光引线连回它原来的正文行（引线 y 与行 y 严格对齐）；
  三项数字作为页边批注贴在各自笔记行外侧，不独立成格。
silhouette: 左纵向笔记栏 + 右标注索引脊；水平引线矩阵；重心左；右上 ≥15% 主动留白。
info_grammar:
  cover:    一行手写体巨标 + 一道荧光带；索引脊收束为单个标签
  toc:      3–6 行带行号目录，右侧同数索引项，引线逐行对齐
  claim:    主张句独占正文首行；关键词抽出到索引脊首位
  analysis: 3–6 行带行号正文 + 同数索引项，引线一一对应
  data:     三项数字 → 三条页边批注（贴对应笔记行外侧，顺序 = 正文行序）
  closing:  引线全部收回，索引脊收束为一条荧光带
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 112px  # 圆体亲切，压强让位给「划重点」；与正文 3.20:1
  --t-body:    35px
  rule: 标题:正文 ≥1.8:1；正文层 opacity = 1，禁灰化弱读；荧光色只进标注层，禁做容器面与正文文字色
  floor_note: heading/subhead/caption/meta 不覆盖，继承骨架 64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 行号列存在且相邻行 y 差恒定 ±2px
  - 引线数 = 索引项数 ≥1，且每条引线 y 与对应正文行 y 偏差 ≤2px
  - 正文层位于左 2/3、索引脊位于右 1/3，两栏不交叠
  - 荧光标注 ≤4 处且同页 ≤2 色（G1 多色立场）
  - 横排等权三格容器数 = 0
forbidden_defaults: [横向等权三格 KPI, 便签卡成阵, 居中内容带, solid hairline, 整段高亮, 荧光色做容器面, 投影]
dna_events: {cover: 中, claim: 强, analysis: 强, data: 中, toc: 弱, closing: 中}
\`\`\``,

  e7: `**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **与 H1 的界限**：H1 是垂直主轴 + 自右向左展开 + 竖排主标题 + 题跋分列；本主题是**水平主轴 + 自上而下分版 + 横排题字 + 逐层左缘错位**，竖排文字每页至多一列且只作远景题名。
- **灵魂承载**：三个版次层是签名结构件，形状由 CSS 承担（data-editable-skip），层内文字仍是 data-editable 叶子节点；姓名印是唯一句读，不是可随处贴的贴纸。
- **DOM 结构测试签署**：删掉 signature_operator，两条横带、三个平涂版次层、逐层 48px 错位、三个版次标号框与末版印章位置全部消失，页面退回「标题 + 两段正文 + 横排三格」；元素数量/分组/顺序/位置**都变** → **PASS**。

\`\`\`yaml
doctrine: 一幅画是分版落印出来的；信息的先后就是版次的先后。
signature_operator: 把整页当作一张套色版画——两条横贯全宽的云霞/浪花带把画幅切成三个版次层，
  每层是一次独立落印的平涂色面；标题独占首版色面（信息容器，不是角标），
  说明与数字按版次逐层下移，每层左缘递增一个固定套印版差；
  三项数字作为版次标号压在每层右缘的墨线框内（不并列成格），姓名印落在末版右端收束。
silhouette: 水平三层套印带 + 逐层左缘递增错位；水平主结构；重心左下；右上长留白只容一行竖排远景题名。
info_grammar:
  cover:    首版满幅平涂 + 题字 + 一枚姓名印；一条浪花带定下缘
  toc:      三层各容一组章节名，版次标号 一/二/三
  claim:    首版题字 + 次版论点，版差 48px
  analysis: 三层各容一类信息（题/论/证），层间云霞横带分隔
  data:     三项数字 → 三层右缘的版次标号框，非横排格
  closing:  末版收束，姓名印回押，与封面闭环
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display:  96px  # 版画题字恒重，不做压强巨字；与正文 2.74:1
  --t-body:     35px
  --t-vertical: 72px  # 仅远景题名，远小于 H1 的 118px，避免竖排主标题撞脸
  rule: 标题:正文 ≥1.8:1；正文层 opacity = 1，禁灰化弱读；accent 面积 ≤5%、满屏 accent 禁止（G1 立场）
  floor_note: heading/subhead/caption/meta 不覆盖，继承骨架 64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 横贯全宽的云霞/浪花带 = 2 条，画幅被切成 3 层
  - 三层左缘 x 严格递增且步长一致（48px ±2）
  - 主标题位于首层平涂色面内（信息容器）
  - 竖排文字节点 ≤1（只许远景题名）
  - 姓名印单页 1 枚且位于末层右端
  - 横排等权三格容器数 = 0
forbidden_defaults: [竖排题跋分列, 上下金轴与卷轴, 横向等权三格 KPI, 卡片墙, 网格矩阵密集排布, 同形重影叠印, 玻璃拟态, 渐变柔光]
dna_events: {cover: 强, claim: 中, analysis: 强, data: 中, toc: 弱, closing: 强}
\`\`\``,

  f1: `**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **灵魂承载**：深度轴与 3–4 层玻璃是签名结构件，形状由 CSS 承担（data-editable-skip），层内文字仍是 data-editable 叶子节点。
- **设计层规避弱读**：文字层 opacity 恒为 1；光斑层是文本层的兄弟节点，永不进入文本节点的祖先链；玻璃不叠玻璃（无祖先-后代 backdrop-filter 嵌套）。
- **DOM 结构测试签署**：删掉 signature_operator，深度轴、3–4 层 z 档差异、逐级错位与三枚后退 chip 全部消失，页面退回同 gap 同 padding 的玻璃卡阵；元素数量/分组/顺序/位置**都变** → **PASS**。

\`\`\`yaml
doctrine: 层级不是靠线划出来的，是靠「离光源多远」量出来的。
signature_operator: 把内容编译成一条由近到远的玻璃深度栈——每类信息是一层玻璃，
  按信息优先级分配离光源的距离（近/中/远景），层数 3–4 且每层有固定 z 深度与不透明度档；
  近景承载标题与结论数字，中景承载说明，远景只容图注；
  层与层不并列，而是沿一条左下到右上的 ≈12° 深度轴逐级错位叠压；
  三项数字重排为沿深度轴逐级后退的三枚玻璃 chip，非横排三格。
silhouette: ≈12° 斜向深度轴 + 3–4 层圆角玻璃面逐级后退；重心由左下推向右上；左上长留白。
info_grammar:
  cover:    单块近景玻璃吞掉标题 + 满幅光斑（封面特权）
  toc:      3–4 层按章节优先级后退，层号即深度档
  claim:    近景主张句 + 中景一行说明，沿轴左右错位
  analysis: 3–4 层按信息优先级排序，同圆角同 gap 但不同 z 档，不并列成阵
  data:     三项数字 → 三枚沿轴逐级后退的 chip，末枚为焦点
  closing:  深度栈收束回近景单层，光斑半亮呼应
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display: 108px  # 轻倒挂细字，靠深度而非字高压层级；与正文 3.09:1
  --t-body:    35px
  rule: 标题:正文 ≥1.8:1；文字层 opacity = 1，禁灰化弱读；环境光斑不计入 accent 面积但禁压正文主列
  floor_note: heading/subhead/caption/meta 不覆盖，继承骨架 64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 玻璃层数 3–4，各层 z / 不透明度档互不相同
  - 相邻层中心沿深度轴位移 ≥120px，主轴 12° ±4°
  - 无祖先-后代 backdrop-filter 嵌套（玻璃不叠玻璃）
  - 光斑层为文本层的兄弟节点，不进入任何文本节点的祖先链
  - 横排等权三格容器数 = 0
forbidden_defaults: [玻璃卡成阵同gap同padding, 横向等权三格 KPI, 卡片墙, 居中 hero, 实心色块卡, 硬偏移影, 光斑压正文主列]
dna_events: {cover: 强, claim: 中, analysis: 中, data: 强, toc: 弱, closing: 中}
\`\`\``
};

/* ---------------- 执行 ---------------- */
const FILES = { e6: 'color/e6/theme.md', g2: 'color/g2/theme.md', e7: 'texture/e7/theme.md', f1: 'light/f1/theme.md' };

function replaceLine(txt, prefix, newLine, tag) {
  const lines = txt.split('\n');
  const hits = [];
  for (let i = 0; i < lines.length; i++) if (lines[i].startsWith(prefix)) hits.push(i);
  if (hits.length !== 1) throw new Error(`${tag}: prefix "${prefix}" 命中 ${hits.length} 次（应为 1）`);
  lines[hits[0]] = newLine;
  log.push(`${tag}: 改写行 ${hits[0] + 1} ← ${prefix}`);
  return lines.join('\n');
}

for (const [id, rel] of Object.entries(FILES)) {
  const f = T(rel);
  let txt = fs.readFileSync(f, 'utf8');
  // theme.md 全库为 CRLF；内部统一按 LF 处理，写回时还原，避免产生整文件换行 diff
  const crlf = txt.includes('\r\n');
  if (crlf) txt = txt.replace(/\r\n/g, '\n');
  if (txt.includes('**G10 composition_program**')) { log.push(`${id.toUpperCase()}: 已含 G10，跳过`); continue; }

  // 3.1 旧条款改写
  for (const [prefix, newLine] of LINES[id]) txt = replaceLine(txt, prefix, newLine, id.toUpperCase());

  // 3.2 G9 css 块：注入 :root 与新增结构件类
  const c = CSS[id];
  const blockRe = /```css\n([\s\S]*?)```/g;
  const blocks = [...txt.matchAll(blockRe)];
  // 取最后一个 css 块（G9 母题块通常是最后一个；用含 .mt- 的块定位）
  const g9 = blocks.filter(m => m[1].includes('.mt-'));
  if (g9.length !== 1) throw new Error(`${id}: G9 css 块定位失败，命中 ${g9.length}`);
  let body = g9[0][1];
  if (c.replaceRoot) {
    if (!body.includes(c.replaceRoot)) throw new Error(`${id}: 未找到原 :root 行`);
    body = body.replace(c.replaceRoot, c.root);
  } else {
    body = c.root + '\n' + body;
  }
  body = body.trimEnd() + '\n' + c.add + '\n';
  txt = txt.replace(g9[0][0], '```css\n' + body + '```');
  log.push(`${id.toUpperCase()}: G9 css 注入 ${c.root} + ${c.add.split('\n').length} 条签名结构件类`);

  // 3.3 插入 G10
  const marker = '**Variants 配色变体**';
  if (!txt.includes(marker)) throw new Error(`${id}: 未找到 Variants 标记`);
  txt = txt.replace(marker, G10[id] + '\n\n---\n\n' + marker);
  log.push(`${id.toUpperCase()}: 插入 G10 composition_program`);

  fs.writeFileSync(f, crlf ? txt.replace(/\n/g, '\r\n') : txt, 'utf8');
}

// 3.4 G10 草案入 progress（HANDOVER §6 换机风险）
const src = path.join(ROOT, 'analysis/G10-主题DNA规范草案.md');
const dst = path.join(ROOT, 'docs/progress/G10-composition-program.md');
if (fs.existsSync(src) && !fs.existsSync(dst)) {
  fs.copyFileSync(src, dst);
  log.push('G10 草案已复制到 docs/progress/G10-composition-program.md');
}

fs.writeFileSync(path.join(DIR, 'apply-log.txt'), log.join('\n'));
console.log(log.join('\n'));
