# 材料合成词汇表（Compositing Recipes）

> 读者：执行主题重建 / 新建主题的 AI coding agent。
> 用途：G3 质感层升级与 G9 母题块的材料配方选型——每个配方是"用 CSS 合成技术模拟一种物理材料"的完整实现。
>
> 设计原理：材料语言是视觉出挑的第一来源；主题身份是双层的——**可编辑身份**（色+字+形）穿透两条导出轨道，**保真身份**（材质+光+合成，本词汇表的全部配方）只穿透保真轨，可编辑轨丢失为预期行为。
>
> 使用纪律：
> - 主题的 G3 `css_recipes` 字段从本表选型（sync-themes.mjs 校验配方名存在）；配方是词汇不是枷锁，参数可按主题微调，但**材料语义不变**——film-grain 永远是乳剂颗粒，不是装饰噪点。
> - 所有色值只许 `var(--*)` / `color-mix()` 引用主题 token，禁字面 hex；data-URI 内的 SVG 用 `%23` 转义 `#`。
> - 纹理类配方是**背景配给制**公民：默认只铺仪式页（`cover-page`），正文页须逐页 `texture-on` 显式落码，且主题的 `--texture-scope` 须声明 `all`。
> - 每页材料层 ≤2 个配方叠加（如 film-grain + light-leak）——材料是舞台不是演员，堆三层以上画面变脏。

## 配方 1：overprint-flat（珐琅/丝网印刷平面）

- **材料**：涂漆钢板 / 搪瓷牌面上的丝网印刷油墨——平整但有物理厚度，两色交叠处油墨叠印出第三色
- **CSS 实现**：

```css
/* 父容器开隔离，叠印只发生在指定层之间 */
.print-stack{isolation:isolate}
.print-stack .layer{mix-blend-mode:multiply}
/* 两块 accent/ink 色面错位交叠，交叠区自然叠出深色——印刷的物理行为 */
```

- **适用层**：背景色面 / 容器 / 装饰色块
- **密度兼容**：全密度
- **导出**：保真轨保留（可能栅格化）；可编辑轨丢失
- **主题亲和**：B1 瑞士、E2 蓝图、E4 包豪斯

## 配方 2：riso-misreg（孔版套色错位）

- **材料**：孔版印刷（Risograph）的套色不准——同一图形的两个色版错位 2–4px，边缘露出另一色
- **CSS 实现**：

```css
.riso{position:relative;isolation:isolate}
.riso,.riso::before{/* 同一形状两份 */}
.riso::before{content:"";position:absolute;inset:0;transform:translate(3px,3px);
  background:var(--accent-2);mix-blend-mode:multiply;z-index:-1}
/* 主体 accent 色 + ::before 偏移 accent-2 色，multiply 叠印 */
```

- **适用层**：装饰图形 / 大字号标题（低密度）/ 色块
- **密度兼容**：全密度（标题级用法仅低密度）
- **导出**：保真轨保留；可编辑轨丢失错位层
- **主题亲和**：E1 孔版（原生）、G5 三色旬刊

## 配方 3：halftone-dots（半调网点）

- **材料**：凸版/报纸印刷的半调网点——色调深浅由网点大小与密度表达
- **CSS 实现**：

```css
/* 细网点（正文页底纹级） */
.halftone-fine{background-image:radial-gradient(circle at 1px 1px,
  color-mix(in srgb,var(--ink) 8%,transparent) 1px,transparent 1.6px);
  background-size:4px 4px}
/* 粗网点（仪式页海报级，点径随密度意图放大） */
.halftone-bold{background-image:radial-gradient(circle at 2px 2px,
  color-mix(in srgb,var(--ink) 22%,transparent) 2px,transparent 2.8px);
  background-size:9px 9px}
```

- **适用层**：背景 / 容器局部 / 装饰带
- **密度兼容**：细网点全密度；粗网点仅低密度仪式页
- **导出**：保真轨保留；可编辑轨丢失
- **主题亲和**：E8 号外、E1 孔版、D4 黄铜年代、G4 靛墨黄页

## 配方 4：paper-fiber（纸张纤维）

- **材料**：棉纸/卡纸的纤维肌理——细碎方向性纤维在侧光下的明暗
- **CSS 实现**：

