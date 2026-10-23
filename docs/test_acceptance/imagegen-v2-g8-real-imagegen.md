# imagegen v2 G8 · 首次真实生图验收证据（2026-10-07）

验收资产：`demos/imagegen-v2/`（4 页演示 deck「穿越周期 · 2026 年度投资策略展望」，主题 e3 装饰艺术 × 墨绿金）。
Provider：`oai生图/script.py`（环境变量 `IMAGE_STUDIO_URL=http://algoplatform.thfund.work/assistant/image-studio`，非 test 路由），一律经 `skills/html-pptx/scripts/imagegen-adapter.py` 受控调用。
成本：真实 provider 调用 **2 次 / 3 张图**（上限 10 次），零重试、零失败。

## 真实调用台账（详见 deck 根 imagegen-ledger.json）

| # | 用途 | 参数 | 结果 |
|---|---|---|---|
| 1 | Step 5.5 插画槽位 A（market-global-3x2） | flare / medium / png / n=1 / 1536×1024，无参考图 | success，1536×1024 精确，1.37 MB，sha256 1b5c6326…，约 21s |
| 2 | Step 5.6 代表页 cover 双候选（page-baked-16x9） | flare / high / png / n=2 / 2560×1440，参考图=真实 HTML 封面截图 anchor-cover.png | success，两张均 2560×1440 精确，约 49s；择优 candidate 0 → assets/page-cover.png，落选保留 assets/page-cover-reject.png |

## 质量结论（机器可验部分；视觉终裁在用户目检）

- rubric 双候选择优：两候选主色板无锚率均 0%、三 token 全在场、行剖面证实巨字宣言构图（标题块占纵向 35–55%、中轴对称、页顶扇形放射与双线金框在场）；同分取先 + 候选 0 金色表达更强（Deco 签名要素）。rubric 全文：`demos/imagegen-v2/prompts/rubric-bake-cover.json`、`rubric-slot-market-global.json`，并后置补记进 ledger（见"遗留问题"）。
- check-image-harmony：2 图 2 告警 0 双触发 NOT BLOCKED——cover 缺 --accent 呼应（金以古铜 #776b3a ΔE 24.3 边缘值呈现，压暗/叠色合法偏离）；market-global 缺 --ink 呼应（暗绿+金双色线稿，合法偏离）。
- check-images：default 模式零错误零警告；illustration 模式恰 1 错误 = 槽位 B（market-china-3x2）**故意保留 placeholder**（G8 编排：留给用户现场点编辑器「补齐插画」），非生成失败。
- end 页按烙入构图约束设计但故意不烙（data-render-mode 保持 html），留给用户现场点「重烙当前页」。
- 导出：双轨 ok——cover 走 baked 直通（carrier=baked），其余 3 页 svg，保真均分 99.52；可编辑轨 native_text_ratio 1.0、认证 PASS、3 族字体内嵌。

## 遗留问题

1. **文字逐字维无机器终裁**：本机无 OCR/机器视觉工具，烙入图与插画的文字正确性、构图细节、禁忌元素以用户目检为最终裁决；若发现错字按 bake-prompts §3 重 roll（预算内尚余 8 次调用）。
2. **rubric 落账时序矛盾**：`--rubric-json` 在 adapter 调用前加载，但评审结论只能生图后得出；本次按 check-image-harmony 同款"原子后置写回"模式补入 ledger 并在 rubric note 声明。建议后续在 adapter 增加 `--rubric-append` 之类的后置补记口。
3. **导出防线 C2 与烙入的先后依赖**：烙入后须重建 `.manifest-baseline.json` 再导出，否则 hidden 源层文本（宽 0）对旧基线误报漂移。已在流程中验证此顺序可行。
4. WPS/Office 365 真实目检 NOT RUN（沿用项目既有遗留项）。
