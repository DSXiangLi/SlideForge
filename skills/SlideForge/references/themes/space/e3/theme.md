# E3 装饰艺术 Art Deco

- **id**：e3
- **气质**：墨黑底 + 金线扇形放射，爵士时代的对称奢华与隆重
- **适用**：品牌发布、晚宴/庆典/颁奖典礼、奢侈品、金融、历史文化、需要仪式感与华丽记忆的场合
- **focus**：G9 + G1
- **世界参考**：1920s Art Deco——《了不起的盖茨比》的爵士时代、克莱斯勒大厦的扇形放射与阶梯几何、剧院海报的对称金框
- **unforgettable**：金线扇形放射（sunburst）+ 对称双线金框——页顶一扇金线放射、标题上下菱形分隔，一眼盖茨比
- **分化声明**：与 c1 分化于 L1/L2/L4/L5/L6——e3 墨黑暖底 + 金属金 accent、c1 纯黑舞台 + 信号橙；e3 是高对比衬线 display + 大写宽字距拉丁 kicker、c1 是极粗无衬线；e3 母题是扇形放射/双线金框/菱形分隔、c1 是信号条/巨号页码/信号方块；e3 容器是双线金描边直角框、c1 是大色块直角面（暗底细框只补边界）；e3 动效 dramatic 慢速隆重（时长 +1、mask-lines 亲和、禁 scale-pop）、c1 dramatic 短促爆发（时长 −1、scale-pop 过冲亲和、禁 mask-lines）

**G1 color**

```css
--paper:#111110; --paper-tint:#1b1b18;
--ink:#f0e9d6;   --ink-tint:#0a0a09;
--accent:#c9a227; --accent-on:#111110;
```

- **accent 预算**：金是线不是面——内容页 accent 面积 ≤8%（金线、扇形放射、菱形分隔、双线框，禁大面积金块）；满屏特权：封面/收束可用满幅双线金框 + 扇形放射仪式背景 + 金底反白特权页；首尾闭环：封面金线 sunburst（全亮）开场 → 收束页同构 sunburst（半亮或缩小）呼应。

**G2 typography**

