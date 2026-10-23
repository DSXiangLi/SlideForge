# K 期：高密度表达——文本容器层 + 章节跳转 + 动效编排纪律（2026-09-20）

> 设计文档：`docs/design/high-density-containers.md`（已过审核，自审修复 5 项）。
> 触发：用户验收——低密度测试充分但高密度缺测试；产物无章节跳转；文本容器层缺失致高密度页面层次感弱；demo1（SmartForge）动效层的可吸收点。

## 三块改动

### 1. 文本容器层（components.md §13 + typography.md §5）

六型文本容器（与结构族正交——族管关系、容器管包装）：**字段行 kv-rows / 数据带 ticker / 指标卡 metric-card / 对照列 versus-cols / 堆栈层 stack-rows / 注记块 note-block**（分型锚点：demo1 的 hero-meta/demo-status/ticker/pain-card/mtx-col/arch-layer）。容器内四层字阶纪律为硬规则（①eyebrow mono 低明度 → ②题 → ③体 → ④注；相邻层至少在字号/字重/明度分化一项）。容器造型委托主题 G4/G9（§12 同口径）。typography.md §5 补"高密度档容器化义务"硬规则：裸排正文列表即违规。gallery 新增六型实例页（p45–50，含 mend-bar 双实例）。

### 2. 章节跳转（skeleton v7）

- 章节页 `.slide` 声明 `data-chapter` + `id`（同 data-slide-id）；目录链接 `<a class="nav-link" href="#id">`（原生 `<a>` 天然 Tab 可达——不劫持 Tab，无障碍不破）；
- 键盘直跳：数字键 1–9 跳第 N 章、0/Home 回封面、End 到末页（老 deck 无章节不动作）；
- 编辑器：编辑态拦截 nav-link 点击（捕获阶段 preventDefault+stopPropagation，点击语义回归选中/编辑）；净化无新增（跳转无运行时状态）。
- SKILL.md：高密度档封面目录【默认】必载。

### 3. 动效编排纪律（motion.md）

审核结论：demo1 Motion Layer 复盘的五条纪律（注意力预算/职能五分法/时长公式/stagger 公式/静止期/语义同构/感知性能）**motion.md v3 的 §1–§2 已全部覆盖**——真正缺的增量落了三处：
- **内容→动效对照表**（§3 新增查询手册，与 motifs.md 互引闭环：motifs 管静态呈现隐喻，对照表管动态过程隐喻）；
- **`mend-bar` 双态修复条**（data 族新 recipe，纯 CSS 两阶段：--from 警示渐变填充 → 收窄 --val 切 accent 纯态，承载"问题→解决"叙事；--from/--val 是产物内容）；
- **`data-rotate` 轮转高亮**（loop 型新机制：容器内子项轮转 .active，in-view 生命周期，2.4s 间隔烧死，freeze 摘除清空，骨架只给最小默认样式）。

契约 v6.3：data-chapter/nav-link 为产物内容；mend-bar 参数口径；rotate .active 为运行时状态（freeze 主责、净化兜底）。

## 验收资产

- **高密度基准内容包** `tests/decks/smartforge-content.md`（抽象自 demo1，与 J 期低密度基准配对——后续 PPT 测试固定用这两份内容）。
- **验收 deck `tests/decks/smartforge-c1/`**（8 页高密度 × c1 信号黑）：封面目录五章三通道可跳、六型容器全用、mend-bar ×4（漏损率 94/86/100/78→0）、流水线 data-rotate、5 关键页呈现发散三案留档 NOTES.md。自检全绿（零溢出零重叠/字号/跳转三通道/freeze）。
- harness 新增 **T22**（数字键/nav-link/End 三通道 + 编辑态拦截 + rotate 轮转与 freeze + mend-bar 参数 + 保存净化）；smartforge-c1 入 T1 回归名单；T18 覆盖 gallery 50 页。
- 全量回归 **45/45 PASS**（T22 新增、T1 注册 smartforge-c1、T18 覆盖 gallery 50 页；修复两处：BOOLEAN_ATTRS 白名单补 data-rotate/data-rotate-item 布尔属性序列化、T22 End 断言改与最大滚动位置比较）。

## 已知边界

- mend-bar 的警示渐变色（红→黄）是框架层常量而非主题 token——"警示"是跨主题语义（同 light-sweep 的白色光既有先例）；如未来主题要求定制警示色，再评估开 token。
- data-rotate 间隔 2.4s 烧死（demo 的 2.2s 略快教训已吸收）。

## K 期深化：密度范式回灌（2026-09-20 第二轮）

用户指出 smartforge-c1 密度提升但未达 demo1，且**目的不是复刻示例而是提炼范式**。处置：逐屏截图 + DOM 量化解剖（`docs/research/demo1-density-analysis.md`）——断层定位在**微字标注层**（demo1 每屏 21–54 个 ≤13px mono 标注，我们为 0），不在容器与字阶。五条范式回灌：typography.md 标注层合法化（12–16px + 五纪律 + 配额 ≥15 处/内容页）、components.md §13 密而不乱纪律（明度分层/3–5 容器区/同构重复）、motion.md 高密度动效配额（主动效不变、容器级语义微动效）、AGENTS.md 元原则「范例是矿不是图」。

**验收 deck v2 重做**（smartforge-c1 就地）：内容页文本叶 25–40 → 56–85、微字标注 0 → 15–42/页（进入 demo1 基线区间）、字阶 5–6 档 → 8–10 档连续；标注层全部为真实元信息（单位/口径/序号/来源，零编造）。新工具：`density_measure.py`（DOM 密度量化）、j_render_check.py 升级标注层豁免口径。全量回归 45/45 PASS（2026-09-20 14:18 复测）。

