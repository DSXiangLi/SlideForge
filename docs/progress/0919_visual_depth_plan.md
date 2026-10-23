# 开工计划：视觉纵深 F1–F6（2026-09-19）

> 依据：`../design/visual-depth.md`（高级感 8 要素 / 组件库双形态 / 动效词汇库 8 族）、`../research/v2-effect-diagnosis.md`（问题定位）
> 目标：六期全部完成后，重制三个风格 deck（v3），用户对比 v0/v2/v3 验收。
> 纪律不变：契约先行、骨架升级带版本号、每期 harness 全绿、枚举项过七件规范、不做 git commit。

## 里程碑表

| 期 | 内容 | 主要产出 | 验收 |
|---|---|---|---|
| **F1** 高级感要素落位 | 归藏 8 要素进系统：① themes.md 每主题补 accent 用量预算/字重映射/字号对比档；② typography.md 硬化（字重倒挂量化、≥8:1 对比）；③ skeleton v4：刊头家具槽位（页眉/页脚/页码）+ 背景配给机制（hero/封面特权）；④ 存量 16 主题 G3 质感填充（A4 纸纹、C2 柔光等） | themes.md / typography.md / skeleton v4 / sync-themes.mjs 适配 | schema 校验过；骨架一致性；harness 绿 |
| **F2** 组件库画廊 | ① components.md 升"6 构图谱系"叙述（巨字宣言/数据英雄/网格矩阵/轴与节点/图文证据/裂屏对开 + 张力来源）；② 容器规格落地（四档明度/单焦点/直角纪律）；③ `skills/html-pptx/gallery/`：每结构族×皮肤一页高复杂度实例（连接件层次/数据墨迹/标注/材质） | components.md v3 + gallery/index.html | 画廊过渲染校验+标记合规；进 harness DECKS |
| **F3** 图表扩类型 + 标注层 | charts.md 扩：堆叠/分组柱、面积、瀑布、散点/气泡、雷达、斜率、漏斗、热力表格；**每配方带标注层规格**（参考线/区间带/数值直标/注释旗标）；画廊补图表实例页 | charts.md v2 + gallery 图表页 | 同上 |
| **F4** 动效词汇库 8 族 | skeleton v5：scroll 族（read-progress 纯 CSS scroll-timeline；parallax/scrub/pin-stack/cover-uncover）、pointer tracker（spotlight/tilt/magnetic/parallax）、文本引擎扩展（mask-lines/typewriter/scramble 主题限定）、新 CSS 族（blur-in/scale-pop/wipe-clip/rise-in/persp-in/fill-bar-y/ring/dash-flow/flow-dot/light-* 系）；motion.md v3（8 族 39 recipe + 五层启用矩阵）；editor 净化同步；面板 motion 选项改五层矩阵 | skeleton v5 / motion.md v3 / editor v2.1 / 契约 v6 | 新 recipe 全生命周期 harness 用例（T19/T20）；reduced-motion；编辑往返幂等 |
| **F5** canvas 粒子 FX | 独立评估后落地：canvas FX runtime（`data-fx`，密度上限烧死，in-view 生命周期，reduced-motion 不启动，主题 G5 声明启用，默认关） | skeleton v5.1 或独立结论 | 若做：粒子 deck 回归；若不做：记录结论 |
| **F6** 三风格 deck 重制验收 | tech-ikb-v3 / culture-kraft-v3 / launch-mono-v3：高密度 + 华丽档（五层矩阵）+ 画廊级信息图/图表 + AI 插画 pass（oai生图） | 三个 v3 deck | 全部自验（骨架一致/零溢出/check-images/插画校验）+ harness 全绿 → 交付用户对比验收 |

## 关键依赖与并行性

- F2/F3 依赖 F1（容器规格依赖主题 accent 预算；画廊用新骨架）；F4 独立但因共享 harness/skeleton 串行执行；
- 顺序：**F1 → F2 → F3 → F4 → F5 → F6**，每期结束 harness 全绿再进下一期；
- 嵌入协议、编辑器既有功能、存量 deck 回归全程不许破。

## 进度记录

