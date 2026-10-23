# 1007 imagegen v2 迭代实录

> 设计：`docs/design/imagegen-v2.md`（用户 2026-10-06 跳过评审直接开发，验收口径 = 最终生图效果 + 编辑器生图按钮）。验收证据：`docs/test_acceptance/imagegen-v2-g8-real-imagegen.md`。

## 范围与结果

P0–P2 全部落地，`run_e2e.py` 57 → **59 项 59 PASS**（新增 T30-harmony、T31-brief 三态、T32 按钮三态/assets-changed、T33 本地插画通道；T16 增 G7 断言）。

- **G2** `scripts/check-image-harmony.py`：浏览器 canvas 取主色板 × manifest token CIEDE2000，指标 A（无锚率>40%）/B（缺呼应，满幅烙入豁免 paper/ink），单图告警、≥50% 双触发阻断；fixture `tests/decks/harmony-fixture/`（纯 Python 合成 PNG）。
- **G3** rubric 五维入 `bake-prompts.md` §5（文字逐字一票否决）；代表页 `--n 2` 双候选择优（用户批准成本）；adapter 增 `--rubric-json` 透传落账。
- **G1** 脑暴第⑧组三态（纯 HTML/AI 插画/混合烙入）+ 条件追问；简报 `bake_intent` 字段（缺省=封面+扉页+收束，脑暴期落语义清单+defaulted，Step 1 落具体 slide id）；编辑器脑暴浮板同步；SKILL v1.8。
- **G4** 契约 v8 图片入场动效白名单（fade/rise-in/scale-pop/wipe-clip，每页≤1，整图≤0.8s）；skeleton v7.5（enter 族对 img 天然通用 + 时长帽）；`data-anim` 不进 canonical string（两端零改动，实测 hash 不变）；导出 freeze 终态三层实测通过；motion.md v3.2。
- **G5** editor v3.7：生图按钮（重烙当前页/补齐插画）三态可达（Bridge 发 intent / 嵌入发 postMessage / 裸静态复制指令）；嵌入协议补 `:bake-intent` 出站与 `:assets-changed` 入站热刷新；协议注释与实现同步。
- **G6** `edit.py --imagegen` 本地插画通道（显式开启+计费警示；provider 由 `PPTX_HTML_IMAGEGEN_PROVIDER` 或 `.pptx-html/config.json` 供给；只补插画不烙入；执行体 100% 技能脚本）。
- **G7** check-images 分辨率下限：页面级 ≥2560×1440、页内短边 ≥640px（SVG 豁免，两模式同口径）；bake-mix 烙入图升采样至 2560×1440。

## G8 真实生图（首次，UNKNOWN → 有证据）

- provider：oai生图 script.py（gpt-image-2.5-flare）；**注意**：默认 assistant-test 路由上游不可用，须 `IMAGE_STUDIO_URL=http://algoplatform.thfund.work/assistant/image-studio` 覆盖。
- 演示 deck `demos/imagegen-v2/`（E3 装饰艺术×墨绿金）：cover 烙入双候选（n=2，Playwright 截图风格锚）rubric 择优；market 槽位 A 真实生成。2 次调用 3 张图零失败。
- 编辑器按钮实测：用户点「补齐插画」→ `illustrate.requested` intent → agent 工作副本生图（market-china，26s）→ harmony 零告警 → 四闸全绿 → complete 发布（receipt `rcpt_zsoyDNiH6vG-T4fsS4-zBtX7`），ledger 回并正式 deck。
- 文字逐字维无机器终裁（本机无 OCR/视觉工具），以用户目检为准。

## 收尾追记（2026-10-08）

- C 组用户目检通过，默认策略定为 C1 臂（带内容锚的升维指令）；随后用户反馈升维仍不明显 → v4 收紧：Style Anchor 写死"只内容与配色"六字诀 + 新增"升维手段"六维节（光线/质感/插画/布局/容器/字体），E 组（E1 封面 / E2 高密度）用户裁决**有明显提升，通过**。
- demo 封面已换 v4 E1 并重建双轨导出；README 烙入展示位换 v4 对照组（封面 + 高密度两对），高密度对图已脱品牌（HTML 侧改字重截图，生图侧 OCR 定位 + inpaint + 补字，残留天弘 0）。
- 高密度页结论固化：38 行/922 字符超逐字渲染上限（v3/v4 同症），此类页诚实留 HTML——选页纪律成立。
- 真实调用累计 8/10。遗留：21 主题 bake_brief 铺量 + D4 锚链未做；E2 高密度图为 text reject 仅作升维效果展示。

