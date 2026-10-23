# G1 翡翠年鉴

- **id**：g1
- **气质**：深翡翠绒面 + 奶油墨 + 金箔——学院年鉴的晚宴礼服，绿是天鹅绒不是荧光
- **适用**：ESG 与可持续报告、教育品牌、机构年报、增长叙事、春季发布
- **focus**：G1 + G4
- **世界参考**：常春藤学院年鉴的墨绿绒面精装 × 金箔烫印——绿是身份不是点缀；金箔只给真正值得铭记的一页
- **unforgettable**：墨绿绒面满铺 + 烫金——页面底色是深翡翠，奶油墨字印在上面，金箔奖章压住唯一焦点
- **分化声明**：与 b1 分化于 L1/L4/L5/L6——b1 灰白冷纸底 + 克莱因蓝单点 + hairline 网格纪律；g1 深翡翠绒面底 + 奶油墨 + 绿档面/奶油墨档容器 + 金箔奖章/栏框母题；b1 锐利急停缓动，g1 端正匀速不覆盖缓动

**本质规范**（从 unforgettable 推理出的骨架硬规则——所有 G1–G9 规范须服从）

| # | 维度 | 规范 | 推理路径 |
|---|---|---|---|
| 1 | 氛围 | 学院年鉴的精装本——绒面满铺 + 烫金压顶 | 年鉴不是海报，是精装出版物 |
| 2 | 容器 | 绒面色面——ink 底奶油面 + paper-tint 绿档面，色面对比即层级 | 年鉴的容器是色面不是描边卡，绒面上描边发虚 |
| 3 | 分隔 | 1px 奶油细线——年鉴兼容 hairline，但须用奶油色不是墨色 | 年鉴是编辑出版物，细线是装帧语言 |
| 4 | 层次 | 色面对比（ink/paper-tint 双面）——无阴影 | 绒面的纵深靠明度差，不靠投影 |
| 5 | 版式 | 年鉴结构化版式——左对齐字段行，不是居中内容带 | 年鉴是表格化的编辑物，不是居中海报 |
| 6 | 入场 | rise-in 端正入场——不弹跳不柔焦 | 年鉴是白昼的正式装帧，弹跳与柔焦都不体面 |
| 7 | 底色 | 深翡翠绒面满铺——绿是身份不是点缀 | 绒面是年鉴的本体，不是背景色 |
| 8 | 字色 | 奶油墨印绿面 + 金箔只给焦点——文字永远落在面上 | 油墨印绒面，金箔是勋章不是文字色 |

**骨架硬规则**（生成侧必须遵从）：
- **禁 `.reveal` 通用入场**——用 `data-anim="rise-in"` 替代（端正入场，不是通用淡入）
- **禁居中内容带布局**（`display:flex;flex-direction:column;justify-content:center`）——用年鉴结构化版式：左对齐字段行，内容按栏目排布
- **禁 scale-pop / blur-in**——弹跳与柔焦都不属于年鉴的端正气质
- **禁 box-shadow**——纵深靠绿三档明度（paper/paper-tint/ink-tint）与奶油墨档面色面对比
- **masthead / hairline 与年鉴兼容，不禁**——年鉴是编辑出版物，刊头与细线是装帧语言而非污染

**G1 color**

```css
--paper:#1E4A3A; --paper-tint:#2B5F4C;
--ink:#F3EDDC;   --ink-tint:#16382B;
--accent:#D9A93A; --accent-on:#1E4A3A;
```

- **accent 预算**：金箔（accent）是唯一的注意力色——内容页 ≤5%（奖章/缎带/关键数字，单页至多一处）；奶油墨承担全部文字与容器面（墨档反白卡 = 奶油面绿字）；满屏奶油是封面/收束特权（奶油底 + 绿墨 = 年鉴扉页）；首尾闭环：绿底金标开场 → 收束页奶油底绿墨呼应。**面积-彩度落点**：绿底走深调窗口（绒面明度，禁亮绿满铺）。
- **多色立场**：本主题无多色 token——色彩纪律是"深绿 + 奶油 + 金"封闭三色结构（无中性黑灰：墨是奶油、线是奶油 alpha、焦点是金）；禁第四彩色。

