# 1007 · 仓库卫生收尾 + README 安装指引

## 改动

- **AGENTS.md 移出版本库**：加入 `.gitignore` 并 `git rm --cached`（含内部信息，本地保留继续生效；此后修改不再被追踪）。
- **test_case1 迁移**：根目录 `test_case1/`（41MB，54 页真实 deck）→ `tests/test_case1/`；`.gitignore` 通配改为显式 `tests/test_case1/`，`git check-ignore` 验证命中。代码无路径引用，历史 progress 文档不回改。
- **README 安装细节**（中英双版，Quick Start 节）：技能安装（`npx skills add DSXiangLi/pptx_fuse_design` 推荐路径 + 手动复制到 `~/.claude/skills/` / `~/.agents/skills/`）；MCP 桥接入（`pip install "mcp>=1.28,<2"`、`claude mcp add` 一行命令、通用 mcpServers JSON、五工具齐备为成功判据）；可选依赖（Playwright / poppler）。

## 验证

- `git check-ignore`：AGENTS.md、tests/test_case1/ 均命中规则。
- 无代码变更，无需回归。
