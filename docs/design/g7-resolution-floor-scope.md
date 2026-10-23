# G7 分辨率下限的适用范围：uploaded 素材豁免

> 日期：2026-10-21 · 触发：`s_bridge_scale_check.py --group integration` 在补跑中 FAIL
> 关联：`docs/design/imagegen-v2.md`（G7 出处）、`skills/html-pptx/references/editing-contract.md` §2b、
> `skills/html-pptx/scripts/check-images.mjs`、`docs/test_acceptance/mcp-apps-upgrade.md` §2.6.1

## 1. 问题

`check-images.mjs` 的 G7 绝对分辨率下限（**硬错误**，非告警）对**所有** `assets/` 图位一视同仁：

- 页面级槽位（`page-baked-*`）栅格素材 ≥ 2560×1440；
- 页内槽位短边 ≥ 640px。

于是 `tests/decks/cmb-retail/index.html`（54 页真实材料 1:1 还原，纳入 T1 回归）直接 **exit 1**：
12 处图位不达标，最极端的是 58×58 / 64×64 / 66×66 的**图标与栏标**，另有 136×127 的装饰图标、
523×148 的横条图与 542×1174 / 591×1281 的手机截图。
（复现：`node skills/html-pptx/scripts/check-images.mjs tests/decks/cmb-retail/index.html`；对照臂 `theme-proving` exit 0。）

## 2. 为什么这不是夹具的错

这些图位的 `data-image-state` 全是 **`uploaded`**——即**用户真实素材**（从源 pptx 提取的原图）。
而技能的 pptx 转换条款明确要求"**图片原样落盘，不重画、不压缩**"（`SKILL.md` Step 0 转换入口）。
把一张 58×58 的真实图标放大到 640px 才算通过，等于**伪造来源**；反过来，任何含小图标/徽标/手机截图的
真实 deck 都会被这条门禁一票否决——这与该门禁的立意不符。

G7 的理由（`check-images.mjs` 文件头第 7 条）是"与烙入 Canvas 节 / adapter `--expected-size` 对齐"，
指向的是**生成侧**（AI 生图与烙入产物的分辨率纪律）。`uploaded` 素材不参与生成，不应受此约束。

## 3. 决策（2026-10-21，用户批准）

**G7 对 `data-image-state="uploaded"` 的图位豁免硬错误，降级为告警；对 placeholder / generated 保持硬错误。**

| 图位状态 | 页面级 <2560×1440 | 页内短边 <640px |
|---|---|---|
| `placeholder` | **错误**（生成侧必须按规格产出） | **错误** |
| `generated` | **错误** | **错误** |
| `uploaded` | **告警**（可见、不阻断；附"真实素材原样保留"说明） | **告警** |
| 缺 `data-image-state` | 仍按 §2 三属性缺失报错（与本决策无关） | 同左 |

不变的约束：SVG 矢量豁免、页面级槽位结构校验（契约 v7 三要素）、`--mode illustration` 下 placeholder
残留报错、src 契约与落盘存在性、比例三方绑定。

## 4. 影响面（实施清单）

1. `skills/html-pptx/scripts/check-images.mjs`：G7 段按 `state === 'uploaded'` 分流为 `warn`；文件头第 7 条补一句适用范围。
2. `skills/html-pptx/references/editing-contract.md` §2b：措辞从"分辨率下限【硬规则】"细化为
   "**生成侧**硬规则；`uploaded` 素材豁免为告警"，并追加契约版本记录。
3. `tests/harness/run_e2e.py::test_check_images`：新增两类断言——(i) `uploaded` 小图 → 告警且 rc=0；
   (ii) 同尺寸但 `state=generated` → 仍报错（保证豁免没有把生成侧纪律一起放开）。
4. `AGENTS.md`：check-images.mjs 的描述补"uploaded 豁免"。
5. 验收记录：`docs/test_acceptance/mcp-apps-upgrade.md` §2.6.1 更新为"已裁决并修复"；`s_ --group integration`
   重跑取证。

## 5. 代价与边界

- `cmb-retail` 会多出 12 条告警（不阻断）；**这是有意的**——真实素材的分辨率事实应当可见，只是不该否决交付。
- 若将来要为"真实素材也得上高清"立规，应作为**独立的、显式的**材料质量要求（用户可拒绝），
  而不是挂在生成侧门禁上。