```css
.paper-fiber{background-image:url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22240%22 height=%22240%22%3E%3Cfilter id=%22f%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.55 0.75%22 numOctaves=%222%22 stitchTiles=%22stitch%22/%3E%3CfeColorMatrix type=%22saturate%22 values=%220%22/%3E%3C/filter%3E%3Crect width=%22240%22 height=%22240%22 filter=%22url(%23f)%22 opacity=%220.05%22/%3E%3C/svg%3E")}
/* baseFrequency 两个分量拉开差值 = 纤维的方向性；opacity 0.04–0.06 */
```

- **适用层**：背景（页面级）
- **密度兼容**：全密度（浅底主题）；暗底主题慎用（纤维在暗底上发灰）
- **导出**：保真轨保留（作为图片渲染）；可编辑轨丢失
- **主题亲和**：C4 纸与墨、D1 奶油物语、D4 黄铜年代、A1 牛皮纸变体

## 配方 5：emboss-deboss（击凸/压凹）

- **材料**：棉纸上的击凸（凸出纸面）与压凹（陷入纸面）——靠一明一暗两条 1px 偏移边制造厚度
- **CSS 实现**：

```css
/* 压凹（deboss）：上内影深 + 下外光浅——光从上方来，凹进纸里 */
.deboss{box-shadow:inset 0 1px 0 color-mix(in srgb,var(--ink) 14%,transparent),
  0 1px 0 color-mix(in srgb,var(--paper) 60%,transparent)}
/* 击凸（emboss）：方向相反——下内影深 + 上外光浅 */
.emboss{box-shadow:inset 0 -1px 0 color-mix(in srgb,var(--ink) 14%,transparent),
  0 -1px 0 color-mix(in srgb,var(--paper) 60%,transparent)}
/* 文字压印（letterpress）：亮底主题下正文下缘一道纸色高光 */
.letterpress-text{text-shadow:0 1px 0 color-mix(in srgb,var(--paper) 55%,transparent)}
```

- **适用层**：容器边缘 / 标题文字（letterpress 变体）
- **密度兼容**：全密度；letterpress 文字变体仅标题字号
- **导出**：保真轨保留；可编辑轨丢失（box-shadow 本来也不导出）
- **主题亲和**：D1 奶油物语、C4 纸与墨、E11 票据

## 配方 6：watercolor-bleed（水彩晕染）

- **材料**：湿画法水彩——颜料在湿纸面上洇开，边缘不规则、中心浓边缘淡
- **CSS 实现**：

```css
.wc-blob{position:absolute;width:46%;aspect-ratio:1.2;pointer-events:none;
  background:radial-gradient(48% 52% at 42% 46%,
    color-mix(in srgb,var(--accent) 26%,transparent),
    color-mix(in srgb,var(--accent) 9%,transparent) 55%,transparent 72%);
  filter:blur(14px);mix-blend-mode:multiply}
/* 2–3 团错位的 blob 叠出洇开层次；blur 8–20px 按团大小调；multiply 让叠处自然加深 */
```

- **适用层**：背景 / 插图位底层
- **密度兼容**：仅低密度仪式页（晕染团需要呼吸空间）
- **导出**：保真轨保留（filter 栅格化）；可编辑轨丢失
- **主题亲和**：C2 暗夜植物园、D3 手绘油彩

## 配方 7：film-grain（胶片颗粒）

- **材料**：银盐乳剂层的微晶体颗粒——不是数字噪点，是相纸的物理肌理
- **CSS 实现**：

```css
/* 细颗粒（正文页，baseFrequency 0.6） */
.grain-fine{background-image:url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22240%22 height=%22240%22%3E%3Cfilter id=%22g%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.6%22 numOctaves=%222%22 stitchTiles=%22stitch%22/%3E%3CfeColorMatrix type=%22saturate%22 values=%220%22/%3E%3C/filter%3E%3Crect width=%22240%22 height=%22240%22 filter=%22url(%23g)%22 opacity=%220.5%22/%3E%3C/svg%3E");opacity:.06}
/* 粗颗粒（仪式页，baseFrequency 0.9）；颗粒层独立元素、pointer-events:none、opacity 0.03–0.06 */
/* 暗底主题把颗粒层 mix-blend-mode:overlay——颗粒叠进暗调不发灰 */
```

