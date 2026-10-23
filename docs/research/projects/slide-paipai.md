# slide-paipai 深度调研

> 一句话定位：一套内容定义、双后端渲染的自建排版引擎（PIL 页图 + python-pptx 原生对象），服务 23 页招商银行高密度汇报 · 来源：source/slide-paipai/（用户提供 zip，2026-09-24 入库）· 调研日期 2026-09-24 · 索引：../source-survey.md

## 1. 定位与产物形态

为「招商银行高拜材料」自建的排版与导出引擎，核心思路：**页面内容只写一遍，可渲染成 1920×1080 页图，也可渲染成原生可编辑 PPT 对象**（`README.md:3`）。七个文件共约 1700 行：`deckkit.py`（337 行 PIL 排版引擎）+ `pptxdeck.py`（514 行 python-pptx 镜像后端）+ `render_pages.py`（867 行，23 页逐页内容定义）+ 三个驱动脚本。

架构是**后端可整体替换**：`build_editable_pptx.py:20-24` 用 4 行 monkey-patch（`R.Page = PD.PP`、`R.content = pp_content`、`R.sans/R.serif = PD.sans/PD.serif`）把同一批页面函数路由到原生后端。页面函数只调统一绘制 API（`rect/line/txt/para/paras/bullets/table/hbars/vbars/donut/kpicard/chip/header/footer/source`），不关心产物形态。

**适用场景自我声明**（README.md:98）：文字量大、数字密集、要求逐字保真的文档转 PPT——AI 生图做不了长段中文。

## 2. 方案详解

### 2.1 deckkit.py：中文排版引擎

**断行 = tokenize + 贪心折行**（`deckkit.py:50-88`）。ASCII 白名单字符（`A-Za-z0-9%+-:/.,×—–±()'"`）粘成原子 token，其余字符（含全部 CJK 与全角标点）一字一 token；测宽用 `ImageDraw.textlength` 逐 token 真实字体测宽，贪心装行，行首空格丢弃。效果：`12,491.32`/`2026H1`/`15.32%` 这类数字串**永不从中断开**。**完全没有标点禁则**（`。，、）」` 可落行首），也无标点悬挂——23 页金融材料没出事是靠行长容错。这暴露了它的上限，也标定了最小基线：**"不断错数字"一条就撑住了专业感**。

**富文本段内混排**：`para()`（:114-130）把 `[(lead, bold_font), (body, reg_font)]` 送进**同一个** wrap_parts 折行，渲染时逐 token 推进 x 光标；颜色归属靠 `f is fb` **字体对象身份比较**（依赖 `F()` 的 `_fc` 缓存 :32-39 保证同参数同对象）——脆弱但有效。`bullets()`（:141-164）同构，加 8×8 方块 marker、缩进 34px。

**last_y 流式定位协议**：每个块级方法返回底部 y 并写 `self.last_y`；页面脚手架 `content()` 返回 `(page, header_bottom_y)`，页面函数用 `y = p.last_y + gap` 串联。README 坑 #1 自曝 **8 页曾因用旧 y 压版**——协议靠纪律不靠断言，引擎内零溢出检查。

**组件参数化**：
- 三线表 `table()`（:206-242）：列宽按权重分配；行高可固定或**干跑测高**（`_cell(..., dry=True)` 只折行不绘制返回高度，:244-259），行高 = 最高单元格行数 × (fs+9) + 16；三线 = 顶 3px + 表头下 2px + 底 3px，zebra `(247,250,254)`。
- KPI 卡 `kpicard()`（:193-204）：圆角底 + 左侧 6px accent 竖条 + 大数字（46px）+ **标签底部锚定**（`y + h - 26 - lsz*1.2`），不同长度标签不顶数字。
- 柱图 `hbars/vbars`（:262-312）：纯形状模拟。值得抄的参数：`ymax = max(vals) * 1.28`（为数值标签预留 28% 头部空间）、`bw = min(slot*0.5, 130)`（柱宽双上限防"胖成墙"）、注释再上移 66px 用强调色。瑕疵：hbars 的 `hi` 按标签名匹配、vbars 按下标匹配——同一 API 两种语义。
- 环形图 `donut()`（:314-325）：pieslice + 白色挖孔（hole=0.56），**图例不归组件管**，页面手画。

