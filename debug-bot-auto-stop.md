# Debug Session: bot-auto-stop

**Session ID:** bot-auto-stop
**Created:** 2025-05-31
**Status:** [OPEN]
**Problem:** 机器人启动后自动停止（启动后几秒内立即停止）

---

## 症状

| 维度 | 描述 |
|------|------|
| **预期行为** | 用户在前端点击启动机器人后，机器人应保持运行状态（running），持续执行交易逻辑 |
| **实际行为** | 机器人启动后几秒内自动变为停止状态（stopped），前端显示已停止 |
| **触发条件** | 用户在前端点击"启动"按钮 |
| **影响范围** | 所有交易机器人类型（martingale / grid / DCA） |

---

## 已分析的代码路径

### 1. API 入口
- **文件**: `app/routes/strategy.py` 第 1235-1297 行
- **端点**: `POST /strategies/start`
- **流程**: `start_strategy()` → `update_strategy_status('running')` → `executor.start_strategy(strategy_id)` → 若失败则恢复为 `stopped`

### 2. 策略执行器核心循环
- **文件**: `app/services/trading_executor.py` 第 992-1073+ 行
- **方法**: `_run_strategy_loop(strategy_id)`
- **关键机制**:
  - 第 1002-1010 行：**Auto-stop 策略**，当 `consecutive_errors >= max_consecutive_errors` 时触发自动停止
  - 第 1032-1071 行：`_is_fatal_error()` 函数定义致命错误类型（API key 无效、symbol 不支持、connection refused 等）
  - 第 1075-1349 行：加载策略配置、获取 K 线数据、持仓同步

### 3. 持仓同步（启动时）
- **文件**: `app/services/trading_executor.py` 第 1300-1309 行
- **方法**: `worker._sync_positions_best_effort(target_strategy_id=strategy_id)`
- **来自**: `app/services/pending_order_worker.py`

### 4. 策略生命周期管理
- **文件**: `app/services/strategy_lifecycle.py`
- **方法**: `auto_stop_live_strategy(strategy_id, reason)` — 强制停止策略

---

## 假设（Hypotheses）

> 以下假设将通过插桩日志验证。在证据确认前，禁止修改业务逻辑代码。

### H1: 致命错误触发自动停止（最可能）
**描述**: `_is_fatal_error()` 函数在启动过程中检测到某个致命错误，立即触发自动停止。
**可能原因**:
- 交易所 API Key 无效/过期
- Symbol 不支持或已被下架
- 连接失败（IBKR/MT5 等桌面券商）
**验证方法**: 在 `_is_fatal_error()` 入口和 `_set_db_stopped_best_effort()` 调用处添加日志，捕获 `err` 和 `msg` 的具体内容。

### H2: K 线数据获取失败导致提前退出
**描述**: `_fetch_latest_kline()` 返回数据不足（少于 2 条），触发第 1284-1286 行的 `return` 退出循环。
**可能原因**:
- 市场数据源连接失败
- Symbol 格式错误导致数据源查询失败
- 网络问题导致无法获取历史数据
**验证方法**: 在 `klines = self._fetch_latest_kline()` 之后添加日志，记录返回的 kline 数量和 symbol。

### H3: 策略类型不支持
**描述**: 第 1081-1083 行检查 `strategy_type`，如果不是 `IndicatorStrategy` 或 `ScriptStrategy` 则直接 `return`。
**可能原因**:
- 用户创建了 `PromptBasedStrategy`（AI 策略）类型
- 数据库中 `strategy_type` 字段值异常
**验证方法**: 在第 1081 行添加日志，记录 `strategy_type` 的实际值。

### H4: 持仓同步异常触发的连锁反应
**描述**: 第 1306 行调用 `worker._sync_positions_best_effort()` 时抛出未捕获的异常，虽然有 try-except 但可能在 `pending_order_worker.py` 内部触发了某种状态变更。
**验证方法**: 在第 1306 行调用处添加日志，记录 `worker` 对象是否存在、同步是否成功。

### H5: indicator_code 为空导致退出
**描述**: 第 1216-1223 行检查 `indicator_code`，如果为空则直接 `return`。
**可能原因**:
- 数据库中 `indicator_code` 字段为空
- 指标 ID 存在但无法从数据库获取到代码
**验证方法**: 在第 1222 行附近添加日志，记录 `indicator_code` 和 `indicator_id` 的值。

---

## 插桩计划

| # | 文件 | 行号 | 插桩内容 | 对应假设 |
|---|------|------|----------|----------|
| 1 | `trading_executor.py` | ~1080 | 记录 `strategy_type` 值 | H3 |
| 2 | `trading_executor.py` | ~1222 | 记录 `indicator_code` 值 | H5 |
| 3 | `trading_executor.py` | ~1284 | 记录 kline 获取结果 | H2 |
| 4 | `trading_executor.py` | ~1306 | 记录持仓同步结果 | H4 |
| 5 | `trading_executor.py` | ~1032 | 记录 `_is_fatal_error` 调用 | H1 |
| 6 | `trading_executor.py` | ~1013 | 记录 `_set_db_stopped_best_effort` 被调用时的 `reason` | H1 |

---

## 证据收集日志

| 时间 | 假设 | 证据摘要 | 状态 |
|------|------|----------|------|
| — | — | 待用户复现后收集 | 待收集 |

---

## Debug Server

- **Session ID**: bot-auto-stop
- **端口**: 随机可用端口（通过 `debug-server.js` 自动探测）
- **状态**: 待启动
- **日志文件**: `trae-debug-log-bot-auto-stop.ndjson`

---

## 修复记录

| 时间 | 假设 | 修复方案 | 结果 |
|------|------|----------|------|
| — | — | — | — |

---

## Session 状态变更记录

- 2025-05-31: Session 创建，开始分析