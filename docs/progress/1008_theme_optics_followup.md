# 1008 · 主题光学轴跟进：F2 差异化 + flicker-in + PPTX 适配实证

> 接续 [1007_theme_optical_axes.md](1007_theme_optical_axes.md)。触发：用户验收三点——① C3/F2 观感过近；② 光与纵深法则要落到技能（不止 themes.md）；③ 新手法须确认 PPTX 适配程度；④ README 精选收敛 12 组。

## 落地清单

- **F2 霓虹夜行差异化重构**：基底 accent 电青→霓紫（#9E8CFF，全库唯一紫色系）；世界锐化"雨后夜街"+ 新母题 `.mt-neo-refl`（雨后倒影：副本 scaleY(-1)+渐隐 mask+blur(1px)）；变体 霓紫(基底)/电青/品红（撤荧绿，与 C3 绿拉开）；签名动效改 flicker-in。gallery/sampler 的 theme-f2 页同步重构并重截图（`assets/theme-sampler/p23-f2.png` 紫化，探针：紫调 1.4%+、青绿残留 0）。
- **skeleton v7.6**：enter 族新增 `flicker-in` 通电点亮（inview 一次性 steps 抖动后常亮；reduced-motion/print 降级配套）；修复其 reduced-motion 关停规则的特异性 bug（(0,2,0) 输 (0,4,0) 已改同特异性后置）。gallery/sampler 内嵌骨架同步补入（meta 版本如实保留 4/7.4，注释注明 v7.6 词汇补丁）。
- **motion.md**：flicker-in 入 enter 族（主题限定：发光体系主题）；词汇表计数订正为 8 族 46 recipe（原 39 已滞后于 v7 增补）。评估结论：light/amb 族已覆盖 F1/F3，仅此一款真实缺口，八族结构不动。
- **components.md §12 硬规则 6「光学容器」**：玻璃叠层/发光边缘/亮度阶梯薄面豁免四档平涂与填充描边互斥；四纪律（主题显式声明/发光单色/阴影带色相/每页 1–2 主轴）。光与纵深法则至此落到技能规范层。
- **PPTX 双轨适配实证**：/tmp 副本 theme-sampler 24 页 `--track both` 全过（274.9s）：保真轨 f1/f2/f3 = 95.2/95.2/99.1 分，backdrop-filter/发光/渐变字/暗角全存活；可编辑轨文本零烙图，视觉层按既定契约降级（f1 玻璃卡→L5 烙图、f2 光晕丢失、f3 近无损）。结论：f1/f2 主用保真轨交付，f3 双轨皆可。
- **README/README_ZH**：样张精选 15→12（删 c4/e9/e11 行；f2 图注改霓紫）。
- **文档**：theme-optical-axes.md 增 §五修订记录；验收文档追加 F2 差异化/导出适配证据。

## 验收

- sync-themes 幂等全绿（含并行会话新增 b1/e12 bake_brief）。
- check-render：sampler ALL PASS；gallery 零新增失败。
- flicker-in 冒烟：非 reduce 播完 opacity=1；reduce 静止常亮。
- run_e2e 全量回归：**59/59 PASS 0 FAIL**（2026-10-08 第二轮，wall 1206.718s；覆盖 skeleton v7.6 + editor.html 同步 + gallery/sampler 改动；T18 56 页、T9 24 卡、T13/T19–T22 动效全绿）。

## 遗留

- gallery 132 项预存小字失败仍为存量；C3 辉光在 gallery 样张页的变化量（0.6%）受页面面积所限，sampler 页 4.66% 为代表性证据。
