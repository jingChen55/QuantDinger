# 修复 Webhook 机器人创建向导的表单验证 Bug

## 问题分析

### 错误现象
- 位置：http://localhost:8000/#/trading-bot
- 操作：点击"下一步"从 Step 1 进入 Step 2（策略参数配置）
- 问题：网页卡死，无法点击下一步
- 浏览器控制台报错：
  ```
  async-validator: ['credentialId is required']
  async-validator: ['symbol is required']
  ```

### 根本原因
1. **WebhookConfig.vue** 组件的表单验证规则中包含：
   - `credentialId` 必填验证
   - `symbol` 必填验证

2. **数据流错误**：
   - `credentialId` 和 `symbol` 应该在 Step 1（基础配置）的 `baseForm` 中填写
   - WebhookConfig 组件只负责 webhook 特定参数（positionSize, orderMode 等）
   - 但 WebhookConfig 的 `validate()` 方法会验证整个表单，包括 `credentialId` 和 `symbol`

3. **Wizard 验证流程**：
   ```javascript
   // BotCreateWizard.vue 第1267-1272行
   if (this.currentStep === 1 && this.$refs.strategyConfig) {
     try {
       await this.$refs.strategyConfig.validate()  // 调用 WebhookConfig 的 validate
     } catch {
       return  // 验证失败，直接返回，无法进入下一步
     }
   }
   ```

4. **验证失败的原因**：
   - WebhookConfig 的 `form` 对象没有初始化 `credentialId` 和 `symbol`
   - 当 `validate()` 被调用时，这两个必填字段为空，导致验证失败
   - Promise 被 reject，nextStep 方法直接 return，无法进入下一步

## 修复方案

### 方案：从 WebhookConfig 移除不必要的验证规则

**文件**: `/frontend-vue/src/views/trading-bot/components/configs/WebhookConfig.vue`

**修改位置**: 第193-202行的 `rules` 对象

**修改内容**:
移除 `credentialId` 和 `symbol` 的必填验证规则，只保留 webhook 特定参数的验证：

```javascript
// 修改前
rules: {
  credentialId: [
    { required: true, message: this.$t('trading-bot.wizard.credentialReq') }
  ],
  symbol: [
    { required: true, message: this.$t('trading-bot.wizard.symbolReq') }
  ],
  positionSize: [
    { required: true, type: 'number', min: 10, message: this.$t('trading-bot.webhook.positionSizeRequired') }
  ]
}

// 修改后
rules: {
  positionSize: [
    { required: true, type: 'number', min: 10, message: this.$t('trading-bot.webhook.positionSizeRequired') }
  ]
}
```

## 验证步骤

1. 打开前端页面 http://localhost:8000/#/trading-bot
2. 选择"Webhook 信号机器人"类型
3. 在 Step 1（基础配置）中填写：
   - 选择交易对（symbol）
   - 选择交易所凭证（credentialId）
4. 点击"下一步"，应该能正常进入 Step 2（策略参数配置）
5. 在 Step 2 中配置 webhook 参数（positionSize, orderMode 等）
6. 继续点击"下一步"，完成创建

## 影响范围

- **受益组件**: WebhookConfig.vue
- **相关组件**: BotCreateWizard.vue
- **用户体验**: 修复后，Webhook 机器人的创建流程将正常工作

## 技术说明

这个修复是正确的，因为：
1. **单一职责原则**：credentialId 和 symbol 是基础配置的一部分，应该在 Step 1 中验证，而不是在 Step 2 的策略参数配置中重复验证
2. **数据流向**：这些值通过 v-model 绑定到 `baseForm`，并通过 `strategyParams` 传递到 WebhookConfig，不需要在 WebhookConfig 中重复验证
3. **与后端一致**：后端 API 在创建策略时会验证所有必要字段，前端验证只是提供即时反馈
