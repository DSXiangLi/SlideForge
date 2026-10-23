# E7 浮世绘

- **id**：e7
- **气质**：宣纸米底 + 墨线平涂 + 印泥红落款，浮世绘版画的平面秩序与东方余白
- **适用**：文化艺术、东方美学、展览与博物馆、品牌故事、茶/器物/旅行、人文叙事
- **focus**：G3 + G9
- **世界参考**：江户浮世绘版画（葛饰北斋《富岳三十六景》、歌川广重《东海道五十三次》）——平涂色面、细轮廓墨线、浪花云霞纹样、落款姓名印
- **unforgettable**：姓名印 + 浪花带——右下角一方印泥红底白字印章如画作的落款，页缘一条扇形浪纹压住版面
- **分化声明**：与 d3 分化于 L2/L4/L5/L6——e7 是宋体系衬线恒重字排，d3 是楷体手绘字排（L2）；e7 母题是姓名印/浪花带/云霞横带/竖排题跋的版画纹样，d3 是笔触块/虚线圈注/画框双描边的油画工艺——版画平涂与油画笔触是两个工艺世界（L4）；e7 容器是无框平涂色面 + 细墨线轮廓 + 直角，d3 是不规则有机圆角 + 零描边（L5）；同为 calm + draw-line，但 e7 节奏更仪式化（阶梯步长 ≥120ms 的套印节奏：一层色面落定再上下一层），d3 只慢半拍无步长纪律（L6）（L3 两者同为 paper+all，按规则不计入）

**G1 color**

```css
--paper:#F5EFE2; --paper-tint:#E9DFC9;
--ink:#23201B;   --ink-tint:#3D3A33;
--accent:#B03A2E; --accent-on:#F5EFE2;
```

- **accent 预算**：内容页 accent 面积 ≤5%——印泥红在浮世绘里是落款与点缀不是主色（姓名印一方 + 至多一处单强调）；**满屏 accent 禁止**——浮世绘的大色面是墨与纸的派生平涂（ink-tint / paper-tint 色面），红永远只是落款；首尾闭环：封面题字旁一方姓名印开场 → 收束页同位置印章呼应。

**G2 typography**