**数值体系**（1920×1080）：页边距左右 96px；header 分隔线 y=150、内容起点 ≥190；footer 线 y=H-62、source 注 H-108；页标题 44px bold、正文 25–26px/lh 38–40（**行距比 ≈1.5**）、表格 18–25px、图表标签 19–24px；封面 104px serif。换算基准 1920px = 13.333in ⇒ **1px = 0.5pt**（正文 25px ≈ 12.5pt）。

### 2.2 pptxdeck.py：原生后端

**API 映射**：rect→ROUNDED_RECTANGLE（`adjustments[0]=min(0.5, radius/min(w,h))` 钳制，:176）；line→connector；txt→`word_wrap=False` 单行框（宽=measure+24 留裁字余量）；para/paras/bullets→**单段 + word_wrap=True**；table→原生 `add_table` + 手写边框 XML；hbars/vbars→**仍是形状模拟**（逐行镜像）；donut→**唯一原生 chart**（DOUGHNUT）；封面渐变→`_D` shim 把 28 条 1px 线变成 28 个 connector（笨但双端可跑）。换算落点 `PX = 6350`、`PT = 0.5`（:32-33）。

**核心策略：预折行只用于测高，不用于落盘**（`pptxdeck.py:256-268`）：

```python
lines = wrap_fs([(lead, fl), (body, fb)], maxw)              # PIL/Noto 测宽算行数
tb, tf = self._textbox(x, y - 5, maxw, (len(lines) + 1) * lh)  # 行数只定框高
tf.word_wrap = True
p0.line_spacing = Pt(lh * PT)                                # 精确行距（等价 lnSpc spcPts）
self._run(p0, lead, fl, lead_col); self._run(p0, body, fb, body_col)  # 同段两 run，PPT 自己重排
```

README 坑 #3：按预折行每行建一个 paragraph 会因段间距累积下溢压版。结论 wrap=square + 单段 + 精确行距——**与我们 export-pptx-editable 的 L1 策略独立收敛、互为印证**。

**表格边框 XML 顺序坑的精确实现**（`borders()` :375-392）：`reversed([lnL, lnR, lnT, lnB])` + `tcPr.insert(0, node)` 使最终子节点顺序恰为 lnL→lnR→lnT→lnB 且在 `a:solidFill` 之前（错了 PowerPoint 报修复）；先 findall-remove 再插入保幂等；**无边的边写 `<a:noFill/>` 显式抹除**（否则主题默认边漏出）。配套：`tbl.first_row = False; tbl.horz_banding = False`（:367-368）关死默认表样式，zebra 改逐格 `cell.fill`。

