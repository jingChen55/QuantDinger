# Webhook 下单机器人 Bug 修复规格

## Why
新增的 Webhook Signal 交易机器人无法通过 webhook 完成下单交易，需要定位并修复下单流程中存在的问题。

## What Changes
1. 修复 webhook 机器人启动时的 `pending_signals` 未初始化问题
2. 修复 MEXC API 签名方法不正确的问题
3. 修复 MEXC API 端点和参数格式错误的问题
4. 修复 order_id 解析逻辑错误的问题
5. 修复 webhook register 接口 user_id 解析问题
6. 补充完整的 webhook 下单流程测试用例

## Impact
- Affected specs: Webhook Signal Trading, MEXC Exchange Integration
- Affected code: 
  - `app/routes/webhook.py` - Webhook 端点
  - `app/services/trading_executor.py` - 策略执行器
  - `app/services/live_trading/mexc.py` - MEXC 客户端
  - `app/services/live_trading/symbols.py` - Symbol 转换

## ADDED Requirements

### Requirement: Webhook Signal Bot Initialization
Webhook Signal 类型的机器人启动时必须正确初始化所有必需的变量。

#### Scenario: Bot 启动成功
- **WHEN** 启动 webhook_signal 类型机器人
- **THEN** pending_signals 变量被初始化为空列表，循环正常运行

### Requirement: MEXC Order Response Parsing
MEXC API 返回的订单响应必须正确解析 order_id。

#### Scenario: 成功获取 order_id
- **WHEN** MEXC API 返回 {"success": true, "data": {"orderId": "123456"}}
- **THEN** order_id 被正确解析为 "123456"

### Requirement: Webhook Order Execution Flow
Webhook 接收信号后必须成功执行订单并返回 order_id。

#### Scenario: 完整下单流程
- **WHEN** 发送 {"action": "buy", "symbol": "BTC/USDT", "qty": 0.1}
- **THEN** 返回 {"status": "success", "order_id": "xxx"}