```css
--font-display:"Songti SC","Noto Serif SC","STSong",serif;
--font-body:"Songti SC","Noto Serif SC","STSong",serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：全衬线恒重——标题 600–700、正文 400–500，层级靠字号差与墨的浓淡
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：全衬线恒重立场（不走倒挂——细衬线大字号发虚）：标题 600–700；正文 400–500；14–16px 小字 500–600
- **标题修饰**：竖排题跋条（见 G9 `.mt-uki-inscription`）——标题右侧一列竖排小字题跋是原生修饰，不另加

**G3 texture**

```css
--texture-type: paper;
--texture-layer: radial-gradient(90% 70% at 20% 15%, color-mix(in srgb, var(--ink) 3%, transparent), transparent 60%), radial-gradient(80% 70% at 80% 90%, color-mix(in srgb, var(--ink) 2%, transparent), transparent 65%);
--texture-scope: all;
```

- **立场**：宣纸纹理 = 材质本体——版画印在纸上，纸是这个世界的一部分，正文页也允许铺（scope all），但仍需生成侧逐页 `texture-on` 落码；强度烧死不得加深

**G4 shape**

- **圆角**：0——版画是方的世界，禁圆角卡
- **hairline**：1px solid color-mix(in srgb, var(--ink) 45%, transparent)，细墨线轮廓即版画骨法
- **阴影**：无——纸面世界不吃投影，层次靠平涂色面叠压与墨线勾勒
- **容器造型**：无框平涂色面 + 细墨线轮廓——分区靠 paper-tint/ink-tint 平涂色面与 1px 墨线描边；禁圆角、禁阴影、禁玻璃拟态、禁弥散
- **高密度容器边界**：平涂色面 + 1px 细墨线轮廓——版画骨法勾边即框，亮底上面与线同属一个印刷世界；同页择一为主力：内容容器走色面，图版边界走墨线轮廓

**G5 motion**

- **气质**：calm
- **强度上限**：低
- **锚点偏好**：draw-line 是签名锚点——墨线轮廓像被毛笔一笔勾出；文字入场 rise-in 轻上浮
- **节奏偏移**：时长档 +1，阶梯步长 ≥120ms——套印节奏：一层色面落定再上下一层，版画等得起
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / persp-in / typewriter / scramble（弹跳、透视与打字机都不属于版画）
- **fx 许可**：全禁（手工版画与数字粒子/字符场冲突）

**G7 illustration**

- **风格**：浮世绘平涂版画——平涂色面、粗墨轮廓线、浪/云/山纹样、限色套印、宣纸底
- **提示词种子**：ukiyo-e woodblock print, flat color planes, bold black outlines, wave and cloud patterns, limited palette, washi paper texture
- **禁忌**：不用照片级写实、不用渐变柔光、不用 3D 渲染与高饱和数码色

**G8 component**

- **亲和**：图文证据（画 + 题跋 = 浮世绘的原生版式）、巨字宣言（封面题字 + 印章落款，画册封面的仪式感）
- **禁忌**：禁网格矩阵密集排布（版画的秩序是中轴与余白不是货架网格）；裂屏对开慎用——版画画幅是完整一张；图表须以墨线轮廓与平涂色面收编，禁终端/信号词汇

**G9 motif**

- **词汇**：姓名印（`.mt-uki-seal`：accent 实色小方块 + 反白篆意字，右下角落款位，每页至多一方）/ 浪花带（`.mt-uki-wave`：repeating radial-gradient 半圆鳞片浪纹条，只许页缘一条横贯）/ 云霞横带（`.mt-uki-cloud`：两条错位的断续横带，区段分隔的霞光）/ 竖排题跋条（`.mt-uki-inscription`：标题右侧竖排小字，文本载体类母题）

```css
/* E7 浮世绘 · 装饰母题 */
.mt-uki-seal{display:inline-flex;align-items:center;justify-content:center;width:2.4em;height:2.4em;background:var(--accent);color:var(--accent-on);font-family:var(--font-display);font-weight:700;font-size:.5em;line-height:1.15;text-align:center;writing-mode:vertical-rl;letter-spacing:.08em;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--accent-on) 40%,transparent)}
.mt-uki-wave{height:26px;pointer-events:none;user-select:none;background-image:radial-gradient(circle at 13px 26px,transparent 9px,color-mix(in srgb,var(--ink) 55%,transparent) 9px 10.5px,transparent 10.5px),radial-gradient(circle at 13px 26px,transparent 4px,color-mix(in srgb,var(--ink) 55%,transparent) 4px 5.5px,transparent 5.5px);background-size:26px 26px;background-repeat:repeat-x}
.mt-uki-cloud{height:10px;pointer-events:none;user-select:none;background-image:repeating-linear-gradient(90deg,color-mix(in srgb,var(--accent) 70%,var(--paper)) 0 60px,transparent 60px 88px),repeating-linear-gradient(90deg,color-mix(in srgb,var(--ink) 25%,transparent) 0 34px,transparent 34px 88px);background-position:0 0,14px 5px;background-size:88px 4px,88px 4px;background-repeat:repeat-x}
.mt-uki-inscription{writing-mode:vertical-rl;font-family:var(--font-display);font-size:.5em;letter-spacing:.35em;color:color-mix(in srgb,var(--ink) 70%,transparent);border-left:1px solid color-mix(in srgb,var(--ink) 40%,transparent);padding-left:.6em}
```

- **禁忌**：姓名印每页至多一方、只许右下角/题跋末尾的落款位（多方印即画蛇添足）；浪花带只许页面上缘或下缘一条横贯，禁进图表区；云霞横带只许区段分隔，禁与浪花带同页（浪与霞不同页）；`.mt-uki-inscription` 是文本载体类母题——样式由类承担，文本保持可编辑；其余母题件一律 `data-editable-skip`

**Variants 配色变体**

#### 北斋蓝

- **气质**：普鲁士蓝（ベロ藍）入画——《神奈川冲浪里》的蓝浪世界，冷静、深邃、构图感最强——海洋、旅行、设计史、沉静叙事

```css
--paper:#F5EFE2; --paper-tint:#E9DFC9;
--ink:#23201B;   --ink-tint:#3D3A33;
--accent:#2B4B6F; --accent-on:#F5EFE2;
```

- **accent 预算**：蓝变体的 accent 是主役色而非落款色——内容页面积放宽至 ≤10%（浪花带/色面可用 accent 派生），姓名印保持 accent 实色不变；满屏仍禁止

#### 藤紫

- **气质**：藤紫落款——平安贵族色的余韵，比红更幽更文——文学、香道花道、雅集、女性向文化品牌

```css
--paper:#F5EFE2; --paper-tint:#E9DFC9;
--ink:#23201B;   --ink-tint:#3D3A33;
--accent:#7A5C8E; --accent-on:#F5EFE2;
```