**run 级三写 typeface**（`_run()` :196-211）：`a:latin`/`a:ea`/**`a:cs`** 三保险（我们只双写，cs 可补）。

**原生 chart 只给 donut**（:474-511）：关 legend/title/dataLabels、`vary_by_categories`、逐 point 上 fill 色、holeSize 靠遍历 chartSpace 直接改 XML（python-pptx 无 API）；**所有 chart 属性操作逐项 try/except**（防御 python-pptx 版本差异）。柱图坚持形状模拟换双端像素一致与标注自由，代价是 PPT 里不可编辑数据。

**其他防御**：每个 shape/connector `shadow.inherit = False`（:163,:193，默认主题阴影是脏底常见来源）；rect 自动交换倒置坐标 + 最小尺寸钳制 0.6px（:166-171，防零宽形状报修复）；文本框四 margin 清零 + space_before/after=Pt(0)（:213-226）。**透明色一律 Python 侧 `blend()` 预混成实色**（render_pages.py:14-15），零 alpha 依赖。

### 2.3 render_pages.py：内容组织与密度实测

尾部 `FULL` 列表（:856-860）按页序排 23 个零参函数；内容页统一脚手架 `content(pno, kicker, title)`。用计数代理实测五页密度：

| 页 | API 调用 | 字符 | 版式 |
|---|---|---|---|
| p20 指数量化谱系 | 113 | 415 | 3 组流式 chips + 4 列芯片墙 |
| p23 AI 销售 | 106 | 635 | 4 列工具卡 |
| p19 产品矩阵 | 99 | 645 | 3×3 风格×市值矩阵 + 25 代表作三列清单 |
| p17 对照双列 | 45 | 636 | 5 行左右对照（招行 ↔ 天弘） |
| p18 七大业务线 | 41 | 635 | 2 列×4 行编号条目 + 底部路径条 |

典型高密度页 p19（:622-670）**整页零表格零图表，全靠 rect+txt 手排**，小字号（18-19px）+ 密栅格撑密度。值得记录的版式模式：对照列（等价于我们 components.md 的 versus-cols，固定行高 + 左右底色微差 + zebra）；三阶段时间线（色头"双 rect 遮圆角"技巧 :418-419）；分层架构图（chips 宽按 `tw()+40` 实测流式排，塞不下换行 :792-794）；流式 chip 云三视觉态；排名行（左侧 8px 色条 + serif 大号名次 + 当前方高亮）。

### 2.4 双后端一致性：共享什么、漂移在哪

**共享**：全部几何常量与色板（pptxdeck.py:14-16 `from deckkit import`）；同一个 tokenize；折行算法逐行镜像（测宽换成无页面的 ImageDraw 测量句柄 :65-77）；页面函数零修改复用；组件数学刻意对齐（table 的 last_y 公式两端精确一致）。

**已存在的漂移**：① **测宽字体 ≠ 落盘字体**（Noto CJK 量行数，PPT 实际渲染微软雅黑——隐性风险，README 未提）；② kpicard 标签行距 `lsz+6` vs `font.size+8`、锚定 `lsz*1.2` vs `lsz*1.4` 两处已漂；③ para 的 last_y 两端差 +4；④ donut 位图 vs 原生 chart 永不可能像素一致；⑤ 封面渐变线宽取整。

这两个漂移源（测宽字体≠落盘字体、组件常数两端手抄）**恰好是我们"渲染真相"路线（从浏览器 DOM 取实测值）已根治的问题**——我们的管线在一致性上严格优于它。

## 3. 对本项目的可提炼范式（按证据）

1. **数字/单位串原子化是中文排版第一禁则**（→ references/typography.md）：tokenize 白名单（deckkit.py:50-51）保证数词永不断开。CSS 侧对应 `white-space:nowrap` 包数词。可作我们断行规范的最小基线，再叠加标点行首禁则超越它。
2. **wrap=square + 单段多 run + 精确行距 > 预折行多段**：双方独立验证（pptxdeck.py:256-268 + README 坑 #3 ↔ 我们 L1）。可作定论脚注写进导出文档。
3. **表格边框 XML 四边顺序 lnL→lnR→lnT→lnB 且先于 solidFill + 无边写 noFill**（pptxdeck.py:375-392）：若 C 系未来做原生表格，这段可逐字抄。
4. **柱图 ymax = max×1.28 标注头部余量**（deckkit.py:296 → charts.md 可量化为硬规则）。
5. **柱宽双上限 `bw = min(slot*0.5, 130px)`**（deckkit.py:299 → charts.md）。
6. **原生 chart 只用于结构简单图形、属性操作逐项 try/except**：印证我们 L3 双源校验保守策略是行业务实解。
7. **last_y 流式协议需要机器校验兜底**：8 页压版事故是纯约定翻车的反向证据——任何手工 y 链都必须过渲染校验（我们 j_render_check 已覆盖）。
8. **干跑测高模式（测量与绘制同码）**（deckkit.py:244-259）：自绘布局引擎防漂移的通用模式。
9. **透明色预混实色是免 alpha 的诚实降级路径**（render_pages.py:14-15）：旧版 WPS 等下游 alpha 失效时的备选。
10. **KPI 卡"值顶锚 + 标签底锚"双锚纪律**（deckkit.py:197 → components.md metric-card 细则）。

## 4. 总体判断

价值不在技术深度（断行无禁则、渐变靠画线、双端有已知漂移），而在**用 337 行证明"统一 API + 后端替换"对双形态交付的可行性**，以及若干数值纪律（原子 token、1.5 行距比、28% 图表头部余量、边框 XML 顺序、shadow.inherit=False）。可放心吸收其内容侧范式与 python-pptx 坑清单；其双后端测宽方案已被我们的渲染真相路线超越，不必吸收。
