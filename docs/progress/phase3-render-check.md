# Phase 3 · 编辑器 / 骨架渲染校验（2026-11-12）

> 对应前文 Phase 1（生成侧角色令牌）+ Phase 2（编辑侧角色下拉）的**实机渲染验收**。
> 用户诉求："请跑一次编辑器渲染校验"。结论：**生成侧 PASS / 编辑侧 PASS**。

## 一、为什么需要这次校验

Phase 1/2 的结论都建立在"静态代码审查 + 数值换算"上：`.t-* { font-size: max(var(--t-*), floor) }`
是否真的在浏览器里生效、主题 `:root` 覆盖是否真的被消费、编辑器角色下拉是否真的
能改字且**不写回裸 `font-size`**——这些必须靠真实 Chromium 计算样式才能证实。
尤其要验证用户拍板的核心命题：**字号下限由设计层结构性锁定，不需要后拦截门禁**。

## 二、校验环境与方法

| 项 | 值 |
|---|---|
| 浏览器 | 系统 Chrome `C:/Program Files/Google/Chrome/Application/chrome.exe` |
| 驱动 | `playwright-core@1.65.0`（装入托管 Node workspace，复用系统 Chrome，不下载 Chromium） |
| 脚本 | `docs/progress/render-check/run.js` |
| 数据 | `docs/progress/render-check/report.json` |
| 画布 | 1920×1080（骨架基准），编辑器 1600×900 |

方法要点：
1. **每个场景开一个全新 page** 加载真实 `skills/SlideForge/assets/skeleton.html`，
   再注入**单个**主题 `:root` 覆盖——避免上一版脚本 `addStyleTag` 累积导致的串味。
2. 对示例页未用到的 4 个角色（`t-subhead/t-caption/t-meta/t-vertical`）注入离屏探针，
   凑齐 7 个角色的计算字号（`getComputedStyle().fontSize`）。
3. **恶意令牌场景（hostile）**：把所有 `--t-*` 强行设成 4–8px，
   验证 `max()` 是否把它们全部顶回地板——这是"设计层规避"最硬的证据。
4. 编辑器侧：载入一个自建 `sample-deck.html`，**先手工埋一个历史裸写 `font-size:37px`**，
   再选中元素并切换角色，验证 `applyRole()` 会清除它。

> 环境坑（已记入 memory）：本会话 shell shim 缺 `dirname/head/tail/ls`，系统 `npm`
> 的 shebang 需要 `bash` 也不可用。解法是用托管 Node 直接调
> `.../node_modules/npm/bin/npm-cli.js install --prefix <workspace>`，且命令里不接管道。

## 三、生成侧结果（px@1920×1080）

| 场景 | display | heading | subhead | body | caption | meta | vertical | 预期 | 地板违规 |
|---|---|---|---|---|---|---|---|---|---|
| 骨架默认 | 96 | 64 | 40 | 28 | 18 | 15 | 96 | ✅ 全中 | 0 |
| B1 瑞士 | **176** | 64 | 40 | **35** | 18 | 15 | 96 | ✅ | 0 |
| C3 终端 | **104** | 64 | 40 | **35** | 18 | 15 | 96 | ✅ | 0 |
| E5 构成 | **128** | 64 | 40 | **35** | 18 | 15 | 96 | ✅ | 0 |
| H1 手卷 | **92** | 64 | 40 | **35** | 18 | 15 | **118** | ✅ | 0 |
| **恶意令牌** | **64** | **32** | **24** | **18** | **16** | **14** | **64** | ✅ 全部夹回地板 | 0 |

- 4 主题 `display` 令牌源（176/104/128/92）**均被真实消费**，主题差异化成立；
  `body` 统一 35、其余角色继承骨架默认，与 theme.md 的 `type_scale` 声明逐字一致。
- **恶意令牌场景是关键**：即使主题把正文压到 4px、meta 压到 6px，
  浏览器算出来仍是 18px / 14px——`max()` 地板结构性不可突破。
  → 证明无需 `sync-themes.mjs` 之类的后拦截门禁，符合"能设计层规避就不加门禁"的决策。
- 视觉复核：`skeleton-b1.png`（最大 176px 巨字）横向未溢出画布；
  `skeleton-hostile.png` 标题仍清晰可读。

## 四、编辑侧结果

| 检查项 | 结果 |
|---|---|
| `#stRole` 存在 | ✅ |
| 选项 | `["",t-display,t-heading,t-subhead,t-body,t-caption,t-meta,t-vertical]`（默认 + 7 角色） |
| `applyRole` 类型 / `ROLE_CLASSES` | `function` / 7 角色数组，与骨架 `.t-*` 一一对应 |
| px 数字框 | 已不存在（截图工具栏只剩"字体 / 大·章节 / 色板 / 对齐"） |
| 角色切换实测 | `t-display (96px)` → 选 `t-heading` → `t-heading (64px)` ✅ |
| **历史裸写迁移** | 预埋 `font-size:37px` → 切换后 `inlineFont` 变 `""` ✅ 自动清除 |
| 旧角色清理 | `t-display` 被移除、`t-heading` 被加上 ✅ |
| 脏标记 | 编辑器顶栏"保存(未保存)"亮起，序列化链路正常 ✅ |

`editor-after-role-switch.png` 可见：选中框、标题缩小、状态栏"选中: h1 · 文本"，
且工具栏显示的是**角色下拉"大·章节"**而非旧的 `−[px]＋` 数字框。

控制台仅有 2 条 `file://` 下探测 `/api/health` 的 CORS 报错——这是编辑器在
**独立静态打开态**探测本地桥接服务是否正常，属既有降级行为，与角色系统无关。

## 五、过程中修正的校验脚本自身缺陷（非产品缺陷）

1. 首版 `measure()` 查询 `.display`/`.body`，漏了 `t-` 前缀 → 7 个角色全返回 `null`。
2. 首版对每个主题 `addStyleTag` 累积注入，后测主题会叠加前面主题的 `:root` → 改用每场景全新 page。
3. `page.evaluate` 里的 `ensureProbes` 引用了 Node 侧 `ROLES` → 改为显式传参。

以上只影响校验脚本，未改动任何产品文件。修正后 `run.js` 全绿。

## 六、产物清单（`docs/progress/render-check/`）

- `run.js` — 可重跑的校验脚本
- `report.json` — 结构化结果 + `verdict: {generator:PASS, editor:PASS}`
- `sample-deck.html` — 编辑器用的最小 deck 夹具
- `skeleton-{default,b1,c3,e5,h1,hostile}.png` — 6 张生成侧渲染截图
- `editor-{loaded,after-role-switch}.png` — 2 张编辑器截图

## 七、结论与遗留

- **Phase 1 + Phase 2 的角色令牌系统通过实机渲染验收**，两条核心不变量都成立：
  ① 文字字号只由 `.t-*` 角色决定；② 下限由 `max()` 结构性锁定，任何主题令牌都突破不了。
- 未发现回归。视觉上唯一可提的是 `skeleton-default.png` 封面标题下有一条细线，
  已核对为骨架既有 `data-anim="chars"` 拆字入场动画的中间帧（每场景独立 page、
  截图时刻不同，故仅一张出现）；`.t-*` 只设 `font-size`/`line-height`，不可能产生该线，与本次改动无关。
- 本轮**未提交**任何改动（用户只要求跑校验 + 落档）。`check-capacity.py`（文本容器溢出测量）
  仍是唯一保留的正当门禁，本次未触碰。
