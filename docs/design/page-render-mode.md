# 子技能 A：整页生图（页面烙入模式）

> 状态：待评审 · 2026-09-21 · 总览与公共地基见 `tri-form-architecture.md`
> 依据：2026-09-21 用户意见——整页生图只保留**完整烙入**一种形态，不做"背景生图 + HTML 文字层"混合态（页内局部生图归属既有插画模式，两个能力边界必须清晰）；整页作图参考 `source/codex-ppt-skill-main/`。

## 1. 边界划分【硬规则】

| 模式 | 粒度 | 页面本质 | 文字 |
|---|---|---|---|
| 插画模式（Step 5.5，既有） | **页内槽位** | HTML 页 | 永远在 HTML 层，可编辑 |
| 烙入模式（本文档） | **整页** | 一张整页图 | 烧死在图里，不可就地编辑 |

不存在第三种"背景生图 + 文字叠加"形态。需要局部生图走插画模式，需要整页生图走烙入模式。

## 2. 产物结构：源层保留

烙入页 = 整页图 + **完整保留的 HTML 源层**：

```html
<section class="slide" data-slide-id="cover" data-render-mode="baked" data-content-hash="a3f8c2e19b04">
  <img data-editable-image
       data-image-slot="page-baked-16x9"
       data-image-intent="（编译后的整页生图意图摘要）"
       data-image-state="generated"
       src="assets/page-cover.png" alt="封面（整页生图）">
  <div class="baked-source" hidden>
    <!-- 原 HTML 页面内容完整保留：标题、正文、组件、契约标记原样不动 -->
  </div>
</section>
```

设计要点：

- **源层是真相锚**：烙入页的文字内容仍可被提取、检索、进 manifest；"图里文字与 deck 内容脱节"成为可检测状态（hash）而非不可知风险；
- **源层参与 hash**：`data-content-hash` 从源层的 `data-editable` 文本计算——编辑源层即翻转 hash，stale 检测对烙入页与 HTML 页同一机制；
- **契约 v7 增量**：`data-render-mode="html|baked"`（缺省 `html`）；`.baked-source` 源层规约——骨架运行时（拆字/动效/in-view）与编辑器可编辑扫描都**跳过** `.baked-source` 内部；源层不标 `data-editable-skip`（它不是装饰件，编辑通过编辑器专用"源层编辑"入口进行）；序列化保存时源层原样保留；
- **骨架改动点（skeleton v7.3，随契约 v7 同步升版）**：①运行时文本引擎与动效初始化选择器排除 `.baked-source` 内部；②打印样式表确认 `hidden` 源层不占打印页（现行"每页独立一页"红线对烙入页的语义 = 打印整页图）；③`skeleton-version` meta 升版，存量 deck 无 `.baked-source` 不受影响；
- **`data-image-intent` 口径**：烙入页的 intent 写**人可读的换图指南**（同插画槽位语义），生图指令全文不入属性（指令是编译产物，存 `prompts/` 工作区或交付说明，不污染产物）；
- **页面级槽位**：`page-baked-16x9` 沿用契约 v5 三方绑定（槽位比例↔画布 1920×1080↔生图 16:9，容差 5%），`check-images.mjs` 扩展识别页面级槽位；
- **窄窗口/打印/缩放行为与 HTML 页一致**（同一 `.slide` 容器与缩放骨架），无新增适配负担；批注对烙入页仍可用（页级 + 坐标区域粒度，excerpt 为空）。

## 3. 工作流（SKILL.md 新增 Step 5.6 · 页面烙入 pass）

入口【硬规则】：Step 5 渲染校验通过 + 用户确认内容验收之后，用户**逐页选定**哪些页烙入（典型候选：封面、章节页、收束页等 `.cover-page` 仪式页）。不做"一键全 deck 烙入"的默认推荐——这是用户用编辑性换表现力的显式选择，交付说明必须诚实声明哪些页文字不再可就地编辑。

**1. 盘点与编译**：对选定页，从 manifest 提取逐字文本与槽位清单，编译生图指令（§4）。

**2. 风格锚**（比 codex 样张机制更强的一手）：codex 的风格锚是"先生成一张样张图再以其为锚"；我们已有渲染好的 HTML deck——**风格锚 = 真实 HTML 页的浏览器截图**（默认取封面页，用户可指定）。图片页与 HTML 页的家族相似性由同一渲染产物直接锚定，而非由另一张生图间接近似。

**3. 代表页审批闸门**：先烙一页代表页（默认取烙入清单中的第一页；封面在清单内时强制取封面）→ 用户确认视觉执行质量 → 才批量。风格方向在 Step 2 主题冻结时已决，此闸门只管执行质量（文字准确性、材质、构图），不重新讨论风格。

**4. 逐页生图**：oai生图 CLI（沿用 Step 5.5 的命令契约），16:9、2K（2560×1440，卡文字清晰度与模型像素上限的平衡点）；落盘 `assets/page-<slide_id>.png`，与槽位同名心智一致；成功后 `data-image-state="generated"`、`data-render-mode="baked"` 就位。

