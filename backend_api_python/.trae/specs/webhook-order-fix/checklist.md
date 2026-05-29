# Checklist - Webhook 下单机器人 Bug 修复验证

## 代码功能验证 (已完成)

- [x] webhook.py: _parse_tradingview_payload 函数正确解析 buy → long
- [x] webhook.py: _parse_tradingview_payload 函数正确解析 sell → close_long
- [x] webhook.py: _parse_tradingview_payload 函数正确解析 short → short
- [x] webhook.py: _parse_tradingview_payload 函数正确解析 close_short → close_short
- [x] webhook.py: _generate_webhook_key 函数生成确定性 key
- [x] webhook.py: _get_strategy_by_webhook_key 函数正确查找策略
- [x] trading_executor.py: webhook_signal bot 正确初始化 pending_signals = []
- [x] mexc.py: _sign 函数使用正确格式 (accessKey + timestamp + params)
- [x] mexc.py: _headers 函数使用正确 header 名称 (ApiKey, Request-Time, Signature)
- [x] mexc.py: 订单端点使用 /api/v1/private/order/create
- [x] mexc.py: 订单参数使用正确字段 (symbol, side, vol, type, openType, leverage)
- [x] mexc.py: order_id 正确从 data.orderId 解析
- [x] symbols.py: to_mexc_swap_symbol 正确转换 BTC/USDT → BTC_USDT

## 测试执行验证 (已完成)

- [x] test_webhook.py 所有测试通过 (11 tests)
- [x] test_webhook_comprehensive.py 所有测试通过 (31 tests)
- [x] test_webhook_integration_full.py 所有测试通过 (17 tests)
- [x] test_webhook_order_flow.py 所有测试通过 (3 tests)
- [x] test_webhook_signal_bot.py 所有测试通过 (5 tests)
- [x] test_mexc_signature.py 所有测试通过 (4 tests)

## 实际功能验证 (需服务器重启后测试)

- [ ] POST /api/webhook/register 返回有效的 webhook_key
- [ ] POST /api/strategies/start?id=XX 机器人成功启动
- [ ] POST /api/webhook/signal 返回 {"status": "success", "order_id": "xxx"}
- [ ] 平仓信号正确执行

## 问题修复验证 (已完成)

- [x] pending_signals 未初始化问题已修复
- [x] MEXC 签名方法已修复 (accessKey + timestamp + params)
- [x] MEXC API 端点已修复 (/api/v1/private/order/create)
- [x] order_id 解析已修复 (从 data.orderId 获取)
- [x] webhook register 接口 user_id 解析已修复

## 测试统计

- 单元测试: 72 passed
- 实际功能测试: 3 failed (服务器未重启)
- 代码修复: 全部完成
