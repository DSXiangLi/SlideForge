# SlideForge 主题「审美巅峰」优化 · Handover

> 建立日期：2026-11-12
> 用途：**新 session 的唯一入口文档**。读完本文即可继续优化剩余主题，无需重放历史对话。
> 基线：`origin/main` 原为 `9c8d7de`；**2026-11-16 已把 6 个本地提交推送至 `origin/main`**（Phase 1–3 / 4–5 / handover / analysis 入库 / 批次 1 / 推送前清理），本地与远端一致（`git status -sb` 可核）。
> 落档约定（用户明确要求）：**每一步变更都必须记录到 `docs/progress/`**。

---

## 0. 新 session 快速启动

| 项 | 值 |
|---|---|
| 主题库总数 | **30 套**（六类设计轴：色法 7 / 线法 4 / 空间 5 / 质感 8 / 光线 4 / 字法 2） |
| 已升级到「审美巅峰」 | **4 套**：B1 / C3 / E5 / H1 |
| 未更新 | **26 套**，分 **7 批**（6 批 × 4 + 尾批 2） |
| 下一批应做 | **批次 1：C1 信号黑 / E7 浮世绘 / G1 翡翠年鉴 / F1 浮光玻璃** |
| 铁律 | **每批只做 4 套 → 多类数据实测 → 出 A/B 与验收包 → 停下来等用户验收 → 通过后才进下一批** |
| 不允许 | 未经用户验收就批量铺量；把「更新 README 示例」做成新增章节；为字号加后拦截门禁 |

**开工前必读（按顺序）**
1. 本文 §5（分批 SOP 与验收门槛）——决定怎么做。
2. `analysis/G10-主题DNA规范草案.md` —— G10 字段组的原始规范与「审美巅峰」验收口径（Phase 6 起 `analysis/` 整目录已随本地提交入库；**只本地、未推送公开远端**）。
3. `docs/progress/phase1-role-type-system.md` / `phase2-editor-role-ui.md` / `phase3-render-check.md` —— 已完成的基础设施。
4. `docs/progress/phase4-sampler-v2-ab.md` / `phase5-readme-gallery-replace.md` —— 最近的实证与结论。
5. `skills/SlideForge/references/themes/<分类>/<id>/theme.md` —— 每套主题的 G0–G9；已升级 4 套含 G10。

---

## 1. 问题定位：为什么主题达不到「审美巅峰」

### 1.1 「审美巅峰」的验收口径（原始定义，勿改写）

出自 `analysis/G10-主题DNA规范草案.md` §7：

> 一页幻灯片有灵魂 = **遮住主题名、去掉颜色、缩到缩略图之后，观众仍能把它归回它的世界**；并且能说出这个主题替内容主张了什么。

拆成三条可验收项：

| 判据 | 含义 | 机器代理 |
|---|---|---|
| **类间可分** | 盲测分类（灰度 + 240×135 缩略 + 去主题名）能归回本主题 | 骨架层两两结构相关 ≤ 0.35，> 0.8 的配对占比 = 0 |
| **类内成族** | 同主题跨页一致但**有节奏**，不是每页复制同一版式 | 类内骨架相关落在 0.55–0.85；`dna_events` 强弱形态在指纹上可测出差异 |
| **主张可读** | 视觉论点先于文字被接收；能答出「主题替内容主张了什么」 | `doctrine` 已写、`signature_operator` 过 DOM 结构测试；人工/VLM 判读 |

> 现有 55 项负向验收（不溢出、不重叠、≥18px…）**一条都没覆盖这三条** —— 这正是「满分过闸却像排版过的 Word」的原因。工程可靠性是底座，不是天花板。

### 1.2 实测证据（`analysis/_fingerprint.py`，旧 28 张 theme-sampler 样张）

| 指标 | 现状 28 张样张 | 4 张 G10 演示页 |
|---|---|---|
| 骨架层两两结构相关（强模糊后的块密度向量） | 均值 **0.459**，最高 0.990；**23.3% 配对 > 0.8** | 均值 **0.055**，最高 0.384；**0% > 0.8** |
| 皮肤层两两结构相关 | 0.299 | 0.040 |
| 与「平均脸」的结构相关 | 均值 0.569，最高 0.871 | — |
| 结构边缘主方向 | **28/28 全水平**，0 个垂直/对角 | 出现垂直主结构（H1 竖排） |
| 墨水重心 X / Y | 0.416 ± 0.087 / 0.455 ± 0.064 | 0.553 ± 0.074 / 0.512 ± 0.073 |

**关键画面**：28 张样张灰度叠加后仍是一张清晰可读的 PPT（标题、正文、三格 KPI、项目符号、页脚位置逐一重合）；4 张 G10 演示页叠加后是一团互相冲突的残影。

### 1.3 根因：能定义身份的字段全都不进 HTML 产物

| 通道 | 内容 | 消费方 | 是否进 HTML |
|---|---|---|---|
| A | G0 世界参考 / unforgettable / 分化声明 | 选型面板与用户 | **否** |
| B | bake_brief · layout_blueprints / 主导隐喻 / 标题重构 | `compile-bake-prompts.py`，仅整页烙入 | **否** |
| C | G1 色值 / G2 字体 / G3 质感 / G9 母题 CSS / G5 动效 | `SLOT: theme tokens` + `SLOT: theme css` | 是 |