- **适用层**：背景（页面级颗粒层，独立绝对定位元素或 ::after）
- **密度兼容**：全密度（细颗粒）；粗颗粒仅仪式页
- **导出**：保真轨保留（作为图片渲染）；可编辑轨丢失
- **主题亲和**：D2 柔光暗房、F3 暮色长镜、E8 号外报纸

## 配方 8：light-leak（漏光/光斑）

- **材料**：胶片漏光——片盒缝隙漏进的一团暖光，边缘柔和、只存在于画面边缘
- **CSS 实现**：

```css
.leak{position:absolute;width:52%;aspect-ratio:1;pointer-events:none;
  background:radial-gradient(50% 50% at 50% 50%,
    color-mix(in srgb,var(--accent) 55%,transparent),transparent 70%);
  filter:blur(40px);mix-blend-mode:screen;opacity:.14}
/* 只许页面上缘或侧缘（如 top:-18%;right:-12% 让光斑被边缘裁切）；blur 30–50px；opacity ≤0.15 */
```

- **适用层**：背景（页面级光效层）
- **密度兼容**：仅低密度仪式页；每页至多 1 个
- **导出**：保真轨保留（filter 栅格化）；可编辑轨丢失
- **主题亲和**：D2 柔光暗房、F2 霓虹夜行、F3 暮色长镜

## 配方 9：spotlight-mask（聚光灯）

- **材料**：舞台聚光灯——黑暗中一束光罩住主角，四周沉入暗部
- **CSS 实现**：

```css
/* 暗角罩层：全页深色罩 + 径向透明孔 = 聚光区 */
.spotlight{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(58% 62% at 50% 42%,
    transparent 26%,color-mix(in srgb,var(--paper) 72%,transparent) 78%)}
/* 或对主角元素反向用 mask-image:radial-gradient(...) 让它只亮在光区内 */
```

- **适用层**：背景光效层 / 主角元素遮罩
- **密度兼容**：仅低密度仪式页与 key-message 页
- **导出**：保真轨保留（mask 转 clipping path / 栅格化）；可编辑轨丢失
- **主题亲和**：C1 信号黑、D2 柔光暗房、F3 暮色长镜

## 配方 10：aged-fade（做旧褪色）

- **材料**：老相纸/老海报的泛黄褪色——银盐氧化、油墨褪彩，对比度微微塌陷
- **CSS 实现**：

```css
/* 作用于背景层（独立元素，不影响文字可读性）：微量 sepia + 微降对比 */
.aged{position:absolute;inset:0;pointer-events:none;
  background:color-mix(in srgb,var(--accent) 5%,transparent);
  mix-blend-mode:soft-light;filter:sepia(.08) contrast(.97)}
/* 可加一道极轻 vignette：radial-gradient(120% 100% at 50% 50%,transparent 70%,color-mix(in srgb,var(--ink) 10%,transparent)) */
```

- **适用层**：背景（页面级色调层）
- **密度兼容**：仅低密度仪式页（正文页做旧会拖累可读性）
- **导出**：保真轨保留（栅格化）；可编辑轨丢失
- **主题亲和**：D2 柔光暗房、D4 黄铜年代、E8 号外报纸、C4 纸与墨

## 配方 11：engraved-line（金属刻痕）

- **材料**：刻刀在金属/漆面上划出的凹线——一道深色刻槽 + 一道紧邻的受光亮边
- **CSS 实现**：

```css
/* 刻线分隔：1px 深线 + 1px 亮边紧贴其下 */
.eng-rule{height:0;border-top:1px solid color-mix(in srgb,var(--ink) 34%,transparent);
  box-shadow:0 1px 0 color-mix(in srgb,var(--paper) 18%,transparent)}
/* 刻槽容器：border + inset 内凹影，像从钢板上刻出来的框 */
.eng-box{border:1px solid color-mix(in srgb,var(--accent) 55%,transparent);
  box-shadow:inset 0 1px 2px color-mix(in srgb,var(--ink) 45%,transparent),
    inset 0 -1px 0 color-mix(in srgb,var(--accent) 22%,transparent)}
/* 刀痕肌理（贴边装饰带）：repeating-linear-gradient 细线 */
.eng-hatch{background:repeating-linear-gradient(90deg,
  color-mix(in srgb,var(--accent) 30%,transparent) 0 1px,transparent 1px 5px)}
```

- **适用层**：容器边框 / 分隔线 / 装饰带
- **密度兼容**：全密度
- **导出**：保真轨保留；可编辑轨丢失 inset 影（border 保留）
- **主题亲和**：D4 黄铜年代、E3 装饰艺术、E2 蓝图

