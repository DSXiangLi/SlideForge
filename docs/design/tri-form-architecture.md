# 三形态架构总览：HTML / 整页生图 / PPTX 导出

> 状态：待评审 · 2026-09-21
> 依据：2026-09-21 用户"上下兼容"两轮设计讨论（整页烙入为唯一生图形态、SVG 中间层、编辑器三态对比、转换即技能）
> 取代：`compat-roadmap.md`（规划级）。本文档与三份子文档构成实施级设计：
> - `page-render-mode.md`——子技能 A：整页生图（向上兼容）
> - `pptx-export-svg.md`——子技能 B：HTML→PPTX 导出（向下兼容）
> - `editor-tri-view.md`——编辑器 v3：三态工作台与翻转对比

## 1. 三形态的角色

| 形态 | 角色 | 核心能力 | 编辑性 |
|---|---|---|---|
| HTML | **唯一真相源 + 主战场** | 快速生成、就地编辑、网页交付 | 文字/图片就地可编辑 |
| 整页图片 | 视觉上限增强层 | 超越 HTML/CSS 的表现力（插画、材质、光影） | 不可编辑（源层保留，可重新翻转） |
| PPTX | 单向交付快照 | 传统行业兼容（PowerPoint 生态） | 不回流；矢量形状可经"转换为形状"微调 |

**翻转（flip）是统一动词**：HTML→整页图片、HTML→PPTX 都是翻转——同一份内容从活的 HTML 凝结为另一种形态。翻转永远从 HTML 出发，永不反向（pptx→HTML 的转换入口是工作流 Step 0 的人工重组 pass，不是同步通道）。

## 2. 转换即技能【架构红线】

两个转换能力都是**技能侧能力**（AI coding agent 执行的 `skills/html-pptx/` 子技能），不是后端功能：

- `tools/edit.py` 只承担静态托管与 git 版本，**永不承担转换**；
- `editor.html` 保持纯静态、无 AI、无转换逻辑，只消费技能产出的 `export/` 产物目录；
- 项目整体 = 技能 + 纯静态页面。新增转换能力先进技能（SKILL.md 工作流 + references + scripts），不进任何常驻服务。

## 3. 总原则：HTML 永远是唯一事实源

与第一性原则 5（文件即真相）一致：整页图片与 pptx 都是**导出态分支**，从 HTML 主分支派生，可再生成；主分支不可替代。任何时候用户回到编辑流程，面对的仍是 HTML deck。烙入页的原 HTML 以源层形式保留在文件内（见 `page-render-mode.md`），保证连"图里文字"都有 HTML 侧的真相锚。

## 4. 公共地基：manifest 与页级 content-hash

### 4.1 中间层 = 派生投影，不是第二真相

不维护平行数据模型（双源同步是幻觉温床）。中间层是**即用即弃的派生物**：

```
index.html（唯一真相，自包含：契约标记 + 源层 + 页级 hash）
  │  extract-manifest.mjs（每次使用重新提取）
  ▼
manifest.json（派生投影）
  ├─→ 生图指令编译（子技能 A：风格段 + HTML 样张锚 + 逐字文本）
  ├─→ PPTX 导出（子技能 B：渲染测量 + 文本逐字回填）
  └─→ 编辑器 stale 检测 / 保真分展示（编辑器 v3）
```

**manifest 提取是渲染后提取，不是静态解析**：`extract-manifest.mjs` 用无头浏览器渲染 deck，逐页遍历 `data-editable` 文本叶，除文本内容外还记录**行数与排版宽度快照**（`line_count` / `advance_width`，供导出端字体漂移检测，见 `pptx-export-svg.md` §4 防线 C）。这保证 manifest 中的文字与版式度量都来自真实渲染，不来自模型转述。

### 4.2 manifest schema（要点）

```json
{
  "deck": { "title": "…", "skeleton_version": "7.2", "extracted_at": "…" },
  "theme": { "id": "…", "variant": "…", "tokens": { "--paper": "…", "--ink": "…", "--accent": "…" } },
  "pages": [
    {
      "slide_id": "cover",
      "render_mode": "html | baked",
      "content_hash": "a3f8c2e19b04",
      "chapter": "…",
      "texts": [
        { "role": "title", "content": "逐字文本", "line_count": 1, "advance_width": 812.5 }
      ],
      "images": [
        { "slot": "page-baked-16x9", "intent": "…", "state": "generated", "src": "assets/page-cover.png" }
      ]
    }
  ]
}
```

