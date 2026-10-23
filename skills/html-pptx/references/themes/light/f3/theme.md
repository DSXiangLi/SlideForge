# F3 暮色长镜

- **id**：f3
- **气质**：暮蓝大地 + 落日色带 + 宽字距片名——一页就是一帧电影，暗角收拢视线
- **适用**：品牌故事、年度叙事、发布会开场、纪录与人文、旅行与地产大片
- **focus**：G3 + G1
- **世界参考**：黄金时刻（golden hour）电影摄影与史诗片海报——低色阳、大气透视、画幅暗角
- **unforgettable**：地平线色带——仪式页底部一条日落渐变带压住画幅，页面定格为一帧
- **分化声明**：与 d2 分化于 L1/L2/L4/L5/L6——d2 是暗房琥珀 + 细衬线斜体 + 齿孔/光束/显影晕母题 + 无框辉光托底 + blur-in 显影签名；f3 是暮色橙阳 + 宽字距片名衬线 + 地平线色带/渐变字/场次时间码母题 + 亮度阶梯薄面容器 + 慢淡入长镜节奏（count-up 全禁）

**G1 color**

```css
--paper:#12101A; --paper-tint:#1C1826;
--ink:#F4EBDC;   --ink-tint:#2A2333;
--accent:#E8753A; --accent-on:#12101A;
```

- **accent 预算**：内容页 ≤8%——落日是远处的光，不落在文字上：正文文字永为 ink，accent 只给地平线色带/关键数字/单焦点；满屏色带仅封面/收束特权；首尾闭环：封面色带在画幅低位 → 收束页色带升至高位（太阳落下去）。

**G2 typography**

```css
--font-display:"Songti SC","Noto Serif SC","STSong",serif;
--font-body:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
--font-mono:"SF Mono","JetBrains Mono","Menlo",monospace;
```

- **字重倾向**：标题 400–500、正文 400——片名的力量来自字距不是字重
- **字号对比**：主标题:正文 ≥8:1（低密度）；高密度 ≥5:1
- **字重映射**：片名立场：≥77px→400–500；35–76px→500；正文 400；14–16px 小字 500–600
- **标题修饰**：拉丁标题全大写 + letter-spacing .18em（片名字卡）；中文标题字距 +.12em；主标题可用 `.mt-dsk-grad` 暮光渐变字（每 deck ≤2 页：封面 + 收束）
- **metric_fallback**：display→Songti SC/Noto Serif SC；body→PingFang SC/Noto Sans SC；mono→SF Mono/Menlo

**G3 texture**

```css
--texture-type: aura;
--texture-layer: linear-gradient(180deg, transparent 52%, color-mix(in srgb, var(--accent) 9%, transparent) 74%, color-mix(in srgb, var(--accent) 22%, transparent) 100%), radial-gradient(115% 95% at 50% 42%, transparent 56%, color-mix(in srgb, black 52%, transparent) 100%);
--texture-scope: cover;
```

- **立场**：暮色 + 暗角 = 仪式页的画框——地平线色带压页底、暗角收四缘（black 只作光学暗角机制，不参与配色）；正文页纯暮蓝，层级靠亮度阶梯

**G4 shape**

- **圆角**：2–6px（电影画幅是硬朗的矩形）
- **hairline**：1px color-mix(in srgb, var(--ink) 20%, transparent)，少而克制——字幕层细线
- **阴影**：无投影——纵深靠大气（色带/暗角/亮度阶梯），不靠承托
- **容器造型**：亮度阶梯薄面（color-mix(in srgb, var(--ink) 4–7%, transparent) 微亮面）+ 顶边 1px 受光线；禁玻璃拟态（这个世界没有玻璃，只有空气）、禁实心亮卡
- **高密度容器边界**：薄面 + 顶边受光线成阵，间距恒定；列间分区靠留白与暗角，不靠描边

**G5 motion**

- **气质**：calm
- **强度上限**：低
- **锚点偏好**：fade/rise-in 慢淡入（长镜头不剪辑）；数字静排——count-up 全禁（电影不打计数器）
- **节奏偏移**：时长档 +1（一切缓慢，镜头呼吸）
- **缓动签名**：默认三 token，不覆盖
- **禁用**：scale-pop / wipe-clip / scramble / typewriter（一切"动效感"都破坏长镜幻觉）
- **fx 许可**：全禁

**G8 component**

- **亲和**：巨字宣言（片名页）、裂屏对开（天/地、明/暗的地平线构图）、图文证据（剧照 + 字幕式图注）
- **禁忌**：禁密集网格矩阵（画面要呼吸）；图表压暗单色描线（图表在电影里是字幕层，不是主体）

**G9 motif**

- **词汇**：地平线色带（`.mt-dsk-horizon`——页底日落渐变带，仪式页专属，每页一条）/ 暮光渐变字（`.mt-dsk-grad`——标题渐变色 background-clip:text，封面与收束限定）/ 场次时间码（`.mt-dsk-code`——mono 小字方括号场次标记，只许页角一枚）

```css
/* F3 暮色长镜 · 装饰母题 */
.mt-dsk-horizon{position:absolute;left:0;right:0;bottom:0;height:22vh;pointer-events:none;background:linear-gradient(180deg,transparent,color-mix(in srgb,var(--accent) 26%,transparent) 78%,color-mix(in srgb,var(--accent) 45%,transparent))}
.mt-dsk-grad{background:linear-gradient(100deg,var(--ink) 30%,color-mix(in srgb,var(--accent) 75%,var(--ink)));-webkit-background-clip:text;background-clip:text;color:transparent}
.mt-dsk-code{font-family:var(--font-mono);font-size:13px;letter-spacing:.22em;opacity:.55;pointer-events:none}
.mt-dsk-code::before{content:"[ "}
.mt-dsk-code::after{content:" ]"}
```

- **禁忌**：色带只在页底且每页一条（升到半空即热气球）；渐变字每 deck ≤2 页；时间码只许页角；母题件一律 `data-editable-skip`

**Variants 配色变体**

#### 黎明

- **气质**：粉金晨光——色带从橙转粉，夜的一侧未退尽，适合新开始、发布与希望叙事

```css
--paper:#101420; --paper-tint:#1A2030;
--ink:#EDEFF5;   --ink-tint:#262E42;
--accent:#E8957C; --accent-on:#101420;
```

#### 午夜

- **气质**：蓝调时刻（blue hour）——太阳完全落下后的靛蓝，最冷最静，适合科幻、宇宙、深海与悬疑叙事

```css
--paper:#0A0E18; --paper-tint:#131A28;
--ink:#E5EAF4;   --ink-tint:#1D2636;
--accent:#6B8AFF; --accent-on:#0A0E18;
```

## G 系 · 色彩结构（J2 期新增）

G 系是色彩轴补完：A–F 系的彩色纪律是"单 accent 锚点 + color-mix 派生"，G 系证明色彩结构本身即风格——彩色满铺底、粉彩×荧光标注、彩色墨、互补双色对撞。多色不是开关是世界：每主题的色板封闭、分配规则与防花纪律写进 G1「多色立场」，规格见 `docs/design/theme-multi-hue.md`。
