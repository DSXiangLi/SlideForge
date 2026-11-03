# D1 奶油物语

- **id**：d1
- **气质**：暖奶油底 + 焦糖点缀，圆润轻盈的甜品店感
- **适用**：生活方式、品牌发布、食品餐饮、母婴亲子、活动邀请等轻暖场景
- **focus**：G4 + G9
- **世界参考**：日系生活方式杂志与甜品店品牌物料——圆角贴纸、手写标价签、柔和色块分区的平面语言
- **unforgettable**：微倾焦糖贴纸徽章——像贴在手账页上的 Q 弹小标签，带着回弹缓动蹦出来，一眼甜品店
- **分化声明**：与 d3 分化于 L2/L3/L4/L5/L6——圆润无衬线对楷体手绘字排（L2）；flat 干净立场对纸面晕染（L3）；贴纸徽章/扇贝花边对笔触块/虚线圈注（L4）；规则大圆角 + 弥散阴影对不规则有机圆角 + 零阴影（L5）；Q 弹 scale-pop 对慢速 draw-line 描绘（L6）

**G1 color**

```css
--paper:#fbf6ee; --paper-tint:#f4ecdc;
--ink:#3d3229;   --ink-tint:#544738;
--accent:#c08334; --accent-on:#fffaf0;
```

- **accent 预算**：内容页 ≤10%（焦糖点缀与小色块）；满屏 accent 仅封面/收束；首尾闭环：封面焦糖色块→收束页焦糖一行字或色带

**G2 typography**

```css
--font-display:"Yuanti SC","PingFang SC","Noto Sans SC",sans-serif;
--font-body:"Yuanti SC","PingFang SC","Noto Sans SC",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 500–600、正文 400，圆润轻盈不用极粗
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：圆润立场（不走倒挂——圆体靠圆融不靠细）：标题 500–600；正文 400；14–16px 小字 500–600
- **标题修饰**：无

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——奶油的柔软靠配色、大圆角与弥散阴影表达，纹理破坏干净感

**G4 shape**

- **圆角**：16–24px 大圆角，全套容器统一圆角语言
- **hairline**：不用分割线，用留白与底色块（paper-tint）分区
- **阴影**：柔和弥散 `0 8px 24px color-mix(in srgb, var(--ink) 8%, transparent)`
- **容器造型**：圆角弥散——大圆角色块卡片（paper-tint 底或 accent 单焦点）+ 弥散软阴影；禁直角、禁玻璃拟态
- **高密度容器边界**：大圆角 paper-tint 面色块卡 + 弥散软阴影——圆角弥散即本主题签名造型，面即边界；卡阵同圆角、同影、同距，accent 面单焦点

**G5 motion**

- **气质**：calm
- **强度上限**：低（减少动画元素，只动主角）
- **锚点偏好**：scale-pop 是本命（贴纸徽章与圆角卡片 Q 弹出场）；其余元素 rise-in 柔和上浮即可
- **节奏偏移**：不偏移
- **缓动签名**：覆盖 `--ease-out` 为 cubic-bezier(.34,1.56,.64,1)——带回弹的 Q 弹出停
- **禁用**：无禁用
- **fx 许可**：仅 particle-drift（柔和漂浮不破坏奶油感；其余全禁）

**G8 component**

- **亲和**：网格矩阵（圆角卡片阵是它的货架）、巨字宣言（圆润巨字可爱不压人）
- **禁忌**：禁直角硬朗构图与 hairline 密集分割；不用加号角标与网格点阵（那是瑞士系词汇）

**G9 motif**

- **词汇**：贴纸徽章（accent 圆角胶囊小标，微倾 −3°，配 scale-pop 出场，单页 ≤2 个）/ 扇贝花边（paper-tint 圆点连成波浪边条，替代一切直线分隔）/ 奶油圆点（accent 实心圆点作列表符号，替代方点与编号）

```css
/* D1 奶油物语 · 装饰母题 + 缓动签名 */
:root{--ease-out:cubic-bezier(.34,1.56,.64,1)}
.mt-crm-sticker{display:inline-block;padding:.45em 1.1em;border-radius:999px;background:var(--accent);color:var(--accent-on);font-weight:600;letter-spacing:.05em;transform:rotate(-3deg);box-shadow:0 6px 18px color-mix(in srgb,var(--accent) 30%,transparent)}
.mt-crm-scallop{height:16px;background-image:radial-gradient(circle at 8px 0,var(--paper-tint) 8px,transparent 8.5px);background-size:16px 16px;background-repeat:repeat-x}
.mt-crm-dot{display:inline-block;width:.55em;height:.55em;border-radius:50%;background:var(--accent)}
```

- **禁忌**：贴纸徽章禁直角、禁每页超过 2 个（贴满即廉价）；扇贝花边禁进数据图表区（干扰读数）；母题件一律 `data-editable-skip`

**Variants 配色变体**

#### 抹茶

- **气质**：抹茶绿 + 奶油底，清新安静的和菓子感——茶饮、健康、自然系、生活方式品牌

```css
--paper:#fbf6ee; --paper-tint:#f4ecdc;
--ink:#3d3229;   --ink-tint:#544738;
--accent:#7A8B3F; --accent-on:#fffaf0;
```

#### 莓果

- **气质**：莓果粉 + 奶油底，甜美柔软的法式橱窗感——美妆、母婴、节庆、礼物场景

```css
--paper:#fbf6ee; --paper-tint:#f4ecdc;
--ink:#3d3229;   --ink-tint:#544738;
--accent:#C45B6E; --accent-on:#fffaf0;
```