## 坑与待办

- 编辑器协议注释曾与实现漂移（漏 `:design`/`:illustrate-intent`），G5 已补齐——协议注释今后随实现同改。
- rubric 落账时序矛盾：`--rubric-json` 需调用前加载，评审只能生图后做；现按 harmony 同款后置写回，adapter 宜加后置补记口（未做）。
- 烙入后须重建 `.manifest-baseline.json` 再导出，否则 C2 对 hidden 源层误报漂移。
- harness 字母段 r/s/t/u/v 已被占用，harmony 子检查命名为 `w_`，本地通道为 `x_`。
- stale MCP 代理进程会缓存旧 discovery 导致 STORAGE_UNAVAILABLE——kill 旧 `edit.py --mcp` 进程后宿主自动重生即恢复；旧 daemon 停止后 serve.json 残留需手动删（`verify_discovery` 对死文件报"文件身份不匹配"）。
- 遗留：Office/WPS 目检 NOT_RUN；G2 阈值待更多真实样本校准；`demos/imagegen-v2/end` 页留作「重烙当前页」验收位（用户尚未点击）。

## 脱敏重构追记（2026-10-08，dense demo 重建）

- 起因：用户验收发现 ① 高密度烙入图右上角仍有天弘基金 logo 图形标（OCR 漏检——文本比对覆盖不到图形标）；② dense demo（cmb-retail 副本）export/ 54 页全是真实基金公司内容，仅 sed 改名不够。
- 处置：`demos/imagegen-v2-dense` 整目录推倒重建为 **3 页中性 deck**（cover / allocation-solution / end），题材=虚构"珩云科技×恪远控股"企业云服务方案（公司名/产品名自查无真实撞名）；allocation-solution 保留原版式与压力测试价值：41 条文本 / **905 字符**（7 编号能力块 + 3 服务段 + 脚注）；masthead 纯文字、**无 logo 图形**。skeleton v7.6 + B1 主题逐字套用；extract-manifest --write-hashes / check-render / check-capacity / check-images 双模式全绿。旧 54 页副本、D/E 组旧候选图、旧 rubric、旧 compare 全部删除。
- 重生图：v4 编译器（B1 bake_brief、analysis 角色）+ 新内容锚（2560×1440 截图），flare/high/n=1，**1 次调用**成功 → `e2-allocation.png`。
- 验证：harmony 零告警；OCR 全行比对 exact 20/37（长句截断同症，text_exact 预期内 reject——该页定位=高密度升维展示）；**新增四角 2× 放大复扫**（cv2 裁切 + easyocr）：logo 原位（右上）为空，品牌词黑名单全图+四角零命中。rubric 落 `demos/imagegen-v2-dense/rubric-e2.json`（38 行比对表）。
- 导出重建：`export-pptx.py --force --track both`（deck.pptx / deck-vector.pptx / deck.pdf 全中性）；README 资产 `assets/ai-bake/imagegen-v2-dense-{html,baked}.png` 换为新中性版本（图注 "(de-branded demo content)" 已准确，无需改）；`compare-dense-v4.png` 重制为 HTML anchor / v4 baked 双联（旧三联中间面板含真实公司内容，随旧图退役）。主 demo `demos/imagegen-v2` grep 天弘/招商零命中（父会话早前已 sed）。
- 教训沉淀：① 生图验收的 OCR 必须含**四角放大复扫**（图形 logo 不落文本行比对）；② demo 内容脱敏要整目录（含 export/ 与拼图资产），sed 改名不是脱敏；③ 源层 masthead 的 logo 槽位会被生图忠实继承——内容锚里的品牌元素即产物品牌元素。
- 真实调用累计 **9/10**。