**v3 动效返工**（同日第三轮，用户验收"标题动效全同、背景装饰层无动效"）：demo1 代码级复盘（读实现非 README）提炼两条回灌 motion.md §6——①标题动效两档制（仪式页最强锚点款；章节/内容页统一一款质感文字动效且必须比正文"贵"；禁止 wipe-clip 色块款充当标题动效）；②背景与装饰层隐性运动（L4 优先全局选型——底纹漂移/噪点；装饰家具低频呼吸计入每屏背景预算）。deck 修正：p2–p7 标题 wipe-clip/rise-in → chars 默认档（封面/收束保持 chars hero 档，同 recipe 两档节奏——主题禁用清单核查拦下了 mask-lines 方案，c1 G5 明禁）；全局 amb-noise 信号噪点底纹（封面不叠加 fx）；巨号页码 folio-breath 8s 呼吸（摆幅 ≤.08）。全量回归 45/45 PASS。

**v4 字体层**（同日第四轮，用户验收"字体层有艺术字体效果"）：demo1 代码复盘——四字体分工制 + "艺术字效果的大头是文字处理不是字体文件"。回灌：skeleton v7.1 文字效果词汇 `.tt-outline/.tt-strike/.tt-mark/.tt-uline`（纯 CSS、文字保持可编辑、描边字编辑态还原本色——契约 v6.4）；typography.md §7 词汇表（含混排手法"祭献一个词给氛围"）；themes.md G2 扩「display 联网备选」可选字段（离线方针不破，c1 声明 Bebas 类窄体备选 + 混排/删除线亲和）。deck v4：封面「SMART 填充 + FORGE 描边」混排（chars 拆字与内嵌 span 冲突——解法：两个独立词元各自 chars，h1 退为容器，已入 NOTES 经验）、ticker from 值 .tt-strike、痛点关键词 .tt-mark ×4、收束宣言 .tt-uline ×3。全量回归 45/45 PASS。

**L 期泛化**（同日第五轮，用户纠正"不是只学这一类字体"+ 补充装饰线/装饰元素缺口）：字体呈现方式抽象为**五轴模型**（字内填充/字外装饰/排印方向/尺度形态/字重混排——demo1 只用了其中两款），骨架 v7.2 新增 `.tt-shadow`（错版叠印）/`.tt-glow`（发光，暗色主题）/`.tt-cond`（窄体拉伸=穷人版 condensed，离线替代联网窄体）；装饰线抽象为**通用语法层**（与主题 G9 母题分层：语法共享、词汇专属、明度服从 G4 口径）——骨架 `.rl-dashed/.rl-ticks/.rl-leader/.rl-fade/.rl-corners` 五款 + 装饰元素三族（几何小件/符号字符/纹样带归主题母题）+ 硬规则（每页 ≤3 款、禁无对象空装饰），落 components.md §14。gallery 新增 p51–52 两页词汇实例（T18/T1 通过）。

**实验 deck：smartforge-e8 报纸版**（用户要求"在已有内容上实验新技能效果"）：同 SmartForge 内容 × e8 号外报纸——报头徽标条/通栏粗细双线/三栏正文/.rl-leader 引线目录/tt-shadow 错版叠印巨题/mend-bar×4/data-rotate 流水线/纸纹噪点全局；密度实测全达标（内容页文本叶 56–82、标注层 24–45、字阶 8–9 档连续）。与 smartforge-c1 构成同内容双主题对照资产。顺带修正 harness 两脚本亮度极性 bug（亮底主题标注层豁免误判，E8 为库中首个亮底高密度 deck 首次暴露；修正只放宽不收紧，回归佐证无外溢）。smartforge-e8 入 T1 回归名单。

**M 期：容器边界义务 + 主题立场三元模型**（同日第六轮，用户裁决 isolation-ab 对照实验：C 面+框胜高密度、A/B 线/框胜低密度；并定调"美不是单一的"——主题不得写死自由区）：

- **§12 例外**（暗底允许面+细框）+ **§13 容器边界义务**（高密度每容器区必须面或框其一；同页同构边距系统；面/框不混页）上一段已记；本轮成文**主题立场三元模型**（themes.md Schema 段 + theme-expression-stack.md §四·补）：主题只声明「必须有什么 / 美感通过什么形式表达 / 不能有什么」，其余为内容驱动自由区（密度、预算、层次纪律动态填充）。
- **20 主题存量三元化改写**：消除全部"结构禁"（c1 禁描边卡、a1/c4/e8/e9 禁描边装饰框、e4/e5 禁描边卡等），保留气质禁（禁圆角/阴影/玻璃/渐变），每主题 G4 补「高密度容器边界」字段（各自世界真实存在的形式：c1 灰档面+细框 / e8 栏框 / e2 双线图框 / e10 虚线星座界框 / e5 纯色带即容器 / c4 灰档面+书籍边栏左粗线……）；sync-themes 零错误（两两七层 diff 全过）。
- **deck 修正**：smartforge-c1 v5（高密度容器统一灰档面+细框、同构边距、p5 对照列补面）；smartforge-e8 v2（纯线→墨线栏框成阵，控制变量密度零变化）。
- **并行任务交叉质检抓到两处 v4 内容错误并已修**：收束页混入 j-localfirst 文案（已替换为 SmartForge 宣言「让内容生产从外包手艺，变成平台流水线。」+ tt-uline）、p3 tt-mark ×4 超 Highlight ≤3 纪律（已减为 3）。
- 对照资产：`tests/decks/isolation-ab/`（三版控制变量，几何逐像素一致，截图 tests/harness/results/isolation-abc.png）。
- 回归：**46/46 PASS**（三元化改写 + 两 deck 容器边界修正 + 两处内容错误修复后全量复测）。
