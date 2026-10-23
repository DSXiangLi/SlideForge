# 整页生图 SOTA 解剖：codex-ppt-skill 与七源横向调研

> 2026-10-07。起因：imagegen v2 流程验收通过，但用户目检封面烙图"太 low"——流程对、视觉不达标。本文解剖 `source/codex-ppt-skill-main/` 的生图体系并横向普查其余七源，定位我们与 SOTA 的**结构性差距**（不是 prompt 措辞差距），给出下一步优化方向。
> 调研纪律：范例是矿不是图——目标是抽象范式回灌 `skills/html-pptx/`，不是复刻 codex。

## 1. codex 的视觉 SOTA 由七个手法构成（系统工程，非神 prompt）

证据：`source/codex-ppt-skill-main/codex-ppt-skill-main/skills/codex-ppt/`。

1. **风格圣经即 prompt**：12 个内置风格各是一份字段固定的 JSON（`references/麦肯锡风格.md:13-118`）——`canvas`（比例/背景/构图/密度双档）、`color_palette`（到 hex + **rule 负向色彩规则**）、`typography`（含 **text_quality** 与标题重构指令）、`layout_patterns`、`layout_blueprints`（位置×数量×标签的语义蓝图）、`visual_elements`（**allowed/avoid 双向白黑名单**）、`rendering_constraints`（15+ 条负向约束，点名"cheap self-media poster feel""default rounded card grid"）。风格描述本身就是可直接注入的生成指令，不是散文。
2. **标题重构（typography reconstruction）是其封面签名单手法**：主标题不是"打出来"而是"设计出来"——细线结构笔划、半空心、断笔、延笔、模块化切割、骨架内嵌网格，且**把主导隐喻融进字体结构本身**（笔划成路径、负空间成漏斗、字身成建筑）。`layout_patterns` 与 `rendering_constraints` 多处明文（`references/麦肯锡风格.md:55-70,95-118`）。
3. **隐喻语义词典**：漏斗=转化、飞轮=增长闭环、断层线=结构变化……每页**恰好一个主导隐喻**（`references/麦肯锡风格.md:51-52`）。
4. **样张门禁 + 样张即参考图 + 方法冻结三段式**：先只生成 1 页代表性内容页给人审批 → 批准后**该样张作为每张后续页的 Image 1 风格参考**（"match style only, do not copy layout"）→ `sample_generation_method`（backend/size/quality/prompt_source）写进 deck_spec 逐页继承，子代理禁换工具禁降级（`docs/outline-style-and-sample.md:113-137`）。
5. **分页 prompt 确定性编译**：`prepare_slide_prompts.py:181-266` 把 deck_spec 编译为固定分节（Canvas/Deck Goal/Global Style 整份 JSON 原样注入/Text/Layout/参考图规则/Universal Constraints），子代理上下文自足。
6. **页角色驱动版式变化**：layout_blueprints 只作候选起点，按 cover/divider/key-message/analysis 选版式、密度双档，明文禁止"每页同构三卡片"——一致性在 DNA 层而非模板层。
7. **质量捷径全灭**：Pillow/SVG/HTML 截图/本地文字叠加全部明文列为 failure mode（`SKILL.md:43`）；局部问题走图像 edit 端点修而非重来。

参数面（次要）：gpt-image-2 默认 2560×1440 quality medium；n=1 不多候选（择优靠门禁+人工 QA，与我们的 rubric 双候选路线不同但兼容）。

## 2. 其余七源的共有收敛与独有手法

调研：`source/{guizang-ppt-skill,ppt-master,baoyu-design,open-design,dashi-ppt-skill,frontend-slides,slide-paipai,demo1}`。

**四源独立收敛的共有手法**（= 行业事实标准，我们必须有）：

- **风格锚定块前置**：guizang 双风格基调段 / ppt-master 每 deck 锁一个 rendering+色锚 / open-design atelier-zero style anchor 永远 prepend / baoyu shared identity block。
- **禁 chrome 条款**："图是素材/整页，不要页眉页脚页码 logo 边框"——我们已有（Constraints 节）。
- **文字双层路由**：按"是否会再编辑"分配图内文字；ppt-master 明文 Layer1 图内限稳定艺术字、Layer2 归原生文本，CJK 三次重生成仍错则回落原生文本——**这是我们烙入模式"文字烧死进图"策略的对照组，其教训是图内文字只放短大字**。
- **槽位/比例先行**：先定落位再生成（我们已有三方绑定）。

**独有但高价值**：

- open-design/Hallmark：**反 AI-slop 禁词清单**（aurora blob、紫青 mesh、浮球、对称居中模板构图、stock 姿势）+ "原图直出 100% 读作 AI，必须后处理（加噪/非对称裁切/调色）"+ enrichment 层级制（纯排版永远是可接受答案）。
- ppt-master：**prompt 词预算**（风格段 80–120 词、总长 150–300 词，禁 tag-soup）+ variant workflow "失败只改一个维度"症状对照表。
- guizang：同组多图一致性后缀（"这是一组图片中的一张，保持相同比例/元素大小/边距/线粗/标注密度"）。
- baoyu：prompt-file-first 可复现记录（我们已有 prompts/ 目录，同构）。

