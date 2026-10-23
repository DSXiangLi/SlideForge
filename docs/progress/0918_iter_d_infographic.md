# 0918 · 迭代 D：信息图系统 v2

依据：`docs/design/infographic-system.md`（2026-09-18 修订意见 3 + antv-infographic 架构调研）。目标：components.md 从 12 个平铺组件重构为"结构族 × Item 皮肤 × 参数变体"正交模型；数据形态匹配从散文门槛升级为可静态校验的断言；契约同步引入信息图分层条款。

## 变更

| 文件 | 变更 |
|---|---|
| `skills/html-pptx/references/editing-contract.md` | 契约 v4（契约先行）：新增"信息图组件的分层"节——Item 文字（label/desc/value）`data-editable`、结构装饰（连线/箭头/圆点/几何）`data-editable-skip`、`data-stylize` 图形必伴 skip、结构变更（增删 Item/换族/改字段）走 AI 流程；标注修饰件文字 editable、引线 skip；嵌套各层按各自规则标记。引入生成侧辅助标记 `data-ig="族-骨架"` / `data-ig-skin="皮肤"` / `data-ig-item`（编辑器不消费、序列化原样保留） |
| `skills/html-pptx/references/components.md` | 重写为 v2：§0 三步选型（内容关系→结构族→皮肤）+ 数据形态自证清单 + 6 条可静态校验断言；§1 六结构族（list/sequence/compare/hierarchy/relation/chart），每族按七件精简版组织（身份/骨架表含 ASCII 构图与 CSS 要点/合法项数区间/密度适配/可编辑分层/反模式/验收要点）；§2 六 Item 皮肤（bare/card/badge/ribbon/stat/icon-line）；§3 族×皮肤适配矩阵（含 stat×hierarchy、ribbon×hierarchy 等禁止组合）；§4 参数变体推导规则（密度/方向/项数，不枚举）；§5 组合与嵌套（一页一主体、嵌套一层限 chart 小图、容量分摊、标注=文字不进几何）；§6 风格化接口（G3 texture → data-stylize）；§7 Callout/Ghost/Highlight 归"页面修饰件"保留；§8 v1→v2 十二组件归类映射全量落实；§9 text_policy 保留；§10 新族/新皮肤入库走七件规范 |
| `skills/html-pptx/SKILL.md` | Step 4 信息图条目改为三步选型 + 数据形态自证清单（项数区间、binary 恰好两项、族×皮肤白名单），自证不过换族或拆页 |
| `tests/decks/infographic-d1/` | 新增信息图密集验收 deck（7 页，D1 奶油物语主题，示例数据口径已标注）：list/grid×stat（含 count-up）、sequence/steps×badge（第 3 步 Item 内嵌 chart-progress 小图，fill-bar 入场）、compare/binary-cols×card（恰好 2 项）、hierarchy/concentric×bare（3 层）、relation/circle-loop×bare（4 节点 + 数值旗标标注修饰件，引线 draw-line）、Callout 收尾。框架层由脚本从 skeleton.html 逐字派生并自检一致（script 逐字节相同，style 仅 theme token 槽位不同） |
| `tests/harness/run_e2e.py` | DECKS 增加 infographic-d1（T1 往返幂等回归）；BOOLEAN_ATTRS 白名单新增 `data-ig-item`（无值 data 属性的解析器序列化规范化）；新增 T15：族×皮肤白名单与项数区间硬断言（binary==2、concentric 2–4、circle-loop 3–5 等，IG_RANGES/IG_ALLOWED 镜像 components.md）、Item 必含可编辑文字、容器不标 data-editable、嵌套 chart 分层（几何 skip / 标签数值 editable）、标注旗标 editable + 引线 skip、装饰抽查（连接线/VS 徽章/圆环/箭头）、flat 主题无 data-stylize、编辑 Item 文字后保存产物净化且辅助标记保留、重载逐字节幂等 |
| `docs/design/infographic-system.md` | 状态：待评审 → 已实施（迭代 D） |
| `docs/skill-roadmap.md` | §四未来规划表加状态列：主题 Schema / 动效 v2 / 信息图 v2 标注已完成（迭代 B/C/D） |
| `docs/design/README.md` | 文档地图 infographic-system 行标注（迭代 D 已实施） |
| `docs/progress/README.md` | 索引补本迭代 |
| `AGENTS.md` | components.md v2、契约 v4、新测试 deck 与 T15 描述同步 |

## 验收

- 新 deck 框架层自检：script 块与 skeleton.html 逐字节一致；style 块剥离 theme token 槽位后逐字一致（构建脚本内 assert）。
- `python3 tests/harness/run_e2e.py`：**26/26 PASS**（原 24 项 + T1-infographic-d1 + T15；9 个存量 deck 回归全绿）。Chromium 145 headless。

## 偏离记录（deviation）

1. **引入 `data-ig` / `data-ig-skin` / `data-ig-item` 辅助标记**：规格 §8 要求"适配矩阵静态可验、项数区间机器可查"，但规格未定义落码形态——没有标记就无法在产物 HTML 上静态断言。标记为生成侧自检元数据，编辑器不消费、序列化原样保留（契约 v4 第 4 条声明），不增加编辑器负担。
2. **harness 白名单新增 `data-ig-item`**：无值 data 属性经 HTML parser 序列化为 `data-ig-item=""`，与既有 `data-editable` 等同属一次性解析规范化，非编辑器行为变更。
3. **deck 页头装饰用 paper-tint 圆角块替代 hairline**：D1 主题 G4 声明"不用分割线，用留白与底色块分区"——页头节奏件按主题 G4 落码，非通用配方变更。
4. **T15 的 IG_RANGES / IG_ALLOWED 是 components.md §1/§3 的镜像**：双源是有意为之（harness 不能解析 md），新增族/皮肤/骨架时两端同步的义务已写进 harness 注释与 components.md §10。
5. **`chart-progress` 嵌套小图不带 `data-ig-skin`**：chart 族不参与皮肤矩阵（components.md §1.6/§3），T15 断言其必须无 skin 标记。

## 明确不做

- geo 族与 3D 透视结构缓建（规格 §9）；
- 存量 deck（infographic-b2 等 v1 组件写法）不追溯重构——v2 是生成侧新产物的规范，旧 deck 仍是合法契约产物；
- 不做页面内结构编辑器（规格 §9），结构变更走 AI 流程的边界声明不变；
- 不做 git commit。