- [x] F1 ✅ 2026-09-19：themes.md 16 主题补 accent 预算/对比档/字重映射 + G3 立场必填填充；typography.md 硬化；skeleton v4（刊头家具 + 背景配给制）；editor v2.0；sync 校验扩展幂等；harness 31/31 绿（详见 `0919_iter_f1.md`）
- [x] F2 ✅ 2026-09-19：components.md v3（§11 构图谱系 6 谱系 + §12 容器规格四档明度/单焦点）；gallery/index.html 15 页多主题 sampler（6 族 × 6 皮肤全覆盖 + 嵌套 + 修饰件）；harness 33/33 绿（新增 T1-components-gallery 往返 + T18 零溢出零重叠/镜像表/谱系节奏校验）（详见 `0919_iter_f2.md`）
- [x] F3 ✅ 2026-09-19：charts.md v2（14 配方 = 基础五 + 扩展九：堆叠/分组柱、面积、瀑布、散点·气泡、雷达、斜率、定量漏斗、热力表格；每配方带标注层规格——参考线/区间带/数值直标/注释旗标）；系列色 8 档推导（1–4 冻结 + 5–8 明暗交错续排，themes.md 同步）；gallery 15→24 页（9 页图表实例，主题错开、谱系最长连续 2 页）；T18 扩展（10 图表根覆盖/分层 + 瀑布水位/雷达顶点/斜率端点几何抽验）；harness 33/33 绿（详见 `0919_iter_f3.md`）
- [x] F4 ✅ 2026-09-19：skeleton v5（触发器层：pointer tracker 只写 CSS 变量 + scroll 族——read-progress 纯 CSS scroll-timeline、parallax/scrub/scrub-draw 因 CSS view() 在 overflow:hidden 画布下绑错滚动容器而改 JS 驱动 --sp 进度变量（偏离记录见 iter_f4）+ cover/stack 页间 sticky + enter/text/data/link/amb/light 族补全）；motion.md v3（8 族 39 recipe + 五层启用矩阵替换三档 + 反目录覆盖纪律）；契约 v6（新族净化清单 + freeze 约定 + gradient-flow 编辑态还原本色）；editor v2.1（冻结交互层 + 净化扩展 + 面板 motion 组改五层矩阵、sync-themes 新增 __MOTION_JSON__ 区间）；新建 tests/decks/motion-v5 验收 deck；harness 36/36 绿（新增 T19 全生命周期 + T20 编辑侧）（详见 `0919_iter_f4.md`）
- [x] F5 ✅ 2026-09-19：评估结论先行——三条红线（产物纯净/注意力预算/降级链）全部守住，落地。skeleton v5.1（canvas FX runtime：`data-fx` 声明，4 款效果 constellation/starfield/particle-drift/ascii-field——后者致敬 guizang ascii-bg；密度/数量/速度烧死无参数通道；位图=渲染尺寸×DPR 随 fit() 重配；rAF 绑 in-view 离屏停帧；reduced-motion 不初始化；freeze 扩展停帧+摘除 width/height）；motion.md v3.1（fx 仪式层小节 + 触发器表第五取值 + 降级链第 7 条）；themes.md G5 新增「fx 许可」白名单（16 主题逐套声明，缺省全禁）；契约 v6.1（canvas 净化条款）；editor v2.2（serializeClean 兜底）；motion-v5 deck 加 2 个 fx 实例；harness 37/37 绿（新增 T21 fx 全生命周期）（详见 `0919_iter_f5.md`）
- [x] F6 ✅ 2026-09-19：三风格 v3 重制（tech-ikb-v3 / culture-kraft-v3 / launch-mono-v3，各 14 页，6 谱系全用 + 华丽档五层全开 + 画廊级信息图/图表）+ 插画 pass 6/6 真实生图零回退（oai生图 2K/medium，B1 瑞士扁平矢量 / A4 牛皮纸剪纸排线 / A1 双色墨绘）；check-images 插画模式三 deck 全过；harness **40/40 绿**（v3 三代同题入 T1 回归）（详见 `0919_iter_f6.md`）——**待用户人工验收三代对比**
