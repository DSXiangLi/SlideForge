# C3 终端绿

- **id**：c3
- **气质**：暗底磷光绿 + 全栈等宽，CRT 终端的物质感与纪律
- **适用**：技术分享、开发者大会、工程文化、安全与基础设施、极客主题
- **focus**：G1 + G9
- **世界参考**：CRT 磷光终端史（VT100 / 早期 Unix）——黑玻璃屏、绿磷光、扫描线、闪烁光标
- **unforgettable**：提示符后的闪烁光标块——那枚 steps() 跳闪的绿色方块，一眼终端
- **分化声明**：与 c1 分化于 L2/L3/L4/L5/L6——c3 是全栈等宽 + CRT 扫描线质感 + ASCII 框/光标/提示符母题 + 描边终端窗口容器 + typewriter/scramble 签名；c1 是极粗无衬线 + flat 平色 + 直角色块 + scale-pop 硬切

**G1 color**

```css
--paper:#0d1117; --paper-tint:#161b22;
--ink:#e6edf3;   --ink-tint:#1c2128;
--accent:#39d353; --accent-on:#0d1117;
```

- **accent 预算**：内容页 accent 面积 ≤10% 且**点状使用**（光标/关键字/单数据点——绿是信号不是油漆）；满屏绿禁止（荧光伤眼），封面暗底 + 绿字而非绿底；首尾闭环：绿字巨标开场 → 收束页绿字/闪烁光标呼应。

**G2 typography**

