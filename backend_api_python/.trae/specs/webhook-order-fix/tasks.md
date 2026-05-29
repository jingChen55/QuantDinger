# Tasks - Webhook 下单机器人 Bug 修复

## 任务清单

- [ ] Task 1: 编写并运行 webhook 核心功能单元测试
  - [ ] Task 1.1: 测试 TradingView payload 解析 (buy/sell/short/close_short)
  - [ ] Task 1.2: 测试 webhook key 生成和查找
  - [ ] Task 1.3: 测试 MEXC symbol 转换 (BTC/USDT → BTC_USDT)
  - [ ] Task 1.4: 测试 MEXC 签名生成
  - [ ] Task 1.5: 测试 MEXC 订单参数构造
  - [ ] Task 1.6: 测试 order_id 解析逻辑

- [ ] Task 2: 修复 pending_signals 未初始化问题
  - [ ] Task 2.1: 在 trading_executor.py 中初始化 pending_signals = []
  - [ ] Task 2.2: 运行测试验证 bot 可以正常启动

- [ ] Task 3: 修复 MEXC API 相关问题
  - [ ] Task 3.1: 修复签名方法 (accessKey + timestamp + params)
  - [ ] Task 3.2: 修复 API 端点 (/api/v1/private/order/create)
  - [ ] Task 3.3: 修复订单参数格式 (symbol, side, vol, type, openType, leverage)
  - [ ] Task 3.4: 修复 order_id 解析 (orderId 在 data 字段内)

- [ ] Task 4: 修复 webhook register 接口问题
  - [ ] Task 4.1: 修复 user_id 解析错误
  - [ ] Task 4.2: 验证可以正常生成 webhook key

- [ ] Task 5: 编写完整下单流程集成测试
  - [ ] Task 5.1: 测试 Webhook → Signal 解析 → MEXC Order → order_id 获取
  - [ ] Task 5.2: 测试平仓流程 (sell → close_long)
  - [ ] Task 5.3: 测试做空流程 (short → open_short)

- [ ] Task 6: 运行所有测试并验证结果
  - [ ] Task 6.1: 运行单元测试 (72+ tests)
  - [ ] Task 6.2: 验证所有测试通过
  - [ ] Task 6.3: 记录测试结果
