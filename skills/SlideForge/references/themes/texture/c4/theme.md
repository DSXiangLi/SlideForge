# C4 纸与墨

- **id**：c4
- **气质**：纸白 + 墨黑 + 一点绯红，传统书籍的安静与仪式感
- **适用**：文化、出版、人文历史、阅读、品牌故事、长篇叙事内容
- **focus**：G2 + G9
- **世界参考**：传统书籍装帧与出版社排版——题花、首字下沉、引文拉页、页码的印刷传统
- **unforgettable**：首字下沉——段首那枚占三行的绯红大字，一眼出版物
- **分化声明**：与 a1 分化于 L1/L2/L4/L6——c4 的 accent 是独立绯红（a1 accent==ink）、全衬线（a1 正文无衬线）、母题是题花/首字下沉/引文拉页（a1 是 Ghost 巨字与竖排题字条）、锚点动效是 draw-line（a1 是 mask-lines）

**G1 color**

```css
--paper:#faf9f7; --paper-tint:#efece7;
--ink:#1a1a1a;   --ink-tint:#2b2b2b;
--accent:#c41e3a; --accent-on:#faf9f7;
```

- **accent 预算**：内容页 accent 面积 ≤5%（绯红出版物式点睛：首字下沉/单引文标记/页码）；满屏 accent 仅封面/收束且宜半版；首尾闭环：封面绯红首字/题花 → 收束页绯红一行题字。

**G2 typography**

```css
--font-display:"Songti SC","Noto Serif SC","STSong",serif;
--font-body:"Songti SC","Noto Serif SC","STSong",serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：全衬线，标题 600–700、正文 400–500
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：全衬线恒重立场（不走倒挂——细衬线大字号发虚）：标题 600–700；正文 400–500；14–16px 小字 500–600
- **标题修饰**：首字下沉（封面/章节首段 drop cap）、引文拉页

**G3 texture**

```css
--texture-type: paper;
--texture-layer: radial-gradient(80% 60% at 25% 12%, color-mix(in srgb, var(--ink) 3%, transparent), transparent 65%);
--texture-scope: cover;
```

- **立场**：轻纸纹——仪式页一角纸光，阅读页要绝对干净

**G4 shape**

- **圆角**：0
- **hairline**：1px solid color-mix(in srgb, var(--ink) 18%, transparent)，栏线/页脚线的书籍栏隐喻
- **阴影**：无
- **容器造型**：无卡片立场——靠栏线与留白分区；引文块用 3px 粗左边线 accent（见 .mt-pub-pull）；底色块只用 paper-tint 灰档；禁圆角卡、禁阴影
- **高密度容器边界**：paper-tint 灰档面 + 3px ink 粗左边线——书籍边栏提要的形态（引文拉页词汇的容器化）；左边线是栏线立场不是框，accent 左线只留给引文块单焦点

**G5 motion**

- **气质**：editorial
- **强度上限**：默认
- **锚点偏好**：draw-line（栏线/下划线绘出）+ mask-lines（章节标题逐行显影）；数字以字号对比直排为主，count-up 只给真正的 KPI 英雄页
- **节奏偏移**：时长档 +1（一切比默认慢半拍，翻页感）；阶梯步长 ≥90ms
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / persp-in / typewriter / scramble（弹跳、透视与打字机都不属于纸面）
- **fx 许可**：仅 ascii-field

**G8 component**

- **亲和**：图文证据（插图 + 栏线）、巨字宣言（封面题字）、裂屏对开（书籍对开页隐喻）
- **禁忌**：禁连续两页网格矩阵——书页靠栏不靠格；不用加号角标与网格点阵（瑞士系词汇）；图表页须配栏线与衬线标注，不用终端/信号词汇

**G9 motif**

- **词汇**：题花（❧ 字符 + 双侧栏线的居中 ornament，章节末尾/标题下的出版社标记，每页至多一个）/ 首字下沉（::first-letter 绯红大字，占约三行，只许每页首段）/ 引文拉页（3px 绯红粗左边线 + 大号衬线引文）

```css
/* C4 纸与墨 · 装饰母题 */
.mt-pub-orn{display:flex;align-items:center;justify-content:center;gap:16px;color:var(--accent);font-family:var(--font-display);pointer-events:none;user-select:none}
.mt-pub-orn::before,.mt-pub-orn::after{content:"";width:64px;height:1px;background:color-mix(in srgb,var(--ink) 28%,transparent)}
.mt-pub-dropcap::first-letter{font-family:var(--font-display);font-weight:700;font-size:3.2em;line-height:.78;float:left;padding:.06em .14em 0 0;color:var(--accent)}
.mt-pub-pull{border-left:3px solid var(--accent);padding-left:1.2em;font-family:var(--font-display);font-size:1.45em;line-height:1.7}
```

- **禁忌**：题花每页至多一个、只许章节/收束页；首字下沉只许每页首段一段；题花等纯装饰件带 `data-editable-skip`；.mt-pub-dropcap/.mt-pub-pull 加在真实文本上，文本保持可编辑

**Variants 配色变体**

#### 藏青

- **气质**：学术专著与商务出版，沉稳理性——研究、金融、机构报告、严肃长文

```css
--paper:#faf9f7; --paper-tint:#efece7;
--ink:#1a1a1a;   --ink-tint:#2b2b2b;
--accent:#27496D; --accent-on:#faf9f7;
```

#### 黛绿

- **气质**：东方出版社气质，文学与自然——文学、茶文化、博物、人文地理

```css
--paper:#faf9f7; --paper-tint:#efece7;
--ink:#1a1a1a;   --ink-tint:#2b2b2b;
--accent:#2F5D50; --accent-on:#faf9f7;
```

---

## D 系 · 形态与工艺主导

D 系是非颜色主导的方向：质感、形态、字排、母题作为设计感来源的世界采样。
