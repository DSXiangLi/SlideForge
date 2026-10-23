# 1007 · 主题光学轴扩展：F 系入库 + C3/E5 升级

> 触发：用户观察"当前主题几乎都在用线+颜色构建视觉，阴影/光线/透明度/容器多样性极少"。设计文档 `docs/design/theme-optical-axes.md`，验收证据 `docs/test_acceptance/theme-optical-axes.md`。

## 盘点（全库量化，回答"少了什么"）

21 主题全量精读 + 正则计数：box-shadow 全库仅 10 处/6 主题且 17 个主题明文禁阴影；backdrop-filter、彩色平滑渐变、filter:blur 光斑、text-shadow 落码全部为零；多层柔和阴影为零；圆角主题仅 D1/E6。差异化实际只靠颜色+字体+线汇+平涂色块四根轴。dashi/open-design/guizang 解剖给出对照手法清单（rim-glow 五层、玻璃六件套、品牌色染影、以影代边、渐变字、噪点+暗角三件套等）。

## 决策：Both

- 新建 F 系「光与纵深」立轴（A–E 系薄是立场不动，8+ 主题明文禁玻璃/阴影不可改）；
- 只升级名实不符的 C3（磷光世界零像素发光）与 E5（石印世界肌理/词汇未兑现）；B1/C4/A1 的薄是编辑部立场，不动。

## 落地清单

- **themes.md**：新增 F1 浮光玻璃（aura 光斑全页 + 玻璃六件套 `.mt-gls-card/blob/chip` + 多层柔和投影三件套）、F2 霓虹夜行（rim-glow `.mt-neo-tube` + 发光字 `.mt-neo-sign` + 光管线/呼吸点，发光严格单色）、F3 暮色长镜（aura 地平线色带+暗角 scope=cover + 渐变字 `.mt-dsk-grad` + 时间码 `.mt-dsk-code`）；各 3 套配色变体；选择建议 +3 行。C3 升级：G4 磷光晕散体系 + `.mt-term-glow` + 窗口/光标辉光（首版晕散过弱 diff 仅 0.09%，加强后 sampler diff 4.66%）；E5 升级：grain scope cover→all + `.mt-con-wedge` 红楔 + `.mt-con-diag--print` 套印双影。
- **sync-themes.mjs**：EXPECTED_COUNT 21→24；主题头/分化声明正则 [A-E]→[A-F]；TEXTURE_TYPES 新增 `aura`（氛围光，质感类型第六值）。
- **editor.html**：sync 注入 24 主题卡片（含变体与 G9 css）。
- **gallery**：56 页（+F1/F2/F3 样张）；母题合入区同步 C3/E5 新版 + F 系三块；21 处"二十一个世界"→"二十四个世界"。
- **theme-sampler**：24 页（+F1/F2/F3 山禾集业务页）；C3 愿景行磷光晕散、E5 加 texture-on+楔块+双印带；`NN / 21`→`NN / 24`。
- **README/README_ZH**：样张精选 12→15（新增 F 系三张截图行）。
- **手法纪律条款**（防"加手法=加噪声"）：每页 1–2 根主轴、发光单色、阴影带色相、玻璃六件齐上——写入各主题 G4/G9 禁忌，不进全局。

## 验收

- sync-themes 全绿（两两七层 diff ≥3 + 分化声明逐层核验）；check-render：sampler ALL PASS，gallery 目标五页 PASS（其余 132 项为 HEAD 预存小字问题，零新增）。
- 截图证据与像素级量化（光斑/发光/色带/前后 diff）见 `docs/test_acceptance/theme-optical-axes.md`。
- run_e2e 全量回归 **59/59 PASS 0 FAIL**（2026-10-07，wall 999.293s；含 T18 56 页口径与 T9 24 主题卡）。

## 遗留

- F 系三主题的 bake_brief 未写（非试点主题合法缺省），烙入简报铺量批次再补。
- gallery 组件页 132 项预存小字失败是既有存量，与本批无关，另立翻修项。
- E3 金属铬字轴（dashi t09 路线）未做——F 系先立三根主轴，金属轴视目检反馈再立项。