```css
--font-display:"SF Mono","JetBrains Mono","Menlo",monospace;
--font-body:"SF Mono","JetBrains Mono","Menlo",monospace;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：全栈等宽统一 400–600，层级靠字号与明暗，不靠字重差
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：等宽两档立场（不走倒挂——mono 无细体）：标题 600；正文 400；14–16px 小字 600
- **标题修饰**：无字重修饰（装饰交给母题：提示符前缀与光标）；关键输出允许 `.mt-term-glow` 磷光晕散（每页 ≤1 处，只给最关键的一行）

**G3 texture**

```css
--texture-type: grain;
--texture-layer: repeating-linear-gradient(0deg, color-mix(in srgb, var(--ink) 4%, transparent) 0 1px, transparent 1px 4px);
--texture-scope: all;
```

- **立场**：CRT 扫描线 = 材质本体——全页许可（scope all），强度烧死不得加深

**G4 shape**

- **圆角**：0–2px（直角为主）
- **hairline**：1px solid color-mix(in srgb, var(--accent) 40%, transparent)，终端描边即磷光线
- **阴影**：磷光晕散体系——文字/描边/光标允许同色低透明辉光（光是这个世界的材质，磷粉在玻璃上晕开）；禁承托投影（屏幕里没有影子）
- **容器造型**：1px 描边终端窗口容器——描边 + 标题栏 hairline（栏内嵌 mono 小字会话名/路径）+ 窗口外缘低透明磷光晕；禁实心色块卡、禁承托投影、禁玻璃拟态
- **高密度容器边界**：描边终端窗口成阵即边界（`.mt-term-box` 骨架 + 标题栏 hairline 分区）——磷光屏上窗口边框即容器，暗底无需面；本主题"面"的等价物不存在，高密度全靠窗阵同构（同 gap 同 padding）

**G5 motion**

- **气质**：techy
- **强度上限**：默认
- **锚点偏好**：typewriter / scramble——techy 限定款即本主题签名锚点：命令行段落打字入场、关键词 scramble 定形；光标闪烁作页面句读
- **节奏偏移**：时长档 −1（快）；阶梯步长 ≤45ms（打字机小步快频）
- **缓动签名**：默认三 token，不覆盖（打字感由 recipe 自身的 steps 节奏承担）
- **禁用**：无
- **fx 许可**：constellation / starfield / ascii-field（particle-drift 太柔禁）

**G8 component**

- **亲和**：网格矩阵（终端表格/仪表墙）、数据英雄（mono 大数字 = 终端输出）、轴与节点（日志流/时间线 = commit log 隐喻）
- **禁忌**：禁圆角大卡片与柔和渐变（不属于玻璃磷光屏）；不用加号角标/网格点阵（瑞士系词汇）；裂屏对开慎用——终端是单窗格世界

**G9 motif**

- **词汇**：ASCII 框（1px 磷光描边 + mono 角件 "+"，终端窗口的装饰骨架）/ 闪烁光标块（行尾的绿色方块 caret，复用骨架 tw-caret steps 跳闪）/ "$ " 提示符前缀（命令行段落行首，accent 色）/ 磷光晕散（`.mt-term-glow`——同色低透明 text-shadow，只给关键输出行与标题字，像磷粉在玻璃上晕开）

```css
/* C3 终端绿 · 装饰母题（光标跳闪复用骨架 tw-caret keyframes，主题块不自带 @keyframes） */
.mt-term-box{position:relative;border:1px solid color-mix(in srgb,var(--accent) 45%,transparent);box-shadow:0 0 28px -2px color-mix(in srgb,var(--accent) 45%,transparent),inset 0 0 16px color-mix(in srgb,var(--accent) 10%,transparent)}
.mt-term-box::before{content:"+";position:absolute;top:-.6em;left:-.35em;color:var(--accent);font-family:var(--font-mono);line-height:1}
.mt-term-box::after{content:"+";position:absolute;bottom:-.6em;right:-.35em;color:var(--accent);font-family:var(--font-mono);line-height:1}
.mt-term-caret{display:inline-block;width:.55em;height:1em;margin-left:.08em;background:var(--accent);vertical-align:-.12em;box-shadow:0 0 12px color-mix(in srgb,var(--accent) 85%,transparent);animation:tw-caret 1s steps(1) infinite}
.mt-term-glow{text-shadow:0 0 16px color-mix(in srgb,var(--accent) 75%,transparent),0 0 42px color-mix(in srgb,var(--accent) 35%,transparent)}
.mt-term-prompt::before{content:"$ ";color:var(--accent);font-weight:600}
```

- **禁忌**：ASCII 框角件只许对角两枚，禁四角全标（过密即噪音）；光标块每页至多两处（句读不是撒布）；提示符前缀只许命令行语义的段落；辉光强度烧死不得加深——磷光晕散永不糊住字形边缘（可读性 > 氛围）；母题件一律 `data-editable-skip`

**bake_brief**

```json
{
  "visual_direction": "CRT phosphor terminal poster, VT100-era Unix console materiality, green-on-black phosphor signal, full monospace typography, subtle scanline texture, ASCII box-drawing frames, command-line session ceremony, engineering discipline with hacker-culture restraint",
  "palette_rule": "green is signal, not paint: phosphor green only as text, hairlines, cursor blocks and single data points on a near-black screen; large green fills forbidden (phosphor burn); the screen stays deep charcoal; monochrome phosphor discipline — no second accent hue, no rainbow syntax highlighting",
  "typography_bake": "主标题重构词汇：全栈等宽立场——标题以等宽 600 重构，字号与明暗建层级而非字重差；光标融字——行尾嵌一枚实心磷光光标块作句读；提示符融字——标题行首冠 '$ ' 前缀；续行缩进——长标题第二行缩进如命令续行；扫描线穿字——水平扫描线低透明掠过字面；字形可有极轻微磷光晕散，禁辉光糊字",
  "uplift": "升维路径（HTML 做不到的物理维度）：CRT 玻璃屏的物质性——磷光字符的余晖发光（辉光随字符边缘真实衰减，不是外发光滤镜）；球面屏玻璃的微妙反光与曲率（屏幕边缘自然暗角）；扫描线的物理纵深——扫描线在玻璃面之下、字符磷光在玻璃面之上，两层有前后关系；磷光剂颗粒感与暗室里屏幕的微弱环境反光——HTML 的扁平绿字符在此获得荧光物质的物理性",
  "allowed": "monospace type at all levels, ASCII box-drawing frames with at most two diagonal corner '+' marks, solid phosphor cursor blocks, '$ ' prompt prefixes, uniform subtle scanlines, terminal window title bars with tiny session names, log-stream and commit-line motifs, faint phosphor glow, flat near-black screen fields",
  "avoid": "photorealism, rounded cards, soft gradients, mesh gradients, aurora blobs, glass morphism, serif or proportional type, rainbow syntax colors, multiple accent hues, large green backgrounds, matrix falling-character rain, neon purple/blue cyberpunk palette, emoji, icon rows, cartoon hackers, hoodie silhouettes, fake OS logos or real brand chrome",
  "layout_blueprints": {
    "cover": [
      {"position": "top edge", "count": 1, "labels": ["细标题栏小字会话名"]},
      {"position": "center-left", "count": 1, "labels": ["'$ ' 提示符前缀 + 等宽重构巨字标题（长题续行缩进）"]},
      {"position": "title line end", "count": 1, "labels": ["实心磷光光标块句读"]},
      {"position": "background", "count": 1, "labels": ["均匀低透明扫描线 + 可选 ASCII 框（对角两枚角件）"]},
      {"position": "bottom", "count": 2, "labels": ["一行副题（命令注释语气）", "一行小字署名/日期"]}
    ],
    "divider": [
      {"position": "center-left", "count": 1, "labels": ["章节序号巨大等宽数字"]},
      {"position": "below number", "count": 1, "labels": ["一行命令行（如 '$ cd <章节>'）"]},
      {"position": "line end", "count": 1, "labels": ["光标块"]},
      {"position": "background", "count": 1, "labels": ["扫描线 + 可选 ASCII 框"]}
    ],
    "key-message": [
      {"position": "top edge", "count": 1, "labels": ["细标题栏会话名"]},
      {"position": "center", "count": 1, "labels": ["2–8 字等宽重构核心词"]},
      {"position": "around typography", "count": 1, "labels": ["恰一个主导隐喻以 ASCII/box-drawing 词汇环绕字型"]},
      {"position": "bottom", "count": 1, "labels": ["一行 log 式注脚"]}
    ],
    "analysis": [
      {"position": "top", "count": 1, "labels": ["标题栏（会话名 + 页题）"]},
      {"position": "main", "count": 1, "labels": ["2–4 个同构终端窗口（同 gap 同 padding），各带细标题栏"]},
      {"position": "inside windows", "count": 3, "labels": ["窗内模块一", "窗内模块二", "窗内模块三"]},
      {"position": "bottom", "count": 1, "labels": ["可选 '> ' 前缀总结行"]}
    ]
  },
  "rendering_constraints": [
    "The page must read as a real terminal session screen, not a generic dark tech template, not a movie hacker cliche.",
    "All type is monospace; hierarchy via size and brightness only — never weight contrast or a second color.",
    "Green stays point-like and small-area; large green fields forbidden; no second accent hue.",
    "The title must be reconstructed with prompt prefix, cursor block or scanline integration — plain big text is a failure.",
    "Exactly one dominant metaphor per page, expressed in ASCII/box-drawing vocabulary.",
    "Scanlines subtle and uniform; glow never blurs glyph edges into illegibility.",
    "Cover/divider/key-message pages: at most 4 text elements; analysis pages: 2–4 uniform windows with identical gaps.",
    "Window corner '+' marks: at most two diagonal ones per frame — four corners is noise.",
    "No photorealistic hardware, no people, no matrix rain, no purple/blue neon.",
    "Do not invent OS logos, brand marks, or extra UI chrome beyond one thin title bar per window."
  ]
}
```

**Variants 配色变体**

#### 琥珀磷光

- **气质**：后期 amber 终端（VT220 琥珀屏），暖调怀旧——计算机史、复古计算、硬件文化

```css
--paper:#0d1117; --paper-tint:#161b22;
--ink:#e6edf3;   --ink-tint:#1c2128;
--accent:#FFB000; --accent-on:#0d1117;
```

#### 白磷光

- **气质**：P1 白磷光终端，最冷最素，接近单色打印纸带——极简技术文档、规范与协议主题

```css
--paper:#0d1117; --paper-tint:#161b22;
--ink:#e6edf3;   --ink-tint:#1c2128;
--accent:#F0F6FC; --accent-on:#0d1117;
```

- **accent 预算**：白磷光 accent 与 ink 近色——点状纪律不变，强调靠亮度差与光标位置；其余同基底口径
