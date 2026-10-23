# 0918 · 三风格 v2 重制 + 插画 pass（效果验收包）

> 目的：用新技能（v1.5，skeleton v3）重制三个旧风格 deck，供用户对比验收新旧效果。口径：高密度 + 丰富动效 + AI 插画 + 复杂信息图 + 复杂图表。

## 产物（新旧对照）

| 风格 | 旧（v0 骨架） | 新（skeleton v3） | 主题 |
|---|---|---|---|
| 技术分享 | `tests/decks/tech-ikb/` | `tests/decks/tech-ikb-v2/`（13 页） | B1 克莱因蓝 |
| 人文读书 | `tests/decks/culture-kraft/` | `tests/decks/culture-kraft-v2/`（13 页） | A4 牛皮纸 |
| 发布会 | `tests/decks/launch-mono/` | `tests/decks/launch-mono-v2/`（13 页） | A1 墨水经典 |

每个 v2 deck：高密度档；华丽动效（chars 拆字封面、count-up、draw-line、fill-bar、ambience ≤2/页，注意力预算内）；≥4 个信息图结构族 + 嵌套/标注组合用法；≥2 种图表（数据可溯源，演示数据均在页面上显式标注"示例数据"）；2 个图位走完 Step 5.5 插画 pass——**6/6 槽位真实 AI 生图成功、零回退**（oai生图 2K/medium，风格段按主题缺省推导：B1 瑞士扁平矢量 / A4 牛皮纸剪纸排线 / A1 双色墨绘静物）。

## 验收结果

- 三 deck 骨架与 skeleton v3 逐字节一致（仅 SLOT 差异）；Playwright 逐页零溢出、零意外重叠、填充度 ≥60%；reduced-motion 全文可读；
- 插画 pass 后 `check-images.mjs --mode illustration` 三个 deck 均零错误；渲染确认图片落位无布局偏移；
- 三 deck 已加入 harness `DECKS` 回归列表；**harness 31/31 PASS**。

## 顺带修复（harness 白名单）

v2 deck 首次进入往返回归暴露了 harness 规范化白名单的盲区——skeleton v3 运行时给 `[data-anim]` 写 `--i` 触发 CSSOM 重序列化，产生等价但字节不同的简写展开：`flex:1`↔`flex:1 1 0%`、`flex:none`↔`0 0 auto`、`0`↔`0px/0%`、盒简写去重、`repeat(3,1fr)`↔`repeat(3, 1fr)`、`font-feature-settings` 单引号↔`&quot;`。修复 `tests/harness/run_e2e.py` `_canon_style`：实体还原提前到分号切分之前（`&quot;` 自身含分号）、零值单位用后环视（`\b` 对 `%` 不成立）。产物本身无问题，纯测试基础设施修复。
