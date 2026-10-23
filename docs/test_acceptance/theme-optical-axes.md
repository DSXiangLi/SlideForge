# 验收证据：主题光学轴扩展（F 系入库 + C3/E5 升级）

> 日期：2026-10-07 · 设计：`../design/theme-optical-axes.md` · 全部截图 1920×1080、Playwright reduced-motion 渲染

## 机器门槛

- `node skills/html-pptx/scripts/sync-themes.mjs`：24 套主题 Schema 校验全绿（G0–G9 字段齐全、两两七层 diff ≥3、分化声明逐层核验为真、F 系 focus 组合 {G3,G4}/{G4,G9}/{G1,G3} 无 accent 撞车、变体六色合法），editor.html 面板数据已同步。
- `check-render.py`：theme-sampler 24 页 **ALL PASS**；gallery 56 页中五个目标页（theme-c3/e5/f1/f2/f3）PASS，其余 132 项失败为 HEAD 预存（组件页小字），与基线逐条一致、**零新增**。
- 两 deck 全页 `data-content-hash` 经 `extract-manifest.py --write-hashes` 写回一致。
- `run_e2e.py` 全量回归：**59 项 59 PASS 0 FAIL**（2026-10-07，wall 999.293s）——含 T18 画廊（56 页零溢出零重叠、谱系节奏与几何抽验全过）与 T9 面板（24 张主题卡与注入 JSON 一致）。

## 截图清单

```
docs/test_acceptance/theme-optical-axes/
├── before/gallery/{theme-c3,theme-e5}.png   # 升级前基线
├── before/sampler/{theme-c3,theme-e5}.png
├── after/gallery/{theme-c3,theme-e5,theme-f1,theme-f2,theme-f3}.png
└── after/sampler/{theme-c3,theme-e5,theme-f1,theme-f2,theme-f3}.png
```

README 资产联动：`assets/theme-sampler/p05-c3.png`、`p14-e5.png` 已用升级后渲染覆盖；新增 `p22-f1.png`、`p23-f2.png`、`p24-f3.png`。

## 效果量化（PIL 像素探针 + ImageChops diff）

| 验证点 | 口径 | 结果 |
|---|---|---|
| F1 光斑存在且透过玻璃卡 | 蓝紫调（b>r+25）像素覆盖 | 命中，覆盖区横跨玻璃卡阵（x 120–1755）；光斑区与非光斑区纸面色差实测存在 |
| F1 玻璃半透明 | 卡面探针 vs 纯纸面 | 卡面 rgb(227,229,235) ≠ 纸面 rgb(238,241,247)（半透明渐变底成立） |
| F2 发光严格单色 | 电青像素占比 + 杂色扫描 | 0.63% 电青像素、零红/零绿杂色 |
| F2 rim-glow 成立 | 灯管卡边缘探针 | 卡缘 rgb(5,15,25) 带青调 vs 背景 rgb(5,7,13) |
| F3 地平线色带（封面） | 橙调像素 | gallery 封面 3.06%、全宽压底（y→1077） |
| F3 内容页无色带（纪律） | sampler 页橙调像素 | 仅 0.07% 且集中在焦点数字（x 150–294, y 624–663） |
| C3 升级前后差异 | 像素 diff >16/255 | sampler **4.66%**、gallery 0.61%（后者页面面积小；变化 100% 集中在 caret 光晕带与终端窗口缘，空白区 0.00%） |
| E5 升级前后差异 | 像素 diff >16/255 | gallery **5.06%**（强变化 4.08%）、sampler **3.04%**（楔块 + 双印错位带） |

## 结论

- 四根空缺手法轴全部入库并有渲染实证：毛玻璃（F1）、发光体系（F2）、彩色平滑渐变 + 渐变字 + 暗角（F3）、多层柔和投影（F1 G4）。
- C3「磷光无像素发光」名实落差修复；E5 石印肌理全页化 + 红楔词汇兑现。
- 手法纪律条款（单色发光/阴影带色相/玻璃六件套/每页 1–2 主轴）已写入各主题 G4/G9 禁忌。

## 追加验收（2026-10-08：F2 差异化 + motion + PPTX 适配）

**F2 差异化重构**（应用户目检"C3 与 F2 太像"）：基底电青→霓紫，新增 `.mt-neo-refl` 雨后倒影母题，签名动效 flicker-in（skeleton v7.6）。探针复核（after 图已重截）：gallery/sampler 的 f2 页紫调像素 1.47%/1.38%，电青与绿残留 0.00%；倒影区淡紫渐隐成立（贴题最强、向下衰减）；flicker-in 冒烟 PASS（非 reduce 模式播完 opacity==1，reduce 模式静止常亮——skeleton 特异性 bug 已修）。

**motion 结论**：light/amb 族既有词汇覆盖 F1/F3，仅补 flicker-in 一款（enter 族，主题限定发光体系），八族结构不动；motion.md 现为 8 族 46 recipe。

**PPTX 双轨适配实证**（/tmp 副本跑 theme-sampler 24 页 `--track both`，274.9s，exit 0，未碰原件）：

| 页 | 保真轨保真分 | 保真轨关键效果 | 可编辑轨（text_coverage=1.0） |
|---|---|---|---|
| f1 浮光玻璃 (p22) | 95.202 | backdrop-filter 存活：光斑透玻璃可见 | 玻璃卡→L5 无字烙图（7 枚）；aura 质感→页底图；文字全原生可编辑 |
| f2 霓虹夜行 (p23) | 95.224 | 发光存活轻微衰减；倒影带渲染 | 光晕丢失（记 uncovered），原生紫字保留；灯管卡→圆角矩形+描边；倒影烙图存活 |
| f3 暮色长镜 (p24) | 99.058 | 薄面/受光线/accent 数字逐像素一致 | 近乎无损：薄面→5 个 alpha 形状，文字全原生（该主题与 PPTX 原生模型天然兼容） |

结论：光学轴主题**保真轨均可交付**；可编辑轨的视觉折损与管线既定契约一致（文本永不烙图）。交付建议：f1/f2 主题 deck 主用保真轨（deck-vector.pptx），f3 双轨皆可。

**README 精选收敛**：样张表 15→12 组（c3/e1/e2/c1/e7/e6/c2/e5/e10/f1/f2/f3），f2 图注改霓紫。
