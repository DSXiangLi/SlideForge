# 验收证据：多色彩主题体系（G 系四主题 + E1/E4/E6 升级）

> 日期：2026-10-08 · 设计：`../design/theme-multi-hue.md` · 分析实录：`../progress/1008_theme_multi_hue_plan.md`

## 机器门槛

- `sync-themes.mjs`：28 套主题全绿——含多色扩展校验（`-on` 配对强制、palette 编号连续、多色立场字段必填、变体合并配对）与两两七层 diff≥3、分化声明逐层核验。
- `check-render.py`：theme-sampler 28 页 ALL PASS；theme-proving 56 页 ALL PASS；gallery 零新增失败。
- **T34-theme-proving**（新增，run_e2e 第 60 项）：7 主题 × 8 页型（cover/toc/low/high/ig×2/chart×2）结构断言 + 逐页几何门禁（T18 同口径）+ 多色像素实证（色相族计数 ≥2 族：e1-cover=4 族、e4-cover=3 族、e6-ig1=4 族、g2-cover=4 族）全部 PASS。

## 截图与探针证据

```
docs/test_acceptance/theme-multi-hue/
├── sampler/  theme-{e1,e4,e6,g1,g2,g3,g4}.png   # 差异样张（同业务页 × 主题）
├── gallery/  theme-{e1,e4,e6}.png               # 升级主题样张
└── proving/  <theme>-cover.png + <theme>-high.png × 7 主题   # 页型验收
```

像素探针（PIL 实测）：

| 主题 | 验证点 | 结果 |
|---|---|---|
| e1 双色套印 | 粉（#FF48B0）×蓝（#0078BF）共存 + multiply 叠出第三色调 | 叠印区实测紫 (114,76,164) ✓ |
| e4 三原色 | 同页红/黄/蓝三色 + 形色对应（圆蓝/三角黄/方红） | sampler 红 3.68%/黄 0.47%/蓝 2.37% ✓ |
| e6 四色轮转 | 碎形同页 ≥2 色 | 粉/黄/青/绿四色命中 ✓ |
| g1 翡翠 | 绿底满铺 >50% + 金箔 ≤2% | 绿 70.2%、金箔 0.017% ✓ |
| g2 荧光笔 | 粉底 + 同页 ≤2 色荧光标注 | 粉底 94.8%、橙/绿两带命中 ✓ |
| g3 陶土 | 零黑零灰、砖红为唯一油墨 | 奶油底 69.3%、砖红 2.40% ✓ |
| g4 靛墨黄页 | 黄出血 + 靛墨文字 | 黄 19.94%、靛 6.59% ✓ |

## 工程发现（已回灌规范）

1. **chart token 作用域坑**：`:root` 处 var() 即冻结，多主题 deck 里图表 token 必须逐页 section 内联——已写入 themes.md 图表 token 节。
2. **旋转 × 重叠门禁**：微旋转只许落装饰层，文字层轴对齐（AABB 膨胀 ≈ w·sinθ）——已写入 components.md §12 规则 8。
3. g4 图表口径对齐：靛墨明度阶梯多系列 + 黄唯一焦点系列（themes.md G8 已明文化）。

## README 资产

`assets/theme-sampler/` 全量 28 张（p01–p28，含刷新 p10-e1/p13-e4/p15-e6 与新增 p25–p28 G 系）；README 精选 12 组 = c1/c3/e1/e2/e6/e7/e10/f1/f2/f3/g1/g2。

## 回归

run_e2e 全量（60 项含 T34）：结果见 `../progress/1008_theme_multi_hue_plan.md` 实施记录节。

## 第三轮追加（2026-10-08：E4 尺度 / E1 对比度 / G5 入库）

- **G5 三色旬刊**（第 29 主题）：封闭三色零中性（胭脂/黄油/勃艮第），探针：纯黑纯白像素 0.0000%、三色俱在；proving 8 页 + sampler p29 + gallery 样张页全过。
- **E4 尺度纪律**（基本形短边 ≥216px、色面容器 1/4–1/2 页、出血合法）：重排后红色面容器实测占页 21.1–27.6%，海报级构成成立。
- **E1 对比度铁律**（深色容器禁令、套印面只压 ≥56px 海报标题）：e1-high 暗像素仅 0.82%（文字笔画级），无深色容器压正文。
- **T34**：8 主题 × 8 页型 = 64 页全绿；多色实证新增 g5-cover（ΔRGB token 近邻计数口径：胭脂 9507/黄油 2523/酒红 114831）。
- **check-render**：proving 64/64、sampler 29/29 ALL PASS；gallery 61 页零新增失败。
- **run_e2e 全量**：见 `../progress/1009_theme_multi_hue_review.md` §五。
