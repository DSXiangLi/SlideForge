# Phase 6 · 批次 1 · 验收报告

> 日期：2026-11-16
> 范围：E6 孟菲斯 / G2 腮红荧光笔 / E7 浮世绘 / F1 浮光玻璃（本批 4 套，按评分 rank 前 4）
> 依据：`docs/progress/HANDOVER.md` §2/§5、`docs/progress/phase6-batch1/brief.md`、`docs/progress/G10-composition-program.md`
> 状态：**已完成，等待用户验收**。通过前不改 README Gallery、不进下一批、不 push。

---

## 1. 交付物清单（§5.6 签收清单逐项）

| 清单项 | 产物 | 状态 |
|---|---|---|
| 4 份 G10 契约 + DOM 结构测试 | `skills/SlideForge/references/themes/{color/e6,color/g2,texture/e7,light/f1}/theme.md` | ✅ 各含 7 字段 + type_scale + DOM 测试签署 PASS |
| 令牌终值表 + 地板核对 | 见 §2；`verify-theme.js` 校验 8/8 字段、字面 hex=0、框架选择器=0、母题类全库无重名 | ✅ |
| ≥40 页 PNG + report.json | `phase6-batch1/png/*.png`（40 张）+ `report.json`（逐节点 bbox/字号/溢出/弱读/重叠） | ✅ |
| 审计 9 项结果 | 见 §3 | ✅ 全绿 |
| 新旧 A/B 并排页 | `phase6-batch1/compare.html`（4 组，旧 `old/pNN` vs 新 `png/xxx-data.png`） | ✅ |
| 指纹/盲测 | `phase6-batch1/fingerprint.json` + `blind-test.html`（40 张灰度 240×135 遮名缩略） | ✅ |
| 本批报告 | 本文 | ✅ |
| **请求签收** | 见 §6 | ⏳ 等你「通过 / 打回 + 原因」 |
| README Gallery 是否更新 | **本批未动**，单独征询 | ⏳ 待你定 |

评分依据与四套方案详见 `brief.md`（含 `score.txt` 26 套完整评分）；G10 草案已复制入 `docs/progress/G10-composition-program.md` 规避换机丢失。

---

## 2. 令牌终值表（px@1920，与骨架地板核对）

骨架默认 / 地板：`display 96/64`、`heading 64/32`、`subhead 40/24`、`body 28/18`、`caption 18/16`、`meta 15/14`、`vertical 96/64`。

| 主题 | `--t-display` | `--t-heading` | `--t-body` | `--t-vertical` | 低密度层级落差实测 |
|---|---|---|---|---|---|
| E6 孟菲斯 | **132** | 继承 64 | 35 | — | 6.4:1（全批最低，≥6 ✓） |
| G2 腮红荧光笔 | **112** | 继承 64 | 35 | — | ≥6 ✓ |
| E7 浮世绘 | **96** | 继承 64 | 35 | **72** | ≥6 ✓ |
| F1 浮光玻璃 | **108** | 继承 64 | 35 | — | ≥6 ✓ |

四套 `subhead/caption/meta` 均继承 40/18/15；恶意令牌场景（`max()` 地板）沿用 Phase 3 结论，下限结构性不可突破。

---

## 3. 审计 9 项（Playwright + 系统 Chrome，40 页，1920×1080）

| # | 项 | 阈值 | 实测 |
|---|---|---|---|
| 1 | 画布越界 | 0 | **0** |
| 2 | 容器内溢出 | 0 | **0** |
| 3 | 内容溢出（scrollHeight 超容器 ≥14px） | 0 | **0** |
| 4 | 弱读（≥18px 且 opacity<0.9） | 0 | **0** |
| 5 | 同层文本块重叠（排除 transform） | 0 | **0** |
| 6 | pageErrors | 0 | **0** |
| 7 | 裸写 inline `font-size` | 0 | **0** |
| 8 | 字号地板（computed ≥ 角色 floor） | 全过 | **0 违规** |
| 9 | 层级落差（低密度页） | ≥6:1 | **6.4:1（min）** |

40 页 = 24 基线（4×6 页型）+ 16 压力（4×4：D2 长段落 / D3 大数负数 / D4 八系列 / D7 极长标题）。

---

## 4. 指纹与盲测（举证，不自动打回）

**类间可分**（基线 24 页，骨架层两两相关）：