C 通道是**一组形容词**（色、字、纹理、贴纸、缓动），而 `skeleton.html` 的 `SLOT: slides` 由生成侧逐页决定 DOM。于是 **30 个主题共享同一副骨架**，主题对「信息如何被摆进空间」没有任何主权。

制度层加剧：`sync-themes.mjs:41-43` 把「两个主题是否不同」实现为 *L1–L7 至少 3 层实质分化（规范化文本比较）* —— 只比 Markdown 字段，**不渲染一帧**。`components.md §11` 的六构图谱系管 deck 级节奏，与主题身份无关。

### 1.4 次生问题：字号、布局、换行在部分主题下不合理

用户第二轮明确指出「风格特点有了，但是字号的设置，和文字的布局、换行再部分主题下感觉并不十分合理」，其中 **E5 / H1 的字号问题最突出**。

根因是架构性的，不是调参能解决的：

- 内容文字的 `font-size` **既可被生成侧（skeleton 示例页）裸写，又可被编辑侧（editing-contract 白名单）内联写**；
- `typography.md` §2 的下限（正文 ≥18 / 图注 ≥16 / meta ≥14 / 标注 ≥12 px@1920）只是**软指引**，没有任何结构性约束；
- 编辑器旧 UI 是 px 数字框，tooltip 甚至写着「低于 18px 警告但不禁止」—— 典型的后拦截姿态；
- 具体表现：正文 `opacity:.82` 灰化弱读、C3 标题磷光辉光烧死字形、C3 第三个 KPI「361家」溢出描边窗口、E5 楔形块/ −12° 力带压住正文、H1 汉数题跋被拆行。

### 1.5 图文不符（Phase 4 抽查坐实）

抽查旧 Gallery 现役 6 张（`p02-b1` / `p05-c3` / `p14-e5` / `p16-e7` / `p25-g1` / `p22-f1`），**12 张全部共享同一版式骨架**：大标题 → 两段正文 → **横向等权三格 KPI** → 三条列表 → 脚注，元素位置几乎逐像素一致，差异仅来自配色、字体与背景装饰。

而旧 README 第 89 行宣称：

> themes differ systematically in **layout**, texture, and graphic language, **not just color**

实测只做到 "color + texture"，**layout 没变**。且「横向等权三格 KPI」正是 B1 的 G10 `forbidden_defaults` 明令禁止的默认构图。旧 E5 尤其典型：红斜带只是贴在标题后面当背景、黑字压红带、KPI 仍横排三格 —— 力带没有成为「决定信息如何进入空间的程序」。

---

## 2. 评审标准与修复方案

### 2.1 决策记录：设计层规避，不加后拦截门禁

用户拍板（务必沿用，新 session 不要重新提议门禁）：

> 「请确认这种约束是必要的？能否从主题设计上就直接规避问题，**我认为能解决根本问题的不要加入后拦截和门禁**。」

因此明确区分三层，避免混淆：

| 层 | 含义 | 本项目取舍 |
|---|---|---|
| **设计层规避**（主路径） | 生成前/生成时结构性锁死，问题无法发生 | ✅ 角色类 `max()` 下限、G10 契约写进 theme.md 作为生成输入、编辑器只给角色下拉 |
| **后拦截门禁** | 生成后检查并打回/改写 | ❌ 用户否决（曾提议 `sync-themes.mjs` 字号门禁，未采纳） |
| **验收测量** | 生成后只做举证，**不自动改写、不作为准入门槛** | ✅ 保留：`check-capacity.py`（文本容量，与字号下限正交）、Playwright 版面审计、指纹/盲测 |

> ⚠️ **历史口径冲突，需知悉**：`G10-主题DNA规范草案.md` §4 曾设计 `check-dna.py` 作为「正向审美**门禁**」，§5 也写了「另加一组正向审美门禁」。该文件早于用户的门禁否决决策。新 session 请以本决策记录为准：**`check-dna.py` / 指纹脚本只作为验收举证工具，不做自动打回**。若确需恢复门禁，先向用户确认。

### 2.2 评审维度与阈值（每批通用）

| # | 维度 | 阈值 / 判据 | 举证工具 |
|---|---|---|---|
| 1 | 类间可分 | 骨架层两两结构相关 ≤ 0.35；> 0.8 配对占比 = 0 | `_fingerprint.py` |
| 2 | 类内成族 | 跨页骨架相关 0.55–0.85 | `_fingerprint.py` |
| 3 | 节奏方差 | `dna_events` 声明的强/弱形态，signature 几何指标有显著差异 | 指纹 + 人工 |
| 4 | 几何不变量 | `invariants` 逐条 PASS，至少 1 条是几何/方向性的 | 渲染 DOM / 像素 |
| 5 | 盲测分类 | 遮名 + 灰度 + 240×135 缩略，人/VLM 可归回本主题 | 人工/VLM |
| 6 | 主张可读 | `doctrine` 一句可复述；`signature_operator` 过 **DOM 结构测试** | 人工签署 |
| 7 | 工程底座 | 零画布越界 / 零容器溢出 / 零弱读 / 零重叠 / pageErrors 0 | `run.js` 审计 |
| 8 | 字号下限 | computed `font-size` 全部 ≥ 角色 floor；裸写 inline `font-size` = 0 | Playwright + grep |
| 9 | 层级落差 | 低密度页 最大/最小字号 ≥ 8:1（B1 系）/ ≥ 6:1（其余） | computed style |