## 3. 我们的差距定位（证据：demos/imagegen-v2/prompts/cover.md）

| 维度 | codex | 我们现状 | 差距性质 |
|---|---|---|---|
| 风格描述 | 结构化 JSON：allowed/avoid、palette rule、typography 重构指令、layout_blueprints、15+ 条 rendering_constraints | 一段散文（Global Style 节约 3 行气质描述 + 3 个 token 色值） | **结构性** |
| 标题处理 | 标题重构为视觉本体，隐喻融进字体结构 | "高对比衬线体、字重庄重、字号极大"——普通大字居中 | **签名单手法缺失** |
| 构图 | 页角色→蓝图库（位置×数量×标签），禁对称居中模板感 | Layout 段散文描述的恰是"居中+上下各一行"的对称模板构图 | **谱系执行层太薄** |
| 负向约束 | 每风格 avoid 清单 + 通用反 slop | 5 行通用 Constraints | **深度不足** |
| 跨页风格锁定 | 样张批准后作后续页 Image 1 参考图 | 每页只用自己 HTML 截图作锚；已批烙图不作后续参考 | **锚链缺失** |
| 隐喻系统 | 语义词典+每页恰一个 | motifs.md 有八类隐喻但未进烙入指令主链路 | **已有资产未接通** |
| 文字策略 | 图内文字全量（与我们烙入同路线） | 同 | 无差距 |
| 样张门禁 | 有 | 有（代表页审批闸门） | 无差距 |

一句话：**我们的管线（门禁/锚定/校验/择优）已不弱于 codex，差的是"指令的内容层"——风格圣经、标题重构、蓝图库、负向约束、锚链。**

## 4. 下一步优化方向（按杠杆排序）

- **D1 风格圣经化（最大杠杆）**：为 themes.md 的 21 个重主题各补一份"可执行风格简报"（bake 专用字段组：visual_direction 英文定调句 / palette rule / typography 重构词汇 / allowed / avoid / layout_blueprints by 页角色 / rendering_constraints）。`compile-bake-prompts.py` 的 Global Style 节从"散文+色值"升级为注入该结构化简报。工作量大，建议先做 Schema + 3 个试点主题（E3 装饰艺术、一个暗黑科技、一个编辑杂志风）跑通再铺量。
- **D2 Layout 段升级**：bake-prompts.md 六构图谱系扩为"页角色 × 蓝图（位置×数量×标签）+ 标题重构词汇表 + 每页恰一个主导隐喻（接通 motifs.md）"；明文禁止"对称居中三行文字"的模板构图出现在封面/章节页。
- **D3 负向约束升级**：通用 Constraints 节并入反 AI-slop 清单（禁 mesh 渐变/aurora/浮球/居中模板构图/自媒体海报感）+ 每主题 avoid 清单进指令。
- **D4 锚链**：代表页审批通过后，把已批烙图作为后续烙入页的**第二参考图**（HTML 截图锚版式与色彩、已批烙图锚生成质感），实现跨页生成风格锁定。adapter 已支持多 `--reference-image`（≤16），零脚本改动。
- **D5 参数策略**：烙入页默认 `--quality high`；风格脱节重 roll 升级 sunburst 的既有纪律不变；封面/扉页可考虑默认 sunburst（成本换一致性，待定）。
- **D6 prompt 词预算**：参照 ppt-master，Layout 段 ≤150 词、风格段 80–120 词，防 tag-soup 稀释。

建议切入点：**D1 Schema + 3 试点主题 + D2 + D3 先做（同一个 PR 的心智），用 demos/imagegen-v2 的封面重烙做 A/B 验收**（同主题同文字，新指令 vs 旧产物），过则铺量 21 主题并落地 D4。

> **2026-10-07 追记（升维转向）**：D1–D3 已落地（试点三主题 e3/c3/a1，实施记录见 `docs/design/imagegen-v2.md` §7）。首轮 A/B 的机器维全胜但用户目检判"视觉几乎无差异"——归因：参考图被指令设为临摹目标、蓝图同构、无超越授权、i2i 保真倾向。烙入语义从"保真封存"重定义为"内容忠实 + 视觉升维"：`bake_brief` 新增 **uplift 字段**（每主题的物理升维路径：材质/光影/纵深/肌理，已落地三主题），Style Anchor 改为内容锚，蓝图降为信息结构纪律，rubric 增"视觉升维"维。本文 §3 差距表因此须补一行隐性差距：**指令目标函数**——codex 的 brief 语义本就是"艺术化再创作"，我们初版误设为"复刻 HTML"。