| 指标 | 旧 28 张样张 | 本批 4 套 | 目标 |
|---|---|---|---|
| 均值 | 0.4594 | **0.2644** | ≤0.35 ✅ |
| 最高配对 | 0.990 | **0.723** | <0.8 ✅ |
| >0.8 配对占比 | 23.28% | **0%** | =0 ✅ |

**类内成族**（同主题跨 6 页型骨架相关，目标 0.55–0.85）：

| 主题 | 类内均值 | 判读 |
|---|---|---|
| E6 | 0.601 | ✅ 达标 |
| F1 | 0.762 | ✅ 达标 |
| G2 | 0.475 | ⚠️ 偏低（6 页型节奏偏大） |
| E7 | 0.861 | ⚠️ 略高（接近「每页复制版式」上界） |

**主轴方向**：40/40 全水平（旧 28/28 也全水平）。E7/G2 的水平主结构符合契约；E6 之字路径 / F1 深度轴是「路径/轴」级细线，强模糊后归入水平块——这是本批的诚实边界（见 §5）。

**盲测页** `blind-test.html` 已生成：40 页灰度 + 240×135 缩略 + 遮主题名，供人/VLM 判读。

---

## 5. 迭代轮次与诚实边界

**迭代 4 轮**（每轮全量重跑 40 页）：

| 轮 | 问题 | 修复 |
|---|---|---|
| rev1 | section `style` 属性被字体栈双引号截断 → `--t-display` 全回落为 108px | style 属性改用单引号 |
| rev2 | F1 玻璃层「深度 N」标签与邻层文本重叠（16 处）；chip 高度装不下 t-heading | 移除可见深度标签（深度档改由 `data-depth` + 背景混合表达）、chip 改自然高 + t-subhead |
| rev3 | E6 数据台阶内 `.mt-mem-step` 过宽挤爆积木（数字 h=304） | 数据台阶移除 step 短条 |
| rev4 | E6 积木误渲染成白底 → 与 G2 白底封面结构趋同（0.872） | 积木改糖果色 palette 填充（焦点块 accent），类间相关降至 0.264 |

**诚实边界（遗留，请验收时一并裁量）**
1. **G2 类内相关 0.475**：其 6 页型（封面巨字 / 目录五行 / 分析四行 / 数据三大字）结构跨度大，节奏偏「散」。若要求收紧，需把 G2 各页型统一到「行号列 + 引线」的更强一致性。
2. **E7 类内相关 0.861**：三层套印各页型高度一致，接近上界。若要求拉开节奏，可让 cover/closing 的层数或版差与其他页型错开。
3. **主轴方向全水平**：E6/F1 的斜向是路径/轴级细线，非 E5 −12° 力带那种大面积色面，像素级主轴仍归水平。若要让对角可测，需给 E6 之字 / F1 深度轴加大面积对角色面——但这会稀释孟菲斯的「轻」与玻璃的「透」，属审美取舍，未擅自加。
4. **封面/极长标题页固有趋同**：cover 与 d7（压力页）是「单点巨字」形态，跨主题仍有一定相似（但已从 0.976 压到 <0.8）。
5. **未做整 deck 连续复验**：本批是「6 页型 × 4 主题」离散页，未按某份真实大纲排连续 deck 验节奏。
6. **批次顺序偏离 §5.2**：按评分把 E6/G2 提前、C1/G1 顺延（理由见 `brief.md` §1.1）。若要严格照 §5.2，请在验收时说明。

---

## 6. 请求签收

请你验收 `compare.html`（新旧 A/B）与 `blind-test.html`（盲测）后，回复：

- **「通过」** → 我提交本地 commit（精确 `git add`，不 push），并按新顺序开下一批（F2 优先）。
- **「打回 + 具体原因」** → 我重做本批（只重做被打回的部分，不带问题进下一批）。

另请一并裁量两件事：
1. 是否接受 §5 的 6 条遗留（尤其 G2/E7 的类内相关、E6/F1 的主轴方向）；
2. 本批结束后是否更新 README Gallery（**默认不动**，单独征询）。

---

## 7. 文件落档位置

```
docs/progress/
  G10-composition-program.md            ← G10 草案入库（换机保障）
  phase6-batch1-report.md               ← 本文
  phase6-batch1/
    brief.md / score.js / score.json / score.txt
    apply-theme-updates.js / apply-log.txt
    verify-theme.js / theme-verify.txt
    build.js / cases.json / sampler.html
    run.js / report.json / audit-summary.txt
    fingerprint.py / fingerprint.json / blind-meta.json
    png/*.png (40) / blind/*.thumb.png (40)
    compare.html / blind-test.html / old/*.png (4)
```