**DOM 结构测试**（G10 草案 §1 字段纪律 1，写 `signature_operator` 后必自问）：
> 如果把这条算子删掉，页面的**元素数量、分组、顺序、位置**会不会变？答「不会，只是颜色/装饰变了」即不合格，退回重写。

- 反例（现状 unforgettable 类贴纸）：`加号角标 + 网格点阵`、`闪烁光标块`、`朱砂印章` —— 可贴在任何版式上。
- 正例：`把整页压进 12 栏网格，标题跨栏语义断行，其余信息沿栏吸附；唯一焦点是一次对齐误差为零的偏移`。

### 2.3 已实施的修复方案（Phase 1–5 全链路）

| 阶段 | 做了什么 | 关键文件 | 验证 |
|---|---|---|---|
| **P1 生成侧** | `skeleton.html` 注入 `--t-*` 令牌 + `.t-*` 角色类，`max(var(--t-*), floor)` 结构性锁死下限；示例页弃用裸 `font-size`；4 套主题 `type_scale` 由 cqw@480 改写为 px@1920 令牌源并在 G9 `:root` 注入覆盖 | `assets/skeleton.html`、4 份 `theme.md` | grep 一致性 |
| **P1 规则** | `typography.md` §8 + `SKILL.md` Step 4 新增硬规则：「内容文字只选角色不选像素，禁裸写 `font-size`」 | `references/typography.md`、`SKILL.md` | — |
| **P2 编辑侧** | `editing-contract.md` 白名单移出 `font-size`，改为三属性（font-family/color/text-align）+ 角色切换；`editor.html` px 数字框 → `#stRole` 角色下拉，`applyRole()` 切类并自动清除历史裸写 px | `references/editing-contract.md`、根目录 `editor.html` | 实机渲染 |
| **P3 渲染验收** | Playwright + 系统 Chrome 实测；含**恶意令牌场景**（7 个 `--t-*` 强压 4–8px） | `docs/progress/render-check/` | **generator PASS / editor PASS** |
| **P4 同内容重做 sampler** | 从 git 历史 `41a3147` 恢复 `tests/decks/theme-sampler/index.html`，用同一「山禾集 1.1」内容对象 × 4 套 G10 `signature_operator` **重编译 DOM**（不是换 token 换皮），A/B 对比旧 Gallery | `docs/progress/theme-sampler-v2/` | rev3 全绿 |
| **P5 README 替换** | 中英双版 Gallery 12 张换皮样张 → 4 张构图程序样张；撤销此前误加的 Theme DNA 章节 | `README.md` / `README_ZH.md`、`assets/theme-sampler/v2-*.png` | 两版 23 条图片引用零缺失 |

**两条关键设计判断（勿重算）**
1. 原 `cqw@480` 的 `display`（2.6–3.0）按 ×19.2 只值 50–58px，会掉进 64px 地板以下、且远低于 `typography.md` §1 封面 120–160px 指引 —— 说明它原本是**次级展示层**，不是封面英雄。故 `--t-display` 改以封面指引为锚按主题性格定档；`body 35px` 才是唯一忠实换算值（1.8 × 19.2 ≈ 35）。
2. `--t-heading` **不覆盖**，保留骨架 64px，使「标题:正文」≥1.8:1，优于原 cqw 换算的 1.2:1 扁平层级。

---

## 3. 已完成修复的 4 套主题（现状明细）

### 3.1 角色令牌终值（px@1920）

骨架默认 / 地板：`display 96/64`、`heading 64/32`、`subhead 40/24`、`body 28/18`、`caption 18/16`、`meta 15/14`、`vertical 96/64`。

| 主题 | `--t-display` | `--t-heading` | `--t-body` | `--t-vertical` | 性格依据 |
|---|---|---|---|---|---|
| **B1** 瑞士国际主义 | **176** | 继承 64 | 35 | — | 倒挂巨字封面，略超 §1 上限契合海报传统 |
| **C3** 终端绿 | **104** | 继承 64 | 35 | — | 扁平层级靠明暗不靠字重差 |
| **E5** 构成主义 | **128** | 继承 64 | 35 | — | 极粗 800–900 承载「巨字宣言」压强 |
| **H1** 氤氲手卷 | **92** | 继承 64 | 35 | **118** | 竖排主标题为签名形态（> 横向 display） |

`subhead / caption / meta` 四套均不覆盖，继承骨架 40 / 18 / 15。

### 3.2 各套 G10 落地与实机数据