`role` 从排版上下文推导（标题/正文/标注层）；`content` 一律逐字取自 DOM，禁止转述。

### 4.3 content-hash 算法

- 输入：`slide_id` + 全部 `data-editable` 规范化文本（文档序拼接）+ 图片槽位三属性 + `render_mode`；
- 规范化：去首尾空白、折叠连续空白；**计算环境统一为"净化后 DOM"语义**——编辑器在保存时的净化产物上计算；extract-manifest 在活体渲染上计算时，必须先 `__pptxMotion.freeze()` + 按契约 §5.4 净化清单还原（拆字 span 还原、运行时 class/变量摘除），保证两侧对同一内容算出同一 hash；
- 算法：SHA-256 取前 12 hex 字符，存于 `<section data-content-hash="…">`；
- **初始写入者**：生成侧在 Step 5 渲染校验通过后运行 extract-manifest 写入全 deck hash（与产物同时交付）；此后编辑器保存时重算（Web Crypto API，异步）；技能侧生图/导出 pass 开头先校验，hash 与产物记录不符的页标记 **stale**。

### 4.4 manifest 的两个落点

- **提取态**：extract-manifest 的 stdout/临时产物，供生图与导出 pass 消费（即用即弃）；
- **交付态**：`export/manifest.json` = 提取态 + 导出报告（每页载体/保真分/导出时 hash/uncovered_glyphs）合并落盘，供编辑器 v3 消费。两者同 schema 不同职责，文件名不混用。

### 4.5 role 推导规则

`texts[].role` 按确定的优先级推导，禁止自由心证：`.masthead/.mastfoot` 内 → `furniture`；标注层口径（12–16px 档且 `data-editable`）→ `annotation`；各页最大字阶标题元素 → `title`；其余 → `body`。推导规则与 typography.md 字号档共用同一阈值表。

### 4.6 防幻觉三硬规则【硬规则】

1. **单向流动**：HTML → 派生物。永不从图片 OCR 回写，永不从 pptx 解析回写。
2. **逐字引用**：生图指令与 PPTX 中的文字从 manifest 字符串原样拷贝，禁止模型转述、重排数字（与"数据真实性"红线同一口径）。
3. **hash 失效检测**：任何编辑翻转 hash → 下游产物（烙入图 / export/ 件 / deck.pptx）标记 stale → 重新翻转前，编辑器对 stale 产物盖"已过期"水印。

## 5. 产物目录约定

```
deck/
  index.html            ← 唯一真相（含烙入页源层与 data-content-hash）
  assets/               ← 图片资产（含整页烙入图，同名替换心智不变）
  fonts/                ← 可选：字体子集 woff2（见 pptx-export-svg.md §4 防线 A）
  export/               ← 导出产物（双轨，C3 起）：deck.pptx（可编辑轨主交付）/
                          deck-vector.pptx + deck.pdf（保真轨）/ page-*.svg / page-*.png /
                          page-*.diff.png / manifest.json（含 export.tracks 逐轨字段）
```

`export/` 同时是编辑器的预览资产来源——转换管线的中间产物天然就是对比视图的展示件，不为预览单独造任何东西。

## 6. 落地路线

```
M1  extract-manifest.mjs + data-content-hash（两子技能共用地基，编辑器 stale 检测依赖）
M2  子技能 A：整页烙入（契约 v7：data-render-mode / 源层 / 页面级槽位；check-images 扩展）
M3  子技能 B：freeze → PDF → SVG → PPTX 管线（含字体防线与降级链）
M4  编辑器 v3：翻转对比 + 导出面板 + stale 闭环 + harness 保真回归
```

每步独立可用：M1 单独即让现有插画模式获得 staleness 检测；M3 不依赖 M2（纯 HTML deck 也可导出）。

## 7. 验收标准（架构级）

- manifest 可重复提取且幂等（同一 deck 两次提取字节一致，`extracted_at` 除外）；
- 编辑任一文字 → 对应页 hash 必翻转；未编辑页 hash 不变；
- 生图指令与导出文本 100% 逐字来自 manifest（harness 校验：指令文件中的文本段是 manifest 文本的精确子串）；
- 主分支 HTML 在两次导出前后字节不变（导出只读主分支，沿用 compat-roadmap 验收）。
