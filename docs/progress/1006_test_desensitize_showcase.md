# 1006 · 测试资产脱敏 + README 可视化展示

## 背景

测试 deck 中含真实业务信息（天弘基金名称、规模数据、口号；smartforge 的赛事 kicker），且根 README 纯文字、缺少"一眼抓人"的展示素材。

## 内容脱敏（入库测试资产全量）

- **cmb 系列严格隔离核验**：`cmb-retail` / `cmb-retail-v2` / `cmb-retail-v3` / `cmb-magazine` / `test_case1` 均已在 `.gitignore` 且 git 零跟踪，未动内容。
- **theme-sampler（21 页）**：先是"天弘→XX"过渡，后按用户要求**整体置换为与基金完全无关的虚构茶饮品牌「山禾集」**——公司介绍、规模叙事（门店 8,637 家 / 会员 6.8 亿 / 售出 2.8 亿杯等虚构数据，数量级与原版一一对应）、经营理念/使命/愿景、标题「一杯好茶 山野作答」、印章/题跋/ghost 字、脚注（标注虚构演示主体）。23 条替换规则全部带精确计数断言。内容量级与布局不变。
- **smartforge-c1 / e8 / smartforge-content.md**：kicker「天弘基金 AI 大赛 · 2026」→「全国高校 AI 创新大赛 · 2026」，出处描述同步改写。
- **pptx_text_metrics.py**：自测断言示例串「天弘」→「示例」（等长，自测通过）。
- 三个改动 deck 的页级 `data-content-hash` 全部用 `extract-manifest.py --write-hashes` 重算写回。

## README 可视化展示（中英双版同步）

新增 `docs/showcase/`（17.7MB，全部 Playwright 真实渲染/录屏）：

- **顶部 hero 动图**：封面入场编排 GIF（`motion/cover-enter.gif`，全宽）
- **主题样张 21→12 精选**：以特色族代表为种子（终端绿/蓝图/浮世绘/星图/孔版/孟菲斯/暗夜植物园）+ 64×36 像素距离贪心 max-min 补满，保证两两区分度最大化；文档标记的撞脸对（A1↔C4、E4↔E5、E6↔E12）各留一套；网格明暗交错排布
- **页面类型实拍 ×6**：smartforge-c1 封面/数据带/流水线/架构 + charts-a3 图表页 + infographic-b2 信息图页
- **动效实拍 GIF ×3**：灯页插画氛围推拉（launch-mono-v3）、打字机+乱码解码（smartforge-c1 closing）、拆字文字引擎（motion-v5）；webm 录屏 → ffmpeg 调色板 GIF，逐帧差分验证有运动
- **AI 插画与整页烙入 ×4**：launch-mono-v3 两页插画槽位 + bake-mix 烙入前后对照
- **尺寸一致性**：静态图全部 1920×1080，GIF 全部 960×540；表格内图片从 `![]()` 改为固定 `width` 的 `<img>` 标签（根因：GitHub 表格列宽按内容自适应，标题长短不一导致显示大小参差）

## 验证

- `check-render.py`：theme-sampler 21 页、smartforge-c1 8 页、smartforge-e8 8 页全部 ALL PASS（零溢出/零重叠）
- 回归：T1 往返幂等（smartforge-c1/e8）+ T22 章节跳转全 PASS
- 全库 grep：tests/ 与 docs/showcase/ 中 天弘/公募/余额宝/蚂蚁/招商 均为 0
- README 全部 26 个图片引用逐一落盘核验

## 遗留说明

- `.gitignore` 注释、`AGENTS.md`、`docs/progress` 历史文档中对"招商银行×天弘基金"的事实性描述**未改**——它们是 cmb 基准 deck 的出处记录，非测试内容；如需一并脱敏另行处理。
- 误触过一次完整 `run_e2e.py`（无 --help 参数设计，直接起全套件），已立即停止；t_imagegen 付费项未执行。