| 主题 | 分类 | `signature_operator` 落地 | 核心 `forbidden_defaults` | 实机字号层级比 | 样张 |
|---|---|---|---|---|---|
| **B1** | 线法 | 12 栏网格（栏界 hairline 可见）＋标题跨栏语义断行倒挂字重＋横向等权 KPI 重排成**右侧纵向数据脊**，仅首个数字一次 accent 实色面积事件 | 三格等权 KPI、居中 hero、通栏长正文 >70cqw、卡片墙、任何渐变 | **11.73:1**（15–176px，19 节点） | `v2-b1.png` |
| **C3** | 字法 | 内容编译成单向时间流：命令行标题（`$ ` + 光标块）＋同构描边窗口 stdout＋数字重构为 `key:value` 输出行 | 卡片墙、圆角大卡、渐变、多色语法高亮、居中 hero、大绿底 | **6.93:1**（15–104px，21 节点） | `v2-c3.png` |
| **E5** | 空间 | 一条 −12° 力带劈开版面、标题反白装进带内、正文沿力线阶梯错排对抗、楔形块从页缘楔入承载结论数字 | 水平垂直网格矩阵、三格等权 KPI、卡片墙、居中对称、hairline 分区 | **8.53:1**（15–128px，17 节点） | `v2-e5.png` |
| **H1** | 质感 | 自右向左展开、上下金轴定界、标题竖排居右、其余按题跋分列向左递推、汉数题跋、朱印为唯一句读 | 网格卡片墙、KPI 仪表盘、水平三栏、终端/蓝图/票据词汇、高饱和多色柱图 | **7.87:1**（15–118px，24 节点） | `v2-h1.png` |

四页 rev3 审计：**零画布越界 / 零容器溢出 / 零灰化弱读 / 零重叠 / pageErrors 0**。恶意令牌场景（全压 4–8px）实测仍被 `max()` 夹回 `64/32/24/18/16/14/64`，证明下限结构性不可突破。

### 3.3 已修主题**仍待补的项**（避免误判为「全部完成」）

| 项 | 说明 |
|---|---|
| 整 deck 未用同一内容复验 | 4 张 v2 样张是**单页高密度页**；`analysis/dna-pilot.html` 的 24 页（6 页型 × 4 主题）用的是另一套自造内容 NEURAL FORGE，两者**不能混为一谈**。若要下「整 deck 达标」结论，需补一轮「同一份山禾集内容 × 6 页型 × 4 主题」。 |
| E5 / H1 缺 `bake_brief` | 全库仅 7 套有 bake_brief（A1/B1/C3/D2/D4/E3/E12）。G10 草案 §1 要求 `layout_blueprints` 与 `info_grammar` 合并为单一信息源，E5/H1 尚未做。 |
| `dna_events` 未做节奏方差实测 | 指纹脚本已存在（`analysis/_fingerprint.py`），但 4 套的强/弱形态差异尚未逐条量化验收。 |
| README 只展示单页 | Gallery 文案未宣称覆盖多页型，一致；但「主题广度」（F/G 系）因 4 张整体替换而不再展示，旧 `p01`–`p29` 28 张仍保留在 `assets/theme-sampler/`，可随时恢复。 |
| G10 草案未写入技能库 | `analysis/G10-主题DNA规范草案.md` 状态仍是「草案，未写入技能库」；G10 schema 检查尚未进 `sync-themes.mjs`。 |

---

## 4. 未更新主题清单（26 套）

判定口径：目录下 `theme.md` **同时**缺少 `composition_program` / `--t-display` / `px@1920` 三项即未更新。实测 30 套中仅 B1/C3/E5/H1 命中，其余 26 套如下。

图例：`G` = 旧 Gallery 现役 12 张之一（Phase 5 前）；`B` = 已有 `bake_brief`（可复用风格圣经）。

| # | ID | 名称 | 设计轴 | 标记 | 批次 |
|---|---|---|---|---|---|
| 1 | C1 | 信号黑 | 色法 | G | **1** |
| 2 | E7 | 浮世绘 | 质感 | G | **1** |
| 3 | G1 | 翡翠年鉴 | 色法 | G | **1** |
| 4 | F1 | 浮光玻璃 | 光线 | G | **1** |
| 5 | E2 | 蓝图 | 线法 | G | **2** |
| 6 | E3 | 装饰艺术 | 空间 | G · B | **2** |
| 7 | E10 | 星图 | 字法 | G | **2** |
| 8 | F2 | 霓虹夜行 | 光线 | G | **2** |
| 9 | E6 | 孟菲斯 | 色法 | G | **3** |
| 10 | G2 | 腮红荧光笔 | 色法 | G | **3** |
| 11 | G4 | 靛墨黄页 | 色法 | G | **3** |
| 12 | G5 | 三色旬刊 | 色法 | — | **3** |
| 13 | C2 | 暗夜植物园 | 质感 | — | **4** |
| 14 | C4 | 纸与墨 | 质感 | — | **4** |
| 15 | D1 | 奶油物语 | 质感 | — | **4** |
| 16 | D3 | 手绘油彩 | 质感 | — | **4** |
| 17 | D4 | 黄铜年代 | 质感 | B | **5** |
| 18 | E9 | 地质地层 | 质感 | — | **5** |
| 19 | E8 | 号外报纸 | 线法 | — | **5** |
| 20 | E11 | 票据 | 线法 | — | **5** |
| 21 | A1 | 电子杂志 | 空间 | B | **6** |
| 22 | E4 | 包豪斯 | 空间 | — | **6** |
| 23 | E12 | 新粗野（商务粗野） | 空间 | B | **6** |
| 24 | D2 | 柔光暗房 | 光线 | B | **6** |
| 25 | F3 | 暮色长镜 | 光线 | — | **7** |
| 26 | E1 | 孔版印刷 | 色法 | — | **7** |