## 配方 12：ink-bleed（墨迹洇开）

- **材料**：毛笔/印章落在宣纸上的洇墨——笔画边缘微微扩散出毛刺
- **CSS 实现**：

```css
/* feMorphology dilate 扩张 + 微 blur：作用于文字或实心形状
   注意：filter:url(#id) 要求 filter 定义以内联 <svg> 存在于同一文档
   （data-URI 外部 filter 引用浏览器支持不稳），生成侧在 deck 里放一段
   隐藏的 <svg><filter id="ink"><feMorphology operator="dilate" radius="0.6"/>
   <feGaussianBlur stdDeviation="0.4"/></filter></svg> */
.ink-bleed{filter:url(#ink)}
```

- **适用层**：标题文字 / 印章类母题
- **密度兼容**：仅低密度（标题字号才看得出洇开）
- **导出**：保真轨保留（栅格化）；可编辑轨丢失
- **主题亲和**：C4 纸与墨、E7 浮世绘、D3 手绘油彩

## 配方 13：torn-edge（撕裂边缘）

- **材料**：手撕毛边纸——不规则锯齿轮廓，纤维参差的白色边
- **CSS 实现**：

```css
/* clip-path 多点多边形模拟撕口（点越多越碎，12–20 点自然） */
.torn{clip-path:polygon(0 4%,3% 0,8% 3%,14% 1%,21% 4%,27% 0,34% 3%,41% 1%,
  48% 4%,55% 0,62% 3%,69% 1%,76% 4%,83% 0,90% 3%,97% 1%,100% 4%,
  100% 96%,97% 100%,90% 97%,83% 99%,76% 96%,69% 100%,62% 97%,55% 99%,
  48% 96%,41% 100%,34% 97%,27% 99%,21% 96%,14% 100%,8% 97%,3% 99%,0 96%)}
/* 只撕一侧更克制：polygon 一侧走直线 */
```

- **适用层**：容器 / 图片遮罩 / 装饰纸带
- **密度兼容**：全密度（容器级）；整页撕边仅低密度
- **导出**：保真轨保留（clipping path）；可编辑轨丢失（变回矩形）
- **主题亲和**：E1 孔版、拼贴/zine 方向、G2 腮红荧光笔

## 配方 14：reflection-fade（倒影渐隐）

- **材料**：镜面/水面倒影——主体的垂直翻转副本向下渐隐
- **CSS 实现**：

```css
.reflect-wrap{position:relative}
.reflect-wrap .reflection{position:absolute;top:100%;left:0;right:0;
  transform:scaleY(-1);opacity:.28;pointer-events:none;
  -webkit-mask-image:linear-gradient(to top,transparent 62%,black);
  mask-image:linear-gradient(to top,transparent 62%,black)}
/* 倒影内容是主体的复制（文本可用 aria-hidden 副本），F2 霓虹已有实现，此处泛化 */
```

- **适用层**：标题 / 焦点图形的倒影
- **密度兼容**：仅低密度仪式页与 key-message 页
- **导出**：保真轨保留；可编辑轨丢失
- **主题亲和**：F2 霓虹夜行（原生）、F1 浮光玻璃、F3 暮色长镜

## 配方 15：organic-stroke（手绘笔触）

- **材料**：手绘线条的抖动与粗细变化——不是完美的矢量线，是手拿着笔画出来的
- **CSS 实现**：

```css
/* feTurbulence + feDisplacementMap 作用于描边，线条产生有机抖动
   同 ink-bleed：filter 定义须内联在 deck 的 <svg> 中
   <filter id="wobble"><feTurbulence type="fractalNoise" baseFrequency="0.02"
   numOctaves="3" result="n"/><feDisplacementMap in="SourceGraphic" in2="n"
   scale="6"/></filter> */
.organic{filter:url(#wobble)}
/* scale 3–8 控制抖动幅度；边框/下划线/箭头线条适用，正文文字禁用 */
```

- **适用层**：装饰线 / 边框 / 手绘箭头
- **密度兼容**：全密度（装饰线级）
- **导出**：保真轨保留（栅格化）；可编辑轨丢失
- **主题亲和**：D3 手绘油彩、G2 腮红荧光笔、C2 暗夜植物园
