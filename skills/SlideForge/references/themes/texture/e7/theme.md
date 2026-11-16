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

- **亲和**：三层套印版次（题/论/证各占一层，层间云霞或浪花横带）、图文证据（画 + 题跋）、巨字宣言（封面题字 + 印章落款，画册封面的仪式感）
- **禁忌**：禁网格矩阵密集排布（版画的秩序是中轴与余白不是货架网格）；裂屏对开慎用——版画画幅是完整一张；图表须以墨线轮廓与平涂色面收编，禁终端/信号词汇

**G9 motif**

- **词汇**：姓名印（.mt-uki-seal：accent 实色小方块 + 反白篆意字，末版右端落款位，每页至多一方）/ 浪花带（.mt-uki-wave：鳞片浪纹横带）/ 云霞横带（.mt-uki-cloud：断续横带，版次层分界）/ 远景题名列（.mt-uki-inscription：右上留白处竖排小字，每页至多一列，**非主标题、非题跋分列**）/ 版次层（.mt-uki-plate：签名结构件，内部文字保持可编辑）/ 版次标号框（.mt-uki-edition：每层右缘的墨线数字框）/ 横带定位（.mt-uki-band）

```css
:root{--t-display:96px;--t-body:24px;--t-vertical:72px}
/* E7 浮世绘 · 装饰母题 */
.mt-uki-seal{display:inline-flex;align-items:center;justify-content:center;width:2.4em;height:2.4em;background:var(--accent);color:var(--accent-on);font-family:var(--font-display);font-weight:700;font-size:20px;line-height:1.15;text-align:center;letter-spacing:.08em;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--accent-on) 40%,transparent)}
.mt-uki-wave{height:26px;pointer-events:none;user-select:none;background-image:radial-gradient(circle at 13px 26px,transparent 9px,color-mix(in srgb,var(--ink) 55%,transparent) 9px 10.5px,transparent 10.5px),radial-gradient(circle at 13px 26px,transparent 4px,color-mix(in srgb,var(--ink) 55%,transparent) 4px 5.5px,transparent 5.5px);background-size:26px 26px;background-repeat:repeat-x}
.mt-uki-cloud{height:10px;pointer-events:none;user-select:none;background-image:repeating-linear-gradient(90deg,color-mix(in srgb,var(--accent) 70%,var(--paper)) 0 60px,transparent 60px 88px),repeating-linear-gradient(90deg,color-mix(in srgb,var(--ink) 25%,transparent) 0 34px,transparent 34px 88px);background-position:0 0,14px 5px;background-size:88px 4px,88px 4px;background-repeat:repeat-x}
.mt-uki-inscription{writing-mode:vertical-rl;font-family:var(--font-display);font-size:.5em;letter-spacing:.35em;color:color-mix(in srgb,var(--ink) 70%,transparent);border-left:1px solid color-mix(in srgb,var(--ink) 40%,transparent);padding-left:.6em}
.mt-uki-plate{position:absolute;left:0;right:0;background:var(--paper-tint);border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);padding:18px 28px}
.mt-uki-plate--first{background:color-mix(in srgb,var(--ink-tint) 12%,var(--paper))}
.mt-uki-edition{position:absolute;border:1px solid var(--ink);padding:6px 12px;font-family:var(--font-mono)}
.mt-uki-band{position:absolute;left:0;right:0;height:10px;pointer-events:none}
```

- **禁忌**：姓名印每页至多一方且只在末版右端；浪花带/云霞带合计每页 2 条且横贯全宽、禁进图表区；**禁竖排题跋分列、禁上下金轴与卷轴（H1 氤氲手卷词汇）**；**禁同形重影叠印（E1 孔版印刷词汇）**；.mt-uki-inscription 是文本载体类母题，文本保持可编辑；其余母题件一律 data-editable-skip

**G10 composition_program**

- **定位**：主题从「可替换参数集」升级为「决定信息如何进入空间的程序」。本组为硬约束，写进页计划表头即整 deck 的构图契约。
- **与 H1 的界限**：H1 是垂直主轴 + 自右向左展开 + 竖排主标题 + 题跋分列；本主题是**水平主轴 + 自上而下分版 + 横排题字 + 逐层左缘错位**，竖排文字每页至多一列且只作远景题名。
- **灵魂承载**：三个版次层是签名结构件，形状由 CSS 承担（data-editable-skip），层内文字仍是 data-editable 叶子节点；姓名印是唯一句读，不是可随处贴的贴纸。
- **DOM 结构测试签署**：删掉 signature_operator，两条横带、三个平涂版次层、逐层 48px 错位、三个版次标号框与末版印章位置全部消失，页面退回「标题 + 两段正文 + 横排三格」；元素数量/分组/顺序/位置**都变** → **PASS**。

```yaml

doctrine: 一幅画是分版落印出来的；信息的先后就是版次的先后。
signature_operator: 把整页当作一张套色版画——横贯全宽的云霞/浪花带把画幅切成 2–3 个版次层，
  每层是一次独立落印的平涂色面；标题独占首版色面（信息容器，不是角标），
  说明与数字按版次逐层下移，每层左缘递增一个固定套印版差；
  三项数字作为版次标号压在每层右缘的墨线框内（不并列成格），姓名印落在末版右端收束。
silhouette: 水平 2–3 层套印带 + 逐层左缘递增错位；水平主结构；重心左下；右上长留白。
info_grammar:
  cover:    首版满幅平涂 + 题字 + 一枚姓名印；一条浪花带定下缘（单层强形态）
  toc:      三层短版各容一组章节名，版次标号 一/二/三（弱形态）
  claim:    首版题字 + 次版论点（两层），一条云霞横带
  analysis: 三层各容一类信息（题/论/证），层间云霞横带分隔
  data:     三项数字 → 三层右缘的版次标号框，非横排格
  closing:  单版收束 + 姓名印回押，与封面闭环
type_scale:            # px@1920×1080 画布基准；下限由骨架 .t-* 的 max() 结构性锁定
  --t-display:  96px  # 版画题字恒重，不做压强巨字；与正文 4:1
  --t-body:     24px  # 正文段落（长段落可读）；图注/说明走 caption 18、注脚走 meta 15
  rule: 标题:正文 ≥1.8:1；正文层 opacity = 1，禁灰化弱读；accent 面积 ≤5%、满屏 accent 禁止（G1 立场）
  floor_note: heading/subhead/caption/meta 不覆盖，继承骨架 64/40/18/15；地板由 max() 保证，无需后拦截门禁
invariants:
  - 横贯全宽的云霞/浪花带 ≥1 条，画幅被切成 2–3 层
  - 多层时各层左缘 x 严格递增且步长一致（48px ±2）
  - 主标题位于首层平涂色面内（信息容器）
  - 姓名印单页 1 枚且位于末版右端
  - 横排等权三格容器数 = 0
forbidden_defaults: [竖排题跋分列, 上下金轴与卷轴, 横向等权三格 KPI, 卡片墙, 网格矩阵密集排布, 同形重影叠印, 玻璃拟态, 渐变柔光]
dna_events: {cover: 强, claim: 中, analysis: 强, data: 中, toc: 弱, closing: 强}
```

---

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