**统计**：未更新 26 套 = 色法 7（缺 B1 无，色法原 7 全在）／线法 3／空间 4／质感 7／光线 4／字法 1。
`bake_brief` 已有 7 套中，5 套在未更新清单内（A1/D2/D4/E3/E12），2 套在已升级清单内（B1/C3）。

**批次排序依据**（与 G10 草案 §6 建议顺序的差异，已明示）
- 草案 §6 建议「先空间/线法 → 再质感/光线 → 最后色法/字法」。
- 本文改为**前 3 批优先旧 Gallery 现役 11 套**：它们是对外门面，且 Phase 4 的指纹/抽查已实证其同质化；后 4 批按设计轴聚批，逼出轴内分化。用户可按偏好重排，但**每批仍须 4 套**。

---

## 5. 分批优化与验收 SOP（核心，新 session 照此执行）

### 5.1 铁律

1. **每批恰好 4 套**（尾批 2 套），不多做。
2. **同一批内必须用同一份内容对象**做基线，保证 A/B 公平。
3. **多类数据压力测试**必须跑，不能只渲一页。
4. **自动化只举证，不代替验收**：审计全绿 ≠ 通过；必须出 A/B 与验收包，**停下等用户明确「通过」**。
5. 用户打回时，只重做该批，**不带着问题进下一批**。
6. 每批的变更与报告落到 `docs/progress/`，提交本地；**不要主动 push**。

### 5.2 批次表

| 批次 | 4 套主题 | 重点 |
|---|---|---|
| **1** | C1 信号黑 / E7 浮世绘 / G1 翡翠年鉴 / F1 浮光玻璃 | 旧 Gallery 高曝光，跨色法·质感·光线三轴；先验「去色后仍可辨」 |
| **2** | E2 蓝图 / E3 装饰艺术 / E10 星图 / F2 霓虹夜行 | 旧 Gallery 高曝光；E3 已有 bake_brief 可作单一信息源样板 |
| **3** | E6 孟菲斯 / G2 腮红荧光笔 / G4 靛墨黄页 / G5 三色旬刊 | 色法轴聚批，**最难**：四套都靠色彩，必须逼出结构级分化，否则按草案 §6.5 考虑合并为变体 |
| **4** | C2 暗夜植物园 / C4 纸与墨 / D1 奶油物语 / D3 手绘油彩 | 质感轴；注意 G3 背景配给制与 `texture-on` 逐页落码 |
| **5** | D4 黄铜年代 / E9 地质地层 / E8 号外报纸 / E11 票据 | 质感 + 线法；印刷/地层/报纸/票据四类「信息容器」易写出好算子 |
| **6** | A1 电子杂志 / E4 包豪斯 / E12 新粗野 / D2 柔光暗房 | 空间 + 光线；本批 4 套全有 bake_brief，可一并验证 G10 ↔ layout_blueprints 合并 |
| **7** | F3 暮色长镜 / E1 孔版印刷 | 尾批 2 套 + 全库 30 套收口复验 |

### 5.3 每批标准作业流程（Step 0–7）

| Step | 动作 | 产出 |
|---|---|---|
| **0 冻结基线** | 固定本批 4 套 + 同一内容对象（建议沿用「山禾集 1.1 整体特色及优势」，字段见 `phase4-sampler-v2-ab.md` §1）；记录各套旧图 `assets/theme-sampler/pNN-*.png` 作为 A/B 对照 | `docs/progress/phaseN-batch<k>/brief.md` |
| **1 写 G10 契约** | 每套补全 7 字段：`doctrine` / `signature_operator` / `silhouette` / `info_grammar`（至少 cover/claim/analysis/data）/ `invariants`（3–5 条，≥1 条几何方向性）/ `forbidden_defaults` / `dna_events`；**逐套过 DOM 结构测试**，不过就重写 | 4 份 `theme.md` |
| **2 令牌与母题** | `type_scale` 写成 px@1920 `--t-*` 令牌源；G9 `:root` 注入覆盖（勿盲用 ×19.2 换算 display）；G9 母题 CSS 遵守 `.mt-*` 命名空间 + 类名全库唯一 + 禁字面 hex | 4 份 `theme.md` |
| **3 构造测试集** | 按 §5.4 造基线集 24 页 + 压力集 16 页（≥40 页/批）；内容对象单一来源，脚本只消费不改写 | `build.js` + `sampler.html` |
| **4 编译** | 按各套 `signature_operator` **重编译 DOM**（不是换 token）；字号只用 `.t-*` 角色类；静态渲染关闭入场动效，避免 `data-anim="chars"` 中间帧 | `sampler.html` |
| **5 自动审计** | Playwright 驱动系统 Chrome，逐 section 截图 1920×1080 + 逐节点 bbox / computed style；按 §5.5 阈值跑 9 项 | `report.json` + PNG |
| **6 指纹与盲测** | 跑 `_fingerprint.py` 量类间/类内相关、主轴方向、墨水重心；生成去色 240×135 缩略图盲测页 | 指纹 JSON + `blind-test.html` |
| **7 出验收包并停** | 生成新旧 A/B 并排页 + 本批报告（问题清单 / 迭代轮次 / 阈值结果 / 遗留）；**present 给用户，明确请求验收** | `phaseN-batch<k>-report.md`、`compare.html` |

