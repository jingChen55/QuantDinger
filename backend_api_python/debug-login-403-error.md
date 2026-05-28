# Debug Session: login-403-error

## Status: [RESOLVED]

## Root Cause
**端口冲突**: macOS AirPlay 接收器服务 (`ControlCe` 进程) 占用了端口 5000，导致后端 API 无法启动在该端口上。

当请求发送到 `http://localhost:5000/api/auth/login` 时，请求被 AirTunes 服务接收，该服务不理解 API 格式，因此返回 403 Forbidden。

## Solution Applied
1. ✅ 将 `.env` 文件中的 `PYTHON_API_PORT` 从 `5000` 修改为 `5001`
2. ✅ 使用 `python3 run.py` 在端口 5001 启动后端服务
3. ✅ 成功验证登录端点在端口 5001 上正常工作

## Verification
```bash
# 测试登录端点 - 成功返回 token
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "quantdinger", "password": "123456"}'

# 响应结果
{
  "code": 1,
  "msg": "Login successful",
  "data": {
    "token": "eyJ...",
    "userinfo": {
      "id": 1,
      "username": "quantdinger",
      "role": "admin"
    }
  }
}
```

## Changes Made
- `.env`: `PYTHON_API_PORT=5000` → `PYTHON_API_PORT=5001`

## Notes
- 如果前端配置了固定的后端地址，需要同步更新前端配置中的 API 地址
- macOS Monterey 及以上版本默认启用 AirPlay，可以通过"系统偏好设置 > 通用 > AirPlay与handoff"关闭
- 推荐永久解决方案: 在 .env 文件中设置 `PYTHON_API_PORT=5001` 或关闭 macOS AirPlay