**5. 回归校验【硬规则】**：

- 重跑 Step 5 渲染校验（烙入页走图片分支：满幅、比例、无位移）；
- `check-images.mjs --mode illustration` 扩展支持页面级槽位，零错误；
- 反降级：声明烙入的页不允许残留 `placeholder`。**生成失败的页诚实回退为 HTML 页**（`data-render-mode` 保持 `html`，源层即页面本体）——我们比 codex 的 blocker 纪律多一条出路：HTML 页本身就是合格交付，不会交付残页。失败页在交付说明逐条列出。

**stale 与重新烙入**：用户在编辑器修改烙入页源层 → hash 翻转 → 编辑器 stale 徽标 → 用户要求时重跑本 pass（仅 stale 页）。生图成本远高于排版，不自动重烙。

## 4. 生图指令编译（确定性拼装，禁即兴）

指令由脚本从 manifest + 主题冻结产物拼装，分节模板（借鉴 codex `prepare_slide_prompts.py` 的分节法）：

```
## Canvas        16:9 整页幻灯片，2560×1440，无页码无水印
## Deck Goal     deck 主题与受众一句话
## Global Style  统一风格段（主题有 bake_brief 时注入结构化风格圣经 JSON——含
                 visual_direction/palette_rule/typography_bake/uplift/allowed/avoid/
                 layout_blueprints/rendering_constraints；无简报回退散文 + token 色值）
## Uplift 升维手段  六维工具箱（光线/质感/插画/布局/容器/字体，每维都要可见地超越
                 参考图；v4 起内置，回退路径同）
## Style Anchor  内容锚（v4 收紧）：附件图只提供①文字内容与信息层级②配色基调，
                 其余一律不参照；与参考图在构图或质感上趋同视为失败。
                 --anchor none 时整节省略（纯文生图臂）
## Text          本页全部文字逐字注入（标题/要点分行列出，标注"文字必须逐字渲染，不得增删改"；
                 furniture 角色（页眉/页码等 chrome）不注入——Constraints 明禁渲染；
                 有简报时补"文字视觉化改造"授权——标题按 typography_bake 重构/材质化）
## Layout        页角色声明 + 角色蓝图（有简报时，信息结构纪律非复刻纪律）+ 构图授权行
                 + 本页构图指令（页计划表的呈现方案）
## Constraints   通用约束（中文清晰不乱码、不出血、不渲染页码）+ 通用反 AI-slop 清单
                 + 主题 avoid 清单（有简报时）
```

- 文字段 100% 逐字来自 manifest（harness 可校验为精确子串）——"指令正确则无幻觉"的工程化保证在**编译**环节，不在模型自觉；
- 可选的生成后 vision 对照抽查（图里文字 vs manifest）作为抽检手段，非常规门禁——用户已判断当前生图能力在指令正确时可信；
- 跨页概念（"上文提到的六点"类）必须展开为显式清单注入（codex 的 deck_context/local_context 纪律）；
- **分工口径**（2026-09-22 用户意见）：脚本只管确定性骨架（Text/Canvas/Constraints 的逐字拼装）；Layout 段与风格段的写法是 agent 手艺层——不同构图谱系（巨字宣言/数据英雄/网格矩阵/轴与节点/图文证据/裂屏对开）对生图模型的指令策略不同，写这两段前必须查询 `skills/html-pptx/references/bake-prompts.md`（按谱系策略、文字量纪律、失败模式对策）。

## 5. 与既有机制的关系

- **插画模式不动**：页内槽位继续走 Step 5.5；烙入 pass 只处理 `data-render-mode` 目标页；
- **编辑器行为**：烙入页图像走既有换图流（上传替换置 `uploaded`，用户真图永不被 AI 覆盖）；文字编辑锁，提供"源层编辑"专用入口（详见 `editor-tri-view.md`）；
- **PPTX 导出**：烙入页 PNG 在导出管线中满幅直通，跳过 PDF 环节（见 `pptx-export-svg.md` §2）；
- **全 deck 图片化的诉求**由"全选所有页烙入"满足，文件形态不变（单 HTML + assets/）。

## 6. 验收标准

- 契约 v7：烙入页三要素（`data-render-mode` / 页面级槽位三属性 / `.baked-source` 源层）静态可校验，check-images 扩展零误报；
- 源层保留：烙入前后页面文本提取结果一致；还原源层（摘除 img 与 render-mode）即完整回退；
- 指令合规：生图指令文本段是 manifest 文本的精确子串（harness 校验）；
- 混合 deck 过 harness 回归：滚动/缩放/章节跳转/保存幂等/编辑器打开烙入页文字锁 + 源层可编辑 + stale 徽标翻转；
- 失败回退路径演练：模拟生图失败，页面保持 HTML 形态且交付说明列明。