> **用户验收通过前，不修改 README Gallery、不进下一批、不 push。**

### 5.4 测试矩阵：「各类数据」的具体定义

**6 种页面类型**（与 G10 pilot 一致）：封面 `cover` / 目录 `toc` / 低密度主张 `claim` / 高密度分析 `analysis` / 图表 `data` / 收尾 `closing`。

**7 类数据形态**：

| 代号 | 形态 | 样例 | 主要考验 |
|---|---|---|---|
| D1 | 短主张 | ≤12 字标题 + ≤40 字说明 | 留白、巨字压强、accent 面积预算 |
| D2 | 长段落 | 中文 200–400 字无分段 | 换行、行高、通栏行长（B1 禁 >70cqw） |
| D3 | 数字 KPI | 3–5 组：`8,637` / `2.8亿` / `3.6%` / `−12%` | **禁横向等权三格**；数据脊 / key:value / 阶梯 / 汉数 |
| D4 | 图表数据 | 4–8 系列折线、堆叠、时间序列，含 0 值与空值 | chart token 派生、系列数上限 8、暗色页镜像派生 |
| D5 | 列表/目录 | 3–8 项，含超长标签、中英混排 | 分栏、题跋列、终端窗口同构 gap/padding |
| D6 | 竖排/题字 | CJK 竖排、汉数、字母混排 | `writing-mode:vertical-rl`、字距、整列可容不强制断列 |
| D7 | 极端与退化 | 30+ 字极长标题、单字、空数据、纯英文、超宽数字 | 溢出、重叠、地板 clamp、字形烧蚀 |

**每批渲染量**：
- **基线集**：4 套 × 6 页型 = **24 页**（同一内容对象，各页型分配 D1/D3/D4/D5 等自然数据）
- **压力集**：4 套 × 4 变体（D2 长段落 / D3 大数与负数 / D4 八系列图 / D7 极长标题）= **16 页**
- 合计 **≥40 页/批**，全部脚本化，无手工截图。

> 内容一致性例外（已获认可）：H1 按 G10 契约把数字改写为汉数题跋，但**阿拉伯数字以括注完整保留**，信息集与其余页一致。

### 5.5 自动验收阈值（每批必须全绿才可提交验收）

| 项 | 阈值 | 工具/注意 |
|---|---|---|
| 画布越界 | 0 | `run.js`：文本 bbox vs 1920×1080 |
| **容器内溢出** | 0 | `run.js`：最近的、有显式 `top`+`height` 的绝对定位祖先。**只查画布会漏这类**（C3「361家」曾漏检） |
| 弱读 | 0 | 字号 ≥18px 且 `opacity < 0.9` 视为弱读 |
| 同层文本块重叠 | 0 | **排除带 `transform` 的元素**：旋转后 AABB 虚胖会误报（E5 −12° 力带） |
| pageErrors | 0 | Playwright |
| 裸写 inline `font-size` | 0 | DOM 检查；历史 px 应由 `applyRole()` 自动清除 |
| 字号地板 | 全部 ≥ 角色 floor | computed style；建议每批跑一次恶意令牌场景复验 |
| 层级落差 | ≥8:1（B1 系）/ ≥6:1（其余） | 低密度页 最大/最小字号比 |
| 类间可分 / 类内成族 / 节奏方差 | 见 §2.2 判据 1–3 | `_fingerprint.py`；**举证用，不自动打回** |

### 5.6 用户验收包与签收清单

每批交付必须包含，缺一不可：

- [ ] 4 份 `theme.md` 的 G10 契约（附逐套 DOM 结构测试自问自答）
- [ ] 4 套 `--t-*` 令牌终值表 + 与骨架地板的一致性核对
- [ ] ≥40 页 PNG + `report.json`（逐节点 bbox / 字号 / 溢出 / 弱读 / 重叠原始数据）
- [ ] 审计 9 项阈值结果表（含未通过项的处理说明）
- [ ] 新旧 A/B 并排页 `compare.html`（新图 vs 该套旧 `pNN-*.png`）
- [ ] 指纹/盲测结果（去色缩略图）
- [ ] 本批报告 `docs/progress/phaseN-batch<k>-report.md`：问题清单、迭代轮次、遗留、诚实边界
- [ ] **明确请求用户签收**：「通过 / 打回 + 具体原因」；通过后才提交本地、才进下一批
- [ ] README Gallery 是否更新，**每批结束后单独征询**，不自动改

### 5.7 落档与提交节奏

```
docs/progress/
  HANDOVER.md                       ← 本文（唯一入口）
  phase1-role-type-system.md        ← 已完成
  phase2-editor-role-ui.md          ← 已完成
  phase3-render-check.md            ← 已完成
  phase4-sampler-v2-ab.md           ← 已完成
  phase5-readme-gallery-replace.md  ← 已完成
  phase6-batch1/                    ← 下一批起，每批一个目录
    brief.md / build.js / run.js / sampler.html / report.json / *.png
    compare.html / blind-test.html / phase6-batch1-report.md
```

- 每批：先落档 → 本地 commit（**精确 `git add`，不用 `-A`**）→ 请用户验收 → 通过后再开下一批。
- 用户只要求本地提交时，**不要 push**。

