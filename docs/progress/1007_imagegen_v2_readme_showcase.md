# 1007 · imagegen v2 入库 + README 编辑器实录 + demos 脱敏

## imagegen v2（G1–G8，本批主体为用户侧改动）

- **editor v3.6/v3.7**：生图入口三态（Bridge 态发 intent / 嵌入态 `pptx-html:bake-intent`、`pptx-html:illustrate-intent` / 裸静态态复制指令）；入站 `pptx-html:assets-changed {files}` 按清单热刷新图片（`?v=` cache-bust、不置脏）。
- **skeleton v7.5**：烙入整图入场动效白名单（≤0.8s 零延迟，m_bake ⑧e/⑧f）；**契约 v8.1**（G7 分辨率下限：页面级槽位 ≥2560×1440、页内槽位栅格短边 ≥640px）；motion v3.2（图片入场白名单）。
- **imagegen v2 通道**：`tools/edit.py --imagegen`（G6）只落 `illustrate.requested`（禁烙入），provider 由 `PPTX_HTML_IMAGEGEN_PROVIDER` / `.pptx-html/config.json` 供给；`scripts/imagegen-adapter.py` 受控调用 + ledger 落账（`--rubric-json` 逐字透传）。
- **check-image-harmony.py**：生图色彩一致性后置校验（canvas 取主色板 × manifest token，CIEDE2000，单图告警不阻断、≥50% 双触发阻断）。
- **验收**：harness 59 项（新增 T32 生图入口三态 / T33 本地插画通道 / w 色彩一致性子进程）；G8 首次真实生图验收证据见 `docs/test_acceptance/imagegen-v2-g8-real-imagegen.md`（2 次调用 / 3 张图，零失败）。
- 设计文档 `docs/design/imagegen-v2.md`，howto/protocol 同步更新。

## README 编辑器实录 + 素材迁移（本次会话）

- **新增 `assets/editor/` 三张 GIF**（均 960×540）：编辑+批注（用户录屏转 GIF，补黑边统一 16:9）、需求脑暴浮板（新录）、导出 PPTX + 对比质检（新录：并排→滑动分割拖拽→差异热区；对比载体为 smartforge-c1 实跑保真轨产物）。
- **编辑器区叙事修正**：主流程是 agent 经 MCP 自动唤起本地网页处理人工节点；手动打开 `editor.html` 降级为备注。
- **`docs/showcase/` 整体迁移至 `assets/`**（git rename 保留历史），README 27 处路径更新。
- 编辑器录屏驱动方式复用 harness 选择器（`#btnBrief` / `#viewSeg` / `#cmpViewSeg` / `#cmpHandle`），无付费调用。

## demos/imagegen-v2 脱敏（提交前卡点）

- G8 演示 deck 原以真实公司署名（4 页页脚/封面 + brief/prompts/manifest 共 11 处），全部置换为虚构机构「衡庐基金」；页级 hash 与 `.manifest-baseline.json` 重算重建；双轨导出重跑（vector+editable ok、载体 baked×1+svg×3、保真均分 99.488、可编辑轨 native_text_ratio 1.0、认证 PASS）。
- 验收文档 `imagegen-v2-g8-real-imagegen.md` 中引用的保真分 99.52 为原始运行记录；脱敏重跑后为 99.488，差异仅为署名文本替换所致。

## 回归

- k_brief / m_bake / w_harmony 三个子进程全 ALL PASS（覆盖本批改动的脑暴浮板、bake-mix fixture、harmony fixture）。
- 完整 59 项 run_e2e 未在本会话重跑（含付费生图项，须另行授权）。