```css
--font-display:"Songti SC","Noto Serif SC","STSong",serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 600–700（Didone 感高对比衬线，粗档表达）、正文 400；层级靠对称构图与字重，不靠色彩泛滥
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：衬线恒重立场（不走倒挂——细衬线大字号发虚）：≥77px→600–700；35–76px→600；正文 400；14–16px 小字 500–600
- **标题修饰**：kicker 行 = 大写拉丁 + 宽字距（letter-spacing ≥.3em），上下配菱形分隔符居中对称——Deco 的原生语言

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——金线本身即质感，任何叠加纹理只会把金属感糊掉

**G4 shape**

- **圆角**：0（Deco 的几何是直角与扇形，圆角不属这个世界）
- **hairline**：1px solid color-mix(in srgb, var(--accent) 55%, transparent)——分隔线即金线
- **阴影**：无
- **容器造型**：双线金框直角容器——border + outline 两条 1px 金线、间距 5–6px，直角、中空、无填充；底色块只用 ink-tint/paper-tint 明度档；禁圆角、禁阴影、禁描边以外的装饰性容器
- **高密度容器边界**：双线金框（`.mt-deco-frame`）直角中空框成阵即边界；需要面的容器升 ink-tint/paper-tint 明度档色块——同页面框不混（隔离三手段选型），金框排布不破中轴对称

**G5 motion**

- **气质**：dramatic
- **强度上限**：默认
- **锚点偏好**：mask-lines 逐行揭示（标题逐行揭幕，剧院开场感）+ draw-line（双线金框与分隔线生长）；封面 chars 逐字登场（慢阶梯）；count-up 只给真正的 KPI 英雄数字
- **节奏偏移**：时长档 +1（一切隆重慢半拍）；阶梯步长 ≥90ms
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / persp-in / scramble（弹跳、透视翻转与字符扰乱不庄重）
- **fx 许可**：全禁（金线放射已是仪式，canvas 仪式层会让它变廉价）

**G7 illustration**

- **种子**：装饰艺术风格插画——暗底金线勾边、扇形/阶梯摩天楼剪影、几何化孔雀与棕榈纹、对称构图；线稿感、禁照片写实、禁柔焦渐变

**G8 component**

- **亲和**：巨字宣言（中轴对称构图）、裂屏对开（中轴对称裂屏 + 金线分界）、轴与节点（对称装饰的时间轴）
- **禁忌**：禁斜线/对角构图——Deco 是中轴对称的艺术；网格矩阵仅许严格对称档且禁连页；不用加号角标/网格点阵（瑞士系词汇）与 ASCII 字符装饰（终端系词汇）

**G9 motif**

- **词汇**：扇形放射 sunburst（repeating-conic-gradient 半扇金线，页顶中央或标题区背景，低透明，每页至多一个）/ 双线金框（border + outline 双线直角框，容器或整页内框）/ 菱形分隔符（旋转 45° 的小金菱，两侧金线翼卫，标题上下居中对称）

```css
/* E3 装饰艺术 · 装饰母题 */
.mt-deco-sun{width:min(56vw,480px);height:calc(min(56vw,480px)/2);border-radius:999px 999px 0 0;overflow:hidden;pointer-events:none;background:repeating-conic-gradient(from -90deg at 50% 100%,color-mix(in srgb,var(--accent) 60%,transparent) 0deg 1.5deg,transparent 1.5deg 9deg)}
.mt-deco-frame{border:1px solid color-mix(in srgb,var(--accent) 70%,transparent);outline:1px solid color-mix(in srgb,var(--accent) 70%,transparent);outline-offset:5px}
.mt-deco-divider{display:flex;align-items:center;justify-content:center;gap:14px;pointer-events:none}
.mt-deco-divider::before,.mt-deco-divider::after{content:"";width:72px;height:1px;background:color-mix(in srgb,var(--accent) 65%,transparent)}
.mt-deco-rhombus{display:inline-block;width:8px;height:8px;background:var(--accent);transform:rotate(45deg)}
```

- **禁忌**：sunburst 每页至多一个、只许页顶/标题区/仪式页背景层，禁与标题同区抢焦；双线金框只许直角、禁配阴影；菱形分隔只许中轴对称位；母题件一律 `data-editable-skip`

**bake_brief**

```json
{
  "visual_direction": "1920s Art Deco jazz-age ceremony, Gatsby-era theatre poster, champagne-gold hairline engraving on deep ink-green lacquer, geometric fan sunburst, stepped skyscraper silhouettes, rhombus dividers, high-contrast Didone serif display type, strict central-axis symmetry carried by ritual ornament, luxury gala restraint",
  "palette_rule": "gold is line, never surface: hairline gold strokes, fan rays, rhombus dividers and double-line frames only; the ground stays deep ink-green lacquer, text stays warm ivory; forbid large gold fills, gold gradients, metallic foil photo texture, sepia photo tones, and any hue outside the ink-green / ivory / gold triad",
  "typography_bake": "主标题重构词汇：高对比衬线重构（竖粗横细的极端对比，楔形衬线放大为装饰锚点）；断笔——横划中段断开、嵌入一段细金线；延笔——撇捺末端延长为金线射线、汇入页顶 sunburst；半空心描边大字作背景残影层；宽字距大写拉丁 kicker（letter-spacing ≥.3em）配菱形分隔符；隐喻融字——标题负空间可容一扇金线放射或阶梯天际线剪影，但字面必须完整可读，不得为造型牺牲笔画",
  "uplift": "升维路径（HTML 做不到的物理维度）：深墨绿漆面有纵深——漆器般的微妙明暗渐变与刻线凹陷感，顶光落在漆面上形成克制的明暗过渡；金线是金属刻痕而非扁平矢量线——刻刀肌理、微弱高光、随视角的光泽变化；主标题如鎏金刻字浮于漆面之上，字面与漆面有毫米级前后层次与贴附阴影；sunburst 如剧院穹顶金箔刻线，带极细腻金属光泽；双线金框如画框鎏金边的内凹刻槽——HTML 的扁平金线在此全部获得物理材质",
  "allowed": "gold hairline fan sunburst (single half-fan, top center or behind title zone), right-angle double-line gold frames, small rotated-square rhombus dividers with gold line wings, stepped geometric skyscraper silhouettes, geometric peacock / palm / fan-shell ornaments, wide-letterspaced uppercase Latin kickers, ivory high-contrast serif type, symmetrical ornament cartouches, flat ink-green lacquer fields",
  "avoid": "photorealism, soft-focus gradients, rounded corners, shadows, glass morphism, mesh gradients, aurora blobs, gold foil or glitter texture, large gold surfaces, diagonal or dynamic composition, asymmetric Swiss grid, sans-serif titles, icon rows, cartoon characters, cheap banquet flyer feel, red-and-gold new-year cliche, lace-like over-ornamentation, page header/footer chrome",
  "layout_blueprints": {
    "cover": [
      {"position": "page inset edge", "count": 1, "labels": ["双线金框整页内框（直角、距页缘约 2%）"]},
      {"position": "top center", "count": 1, "labels": ["半扇金线 sunburst（低透明、不压标题区）"]},
      {"position": "upper third", "count": 1, "labels": ["宽字距大写拉丁 kicker + 居中菱形分隔符"]},
      {"position": "center", "count": 1, "labels": ["重构巨字主标题（高对比衬线、断笔/延笔）"]},
      {"position": "below title", "count": 2, "labels": ["一行副题", "一行小字署名/日期"]}
    ],
    "divider": [
      {"position": "page inset edge", "count": 1, "labels": ["双线金框内框"]},
      {"position": "center", "count": 1, "labels": ["章节序号巨字（衬线重构拉丁数字或中文数词）"]},
      {"position": "above and below center", "count": 2, "labels": ["菱形分隔符 + 两侧金线翼卫", "一行章节题"]},
      {"position": "background", "count": 1, "labels": ["低透明扇形放射或阶梯天际线剪影（二选一）"]}
    ],
    "key-message": [
      {"position": "top", "count": 1, "labels": ["宽字距 kicker + 菱形分隔"]},
      {"position": "center 60%", "count": 1, "labels": ["2–8 字核心词重构巨字"]},
      {"position": "inside typography", "count": 1, "labels": ["恰一个主导隐喻融入字型（回环/天平/阶梯，以断笔延笔实现）"]},
      {"position": "left and right edge", "count": 2, "labels": ["起点词", "对照词"]}
    ],
    "analysis": [
      {"position": "top", "count": 1, "labels": ["标题 + kicker + 菱形分隔"]},
      {"position": "center", "count": 1, "labels": ["中轴对称核心结构（对仗双栏/镜像模块/对称时间轴）"]},
      {"position": "left and right", "count": 2, "labels": ["对称辅助模块（金线 hairline 分隔）", "对称辅助模块"]},
      {"position": "bottom", "count": 1, "labels": ["可选一行结论（菱形分隔符引出）"]}
    ]
  },
  "rendering_constraints": [
    "The page must read as a 1920s Art Deco theatre poster or gala invitation, not a generic dark PPT template, not a social-media poster.",
    "Symmetry is ceremonial: every symmetric composition must be carried by Deco ornament (double-line frame, fan, rhombus) — bare centered text blocks are forbidden.",
    "Gold stays hairline: strokes, rays, rhombi and frames only; total gold area small; the ground remains deep lacquer.",
    "The main title must be typographically reconstructed (extreme stroke contrast, broken or extended strokes, metaphor in negative space) — plain bold filled type is a failure.",
    "Exactly one lead motif per page (fan OR double frame OR rhombus system); the rest stay subordinate — never stack all motifs at equal intensity.",
    "Flat engraved line work only: no photorealism, no soft gradients, no rounded corners, no shadows, no glass.",
    "Cover/divider/key-message pages: one giant title, one kicker, at most one subtitle plus one small annotation line; forbid 5 or more text modules.",
    "Analysis pages keep the central axis: symmetric twin columns or mirrored modules; asymmetric Swiss-grid and diagonal layouts are forbidden in this theme.",
    "Chinese strokes must render accurately; title legibility outranks ornament density — keep the title zone quiet and low-contrast.",
    "Do not invent logos, monograms, seals, watermarks, or brand marks."
  ]
}
```

**Variants 配色变体**

#### 墨绿金

- **气质**：深墨绿 + 金，老钱俱乐部与丝绒帷幕——金融、家族传承、威士忌、私享晚宴

```css
--paper:#0e1a14; --paper-tint:#16241c;
--ink:#f0e9d6;   --ink-tint:#080f0b;
--accent:#c9a227; --accent-on:#0e1a14;
```

#### 珍珠白银

- **气质**：珍珠浅底 + 深墨 + 银灰金，日间舞会与珠宝图册——时尚、美妆、婚礼、轻奢华品牌

```css
--paper:#ece9e2; --paper-tint:#e0dcd2;
--ink:#17181c;   --ink-tint:#26272c;
--accent:#8c7a4f; --accent-on:#ece9e2;
```

- **accent 预算**：浅底下银灰金明度差弱于暗底金——金线加倍克制（面积 ≤6%），满屏特权改为深墨反白页 + 银灰金双线框；其余同基底口径