---

## 6. 资产与工具地图（新 session 必读）

| 路径 | 用途 | 入库状态 |
|---|---|---|
| `skills/SlideForge/references/themes/index.md` | 主题库索引、七层表达力栈、G9 CSS 纪律、禁忌、入库流程 | ✅ |
| `skills/SlideForge/references/themes/<分类>/<id>/theme.md` | 30 套主题 G0–G9；4 套含 G10 | ✅ |
| `skills/SlideForge/assets/skeleton.html` | v7.6 骨架，1920×1080 基准，`.t-*` 角色类与地板 | ✅ |
| `skills/SlideForge/references/typography.md` | §2 字号地板、§7 `.tt-*` 文字效果、§8 角色令牌系统 | ✅ |
| `skills/SlideForge/references/editing-contract.md` | 编辑器白名单（三属性 + 角色切换） | ✅ |
| `editor.html`（仓库根） | Bridge 编辑器；`#stRole` 角色下拉、`applyRole()` | ✅ |
| `assets/theme-sampler/` | 旧 `p01`–`p29` 共 28 张换皮样张 + 新 `v2-{b1,c3,e5,h1}.png` 4 张 | ✅ |
| `docs/progress/render-check/run.js` | Phase 3 实机渲染校验（含恶意令牌场景） | ✅ |
| `docs/progress/theme-sampler-v2/build.js` + `run.js` | **可直接复用**的同内容多主题编译器 + 四类版面审计 | ✅ |
| `docs/progress/theme-sampler-v2/compare.html` | 新旧 A/B 并排页模板 | ✅ |
| `analysis/G10-主题DNA规范草案.md` | G10 规范草案、验收口径、指纹实测 | ✅ Phase 6 入库，已随本次推送公开 |
| `analysis/_fingerprint.py` / `_fingerprint.json` | 28×28 结构相关矩阵、指纹测量 | ✅ |
| `analysis/check-dna.py` / `dna-pilot.html` / `dna-soul.html` | 24 页 pilot、盲测演示、check-dna 草案 | ✅ |
| `analysis/DNA-*.png` / `PILOT-*.png` / `B1-*.png` | 诊断与 pilot 截图 | ✅ |
| `analysis/_render*.py` / `_patch*.py` / `_scan-themes.js` | 渲染、补丁与扫描脚本（路径已相对化，可跨机复跑） | ✅ |
| `analysis/*.log` / `_*.txt` stdout 转储 | 运行日志（可重跑生成） | ❌ 已从跟踪剔除，`.gitignore` 忽略，只本地保留 |
| `docs/progress/_logs/theme-sampler-source.html` | 从 git 历史恢复的源 deck | ❌ `.gitignore` 忽略（只本地） |
| `tests/decks/theme-sampler/index.html` | 原始 sampler（29 section、skeleton v7.4） | ❌ 工作树不存在；可用 `git show 41a3147:tests/decks/theme-sampler/index.html` 取回 |

> ✅ **换机风险已消除，并已推送（2026-11-16）**：`analysis/` 的核心判据资产已随本地提交推送到 `origin/main`；运行日志与 stdout 转储在推送前从跟踪中剔除（`.gitignore` 忽略、只本地保留），脚本内的硬编码本机路径已改为相对定位。两个边界：① 干净克隆/另一台机器需同步远端；② 前 5 个提交（含 `fa4666f` / `c1efc3e`）的**历史文本**里仍留有本机路径，当前 HEAD 已无；按用户决策本轮「追加清理提交、不改写已有提交」，若需从历史彻底抹除要另行重写整条提交链。

**本机环境速查（shim 有坑）**

| 项 | 值 |
|---|---|
| 托管 Node | 用 `node -v` / `command -v node` 定位（22.x）；路径因机器而异，脚本不写死 |
| playwright-core | 装在托管 node 的 workspace `node_modules`（1.65.0，纯 JS，不下载 Chromium）；渲染脚本用 `PLAYWRIGHT_CORE` 环境变量定位 |
| 系统 Chrome | 用 `CHROME_PATH` 环境变量指定 `executablePath`；未设置时回退 Windows 默认安装路径 |
| 安装方式 | 系统 `npm` 在本 shell 不可用；用 `node "<managed>/node_modules/npm/bin/npm-cli.js" install --prefix <workspace> playwright-core@1.65.0` |
| shell 缺失命令 | `dirname` / `head` / `tail` / `ls` / `mkdir` / `cat` / `sed` 均不可用或静默失败 → **一律用托管 Node 的 `fs` / `child_process.execFileSync` 代替，命令里不要接管道**；脚本 stdout 可能被吞，重定向到 `.log` 再用 Node 读 |
| 预览页路径 | 从 `docs/progress/theme-sampler-v2/` 到仓库根是 `../../../`；静态预览服务根跨不到 `assets/`，需加 `onerror` 同源回退 |

---

## 7. 已知遗留、风险与「不要重做的坑」