**G2 typography**

```css
--font-display:"Songti SC","Noto Serif SC","STSong",serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 600–700（年鉴衬线的端正恒重）、正文 400
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：衬线恒重立场：≥77px→600–700；35–76px→600；正文 400；14–16px 小字 500–600
- **标题修饰**：无（绿底 + 衬线即身份）
- **metric_fallback**：display→Songti SC/Noto Serif SC；body→PingFang SC/Noto Sans SC；mono→SF Mono/Menlo

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——草坪是平涂的，绿底加任何纹理都是杂草

**G4 shape**

- **圆角**：0–4px（年鉴是方正的装帧）
- **hairline**：1px solid color-mix(in srgb, var(--ink) 30%, transparent)——奶油细线在绒面上成立
- **阴影**：无承托投影——纵深靠绿三档明度（paper/paper-tint/ink-tint）与奶油墨档面；金箔章允许极淡 inset 内环（G9 已含）
- **容器造型**：奶油墨档卡（ink 平涂 + 绿字反白——奶油卡是绿绒面上的"纸"）与深绿档面（paper-tint）双轨；禁描边卡（绒面上描边发虚）、禁玻璃
- **高密度容器边界**：奶油墨档卡阵（同 gap 同 padding）或深绿档面 + 奶油 hairline 分区

**G5 motion**

- **气质**：professional
- **强度上限**：默认
- **锚点偏好**：rise-in 端正入场；数据页 count-up；禁一切弹跳与柔焦
- **节奏偏移**：不偏移
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / blur-in（弹跳与柔焦都不体面）
- **fx 许可**：全禁

**G8 component**

- **亲和**：网格矩阵（年鉴格子照是它的原生形态）、数据英雄（绿底奶油巨数）、裂屏对开（绿/奶油对撞）
- **禁忌**：禁暗场效果词汇（辉光/霓虹/暗角不属于白昼草坪）；不用幽灵巨字（杂志系词汇）

**G9 motif**

- **词汇**：金箔奖章（`.mt-emr-seal`——双环金章，只给荣誉/首版/里程碑标记）/ 年鉴栏框线（`.mt-emr-rule`——粗细双线对，栏目的装帧分隔）/ 金箔页签（`.mt-emr-tab`——页顶缘小缎带标，标记章节性质）

```css
/* G1 翡翠年鉴 · 装饰母题 */
.mt-emr-seal{width:88px;height:88px;border-radius:50%;border:2px solid var(--accent);box-shadow:inset 0 0 0 5px color-mix(in srgb,var(--accent) 25%,transparent);pointer-events:none}
.mt-emr-rule{display:block;height:6px;border-top:2px solid var(--ink);border-bottom:1px solid var(--ink)}
.mt-emr-tab{position:absolute;top:0;width:56px;height:14px;background:var(--accent);pointer-events:none}
```

- **禁忌**：金箔单页至多一处（奖章泛滥即贬值）；栏框线只分栏不框卡；母题件一律 `data-editable-skip`

**Variants 配色变体**

#### 薄荷晨场

- **气质**：薄荷浅底 + 翡翠 accent——清晨的草坪（浅调低彩窗口），最轻亮的一档，适合教育、健康、春季上新

```css
--paper:#D8F3E6; --paper-tint:#C3E9D4;
--ink:#0F1A5C;   --ink-tint:#1B2A75;
--accent:#1E9E6A; --accent-on:#F2FBF6;
```

#### 松针正午

- **气质**：松针绿中调底 + 海军蓝墨 + 金——白昼的年鉴，学院运动衫感，适合校招、社团、体育与团队叙事

```css
--paper:#2E7D5B; --paper-tint:#3A8F6B;
--ink:#0F1A5C;   --ink-tint:#1F6647;
--accent:#F2C14E; --accent-on:#0F1A5C;
```
