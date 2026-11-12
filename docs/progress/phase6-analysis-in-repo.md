# Phase 6 · `analysis/` 整目录入库（仅本地提交）

> 日期：2026-11-12
> 触发：Handover §6 标注「`analysis/` 整目录未入库，换机/克隆即丢判据原始依据」，上一轮询问是否把 4 个关键文件迁移进 `docs/progress/`。
> 用户决策：**是的，修改 `.gitignore`，把 `analysis/` 提交，都按本地**（即整目录入库，不 push）。

## 1. 决策与口径

- **不做** 4 文件零散迁移：`analysis/` 内脚本互相引用、并依赖同目录的截图与 stdout 转储，拆散后反而失去可复现性。
- `.gitignore` 末尾追加 `!/analysis/` 显式放行，并写明「只提交本地、不推送公开远端；push 前须复核含本机路径的文件」。
- 提交范围：`.gitignore`、`analysis/` 全部文件、`docs/progress/HANDOVER.md` 的同步勘误、本文。
- 暂存方式沿用 `git add -u` + 显式路径，**不用 `git add -A`**：`.workbuddy/`、`skills/SlideForge.zip`、h1 两张 demo 图仍未跟踪且未被忽略。

## 2. 入库范围实测

| 项 | 值 |
|---|---|
| 文件数 | **89**（`git ls-files -- analysis/` 实测，含运行期探测日志） |
| 总体积 | 约 **3.25 MB**（单文件最大 256 KB） |
| 核心判据 | `G10-主题DNA规范草案.md`（「审美巅峰」验收口径、G10 七字段规范） |
| 指纹证据 | `_fingerprint.py` / `_fingerprint.json` / `_fingerprint-demo.json` / `_fp-rank.log`（28×28 结构相关矩阵与骨架排序） |
| 主题扫描 | `_scan-themes.js` / `_scan-themes.json`（30 套主题的字段实测数据） |
| Pilot 与审计 | `check-dna.py` / `dna-pilot.html`（24 页）/ `dna-soul.html` / `b1-aesthetic-peak.html` / `check_dna_report.*` |
| 截图 | `DNA-*.png`、`PILOT-*.png`（6 页型 × 4 主题）、`B1-*.png` |
| 辅助脚本/转储 | `_render*.py`、`_patch*.py`、`_audit*.py`、`_*.txt`、`*.log` |
| 安全检查 | 全目录扫描 `api_key` / `secret` / `password` / 私钥头 / 长 token → **0 命中**；含本机绝对路径，但不包含任何凭据 |
| 显式排除 | 无（按「整目录」口径，运行日志也一并留痕）；`__pycache__/` 由全局规则排除 |

> 注：`_fingerprint.py`、`_render*.py`、`_patch*.py` 等含硬编码本机绝对路径；入库为留痕与判据可追溯，**跨机复跑前需改成相对路径**。
>
> 注 2：提交期间另有进程持续写入 `_env-check.log` / `_py-check.log` / `_pip-*.log` 等环境探测日志，已按提交时刻的快照一并纳入；之后若继续变化只会显示为本地修改，不影响核心资产。`_pw_find.txt` / `render.log` 含 NUL 字节，git 按二进制存储。

## 3. Handover 同步勘误（8 处）

| 位置 | 原口径 | 改为 |
|---|---|---|
| §0 基线行 | 领先 3 个提交 | 领先 4 个提交（含 Phase 6） |
| §0 必读第 2 条 | G10 草案「未入库、只在本机」 | 已整目录入库、只本地未推送 |
| §6 资产地图 4 行 | ❌ 未入库 | ✅ Phase 6 入库 |
| §6 换机风险段 | 建议迁移 4 文件 | 风险已消除 + push 前复核提醒 |
| §7 坑 3 | `analysis/` 与其余项均未被忽略 | `analysis/` 已入库；其余 3 项仍未忽略 |
| §7 其他遗留 | — | 新增「研究脚本含硬编码本机路径」一条 |
| 附录 A | 3 行 commit | 补 `d4209e9` 与 Phase 6 两行 |
| 附录 B 第②问 | 是否先迁移 4 文件 | 确认工作副本包含这批本地提交 |

## 4. 边界与后续

- **所有提交均未 push**；`origin/main` 仍停在 `9c8d7de`。
- 干净克隆 / 另一台机器需先同步本地提交，否则 `analysis/` 仍不可见。
- 若将来要 push 到公开远端：先复核并清理 `analysis/` 内含本机绝对路径与内部研究痕迹的脚本、日志；`.gitignore` 注释已写明这条边界。
- 本阶段不改变任何主题、骨架、编辑器或 README 内容，只解决「判据原始依据的可追溯性」。