| # | 坑 | 正确做法 |
|---|---|---|
| 1 | 把「更新 README 中示例」理解成**新增章节** | 用户要的是**更新已有 Theme Gallery**。`5dc73a8` 曾另起自造内容新增 "Theme DNA" 章节，被纠正并于 Phase 4 撤销 |
| 2 | 为字号加后拦截门禁 | 用户明确否决。用 `.t-*` 角色类 + `max()` 地板做设计层规避；`check-capacity.py` 是唯一保留的正当门禁 |
| 3 | `git add -A` | `.workbuddy/`（含本机绝对路径 memory）、`SlideForge.zip`、h1 两张 demo 图**仍未被 gitignore 忽略**；`analysis/` 虽已入库，也需用显式路径 `git add analysis/`。一律 `git add -u` + 显式路径 |
| 4 | 同一条消息里对同一文件发多个 Edit | 会竞态丢一个（曾导致 B1/C3 的 `type_scale` 与 E5/H1 的 `:root` 丢失）→ **一次只改一个文件的一处** |
| 5 | 用 ×19.2 盲换算 cqw `display` | 那是次级展示层，不是封面英雄；改以 `typography.md` §1 封面 120–160px 为锚按主题性格定档 |
| 6 | 版面审计只查画布越界 | 会漏**容器内溢出**（C3 KPI 越出描边窗口）→ 补「最近显式 `top`+`height` 绝对定位祖先」检测 |
| 7 | 重叠检测不排除旋转元素 | −12° 力带 AABB 虚胖造成假阳性 → 排除带 `transform` 的元素 |
| 8 | 灰化弱读 / 辉光烧字形 | `opacity < .9` 且字号 ≥18px 即弱读；C3 标题磷光曾糊住字形边缘（G9 明令禁止）。迭代 rev1→rev3 花了 3 轮才全绿 |
| 9 | 把 H1 汉数题跋当成「内容不一致」 | 阿拉伯数字以括注完整保留，信息集一致，这是 G10 契约要求的形态转换 |
| 10 | G10 草案 §4 的 `check-dna.py` 被当成门禁恢复 | 见 §2.1 决策记录：只作验收举证，不自动打回；要恢复门禁先问用户 |
| 11 | 以为 30 套主题都已有「升级后版本」 | 只有 4 套。**其余 26 套重渲旧内容只会复刻换皮，没有 A/B 意义**，必须先写 G10 契约 |
| 12 | 盲测用彩色大图 | 必须灰度 + 240×135 缩略 + 遮住主题名，否则测的是配色不是结构 |

**其他遗留**
- `sync-themes.mjs` 尚未加 G10 schema 必填检查；`EXPECTED_COUNT` 仍按 30 套口径。
- `bake_brief.layout_blueprints` 与 `G10.info_grammar` 的单一信息源合并（草案 §1 纪律 5）**全库未做**。
- `docs/progress/_logs/` 被 `.gitignore` 排除；`docs/design/` 等其余 docs 内容仍不随仓库发布（`.gitignore` 用 `/docs/*` + `!/docs/progress/` 白名单）。
- `assets/theme-dna/` 8 张图保留未删，自 Phase 4 起不再被任何 README 引用。
- `analysis/` 的研究脚本含硬编码本机绝对路径（`_fingerprint.py` / `_render*.py` / `_patch*.py` 等），跨机复跑前需改为相对路径；入库只为留痕与判据可追溯。

---

## 附录 A · Commit 时间线

| Commit | 内容 |
|---|---|
| `9c8d7de` | `origin/main`（远端仍停在此） |
| `41a3147` | 历史提交，`tests/decks/theme-sampler/index.html` 源 deck 可从中取回 |
| `5dc73a8` | 误加 README Theme DNA 章节（后撤销） |
| `490bfa7` | Phase 1–3：角色化字号系统 + 编辑器角色下拉 + 实机渲染验收落档（28 文件，+1574/−116） |
| `da7dca0` | Phase 4–5：同内容重编译 4 主题 + README Gallery 替换 + 落档（27 文件，+2537/−55） |
| `d4209e9` | Handover 文档（仅本文，+421） |
| `fa4666f` | `.gitignore` 放行 `analysis/` + 整目录入库 + 本文同步勘误（**未改写**，历史文本仍含本机路径） |
| `c1efc3e` | 批次 1：E6/G2/E7/F1 的 G10 构图程序 + 40 页验收包（并行会话提交） |
| 推送前清理提交 | 剔除 33 个运行日志 / 两批脚本路径相对化 / 文档勘误；作为第 6 个提交追加，不改变前 5 个提交 |

2026-11-16 已全部推送至 `origin/main`，本地与远端一致。

## 附录 B · 新 session 第一句可以这样说

> 「我读了 `docs/progress/HANDOVER.md`。当前 30 套主题中 B1/C3/E5/H1 已升级，26 套待做。按 §5 从**批次 1（C1 / E7 / G1 / F1）**开始：先补四套的 G10 契约并过 DOM 结构测试，用同一份「山禾集 1.1」内容构造 24 页基线 + 16 页压力集，跑 9 项审计与指纹，出 A/B 验收包后**停下来等你验收**。开始前请确认：① 批次顺序是否照 §5.2；② `analysis/` 已随 Phase 6 入库并推送至 `origin/main`，请确认当前工作副本已同步。」

---

*本文是 handover 的唯一入口。后续每批完成后，请回到 §4 更新未更新清单、§附录 A 追加 commit，并同步 `.workbuddy/memory/`。*
