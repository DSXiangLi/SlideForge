# brief.submitted intent 在 daemon 重启时自动取消

## 日期
2026-10-24

## 背景

SproutHarness 本地 work 环境频繁重启服务。daemon 重启时，`_invalidate_previous_instance()` 把所有 `processing` 状态的 intent 标记为 `interrupted`，session 进入 `recovering` 状态。之后 `await_intent` 被 `RECOVERY_REQUIRED` 拦截，要求用户在编辑器页面手动选择 rebuild/resume。

对于 `brief.submitted` 这种纯指令型 intent，daemon 不做实际工作（只是把简报转交给 agent），interrupted 后没有任何实际工作需要恢复——agent 只需要重新拿到简报文本即可。当前机制无差别地把所有 intent 都标记为需要手动恢复，导致开发体验卡顿。

## 问题

- daemon 重启后，`brief.submitted` intent 进入 `interrupted` 状态
- session 进入 `recovering`，`await_intent` 返回 `RECOVERY_REQUIRED`
- 用户必须在编辑器页面手动选择 rebuild/resume 才能继续
- 对于 `brief.submitted` 这类纯指令 intent，手动恢复无意义

## 方案

修改 `tools/bridge_core.py` 的 `_invalidate_previous_instance()`：daemon 重启时，对 `brief.submitted` 类型的 `processing` intent 直接标记为 `cancelled`（而非 `interrupted`），使其不触发 `recovering` 状态。

### 判定标准

纯指令型 intent（daemon 不执行实际工作、不产生 work_path）：
- `brief.submitted` — 简报提交，daemon 只转交文本
- 未来新增的纯指令型 intent 同理

### 改动点

`_invalidate_previous_instance()` 中，按 intent type 分流：
- `brief.submitted` → `cancelled`（不触发 recovering）
- 其他类型 → `interrupted`（保持现有行为，需手动恢复）

## 状态

已实施 — `_invalidate_previous_instance()` 中新增按 intent type 分流：
- `brief.submitted` → `cancelled`（不触发 recovering）
- 其他类型 → `interrupted`（保持现有行为）

`INTENT_STATUSES` 已包含 `cancelled`，无需额外改动。
