# E11 票据

- **id**：e11
- **气质**：纸白票纸 + 墨黑字段 + 航司蓝 accent，登机牌与票根的工业浪漫与出发感
- **适用**：旅行与出行、活动票务、产品发布（"启程/上线"叙事）、物流交通行业、流程与清单型内容
- **focus**：G9 + G2
- **世界参考**：航空登机牌与演出票根（IATA 登机牌 / 热敏纸演出票）——撕线齿孔、条码、mono 大写字段、副券存根
- **unforgettable**：撕线副券——一条齿孔虚线把页面撕出主券/副券，条码压底，一眼登机牌
- **分化声明**：与 c3 分化于 L1/L2/L3/L4/L6——e11 是纸白浅底的票纸世界，c3 是暗底磷光屏（L1）；e11 的 mono 只用于字段标签与票据数据（正文用黑体），c3 是全栈等宽（L2）；e11 是 flat 干净票纸，c3 是 CRT 扫描线 grain/all（L3）；e11 母题是齿孔撕线/条码/副券字段行，c3 是 ASCII 框/闪烁光标/提示符（L4）；e11 签名动效是 wipe-clip 撕开式揭示，c3 是 typewriter/scramble 打字机（L6）

**G1 color**

```css
--paper:#FDFCF9; --paper-tint:#F2F0E8;
--ink:#1D2129;   --ink-tint:#3A3F4A;
--accent:#0F4C81; --accent-on:#FDFCF9;
```

- **accent 预算**：内容页 accent 面积 ≤8%——蓝只给：头带横条、关键字段值（班次/座位号/日期）、条码上方一行字；封面/收束允许 accent 头带横贯版面上缘（≤30%，登机牌头带是它的原生形态），不满屏；首尾闭环：封面头带 + 条码开场 → 收束页同位头带 + 条码呼应。

**G2 typography**

```css
--font-display:"Arial Black","Avenir Next Heavy","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：display 700–900 极粗无衬线、正文 400–500 黑体；mono 字段 500–700 + 大写 + 加宽字距——票据的层级是"字段纪律"而非字体重量游戏
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：极粗标题立场：≥77px→800；35–76px→700；正文 400；14–16px 小字 500–600
- **标题修饰**：mono 小号大写字段行压题（LABEL / VALUE 对，见 G9 `.mt-tix-field`）——标题上方一行 "FLIGHT / PPTX-0926" 式字段是原生修饰

**G3 texture**

```css
--texture-type: flat;
--texture-layer: none;
--texture-scope: cover;
```

- **立场**：flat 即质感立场——登机牌是热敏打印的工业纸面，纹理交给齿孔与条码的几何节奏，纸纹多余

**G4 shape**

- **圆角**：0–4px（票据是工业切片，几乎不用圆角）
- **hairline**：1px solid color-mix(in srgb, var(--ink) 30%, transparent)，字段分隔线即票面框线
- **阴影**：无——票纸是平的，禁弥散投影
- **容器造型**：票据容器——1px 描边 + 齿孔分隔（`.mt-tix-perf`）+ 副券区（`.mt-tix-stub` 淡 accent 底）；禁圆角大卡、禁弥散阴影、禁玻璃拟态
- **高密度容器边界**：票据容器成阵——1px 描边票面 + 字段分隔线即边界（票面框线是工业印刷的原生形态）；主券/副券撕线切大区，票内字段行 hairline 细分，框阵同距同构如值机柜台

**G5 motion**

- **气质**：professional
- **强度上限**：默认
- **锚点偏好**：wipe-clip 是签名锚点——撕开的揭示感，副券与字段像被撕出来；数据页 fill-bar 亲和（登机进度条隐喻）；其余元素 rise-in
- **节奏偏移**：不偏移；阶梯步长 ≤60ms（值机柜台的高效节奏）
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / magnetic / typewriter / scramble（弹跳吸附与打字机都不属于票纸——mono 字段直接落位，不打字）
- **fx 许可**：全禁（票面是印刷品，无仪式层）

**G8 component**

- **亲和**：轴与节点（航线/时刻 = 行程时间线的原生隐喻）、网格矩阵（值机柜台式字段阵列）、数据英雄（航班号/座位号式 mono 大数字）
- **禁忌**：不用竖排题字条/Ghost 残影（杂志系词汇）、不用圆角弥散卡（奶油系词汇）；裂屏对开慎用——票据是单张连续票面，对开请用主券/副券撕线代替

**G9 motif**

- **词汇**：齿孔撕线（`.mt-tix-perf`：dashed 虚线 + 两端半圆缺口，把票面撕出主券/副券，每页至多一条）/ 条码（`.mt-tix-barcode`：repeating-linear-gradient 粗细交替竖条，只许页底一条横贯）/ 票根字段行（`.mt-tix-field`：mono 大写小字 LABEL/VALUE 对，文本载体类母题）/ 副券区（`.mt-tix-stub`：淡 accent 底 + 左描边的存根区）

```css
/* E11 票据 · 装饰母题 */
.mt-tix-perf{position:relative;border-top:2px dashed color-mix(in srgb,var(--ink) 50%,transparent)}
.mt-tix-perf::before,.mt-tix-perf::after{content:"";position:absolute;top:-10px;width:20px;height:20px;border-radius:50%;background:var(--paper)}
.mt-tix-perf::before{left:-10px}
.mt-tix-perf::after{right:-10px}
.mt-tix-barcode{height:44px;pointer-events:none;user-select:none;background-image:repeating-linear-gradient(90deg,var(--ink) 0 2px,transparent 2px 5px,var(--ink) 5px 6px,transparent 6px 11px,var(--ink) 11px 14px,transparent 14px 17px,var(--ink) 17px 18px,transparent 18px 23px)}
.mt-tix-field{font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.08em;line-height:1.4}
.mt-tix-field small{display:block;font-size:.55em;font-weight:500;color:color-mix(in srgb,var(--ink) 55%,transparent);letter-spacing:.18em}
.mt-tix-field b{font-weight:700;color:var(--ink)}
.mt-tix-stub{background:color-mix(in srgb,var(--accent) 8%,var(--paper));border-left:1px solid color-mix(in srgb,var(--ink) 35%,transparent);padding:1em 1.2em}
```

- **禁忌**：齿孔撕线每页至多一条（横竖皆可，只一条——撕两次票就废了）；条码只许页底一条横贯，禁进图表区、禁竖放；字段行 LABEL 永远大写 mono，禁中文进 LABEL 位（中文进 VALUE）；`.mt-tix-field` 是文本载体类母题——样式由类承担，文本保持可编辑；`.mt-tix-perf`/`.mt-tix-barcode` 一律 `data-editable-skip`

**Variants 配色变体**

#### 铁路绿

- **气质**：绿皮车与 JR 线路色——铁道票的怀旧工业感，比航司蓝更慢更有人情——铁路/公路旅行、城市漫游、复古交通主题

```css
--paper:#FDFCF9; --paper-tint:#F2F0E8;
--ink:#1D2129;   --ink-tint:#3A3F4A;
--accent:#2F6B4F; --accent-on:#FDFCF9;
```

#### 演出粉

- **气质**：livehouse 与音乐节热敏票根——高饱和演出粉，票务的躁动与收藏欲——演出、赛事、潮流活动、青年文化

```css
--paper:#FDFCF9; --paper-tint:#F2F0E8;
--ink:#1D2129;   --ink-tint:#3A3F4A;
--accent:#D6336C; --accent-on:#FDFCF9;
```
